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

## Current release qualification

The replacement upstream is `https://github.com/jordanhubbard/LeRTX`. Its camera,
recording and integrated calibration work is retained. The next source/setup
release combines that code with OVRTX 0.5.1.385782, OVStage 0.2.1.385922, Newton
1.6.1 and Warp 1.18.0. Historical platform and admission results below describe
earlier snapshots. Fresh portable, Linux NVIDIA and framework admission checks
must bind the combined source before publication. Windows/ARM64 refresh,
physical-arm qualification and two-core cold-cache qualification remain separate
follow-up coverage for the operator-authorized scoped release.

## Dependencies

No blocking dependency on another repository's PROJECT.md completion is declared.
Literate AI is pinned by its initialization lineage and lifecycle identity.
Milestone two requires compatible OVRTX and OVStage SDK artifacts, Newton, and an
accessible Linux or Windows NVIDIA GPU execution target. Exact SDK versions are
selected in the native Python Flavor. RTX/OVStage/Newton application scene and
Qt control tests pass on Linux and Windows. Linux ARM64 retained-source admission,
independent acceptance, sealed dependency validation and all 160 tests against
the admitted artifact now pass. Formal release packaging remains separate work.
The Astra endpoint is `https://inference-api.nvidia.com/v1/responses`, using model
`azure/openai/gpt-6-astra` and an initial output limit of 512 tokens. An authorized
live text request and a synthetic-image reconstruction succeeded. The image
workflow and validated local USD construction are implemented and covered by the
current native prototype tests. Follow-on physical synchronization requires the
SO-101 devices and calibration data, but is not a milestone-three gate.

## Completeness

| Area | State |
| --- | --- |
| Literate AI creation | Canonical application scaffold initialized with litai 1.1.0 |
| Host development profile | Python / Make / macOS bootstrap; not a GPU product target |
| Production targets | Current 160-test suites pass on Linux ARM64 GB10, Linux x86-64 RTX 5090, Omarchy RTX 5080 Laptop, and Windows 11 L40; fresh Windows 11 RTX 5080 Laptop installation also passes all 160 tests and Start Menu launch |
| Starter Component | Framework greeting sample; not the LeRTX application |
| LeRTX harness Component | `components/harness`: generated, built, launched; 13 tests passed on the bootstrap Mac |
| Application window and real rendered frames | Retained Qt application renders on all four tested targets; visible controls and screenshots reviewed; ARM64 artifact acceptance passed |
| OVRTX / OVStage / Newton integration | Application session tests verify motion, pause/camera, reset, edit/save/reopen and cleanup on both targets |
| Native USD authoring | Private document layers, atomic save, transform editing and failure recovery tested; broader asset/interaction coverage remains |
| USB, models, Astra, robot calibration | Shared SO-101 controllers, guided calibration, measured RTX viewing, joint recordings, explicit follower tracking/playback and action presets implemented. Operator saved both calibrations and confirmed the workflow. USB camera selection/preview works on Windows, with Windows/Linux device CI; broader hardware qualification and world registration remain. Photo reconstruction remains unverified geometry |
| LLM configuration | Settings UI and bounded asynchronous connection tests implemented; blank-key persistence and staged settings tested in the passing native suites |

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

PORT-001 records the current cross-platform delivery work. All four current
native suites pass 160 tests, including a second Windows run in the isolated
launcher environment. Setup uses platform-specific hash locks and a bounded real
render warmup. The project has been copied to the additional Omarchy worker;
desktop launcher installation and removal are implemented. Detailed evidence is
in `verification/prototype-platform-review.json`.
The project now binds the qualified framework revision containing both the
directory-artifact count repair and oversized Windows filesystem-identifier
repair. Its exact merged revision passes the full hosted matrix; the supported
rebind preserves the policy and required receipt evidence. `litai verify` remains
the authority for current application admission and passes all applicable gates.
The admitted ARM64 artifact passes all 160 tests; the source/setup ZIP passes a
fresh Omarchy installation, upgrade and all 160 tests. A fresh Windows 11 installation now passes all 160 tests and the real Start Menu
launch, closing the earlier capacity-limited installation gap.
The source/setup ZIP is a development bundle, not a published release.
Measured registration, licensed robot kinematics, read-only physical telemetry
and any later model/task-control workflow are separate follow-on work.

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
