# Windows isolated wheel target probe blocker

Observed with the pinned Literate AI 1.2.0 distribution on Windows and CPython
3.11.9. This is framework-owned; the installed distribution remains unchanged.

`install_python_wheels` constructs an environment containing PATH, SystemRoot,
WINDIR, TEMP, TMP, LANG and LC_ALL, then calls `observe_python_wheel_target`.
The selected interpreter's `platform.machine()` returns an empty string in that
environment. The ordinary target probe returns AMD64. Strict wheel-lock parsing
then rejects the isolated probe with `dependencies.python-lock-invalid: Python
lock target fields must be nonempty bounded strings`. A current lifecycle receipt
cannot be produced through this installer on this host.

Minimal reproducer (no packages, hardware, paths or credentials):

```python
import os, subprocess, sys

probe = 'import platform; print(repr(platform.machine()))'
keys = ('PATH', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'LANG', 'LC_ALL')
isolated = {key: os.environ[key] for key in keys if key in os.environ}
for environment in (os.environ, isolated):
    subprocess.run([sys.executable, '-I', '-S', '-c', probe],
                   env=environment, check=True)
```

Observed output: `'AMD64'`, then `''`. Qualify the framework's Windows target
observation under its own controlled installer environment, retaining strict
target validation and package custody. Do not synthesize a passing receipt or
change the pinned distribution locally.

The repair is tracked by [framework issue #63](https://github.com/jordanhubbard/literate-ai/issues/63)
and merged in [PR #64](https://github.com/jordanhubbard/literate-ai/pull/64).
Fourteen real installer/fixture tests and LeRTX's complete Windows wheel-set
installation pass with the repaired source: 11,867 installed files, revalidation
and cleanup verified. The released 1.2.0 wheel remains unchanged; a qualified
replacement distribution and current downstream receipt are still required.
