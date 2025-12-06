# _\>__ comrun

**comrun** (shorthand for **com**mand **run**ner) is a simple, configurable wrapper for Python's [subprocess.Popen](https://docs.python.org/3/library/subprocess.html#popen-constructor), focused on making it easy to run external commands from Python scripts.

## Installation

Add to your project with [uv](https://docs.astral.sh/uv/):

```bash
uv add comrun
```

## Usage

Just create a `CommandRunner` instance and call it with the command you want to run:

```python
from comrun import CommandRunner

comrun = CommandRunner()

# Run your command – instance is callable
result = runner('echo "The cake is a lie."')

# (prints "The cake is a lie." to the console)
```

The same comrun instance can be reused indefinitely to call other commands.

Full documentation [can be found here](https://jgroxz.github.io/comrun/).
