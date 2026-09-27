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
When following locks a selected follower joint, expose an adjacent explicit
"Manipulate follower independently" action. Retain following changes until the
native worker can accept them; a busy renderer must not silently discard input.
Pause holds simulation state; Reset restores the authored poses and target state.
Report tracking or physics failure visibly instead of falling back to animation.
Reject inconsistent articulation metadata. Arbitrary transform edits to an
individual robot link must not break its articulation silently.

Allow grabbing a rendered arm link and dragging its associated joint. Native RTX
picking must respect image scaling and letterboxing, and agree with hierarchy
selection. Show the selected joint and target; clamp targets to model limits.
Left drag manipulates joints, Alt-left drag orbits, right drag pans and the wheel
zooms. A paused drag advances a bounded physics preview and remains paused;
playing drags update targets through the normal simulation loop. Following must
be disabled before manipulating the follower. Coalesce drag updates, preserve
the final released target, and cancel gestures on reset, scene change or focus
loss. Never teleport links or route these gestures to a physical USB device.

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

## Photo request feedback

The photo dialog must show missing credentials before upload, provide a masked
in-memory API key field, and focus that field when an upload is blocked. Preserve
the selected image for retries, show in-flight progress, and clear the dialog key
on close. Do not persist or log the key or send the image before explicit Upload.
