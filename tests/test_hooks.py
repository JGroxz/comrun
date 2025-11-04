"""
Tests verifying that command lifecycle hooks function correctly.
"""

from __future__ import annotations

import sys

import pytest

from comrun import CommandResult, CommandRunner
from comrun.comrun import StreamName
from comrun.datatypes import CommandContext


def test_hooks_receive_context_and_streams() -> None:
    """
    Hooks should receive a consistent context and accurate stream labels.
    """

    starts: list[CommandContext] = []
    finishes: list[tuple[CommandResult, CommandContext]] = []
    lines: list[tuple[str, StreamName, CommandContext]] = []

    def on_start(ctx: CommandContext) -> None:
        starts.append(ctx)

    def on_line(line: str, stream: StreamName, ctx: CommandContext) -> None:
        lines.append((line, stream, ctx))

    def on_finish(result: CommandResult, ctx: CommandContext) -> None:
        finishes.append((result, ctx))

    runner = CommandRunner(
        on_start=on_start,
        on_line=on_line,
        on_finish=on_finish,
        encoding="utf-8",
        quiet=False,
    )

    result_stdout = runner.run(["echo", "out"], check=False)
    assert result_stdout.stdout.lines == ("out",), "stdout should capture echo output"

    result_stderr = runner.run(
        [sys.executable, "-c", 'import sys; sys.stderr.write("err\\n")'],
        check=False,
    )
    assert result_stderr.stderr.lines == ("err",), (
        "stderr should capture scripted output"
    )

    assert len(starts) == 2, "on_start should run for each invocation"
    assert len(finishes) == 2, "on_finish should run for each invocation"

    # Hoist contexts and results for inspection
    context_stdout = starts[0]
    context_stderr = starts[1]
    assert context_stdout.encoding == "utf-8"
    assert context_stderr.encoding == "utf-8"

    assert finishes[0][0] is result_stdout
    assert finishes[1][0] is result_stderr
    assert finishes[0][1] is context_stdout
    assert finishes[1][1] is context_stderr

    assert {stream for _, stream, _ in lines} == {"stdout", "stderr"}
    assert {text for text, _, _ in lines} == {"out", "err"}
    assert {ctx for _, _, ctx in lines} == {
        context_stdout,
        context_stderr,
    }, "Callbacks should provide the corresponding context instances"


def test_on_line_hook_exception_propagation() -> None:
    """
    BaseException raised inside on_line should propagate to the caller.
    """

    class HookError(BaseException):
        pass

    def broken_hook(*_: object) -> None:
        raise HookError()

    runner = CommandRunner(on_line=broken_hook)

    with pytest.raises(HookError):
        runner.run("echo", check=False)
