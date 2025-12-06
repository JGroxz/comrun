# Cookbook

Practical examples for common runner configurations and usage patterns.

### Run quietly but fail fast

```python
from comrun import CommandRunner

runner = CommandRunner(check=True, quiet=True)
result = runner("pytest -q")
```

### Log each line with a prefix

```python
import logging
from comrun import CommandContext, CommandRunner

log = logging.getLogger(__name__)

def log_lines(line: str, stream: str, ctx: CommandContext):
    # log each line with stream name, command info and it's output
    log.info("%s | %s | %s", stream.upper(), ctx.command, line)

runner = CommandRunner(on_line=log_lines)
runner("git status")
```

### Add env vars and a working directory

```python
import os
from comrun import CommandRunner

env = {**os.environ, "APP_ENV": "dev"}
runner = CommandRunner(cwd="examples", env=env)
runner("python main.py")
```

### Run on Windows without WSL

```python
from comrun import CommandRunner

windows_runner = CommandRunner(wsl=False)
windows_runner(["cmd", "/c", "dir"])  # (1)!
```

1. Executes `dir` in the native **cmd.exe** instead of WSL.

    !!! note
        comrun uses `shell=False`, so shell built-ins like `dir` must be invoked via `cmd /c ...` (or `powershell -Command ...`).

### Derive a runner with new options

```python
base = CommandRunner(check=True, quiet=True)
verbose = base.with_options(quiet=False)

verbose("echo loud")   # (1)!
base("echo silent")    # (2)!
```

1. Inherits base settings, but prints live output because `quiet=False`.
2. Uses the quiet base runner.

## Branch on failure without raising

```python
from comrun import CommandRunner

runner = CommandRunner(check=False)
result = runner("exit 1")  # (1)!

if result.failure:
    # Handle non-zero exit here
    print(f"Command failed with {result.exit_code}")
```

1. `check=False` keeps exceptions off; use `failure`/`exit_code` to branch.

## Catch exceptions with strict mode

```python
from comrun import CommandError, CommandRunner

runner = CommandRunner(check=True)

try:
    runner("exit 1")  # (1)!
except CommandError as err:
    print(f"Command failed: {err.exit_code}")
    # Access captured output if needed: err.result.stdout / stderr / output
```

1. `check=True` raises `CommandError` on non-zero exit.

## Add an asyncio timeout

```python
import asyncio
from comrun import CommandRunner

runner = CommandRunner()

async def main():
    try:
        result = await asyncio.wait_for(
            runner.run_async("sleep 5"),  # (1)!
            timeout=2.0,                  # (2)!
        )
        print(result.exit_code)
    except asyncio.TimeoutError:
        print("Timed out")

asyncio.run(main())
```

1. `run_async` executes `run` in a worker thread (same semantics as sync).
2. `asyncio.wait_for` enforces the timeout; on timeout, the process is not auto-killed—consider an external timeout wrapper if you need cancellation.
