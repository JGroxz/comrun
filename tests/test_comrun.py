import os
from pathlib import Path

import pytest

from comrun import CommandRunner, CommandError

IS_ON_WINDOWS = os.name == "nt"


@pytest.mark.asyncio
async def test_exit_codes(comrun: CommandRunner):
    """
    Tests that exit codes are captured correctly for successful and failing commands.
    """
    assert not IS_ON_WINDOWS, "This test is not tested on Windows (yet)."

    # test a valid command with zero exit code
    command = "true" if (not IS_ON_WINDOWS) else "exit /b 0"
    result = comrun.run(command, raise_on_error=False)

    assert result.success, (
        f"Command '{command}' must successfully execute with exit code 0."
    )

    # test a valid command with non-zero exit code (without raising an exception
    command = "false" if not IS_ON_WINDOWS else "exit /b 42"
    excepted_exit_code = 1
    result = comrun.run(command, raise_on_error=False)

    assert result.failure, f"Command '{command}' must fail with non-zero exit code."
    assert result.exit_code == excepted_exit_code, (
        f"Command '{command}' must fail with exit code {excepted_exit_code}."
    )

    # same for async
    a_result = await comrun.run_async(command, raise_on_error=False)
    assert a_result == result, (
        "The async invocation result should be the same as the sync result."
    )

    # test a valid command with non-zero exit code (with raise_on_error)
    with pytest.raises(CommandError):
        comrun.run(command, raise_on_error=True)


@pytest.mark.asyncio
async def test_cwd(comrun: CommandRunner):
    """
    Tests that the working directory is being set correctly when running a shell command.
    """

    # current working directory
    command = "pwd"
    result = comrun.run("pwd")

    assert result.success, f"Command '{command}' must successfully execute."
    assert result.output.stripped == os.getcwd(), "Working directory is not correct."

    # custom working directory
    custom_cwd = str(Path(__file__).parent.parent)
    result = comrun.run(command, cwd=custom_cwd)

    assert result.success, f"Command '{command}' must successfully execute."
    assert result.output.stripped == custom_cwd, (
        "Custom working directory is not correct."
    )

    # same for async
    a_result = await comrun.run_async(command, cwd=custom_cwd)
    assert a_result == result, (
        "The async invocation result should be the same as the sync result."
    )


@pytest.mark.asyncio
async def test_output(comrun: CommandRunner):
    """
    Tests that stdout, stderr, and combined output are captured in the expected formats.
    """

    test_echo_message_lines = [
        "The cake is a lie.",
        "But this test is not.",
    ]
    test_echo_message = "\n".join(test_echo_message_lines)

    command = f"echo '{test_echo_message}'"
    result = comrun.run(command, wsl=True)

    assert result.success, f"Command '{command}' must successfully execute."
    assert result.output.text == test_echo_message, (
        "Stripped captured output of the command is not correct."
    )
    assert list(result.output.lines) == test_echo_message_lines, (
        "Captured output of the command split into lines is not correct."
    )

    # same for async
    a_result = await comrun.run_async(command, wsl=True)
    assert a_result == result, (
        "The async invocation result should be the same as the sync result."
    )


@pytest.mark.asyncio
async def test_environment_variables(comrun: CommandRunner):
    """
    Tests that environment variables are applied to the spawned subprocess.
    """

    # test environment variables
    test_env_var_name = "TEST_ENV_VAR"
    test_env_var_value = "test_value"
    test_env = {test_env_var_name: test_env_var_value}

    command = f"printenv {test_env_var_name}"
    result = comrun.run(command, env=test_env)

    assert result.success, f"Command '{command}' must successfully execute."
    assert result.output.stripped == test_env_var_value, (
        "Environment variable is not set correctly."
    )

    # same for async
    a_result = await comrun.run_async(command, env=test_env)
    assert a_result == result, (
        "The async invocation result should be the same as the sync result."
    )


@pytest.mark.asyncio
async def test_invalid_command(comrun: CommandRunner):
    """
    Tests that running a non-existent command raises the expected exception.
    """

    # test an invalid command (it must raise an exception even if raise_on_error is False)
    invalid_command = (
        "invalid_command_that_doesnt_exist --with-invalid-option and-invalid-argument"
    )
    with pytest.raises(FileNotFoundError):
        comrun.run(invalid_command, raise_on_error=False)

    # same for async
    with pytest.raises(FileNotFoundError):
        await comrun.run_async(invalid_command, raise_on_error=False)


def test_command_result_truthiness(comrun: CommandRunner):
    """
    Tests that CommandResult truthiness reflects command success.
    """

    # test a valid command with zero exit code
    command = "true" if (not IS_ON_WINDOWS) else "exit /b 0"
    result = comrun.run(command, raise_on_error=False)

    assert result, "A successful command must be truthy."

    # test a valid command with non-zero exit code
    command = "false" if (not IS_ON_WINDOWS) else "exit /b 42"
    result = comrun.run(command, raise_on_error=False)

    assert not result, "A failed command must not be truthy."


def test_with_options_creates_configured_copy(comrun: CommandRunner):
    """
    Tests that with_options returns a new runner with the requested overrides.
    """

    same_runner = comrun.with_options()
    assert (
        same_runner is comrun
    ), "with_options() without overrides should return the original instance."

    custom_env = {"WITH_OPTIONS_TEST": "1"}
    configured_runner = comrun.with_options(
        quiet=True,
        env=custom_env,
        wsl=False,
    )

    assert (
        configured_runner is not comrun
    ), "Overriding options should yield a new CommandRunner instance."
    assert configured_runner.quiet is True, "Quiet override must apply to the new runner."
    assert (
        configured_runner.env == custom_env
    ), "Environment override must be carried to the new runner."
    assert configured_runner.wsl is False, "WSL override must be carried to the new runner."

    assert comrun.quiet is False, "Original runner's quiet flag must remain unchanged."
    assert comrun.env is None, "Original runner's env must remain unchanged."
    assert comrun.wsl is True, "Original runner's WSL flag must remain unchanged."

    chained_runner = configured_runner.with_options(quiet=False)
    assert (
        chained_runner is not configured_runner
    ), "A chained with_options() call should return a different instance when overrides change."
    assert chained_runner.quiet is False, "Latest quiet override must be reflected."
    assert (
        chained_runner.env == custom_env
    ), "Existing overrides must persist when not replaced."
    assert (
        chained_runner.wsl is False
    ), "Unchanged options should carry forward through chained overrides."
