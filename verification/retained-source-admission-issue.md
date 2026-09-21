# Standard lifecycle: qualify retained source under an existing Component

## Problem

An operator may explicitly authorize retaining and repairing generated source
without relaxing its existing Component specifications or acceptance gates.
The resulting tree is neither an untouched generation nor already-admitted
source. It needs an honest provenance category and verifier-owned admission.

The inspected CLI exposes `rebuild --from-accepted-source`, which requires
previously admitted membership, and `spec qualify`, which performs clean
generation. `spec merge SOURCE --component EXISTING` fails closed with
`project.spec_merge_component_exists`. Planning a new Component works, but does
not provide admission under the existing Component's exact behavior contract.

These observations do not prove no lower-level path exists. Please identify a
supported existing-Component path, or provide a reviewed explicit transition.

## Required behavior

- Require explicit operator authorization for the exact retained tree; never
  imply authorization from a matching filename or a test pass.
- Preserve the existing Component, specifications, target selections, dependency
  locks, execution policy and independent acceptance requirements.
- Capture an immutable source snapshot, distinguish edited retained source from
  model-generated provenance, and bind all evidence to its exact content identity.
- Re-run classification, dependency and payload verification, source/resolved
  SBOM validation, target build/tests, independent acceptance and cleanup.
- Emit admission and receipts only through verifier-owned code after all gates
  pass. Reject changed input bytes, stale authority, wrong-target dependencies,
  incomplete evidence and failed acceptance.
- Do not promote source to fungible regenerative authority merely because a
  retained-source run passed.

## Portable regression fixture

Use a tiny generated Python Component with one behavior requirement and an
independent acceptance case. Retain an authorized source correction, then prove
that qualification preserves its Component identity and exact source bytes.
Negative fixtures should mutate the tree mid-run, change the locked requirement,
break acceptance, alter a dependency hash and present an obsolete target. No GPU,
private workspace, credentials or external service is required for this fixture.

The requested change is an explicit retained-source qualification path, not a
waiver of existing generation, dependency, execution or acceptance policy.
