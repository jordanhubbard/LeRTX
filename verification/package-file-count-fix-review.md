# Package-count local fix review

Issue: [NVIDIA-dev/literate-ai #480](https://github.com/NVIDIA-dev/literate-ai/issues/480).
Prepared in the existing project-local parent checkout, based on qualified
revision `aa3a58689fa5b1c585dd532939ef1869ab6bea20`. The diff is local and
uncommitted; no branch switch, push, merge, global installation or LeRTX rebind
was performed.

## Scope and review

`PackageResult` now applies the existing 16,384 logical-file bound to directory,
runtime-bundle and standalone-executable artifact lists. Archive, installer and
container-image outer outputs retain their 256-entry bound. The v2 JSON schema
matches those package-kind-dependent limits. Documentation and the parent queue
record this distinction; no production code outside the contract was changed.

Canonical order, duplicate detection, file membership, target and digest checks,
and sealed Python runtime validation remain unchanged. Resource files are not
truncated or bundled into an unverified escape path. The larger lifecycle fixture
adds 257 resource files to its wheel before RECORD/hash/lock generation and
installation, so the relocation test exercises real dependency custody rather
than adding files after sealing.

## Passing local evidence

All runs use the parent Make-managed `qualify-473` environment:

| Gate | Result |
| --- | --- |
| `test_package_adapters.py` | 28 tests, 12.585 seconds |
| `test_package_release_contracts.py` | 19 tests, 0.144 seconds |
| `test_schema_catalog.py` | 20 tests, 0.249 seconds |
| `test_standard_python_lifecycle.py` | 11 tests, 41.028 seconds; pinned offline installer supplied |
| `make lint format-check repository-layout-check` | Pass; 1,250 formatted Python files |
| `git diff --check` | Pass |

The adapter tests exercise all three directory shapes at 256, 257, 11,117 and
16,384 entries, serialization round trips, rejection at 16,385, outer-output
limits, altered bytes and missing/extra logical members. Draft 2020-12 validation
checks the conditional schema at the 256/257 boundary; the repository catalog
validator covers the large fixtures. This distinction matters because the simple
catalog test helper does not implement conditional schema evaluation.

Two initial test-authoring failures were corrected: membership rejection must
mutate the logical closure, not only the separate output list; conditional schema
tests require the full JSON Schema validator. No production verifier was loosened
to satisfy those tests. A formatting failure was corrected before the passing
quality run.

## Remaining adoption gates

`make driver-review` deliberately reports stale: only the package contract in
the declared trusted computing base changed. The preserved pin is
`sha256:ca71879981eb2b2d62d2706c481a00ab24fbafb7e5d037828d5cd81b3f4a60be`;
the candidate computes
`sha256:302489e5044d3b6eb2b67008d736e5165dec6b2dc034615c186c6759a54631d0`.
No review pin was recorded. Full-suite, installed-wheel, hosted/platform and real
downstream admission qualification are not claimed for this diff.

The checkout's legacy GitLab tracker routing was reported; filing/search used
the user-designated GitHub repository explicitly. Start/end peer-work surveys
ran, and historical branches/worktrees were preserved. CodeGraph reported no
usable index, so ordinary source inspection was used. Local worker-health checks
showed ample disk space; no cleanup or remote job was needed.

Next: approve qualification/landing scope, review and record the driver pin through
the supported command, qualify exact wheel bytes, and only then review a new
LeRTX rebind and rerun admission. The renderer-startup failure remains separate.
