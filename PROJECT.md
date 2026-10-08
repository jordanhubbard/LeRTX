# LeRTX

## Goals

Create a beautiful Windows 11, Linux x86-64 and Linux ARM64 application for NVIDIA GPUs that makes a
LeRobot robot and its workspace a usable digital twin. Start with the SO-101
leader and follower, connected by USB with device discovery and persistent role
assignment. Use Hugging Face LeRobot code and models.

1. **Milestone one — application harness:** create and maintain the application
   through Literate AI (`litai`), with specifications as authority, reproducible
   dependency resolution, and verified lifecycle. The operator has approved
   retaining and directly repairing generated desktop source with reviewable
   diffs and unchanged safety/acceptance requirements.
2. **Milestone two — running 3D application:** render actual frames using OVRTX,
   manage USD scenes through OVStage, and simulate scene bodies using Newton.
   Provide a responsive application window, viewport, scene hierarchy, selection,
   transform inspection, and simulation play/pause/reset.
3. **Milestone three — Astra photo-to-USD reconstruction:** reconstruct an
   editable, saveable USD workspace draft from a single photo through the remote
   Astra inference service. Render it in the application and retain explicit
   unverified dimensions, uncertainty and provenance after save/reopen.
4. **Follow-on physical twin:** discover SO-101 USB devices and synchronize
   digital robot joints with read-only physical leader/follower servo readings.
   Identify obstacles and calibrate the twin against measured physical geometry
   so real tasks can use scene constraints to avoid obstacles. A photo alone does
   not establish metric scale, occluded geometry, or a verified collision model.
5. Provide a polished configuration UI for LLM access and useful application
   settings. Default inference to the NVIDIA Responses endpoint and
   `azure/openai/gpt-6-astra`. Ship with a blank API-key field. Development
   credentials must never become application defaults or appear in logs, exports,
   generated source, or screenshots.

## Dependencies

Literate AI is pinned by its initialization lineage and lifecycle identity.
The desktop requires an NVIDIA GPU on Linux or Windows. Current SDK pins are
OVRTX 0.5.1.385782, OVStage 0.2.1.385922, Newton 1.6.1 and Warp 1.18.0.
The October SDK refresh passes 239 portable tests plus 59 subtests, 17 Linux
native tests and four offscreen Qt/native interaction checks. Its observed Linux
x86-64 CPython 3.12 target is selected for current framework admission. Previous
Windows and ARM64 results describe the earlier SDK stack, not this candidate.

## Completeness

The release delivers a source/setup desktop bundle with real RTX rendering,
Newton physics, USD editing, photo reconstruction drafts and SO-101 controls.
Guided calibration tests use an emulated bus. Physical-arm qualification, measured
world registration, fresh Windows/ARM64 validation and cold-cache startup within
the two-core diagnostic limit remain follow-up work. They are not prerequisites
for the operator-authorized scoped release. macOS is a development host only.
Photo dimensions and collision geometry remain unverified. The harness's
`runtime_ready: false` describes its original milestone and is not changed by
publication of the desktop bundle. Application admission is reported by
`litai verify`; native evidence is separately recorded in
`verification/sdk-refresh-review.json`.

## Current work

APP-001 delivers a self-contained installed desktop application and a preloaded,
physically simulated SO-101 leader/follower workspace. The prototype qualification
is its baseline, not the completion criterion. Application installation must be
independent of this checkout; robot behavior needs articulation and contact tests.

PORT-001 completed the native prototype expansion to Linux ARM64 and an additional
Arch/Omarchy GPU target, with reproducible isolated setup and real application
verification on each platform. The operator accepted limited Windows testing;
native platform support is not proof of physical SO-101 control. The operator
has authorized copying to the additional worker's source directory, provisioning
project environments and running the application tests over SSH.

See [active work](docs/roadmap/active-work.md). HARNESS-001 establishes milestone
one; RENDER-001 owns milestone two. Product vision beyond those milestones is
preserved above without treating it as implemented behavior.
CONFIG-001 owns application settings and the inference adapter. TWIN-001 owns
milestone-three photo reconstruction. ROBOT-001 owns separately scoped follow-on
mock support and SO-101 synchronization. The operator now authorizes implementing
manual USB reads/writes, explicit motor arming, bounded motion and measured
virtual binding. The operator also authorizes a guided SO-101 setup/calibration
wizard with torque-off homing and measured-limit EEPROM writes, a durable original
register backup and rollback on cancellation. Connections initially read only;
calibration and motor arming are separate explicit workflows. Autonomous execution
remains separate work; physical qualification follows when the operator connects
the hardware.

Earlier cross-platform results are retained in
`verification/prototype-platform-review.json`. They do not qualify the updated
SDK stack. The release work and current evidence are tracked in the active queue.

## Completed work

See [CHANGELOG.md](CHANGELOG.md). Milestone one is accepted for the local harness:
generation, build, 13 tests, independent acceptance, and the launch command passed.
Milestone two is not yet accepted. The retained application renders actual RTX
frames with Newton motion and has passing Qt interaction tests on both GPU targets.
The 122-test photo-workflow snapshot passes on both GPU targets. Tests do not yet prove
every product requirement or a distributable installation; see the current evidence
and remaining checks in the active-work queue. Milestone-three photo inference,
validation and local draft construction are implemented. USB telemetry, guided
calibration and measured virtual binding now have SDK/emulated-arm coverage;
qualification with physical arms remains pending. A separate native import-order repair
passes fresh-process existing-file launch tests on both platforms.
