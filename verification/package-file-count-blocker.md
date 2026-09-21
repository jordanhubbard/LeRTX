# Directory runtime bundles exceed the package artifact limit

Status: filed as [upstream #480](https://github.com/NVIDIA-dev/literate-ai/issues/480).
The operator authorized a reviewed local fix, without merge, publication or rebind.
The local proposal and 78 passing focused tests are documented in
`package-file-count-fix-review.md`; full qualification and adoption remain pending.

## Actual application failure

After qualified adoption of merged revision
`aa3a58689fa5b1c585dd532939ef1869ab6bea20`, retained-source admission builds
the pinned native Python dependencies and seals the original artifact, then exits
2 with:

```text
cli.invalid_input: PackageResult.artifacts: must contain at most 256 values
```

The built artifact contains 11,172 regular files, including 56 files under its
single exported application directory. The remaining 11,116 runtime/resource
files plus that directory export require 11,117 logical package entries.
The retained source remains tree
`sha256:272e1af07312461fb27fbdc7a2abb8bf72a2c9316c829efb888f89f514e29304`.
Fresh authorization is
`sha256:3dfa324f2f34c533fd15db238bdf86bae28c6aa6864e326fb4c5748035a9205a`.
No passing candidate or package is produced; the prior receipt remains stale.

## Cause and boundary reproduction

`DirectoryPackageAdapter.package` passes the same full logical file sequence as
both `files` and `artifacts` to `package_result_for`. `PackageResult` allows up
to 16,384 logical files but explicitly caps artifacts at 256. Carrying real
installed Python dependency files into a runtime bundle exposes this mismatch.

The existing `PackageAdapterTests` fixture reproduces the boundary without
native SDKs: extend a `RUNTIME_BUNDLE` plan with uniquely named, digest-bound
resource inputs and run `DirectoryPackageAdapter.package` with the fixture's
blob reader. Locally observed at the qualified revision:

```json
{"inputs":256,"artifacts":256,"status":"pass"}
{"inputs":257,"status":"rejected","error":"PackageResult.artifacts: must contain at most 256 values"}
```

This is separate from the missing-runtime/seal defect fixed by PR #474. A fix
needs reviewed agreement between directory-package semantics, contract/schema
bounds, verification, and regression tests. Do not truncate the file closure,
omit dependency custody, or raise a bound only in an installed environment.

## Preserved boundaries

The qualified parent checkout and wheel are unmodified. No additional driver
pin has been recorded, no test assertion relaxed, and no acceptance fabricated.
Native regression against the built runtime is independent evidence and cannot
override this admission failure.
