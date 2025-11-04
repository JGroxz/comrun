"""
Tests for CommandResult behavior in comrun.
"""

from __future__ import annotations

import os

import pytest

from comrun import CommandError, CommandRunner

IS_ON_WINDOWS = os.name == "nt"


def test_command_result_truthiness(comrun: CommandRunner) -> None:
    """
    CommandResult should be truthy only for successful commands.
    """

    success_cmd = "exit /b 0" if IS_ON_WINDOWS else "true"
    assert comrun.run(success_cmd)

    failure_cmd = "exit /b 42" if IS_ON_WINDOWS else "false"
    assert not comrun.run(failure_cmd)


@pytest.mark.asyncio
async def test_exit_codes(comrun: CommandRunner) -> None:
    """
    Exit codes should be captured for both success and failure.
    """

    command = "exit /b 0" if IS_ON_WINDOWS else "true"
    result = comrun.run(command)
    assert result.success

    failing_command = "exit /b 42" if IS_ON_WINDOWS else "false"
    result = comrun.run(failing_command)
    assert result.failure
    assert result.exit_code == 1

    async_result = await comrun.run_async(failing_command)
    assert async_result == result

    with pytest.raises(CommandError):
        comrun.run(failing_command, check=True)
