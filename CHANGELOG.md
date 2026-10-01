# Changelog

## Unreleased

- Desktop: selecting any non-robot object (the ball, the obstacle, the work
  surface) now automatically raises the Inspector tab so its Translate/
  Rotate/Scale fields are immediately visible, instead of staying hidden
  behind the Robot simulation tab. Hint text, tooltip and Help now explain
  that this is how you move anything other than an arm joint.

- Desktop: dragging a locked follower link (while "Follower tracks the
  simulated leader" is checked) now shows a tooltip right at the cursor
  explaining why, in addition to the status bar message — the status bar
  alone was easy to miss while looking at the 3D viewport. Disabled follower
  sliders in the Robot simulation panel now explain themselves on hover too.

- Desktop: the Robot simulation panel can now save the current leader/follower
  joint positions as a named pose and load it back later. Two bundled presets
  ship with the app — "Danger" (arms raised, claws open) and "The Signal" (arm
  extended, pointing) — alongside any poses you save, which are stored under
  the settings directory. Loading a pose commands both arms to it directly,
  independent of follower tracking.

- Desktop: left- or right-drag an arm link to move its joint directly, following
  the mouse; both buttons grab and drive the joint the same way, and the earlier
  right-click popup is gone. Every leader and follower joint (12 total) now has
  its own labeled slider and numeric field, always visible in the Robot
  simulation panel — no joint picker or hidden toggle required. Alt-left-drag
  orbits, middle-drag pans, and wheel or trackpad scroll zooms. Clicking outside
  the rendered image or on a non-joint link now reports a status message instead
  of doing nothing. Verified with actual RTX picking and paused simulated motion
  on Linux ARM64.

- Desktop: grouped the toolbar with separators, added a leader/follower color
  legend under the viewport matching the rendered arm colors, colorized device
  role status, gave the device-assignment failure message concrete next steps,
  stripped the raw Python exception type name from native error text, and added
  a Back button plus joint-count/completion cues to the SO-101 setup wizard.

- Verification: reconcile photo-preset authority and specification metadata;
  package exact SO-101 resources as a hash-locked offline dependency so retained
  application admission includes binary models without weakening source limits.
  Current authority, component locks and receipt are checked by `litai verify`.

- Desktop: persistent joint instructions, named joint selection and a prominent
  angle slider. Added a modeless SO-101 USB calibration wizard with reference
  alignment, six individual range/direction checks, live provisional RTX mirroring,
  torque-off homing/limit writes, original-register backup and cancellation rollback.
  Exports LeRobot calibration and the matching virtual binding. Tested with the
  pinned SDK's emulated serial stream and Windows RTX; physical-arm acceptance is pending.
- Photos: OpenRouter defaults to GPT-6 Astra with high reasoning for detailed
  shapes, with explicit cost/latency guidance and a cheaper layout option.
  Generated drafts show geometry counts before opening. The actual turtle photo
  produced a recognizable low-poly turtle in native RTX, rather than a single box;
  this remains approximate colored geometry, not textured photogrammetry.

- Desktop: request schema-constrained photo scenes from OpenRouter while retaining local geometry validation; verified GPT-5 Mini image inference and Windows USD import.

- Desktop: make locked follower joints directly unlockable, retain following changes while rendering, and provide an inline photo API-key field with explicit upload progress and retry feedback.

- Desktop hardware: explicit SO-101 USB telemetry, LeRobot calibration import,
  motor arming, held bounded movement, torque-off stop and fault handling through
  the pinned Feetech SDK. Measured joint bindings support live articulated viewing
  and explicit virtual-pose targets. Added a Selected joint slider for simulation.
  Software validation uses emulated motors; physical-arm qualification is pending.

- Desktop: grab rendered SO-101 links to manipulate joints through bounded
  Newton targets, with RTX selection outlines and synchronized hierarchy selection.
  Paused drags preview physics; follower dragging requires following to be off.
  Alt-drag orbits, right-drag pans, and scroll zooms. Physical USB control remains
  unimplemented.

- Omarchy performance testing of the SO-101 workspace: corrected frame scheduling
  improves the actual 720p Qt window from 12.4 to 29.95 fps and simulation from
  41.5% to 99.7% of wall time. Compact, bounded runtime snapshots reduce scene
  reopen latency. Sequential memory-capped runs cover sustained rendering, idle,
  ten resets and ten reopens; 11 focused regressions pass in desktop startup order.
  Reopen memory retention and late-Qt SDK initialization remain unresolved.
  See `verification/performance/omarchy-20260926/README.md`; this is worktree
  performance evidence, not full application or release qualification.
- Prototype platform support: Linux ARM64 uses the verified `usd-exchange`
  provider; Windows and Linux x86-64 retain `usd-core`. Added per-platform hash
  locks, isolated setup, diagnostics, renderer warmup, desktop launchers and a
  reproducible source/setup ZIP. All 160 application tests pass on Windows 11,
  Linux x86-64, Linux ARM64 and Omarchy. Windows Start Menu launch produces a
  real frame and closes cleanly. ARM64 artifact admission and its full native suite
  pass. Fresh Windows 11 installation on an RTX 5080 Laptop also passes all 160
  tests and Start Menu launch; physical robot control is separate follow-on work.
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
