from __future__ import annotations

import signal
from dataclasses import dataclass
from functools import cached_property
from os import PathLike
from typing import Mapping


@dataclass(frozen=True)
class CommandResult:
    """
    Result of executing a command.
    """

    command: str
    """Command that was executed."""
    exit_code: int
    """Exit code of the command."""

    stdout: CommandOutput
    """Captured raw output of the command's stdout."""
    stderr: CommandOutput
    """Captured raw output of the command's stderr."""
    output: CommandOutput
    """Captured combined raw output of the command's stdout and stderr."""

    @cached_property
    def success(self) -> bool:
        """
        Returns True if the command completed successfully (exit code is 0), False otherwise.
        """
        return self.exit_code == 0

    @cached_property
    def failure(self) -> bool:
        """
        Returns True if the command failed (exit code is non-zero), False otherwise.
        """
        return not self.success

    def __str__(self):
        if self.exit_code < 0:
            try:
                return f"Command '{self.command}', died with {signal.Signals(-self.exit_code)!r}."
            except ValueError:
                return f"Command '{self.command}' died with unknown signal {-self.exit_code:d}."

        if self.exit_code == 0:
            return f"Command '{self.command}' finished with exit status {self.exit_code:d}."

        return f"Command '{self.command}' finished with exit code {self.exit_code:d}."

    def __bool__(self):
        # CommandResult is truthy only if the command was successful
        return self.success


@dataclass(frozen=True)
class CommandOutput:
    lines: tuple[str, ...]
    """Output split into lines."""

    def __post_init__(self):
        # Ensure immutability even if a list was provided
        object.__setattr__(self, "lines", tuple(self.lines))

    @cached_property
    def text(self) -> str:
        """
        Raw output text.
        """
        return "\n".join(self.lines)

    @cached_property
    def stripped(self) -> str:
        """
        Output with leading and trailing whitespaces and newlines removed.
        """
        return self.text.strip(" \n")

    @cached_property
    def value(self) -> str | None:
        """
        Similar to "stripped", but returns None if the stripped output is an empty string.
        """
        stripped = self.stripped

        return stripped if (stripped != "") else None

    def __str__(self):
        return self.text


@dataclass(frozen=True)
class CommandContext:
    """
    Resolved execution context supplied to CommandRunner hooks.
    """

    command: str
    """Command string that will be executed."""
    cwd: PathLike[str] | str | None
    """Effective working directory for the subprocess."""
    env: Mapping[str, str] | None
    """Environment variables supplied to the subprocess, if any."""
    quiet: bool
    """Whether live output printing is suppressed."""
    check: bool
    """Whether non-zero exits will raise CommandError."""
    wsl: bool
    """Whether the command is executed through WSL."""
    encoding: str
    """Encoding used for decoding the subprocess output."""
