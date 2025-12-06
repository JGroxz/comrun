import signal
from subprocess import SubprocessError

from .datatypes import CommandResult


class CommandError(SubprocessError):
    """
    Raised when a CommandRunner instance is called with check=True and the process returns a non-zero exit status.
    """

    def __init__(self, command: str, result: CommandResult):
        self.command = command
        """The command that was run."""
        self.result = result
        """The result of the command that was run."""

    @property
    def cmd(self):
        """Shorthand for command attribute."""
        return self.command

    @property
    def exit_code(self):
        """Shorthand for exit_code attribute."""
        return self.result.exit_code

    def __str__(self):
        if self.exit_code and self.exit_code < 0:
            try:
                return f"Command died with {signal.Signals(-self.exit_code)!r}: '{self.cmd}'"
            except ValueError:
                return f"Command died with unknown signal {-self.exit_code:d}: '{self.cmd}'"
        else:
            return f"Command returned non-zero exit status {self.exit_code:d}: '{self.cmd}'"
