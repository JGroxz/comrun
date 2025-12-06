# _>\__ comrun

**comrun** (shorthand for **com**mand **run**ner) is a configurable wrapper for [subprocess.Popen](https://docs.python.org/3/library/subprocess.html#popen-constructor), focused on making it easy to run external commands from Python scripts.

## Features

- Simple [runner interface](usage_general.md#running-a-command) to execute commands.
- [Configure and reuse runners](usage_general.md#configuration) to minimize boilerplate when running multiple commands.
- [Access captured stdout/stderr and exit code](usage_general.md#reading-results) for further processing.
- Use [output hooks](usage_advanced.md#live-output-hooks) to handle command output line-by-line as it arrives.

## Installation

Install using your preferred package manager:

=== "uv"
    ```bash
    uv add comrun
    ```
=== "poetry"
    ```bash
    poetry add comrun
    ```
=== "pip"
    ```bash
    pip install comrun
    ```

## Getting started

Explore the docs to learn how to use comrun:

- Run your first command and read results: [Usage → General](usage_general.md)
- Stream output with custom hooks: [Usage → Advanced](usage_advanced.md#live-output-hooks)
- Examples of runner configurations: [Usage → Cookbook](cookbook.md)
- Return types and behaviors: [Reference](reference.md)
- See [Alternatives](alternatives.md) to compare with other command-running libraries.
