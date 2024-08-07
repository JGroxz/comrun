from __future__ import annotations

import signal
from dataclasses import dataclass
from functools import cached_property


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
            return f"Command '{self.command}' finished with non-zero exit status {self.exit_code:d}."

        return f"Command '{self.command}' finished with exit code {self.exit_code:d}."

    def __bool__(self):
        # CommandResult is truthy only if the command was successful
        return self.success


@dataclass(frozen=True)
class CommandOutput:
    lines: list[str]
    """Output split into lines."""

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
