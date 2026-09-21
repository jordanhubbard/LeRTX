# Merged directory-package bound fix

## Latest checkpoint — 2026-09-20

Exact-revision installed-wheel qualification completed successfully. Manifest
`parents/literate-ai/_build/ci-wheels/run-xivvuz4g/manifest.json` binds revision
`f99e4cb2db980c36611747932e083f1baa194602` and wheel SHA256
`5064c5d2df52cd0465dcb559d038e0610226e669934a2f1dbfbe5dc3f22174d0`
(3,040,533 bytes). The merged-revision CI run below completed with a failure in
Windows / Python 3.12 / tests (2 of 3). Diagnose that failure before adoption;
no LeRTX rebind or acceptance is claimed. The remainder is the earlier review
checkpoint and retains its then-pending statuses as history.

The operator authorized conflict resolution, landing, qualification and continued
application recovery without repeated routine approval requests.

Upstream [PR #482](https://github.com/NVIDIA-dev/literate-ai/pull/482) is merged
as `f99e4cb2db980c36611747932e083f1baa194602`. During local qualification, another
upstream session resolved and merged it. No competing branch was pushed.

## Preservation and review

The previous seven-file local proposal is preserved in Git stash
`360a3229fe66ffaa4702d49575cb8a7da58186a6` in the project-local parent checkout.
Local integration commit `4b3832c4` is retained on `integrate/482-lertx`.
The checkout is now clean on `qualify/482-merged`, at the upstream merge.

Conflicts affected only the changelog, lifecycle-driver identity and documentation
review marker. Both changelog entries were retained. Review against main found
only the intended package-kind-dependent artifact bound and matching schema;
review against the PR found the main branch's separately tested bounded JavaScript
generation retry. Supported commands regenerated the combined review identities.
The upstream merged tree differs from the local integration only by one blank
line in the changelog; production code, schema, tests and review identities match.

Directory-shaped outputs allow up to 16,384 artifacts. Archive, installer and
container-image outputs retain the 256 limit. Membership, ordering, uniqueness,
digest and sealed Python dependency verification remain unchanged.

## Exact merged-revision evidence

- Focused package, contract, schema, Python lifecycle and coding-CLI regression:
  207 tests in 56.288 seconds, passing with two skips.
- Driver and documentation review: current.
- Lint, formatting (1,250 files) and repository layout: pass.
- Merged tree: `f50b8c0e2c65622a1ce9a8b9ba8c3f03e5ac385c`.
- Driver identity: `sha256:23dc8d0b17248731d720b6c3ce24b795b0fb1080eb3d0c97fb8aafa30fa277a5`.
- Documentation identity: `sha256:f03da61a2a33db6e734ecf4d72f86afebba86a72b0d15b6823cd0e370e047883`.

All 19 checks on the original PR head had passed. That result is not qualification
of the new merged tree. [Merged-revision CI](https://github.com/NVIDIA-dev/literate-ai/actions/runs/35478113877)
is still pending at this checkpoint. Exact merged-revision installed-wheel
qualification is running; its output is in parent `_build/pr482-merged-wheel-check.log`.
Focused and quality logs are `_build/pr482-merged-focused.log` and
`_build/pr482-merged-quality.log` in that checkout.

The earlier local integration's broad test and wheel runs were deliberately
stopped when the upstream merge appeared. Neither interrupted run counts as
passing qualification. The initial wheel attempt correctly refused the uncommitted
merge; subsequent attempts use a clean exact Git revision.

## Remaining application gates

Require completed current-revision CI and installed-wheel qualification, then
review/apply a project-local Standard rebind and re-prepare the current renderer-fixed
source with its exact recipe, wheel lock and SBOM. Retry retained-source admission
and native/package acceptance without relaxing validators or frame deadlines.
No global installation, new application binding, admission receipt, physical
actuation or installed-product acceptance is claimed here.

The historical GitLab origin remains unchanged; GitHub is the operator-designated
upstream. Start peer-work survey ran against the configured origin, and its empty
review result was not substituted for the explicit GitHub PR/CI inspection.
