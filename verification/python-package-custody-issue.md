# Standard Python wheel runtime is omitted from packaged independent acceptance

## Reproduction

In the local Python-wheel lifecycle integration, use the existing
`StandardPythonLifecycleTests` tiny `example` / `helper` wheel fixture. Build,
run generated tests, and execute the Component successfully. Realize its export
manifest and artifact graph, then call `create_project_package` followed by
`test_root_integration`.

Root integration fails with:

```text
Python execution differs from its sealed artifact
```

The original artifact's complete tree identity remains unchanged. This is not
an observed mutation of the original artifact.

## Diagnosis

`_build_python_target` retains the installed dependencies as `python-runtime`
and their evidence as `python-dependencies.json`, siblings of the application
export. It registers the original artifact directory's execution seal and
dependency observer.

`create_project_package` copies the application export into a new package
directory. The dependency runtime and manifest are absent from that packaged
directory. `_packaged_argv` then calls `_locked_argv` with the new directory,
which has no registered Python execution seal or dependency observer. The
current check correctly refuses to execute it.

## Required behavior

Package the entire verified runtime closure through explicit artifact/package
authority. Bind the copied dependency files, dependency evidence, application
and resolved SBOM to immutable package identities. Validate the new packaged
location before execution. Do not ignore the missing seal, point a supposedly
portable package back to the build cache, or silently rely on host-installed
packages.

## Acceptance

- Existing tiny wheel fixture passes build, generated tests, execute, packaged
  root integration and independent acceptance.
- Packaged execution succeeds without access to the original artifact root or
  provisioning wheelhouse, using only the declared interpreter and package.
- Missing/modified packaged runtime, application, dependency manifest or SBOM
  is rejected before execution.
- Linux and Windows relocation preserve the same guarantees.
- Retained-source admission and accepted-source replay receive end-to-end
  coverage, beyond Component-only build/test/launch.

Filed with explicit operator authorization as
[NVIDIA-dev/literate-ai #473](https://github.com/NVIDIA-dev/literate-ai/issues/473).
Searches for Python package runtime and sealed artifact issues found no matching
open report. The issue uses the operator-designated GitHub upstream, not the
parent checkout's legacy remote.
