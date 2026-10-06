# Active work

This file is the durable resumption queue for user-directed and discovered work. Before
implementation, follow `skills/agent/record-user-directed-work/SKILL.md`.
Keep detailed designs in focused roadmap documents and link them here.

## Current open-items checkpoint — 2026-09-25

PORT-001 below records the current four-platform runtime and delivery evidence.
All four native suites pass 160 tests. The isolated Windows runtime also passes
all 160 tests. PORT-002 adds a fresh Windows 11 installation on an RTX 5080
Laptop GPU: hash-checked downloads, native warmup, all 160 tests and Start Menu
launch pass, closing the earlier Windows capacity limitation.
Formal admission reproduced the old framework's 256-artifact limit. Its retry
then exposed oversized Windows filesystem identifiers. Both repairs are now
upstream: the project binds exact revision `b2f8013491b7298b09a7d325f70595bf595bfe30`,
qualified by successful full CI run `35971877165` and its checksum-verified wheel.
The supported local rebind preserves policy and required receipt evidence.
`verification/framework-platform-qualification.json` retains the superseded
failure and current qualification. ARM64 application admission, independent
acceptance and all 160 tests against the admitted artifact now pass; see
`verification/prototype-admission-review.json`. Fresh Omarchy bundle installation,
upgrade and all 160 tests pass. PORT-001 is complete under the accepted scope.

This checklist is the current execution order. The detailed narratives below
retain historical failures and approvals; their older "next" and "in progress"
statements do not supersede this checkpoint. This is a development snapshot,
not an accepted or distributable release. HARNESS-001 is complete; RENDER-001,
CONFIG-001, TWIN-001 and ROBOT-001 remain open at the boundaries listed here.

### RENDER-001: qualification, admission and delivery

Current repair: photo preset authority and specification metadata are reconciled;
all three component locks are refreshed through the supported CLI. The exact
SO-101 resource wheel preserves original model bytes and provenance while keeping
retained source text-only. `verification/authority-refresh-review.json` records
current application admission and gate results; `litai verify` is the authority
for freshness. Physical-arm acceptance remains separate.


- [x] Diagnose the failed Windows shard and adopt an exact framework revision
  with green full-matrix CI. PRs #482 and #491 supply the required repairs;
  preserve canonical integer bounds and full artifact-custody validation.
- [x] Install the qualified exact wheel in a project-local environment, review
  and apply the supported Standard rebind; leave global installations unchanged.
- [x] Prepare current retained-source metadata, recipe, target-specific wheel
  lock and source/resolved SBOMs without changing tested application modules.
- [x] Complete verifier-owned retained-source admission, independent acceptance,
  sealed dependency custody and a current project test receipt. Resolve any new
  blocker at its owner rather than weakening validation or inventing evidence.
- [ ] Run native and Qt acceptance against the admitted artifact on both GPU
  targets for formal release qualification. ARM64 admitted-artifact tests pass
  all 160 cases; the four-platform development suites also pass all 160 cases.
- [ ] Verify first-frame startup, repeated scene reload/close, physics, camera,
  edit/save/reopen, error recovery and requirements coverage on the delivered
  artifact. Fresh-process success is not cleared-cache cold-start evidence.
- [ ] Complete reproducible Linux and Windows package construction and package
  verification, then clean-machine install, launch, upgrade and uninstall tests,
  dependency/license notices and user-facing setup/troubleshooting documentation.
- [ ] Establish sufficient Windows staging capacity using fresh worker-health
  checks. Prior free-space measurements are historical, not current permission
  to install; preserve active SDKs, environments and unrelated data.
- [ ] Deploy the repaired/admitted application deliberately; the existing
  interactive development process was not restarted and still has older code.

### CONFIG-001 and TWIN-001: final application acceptance

- [ ] Bind the tested settings transaction, blank-key defaults, endpoint/key
  separation, redaction, connection-test cancellation and persistence behavior
  into current admitted Linux/Windows application evidence.
- [ ] Bind photo preview/explicit upload, bounded Responses handling, cancellation,
  failure preservation and native draft edit/save/reopen into that same accepted
  artifact. Preserve unverified dimensions and provenance. Live synthetic-image
  inference is demonstrated, not measured reconstruction accuracy.
- [ ] Complete the remaining requirement-by-requirement UI/asset/failure-path
  review and close milestones two and three only after their dependencies pass.

### ROBOT-001: manual USB controls, physical twin and deferred product vision

Current live debugging direction: the operator reports frozen physical previews,
unclear base sweep progress and a reference diagram that does not match the arm.
Add an application-owned local diagnostic interface for co-session inspection:
current device samples, setup decisions, pose publication, rendered frames,
UI state, bounded timing history and validated live camera/performance controls.
Keep Qt/native/serial ownership intact and expose no arbitrary code or motor writes.
Use the instrumentation to trace and repair actual measurement-to-frame behavior.
Reproduction isolates a pinned OVRTX interaction: native outline selection stops
renderable descendants observing ancestor-only transform changes. Explicitly
refreshing their local transforms restores visible movement without dropping
native highlighting. Retain identities even after deselection until scene reload.
- [x] Implement and test local diagnostics, capture and bounded tuning commands.
  Live state/UI/RTX/window capture, camera and temporary frame-rate commands pass;
  GPU metrics are visible. The 84-test controller/UI/runtime scope passes after
  a focused 24-test rerun of the final preview scheduling and diagnostic changes.
- [x] Correct reference geometry and make sweep progress/action requirements visible.
- [x] Trace emulated telemetry through mapped angles, published poses and RTX pixels;
  both roles pass all six joints, automatic advancement and torque-off save on
  Windows RTX. Selection/deselection dynamics also pass. Physical operator
  confirmation remains pending; see verification/live-debug-review.json.

Current startup regression: scene opening inadvertently shuts down the application
registry permanently. Remove shutdown from document loading; prove hardware
controls can open after initial scene load and after replacement. Preserve shutdown
only for accepted application exit and finalization.
- [x] Verify scene-load/device-control regression (29 tests pass).
- [x] Verify both live Open controls buttons and Back navigation after restart;
  Leader COM6 and Follower COM5 open without connecting or actuating motors.

Current architecture repair: the wizard and hardware panels independently create
serial owners and use a window dictionary as a device registry. Introduce a
first-class application device registry with one controller per attachment,
shared telemetry/calibration/binding, scoped control access and serialized cleanup.
Review all application layers and record prioritized ownership, threading,
navigation and verification findings in docs/architecture/application-review.md.
- [x] Replace per-panel serial ownership with shared device controllers.
- [x] Verify simultaneous hardware/setup views, exclusive calibration, cancellation,
  completed handoff and application shutdown through the real serial emulator.
- [x] Complete the [architectural review](../architecture/application-review.md)
  and document remaining staged work.

Current navigation refinement: keep the numbered joint reference diagram visible
above scrolling setup instructions, with no hide option. Add explicit parent-panel
back actions to Device Manager, hardware controls, setup and its RTX companion.
Leaving hardware/setup must use existing shutdown and calibration recovery;
returning from RTX must preserve setup progress and live rendering.
- [x] Verify persistent diagram and parent navigation through Qt controls (37 tests
  pass; native Windows reference-step screenshot inspected).

Current assignment repair: live inspection found a cached Leader control window
on the former port after saved roles were exchanged. Desktop must validate both
role and attachment before reusing a hardware window, prevent assignment edits
while physical sessions are open, and make Device Manager roles/ports explicit
with the shared contrast-outlined color dots in rows and buttons. Preserve the
operator's current saved assignments and black/white palette.
Use distinct controller/gripper symbols inside role badges throughout the UI,
with automatic contrasting symbol ink and normal-contrast text. Color alone
must not encode role, including identical or nearly identical custom colors.
- [x] Reject stale cached windows and conflicting active port owners.
- [x] Show role-colored device rows and role/port-specific hardware buttons.
- [x] Verify reassignment routing, active-session guards, and black/white contrast.

Current device-coupling repair: a traced physical follower reference capture
fails while clearing wrist-roll homing: its unoffset encoder is 4530, outside
the normal 0..4095 measurement contract. The original offset/limits restore.
Desktop owns a bounded calibration-only unoffset read and representable homing
selection, retaining the actual reference encoder per joint instead of assuming
2047. Normal read/command guards remain strict. Always show the selected arm's
reference guide during preparation and keep capture errors outside the scroll area.
- [x] Reproduce extended unoffset feedback in the serial emulator for both roles.
- [x] Verify reference capture, mapping and cancellation with non-midpoint references.
- [x] Verify the physical capture/restore path with torque off and native previews.
  Both physical arms pass capture and restore with torque off; follower wrist
  reference is 2483 ticks. Native emulated six-joint frame changes pass for both
  roles. Controller/setup suite: 53 tests, one platform skip; Qt setup/hardware
  suite: 29 tests pass. See `verification/reference-capture-review.json`.
  Full physical sweeps and powered motion remain operator qualification work.

Operator follow-up: Enable motors opens no confirmation and disabled controls
are visually ambiguous; Release torque appears inert. Desktop owns explicit
disabled styling, the exact arming prerequisite beside the button, measured
six-motor torque state and pending/confirmed/failed command feedback in setup and
hardware controls. Diagnose using the serial emulator without actuating the
operator's arm. Preserve calibration, freshness and explicit torque authorization.
Refinement: replace mirror enable/release buttons with one measured-state control.
All-off offers Engage; any-on offers Release; unknown/mixed states are explicit.
Calibration remains torque-off and shows “Motors free” when already released.
Live screen inspection found the follower at the stationary reference step and
the leader in raw read-only mode with no calibration/binding. Make reference,
waiting and live preview modes conspicuous; explain missing mirror prerequisites
beside the disabled control. Do not invent physical joint coordinates before
calibration or claim the reference guide is following the arm.

- [x] Implement visible disabled states and motor-action feedback.
- [x] Verify blocked/confirmed/cancelled enable, repeated release, disconnected
  release and failed stop, including the real Qt buttons and both themes.
  The 92 focused tests pass (one platform-specific skip). Serial-emulator Qt
  screenshots verify both themes; see `verification/motor-feedback-review.json`.
  Active physical sessions were inspected without commanding or restarting them.


Operator follow-up: keep the selected leader/follower unmistakable throughout
setup. Desktop owns persistent role labels and a shared palette for the wizard,
reference diagram, viewport legend and rendered printed parts. Allow saved custom
colors before connection to match printed arms; retain textual role identification
even when colors are identical. Color changes must not alter motor assignments,
calibration, authored geometry or hardware state.
Extend the same color dots to role references throughout controls, device assignment,
simulation, mock telemetry and selection UI. Use dual light/dark outlines so user
colors remain visible on either theme while keeping text at normal contrast.

- [x] Implement shared role colors, persistent selection labels and saved choices.
- [x] Verify role switching, persistence/migration, material colors and setup UI.
  Windows passes 89 focused configuration, settings, setup, simulation, device,
  mock and hardware UI tests, plus two role-dot contrast/text tests. The settings
  test teardown now drains deferred Qt deletion to avoid retaining prior dialogs.
  Native RTX verification captures the custom purple follower, consistent labels
  and all six automatic joint transitions in 34.94 seconds. See
  `verification/arm-colors-review.json`; hardware was emulated. Formal lifecycle
  admission remains stale and is not advanced by these feature checks.


Operator follow-up (2026-10-05), implemented: tolerate incidental motion of
unselected joints, make each joint capture advance automatically, and give the
solid native RTX arm a dedicated live window. The current three-tick movement
message is too sensitive, and the schematic is being mistaken for live geometry.
Desktop owns this correction. Gather two deliberately held endpoints and a
repeat visit to the first endpoint using only the selected motor, with minimum
travel, sample-count, dwell and freshness gates. A valid rendered observation must
precede automatic advancement. Keep reference capture and final hardware save
explicit; the operator reviews travel and direction once before saving.

- [x] Add automatic sweep capture with jitter, incidental-motion, stale-data and
  duplicate-sample regressions; do not infer full mechanical travel from a twitch.
- [x] Open a dedicated solid RTX preview window, stream every native frame to it,
  keep all six measured joints moving, and demote the schematic to optional help.
- [x] Verify automatic six-joint progression and actual changing native frames,
  cancellation/recovery, review/save and preview-window lifecycle, then commit and
  push the correction. Physical-arm acceptance remains the operator's check.

Evidence: `verification/guided-setup-auto-review.json` records 74 passing tests
and one POSIX-only skip, all six automatic joint transitions, native joint
readback and changing RTX frame bytes, explicit final save with torque off, and
the separate live-window lifecycle. Next: check this revision on the physical
arm after saving the current workspace and finishing/cancelling its calibration.

Current operator correction (2026-10-05): first physical follower setup exposes
missing visible motion and unfamiliar anatomical joint names. Implemented:
make calibration a self-contained visual wizard owned by the desktop Component.
Keep the native RTX preview next to plain-language, numbered joint identification,
show measured movement and completion per joint, and retain pending preview intent
while rendering is busy. Preserve torque-off calibration and rollback semantics.

- [x] Add illustrated joint locations, individual instructions, travel feedback,
  integrated native preview, review and explicit completion.
- [x] Prevent renderer scheduling from starving calibration and subsequent live view;
  reject stale observations and invalidate cancelled/in-flight preview work.
- [x] Verify busy-renderer, stale/disconnect, all-six-joint and cancellation paths
  with emulated hardware, Qt and native RTX evidence; record physical qualification
  separately from software verification.

Evidence: `verification/guided-setup-visual-review.json` records 54 passing focused
tests (one POSIX-only skip), native RTX readback and changing frame bytes for all
six joints, torque-off save and compact-layout inspection. The Component lock is
refreshed. The pre-existing formal lifecycle test receipt still needs renewal;
this retained-source development change is not a release attestation. Next:
operator checks the new wizard against the physical follower after cancelling or
finishing the old setup and restarting the application.


Current direction supersedes the earlier read-only boundary: the user explicitly
requested USB reads and writes before taking the app to the physical SO-101 pair.
Implemented: pinned Feetech SDK transport, LeRobot calibration validation,
independent hardware workers, read/arm/move/stop controls and measured virtual
binding. Connect/reconnect stays read-only. SDK byte-stream, OS serial endpoint,
failure-path, Qt and native RTX checks are recorded in
`verification/usb-control-review.json`. The Windows development app is deployed;
Current framework authority/lock/receipt results are tracked separately in
`verification/authority-refresh-review.json`; software checks do not qualify hardware.
Actual leader/follower qualification remains pending for the connected arms.
Guided torque-off homing/range calibration now has a separate explicit write path
and original-register backup. Individual motor-ID commissioning and autonomous
policies remain separate; the wizard links the official fresh-motor setup guide.

- [ ] Finish and verify USB candidate discovery, persistent explicit roles,
  ambiguous/missing serial handling, hotplug/reconnect and stale-state behavior.
- [ ] Source licensed SO-101 geometry/kinematics; verify axes, offsets, units and
  limits, including the gripper. Connect the explicit leader/follower mock to
  rendered joint poses through the native worker, without Newton pose conflicts.
- [x] Ship the unchanged checksum-pinned Feetech SDK used by LeRobot and the
  hash-locked pyserial 3.5 dependency; verify calibration against motor registers.
  No high-level robot setup or EEPROM writes run implicitly.
- [x] Verify software packet/controller failure paths, read-only no-write behavior,
  explicit arm/move/stop, bounded targets, held-motion release and stale heartbeat
  handling. Test measured live-pose publication and simulation ownership on RTX.
- [ ] Next physical gate: connect the real leader and follower, confirm motor
  identities/calibration, measured directions, bounded motion, stop behavior and
  rendered poses. No emulated result counts as physical-arm acceptance.
- [ ] Design and implement measured scene scale, robot-base registration,
  obstacle/occlusion review and verification invalidation after geometry edits;
  a plausible photo reconstruction must never imply collision safety.
- [ ] Specify and qualify any Hugging Face model selection/download/inference
  workflow separately; no robot policy execution is currently implemented.
- [ ] Deferred: autonomous task execution, planning and physical safety-system
  integration. Manual bounded USB control is implemented above; real hardware
  qualification is still required.

### CHECKPOINT-001: repository publication

- [x] Commit the reviewed source/specification/test/evidence checkpoint and push
  to `NVIDIA-dev/LeRTX`; verify the remote SHA. The operator selected the
  NVIDIA-dev organization. Create a private development repository; public
  publication is not implied by this checkpoint.
- [ ] Establish project CI and repeatable contributor verification on the chosen
  remote without confusing upstream Litai CI with LeRTX native acceptance.
- [ ] Before public publication, select the application license, review NVIDIA
  SDK redistribution obligations, resolve internal framework references through
  supported tooling, and establish public availability of the configured Astra
  service/model. Public SDK downloads do not make those SDKs open source.

## Detailed-roadmap lifecycle

This file is the sole resumable queue. Create a supporting file beneath `docs/roadmap/`
only when one item cannot keep a program's rationale, ordering, and acceptance contract
readable. Put this visible header immediately after the detailed document's title:

```markdown
- **Status:** active
- **Owning queue item:** [AREA-NNN](active-work.md#area-nnn-heading)
- **Completion / archival evidence:** pending while AREA-NNN remains open
```

Status is exactly `active`, `partial`, `deferred`, `completed`, or `historical`. The
owner must resolve to a checkbox or named program heading in this file. A terminal state
requires linked evidence. Keep a completed plan here only when doing so preserves useful
inbound links; move substantial closed programs beneath `docs/history/roadmap/`, retain
their owner, and mark them `historical`. Do not create a separate file for an ordinary
queue item or let `docs/roadmap/` become a plan archive.

## P0

### [x] HARNESS-001 — Milestone one: Literate AI application harness

- **Priority:** P0
- **Owner:** project authority and application harness
- **Direction:** Use litai as the creation system for LeRTX.
- **Conclusion:** Initialize canonical authority, record the product milestones, and verify the harness before claiming runtime completion.
- **Depends on:** none
- **Implementation:**
  - [x] Create the project through litai onboard create.
  - [x] Record product requirements and the real-rendering milestone contract.
  - [x] Catalogue Linux and Windows target Flavors without conflating them with the macOS bootstrap host.
- **Evidence:**
  - [x] litai project validate passes.
  - [x] litai verify passes, or records precise outstanding lifecycle evidence without claiming completion.
  - [x] A current build and test receipt proves a generated harness Component executes.

- **Result:** `components/harness` passed generation, build, 13 tests, independent
  acceptance, and launch on the macOS development host. `litai verify` reported
  three passing gates, no failures, and two intentional skips (no CodeGraph or
  HTML artifacts). Launch uses the framework argument array
  `[{"command":"info"}]`. The receipt is `verification/current.json`.
- **Survey:** The workspace has no Git remote; forge review and peer-work GC
  inspection were unavailable. No publication or remote landing is claimed.

### [ ] RENDER-001 — Milestone two: OVRTX, OVStage, and Newton application

- **Renderer startup repair (current):** The operator requested fixing the
  fresh-process existing-scene failure. Trace evidence points to renderer
  destruction during the first document rebuild: the worker eagerly creates an
  empty renderer, then immediately destroys/recreates it before any frame.
  Repaired: defer renderer creation until the first runtime scene is ready.
  Deterministic startup coverage, all 158 Linux tests, three additional fresh
  existing-scene launches, and eight Windows native/worker tests pass with
  unchanged deadlines. See `verification/renderer-startup-review.md`.
  The package-count proposal and existing running application remain untouched;
  no new admission or package claim follows from these tests.
- **First-running-app continuation:** The user requested a usable running
  application. Fresh testing on the Linux user's real X11 desktop passes the
  visible RTX/Newton edit/save control test, blank-scene CLI launch, and repeated
  in-process close. The existing-file subprocess test fails its first-frame
  deadline when ordered after the native-window test, but passes alone in
  15.978 seconds. Preserve that order-dependent reliability gap; do not report
  this four-test batch as passing. Normal interactive launch is now verified on
  the user's desktop: live rendered workspace, `Native: ready`, about 16 fps,
  and process left open. See `verification/first-running-application.json`.
  That original mixed-order failure is repaired and verified by the later
  startup/shutdown evidence below. Formal admission remains open.
- **Remaining-items direction:** Resolve startup reliability, retained application
  admission and Linux/Windows packaging. The preparation-base framework run ended
  with a stale driver-review identity; published PR #464 has failing CI that must
  be diagnosed before adoption. Startup/shutdown repair now passes both full
  native suites without weakening the timeout or success assertions. Do not merge or change review pins merely
  to make these checks green.
- **Startup repair evidence:** The timeout reproduces under Xvfb with the native
  worker blocked at `attach_ovstage`; importing `Usd` alone leaves stage/plugin
  initialization lazy. Explicitly creating and releasing an anonymous USD stage
  before RTX construction passes the previously failing four-test order in
  29.623 seconds and a repeated seven-test native/launch run in 31.623 seconds.
  Three portable worker tests pass, including ordering and fail-closed bootstrap.
  Full Linux regression initially had two missing-fixture-environment errors;
  the configured rerun passes all 156 tests in 67.386 seconds. At that point
  Windows verification was held with only 1.25 GiB free. The subsequent archive
  recovery and full platform results are recorded below; SDKs and unrelated
  files were preserved.
- **Admission/packaging frontier:** PR #464 now contains documentation review
  correction `0cb23378`; its focused canonical-project validation passes. Hosted
  Ubuntu/Python 3.14 (4,921 tests) and Windows shard three (2,267 passes) now fail
  only the inspected lifecycle-driver identity check; matrix siblings were
  cancelled and are not passing evidence. Driver review/pin approval was requested before local build
  qualification. The earlier generic pip probe was inappropriate: the desktop
  deliberately selects `flavor://lertx/desktop-wheels` and excludes generic pip.
  `litai package plan components/desktop --target host` succeeds with that exact
  existing provider (declaration `sha256:fec709b9446e7ba08d8b134bde05ccc2d60f67b4116ee5f81999091cd57a6512`).
  It grants neither execution nor publication and is not an accepted package.
  Preserve the existing selection; finish admission and current artifact/SBOM
  evidence before constructing and verifying native delivery.
  After the native-contract update, supported documentation review and all three
  lock checks pass. `litai verify` still fails its current-receipt gate, as expected
  while retained application admission is unfinished. The peer-work survey cannot
  resolve HEAD in this unborn repository; no Git cleanup was performed.
- **Windows capacity recovery:** Under the existing cleanup authorization,
  removed ten completed-install wheel staging archives after every size/hash
  matched retained Mac copies and no installer referenced the staging directory.
  Recovered 1,701,072,896 bytes; 2.73 GiB remains. Installed SDKs and Qt are
  unchanged. The volume remains percentage-critical; only existing-environment
  regression tests may proceed with a 2 GiB reserve and a 256 MiB write budget.
  Stop the owned test process tree if either bound is crossed. Full installs and
  packaging still require substantially more space. The bounded Windows run
  completed seven tests in 407.630 seconds with two fresh-process CLI timeouts;
  visible controls, repeated in-process shutdown and portable worker cases passed.
  Free space remained 2,823,094,272 bytes. The isolated existing-file case passed
  in 43.927 seconds. A mixed-order diagnostic confirms native SDK initialization
  changes Windows PATH outside Python's environment mapping, but passing an
  explicit environment does not resolve the failure: native controls passed in
  70.203 seconds, then CLI launch failed after 150.890 seconds with repeated
  worker traces at `attach_ovstage`. Free space remained 2,692,968,448 bytes.
  The identical 54-file source snapshot passes all 157 Linux tests in 67.203
  seconds. Keeping the parent's Qt events responsive also fails (150.726 seconds)
  at the same native call. Installed Windows loader source additionally sets
  `OMNI_PLUGINS_BASE_PATH` and `OMNI_USD_PLUGINS_BASE_PATH` in Python's environment.
  Restoring the pre-initialization environment also fails (150.669 seconds).
  The separate Windows DLL-directory state is unchanged; no restoration was
  performed. A further diagnostic kept the completed native test process
  alive briefly while a separately launched SSH process runs the original CLI
  regression: the independent launch also times out (151.378 seconds), ruling
  out inheritance as a necessary condition. The installed SDK documents
  `RendererConfig.keep_system_alive` defaulting to enabled even after every
  renderer instance is destroyed. Explicit `keep_system_alive=False` now passes
  the previously failing Windows seven-test order in 234.028 seconds, including
  both fresh-process CLI cases and repeated native close. Linux passes all 157
  tests in 95.020 seconds on the same source identity
  `sha256:394bda7d83268dfc5559886575f5a7c6c3947d4bb3beeedfe541c834238cf0db`.
  The native-interface contract now records both the USD stage bootstrap and full
  renderer-system shutdown; the desktop lock is refreshed without changing
  dependency versions or driver pins. The full Windows suite now also passes:
  157 tests in 520.415 seconds, process exit 0, with 2,694,156,288 bytes free.
  Both worker trees still match the recorded source identity after completion.
  The run respected the 2 GiB reserve, 256 MiB write budget and 900-second bound.
  Next: complete reviewed retained-source admission and exact-target packaging;
  the operator now explicitly approves local driver review, supported pin recording
  and local-build qualification, without application rebind or global installation.
  Do not weaken frame, shutdown or timing assertions or attribute the hang to PATH.
  The review and supported pin recording are complete in parent local commit
  `051852ad94e3ed6ce4ba3c13de44993ed949d6bf`; the driver identity is
  `sha256:75f82723a21237d8c88254e41fb62bab770cfac1363c6eae86956462c1c4a434`.
  Fresh full-suite qualification passed on that frozen revision: 5,131 tests in
  4,890.786 seconds, 34 skips, exit 0. Installed-wheel qualification also passed,
  retaining wheel `sha256:d4a1fb0b6be34d7f59b66b2e45f917f7aef7253a1561bdddbe017e8004ae486c`.
  The separate project-local CLI has the same 872-member distribution identity
  observed by wheel qualification and passes its dependency check. See
  `verification/retained-driver-qualification.json` for exact evidence and paths.
  The early pre-commit test attempt was stopped and is not passing evidence.
  The operator now authorizes the next steps following merge. PR #464 is already
  merged upstream as `26c8b22fa93af663905142d87769bea8ee18b839`; no duplicate merge
  or publication of private dependency work is needed. The reviewed supported
  lifecycle rebind is now applied, with unchanged policy and receipt requirements.
  Current Linux source metadata and exact-source authorization are prepared;
  admission reaches independent acceptance but fails because the packaged
  directory omits the verified Python runtime and its execution custody. The
  original sealed artifact is unchanged. A tiny framework wheel fixture
  reproduces the failure without native SDKs. With explicit operator approval,
  filed **GitHub issue:** [#473](https://github.com/NVIDIA-dev/literate-ai/issues/473)
  and queued a technical handoff to the active framework Codex session. Next:
  coordinate the parent package-custody repair, then review and qualify any new
  lifecycle build before adoption. See
  `verification/retained-admission-review.md` and the sanitized report
  `verification/python-package-custody-issue.md`. Global Litai and physical
  actuation remain out of scope; no passing application receipt is claimed.
  A fresh 157-test native/application rerun against the built dependency runtime
  passes in 95.255 seconds. The initial diagnostic had two non-inherited import
  path failures and one first-window frame deadline failure; preserve that
  cold-start gap rather than treating the warm rerun as universal startup proof.
  See `verification/native/linux/retained-admission-regression.json`. Windows
  remains held at 2.49 GiB free; the inspected pip cache contains only 98 bytes,
  with no material safe cache recovery established.
- **Merged-fix adoption:** The operator authorizes qualification and adoption of
  merged PR #474, upstream commit `89e050061769a56f77df383258c25c6fd57580ed`.
  In progress: diagnose the reported CI failure and qualify that exact framework
  integration before any new rebind. Preserve the existing qualified wheel and
  retained source, review the supported rebind plan, then rerun exact-source
  Linux admission and native regression. Issue closure is not application
  acceptance; Windows staging remains conditional on fresh capacity checks.
  The initial merge still carries the known fixture error. The subsequent merged
  integration PR #477, `aa3a58689fa5b1c585dd532939ef1869ab6bea20`, corrects it
  and includes #474. Its Git tree exactly matches CI-tested head `4a817054`;
  all 19 jobs in run `35324091520` passed. Qualification now targets this complete
  integration, not the earlier failing tree. The superseded old-tree local test
  was interrupted and is not passing evidence. Current driver/document review
  and all 11 local Python lifecycle tests pass. Installed-wheel, lint, formatting,
  and layout checks also pass. The exact qualified wheel is now installed in
  isolated environments; reviewed Standard rebind `58fcb849` was applied without
  changing policy or required evidence. Linux admission of the unchanged tree
  `272e1af0`, authorization `3dfa324f`, builds the native artifact but fails at
  `PackageResult.artifacts: must contain at most 256 values`. The directory
  adapter maps every logical runtime file to an artifact; this closure needs
  11,117 entries. A tiny fixture passes at 256 and rejects 257. See
  `verification/package-custody-qualification.md` and
  `verification/package-file-count-blocker.md`. Native regression completes in
  212.590 seconds: 156/157 pass; the existing-scene fresh-process CLI launch
  delivers no native frame, with a renderer-destruction trace during scene open.
  See `verification/native/linux/package-adoption-regression.json`.
  No current application receipt or verified package is claimed. A separate
  reviewed framework fix is needed; no validator has been bypassed.
- **Package-count fix authorization:** The operator approved filing the new
  blocker and preparing a reviewed local fix. Filed
  [literate-ai #480](https://github.com/NVIDIA-dev/literate-ai/issues/480).
  The project-local parent patch aligns directory-shaped artifact bounds with
  the existing 16,384-file closure limit while preserving 256 outer outputs for
  archives/installers/container images. All 78 focused tests and lint/format/layout
  checks pass. The driver review correctly remains stale pending qualification;
  no new pin, merge, publication or LeRTX rebind was performed. See
  `verification/package-file-count-fix-review.md` for review and remaining gates.
- **Packaging continuation (2026-09-19):** Upstream PR
  [#482](https://github.com/NVIDIA-dev/literate-ai/pull/482), head `5c84af3f`,
  implements the same directory-shaped bound distinction and retains seal
  validation. At inspection, 18 CI checks pass and one macOS conformance job
  remains running; GitHub reports conflicts with current main. Prefer that
  existing contribution over a duplicate publication. The local proposal remains
  preserved in a named Git stash. The operator authorizes conflict resolution
  and completing the fix without repeated routine approval requests. Local
  integration `4b3832c4` resolves the three documentation/review-pin conflicts;
  207 focused tests pass with two skips, as do lint, formatting and layout.
  Another upstream session merged #482 as `f99e4cb2` during qualification.
  Comparison finds only one changelog blank line differs from the local merge;
  code, tests, schemas and reviewed identities match. The superseded local broad
  test and wheel runs were stopped, not counted as passes. In progress: qualify
  exact merged revision `f99e4cb2`, then review the application rebind and retry
  admission. Its new hosted CI is not yet complete; no global install or LeRTX
  rebind has occurred.
- **Current source-artifact audit:** After the native lifecycle contract update,
  read-only planning yields recipe
  `sha256:54b5228c3369d9bc4220096f8c13cd7847cb7d7307a73f417fc6458f89b9fe5a`,
  but the retained test manifest still binds
  `sha256:5966b75bd8876599e2881702e8d99d59b2a94e9fcd07c302d8571425a8d3745c`.
  The retained tree has no `.literate/sbom.cdx.json` or
  `python-wheel-lock.json`. The byte-preserved original archive contains an SBOM,
  but it binds old Component/graph authority and must not be reused as current
  evidence. Prepare and independently validate current declarative source
  metadata and exact-target dependency closure before seeking snapshot admission;
  never fabricate an acceptance receipt or alter source during admission.
- **Priority:** P0
- **Owner:** application shell and native integration Components
- **Direction:** Run an application rendering 3D frames with OVRTX and OVStage and using Newton physics.
- **Conclusion:** Use actual native SDK interfaces, bind physics bodies by USD prim identity, and require rendered-frame and lifecycle evidence on NVIDIA hardware.
- **Current UI repair:** the source still presents USD hierarchy as a flat list
  and the retained Windows screenshot shows cramped three-across transform fields.
  In progress: nested parent/child scene navigation with ancestor-preserving
  search, explicit full-path identity and selection safety; readable labeled
  X/Y/Z inspector rows. Verify visible controls and native edit/save on both
  targets, preserving paused camera input and unsaved-edit behavior.
  Linux now passes all 144 tests (91.014 seconds). Its updated native screenshot
  shows nested prim navigation and readable stacked X/Y/Z fields. The screenshot
  also exposes an old status-bar parse error surviving successful recovery;
  clear or expire that transient message without hiding an active native error.
  Windows also passes all 144 tests (269.635 seconds) on the same 53-file source
  identity. Both remote trees match the local snapshot; transfers completed
  before dispatch and no app files were changed during these suites. Evidence
  is retained in `verification/navigation-ui-review.json`.
  Read-only lifecycle investigation: `spec merge desktop/source --component desktop`
  fails closed with `project.spec_merge_component_exists`. Planning a distinct
  Component succeeds, but its proposal contains source/test inventory statements
  rather than the existing desktop behavior contract; it was not applied.
  `spec qualify` performs clean generation, and `rebuild --from-accepted-source`
  requires already-admitted membership. The operator approved filing the issue
  and preparing a project-local retained-source admission fix, preserving existing
  authority and acceptance, initially without merge/publication. Filed upstream
  [issue #463](https://github.com/NVIDIA-dev/literate-ai/issues/463).
  The operator subsequently authorized publication: isolated draft
  [PR #464](https://github.com/NVIDIA-dev/literate-ai/pull/464) contains only
  the retained-source patch, excluding earlier private Python-wheel commits.
  No merge, installation or lifecycle rebind was performed. Qualification remains
  in progress; exact limitations are in `verification/retained-source-fix-review.md`.
  The sanitized issue body is
  `verification/retained-source-admission-issue.md`.
  `verification/milestone-acceptance-audit.md` maps the remaining acceptance
  boundaries; notably both OS dependency-installation qualifications already
  passed, but they are not retained-application admission or delivery evidence.
- **Depends on:** HARNESS-001
- **Current checkpoint:** The qualified local framework at `0449e10c` is bound
  through the reviewed CLI transition. Documentation and all three locks pass;
  the application receipt is correctly stale. The exact same non-editable wheel
  now passes the complete Linux offline native installation: 11,105 files,
  independent revalidation and cleanup. Evidence is
  `verification/native/linux/qualified-install-review.json`; the wheel identity
  and full framework qualification are in `verification/shared-wheel-review.json`.
  This supersedes earlier patched-environment dependency evidence, not application
  acceptance. Next in progress: establish bounded desktop implementation and
  independent native/UI acceptance through Litai; do not execute either rejected
  candidate or repeat unchanged whole-application generation. Windows installation
  remains held for insufficient staging headroom.
  Boundary inspection confirms the qualified wheel profile supports a single
  Python application entrypoint, not a third-party-dependent library Component
  (`standard_project.py`, `standard_command.python_wheel_profile_unsupported`).
  Do not assume splitting native code into library Components is already supported.
  Dependency-free configuration logic can be considered separately; native scene
  and UI work must retain a supported application lifecycle and real acceptance.
  The next candidate will use materially new generation inputs: a project-owned
  Linux target Flavor carrying the observed interpreter environment, all compatible
  tags and exact verified ten-wheel metadata, plus concrete pinned SDK call and
  ownership contracts. Previous requests lacked the exact lock data necessary for
  admission. Keep source generation and pre-execution review separate; this is
  not permission to execute rejected candidates or invent wheel hashes. Review
  native, scene, settings and UI boundaries before any application execution.
  The Linux target lock now validates ten packages, fifteen dependency edges and
  all 1,089 observed tags. The pinned SDK reference is included in generation,
  and verifier-owned settings cases are separate from native/UI acceptance.
  The new Astra source-only generation ended with `coding_cli.empty_generation`
  and produced no candidate. The CLI reports only the failure code; the provider's
  underlying reason has not yet been recovered. Do not retry unchanged or claim
  an application exists. Generation-transport diagnosis remains next after the
  operator-requested Windows cache cleanup.
  The provider reason has now been recovered with process-local error logging:
  Codex's initial request read was truncated; its no-shell instruction prevented
  further reads, and inherited repository onboarding demanded a missing root
  SKILL.md in the disposable workspace. A small sandboxed file-write probe passes,
  so workspace write permission is not the blocker. No installed framework file
  was changed. Next generation uses the explicitly selected supported Claude
  provider with its dedicated Read tool and an external disposable workspace,
  preserving source-only scope and all validation/execution gates.
  That external-workspace generation finished successfully as source generation,
  but terminal review rejected the application: Save does not write USD, the
  frame timer only updates a label, and no UI-driven Newton stepping exists.
  The terminal tests use unittest, resolving the earlier pytest dependency concern;
  that correction does not resolve missing application integration. No application
  execution or admission occurred. Exact file hashes and blocking findings are
  retained in `verification/desktop-terminal-review.json`. The Windows transfer remains live. The
  supported-provider route avoids the observed input-reading failure without a
  parent patch or relaxed sandbox.
  Preliminary inspection during generation still finds inert Save and frame-tick
  handlers and incomplete native tests. A separate installed-USD check confirms
  `Matrix4d.ExtractScale` is absent; the candidate's unit-scale fallback would
  distort colliders (`verification/native/linux/usd-transform-api.json`). Terminal
  inspection confirms that fallback remains. Independent centimeter/Y-up and
  unsupported-collider fixtures now parse successfully under installed Linux USD
  (`verification/acceptance/scenes/parse-review.json`); this is fixture validation,
  not application acceptance. The operator has been asked
  whether direct, reviewable repairs to generated source may replace repeated
  spec-only regeneration if these defects remain. The operator has now explicitly
  approved direct repair and retention with reviewable diffs and full native/UI
  testing. Retain the exact generated baseline separately from `desktop/source`,
  repair application code incrementally, and preserve all safety and acceptance
  requirements. This exception does not authorize fabricated Standard lifecycle
  receipts or mark modified source as untouched generation. The next action in
  progress is retained-source repair of authored USD and native coordination.
  The consolidated 35-file snapshot now passes 93 tests on each NVIDIA platform
  (Linux 38.061 seconds, Windows 106.908 seconds), recorded in their respective
  `verification/native/*/full-suite-review.json` files. This is not complete
  milestone acceptance. The next repair validates real application launch and
  shutdown, unique temporary workspaces, and Save As protection for untitled
  scenes, including cancellation and rejection of temporary descendants.
  These checks now pass in the 97-test Linux suite (53.730 seconds), including
  two real Qt event-loop launches with rendered frames and completed native
  shutdown. See `verification/native/linux/launch-save-review.json`. The matching
  Windows run also passed all 97 tests in 141.862 seconds, with matching source
  hashes (`verification/native/windows/launch-save-review.json`). Follow-up: keep native SDK stdout separate from CLI
  result JSON and test that boundary in a subprocess; complete the remaining
  settings, interaction and distributable-install acceptance rather than treating
  test-count growth as milestone completion.
  CLI subprocess isolation now passes on both targets: four launch/protocol tests
  take 33.706 seconds on Linux and 91.258 seconds on Windows. This includes an
  actual RTX frame through the CLI entrypoint and native shutdown with only JSON
  on stdout (`verification/cli-launch-review.json`). Packaging and the remaining
  settings/interaction acceptance are still open.
  Current Litai verification passes authority and all three locks, but fails the
  stale project test receipt; no replacement receipt is claimed. Peer-work
  cleanup survey cannot resolve HEAD in the unborn repository, and forge review
  is unavailable without a supported remote. No Git cleanup was performed.
  Baseline-to-source whitespace checking reports trailing blank lines in 13
  generated files; these remain a review cleanup item, not a passing check.
  The document, CUDA physics and native worker tests now report seven passes on
  Linux (`verification/native/linux/retained-source-review.json`). These cover
  disk persistence, centimeter/Y-up and parent scale, static collider rejection,
  and an owned RTX frame. UI composition, live simulation publication, repeated
  lifecycle and Windows application acceptance remain unchecked. The operator
  expanded the goal to milestones one through three. The subsequent explicit
  clarification scopes TWIN-001 milestone three to Astra photo-to-USD only;
  read-only physical joint synchronization remains follow-on work, without
  assuming actuation authority.
  The native scene session now couples authored USD, CUDA Newton, OVStage pose
  publication and RTX frames. Its integrated Linux test passed motion, paused
  camera rendering, reset, edit/save/reopen and shutdown in 20.270 seconds
  (`verification/native/linux/scene-session-review.json`). Explicit OVStage query
  and path-list releases removed the warnings found in the first run. Thirty-three
  portable configuration/transport/clock/dispatch tests also pass. The next action
  is Qt integration plus recoverable-command regression coverage; these results
  are not yet a running, accepted cross-platform desktop application.
  Qt now queues scene, frame, save, transport, inspector and camera operations on
  the native worker and polls results on the UI thread. A portable recoverable-
  command regression passes. The first Qt/GPU test timed out at loading; a stack
  sample found the test in QTest.qWait. Replacing its wait with event processing
  and a GIL-releasing Python sleep produced a pass in 28.236 seconds with the
  same timeout and assertions. Screenshot inspected and retained with the result
  (`verification/native/linux/window-review.json`). Visual framing, complete
  settings behavior, failure dialogs and Windows UI verification remain open.
  Connection testing now uses a bounded background request with stale-result
  invalidation; defaults stay staged until Save and invalid fields retain the
  prior profile. Ten Qt/settings/worker tests pass with injected transport
  (`verification/native/linux/settings-review.json`), without reading credentials
  or contacting inference. Complete diagnostics, theme/units behavior, rendering
  quality settings and cross-platform acceptance still remain.
  Windows now passes five document/CUDA/native-session tests in 63.671 seconds
  (`verification/native/windows/scene-session-review.json`). The first run found
  fsync on a read-only temporary handle fails on Windows; the writable-handle
  repair passed the unchanged save and integrated-session tests. Display units
  and light/dark theme now have UI behavior; four focused settings tests pass on
  Linux. Windows Qt verification now passes four real-window/settings tests in
  72.137 seconds (`verification/native/windows/window-review.json`). The SDK-only
  environment lacked Qt; verified wheels were provisioned into a separate target
  without modifying it. The screenshot shows real rendering but an overly narrow
  hierarchy dock; corrected dock sizing now passes the Windows rerun (five tests,
  73.177 seconds) and screenshot inspection. Runtime GPU/SDK versions and workspace
  directories now populate Diagnostics; display-unit changes refresh inspector
  values. Evidence: `verification/native/windows/layout-review.json`. Numeric
  fields remain visually cramped; remaining interaction and packaging acceptance
  must not be inferred from the current passes.
  Document failure-path tests reproduced shared dirty USD layers and an Euler
  round-trip defect. Private disk-loaded layers and corrected decomposition now
  pass five tests on both Linux and Windows, including anchored relative assets
  through Save As and nonmutating shear rejection
  (`verification/document-isolation-review.json`). Integrated UI regression and
  failed-open recovery remain next; document-only passes do not close those gates.
  Linux integration now passes with private layers: malformed USD preserves the
  existing scene and worker, the UI remains ready after reporting the error, and
  failed Save prevents discard/open continuation. Native-session, settings/dialog
  and real-window runs all passed (`verification/native/linux/recovery-review.json`).
  Windows recovery regression and remaining settings/asset-policy checks are open.
  Rendering quality now authors the pinned OVRTX DLSS token in the runtime
  render product; balanced/high restart and real-frame checks pass on Linux.
  Configured local asset search paths now resolve missing relative root-layer
  assets; six document tests pass. Evidence is
  `verification/native/linux/runtime-settings-review.json`. The Windows recovery
  run has passed document/native stages and remains live in its Qt stage; it
  predates these quality/search-path changes and must not be called current full
  application acceptance.
  The Windows recovery run finished: 12 tests pass in 138.452 seconds
  (`verification/native/windows/recovery-review.json`). A new bounded recursive
  preflight checks local layer dependencies and rejects remote texture/asset
  paths before stage composition. Nine Linux asset/document tests pass
  (`verification/native/linux/asset-policy-review.json`). Packaged/custom USD
  formats remain explicitly unsupported; concurrent external asset replacement
  and broader asset-resolution coverage are not claimed solved.
  That cleanup recovered approximately 3.90 GB of actual volume space: completed
  installer staging/downloads and supported pip, uv and npm cache cleaning.
  C: now has about 11.07 GB (10.31 GiB) free. Installed SDKs, environments,
  checkouts and Windows repair data were preserved. Details and recovery limits
  are in `verification/native/windows/cache-cleanup.json`. The full retained
  application install still needs a fresh peak-plus-reserve check; it has not run.
  The exact qualified framework wheel is also installed non-editably in a new
  isolated Windows review environment; its dependency check and CLI startup pass
  (`verification/native/windows/framework-review.json`). All ten native wheel
  archives transferred successfully. The qualified framework's disposable offline
  install then passed: 10,974 installed files, independent revalidation and cleanup
  (`verification/native/windows/qualified-install-review.json`). The staging
  directories are gone and C: has 9.28 GB free after the check. No application copy
  was retained and the existing SDK environment was not changed. This is dependency
  installation evidence, not application admission or native/UI acceptance.
- **Status:** Linux SSH connectivity and the Literate AI hardware probe now pass
  on the user-assigned Ubuntu 26.04 NVIDIA worker. The worker has an RTX 5090,
  driver 595.84, and 32607 MiB GPU memory. Its assignment is private operator
  configuration, outside this repository. Windows SSH now passes and reports an
  NVIDIA L40 with driver 595.97. The Linux native probe rendered the original USD
  fixture, simulated the sphere from 0.80 m to 0.099993 m on CUDA, published its
  pose through OVStage, and rendered the changed frame. Images were visually
  inspected. Evidence is retained in `verification/native/linux/` and the
  independent verifier is `verification/native_probe.py`.
  Windows SDK installation initially failed for insufficient disk space. Authorized
  cleanup removed old NVIDIA installer extracts, the disposable uv cache, and
  downloaded CUDA/Vulkan installers; supported Windows component cleanup completed.
  Free space increased from 1.87 GB to 12.12 GB, with driver 595.97 still healthy.
  Hibernation, personal files and installed SDKs were preserved. Deleted caches and
  installers are recoverable by download, not from the recycle bin. No Windows frame pass is
  claimed. In progress: resolve supported Python dependency admission so native
  implementation can be repaired and verified through the authorized lifecycle.
  The application will use a Qt desktop shell with native scene work off the UI
  thread. The installed Standard lifecycle currently rejects generated Python
  dependency lock manifests; investigate its supported native dependency route
  before admitting the desktop Component, without weakening that gate.
  The [upstream issue and local draft](python-lock-gap.md) record the portable dependency
  limitation; the operator has authorized issue filing and a reviewable fix in a
  project-local parent checkout, without merging or publishing.
  Issue #1 is filed. Unpublished parent commit `dcacfbc2` now supplies manifest/lock
  reconciliation, complete wheel verification, owned staging, selected-interpreter
  observation, a fixed offline installer, independent command-wrapper projection,
  installed-payload/graph verification, retained artifact evidence, and fresh
  source-to-resolved dependency admission. All 175 focused tests pass with the exact
  installer fixture, including real installation, repeated-install identity,
  tampering/collision rejection and cleanup. Another 22 application-port and
  CycloneDX tests pass. Lint and formatting pass. Resolution now rechecks retained
  payloads and target identity and verifies source imports against installed
  modules; a distribution name or ambient package does not establish that proof.
  An explicit Python wheel command profile now binds interpreter, packaging
  Flavor, manifest and lock into command/toolchain authority. Isolated build and
  launch commands preserve dependency-free Python behavior. A further 148-test
  profile/schema/runtime/lifecycle run passes with two existing platform skips;
  actual local launch imports retained wheel packages and ignores injected ambient
  startup paths. Linux/Windows profile-description checks are not native GPU runs.
  Offline Standard build/cache dispatch now connects those commands, the installer
  and retained-payload resolver. An explicit operator wheel directory supplies
  untrusted bytes; exact lock verification, authorization and external artifact
  checkpoints remain required. Test/execute preparation rejects changed application
  or dependency files. Fresh local regression: 374 tests, 372 passed and two existing
  platform skips; a separate 50-test rebuild/CLI/qualification run passes.
  A hashed export of parent commit `4853ee67` also passes all 209 focused dependency,
  retained-runtime and Standard lifecycle tests on Linux x86-64 with Python 3.11.16,
  without skips, using an isolated Make-managed environment. The existing SDK
  environment and installed Litai remain unchanged. This is native-platform
  framework evidence, not native SDK or graphical application acceptance.
  Windows testing of the same parent revision has now completed: 209 tests in
  225.706 seconds, with five failures, 40 errors and two skips. It is not qualified.
  Diagnosis identifies a Windows metadata defect in the installed-tree observer:
  `DirEntry.stat()` supplies zero file identity/link-count fields, while
  `Path.lstat()` and opened-file `fstat()` supply matching real identity and a
  single link. Use full metadata rather than relaxing custody checks. The wheel
  profile fixture also writes platform-default CRLF where authoring requires LF;
  existing symlink fixtures additionally encounter disabled Windows link types.
  Next for this regression: repair metadata observation and explicit LF fixture
  writes with targeted tests, then classify remaining failures independently.
  Parent source remains unchanged while its exact-commit broad gate is running.
  A reviewable two-change draft is retained at
  `verification/windows-wheel-portability.patch` and applied only to the disposable
  Windows source snapshot. It uses full `lstat()` metadata and explicit LF fixture
  writes. The independent regression in `verification/test_windows_wheel_metadata.py`
  reproduces the metadata failure on the unchanged parent. Both regressions pass
  on patched Windows, including rejection of an actual hardlinked payload.
  The four affected Windows test modules now pass: 48 tests in 374.448 seconds,
  with one platform skip. The broad local gate finished 5,007 tests in 5,312.101
  seconds with one failure and 29 skips: the self-hosting driver content identity
  is stale. After that run ended, the two fixes and both metadata regressions were
  integrated into the local parent worktree. All 50 focused local tests pass in
  53.557 seconds, without skips; changed-file lint, format and diff checks pass.
  review/refresh of the parent self-hosting identity and renewed qualification
  remain required. No installed LeRTX lifecycle rebind or full-suite pass is claimed.
  The parent review helper subsequently refreshed its self-hosting driver identity
  after reviewing the source changes, and all 12 version-authority tests pass.
  The Windows repairs, regressions and parent identity review are committed locally
  as `dcacfbc2`, without push or installation. The fresh broad local gate now passes
  against that clean commit: 5,148 tests in 5,353.028 seconds, 29 skips, and
  `make python-check` exits zero. The parent worktree remains clean at the tested
  revision. This qualifies the local Python gate only; it does not establish
  Windows qualification, project lifecycle binding, or desktop acceptance.
  The remaining Windows modules completed 161 tests in
  183.146 seconds with four errors and one skip. All Python-wheel/runtime/evidence
  modules passed; the errors are existing Mach-O/npm fixtures encountering
  WinError 1463 when following symbolic links. Combined patched Windows results:
  203 passed, two platform skips, four errors. A read-only policy query was
  incomplete; no host policy change, added skip or full Windows qualification
  is claimed. Those errors remain separate from the repaired wheel metadata path.
  Git blob comparison confirms both the observer and its four failing test cases
  are byte-identical between parent baseline `143c2689` and draft `dcacfbc2`.
  These are inherited failures, not newly changed wheel-observer behavior; they
  remain failed evidence rather than being suppressed.
  An additional Linux 50-test rebuild/CLI/qualification run is not accepted:
  27 CLI cases first lacked exact origin in the source-only export. Retesting a
  framework wheel built from that export with exact origin/revision metadata
  reaches lineage resolution, but the worker cannot resolve the private origin.
  Only the disposable Make-managed review environment was changed. No alternate
  origin or networking override was used; this prerequisite remains open.
  Next: complete framework qualification, then validate the actual native wheel
  closure and production rebuild/receipt chain. Automatic network acquisition is
  unimplemented but is not required for verified offline provisioning.
  The ten pinned Linux application wheel archives were checked by
  `verification/native_wheels.py`; nine pass. Exact filenames, hashes, dependency
  metadata and results are retained in `verification/native/linux/wheel-archives.json`.
  The USD 25.11 wheel fails because WHEEL contains conflicting duplicate
  Root-Is-Purelib fields (`true` and `False`). The Linux CPython 3.11 wheels for
  upstream 26.3 and 26.8 have the same defect; a version bump does not resolve it.
  The operator now authorizes a separately hashed, reproducible metadata-only
  repair preserving all library bytes. Preparation now passes: the exact original
  hash is bound, only WHEEL and its RECORD entry change, and every other member
  is byte-identical. Two runs produce the same repaired archive; three regression
  tests pass, including tampered-input and overwrite rejection. The unchanged
  strict validator accepts all 122 payload members. The repair script is
  `verification/repair_usd_wheel.py`; hashes and per-member evidence are retained
  in `verification/native/linux/usd-metadata-repair.json`. Original and repaired
  archives remain separate under `_build/usd-metadata-repair/run-1/`. Nothing is
  installed on a GPU worker, and no application admission is claimed.
  The operator also authorizes using the qualified local framework through a
  reviewed project-local lifecycle rebind, without global installation or publication.
  No validator check will be relaxed. RTX/OVStage binary wheels are provisioned from
  NVIDIA's index; the PyPI RTX release is a wheel-stub source wrapper.
  Archive integrity alone is not installed-payload or desktop acceptance.
  The pinned Windows CPython 3.12 USD wheel was checked independently and does
  not share the Linux metadata defect. Its published SHA-256 matches, all 131
  archive payload members pass verification, and WHEEL has one Root-Is-Purelib
  field. `verification/native/windows/usd-wheel.json` records this unmodified
  archive evidence. After checking worker headroom, the unmodified wheel was
  installed only into the disposable Windows SDK environment. The original
  USD-authoring/render/physics probe now passes there: USD creates/saves the
  fixture, OVStage loads it, RTX renders both poses, and Newton settles the sphere
  from 0.80 m to 0.099993 m. Cleanup completes; GPU memory returns to 122 MiB.
  Retained artifacts in `verification/native/windows/authored/` match reported
  hashes and were visually inspected. Both frame hashes and the authored USD
  hash equal the earlier fixed-fixture probe's outputs. C: retains about 8.7 GiB
  free, still under warning. No Linux wheel repair is implied, and this does not
  admit the complete Windows dependency closure or verify application UI editing.
  All ten exact Windows CPython 3.12 application wheels have now been acquired on
  the development host and pass archive verification. Their complete dependency
  graph also passes against the independently observed Windows SDK interpreter.
  `verification/native/windows/wheel-archives.json` records hashes, payload sizes,
  dependency edges and the captured-target identity. Negative checks reject wrong
  platform tags, missing transitive packages, incompatible Qt edges and failed
  archive evidence. Archives total 1,701,056,243 bytes; expanded payload totals
  3,430,953,557 bytes, before installer staging and retained artifact copies.
  RTX/OVStage downloads came from NVIDIA's binary index; other wheels came from
  PyPI. This is not installed-closure or application admission. Windows headroom
  must be checked against the complete staging footprint before dispatch.
  The Windows worker exposes only one writable local volume; its other drive is
  optical. C: has approximately 9.34 GB free. The current offline installer plus
  retained-artifact flow needs roughly 10.26 GB for two archive/payload copies,
  before reserve and overhead. Do not dispatch that full installation under
  current headroom. Bounded investigation found only 9.9 MB of pip cache and
  about 62.6 MB of copied framework provisioning archives; NVIDIA downloader and
  uv caches were absent. These do not close the staging deficit. Unknown updater
  directories are not established cleanup candidates. No SDK, environment,
  personal data or unknown updater files have been deleted.
  The operator authorizes using the qualified patched local framework through a
  reviewed project lifecycle rebind without a global installation or publication.
  The non-editable local installation is complete at `_build/local-litai/venv`.
  The reviewed plan `verification/local-litai-rebind-plan.json` was applied using
  the supported CLI. A subsequent plan reports no changes required. The installed
  distribution binds exact commit `dcacfbc243bb6c6c30c7e95ab079fa8ede5bf728`, and
  dependency consistency passes. Global Litai and the clean parent checkout are
  unchanged. The framework wheel SHA-256 is
  `1f2d4880c2fd9319591aa4610a8a2e86c24d8d3cfd13538426c224c55ae3cdcd`.
  No application acceptance is implied by the binding transition; current receipts
  remain stale until a real rebuild. Next: select the desktop wheel-packaging
  Flavor and validate the complete native dependency installation.
  The project-owned `desktop-wheels` packaging Flavor now selects
  `standard-python-wheel-command-profile`, the Python toolchain,
  `source/requirements.txt` and adjacent `source/python-wheel-lock.json`.
  Desktop selectors omit Make, and the language specification now describes the
  retained-dependency tree export. Desktop lock update and plan pass, selecting
  desktop-python and desktop-wheels with no build-system profile. The harness
  and sample lock diffs contain no semantic changes; only their catalog audit
  needs refresh after adding a Flavor. Native target installation and runtime
  admission remain unverified. The repaired Linux ten-wheel closure now passes
  archive and actual-interpreter compatibility checks through the qualified
  framework; evidence is `verification/native/linux/repaired-wheel-archives.json`
  and `python-target.json`. A disposable offline installation reaches independent
  payload observation, which rejects shared paths across the three PySide6
  wheels. Read-only archive comparison finds 62 shared paths (124 comparison
  pairs), all byte-identical, including type stubs and package initialization.
  `verification/native/linux/install-review.json` records the failure and
  `verification/native_install.py` reproduces the installer boundary. Temporary
  installation/staging cleanup completes; the existing SDK environment is unchanged.
  No validator relaxation, Qt repack, or application execution occurred.
  Next: review parent support for provably identical shared wheel payloads while
  retaining fail-closed rejection of conflicting bytes and ambiguous ownership.
  A local parent follow-up now validates each identical ordinary file against
  every owner's locked bytes and installed RECORD and binds all owners into tree
  evidence. Metadata, relocated payloads and generated-script collisions remain
  rejected. All 62 focused tests pass without skips. With only this observer
  patched in the disposable Linux review environment, the actual ten-package
  closure passes offline installation, independent observation of 11,105 files,
  revalidation and cleanup. Evidence is `shared-install-review.json` beside the
  original failure report. The observer source SHA-256 tested there is
  `89acf1c3bedb2239f917f8520e2a4c502005722090f39e7b73ff354478c466d2`.
  The project-bound framework remains unchanged until the follow-up has fresh
  qualification and a reviewed binding transition. No desktop source was run.
  The follow-up is now local commit `0449e10c3a487ae21c4f606d69ee416dd853056f`.
  Driver identity was reviewed/refreshed and all 12 version-authority tests pass.
  The full Python gate passed against that clean, frozen revision: 5,155 tests
  in 5,177.128 seconds, 29 skips, command exit zero. The parent worktree remains
  clean at the tested commit. `verification/shared-wheel-review.json` separates this qualification
  from the prior successful full run at `dcacfbc2`; neither result is desktop
  application acceptance. Nothing was pushed or globally installed.
  The follow-up also passes 26 focused Windows tests in 31.204 seconds without
  skips, using the existing disposable review snapshot plus the exact observer
  and test changes. Coverage includes shared-payload offline install, conflicting
  bytes, script collisions and cleanup. This is not full Windows qualification.
  Windows free space has fallen to about 6.7 GiB (below 2%); native installation
  remains held. A fresh bounded cache investigation finds only about 9.9 MB of
  pip cache and no previously identified NVIDIA/uv cache candidates. No further
  deletion was performed. The small fixture tests fit without new dependencies.
  After the full gate passed, a non-editable framework wheel was built from exact
  clean commit `0449e10c` and installed in `_build/local-litai-0449/venv`.
  Dependency consistency passes. The reviewed `shared-wheel-rebind-plan.json`
  was applied through the supported CLI, changing only framework/runner identities
  while preserving required evidence and policy. A fresh plan reports no change
  required. The previous environment is retained; global Litai is unchanged.
  Application receipts remain stale until a fresh desktop rebuild and acceptance.
  A host plan is not a Linux or Windows native acceptance result.
  The existing Windows SDK interpreter was independently observed through the
  parent's isolated target probe; `verification/native/windows/python-target.json`
  retains its marker environment, compatible wheel tags and target/probe
  identities. `verification/native_target.py` runs the observation without
  importing SDK packages. This is interpreter compatibility evidence only, not
  installed-closure or application admission.
  Linux Qt display readiness also passes: Qt 6.10.2 using xcb on a temporary
  isolated Xvfb display creates, captures and closes a visible window twice.
  `verification/native/linux/qt-platform.json` records this prerequisite probe;
  it is not the generated LeRTX window or UI acceptance.
  No gate has been weakened and the installed Litai distribution is unchanged.
  Full framework qualification remains open; historical interrupted broad-suite
  results are retained in `verification/python-lock-review.json`, not claimed as a pass.
  Windows IPv4 SSH subsequently recovered. Fresh checks identify the L40 and
  driver 595.97, ample memory and initially 12.1 GiB free on C: (about 3%, a disk
  warning). Task cache inspection found no cache to reclaim. Exact binary
  OVRTX 0.5.0.377615 and OVStage 0.2.0.377349 installed without caching into the
  disposable Python 3.12 probe environment; the rejected USD wheel was not
  installed. Two renderer/stage startup, attach/detach and destruction cycles
  now pass. The subsequent fixed-fixture SDK probe also passes twice on Windows:
  the sphere falls from 0.80 m to 0.099993 m on CUDA and its published OVStage pose
  changes the RTX frame (mean difference 2.11246). Images were visually inspected;
  repeat frame hashes are identical and both runs complete cleanup. Evidence is
  retained in `verification/native/windows/`; the independent probe is
  `verification/native_fixture_probe.py`. It verifies the exact retained fixture
  hash and deliberately does not claim USD authoring, scene import semantics or
  application UI behavior. GPU memory returned to 122 MiB. C: retains about
  9.0 GiB free, under disk warning. No desktop application acceptance is claimed.
  Upstream native-SDK PR #438 is an unmerged integration stack, not an installed
  Python-wheel admission solution. No upstream branches were switched or merged.
  `components/desktop` and `flavors/desktop-python` now define the native window,
  USD editing, simulation, settings and transport behavior. Lock and plan pass
  with the native Python Flavor and without the standard-library pip Flavor.
  The first source candidate was rejected during review: inert toolbar/transport,
  missing frame delivery, and a nonexistent Newton API. Its generation was stopped
  before admission. The Codex-backed replacement used the explicit verified
  native API contract and a portable settings-validation entry point; no hand-written
  replacement application or weakened acceptance is being substituted.
  The second, Codex-backed candidate was also rejected before admission and its
  generation stopped. `verification/desktop-review.json` binds the reviewed files
  by hash and records missing editable settings, USD save/edit handlers, incorrect
  SDK calls, empty pose publication, and placeholder native/UI tests. The full
  requirements were present in the generation request. Do not run this candidate
  as an application or launch another blind full-app generation. Subsequent
  implementation should use bounded native/scene/UI repairs with real acceptance
  at each boundary after dependency admission is unblocked.
  Read-only inspection of the parent's candidate-repair adapter confirms that
  its bounded retries apply only to selected BUILD/TEST failures and always
  request a complete fresh replacement without prior candidate files. It does
  not provide a file-scoped repair path for this source-review rejection. Do not
  misrepresent that retry mechanism as supporting surgical desktop repairs or
  bypass admission by executing the rejected source.
  All three locks and documentation authority pass current verification; the
  project receipt remains stale and must not be replaced by a harness-only pass
  presented as desktop acceptance.
- **SDK preflight:** An isolated Python 3.11 environment successfully installed
  OVRTX 0.5.0.377615, OVStage 0.2.0.377349, Newton 1.6.0, Warp 1.17.0, and NumPy
  2.4.6 from the upstream package distributions. Installation is not proof of
  rendering or physics execution. OVRTX renderer creation, OVStage attach/detach,
  orderly destruction, and Warp CUDA device initialization subsequently passed
  against these installed versions. No rendered frame or Newton step is claimed
  by that initialization probe alone. The subsequent native probe supplies frame
  and physics evidence, not application UI acceptance. Runtime inference is specified under
  CONFIG-001; the remote coding CLI is separate development tooling.
- **Implementation:**
  - [ ] Resolve exact OVRTX, OVStage, and Newton packages and their supported ABI and GPU target.
  - [ ] Create the application window, shared scene, render loop, physics stepping, and play/pause/reset controls from specifications.
  - [ ] Implement open/save USD, scene hierarchy, selection, and transform inspection.
- **Evidence:**
  - [x] Real GPU frames show a known USD fixture and Newton-driven body movement.
  - [ ] Pause stops physics, reset restores authored state, and repeated open/close releases resources.
  - [ ] Linux and Windows NVIDIA runs record SDK versions, driver, GPU, frame artifacts, and current tests.

### [ ] CONFIG-001 — Application settings and Astra inference configuration

- **Priority:** P0
- **Owner:** application configuration and inference adapter
- **Current repair:** settings were persisted and the UI profile changed before
  native rebuild completed. Make native application and atomic persistence one
  worker-owned transaction: retain the prior UI/file profile until success,
  restore the old native profile after recoverable apply/save failure, and
  fail visibly if restoration itself fails. Non-native settings must not reset
  the simulation. Add deterministic failure tests plus actual GPU resize/edit
  preservation coverage. Successful status updates must clear stale prior error
  messages; frame delivery alone must not conceal an active error.
  Implemented and verified in the full 152-test matrix: Linux 92.753 seconds,
  Windows 283.305 seconds, identical 54-file source snapshot. The native test
  changes real framebuffer dimensions while retaining dirty USD edits, injects
  persistence failure, and renders again with the restored prior settings.
  UI tests verify delayed profile adoption and failure preservation. Evidence:
  `verification/settings-transaction-review.json`. The stale status message is
  now cleared on successful operation; normal frame delivery retains an active
  error. Next: close the fresh-dialog blank-key and photo failure-path coverage
  gaps identified in `verification/milestone-acceptance-audit.md`, while retained
  source admission approval remains pending. Ten baseline EOF whitespace
  findings remain explicit review cleanup; no lifecycle acceptance is claimed.
  In progress: direct fresh-dialog blank-key test with file reads forbidden,
  plus actual native-window photo failures (malformed/incomplete/auth/timeout)
  asserting unchanged authored document, dirty state and active rendering.
  These 14 focused tests now pass on Linux (34.418 seconds) and Windows
  (113.283 seconds). `verification/photo-failure-review.json` binds the current
  source snapshot. Only tests changed from the preceding full 152-test snapshot;
  this is not a claim of a new full matrix or current lifecycle receipt.
  Final verification passed: removed the ten trailing-blank-line review findings
  without behavioral changes. All 154 tests pass on Linux (117.477 seconds) and
  Windows (325.596 seconds), with identical source hashes on both workers and
  locally. See `verification/final-native-suite-review.json`.
  Retained-source admission remains the same unresolved approval
  boundary; do not replace the receipt or invent a smaller completion claim.
- **Direction:** Use the NVIDIA Responses endpoint and exact Astra model, permit the operator key for development, and ship a good settings UI with a blank API-key default.
- **Conclusion:** Keep inference configuration separate from the coding CLI, publish nonsecret defaults and a UI contract, and test the configured endpoint without exporting the development credential.
- **Review follow-up:** malformed bracketed hosts currently escape URL validation
  as exceptions, and percent-encoded credential query names bypass its marker
  check. Repair validation to return field errors without retaining or displaying
  the endpoint value, then exercise the same cases through the settings UI.
  The repair now passes 21 focused configuration, Qt settings and CLI tests on
  both platforms (Linux 1.176 seconds; Windows 5.147 seconds), recorded in
  `verification/endpoint-validation-review.json`. No live inference request or
  development credential was used.
- **Depends on:** HARNESS-001
- **Implementation:**
  - [x] Record endpoint, model, token limit, credential handling, and configuration-panel behavior as application authority.
  - [ ] Implement editable LLM and application settings in the graphical application.
  - [ ] Implement Responses transport with bounded requests and sanitized failures.
- **Evidence:**
  - [x] An authorized live text request succeeds against the exact configured model.
  - [ ] A fresh settings panel shows a blank key and never reads the developer key file automatically.
  - [ ] Settings save/reload, validation, connection testing, cancellation, and secret handling pass on Linux and Windows.

- **Result:** The [configuration contract](../architecture/configuration.md) and
  nonsecret defaults preserve the user-supplied API/model and blank credential.
  The development-only request returned HTTP 200, completed output, and the exact
  `azure/openai/gpt-6-astra` model (392 total tokens). The key was read directly
  into request memory, not copied into the project or printed. Next: implement
  the settings panel and transport within the RENDER-001 application shell.

### [ ] TWIN-001 — Milestone three: Astra photo-to-USD reconstruction

- **Photo quality follow-up:** The operator turtle photograph became a blue block. The high-reasoning OpenRouter preset now produces a recognizable low-poly turtle from that exact input, verified in native Windows RTX. The final request took 301.43 seconds and reported $1.06554 for 29 parts (27 meshes). The dialog explains cost/latency, offers coarse/configured alternatives, shows geometry counts and lets the operator choose the initial view. See `verification/turtle-photo-review.json`. This qualifies an approximate colored-mesh improvement, not faithful textured reconstruction or measured collision geometry.

- **OpenRouter trial:** Operator requested GPT-5 Mini after NVIDIA throttling. Two authenticated image requests completed but emitted nested mesh indices, rejected by the local flat-index contract. Add strict JSON-schema output for the OpenRouter Responses route, preserve independent scene validation, verify a live synthetic-image request through USD construction, and configure the Windows deployment with its own encrypted provider credential. Live structured-output request passed: three objects, 15.46 seconds, USD 0.003351. Windows passes 18 photo/UI/reconstruction tests and constructs the returned USD stage. Visible RTX validation passed on Windows with the imported cube, sphere and platform and the unverified-draft warning. No operator photo or robot actuation is part of this trial.

- **Current usability repair:** The visible Windows dialog rejects upload because the session key is missing, but the small status message is easily missed. Add an inline password field, preflight feedback and visible in-flight progress while preserving the chosen photo; verify missing-key, success and failure paths without transmitting the operator photo during tests. Windows Qt verification passes missing-key, inline-key success, authentication failure/retry and cancellation cases. Live provider acceptance still requires the operator credential.

- **Scope clarification:** The operator explicitly selected Astra photo-to-USD
  reconstruction as milestone three. USB discovery and read-only SO-101
  synchronization remain follow-on product work, not milestone-three acceptance
  gates. Preserve the partially written discovery code without treating it as
  verified. Next: complete current photo-workflow regression and acceptance
  evidence, including the native startup repair, on both GPU platforms.
  Current regression follow-up: assert that adopting a photo draft produces a
  changed, nonuniform RTX frame in the visible viewport, and show loading rather
  than stale ready status while its native scene is being constructed.
  The 49-file snapshot now passes 134 tests on Linux (109.309 seconds) and
  Windows (283.948 seconds), including fresh-process startup and retained device
  panel tests. `verification/current-native-suite-review.json` records exact
  scope, source identity and deployment-observation limitations. This precedes
  the stronger photo-frame assertion and loading-label follow-up. Authority and
  all three locks pass; the lifecycle receipt remains stale. No physical-device
  or distributable-installation acceptance is claimed.

- **Design:** [Digital-twin implementation contract](../architecture/digital-twin.md).
  Follow-on work, paused: USB serial discovery and explicit leader/follower role assignment.
  Read-only inventory found no USB serial robot candidates on either GPU worker;
  only legacy non-USB serial ports were reported. The development Mac likewise
  exposes no USB serial candidate. The reviewed LeRobot revision requires Python
  3.12+ and NumPy below 2.3, incompatible with the Linux renderer's pinned Python
  3.11 and NumPy 2.4.6. Use a separately qualified LeRobot helper environment;
  do not weaken metadata validation or install it into the renderer environment.
  Qt's existing serial metadata API works on Linux and needs no added dependency.
  Live synthetic-image inference succeeded with the exact configured NVIDIA
  model and a development-only 4096-token budget (`verification/live-photo-response.json`).
  A standalone render probe crashed in native USD parsing when OVRTX initialized
  first, both with and without Xvfb; importing OpenUSD first rendered the same
  response successfully and closed the worker. Repair native import order and
  add a fresh-process existing-file launch regression; do not hide this behind
  in-process suites that already imported USD during earlier tests.
  Photo workflow now passes the 122-test matrix on both platforms, including
  actual photo-dialog preview/upload, injected inference, native draft adoption,
  Save As and reopen with a persistent warning. Live model output renders as a
  three-object draft when USD is loaded first; the retained image has been
  visually inspected. Evidence: `verification/photo-workflow-review.json`.
  This matrix predates the startup import-order repair; its fresh-process
  regression now passes on Linux (16.923 seconds) and Windows (46.016 seconds).
  The unmodified standalone render probe also succeeds using the repaired worker,
  producing the same image and USD hashes as the controlled USD-first run
  (`verification/native-import-order-review.json`). The root SDK ABI defect is
  not attributed beyond demonstrated import-order sensitivity. Measurement and physical telemetry remain
  unimplemented, and the project lifecycle receipt remains stale.
  LeRobot read-only API review is recorded in the design contract. Physical USB
  attachment location and calibration availability have been requested. No
  serial device has been opened and no motor registers have been written.
  Implemented bounded scene JSON validation and local USD boxes, spheres and
  triangle meshes with persistent source hash/model, uncertainty and unverified
  provenance. Linux passes all 113 tests, including actual RTX draft rendering,
  edit/save/reopen and explicit disabled physics for scenes without rigid bodies
  (`verification/native/linux/reconstruction-review.json`). Windows also passes
  all 113 tests in 199.608 seconds on the identical source snapshot
  (`verification/native/windows/reconstruction-review.json`). Next implementation: explicit photo preview/upload, cancellable
  Responses inference, and native-worker draft adoption; no live reconstruction
  or user-facing photo workflow is claimed by these importer tests.
  Desktop specification lock and plan pass; dependent catalog audits were
  refreshed without changing harness/sample semantic locks. Authority and locks
  pass `litai verify`; the project receipt remains stale. Peer-work survey still
  cannot resolve HEAD in the unborn repository, and no Git cleanup was performed.

- **Priority:** P0
- **Owner:** desktop photo reconstruction and USD workspace
- **Direction:** Complete milestone three as Astra photo-to-USD reconstruction.
- **Conclusion:** Deliver explicit photo upload, configured Astra inference,
  validated local USD construction, editing and save/reopen. Reconstructions
  remain unverified drafts; physical telemetry and measured robot registration
  are follow-on work. No robot actuation, torque enable, calibration writes, or
  autonomous movement is authorized.
- **Depends on:** RENDER-001, CONFIG-001
- **Implementation:**
  - [x] Specify bounded photo-to-scene interchange, preview, persistent unverified metric status, editing and failure handling.
  - [x] Implement configurable Responses image requests and validated local USD construction with no executable or remote asset imports.
- **Evidence:**
  - [x] Linux and Windows UI tests cover reconstruction success, malformed output, cancellation and draft verification state.
  - [x] Live Astra output becomes an editable, saveable USD draft rendered by RTX; record source and output identities without secrets.
- **Functional evidence:** `verification/photo-failure-review.json` adds the
  actual UI failure-preservation checks on both platforms to the existing
  success, cancellation and unverified-draft coverage. The retained live Astra
  output also passes `verification/render_live_photo.py --verify-edit`: original
  frame/USD hashes reproduce, a 0.125 m ground-object translation survives
  save/reopen, the edited USD and rendered frame hashes change, the draft stays
  unverified and the worker closes. Artifacts and exact hashes are in
  `verification/native/linux/live-edit-review/`. No new inference call or
  credential access was needed. TWIN-001's feature requirements are verified;
  final milestone acceptance still depends on RENDER-001/CONFIG-001 and honest
  retained-application lifecycle evidence.
- **Separate follow-on:** ROBOT-001 owns all mock and physical SO-101 work.
  Its unfinished gates are not milestone-three requirements. TWIN-001 remains
  open pending its own final evidence and prerequisite application acceptance.

### [ ] ROBOT-001 — SO-101 USB control and physical twin

- **Guided setup direction:** Build in-window USB identification, role assignment, six-motor checks, explicit torque release, LeRobot-compatible reference homing and individual range capture, live provisional mirroring with direction verification, and paired calibration/binding export. The new calibration request authorizes scoped persistent homing/range writes after the wizard confirmation; ordinary hardware control still cannot write EEPROM. Back up original registers before writes, restore on cancellation/failure where possible, and report unconfirmed restoration. Verify with SDK emulator, Qt interaction and bounded Windows rendering; real-arm acceptance remains pending.

- **Priority:** P1
- **Owner:** desktop device and LeRobot adapters
- **Direction:** Build robot support and a hardware-free mock; the physical devices are not currently attached.
- **Conclusion:** Preserve explicit mock identity and read-only connection defaults. The later operator direction now authorizes bounded manual writes and measured virtual bindings; see the current ROBOT-001 checkpoint above. Physical acceptance remains pending.
- **Depends on:** RENDER-001
- **Implementation:**
  - [x] Provide isolated simulated leader/follower streams with connection, pose, freeze and stale controls.
  - [x] Implement explicit discovery/roles, the pinned Feetech SDK, calibration import and separately armed manual controls.
  - [x] Add the modeless six-joint calibration wizard, durable register backup/rollback, verified torque-off writes and provisional native preview. SDK/Qt/native evidence is in `verification/guided-setup-review.json`; assembled arms require motor IDs 1–6 at 1 Mbps.
  - [ ] Qualify homing, travel, direction and cancellation on the physical leader and follower before treating this as hardware acceptance.
  - [x] Publish calibrated observations through SO-101 kinematics to the native viewport without conflicting Newton control or automatic motor writes.
- **Evidence:**
  - [x] Exercise mock states, sample validation and cleanup on Linux and Windows.
  - [ ] Verify real adapter ambiguity, persistence, reconnect, joint units and absence of actuator writes.
  - [ ] Verify physical leader/follower motion against rendered poses when devices and calibration become available.
- **Evidence and boundary:** The initial mock panel and read-only sample boundary
  pass 18 focused tests on both GPU platforms (Linux 17.539 seconds; Windows
  71.334 seconds), plus subsequent full-suite regression. Evidence is
  `verification/mock-telemetry-review.json`. Neither serial ports nor real
  motor registers were accessed. The operator confirms both devices are
  elsewhere; physical attachment is not a blocker to building support.
  This is historical mock evidence. Current software-control evidence is in
  `verification/usb-control-review.json`; the next gate is the actual attached
  arms. Mock identities never become persistent hardware identities.

### [x] CHECKPOINT-001 — Publish the current LeRTX development checkpoint

- **Priority:** P0
- **Owner:** project roadmap and repository
- **Direction:** Update all open roadmap items, then commit and push current work.
- **Conclusion:** Publish a reviewed development snapshot without claiming application admission or release; exclude private worker state and build outputs.
- **Depends on:** none
- **Implementation:**
  - [x] Reconcile open implementation, qualification, packaging and physical-twin work.
  - [x] Audit and commit the retained source, specifications, tests and nonsecret evidence.
  - [x] Push to the operator-selected repository and verify remote commit identity.
- **Evidence:**
  - [x] Authority and locks pass; stale acceptance receipt remains explicit.
  - [x] Staged files contain no credentials, private worker assignments or build caches.
  - [x] Local and remote checkpoint commit IDs match.
- **Checkpoint evidence:** 34 portable worker/configuration/transport/simulation/
  mapping tests pass in 0.121 seconds. No application modules changed during this
  roadmap/publication pass. The staged text and original source archive were
  scanned for credential patterns; private worker paths were removed from the
  renderer report. Native evidence bytes retain their original line endings to
  preserve artifact hashes. Parent checkouts, transient locks and build outputs
  are excluded. Local authority and all three locks pass; the receipt remains
  stale. The private `NVIDIA-dev/LeRTX` repository now contains the development
  checkpoint. Initial publication was verified with matching local and remote
  commit `19f71e7201bf827eadbb6e56a29f116810a4785b`. No pre-existing branch or
  review existed for the initial push. Project CI and public-release review
  remain open above; publication does not constitute application acceptance.

### [x] PORT-001 — Complete the prototype across Windows and Linux architectures

- **Priority:** P0
- **Owner:** Desktop Component, native Flavors, packaging and acceptance
- **Direction:** Finish the prototype for Windows 11, Linux x86-64 and Linux ARM64; deploy and test on an additional Omarchy GPU worker over SSH.
- **Conclusion:** Qualify actual rendering, editing, physics, settings and reconstruction on each target; complete reproducible setup and delivery, with physical motor control remaining separately gated.
- **Depends on:** RENDER-001
- **Implementation:**
  - [x] Resolve and lock real native dependencies for Linux ARM64 alongside Windows 11 and Linux x86-64.
  - [x] Implement portable installation, launch and diagnostics with actionable dependency and platform errors.
  - [x] Complete outstanding prototype functionality and application acceptance without substituting mock rendering.
  - [x] Copy the project into the additional Omarchy worker source directory and provision an isolated runtime without overwriting unrelated work.
- **Evidence:**
  - [x] Current full application suites and real rendered Qt interaction on Windows 11, Linux x86-64, Linux ARM64 and Omarchy.
  - [x] Verify delivered setup, launch, reload, physics, camera, editing, save/reopen, photo workflow, shutdown and installation lifecycle within the agreed platform coverage.
  - [x] Refresh dependency evidence and project acceptance receipt; retain exact source identities and platform evidence.
- **Current evidence:** `verification/prototype-platform-review.json` binds
  matching source/test identities observed on all four workers. Full suites:
  ARM64 211.522 seconds, Linux x86-64 83.834 seconds, native Wayland Omarchy
  108.239 seconds, isolated Windows 371.490 seconds; each passes 160 tests.
  Setup warmup produces actual nonuniform RTX pixels and cleans up. First-frame
  and process deadlines in the application tests remain unchanged. The ARM64
  archive and isolated-install reviews pass for all ten distributions and
  11,212 installed files. The admitted ARM64 artifact then passes all 160 native
  tests in 108.157 seconds against its sealed SDK closure; all 30 declared
  contract tests and independent acceptance pass, with a current verifier-owned
  receipt. The delivered ZIP passes fresh Omarchy setup, upgrade and all 160
  tests in 131.481 seconds. Windows Start Menu launch produces a real frame in
  17.844 seconds and closes cleanly. No physical serial device or motor register
  was accessed.
- **Accepted coverage:** The operator accepts limited Windows testing and considers
  this prototype complete when Linux is good. Windows clean-download installation
  was initially unverified because of worker capacity; PORT-002 below closes that
  gap on another worker. The original isolated runtime, idempotent
  setup, complete native suite and actual shortcut launch pass. This is not a
  blocker to PORT-001 under that explicit direction.
- **Delivery boundary:** The tested deliverable is the reproducible source/setup
  ZIP. The separate formal native-wheel command rejects the custom
  `desktop-wheels` provider name. Its naming experiment was removed; no framework
  validator or native dependency policy was weakened. Native registry packaging
  and production release qualification remain separate RENDER-001 release work.


### [x] PORT-002 — Qualify a fresh Windows 11 installation

- **Direction:** Prioritize the newly supplied Windows boot of the additional GPU
  laptop; install required dependencies and test the prototype before the operator
  switches it back to Omarchy.
- **Scope:** Project-local Python environment, hash-locked SDK installation from
  the existing source/setup bundle, native tests and Start Menu launch.
- [x] Complete a fresh SDK download, install, diagnostics and first-frame warmup.
- [x] Run all 160 tests and verify the native desktop launcher.
- [x] Retain sanitized evidence and report readiness for the Omarchy reboot.
- **Evidence:** The unchanged prototype ZIP and delivery identity match the Linux
  qualification. Python 3.11.9 and all ten pinned SDK distributions installed
  from fresh downloads. Native warmup passed in 149.969 seconds; all 160 tests
  passed in 140.770 seconds. Start Menu install/remove/reinstall passed; the actual
  shortcut delivered a native frame in 6.844 seconds and closed with no remaining
  application processes. Screenshot reviewed; sanitized results and private-log
  hashes are in `verification/prototype-platform-review.json`. The worker is ready
  for the operator to switch back to Omarchy.

### [ ] APP-001 — Deliver an installed desktop application with a simulated SO-101 pair

- **Portable Make entry point:** The operator requests `make run` on Windows,
  Linux and macOS. Route Windows to the existing PowerShell launcher and Linux
  to the automatic management setup/launch path, removing the Unix-only build
  prerequisite from `run`. macOS must report the existing unsupported NVIDIA
  renderer contract before setup; this request cannot create missing Mac SDKs.
  - [x] Update the Make target, startup contract and contributor instructions.
  - [ ] Verify actual GNU Make routing, checkout paths with spaces and failure
    propagation locally and in the six-job Windows/Linux/macOS CI matrix.
    Local Windows passes all thirteen startup tests. Actual `make run` reaches
    a native RTX frame and clean shutdown with exit zero using the bounded
    integration hook; project validation passes. Hosted matrix pending.

- **Windows contributor startup:** The operator requests one command to build and
  run a checkout. Added `run.ps1` and automatic setup for `manage.py run`,
  retain successful setup evidence keyed to pinned dependency inputs, and preserve
  checksum-sensitive robot model bytes across Windows checkouts. This is local
  contributor startup; installed application delivery remains below.
  - [x] Implement first-run setup, unchanged-input reuse, invalidation and failure recovery.
  - [x] Verify startup control flow, PowerShell entry point and pinned model identities.
    Twelve startup regressions pass on Windows with Python 3.11.9, including
    canonical LF authoring and byte-preserved vendored SDK checks.
  - [x] Verify native warmup and launch in the updated checkout; interactive desktop
    visibility requires the operator's session, not the coding sandbox.
    Fresh setup warmup passed in 124.516 seconds; repeated warmup passed in
    12.875 seconds. The real CLI first-frame/shutdown check and three robot
    asset tests pass. See `verification/windows-startup-review.json`.
  - [x] Run startup regressions in GitHub CI on Windows, Linux and macOS with
    Python 3.11 and 3.12. The initial ten-test matrix passed all six jobs in
    run 37271031449. The final twelve-test matrix at a3c425c passed all six jobs
    in run 37271796770. The actual `run.ps1` command with its setup receipt
    removed completed pinned setup, native warmup, first frame and clean shutdown.
  - **Tooling limitation:** The local framework source CLI now runs and its
    development guidance and project validation succeed after the LF checkout
    repair and supported documentation review. The prescribed peer survey needs
    unavailable `gh`. Framework admission is not advanced. GitHub API reads CI;
    PR creation is unavailable through the connector and browser access was denied.

- **Contextual joint controls:** The operator reports that joint movement remains
  difficult to discover. Implement cross-platform right-click joint controls with
  a visible bounded slider, angle input and lock explanation; reserve middle-drag
  for panning and keep camera input separate. Reuse the native picker and simulated
  command path. Windows is a validation target, not an implementation constraint.
  The operator also authorizes contained Linux ARM64 GPU validation for this work.
  - [x] Implement contextual controls, cancellation and updated input guidance.
  - [x] Verify delayed picking, slider coalescing, limits, locks and camera routing.
  - [x] Verify actual picked-joint motion and rendered frames on Linux ARM64 and Windows.
  Native context-window checks pass on both platforms: a 25 degree target moves
  the picked leader shoulder joint to approximately 26.1 degrees in the bounded
  paused preview, changes RTX pixels, preserves authored USD, pans with the
  middle button and shuts down cleanly. See `verification/joint-context-review.json`.
  All 24 focused input/UI regressions pass on each platform. Retained-source
  admission passes 30 contract tests and three unchanged independent acceptance
  cases; all 90 application/test Python files match the admitted artifact.
  The pinned framework's `litai verify` passes all three applicable gates.

- **Discoverability direction:** Provide persistent on-screen joint instructions, named joint selection, direct angle controls, contextual lock recovery and an obvious real-arm setup entry point. Test the visible Windows flow without relying on the scene tree or undocumented gestures.

- **Current interaction repair:** The selected follower joint is locked by leader-following. Provide an explicit action beside the selected joint to disable following, retain toggle requests while the native worker is busy, and verify subsequent slider and pointer motion. Windows verification passes the busy-worker regression and visible native follower unlock plus slider motion (20 degree target, 21.8 degree measured paused pose, changed RTX frame). Physical motor control is unchanged.

- **Priority:** high
- **Owner:** Desktop Component and native delivery
- **Direction:** Make LeRTX a proper application and preload a physically simulated SO-101 leader and follower pair.
- **Resource blocker:** A native test overlap on the shared-memory Spark caused severe memory pressure; kernel logs show GPU allocation failures and a global OOM kill of an unrelated compiler. No further native qualification before enforced containment, headroom admission, and measured memory/performance evidence.
- **Performance evidence:** [Omarchy measurements](../../verification/performance/omarchy-20260926/README.md) cover native throughput, actual Qt frame delivery, idle, ten resets, ten reopens, memory and shutdown. Corrected Qt scheduling restores 29.95 fps / 99.7% real-time simulation at 720p. Compact runtime snapshots reduce reopen cost. Reopen memory retention and late-Qt SDK initialization remain unresolved; APP-001 is not complete.
- **Performance testing direction:** Run sequential contained performance tests on Omarchy, covering the default robot scene at supported viewport sizes, sustained motion, idle CPU/GPU work, repeated resets/reopens, startup and shutdown. Preserve raw measurements and state the test limits; Spark performs no native work.
- **Additional direction:** Apply NVIDIA/skills to RTX views, robot USD authoring, simulation validation and explicit virtual-to-physical joint mapping; follow the pinned methodology in `docs/architecture/nvidia-methodology.md`.
- **Conclusion:** Replace checkout-dependent delivery with a self-contained graphical installation and complete desktop behavior; qualify traceable articulated robot models and simulated following before claiming a working virtual robot.
- **Depends on:** PORT-002
- **Implementation:**
  - [ ] Implement owned, relocatable application installation, upgrade, removal, icons and file opening without a system Python requirement.
  - [x] Direct viewport joint manipulation: native RTX picking and outlines, shared hierarchy selection, bounded targets, coalesced pointer updates, cancellation and physics-driven paused previews. Windows passes seven focused input/runtime tests and the real Qt/RTX interaction check, including paused and playing motion; see `verification/windows-joint-interaction.json`. Runs were sequential under a 12 GiB committed-memory limit. This is feature evidence, not full APP-001 qualification.
    Documentation discovery now includes the existing performance evidence and NVIDIA methodology. Project validation reaches the pre-existing stale documentation authority review; the complete APP-001 authority review and retained-source admission remain pending, with no receipt or review marker advanced by this feature check.
  - [x] Add persistent joint instructions, semantic joint selection, a prominent angle slider and a setup entry point; verify paused movement and all six calibration previews on Windows RTX.
  - [ ] Complete desktop menus, document identity, recent files, startup progress and actionable errors.
  - [ ] Source and attribute SO-101 leader/follower models; implement actual joint dynamics, limits, grippers and simulated following in the default scene.
- **Evidence:**
  - [ ] Validate installed launch, upgrade, removal and native suites on Linux ARM64, Linux x86-64 and Windows.
  - [ ] Test robot kinematics, commanded tracking, limit enforcement, leader/follower mapping, gripper motion, contacts, reset and saved-scene behavior.
  - [ ] Review real installed UI screenshots and retain current framework acceptance and model provenance.
