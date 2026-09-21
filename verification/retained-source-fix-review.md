# Retained-source admission: local review

Upstream issue: [#463](https://github.com/NVIDIA-dev/literate-ai/issues/463).
The issue initially filed against the checkout's GitLab remote was closed as
misplaced, with a pointer to the operator-confirmed GitHub upstream.
The operator initially authorized local preparation only, then explicitly
authorized publication. Published for review as draft
[PR #464](https://github.com/NVIDIA-dev/literate-ai/pull/464), commit
`84a1bc55bf132188fb62d721484976029680b6fd`, directly atop GitHub main
`0e49b4fd6c5eae08d8105698760a36482c479c3c`. The twelve earlier local
Python-wheel commits are excluded. No merge or installation was performed.

The proposed changes are in `parents/literate-ai`, based on
`0449e10c3a487ae21c4f606d69ee416dd853056f`, on the existing local repair branch.
That preparation checkout is preserved; the isolated publication was constructed
without switching its branch or disturbing its running regression tests.
The fix has not been installed or rebound into this project.
The application source, existing Component specifications, dependency locks,
global Litai installation and current application receipt are unchanged.

## Proposed behavior

- A read-only `rebuild --retained-source SOURCE --retained-source-plan` review
  binds the exact tree, Component lock, project authority and target.
- Execution separately requires the exact review identity and host-execution
  acknowledgement. The existing Standard lifecycle performs admission and receipt
  issuance; neither the review nor a source snapshot grants acceptance.
- Source-directory bytes are preserved inside the normal `source/` envelope.
  Current source SBOM and test metadata are required; stale metadata is rejected.
- Provenance and scheduling explicitly distinguish retained input from model
  generation. Retained cache entries cannot use ordinary model-generation keys.
- Retained runs exclude old source/checkpoint replay. Ordinary rebuilds reject
  retained checkpoints before materialization.
- The initial path is local, single-Component, UTF-8 source only, without separately
  materialized binary assets. Existing build, dependency, payload, resolved SBOM,
  independent acceptance, packaging and cleanup gates are not waived.

## Evidence

The focused 62-test source, wire, checkpoint, cache and rebuild-adapter set passes.
Four additional CLI review/authorization and lifecycle acceptance tests pass.
Repository-wide Ruff lint and formatting checks pass (1,097 Python files checked
for formatting). `git diff --check` passes.

The isolated upstream export ran 65 focused tests: 64 passed, with one CLI
initialization error (`standard_binding.distribution_payload_invalid`) because
the archive lacked a bounded installed-distribution inventory. Ruff lint and
formatting passed (1,078 files). This is partial integration evidence, not a
passing full suite. The draft retains the upstream documentation/driver review
pins, which must be reviewed for this integration before readiness.

An initial full `make python-check` correctly failed its source-stability check
because implementation edits overlapped self-hosting replication. It is not
passing evidence. A second frozen-tree run completed 2,818 tests with one failure
and 25 skips: the documentation-authority review marker was stale. After reviewing
the documentation and recording its current authority through the supported CLI,
the failed canonical-project test passes. The checkpointed framework run ended
with a stale lifecycle-driver identity in the version-authority test; it is not
passing full-suite evidence. The publication branch subsequently recorded reviewed
documentation authority through the supported CLI in commit `0cb23378`. Its
focused canonical-project test passes in 3.090 seconds; hosted CI is rerunning.
The lifecycle-driver pin remains unchanged pending explicit approval.

Hosted run `35170870291` now confirms the same boundary on the PR's tested merge
tree: Ubuntu/Python 3.14 ran 4,921 tests in 3,169.074 seconds with one failure and
30 skips; the failure is the lifecycle-driver identity check. Windows shard three
reports 2,267 passes, 57 skips and the same one identity failure in 2,470.51
seconds. The other Windows shards and Linux/macOS matrix siblings were cancelled,
not passing results. Windows lint/OpenSpec/wheel was still running at inspection.
Do not copy the merge-tree's computed driver hash into a different local tree;
review and compute the identity separately for each intended integration.

A further read-only review suspected a missing exception-message attribute.
New regression coverage disproves that suspicion: both the exception interface
and the CLI's late adapter-failure translation already work. No production code
changed. The expanded retained-source/CLI suite passes all 40 tests in 88.297
seconds; changed-test Ruff lint and formatting pass. These test-only additions
are local and are not yet part of PR #464's published head.

Before the subsequent operator approval, the parent lifecycle-driver review gate
reported a stale pin, as expected after TCB edits. It was not advanced without
review. The local qualification below supersedes that blocker; application
admission and release readiness remain unclaimed.

## Next boundary

The operator subsequently approved local driver review, supported pin recording
and qualification of a new project-local build, explicitly excluding application
rebind, global installation, merge and release. The reviewed local TCB computes
`sha256:75f82723a21237d8c88254e41fb62bab770cfac1363c6eae86956462c1c4a434`,
replacing the prior `sha256:59c56e3bb7ced25291a1944f8f8f8f8f42cc39926e7c2b20a09ea80d06b8898bbc`
only via `make driver-review-record`. The eleven tracked TCB diffs and new
`adapters/retained_source.py` were reviewed, including CLI authorization and
local-only restrictions, bounded UTF-8 input capture, lock/project/target binding,
fresh-source execution, retained wire provenance and cache separation. Existing
classification, metadata, dependency, build and independent acceptance gates
remain required. The helper lists tracked changes only; the new reader was
reviewed explicitly rather than relying solely on that listing. No additional
production change was required. Supported pin recording and documentation review
are complete in local commit `051852ad94e3ed6ce4ba3c13de44993ed949d6bf`.

The fresh Make-managed Python gate passes: 5,131 tests in 4,890.786 seconds,
34 skips, exit 0. This run started from test one on the frozen local revision;
the earlier interrupted pre-commit attempt is not passing evidence. The
installed-wheel gate also passes and retains the exact tested wheel, verified
again after installation into a separate project-local CLI. Lint, formatting,
layout, OpenSpec, documentation and driver-review gates pass. Exact wheel and
installed-distribution identities, paths and log hashes are recorded in
`retained-driver-qualification.json`. These are local qualification results,
not new upstream CI, native application admission or release evidence.

The local review and build-qualification step is complete. Obtain explicit
authorization for the application lifecycle rebind, review the supported command's
exact plan, and only then apply it. Subsequently prepare a current, explicitly
reviewed application snapshot and run its full native lifecycle. Existing
development test results do not replace that application admission. The active
application binding, global installation and published PR head remain unchanged.
At the final read-only check, GitHub reports that the operator separately merged
PR #464 at `2026-09-17T08:10:21Z`, producing
`26c8b22fa93af663905142d87769bea8ee18b839`. This task did not perform that merge
or pull it into the preparation checkout. The qualified wheel still binds local
revision `051852ad`; the upstream merge is not substituted as its provenance.
