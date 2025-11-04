import asyncio
import locale
import os
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from threading import Lock
from typing import IO, Callable, Literal

import rich
from rich.markup import escape as rich_escape

from .datatypes import CommandContext, CommandOutput, CommandResult
from .errors import CommandError

_DEFAULT_ENCODING = locale.getpreferredencoding(False) or "utf-8"
_IS_ON_WINDOWS = os.name == "nt"
_UNSET = object()


StreamName = Literal["stdout", "stderr"]


def _default_on_line(line: str, stream: StreamName, ctx: CommandContext):
    """
    Default line print callback that uses the Rich console to print the line.
    """
    console = rich.get_console()

    # Sanitize the line to prevent Rich from interpreting control characters
    line = rich_escape(line)

    # Set the style based on the stream
    style = "red" if stream == "stderr" else None

    console.print(line, style=style, crop=False)


@dataclass(frozen=True, kw_only=True)
class CommandRunner:
    cwd: os.PathLike[str] | str | None = None
    """Working directory for launched commands; defaults to the parent process cwd when unset."""
    env: dict[str, str] | None = None
    """Environment variable overrides merged into the subprocess environment."""
    quiet: bool = False
    """Suppress live output when True; defaults to streaming command output to the console."""
    check: bool = False
    """Raise CommandError on non-zero exit codes when True (mirrors subprocess.run(check=True))."""
    wsl: bool = True
    """On Windows, run the command through WSL when True; ignored on other platforms."""
    encoding: str = _DEFAULT_ENCODING
    """Encoding used to decode command output."""
    on_line: Callable[[str, StreamName, CommandContext], None] = _default_on_line
    """Per-line output callback `(line, stream, ctx)`; skipped when quiet=True. Defaults to Rich console."""
    on_start: Callable[[CommandContext], None] | None = None
    """Hook invoked just before execution with the resolved command context."""
    on_finish: Callable[[CommandResult, CommandContext], None] | None = None
    """Hook invoked after completion with the CommandResult and command context."""

    def with_options(
        self,
        *,
        cwd: os.PathLike[str] | str | None | object = _UNSET,
        env: dict[str, str] | None | object = _UNSET,
        quiet: bool | None | object = _UNSET,
        check: bool | None | object = _UNSET,
        wsl: bool | None | object = _UNSET,
        encoding: str | object = _UNSET,
        on_line: Callable[[str, StreamName, CommandContext], None] | object = _UNSET,
        on_start: Callable[[CommandContext], None] | None | object = _UNSET,
        on_finish: Callable[[CommandResult, CommandContext], None]
        | None
        | object = _UNSET,
    ) -> "CommandRunner":
        """
        Returns a copy of this CommandRunner with the provided options overridden.
        """
        updates: dict[str, object] = {}

        if cwd is not _UNSET:
            updates["cwd"] = cwd
        if env is not _UNSET:
            updates["env"] = env
        if quiet is not _UNSET:
            updates["quiet"] = quiet
        if check is not _UNSET:
            updates["check"] = check
        if wsl is not _UNSET:
            updates["wsl"] = wsl
        if on_line is not _UNSET:
            updates["on_line"] = on_line
        if on_start is not _UNSET:
            updates["on_start"] = on_start
        if on_finish is not _UNSET:
            updates["on_finish"] = on_finish
        if encoding is not _UNSET:
            updates["encoding"] = encoding

        return replace(self, **updates) if updates else self

    def __call__(
        self,
        command: str | list[str],
        *,
        cwd: os.PathLike[str] | str | None = None,
        env: dict[str, str] | None = None,
        quiet: bool | None = None,
        check: bool | None = None,
        wsl: bool | None = None,
        encoding: str | None = None,
    ) -> CommandResult:
        """Alias for run()."""
        return self.run(
            command,
            cwd=cwd,
            env=env,
            quiet=quiet,
            check=check,
            wsl=wsl,
            encoding=encoding,
        )

    def run(
        self,
        command: str | list[str],
        *,
        cwd: os.PathLike[str] | str | None = None,
        env: dict[str, str] | None = None,
        quiet: bool | None = None,
        check: bool | None = None,
        wsl: bool | None = None,
        encoding: str | None = None,
    ) -> CommandResult:
        """
        Executes the given command in a subprocess.

        Args:
            command: Command to execute.
            cwd: Working directory to execute the command in.
                Defaults to runner's current configuration.
            env: Environment variables for the command's subprocess.
                Defaults to runner's current configuration.
            quiet: If set to True, command output will be suppressed. If set to False, command output will be printed to the console.
                Defaults to runner's current configuration.
            check: If set to True, a CommandError will be raised if the executed command exits with a non-zero exit code.
            wsl: If set to True and running on Windows, the provided command will be run in WSL.
                Defaults to runner's current configuration.
            encoding: Encoding to use when decoding command output.
                Defaults to runner's current configuration.
        """

        # Use the arguments or pre-configured values
        cwd = self.cwd if (cwd is None) else cwd
        env = self.env if (env is None) else env
        wsl = self.wsl if (wsl is None) else wsl
        quiet = self.quiet if (quiet is None) else quiet
        check = self.check if (check is None) else check
        encoding = self.encoding if (encoding is None) else encoding

        # Use WSL if required on Windows
        command_string = command if isinstance(command, str) else shlex.join(command)
        if _IS_ON_WINDOWS and wsl:
            command = f"wsl {command_string}"

        # Prepare the command args list
        args = shlex.split(command) if isinstance(command, str) else command

        # Craft the context
        context = CommandContext(
            command=command_string,
            cwd=cwd,
            env=env,
            quiet=quiet,
            check=check,
            wsl=bool(_IS_ON_WINDOWS and wsl),
            encoding=encoding,
        )

        # Execute the pre-run callback
        if self.on_start:
            self.on_start(context)

        # Start the subprocess
        process = subprocess.Popen(  # nosec
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
        if process.stdout is None:
            raise RuntimeError("Failed to open the command's stdout stream.")
        if process.stderr is None:
            raise RuntimeError("Failed to open the command's stderr stream.")

        # Lock is required to prevent prints from stdout- and stderr-reading threads from interfering with each other
        output_lock = Lock()

        # Prepare output buffers
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        all_lines: list[str] = []

        # Define the output line callback
        def _handle_subprocess_output(pipe: IO, _stderr: bool, *, encoding: str):
            """
            Reads lines from the stream and decodes them.
            """
            for line in iter(pipe.readline, b""):  # Lines are separated by b'\n'.
                decoded_line: str = line.decode(encoding, errors="replace")

                # Remove the trailing newline characters
                decoded_line = decoded_line.rstrip("\r\n")

                with output_lock:
                    # Capture output
                    if _stderr:
                        stderr_lines.append(decoded_line)
                    else:
                        stdout_lines.append(decoded_line)

                    # Capture shared output
                    all_lines.append(decoded_line)

                    # Print to console if not silenced
                    if not quiet:
                        try:
                            stream: StreamName = "stderr" if _stderr else "stdout"
                            self.on_line(decoded_line, stream, context)
                        except Exception as e:
                            error_message = rich_escape(str(e))
                            rich.print(
                                f"[red][i]{type(e).__name__}[/] caught in on_line handler:[/] {error_message}"
                            )

        try:
            # Read stdout and stderr in threads to capture outputs from both streams concurrently
            with (
                process.stdout,
                process.stderr,
                ThreadPoolExecutor(max_workers=2) as executor,
            ):
                stdout_future = executor.submit(
                    _handle_subprocess_output,
                    process.stdout,
                    False,
                    encoding=encoding,
                )
                stderr_future = executor.submit(
                    _handle_subprocess_output,
                    process.stderr,
                    True,
                    encoding=encoding,
                )
                stdout_future.result()
                stderr_future.result()
        except KeyboardInterrupt:
            # Kill the subprocess if the user interrupts the program
            process.kill()

        # Wait for the subprocess to finish
        exit_code = process.wait()

        # Create the result object
        result = CommandResult(
            command=command_string,
            exit_code=exit_code,
            stdout=CommandOutput(tuple(stdout_lines)),
            stderr=CommandOutput(tuple(stderr_lines)),
            output=CommandOutput(tuple(all_lines)),
        )

        # Raise on error if required
        if result.failure and check:
            raise CommandError(command_string, result)

        # Execute the post-run callback
        if self.on_finish:
            self.on_finish(result, context)

        return result

    async def run_async(
        self,
        command: str | list[str],
        *,
        cwd: os.PathLike[str] | str | None = None,
        env: dict[str, str] | None = None,
        quiet: bool | None = None,
        check: bool | None = None,
        wsl: bool | None = None,
        encoding: str | None = None,
    ) -> CommandResult:
        """
        Executes the given command in a subprocess, asynchronously.

        Args:
            command: Command to execute.
            cwd: Working directory to execute the command in.
                Defaults to runner's current configuration.
            env: Environment variables for the command's subprocess.
                Defaults to runner's current configuration.
            quiet: If set to True, command output will be suppressed. If set to False, command output will be printed to the console.
                Defaults to runner's current configuration.
            check: If set to True, a CommandError will be raised if the executed command exits with a non-zero exit code.
            wsl: If set to True and running on Windows, the provided command will be run in WSL.
                Defaults to runner's current configuration.
            encoding: Encoding to use when decoding command output.
                Defaults to runner's current configuration.
        """
        return await asyncio.to_thread(
            self.run,
            command,
            cwd=cwd,
            env=env,
            quiet=quiet,
            check=check,
            wsl=wsl,
            encoding=encoding,
        )
