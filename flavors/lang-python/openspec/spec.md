# Python implementation Flavor

### Requirement: Portable Python implementation

When `implementation.language-ecosystem=python` is selected, generate a Python 3.11+
standard-library application with `source/main.py` as its entrypoint. The module SHALL
expose `main(payload)`, return a JSON-serializable result, require no standard input when
called as `main(*arguments)`, and avoid platform-specific dependencies unless the
selected OS Flavor requires them. Its executable entrypoint SHALL accept one UTF-8 JSON
array containing the declared positional arguments in `argv[1]`, invoke
`main(*arguments)`, and write only the returned JSON value to standard output.

#### Scenario: Python application executes

- **WHEN** the generated source is compiled with the selected host Python toolchain
- **THEN** the checked-hash bytecode entrypoint runs without generated source being present on its import path
