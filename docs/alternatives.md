# Alternatives

A quick look at other ways to run external commands in Python, and when they might fit better than comrun.

## Python standard library

- [`subprocess.run` / `subprocess.Popen`](https://docs.python.org/3/library/subprocess.html): battle-tested and built in, but requires boilerplate. You manage streaming, decoding, and error handling yourself. This friction is what inspired the creation of comrun.
- [`asyncio.create_subprocess_exec`](https://docs.python.org/3/library/asyncio-subprocess.html): async-friendly subprocesses. You handle reading/writing streams and timeouts.

Use these when you want zero dependencies and are fine wiring up I/O, timeouts, and logging yourself.

## Higher-level libraries

- **[Invoke](https://www.pyinvoke.org/)** / **[Fabric](https://www.fabfile.org/)**: task runners with decorators, remote execution, and SSH. Good for deployment scripts; heavier footprint than comrun.
- **[plumbum](https://plumbum.readthedocs.io/en/latest/)**: shell-like DSL with pipelines and path abstractions; nice for Unix-like scripting, more opinionated than comrun.
- **sh-style wrappers** (e.g., [`sh`](https://amoffat.github.io/sh/), [`delegator.py`](https://github.com/amitt001/delegator.py)): call executables as functions (`git.status()`), often `shell=True`; convenient, but can hide quoting concerns.

Choose these when you want richer task abstractions or DSL-like command composition.

## When to choose comrun?

You want a small, synchronous runner with:

- Live output streaming (via Rich) and captured stdout/stderr/combined output.
- Structured results and simple success/failure helpers.
- Hooks for logging/metrics without adopting a heavier task runner.
