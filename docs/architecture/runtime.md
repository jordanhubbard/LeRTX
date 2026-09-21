# LeRTX runtime contract

Milestone two belongs to RENDER-001 in [active work](../roadmap/active-work.md).
This design is subordinate to the root `PROJECT.md`.

## Ownership

The application owns its window, user interaction, session lifecycle, and project
save state. OpenUSD owns authored scene descriptions; OVStage owns shared runtime
scene data. OVRTX consumes that stage and produces real image frames. Newton owns
simulation state. Body indices must map to USD prim paths using the actual importer
mapping, never by slicing independently ordered arrays.

One scene coordinator serializes edit and simulation publications. Each committed
state gets a monotonically increasing ordinal. Physics steps at a fixed timestep;
rendering consumes a committed ordinal. Pause stops physics advancement while
camera navigation continues; reset restores the authored initial state and clears
accumulated simulation time. Scene edits invalidate affected simulation state and
must rebuild or update it before stepping resumes.

## First visible experience

A restrained dark workspace centers the rendered viewport, with a scene hierarchy
on the left, selected-object properties on the right, and transport/status below.
Open/save, selection, transform editing, camera orbit/pan/zoom, and play/pause/reset
are visible controls. Display actionable loading and SDK errors. Long SDK work
must not freeze the window. Detect unsupported hosts before native initialization.

The first fixture is a self-contained USD work surface with camera, illumination,
one static obstacle, and a dynamic body that falls and settles under Newton. This
proves the rendering/physics loop before robot hardware is connected. Saved USD
must preserve authored edits; transient simulated poses are saved only through an
explicit bake operation. Keep remote asset resolution explicit.

## SDK evidence

The local OVRTX public minimal example uses `ovrtx.Renderer`, `ovstage.Stage`,
`renderer.attach_ovstage`, `ovstage.population.open_usd`, an ordinal write-floor
barrier, and `renderer.step`. It maps frame data through DLPack and releases mapped
views before detach/destroy. Use the corresponding pinned public API contract;
the earlier Kit `mock-use-cases` examples are not implementation authority.

Initialize an anonymous OpenUSD stage on the native owner before constructing
RTX, including when opening an existing file. Import alone leaves relevant USD
initialization lazy. Explicitly set `RendererConfig.keep_system_alive=False`:
the pinned SDK otherwise retains its rendering system after the last renderer
is destroyed. Native worker shutdown must release that system too. The current
startup/shutdown evidence and remaining platform checks are recorded in
`verification/usd-bootstrap-review.json`.

Start the scene command worker without eagerly creating an empty renderer.
The first validated document rebuild constructs the renderer only after its
runtime USD snapshot is ready. Otherwise the initial open destroys an unused
renderer while SDK initialization may still be active, delaying the first frame.
Subsequent rebuilds and final shutdown retain owner-thread cleanup and the USD
bootstrap; the first-scene path must construct exactly one native renderer.

The Linux CUDA probe now verifies OVRTX 0.5.0.377615, OVStage 0.2.0.377349,
Newton 1.6.0, Warp 1.17.0, NumPy 2.4.6 and usd-core 25.11 on Python 3.11 and an
RTX 5090. These versions are selected by `flavors/desktop-python`; PySide6 6.10.2
is the desktop UI dependency. Use Newton's explicit CollisionPipeline, not the
deprecated Model.collide shortcut. The bootstrap Mac's Python version is not the
native-runtime Python choice. Windows dependency qualification and the retained
application tests now pass using the verified SDK and isolated Qt installation;
large installations remain subject to the worker's limited disk headroom.

The probe's before/after frame artifacts and pose/hash evidence are retained in
`verification/native/linux/`. This verifies native rendering and physics coupling,
not application acceptance by itself. Subsequent retained-source application
tests exercise real Qt controls, pause/reset/edit/save and repeated launch on both
GPU platforms. See the platform `launch-save-review.json` reports; complete
packaging and all specification acceptance remain outstanding.

Public sources:

- [OVRTX](https://github.com/NVIDIA-Omniverse/ovrtx)
- [OVStage](https://github.com/NVIDIA-Omniverse/ovstage)
- [Newton](https://github.com/newton-physics/newton)
- [LeRobot code](https://github.com/huggingface/lerobot)
- [LeRobot models](https://huggingface.co/lerobot)

## Acceptance

Require Linux and Windows NVIDIA evidence for the claimed product platforms:
actual output frames with correct dimensions and nonconstant pixels; a changed
rendered body pose matching Newton state; pause/reset behavior; USD edit/save/reload
round trips; and repeated scene open/close without leaked native resources. Record
SDK identities, driver/GPU facts, commands, test results, and frame artifacts.
Screenshots of a mock viewport do not satisfy this milestone.

## Later digital-twin boundaries

USB discovery detects candidates; role assignment must distinguish identical
leader/follower adapters and persist stable device identities. Reconnection marks
telemetry stale until fresh data arrives. Servo calibration establishes joint
units, signs, zeros, and limits before transforms are applied to the twin.

Astra reconstruction returns a draft scene with scale and geometry uncertainty.
Users verify dimensions, robot base alignment, and occluded obstacles before a
workspace is eligible for motion planning. Rendering a plausible reconstruction
does not certify collision clearance. Physical actuation is a later capability
with explicit arming, stop behavior, stale-state handling, and bounded commands.
