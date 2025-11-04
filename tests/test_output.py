""" """

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from comrun import CommandOutput, CommandRunner
from comrun.comrun import StreamName
from comrun.datatypes import CommandContext

IS_ON_WINDOWS = os.name == "nt"


@pytest.mark.asyncio
async def test_output_capture(comrun: CommandRunner) -> None:
    """
    Stdout and stderr should be captured and merged in order.
    """

    lines = ["The cake is a lie.", "But this test is not."]
    message = "\n".join(lines)

    command = f"echo '{message}'"
    result = comrun.run(command, wsl=True)

    assert result.success
    assert result.output.text == message
    assert list(result.output.lines) == lines

    async_result = await comrun.run_async(command, wsl=True)
    assert async_result == result


def test_output_properties() -> None:
    """
    CommandOutput convenience properties should behave as documented.
    """
    output = CommandOutput(("  hello  ", "world"))
    assert output.lines == ("  hello  ", "world")
    assert output.text == "  hello  \nworld"
    assert output.stripped == "hello  \nworld"
    assert output.value == "hello  \nworld"
    assert str(output) == output.text

    empty = CommandOutput(("   ", ""))
    assert empty.value is None
