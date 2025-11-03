import pytest

from comrun import CommandRunner


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call():
    print()  # <- newline at the start of the logs to make them more readable
    yield


@pytest.fixture()
def comrun() -> CommandRunner:
    """Provides a CommandRunner instance for tests."""

    from comrun import CommandRunner

    return CommandRunner()
