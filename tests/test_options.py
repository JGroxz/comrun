"""
Tests for options that can be passed to CommandRunner.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from comrun import CommandRunner, StreamName, CommandContext
from comrun.errors import CommandError


@pytest.mark.asyncio
async def test_cwd(comrun: CommandRunner) -> None:
    """
    The working directory should be applied to subprocesses.
    """

    command = "pwd"

    result = comrun.run(command)
    assert result.success, "pwd without overrides should be successful"
    assert result.output.stripped == os.getcwd(), (
        "pwd output should match current working directory"
    )

    custom_cwd = str(Path(__file__).parent.parent)
    custom_result = comrun.run(command, cwd=custom_cwd)
    assert custom_result.success, "pwd with custom cwd should be successful"
    assert custom_result.output.stripped == custom_cwd, (
        "pwd output should match custom working directory"
    )

    async_result = await comrun.run_async(command, cwd=custom_cwd)
    assert async_result == custom_result, "async run should match sync result"


@pytest.mark.asyncio
async def test_env(comrun: CommandRunner) -> None:
    """
    Environment overrides should reach the subprocess.
    """

    var = "TEST_ENV_VAR"
    value = "test_value"

    command = f"printenv {var}"
    result = comrun.run(command, env={var: value})

    assert result.success, "printenv should succeed when variable is provided"
    assert result.output.stripped == value, (
        "Environment override should appear in subprocess"
    )

    async_result = await comrun.run_async(command, env={var: value})
    assert async_result == result, "async run should match sync when overriding env"


def test_quiet() -> None:
    """
    When quiet mode is enabled, live output callbacks should not fire, but output is still captured.
    """

    records: list[tuple[str, str, object]] = []

    def on_line(line: str, stream: str, ctx: object) -> None:
        records.append((line, stream, ctx))

    runner = CommandRunner(on_line=on_line)

    command = [
        sys.executable,
        "-c",
        'import sys; sys.stdout.write("quiet\\n"); sys.stderr.write("noise\\n")',
    ]

    # Test with quiet=True (on_line hooks should be suppressed)
    result = runner.run(command, quiet=True)

    assert result.stdout.lines == ("quiet",), (
        "stdout should still be captured when quiet=True"
    )
    assert result.stderr.lines == ("noise",), (
        "stderr should still be captured when quiet=True"
    )
    assert records == [], "quiet=True should suppress live output callbacks"

    # Test with quiet=False (on_line hooks should resume)
    new_result = runner.run(command, quiet=False)

    assert new_result.stdout.lines == ("quiet",), "stdout capture remains intact"
    assert {stream for _, stream, _ in records} == {
        "stdout",
        "stderr",
    }, "Callbacks should resume when quiet=False"


def test_check() -> None:
    """
    The check option should raise an exception on non-zero exit codes.
    """

    runner = CommandRunner()

    error_code = 42
    failing_command = [sys.executable, "-c", f"import sys; sys.exit({error_code})"]

    # Test with check=True (should raise CommandError)
    with pytest.raises(CommandError) as exc_info:
        runner.run(failing_command, check=True)

    assert exc_info.value.exit_code == error_code, (
        "CommandError exception should include the correct exit code"
    )

    # Test with check=False (should not raise)
    result = runner.run(failing_command, check=False)

    assert result.exit_code == 42, "Result should capture the non-zero exit code"


def test_encoding() -> None:
    """
    Explicit encodings should decode bytes correctly and escape Rich markup.
    """
    records: list[tuple[str, StreamName, CommandContext]] = []

    def record_line(line: str, stream: StreamName, ctx: CommandContext) -> None:
        records.append((line, stream, ctx))

    runner = CommandRunner(on_line=record_line, encoding="utf-8")

    # Latin-1 test
    latin_command = [
        sys.executable,
        "-c",
        'import sys; sys.stdout.buffer.write(b"hi\\xff[!\\n")',
    ]
    latin_result = runner.run(latin_command, encoding="latin-1")

    assert latin_result.stdout.lines == ("hiÿ[!",)
    assert len(records) == 1
    line, stream, ctx = records.pop()
    assert line == "hiÿ[!"
    assert stream == "stdout"
    assert ctx.encoding == "latin-1"

    # UTF-16 test
    utf16_command = [
        sys.executable,
        "-c",
        'import sys; sys.stdout.buffer.write("あい".encode("utf-16le"))',
    ]
    utf16_result = runner.run(utf16_command, encoding="utf-16le")

    assert utf16_result.stdout.lines == ("あい",)
    assert len(records) == 1
    line, stream, ctx = records.pop()
    assert line == "あい"
    assert stream == "stdout"
    assert ctx.encoding == "utf-16le"


def test_with_options_creates_configured_copy(comrun: CommandRunner) -> None:
    """
    with_options() should return a new runner with the requested overrides.
    """

    same_runner = comrun.with_options()
    assert same_runner is comrun, (
        "without overrides, with_options should return the same runner"
    )

    custom_env = {"WITH_OPTIONS_TEST": "1"}
    configured_runner = comrun.with_options(
        quiet=True,
        env=custom_env,
        wsl=False,
    )

    assert configured_runner is not comrun, "overrides should return a new runner"
    assert configured_runner.quiet is True, "quiet override should apply to new runner"
    assert configured_runner.env == custom_env, (
        "env override should persist on new runner"
    )
    assert configured_runner.wsl is False, "wsl override should persist on new runner"

    assert comrun.quiet is False, "original runner quiet flag should remain unchanged"
    assert comrun.env is None, "original runner env should remain unchanged"
    assert comrun.wsl is True, "original runner wsl flag should remain unchanged"

    chained_runner = configured_runner.with_options(quiet=False)
    assert chained_runner is not configured_runner, (
        "changing options again should produce another runner"
    )
    assert chained_runner.quiet is False, "latest quiet override should be reflected"
    assert chained_runner.env == custom_env, "unchanged env override should persist"
    assert chained_runner.wsl is False, "unchanged wsl override should persist"
