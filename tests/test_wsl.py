from __future__ import annotations

import io
from typing import Any

import pytest

from comrun import CommandRunner


class DummyPipe(io.BytesIO):
    def __enter__(self) -> "DummyPipe":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        self.close()


class DummyProcess:
    def __init__(
        self,
        args: list[str] | tuple[str, ...],
        *,
        stdout_data: bytes = b"",
        stderr_data: bytes = b"",
        returncode: int = 0,
    ) -> None:
        self.args = args
        self.stdout = DummyPipe(stdout_data)
        self.stderr = DummyPipe(stderr_data)
        self._returncode = returncode

    def wait(self) -> int:
        return self._returncode


def test_wsl_prefixes_command_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    On Windows with WSL enabled, commands should be prefixed with 'wsl'.

    Notes:
        We pretend to be on Windows by monkeypatching the internal flag.
    """

    import comrun.comrun as comrun_module

    captured: dict[str, Any] = {}

    def fake_popen(
        args: list[str] | tuple[str, ...],
        stdout: object,
        stderr: object,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> DummyProcess:
        captured["args"] = args
        captured["cwd"] = cwd
        captured["env"] = env
        return DummyProcess(args)

    monkeypatch.setattr(comrun_module, "_IS_ON_WINDOWS", True)
    monkeypatch.setattr(comrun_module.subprocess, "Popen", fake_popen)

    runner = CommandRunner(quiet=True, wsl=True)
    runner.run("echo 'hello'")

    assert captured["args"][0] == "wsl"
    assert captured["args"][1:] == ["echo", "hello"]
