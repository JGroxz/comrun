# Reference

This section provides detailed information about the main types and behaviors in comrun.

## CommandRunner

| Option | Default | Description |
| --- | --- | --- |
| `cwd` | `None` | Working directory for the subprocess. |
| `env` | `None` | Environment overrides. If set, replaces the env; merge with `os.environ` to add keys. |
| `quiet` | `False` | Suppress live output (still captured). |
| `check` | `False` | Raise `CommandError` on non-zero exit. |
| `wsl` | `True` (Windows) | Prefix with `wsl` on Windows; ignored on POSIX. |
| `encoding` | `locale.getpreferredencoding(False)` | Decoding for stdout/stderr. |
| `on_line` | Rich printer | Hook for each line `(line, stream, ctx)`. Skipped when `quiet=True`. |
| `on_start` | `None` | Hook before launch `(ctx)`. |
| `on_finish` | `None` | Hook after completion `(result, ctx)`. |

### Methods

- `run(command, **options) -> CommandResult`: Executes synchronously. Strings are split with `shlex.split`; lists bypass splitting. Shell is always `False`.
- `__call__(...)`: Alias for `run`.
- `run_async(command, **options) -> CommandResult`: Runs `run` in a worker thread via `asyncio.to_thread` (same semantics as `run`).

### Hooks and context

- `on_line(line: str, stream: Literal["stdout", "stderr"], ctx: CommandContext)`: Called from reader threads; avoid blocking.
- `on_start(ctx: CommandContext)`: Called just before starting the process.
- `on_finish(result: CommandResult, ctx: CommandContext)`: Called after the process completes.
- `CommandContext` fields: `command`, `cwd`, `env`, `quiet`, `check`, `wsl`, `encoding`.

## CommandResult

| Field | Type | Notes |
| --- | --- | --- |
| `command` | `str` | Command string that was executed. |
| `exit_code` | `int` | Raw process exit code. |
| `success` | `bool` | `True` when `exit_code == 0`. |
| `failure` | `bool` | `True` when `exit_code != 0`. |
| `stdout` | `CommandOutput` | Captured stdout. |
| `stderr` | `CommandOutput` | Captured stderr. |
| `output` | `CommandOutput` | Stdout and stderr merged chronologically. |

`CommandOutput` properties:

- `lines`: tuple of lines
- `text`: joined lines as a single string (also used by `str(output)`)
- `stripped`: `text` without leading/trailing whitespace and newlines
- `value`: same as `stripped`, but returns `None` if empty

## CommandError

Raised when `check=True` and the command exits non-zero.

- `command` / `cmd`: the command string
- `result`: the `CommandResult`
- `exit_code`: the process exit code

## Execution details

- Quoting: prefer argv lists (`["git", "status"]`) to avoid shell quoting. Strings are split with `shlex.split`.
- Shell built-ins: comrun uses `shell=False`; on Windows with `wsl=False`, run built-ins via `["cmd", "/c", "dir"]` (see Cookbook).
- WSL: on Windows, `wsl=True` prefixes the command with `wsl ...`.
- Output: stdout/stderr are streamed via `on_line` (unless `quiet`) and buffered in memory; for huge output, process lines in `on_line` to avoid large buffers.
- Truthiness: `CommandResult` is truthy on success; `check=True` raises `CommandError` on non-zero exit.
