# NVIDIA development methodology

For RTX viewport, OpenUSD robot asset, and simulation changes, use the relevant
skills from [NVIDIA/skills](https://github.com/NVIDIA/skills) at reviewed revision
`d8519c57da6db5d9bea274ec1724a4a7a56a3dee`. These guide implementation;
Component specifications remain the behavioral authority. Do not substitute a
newer checkout silently or install every catalog dependency.

Read these entry points and their task-specific references before related work:

- [Omniverse Realtime Viewer](https://github.com/NVIDIA/skills/blob/d8519c57da6db5d9bea274ec1724a4a7a56a3dee/skills/omniverse-realtime-viewer/SKILL.md):
  routing, conventions, OVStage population/data plane/integration, validation,
  viewer layout/input, and native picking/selection.
- [Omniverse CAD to SimReady](https://github.com/NVIDIA/skills/blob/d8519c57da6db5d9bea274ec1724a4a7a56a3dee/skills/omniverse-cad-to-simready/SKILL.md):
  route-scoped preflight, URDF conversion, minimum USD validation, NVIDIA Asset
  Validator, geometry and physics validation.

A local reference checkout may live under ignored `_build/reference/nvidia-skills`.
Check its exact revision before executing its scripts. Build-only conversion and
validation dependencies belong to `desktop/tools/pyproject.toml` and `uv.lock`,
separate from the application's hash-locked native runtime. Never co-install
incompatible USD distributions into the application to satisfy an asset tool.

## RTX viewport

OVRTX owns rendering and native picking. One native owner serializes scene
population, simulation, camera updates and rendering. Publish runtime state to
OVStage with monotonically increasing ordinals; wait for completion and advance
the write floor before consuming it. Matrix tensors are float64 and row-major. In the attached OVStage path,
convert simulated world poses through the current parent frame before publication;
keep the multi-frame nested-articulation regression to verify that contract. Do not bake transient simulation transforms into authored USD.

Keep the viewport prominent, panels usable at the supported window size, and
input routing independent of text editing. Coordinate mapping for native picking
must account for the actual rendered image and letterboxing. Native selection and
the scene tree must agree. Validate the first frame, camera changes, selection,
scene changes, simulated link motion, ordinal progression and clean shutdown on
the actual GPU renderer. A screenshot alone is insufficient.

## SO-101 assets and simulation

Use the official `urdf-usd-converter` route, preserving standard USD links,
revolute joints, collision geometry, masses and inertias. These pinned URDFs
already supply physics properties, so this is conversion-only: Content Agents
inference and service deployment are unnecessary. Run preflight and dependency
checks, minimum USD checks, then NVIDIA Asset Validator with geometry and physics
coverage. Keep warnings and failures visible in evidence.

`uv run --project desktop/tools desktop/tools/convert_robots.py` reproduces the
packaged assets. Record upstream identities and hashes, converter versions,
options, and any deliberate adaptations. A negligible-mass fixed tool-coordinate frame
is retained as an Xform rather than an invalid rigid body. Preserve the upstream
CAD estimates and mesh warnings. Physical contact uses per-part convex hulls;
that approximation is not a claim of exact gear, friction or actuator behavior.

Validate USD joint relationships, axes, origins, ranges and inertias against the
pinned URDF independently of runtime model construction. Then test integrated
Newton dynamics: tracking, limits, gravity, base stability, contacts, obstruction,
leader/follower mapping, reset and saved scenes. Standard USD validation does not
prove dynamics or hardware calibration.

## Physical joint mapping

The catalog is not an SO-101 calibration specification. Use LeRobot's actual
SO-101 and Feetech bus definitions alongside the pinned model. Match joints by
semantic name and motor identity, never by an incidental array index. Preserve
units explicitly: USD angular limits are degrees; Newton/URDF angles are radians;
LeRobot's gripper observation is normalized travel. Arm observations can also be
normalized unless degree mode is explicitly configured.

Binding a real device additionally requires its own identity, motor IDs,
calibration ranges and direction, homing offsets, timestamps and connection state.
Do not reuse leader trigger angles as follower gripper angles. A simulated pair
and a serial-port name do not establish calibration. Physical commands remain
outside the simulated-controls path until a separate explicit hardware workflow
provides those inputs and validates them on the connected device.

The mapping review uses LeRobot revision
`e595b7902714ba51f91e47523f66f89c5181b649`:
[SO follower](https://github.com/huggingface/lerobot/blob/e595b7902714ba51f91e47523f66f89c5181b649/src/lerobot/robots/so_follower/so_follower.py),
[SO leader](https://github.com/huggingface/lerobot/blob/e595b7902714ba51f91e47523f66f89c5181b649/src/lerobot/teleoperators/so_leader/so_leader.py),
and [motor normalization](https://github.com/huggingface/lerobot/blob/e595b7902714ba51f91e47523f66f89c5181b649/src/lerobot/motors/motors_bus.py).
The standard IDs 1–6 correspond to shoulder pan, shoulder lift, elbow flex,
wrist flex, wrist roll and gripper. A specific device must confirm that assignment.
A saved calibration's sensor range alone does not prove the sensor's zero matches
the CAD zero; record a measured zero/direction or paired physical/virtual poses.

## Qualification containment

All Linux native qualification now goes through `verification/native_guard.py`.
It serializes native tests per host, uses a systemd cgroup with a memory cap and
zero swap, checks admission headroom, watches the host reserve, and enforces a
wall-clock deadline. Unified GPU memory may not be fully charged to a cgroup;
the headroom watchdog is additional protection, not a claim of a hard GPU quota.
Do not run renderer tests concurrently on the same host. GPU allocation and
steady-state/reset memory growth still need explicit profiling. Idle scenes must
settle and stop submitting native work; portable idle tests alone do not prove
resource usage in the real renderer.

Omarchy mixed Qt/native regression runs initialize QApplication before OVRTX,
matching the desktop entry point. Creating Qt only after previous headless OVRTX
sessions crashed in `libEGL_nvidia`; this remains an SDK initialization-order
limitation, not a resolved SDK defect. `verification/run_native_regression.py`
preserves application startup order and must run through the resource guard.

For the complete Linux native suite, use the application interpreter to run
`verification/qualify_native.py --output <new-evidence-directory>`. It runs each
native module in a fresh guarded process, initializing Qt before the SDK. This
also isolates the fresh-process launch tests from native threads retained by
earlier tests; a combined run exceeded the guard's 128-task limit. Each module
keeps the memory cap, host reserve and deadline. The runner preserves logs and
guard reports, and fails if any module fails. It may reuse shader caches and
does not establish cold-cache startup performance.
The guard records its CPU quota and task limit. `--cpu-cores` allows an explicit
diagnostic budget after checking worker headroom; its default remains two cores.
Changing that budget is a distinct experiment and must be recorded as such.
