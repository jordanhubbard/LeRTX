# Directory runtime bundles reject valid file closures above 256 entries

Observed at merged revision `aa3a58689fa5b1c585dd532939ef1869ab6bea20`, after the
Python package-custody repair in #474 (integrated by #477).

## Failure

A Python application with a pinned native dependency closure builds successfully,
but Standard retained-source admission stops before independent packaged acceptance:

```text
cli.invalid_input: PackageResult.artifacts: must contain at most 256 values
```

The anonymized downstream closure requires 11,117 package entries. This is a
framework packaging blocker, independent of application behavior or GPU hardware.

## Cause

`DirectoryPackageAdapter.package` calls
`package_result_for(plan, files=files, artifacts=files)`.
`PackageResult.files` allows 16,384 entries, but `PackageResult.artifacts`
unconditionally allows only 256. The Python custody repair now correctly includes
dependency runtime resources, exposing this mismatch for directory/runtime bundles.

## Portable reproduction

Use the existing `tests.unit.test_package_adapters.PackageAdapterTests` fixture:
create a `RUNTIME_BUNDLE` plan and extend its inputs with uniquely named
`PackageInput` resources backed by one valid digest-bound blob. Run
`DirectoryPackageAdapter.package` with the fixture blob reader.

- 256 total plan inputs: passes, 256 artifacts.
- 257 total plan inputs: rejected with the error above.

No external dependency, device, credential, or native SDK is needed.

## Requested contract and acceptance

Allow directory-shaped package outputs to carry the complete bounded logical
file closure; preserve the stricter bound for outer archive/native package outputs.
Keep wire-schema and Python validation consistent. Preserve exact file membership,
target/digest binding, tamper rejection and finite limits; do not truncate resources
or bypass sealed-artifact checks.

Cover the 256/257 boundary, a representative large closure, maximum/over-limit
behavior, serialization/schema round trips, archive-output limits and mutation
rejection. Exercise the Python packaged-runtime lifecycle with more than 256 files.

Downstream recovery remains blocked pending a reviewed, qualified framework fix;
issue filing does not claim application admission or authorize publication.
