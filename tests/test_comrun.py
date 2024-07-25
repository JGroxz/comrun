import os
from pathlib import Path

import pytest

from comrun import CommandRunner
from comrun.errors import CommandError

IS_ON_WINDOWS = os.name == "nt"


def test_exit_codes():
    assert not IS_ON_WINDOWS, "This test is not tested on Windows (yet)."

    comrun = CommandRunner()

    # test a valid command with zero exit code
    command = "true" if (not IS_ON_WINDOWS) else "exit /b 0"
    result = comrun(command, raise_on_error=False)

    assert (
        result.success
    ), f"Command '{command}' must successfully execute with exit code 0."

    # test a valid command with non-zero exit code (without raising an exception
    command = "false" if not IS_ON_WINDOWS else "exit /b 42"
    excepted_exit_code = 1
    result = comrun(command, raise_on_error=False)

    assert result.failure, f"Command '{command}' must fail with non-zero exit code."
    assert (
        result.exit_code == excepted_exit_code
    ), f"Command '{command}' must fail with exit code {excepted_exit_code}."

    # test a valid command with non-zero exit code (with raise_on_error)
    with pytest.raises(CommandError):
        comrun(command, raise_on_error=True)


def test_cwd():
    """Test that the working directory is being set correctly when running a shell command."""

    comrun = CommandRunner()

    # current working directory
    command = "pwd"
    result = comrun("pwd")

    assert result.success, f"Command '{command}' must successfully execute."
    assert result.output.stripped == os.getcwd(), "Working directory is not correct."

    print(f"none: {result.output}")

    # custom working directory
    custom_cwd = str(Path(__file__).parent.parent)
    result = comrun(command, cwd=custom_cwd)

    print(f"custom: {result.output}")

    assert result.success, f"Command '{command}' must successfully execute."
    assert (
        result.output.stripped == custom_cwd
    ), "Custom working directory is not correct."


def test_output():
    """Test that a valid shell command is executed correctly."""

    comrun = CommandRunner()

    test_echo_message_lines = [
        "The cake is a lie.",
        "But this test is not.",
    ]
    test_echo_message = "\n".join(test_echo_message_lines)

    command = f"echo '{test_echo_message}'"
    result = comrun(command, wsl=True)

    assert result.success, f"Command '{command}' must successfully execute."
    assert (
        result.output.text == test_echo_message
    ), "Stripped captured output of the command is not correct."
    assert (
        result.output.lines == test_echo_message_lines
    ), "Captured output of the command split into lines is not correct."


def test_environment_variables():
    """Test that environment variables are being set correctly when running a shell command."""

    comrun = CommandRunner()

    # test environment variables
    test_env_var_name = "TEST_ENV_VAR"
    test_env_var_value = "test_value"
    test_env = {test_env_var_name: test_env_var_value}

    command = f"printenv {test_env_var_name}"
    result = comrun(command, env=test_env)

    assert result.success, f"Command '{command}' must successfully execute."
    assert (
        result.output.stripped == test_env_var_value
    ), "Environment variable is not set correctly."


def test_invalid_command():
    """Test that an invalid shell command raises an exception."""

    comrun = CommandRunner()

    # test an invalid command (it must raise an exception even if raise_on_error is False)
    invalid_command = (
        "invalid_command_that_doesnt_exist --with-invalid-option and-invalid-argument"
    )
    with pytest.raises(FileNotFoundError):
        comrun(invalid_command, raise_on_error=False)
