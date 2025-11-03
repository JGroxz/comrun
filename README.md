# _\>__ comrun

**comrun** (shorthand for **command runner**) is a simplified and configurable wrapper for
Python's [`subprocess.Popen`](https://docs.python.org/3.11/library/subprocess.html#popen-constructor), focused on making
it easy to run external commands from Python scripts.

## Features

- Easy-to-use interface for executing commands directly.
- Captures command output and exit code for further processing.
- Simplifies error handling and logging of external commands.

## Installation

Install **comrun** using `poetry`:

```bash
poetry add comrun
```

## Usage

Just create a `CommandRunner` instance and call it with the command you want to run:

```python
from comrun import CommandRunner

comrun = CommandRunner()

# Run your command – instance is callable
result = comrun('echo "The cake is a lie."')

# (prints "The cake is a lie." to the console)
```

The same comrun instance can be reused indefinitely to call other commands.

### Exit status

Calling `CommandRunner` returns a `CommandResult` object, which contains exit code of the command:

```python
if result.success:  # <- Shorthand for result.exit_code == 0
    print(f"Command succeeded with exit code 0")

if result.failure:  # <- Shorthand for result.exit_code != 0
    print(f"Command failed with exit code {result.exit_code}")
```

You can also check for success just by using the `CommandResult` object as a boolean (it is truthy only if the command
was successful):

```python
if result:
    print(f"Command succeeded with exit code 0")
else:
    print(f"Command failed with exit code {result.exit_code}")
```

### Output

By default, **comrun** prints the command's output to the console as it appears. You can disable this behavior by
passing `quiet=True`:

```python
comrun('echo "Potato."')
# (prints "Potato." to the console)

comrun('echo "POTATO!"', quiet=True)
# (prints nothing, no matter how loud the command is)
```

Regardless of the `quiet` parameter, `CommandResult` always contains the command's output (both `stdout` and `stderr`):

```python
# Each output can be accessed as a single string...
print(result.stdout)

# ...or as a list of lines, depending on what you need.
for line in result.stdout.lines:
    print(line)
```

You can also access the combined output of both `stdout` and `stderr` in the correct chronological order using `output`
property:

```python
print(result.output)  # <- Prints all output lines of the command
```

## Advanced usage

### Exceptions

By default, **comrun** will quietly execute the command even if it fails and returns a non-zero exit code. If you want
to catch it as an exception instead, you can pass `check=True`:

```python
result = comrun('exit 1')
# (executed normally, result.exit_code == 1)

result = comrun('exit 1', check=True)
# (raises a CommandError because the command fails)
```

### Live output

By default, **comrun** uses rich's `Console` for printing stdout and stderr lines as they come in from the command
subprocess (unless `quiet=True` is passed). This output handling can be changed by passing a
custom `on_line` callback to the `CommandRunner`
constructor:

```python
from comrun import CommandContext, CommandRunner


def print_line_with_stream_name(line: str, stream: str, ctx: CommandContext):
    # Note: line argument does not have a trailing newline character

    print(f"{stream.upper()} | {ctx.command} | {line}")


comrun = CommandRunner(on_line=print_line_with_stream_name)

comrun('echo "For science."')

# (prints "STDOUT | For science." to the console)
```
