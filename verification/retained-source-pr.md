## Summary

Refs #463.

Introduce an explicit, exact-content-authorized retained-source input to Standard
rebuild under the existing Component. Preserve source bytes and specifications,
distinguish retained provenance from generation, isolate its cache namespace, and
reject stale checkpoint replay. Existing acceptance gates remain mandatory.

This is a draft for review, not a release or approval to bypass admission. The
patch is isolated on GitHub main; earlier local Python-wheel commits are excluded.

## Verification

- Preparation base: 62 focused source/wire/cache/rebuild tests plus four additional
  CLI/acceptance tests passed. Repository lint, formatting and diff checks passed.
- Isolated upstream export: 65 focused tests ran; 64 passed and one CLI
  initialization test errored with `standard_binding.distribution_payload_invalid`
  because the archive lacks bounded installed-distribution inventory. This is not
  a passing suite. Ruff lint and formatting passed (1,078 files).
- The preparation-base full framework regression run remains in progress. Prior
  attempts exposed source-stability and documentation-review issues; neither is
  claimed as passing qualification.

## Before marking ready

- Run the exact integration through the managed full framework suite and installed
  wheel end-to-end retained admission, including independent acceptance failures.
- Review and record documentation authority and lifecycle-driver identity for this
  integration. Existing review pins were deliberately not advanced by this draft.
- Pass hosted CI. No merge, release, downstream lifecycle rebind or application
  admission is performed by publishing this PR.
