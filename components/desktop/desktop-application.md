---
name: Installed LeRTX application
summary: Desktop delivery, articulated robots, guided controls and photo reconstruction
kind: feature
---
# Installed LeRTX application

## Desktop delivery

Ship self-contained Windows x86-64, Linux x86-64 and Linux ARM64 application
bundles with their exact Python and native dependencies. End users must not need
a source checkout, command shell, Python installation or online dependency setup.
Provide graphical per-user install, upgrade and removal. Install into owned user
application storage, preserve documents and settings, and never replace an
unrelated file. Failed upgrade leaves the prior application launchable. Record
the installed build and its file identities. Include an application icon, OS
launcher and Windows installed-app registration, with correct quoted file-open
arguments. Native startup failures must produce a visible actionable dialog and
a discoverable user log. Logs and caches must not require writable program files.

Provide File, View and Help menus, standard open/save shortcuts, recent local
files, document name and modified state in the window title, About and usage
help. Remember window layout without persisting credentials. Loading and failed
renderer states remain visible. A normal launch opens the robot workspace.

## Contributor checkout startup

Contributors use `make run` as the common checkout entry point. On Windows it
invokes the PowerShell launcher without Unix shell tools; on Linux it invokes
the management setup/launch path. GNU Make and the documented Python bootstrap
prerequisites are required. On macOS the target must fail before environment
creation or downloads with an explanation that the pinned NVIDIA renderer is
unavailable; portable launcher routing does not establish Mac rendering support.
Windows contributors can also prepare and launch a checkout with one command,
`run.ps1`, using a real Python 3.11/3.12 or uv. The desktop management `run`
command prepares missing or stale environments before launching. Setup uses
the pinned hash locks and succeeds only after diagnostics and a real rendered
warmup frame pass. Reuse successful setup for unchanged inputs; changed locks,
bundled wheels, requirements or management code invalidate it. Interrupted or
failed setup must retry and must not launch the application. Forward explicit
scene paths and return setup/launch failures to the invoking shell. Preserve
checksum-sensitive upstream robot resource bytes in Windows checkouts.
Contributor setup remains separate from the self-contained end-user delivery
contract above.

## Default SO-101 workspace

Preload separately identifiable SO-101 leader and follower arms on the work
surface. Use pinned, attributed upstream leader and follower URDF descriptions
and their actual geometry, joint axes, origins, limits, masses and inertias.
Preserve upstream calibration and geometry limitations in model provenance and
user help. Store geometry and articulation metadata in saved USD so reopening
does not silently replace a model with a different revision.

The robot must be an articulated Newton model, not independent moving meshes.
The five rotary arm joints and gripper must obey their declared limits, maintain
link constraints, participate in workspace collision, and have a grounded base.
Joint controls command bounded position targets; simulation integrates actual
state. The follower follows the simulated leader's measured joint positions.
Map the leader trigger and follower gripper through normalized travel, not by
assuming equal angle limits. Clearly label simulated controls and measured
virtual state. No physical port opening or actuation follows from these controls.

Expose independent following on/off, joint position controls, Play/Pause and Reset.
Show the shared "Follower tracks the simulated leader" checkbox beside the
joint controls; clearing it enables independent follower manipulation. Retain following changes until the
native worker can accept them; a busy renderer must not silently discard input.
Pause holds simulation state; Reset restores the authored poses and target state.
Report tracking or physics failure visibly instead of falling back to animation.
Reject inconsistent articulation metadata. Arbitrary transform edits to an
individual robot link must not break its articulation silently.

Allow grabbing a rendered arm link and dragging its associated joint. Native RTX
picking must respect image scaling and letterboxing, and agree with hierarchy
selection. Show the selected joint and target; clamp targets to model limits.
Keep all twelve joint controls visible in the robot panel, with arm and joint
names, sliders and keyboard-accessible numeric targets bounded by model limits
in degrees (normalized travel percent for a gripper). Explain following locks
inline. Left or right drag on a rendered link manipulates its associated joint;
a press without movement must not change its target. These controls never enable
physical writes. Alt-left drag orbits, middle drag pans and the wheel
or trackpad scroll zooms. A paused drag advances a bounded physics preview and remains paused;
playing drags update targets through the normal simulation loop. Following must
be disabled before manipulating the follower. Coalesce drag updates, preserve
the final released target, and cancel gestures on reset, scene change or focus
loss. Never teleport links or route these gestures to a physical USB device.
Slider updates use the same coalesced simulated command path and preserve the final
value when dismissed normally. Escape, focus loss, reset and scene changes cancel
unsent input and stale pick callbacks. Controls must remain inside the active screen.

## Qualification

Validate independent forward kinematics at known poses, per-joint axes and ranges,
both end effectors, gripper mapping, dynamic target tracking, limit enforcement,
base stability, follower separation, collision/contact behavior, reset and USD
save/reopen. Include an obstructed-motion test so a rendered moving arm cannot
pass as proof of collision-aware physics. Test real Qt controls with rendered
frames and prove visuals track the simulated link transforms. Qualify installed
launch, upgrade, file opening and uninstall on supported targets.

## Asset and joint binding methodology

Use the pinned NVIDIA development methodology in
`docs/architecture/nvidia-methodology.md`. Standard USD joints, rigid-body masses,
inertias and collision metadata must survive saving and reopening. Compare the
converted USD contract independently against the pinned URDF. Preserve meaningful
validation warnings and record adaptations such as a negligible-mass tool marker.

A physical observation mapping is an explicit, non-actuating boundary: bind each
semantic joint and expected motor ID to its USD joint, physical observation unit,
measured zero/direction or paired calibration poses, and calibration identity.
Reject missing or ambiguous bindings, wrong device identity, nonfinite values,
stale observations and out-of-range poses. Never infer a physical zero from a
model limit or emit a serial command from a simulated control. This mapping does
not establish hardware qualification without observations from a calibrated arm.

## Resource containment

Native renderer initialization and simulation must not make the user's desktop
unresponsive under memory pressure. Keep the UI responsive to cancellation and
shutdown when native calls stall. Admit only one native qualification process per
host, enforce a bounded process memory budget and no swap for qualification, and
monitor system memory headroom on unified-memory GPUs. Abort the owned workload
before its reserve is exhausted; never terminate another project's processes to
make a test pass. Refuse startup with an actionable error when the budget cannot
be met. Record peak process memory, host headroom, GPU allocation where available,
first-frame latency, steady simulation/render timing, repeated scene-reset growth
and idle behavior. Run those measurements under containment before further native
qualification. Paused unchanged scenes must not continuously republish transforms
or perform inverse kinematics solely to redraw the same image.

Schedule frame starts against the requested cadence, rather than adding a full
frame interval after render completion. Simulation receives elapsed wall time
between tick starts. Idle polling remains inexpensive. Use compact runtime USD
snapshots, and discard previous owned snapshots after their native stage closes;
reopening a document must not retain every prior runtime export until app exit.

## Photo reconstruction workflow (milestone three)

The milestone-three toolbar offers Reconstruct Photo. A modal dialog previews a
user-selected PNG/JPEG and names the configured destination before an explicit
Upload and Reconstruct action. Never scan for images or credentials. Bound input
to 8 MiB and 16 million pixels, resize the upload to at most 2048 pixels per side,
and re-encode it without source metadata. Explain this transformation before
upload. Bind provenance to the actual uploaded bytes. Use a Responses user message
with input_text and a base64 input_image data URL. Use the model, token budget
and timeout explicitly selected in the photo dialog, as defined in
`desktop-application.md`; its configured-model option uses saved settings.
Never silently increase the selected budget or change the destination. Reject
incomplete, failed, oversized, malformed or schema-invalid output. Reject
redirects and suppress raw provider failures. Cancel invalidates late results
without claiming server-side cancellation. Allow only one in-flight request per
window, including after a cancelled dialog is closed.

On success, ask before discarding unsaved work, then construct and adopt the
validated draft on the native worker. Mark it dirty and require Save As outside
the temporary workspace. Keep a visible unverified/estimated-dimensions warning
when such USD is loaded again. Preserve existing scene state on invalid results;
do not claim readiness until native initialization completes. Image inference is
distinct from the inexpensive Intelligence connection test. Test with injected
Responses transports plus separate live endpoint image-capability verification.

## Photo request feedback

The photo dialog must show missing credentials before upload, provide a masked
in-memory API key field, and focus that field when an upload is blocked. Preserve
the selected image for retries, show in-flight progress, and clear the dialog key
on close. Do not persist or log the key or send the image before explicit Upload.

For the OpenRouter Responses endpoint, request strict schema-constrained scene
JSON and require provider support. Mesh triangles remain a flat integer array.
The local parser still validates bounds, unique identities, nondegenerate meshes
and aggregate budgets before importing USD; provider schema compliance is not
trusted as a replacement. Other configured endpoints keep their request format.


### Guided controls and photo quality

Keep joint manipulation instructions visible above an arm selector, semantic joint
selector and angle slider. Selecting a joint by name must pick its actual USD link
and work while paused. Preserve requests made while the native owner is busy.
Place advanced target/readback rows in an expandable area and allow scrolling.
Expose per-role Calibrate actions in Device Manager. The modeless setup
wizard keeps the native viewport visible throughout reference alignment and each
joint's measured range/direction check. Label provisional calibration poses distinctly
from verified physical telemetry. Never enable motor torque in the wizard.

The wizard embeds a live 3D view beside the persistent reference diagram and
progress in one resizable window. Subscribe this view to native frames, retain
the single native owner, and offer camera orbit, zoom and arm framing. The always
visible static numbered joint map is location help, never the live preview.
Introduce joints by physical
location and motion (base turn, upper-arm hinge, middle hinge, wrist tilt, wrist
twist, claw/trigger), then show the technical name and motor ID. Highlight the
current joint in the diagram and native scene. Record only the selected motor for
step progress while the 3D arm mirrors all six joints. Incidental motion of other
joints must neither warn, reset capture, nor advance the step. Prompt a comfortable
endpoint hold, an opposite endpoint hold and a repeat visit at or beyond the first endpoint in the return direction.
Require a meaningful per-joint span, multiple distinct fresh samples, stable holds
with encoder-noise tolerance, and a current displayed native frame before automatic
advancement. Duplicate samples, stale intervals, isolated spikes and small twitches
must not qualify. Keep direction reversal available. Reference capture and final
travel/direction review and hardware saving remain explicit. Endpoint pauses are
operator-chosen positions, not proof that software detected mechanical hard stops.
Transfer the embedded live 3D view to the hardware panel on completion; dispose it when
the hardware session closes. Show recorded travel, review and explicit completion.
Explain that the initial reference is a stationary pose to copy; raw movement
readings remain available before calibration establishes the reference.
Keep instructions scrollable and navigation reachable at laptop window sizes.
Live calibration and subsequent hardware viewing retain one pending update while
the renderer is busy, use fresh telemetry when it executes, and invalidate
cancelled or superseded work. Stale data cannot satisfy visual confirmation.

On OpenRouter, photo upload defaults to the high-reasoning detailed-shape preset
(openai/gpt-6-astra, high reasoning, 24576 output tokens, 300-second transport
read timeout). Offer a cheaper coarse-layout preset and the configured model;
never change saved connection settings or silently switch the destination/key.
Explain latency, cost and colored-mesh limitations before upload. Instruct the
model to preserve the main subject's silhouette and appendages, and omit large
background proxies. Report primitive/mesh counts and offer a named initial focus before the user opens the draft;
a schema-valid scene is not proof of visual fidelity. Only a native-rendered review
of the user's actual input establishes whether a model trial improved shape.


## Verified robot resource packaging

For lifecycle admission, package the exact SO-101 resource tree (USD, STL, URDF,
collision hulls, licenses and provenance) as the platform-independent
`lertx-robot-assets==1.0.0` wheel. Its archive hash belongs in each target dependency
lock; the offline installer verifies it alongside the SDK. A deterministic local
builder must reproduce the wheel and compare every resource byte to the reviewed
source tree. Retained source snapshots omit that resource subtree only when the
verified asset wheel contains the identical complete tree. Keep application Python
modules byte-identical to the retained source. Checkout launches may use their
adjacent resource tree; admitted exports resolve the installed asset package.
No asset fetch, conversion, or network access occurs on application startup.

Native worker synchronous shutdown allows up to 30 seconds for renderer teardown.
A timeout retains the worker reference so cleanup can be joined again; GUI close
continues asynchronously while native cleanup runs.
