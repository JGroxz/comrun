# General

The core of comrun is a `CommandRunner` class. It's how you run commands and get results. This section covers the basics of using it.

## Running a command

Just create a `CommandRunner` instance and call it with the command you want to run:

```python
from comrun import CommandRunner

runner = CommandRunner()

runner.run('echo "The cake is a lie."')  # (1)!
```

1. Prints to stdout:
    ```text {.no-copy}
    The cake is a lie.
    ```

You can also run commands asynchronously:

```python
async def some_coroutine():
    await runner.run_async('echo "This cake is an async lie."')  # (1)!
```

1. Prints to stdout:
    ```text {.no-copy}
    This cake is an async lie.
    ```

The same runner instance can be reused indefinitely to call other commands. This allows you to invoke multiple commands using the same base configuration, and override individual options on each run as needed (more on this in [Configuration](#configuration) section).

??? example "Extra `CommandRunner` trivia"
    - `CommandRunner` instances are callable: `__call__` forwards to `.run()`. So you can do `runner("ls -la")` instead of `runner.run("ls -la")`, for example.
    - Runner accepts commands both as a string (`#!python "git status"`) and as an argv (`#!python ["git", "status"]`). Strings are split with [`shlex.split()`](https://docs.python.org/3/library/shlex.html#shlex.split) internally.

## Reading results

Each run returns a `CommandResult` instance with details about the execution:

```python
result = runner.run("ls")  # (1)!
```

1. `result` is a `CommandResult` instance with details about this run.

### Exit status

There are several ways to check how the command exited:

```python
print(result.exit_code)  # (1)!
print(result.success)  # (2)!
print(result.failure)  # (3)!
```

1. Raw exit code (0 means success).
2. `True` when `#!python exit_code == 0`.
3. `True` when `#!python exit_code != 0`.

`CommandResult` instance is truthy upon success, so you can use it in conditionals:

```python
if result:
    print("Command succeeded!")
else:
    print("Command failed :(")
```

### Captured output

Output of the command is captured in  `CommandOutput` objects. Result has three properties of this type:

```python
print(result.stdout)  # (1)!
print(result.stderr)  # (2)!
print(result.output)  # (3)!
```

1. Stdout output.
2. Stderr output.
3. Output of stdout + stderr in chronological order.

`CommandOutput` objects allow you to access their content in several ways:

1. `lines`: A tuple of output lines, each without trailing whitespaces/newlines.
    ```python
    for line in result.stdout.lines:
        print(line)
    ```
    
    !!! tip "If you want to process lines right as they come, look into [live output hooks](usage_advanced.md#live-output-hooks)."

2. `text`: Full output as a single string.
    ```python
    print(result.stdout.text)
    ```

    ??? tip "Converting `CommandOutput` to a `#!python str` is the same as accessing its `text` property"
        ```python {.no-copy}
        str(output) == output.text
        ```
        So to print the full captured stdout, you can simply `#!python print(result.stdout)`.

3. `stripped`: Full output as a single string, but without leading and trailing whitespaces/newlines.
    ```python
    print(result.stdout.stripped)
    ```
4. `value`: Same as `stripped`, but is `None` if the output is empty.
    ```python
    if result.stdout.value is not None:
        print("Command produced some output!")
    ```

These options keep command-output handling short and readable.

## Configuration

The strength of comrun is in the ability to create pre-configured runners. There are 3 ways to configure a `CommandRunner`:

1. Via constructor arguments:
    ```python
    base_runner = CommandRunner(quiet=True, check=True) # (1)!
    ```

    1. This runner will be [silent](#silencing-output) and will [raise exceptions on failures](#raising-on-failures).
   
2. By modifying an existing runner via `.with_options()`:
    ```python
    loud_runner = base_runner.with_options(quiet=False) # (1)!
    ```
    
    1. This runner will now print its output (`#!python quiet=False`), but keeps `check=True` from `base_runner`.

    !!! info "`.with_options()` always creates a new `CommandRunner` instance, so the original remains unchanged."

3. By passing options to individual `.run()` calls:
    ```python
    loud_runner.run("echo 'Hello, World!'", check=False)  # (1)!
    ```
    
    1. This specific run will not raise on failure (`#!python check=False`), even though `loud_runner` has `check=True`.
   
         It still prints output like `loud_runner` is configured to do.

    !!! tip "This, of course, works the same with async calls via `.run_async()`."

These methods can be combined as needed to create runners that fit your use case, all while minimizing repeated boilerplate when calling commands.

Available configuration options are listed below.

### Working directory (`cwd`)

Working directory for the command is set with `cwd`:

```python
runner = CommandRunner(cwd="/path/to/dir")  # (1)!
```

1. Commands run via this runner will execute with `/path/to/dir` as their working directory.

### Environment variables (`env`)

You can override environment variables for the command with `env`:

```python
runner = CommandRunner(env={"MY_VAR": "value"})  # (1)!
```

1. Commands run via this runner will have `MY_VAR` set to `"value"` in their environment.

!!! info "Environment variables set via `env` replace the entire environment for the command." 
    To add variables while keeping existing ones, merge with [`os.environ`](https://docs.python.org/3/library/os.html#os.environ):
    ```python
    CommandRunner(env={**os.environ, "MY_VAR": "value"})
    ```

### Silencing output (`quiet`)

By default, comrun prints the command's output to the console as it appears. You can disable this behavior by passing `quiet=True`:

```python
runner('echo "Potato."')  # (1)!
runner('echo "POTATO!"', quiet=True)  # (2)!
```

1. Prints `Potato.` to the console.
2. Prints nothing, no matter how loud the command is. `POTATO!` is still captured and available in `result.stdout`.

### Raising on failures (`check`)

By default, comrun will quietly execute the command even if it fails and returns a non-zero exit code. If you want to catch it as an exception instead, you can pass `check=True`:

```python
result = runner("exit 1")  # (1)!

try:
    runner("exit 1", check=True)  # (2)!
except CommandError as exc:
    print(exc)
```

1. Non-zero exits set `result.failure` to True.
2. With `check=True`, non-zero exits raise `CommandError`.

!!! tip "Read more about `CommandError` in the [Reference](reference.md#commanderror) section."

### Using WSL on Windows (`wsl`)

On Windows, comrun can automatically prefix commands with `wsl` for you to run them inside the [Windows Subsystem for Linux](https://learn.microsoft.com/en-us/windows/wsl/about). This behavior is controlled with the `wsl` option (default: `True` on Windows, ignored on POSIX):

```python
windows_runner = CommandRunner(wsl=False)  # (1)!
```

1. Commands run via this runner will execute with the native Windows shell instead of WSL (when on Windows).

### Encoding (`encoding`)

By default, comrun decodes command output using the system's preferred encoding. You can override this with the `encoding` option:

```python
runner = CommandRunner(encoding="utf-8")  # (1)!
```

1. Commands run via this runner will decode output using UTF-8.

### Others

You can find more configuration options in the [Advanced usage](usage_advanced.md) and [Reference](reference.md) sections.
