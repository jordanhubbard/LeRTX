# Retained desktop admission continuation

The operator requested merge and next steps. GitHub PR #464 was already merged
as `26c8b22fa93af663905142d87769bea8ee18b839`. The separate, qualified local
build remains based on `051852ad94e3ed6ce4ba3c13de44993ed949d6bf`; its private
Python dependency changes have not been published or represented as upstream.

## Completed lifecycle rebind

The supported rebind applied the reviewed plan in
`retained-standard-rebind-plan.json`, identity
`sha256:9bcb190bd180306576991d3af4148c807896a184d29678cb371ad5d3e193a996`.
The installed distribution is
`sha256:1168298f2e2f0f2ebf34c74a2c33b6710fb0e224cffb01c048ca18dc00757d5e`
with 872 members, independently observed on both development and Linux hosts.
Policy, required receipt evidence and minimum tests are unchanged. Supported
documentation review records project authority
`sha256:6eda700d0b8c56a8b393dca341160fd2e02c305f98632aa7f87574a77558c42c`.
The global Litai installation is unchanged. The old application receipt remains
stale until actual admission succeeds.

## Exact source preparation

`prepare_retained_snapshot.py` copies application modules unchanged into a new
snapshot, updates the test manifest recipe, and declares the exact Linux wheel
lock and pre-build SBOM. No installed dependency evidence or acceptance receipt
is synthesized. The source contains 56 files: 53 unchanged, one corrected
manifest, and two new dependency declarations. All 56 hashes match
`native/linux/retained-snapshot-preparation.json`; all 30 portable manifest cases
pass on this snapshot.

Two earlier attempts were rejected before building because the metadata helper
initially used the standalone preparation recipe, then the development host's
Claude-bound Standard recipe. Linux selects Codex. The corrected helper uses
Standard's planner and node projector on the admission worker. These failures
are not acceptance evidence; no framework validator was changed.

The current Linux recipe is
`sha256:7d8264a4f5d159b3fb4a275135bff4b3aa6dab60e961de7ca0b998373378ba5c`.
The exact tree is
`sha256:272e1af07312461fb27fbdc7a2abb8bf72a2c9316c829efb888f89f514e29304`.
Its supported review authorization is
`sha256:2b4ed7c7c39215e78d716a5509046eb20d909da68ab89b764bb83b9d0c7e2a9b`.
Linux admission ran in a separate task-owned workspace, using the qualified
wheel and an isolated copy of the verified native wheelhouse. It stopped at
`standard_rebuild.independent_acceptance_failed`: `Python execution differs
from its sealed artifact`. The original artifact still matches its publication
checkpoint, `sha256:2ad489898a280824d859af901dbed1f923cfb821cc067c5c3bbd0e952a509bb1`.
This is not evidence of changed original artifact bytes.

The existing framework example/helper wheel fixture reproduces the defect:
Component tests and execution pass, the original artifact remains unchanged,
but the packaged directory lacks the dependency runtime, dependency manifest,
and registered execution seal. Packaged root integration raises the same error.
See `native/linux/package-custody-diagnostic.json` and the portable reproducer
`reproduce_python_package_custody.py`. No framework implementation or review
pin was modified to bypass the failure. The operator subsequently authorized
filing and a handoff to the active framework Codex session. The sanitized report
is now [upstream issue #473](https://github.com/NVIDIA-dev/literate-ai/issues/473);
its local copy is `python-package-custody-issue.md`.
The supported `codex queue` command accepted the blocker notification for the
active session in the framework workspace, including the issue, exact diagnosis,
portable reproducer, local qualification context and unchanged safety boundaries.
Queue acceptance confirms submission, not that the receiving agent has read or
resolved the blocker.

## Remaining boundaries

All 157 native/application tests pass in 95.255 seconds using the newly built
dependency runtime with an explicit inherited import path. An earlier diagnostic
run failed two subprocess cases because its parent-only import path was not
inherited, and its first native window exceeded the unchanged frame deadline.
The corrected-environment rerun passes, but does not prove cold-start reliability.
Both outcomes are retained in `native/linux/retained-admission-regression.json`.

Admission, native regression on the resulting artifact, package construction
and package verification remain required. Planning alone is not a package.
Windows has 2,673,975,296 bytes free on C: at this check; full installs and package
staging remain held. Physical device actuation and global installation are not
part of this continuation.
The bounded Windows cache inspection found only one 98-byte pip-cache file;
the known wheel staging directory was already cleared. Installed SDK/framework
environments and an unrelated Python process were preserved. No additional
material cleanup candidate was established in these task-owned locations.
Final local `litai verify` passes authority and all three locks; source-intelligence
and HTML gates are intentionally skipped. The receipt gate remains stale and is
not overridden. The parent checkout remains clean with its qualified implementation
unchanged; both new diagnostic/preparation helpers pass Ruff checks.
