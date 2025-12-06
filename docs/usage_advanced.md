# Advanced

Advanced techniques when using comrun.

## Live output hooks

comrun allows you to hook into the command's lifecycle with 3 callbacks:

- `on_start`
- `on_line`
- `on_finish`

## Start / Finish

Lifecycle hooks let you log around execution:

```python
def on_start(ctx: CommandContext):
    print(f"Running: {ctx.command}")

def on_finish(result: CommandResult, ctx: CommandContext):
    print(f"Done ({result.exit_code})")

runner = CommandRunner(on_start=on_start, on_finish=on_finish)
runner("ls")
```

This can be useful when integrating comrun into larger scripts or applications where you want to track command execution.

## Lines

By default, comrun uses [Rich](https://github.com/Textualize/rich)'s [Console](https://rich.readthedocs.io/en/latest/console.html) for printing stdout and stderr lines as they come in from the command subprocess (unless `quiet=True` is passed). This output handling can be changed by passing a custom `on_line` callback to the runner:

```python
from comrun import CommandContext, CommandRunner, StreamName

def print_line_with_stream_name(
    line: str, 
    stream: StreamName, # (1)!
    ctx: CommandContext
):
    print(f"{stream.upper()} | {line}") # (2)!

runner = CommandRunner(on_line=print_line_with_stream_name)

runner('echo "For science!"') # (3)!
```

1. !!! info "`StreamName` is a type alias for `#!python Literal["stdout", "stderr"]`"
       Use it to distinguish which stream the line came from.
2. !!! info "`line` argument does not have a trailing newline character, so we can just print it directly"
3. Prints the following:
    ```text {.no-copy}
    STDOUT | For science!
    ```
   
This is useful when you want to process or log command output in a custom way, such as prefixing lines with timestamps, writing to a file, or filtering certain messages.

!!! warning "Things to be aware of when using `on_line`:"
    - The `on_line` callback runs on reader threads for stdout and stderr; keep it non-blocking and thread-safe.
    - When `quiet=True` is set on the runner or the individual `.run()` call, `on_line` is skipped.
