# Changelog

## Unreleased

- Project checkpoint: consolidate all remaining framework qualification,
  application admission, Linux/Windows delivery, configuration/photo acceptance,
  robot telemetry, measured registration and deferred control work in the roadmap.
  Upstream package-count repair is merged; a failed upstream Windows CI shard
  still blocks adoption. This checkpoint is not a release or admission claim.
- Desktop startup now creates its first RTX renderer only when the scene is
  ready, avoiding an unused renderer's immediate teardown before the first frame.
  All 158 Linux tests and eight targeted Windows native/worker tests pass, plus
  three additional Linux fresh-process existing-scene launches. First-frame and
  process deadlines are unchanged; packaging/admission remains pending.
- Desktop shutdown now explicitly releases the RTX rendering system instead of
  retaining the SDK backend until process exit. The Windows mixed-order seven-test
  startup/close regression passes, and all 157 tests pass on Linux and Windows
  against the same source. Application admission and packaging are not yet
  complete. The Litai native-interface contract preserves the fix.
- Desktop startup: initialize an anonymous OpenUSD stage before RTX attachment,
  fixing the reproduced mixed-order existing-file startup timeout on Linux.
  Added ordering/failure regressions and timeout stack diagnostics. All 156 Linux
  desktop tests passed on that snapshot; later platform evidence is recorded above.
- First interactive Linux development launch verified on the real user desktop:
  RTX workspace visible and native ready. Fresh UI physics/edit/save and ordinary
  launches pass; an existing-file launch times out after another native test but
  passes alone. This reliability gap and formal admission remain open.
- Desktop verification: all 154 tests pass on Linux and Windows NVIDIA workers
  against the same retained-source identity, including hardware-free mock
  telemetry. Lifecycle admission and end-user packaging remain pending.
- Photo workflow verification: malformed/incomplete responses, authentication
  failures and timeouts leave unsaved USD and active rendering intact on both
  platforms. Fresh Intelligence dialogs keep keys blank without file reads.
  Retained live Astra output has now been edited, saved, reopened and rendered
  while retaining its unverified status. Formal application admission is pending.
- Settings: apply native changes before persisting them, restore the prior
  configuration on recoverable failure, and preserve unsaved scene edits.
  LLM-only changes no longer reset simulation. Successful operations clear old
  error messages. The 152-test snapshot passes on both NVIDIA targets.
- Scene navigation: added nested USD hierarchy with ancestor-preserving search
  and full-path selection, plus readable stacked X/Y/Z inspector controls.
  The complete 144-test snapshot passes on Linux and Windows NVIDIA workers.
- Device development: added an explicitly simulated leader/follower telemetry
  panel with independent connections, joint inputs and frozen/stale-stream
  testing. Eighteen focused tests pass on Linux and Windows, including the
  strengthened photo viewport check. Mock readings do not yet drive rendered
  SO-101 joints, and no physical hardware or calibration is claimed.
- Photo reconstruction: added preview, explicit metadata-stripped upload, cancellable
  inference, native draft adoption and Save As with persistent uncertainty warnings.
  The 122-test matrix passes on Linux and Windows. A development-only live NVIDIA
  Astra request returned a valid three-object scene from a synthetic workspace image.
- Native startup: initialize OpenUSD before RTX to avoid the reproduced native
  parser crash in fresh existing-file sessions; targeted subprocess regressions
  pass on both platforms and the live reconstruction renders after the repair.

- Photo-scene groundwork: bounded JSON validation creates editable USD boxes,
  spheres and meshes with persistent unverified provenance. Draft scenes render
  with physics visibly disabled when no rigid bodies exist. All 113 current
  tests pass on Linux and Windows; photo upload/inference UI remains pending.

- Desktop CLI: keep Python and native shutdown diagnostics off the JSON result
  stream; actual Qt/RTX subprocess launch tests pass on Linux and Windows.
- Intelligence settings: malformed URL syntax now returns field errors, and
  percent-encoded credential query names are rejected.

- Retained desktop development: implemented actual RTX/OVStage/Newton scene
  coordination, Qt controls, private USD editing and atomic saving, asynchronous
  settings tests and failed-open recovery. Native/UI checks pass on Linux and
  Windows; 97 tests pass on each target, including repeated application launches
  and untitled Save As safeguards. Full milestone acceptance,
  packaging and physical robot integration remain open.

- Linux dependency verification: the exact qualified local Litai wheel verifies
  the complete native dependency installation, revalidation, and cleanup (11,105
  files). This is a prerequisite check, not desktop application acceptance.

- Development lifecycle: bound LeRTX to the qualified project-local Litai patch
  through a reviewed CLI transition. Global Litai is unchanged; application
  receipts still require a fresh rebuild and acceptance.

- Dependency preparation: added a reproducible metadata-only Linux USD wheel
  repair with original/repaired hashes, byte-identical library verification,
  and unchanged strict archive validation. No application installation is claimed.

- Native integration verification: retained real Linux RTX before/after images
  of an original USD scene with Newton CUDA body motion and clean SDK teardown.
  Added the desktop Component and native Python Flavor specifications; the
  graphical application is not yet accepted.
- Configuration requirements: recorded the NVIDIA Responses endpoint, exact Astra
  model, blank-key defaults, and LLM/application settings UI contract. A live text
  request passed; the graphical settings panel remains unimplemented.
- LeRTX harness: added a specification-led application entry point, independent
  acceptance, Linux/Windows target catalog entries, and the OVRTX/OVStage/Newton
  runtime contract. Local generation, build, 13 tests, and launch passed. Native
  application UI and robot integration remain future milestones.
- Initialized the project with Literate AI's specification-led lifecycle and durable
  user-directed work queue.
