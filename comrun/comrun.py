import os
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import IO, Callable

import rich

from .datatypes import CommandOutput, CommandResult
from .errors import CommandError

_IS_ON_WINDOWS = os.name == "nt"
_OUTPUT_ENCODING = "utf-8"


def _default_live_output_callback(line: str, command: str, is_stderr: bool):
    """
    Default line print callback that uses the Rich console to print the line.
    """
    console = rich.get_console()

    # sanitize the line to prevent Rich from interpreting control characters
    line = line.replace("[", "\\[")

    # set the style based on the stream
    style = "red" if is_stderr else None

    console.print(line, style=style)


@dataclass(frozen=True, kw_only=True)
class CommandRunner:
    cwd: os.PathLike[str] | None = None
    """Working directory to execute the command in."""
    env: dict[str, str] | None = None
    """Environment variables for the command's subprocess."""
    quiet: bool = False
    """If set to True, command output will not be printed to console. If set to False, command output will be printed to the console."""
    raise_on_error: bool = False
    """If set to True, a CommandError will be raised if the executed command exits with a non-zero exit code."""
    wsl: bool = True
    """If set to True (default) and running on Windows, the provided command will be run in WSL."""

    live_output_callback: Callable[[str, str, bool], None] = (
        _default_live_output_callback
    )
    """
    Callback to print a line of the command's output.
    Will not be called if the 'quiet' option is set to True.

    Args:
        line: The line to print.
        command: String containing the command producing the output.
        stderr: If set to True, the line is from the command's stderr stream (stdout otherwise).

    Defaults to using print() if not set.
    """
    pre_run_callback: Callable[[str, bool], None] | None = None
    """Callback to execute before the command is run. Receives the command string and quiet flag as arguments."""
    post_run_callback: Callable[[CommandResult, bool], None] | None = None
    """Callback to execute after the command is finished. Receives the CommandResult object and quiet flag as arguments."""

    def __call__(
        self,
        command: str | list[str],
        *,
        cwd: os.PathLike[str] | None = None,
        env: dict[str, str] | None = None,
        quiet: bool | None = None,
        raise_on_error: bool | None = None,
        wsl: bool | None = None,
    ) -> CommandResult:
        """
        Executes the given command in a subprocess.

        Args:
            command: Command to execute.
            cwd: Working directory to execute the command in.
                Defaults to the working directory set in the constructor.
            env: Environment variables for the command's subprocess.
                Defaults to the environment set in the constructor.
            quiet: If set to True, command output will be suppressed. If set to False, command output will be printed to the console.
                Defaults to the value set in the constructor.
            raise_on_error: If set to True, a CommandError will be raised if the executed command exits with a non-zero exit code.
            wsl: If set to True and running on Windows, the provided command will be run in WSL.
                Defaults to the value set in the constructor.
        """

        # use the arguments or pre-configured values
        cwd = cwd or self.cwd
        env = env or self.env
        wsl = wsl or self.wsl
        quiet = quiet or self.quiet
        raise_on_error = (
            raise_on_error if (raise_on_error is not None) else self.raise_on_error
        )

        # use WSL if required on Windows
        command_string = command if isinstance(command, str) else shlex.join(command)
        if _IS_ON_WINDOWS and wsl:
            command = f"wsl {command_string}"

        # prepare command args list
        args = shlex.split(command) if isinstance(command, str) else command

        # execute pre-run callback
        if self.pre_run_callback:
            self.pre_run_callback(command_string, quiet)

        # start the subprocess
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

        # lock is required to prevent prints from stdout- and stderr-reading threads from interfering with each other
        output_lock = Lock()

        # prepare output buffers
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        all_lines: list[str] = []

        # define the output line callback
        def _handle_subprocess_output(pipe: IO, _stderr: bool):
            """
            Reads lines from the stream and decodes them.
            """
            for line in iter(pipe.readline, b""):  # b'\n'-separated lines
                decoded_line: str = line.decode(_OUTPUT_ENCODING)

                # remove the trailing newline character
                decoded_line = decoded_line[:-1]

                with output_lock:
                    # capture output
                    if _stderr:
                        stderr_lines.append(decoded_line)
                    else:
                        stdout_lines.append(decoded_line)

                    # capture shared output
                    all_lines.append(decoded_line)

                    # print to console if not silenced
                    if not quiet:
                        try:
                            self.live_output_callback(
                                decoded_line, command_string, _stderr
                            )
                        except Exception as e:
                            rich.print(
                                f"[red]{type(e).__name__} caught in live output callback. Please check your callback implementation.[/]"
                            )

        try:
            # read stdout and stderr in threads to capture outputs from both streams concurrently
            with (
                process.stdout,
                process.stderr,
                ThreadPoolExecutor(max_workers=2) as executor,
            ):
                executor.submit(_handle_subprocess_output, process.stdout, False)
                executor.submit(_handle_subprocess_output, process.stderr, True)
        except KeyboardInterrupt:
            # kill the subprocess if the user interrupts the program
            process.kill()

        # wait for the subprocess to finish
        exit_code = process.wait()

        # create the result object
        result = CommandResult(
            command=command_string,
            exit_code=exit_code,
            stdout=CommandOutput(stdout_lines),
            stderr=CommandOutput(stderr_lines),
            output=CommandOutput(all_lines),
        )

        # raise on error if required
        if result.failure and raise_on_error:
            raise CommandError(command_string, result)

        # execute post-run callback
        if self.post_run_callback:
            self.post_run_callback(result, quiet)

        return result
