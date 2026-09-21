# LeRTX

## Goals

Create a beautiful Linux and Windows application for NVIDIA GPUs that makes a
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

No blocking dependency on another repository's PROJECT.md completion is declared.
Literate AI is pinned by its initialization lineage and lifecycle identity.
Milestone two requires compatible OVRTX and OVStage SDK artifacts, Newton, and an
accessible Linux or Windows NVIDIA GPU execution target. Exact SDK versions are
selected in the native Python Flavor. RTX/OVStage/Newton application scene and
Qt control tests now pass on Linux and Windows; release-ready packaging and full
application acceptance remain outstanding. Windows also passes native fixture authoring using the
unmodified, archive-verified USD Python wheel. A reproducible local metadata-only
repair of the Linux USD wheel now passes unchanged strict archive validation;
the complete Linux closure passes disposable installation and revalidation using
the exact qualified framework wheel. That framework is now bound locally;
full application admission remains outstanding.
The Astra endpoint is `https://inference-api.nvidia.com/v1/responses`, using model
`azure/openai/gpt-6-astra` and an initial output limit of 512 tokens. An authorized
live text request and a synthetic-image reconstruction succeeded. The image
workflow and validated local USD construction are implemented; full current
acceptance remains outstanding. Follow-on physical synchronization requires the
SO-101 devices and calibration data, but is not a milestone-three gate.

## Completeness

| Area | State |
| --- | --- |
| Literate AI creation | Canonical application scaffold initialized with litai 1.1.0 |
| Host development profile | Python / Make / macOS bootstrap; not a GPU product target |
| Production targets | Linux RTX 5090 and Windows L40 development tests pass; Windows fresh-install staging requires a new capacity check. Historical free-space measurements are not current readiness evidence |
| Starter Component | Framework greeting sample; not the LeRTX application |
| LeRTX harness Component | `components/harness`: generated, built, launched; 13 tests passed on the bootstrap Mac |
| Application window and real rendered frames | Retained Qt application renders on both GPU targets; visible controls tested and screenshots reviewed; full acceptance pending |
| OVRTX / OVStage / Newton integration | Application session tests verify motion, pause/camera, reset, edit/save/reopen and cleanup on both targets |
| Native USD authoring | Private document layers, atomic save, transform editing and failure recovery tested; broader asset/interaction coverage remains |
| USB, models, Astra, robot calibration | Photo preview/upload, Astra draft import and persistent unverified warning implemented; live synthetic-image inference succeeds; robot telemetry and measured registration not implemented |
| LLM configuration | Settings UI and bounded asynchronous connection tests implemented; blank-key persistence and staged settings tested; complete acceptance pending |

## Current work

See [active work](docs/roadmap/active-work.md). HARNESS-001 establishes milestone
one; RENDER-001 owns milestone two. Product vision beyond those milestones is
preserved above without treating it as implemented behavior.
CONFIG-001 owns application settings and the inference adapter. TWIN-001 owns
milestone-three photo reconstruction. ROBOT-001 owns separately scoped follow-on
mock support and SO-101 synchronization. Physical actuation and automatic motor-register
calibration writes are not authorized.

The roadmap's 2026-09-20 open-items checkpoint is the current execution order.
The renderer-fixed source passes 158 Linux tests and eight targeted Windows
tests; a full latest-source Windows run remains open. Litai PR #482 supersedes
the local package-count patch, but its merged-revision CI has a failed Windows
test shard. Local exact-wheel qualification passed; application rebind, admission,
current receipts, end-user packaging and clean-install verification remain open.
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
validation and local draft construction are implemented; physical telemetry and
measured calibration remain unimplemented. A separate native import-order repair
passes fresh-process existing-file launch tests on both platforms.
