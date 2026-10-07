---
name: SO-101 USB hardware controls
summary: Explicit telemetry, bounded motor writes and torque-off guided calibration
kind: feature
---
# SO-101 USB hardware controls

Setup must persistently name the selected Leader (hand-operated controller) or
Follower (robot hand), including during joint capture and in the embedded RTX
view. Use the same role palette in the diagram, selection banner, viewport
legend and rendered printed parts. Offer custom colors before connecting an arm,
saved as general.leader_color and general.follower_color (#RRGGBB); defaults are
#1FAD9E and #F2A31F. Migrate older saved profiles by adding only these defaults.
Keep role text visible for identical colors and color-vision differences. Apply
colors to runtime printed-part materials only, preserving authored USD and motor
state. Changes are unavailable during a connected hardware session.
Role references in labels, selectors, buttons and simulation/device controls also
carry small shared color dots. Dots have contrasting light and dark outlines so
black, white or background-matching custom colors remain visible in either theme;
the role text keeps normal readable contrast and remains accessible as text.

Implement explicit manual hardware reads/writes, superseding earlier blanket
read-only restrictions. Discovery and role assignment still perform no motor I/O.
Open only an explicitly selected, revalidated USB attachment. Use the pinned
Feetech SDK used by LeRobot: IDs 1..6, STS3215 model 777, protocol 0, 1 Mbps.
Never call high-level robot setup/connect that changes registers implicitly.
Ordinary manual controls never change motor IDs, baud, operating mode or EEPROM calibration.
The explicit setup wizard may write homing and range calibration with torque off,
following the pinned LeRobot half-turn procedure. Capture and persist original
registers before modification, verify every write and restore on cancellation or
failure where communication permits; report any unconfirmed restoration.
A calibration preview must be visibly provisional until reference, automatically
captured joint sweeps, and final operator travel/direction review are complete.
Automatic per-joint advancement writes no hardware registers; final calibration
save remains explicit. Never auto-enable torque on completing setup.

One independent worker owns each port, bounded I/O and the latest complete
timestamped sample. Read positions, voltage, temperature, load and torque state.
Report missing IDs, wrong models, packet errors, stale data and disconnects.
Read-only disconnect emits no writes; never automatically reconnect or rearm.

Import six-joint LeRobot calibration JSON. Verify IDs, ranges and homing offsets
against the motors. Raw reads work without calibration; writes require a match.
Use LeRobot degree units for body joints and percent/direction for the gripper.
Reject invalid or out-of-range measurements and targets.

Arm only with fresh healthy readings and all motors initially torque-off. Seed
goals to current positions before enabling torque; bound speed, acceleration and
torque using volatile registers. Verify writes. A held motion control admits
range-checked, rate-limited targets; release holds measured positions. Stop,
shutdown, lost UI heartbeat, stale telemetry and motor faults cancel queued
targets and attempt torque-off independently of RTX. Failed stop must remain
visibly unconfirmed: software cannot guarantee a stop through an unplugged bus
or support an arm after torque release. Reconnection always requires explicit arm.
Disabled controls must be visually distinct in both themes. Beside Enable motors,
show the exact unmet prerequisite (connection, calibration, fresh telemetry,
calibration mismatch or existing torque), plus the measured six-motor torque
state. Clicking an available action shows pending and then verified success or
failure. Release reports already-off states and never claims successful release
without fresh all-off telemetry and acknowledged writes. Keep feedback visible
in the wizard as well as the hardware panel; retain explicit enable confirmation.
Use one measured-state torque control instead of separate enable/release buttons:
all-off offers Engage motors; any-on offers Release motors. Allow cancelling a
pending engage through release. Never display a requested state as a measured
state. In calibration, engaging stays unavailable; all-off explicitly displays
Motors free, and release is actionable only when torque is on. Report unknown or
mixed torque without suggesting engagement is safe.
The stationary reference step must name the RTX view Reference guide, not Live,
and prominently state that it does not follow the arm until reference capture.
Waiting, paused, stale and live states must remain distinguishable. The hardware
panel explains missing calibration/binding or telemetry beside its mirror control.
Device Manager shows the shared outlined role color in device rows and explicit
role/port hardware buttons, with normal-contrast status text. Role assignment
edits are unavailable while physical sessions remain open. A cached hardware
window may be reused only for the same role and USB attachment; otherwise ask
the operator to close the conflicting session, without changing torque or
silently opening the old device. Report the actual active session state.
Role badges contain distinct controller (leader) and gripper (follower) symbols.
Choose black or white symbol ink for contrast against each user-selected badge
fill; retain both outer contrast rings and normal-theme adjacent text. Reuse
these badges in labels, buttons, scene rows and viewport legends. Equal colors
must still yield distinguishable roles; keep textual accessible names.
Show the selected role's reference guide throughout preparation, independently
of USB connection and reference-capture success. Keep capture faults visible
beside navigation, outside the scrolling instructions.
During explicit torque-off reference capture, clearing an existing offset may
expose an unoffset encoder outside one turn. Accept only the bounded unoffset
range reachable from a valid 0..4095 reading and signed 11-bit homing offset;
do not publish it as normal telemetry. Choose a representable homing offset
nearest the half-turn target and retain each actual reference encoder for
preview and binding. Verify recentered normal readings before proceeding.
Never modulo-wrap normal measurements or relax motor command bounds.

Virtual controls remain simulated by default. Measured two-point bindings identify
device, calibration and semantic joints; provide per-joint capture and JSON
import/export. Opt-in live viewing publishes calibrated physical poses through
the native owner while simulation is paused; simulated controls cannot move
live-owned links. Loading a virtual pose into hardware targets is explicit and
requires binding, calibration and arming, followed by held motion. Never infer
CAD zero from encoder midpoint or bake live observations into saved USD.

Verify real SDK packet bytes through emulated serial endpoints, controller/Qt
behavior, partial replies, checksums, timeouts, stale heartbeat, stop ordering,
failed arming and rate/range limits. Windows/Linux software evidence does not
replace pending physical-arm qualification.

Always show the numbered joint reference diagram throughout setup, pinned outside
the scrolling instructions with no visibility toggle. Hardware setup sub-panels
provide explicit Back actions naming their parent: Device Manager returns to the
scene, hardware controls to Device Manager, setup to Device Manager. RTX and reference views share the setup window. Navigation out of physical controls uses
the existing verified shutdown/recovery path before reopening the parent. The embedded RTX view remains visible throughout calibration.

Application-level device controllers own serial sessions independently of windows.
One attachment has one session shared by all its views. The registry rejects
conflicting role/attachment identities before opening a port. Access objects expose
telemetry to all consumers and grant writes/heartbeats to one controlling consumer;
setup takes exclusive control only with motors off and no pending engage. Other
views remain visible as observers with explicit ownership feedback. Closing an
observer cannot stop another consumer's calibration. Releasing the controlling
consumer waits for verified stop/register recovery before granting another writer;
last-consumer and application shutdown close the physical session. Calibration
and virtual binding belong to the shared device model, not a widget. Completed
setup returns control to an existing hardware view when available. Window caches
are navigation state, never the source of physical-device ownership.

The wizard preselects the saved attachment for the chosen role after discovery
and role changes, rather than silently defaulting both roles to the first port.

Loading or replacing a scene must not permanently shut down device services.
Scene loading may pause physical mirroring; registry shutdown belongs only to
accepted application exit or finalization. Hardware controls remain available
after the initial scene load and subsequent document changes.

## Live co-session diagnostics

An explicitly enabled local diagnostic service (`LERTX_DEBUG=1`) exposes versioned
JSON snapshots, bounded event/timing history, current RTX frames and application
window captures without desktop occlusion. Bind only IPv4 loopback on an ephemeral
port with a per-run bearer token in a user-local discovery file. Reject browser
origins and unauthenticated requests. Remove discovery on shutdown. Diagnostics
must never open a serial port, send motor commands or evaluate arbitrary code.
Snapshots include role/port, measured encoder values, sample age and sequence,
control owner, wizard step/sweep/next requirement, mapped joint angles, native
publication ordinal, rendered pose and frame identity, pending work and timings.
Offer a CLI for discovery, observation, capture and bounded camera/frame-rate
commands. Marshal GUI access to Qt and native access to its existing worker;
use bounded queues/history and preserve application errors in diagnostic events.
Enable tuning for the current session only, validating limits and reporting results.

The persistent setup diagram must use the selected arm's actual model reference
pose, including the leader trigger or follower claw. Keep selected-joint progress,
measured travel and the next required action visible outside scrolling content.
Return-to-endpoint capture must explain the target and remaining distance.

Physical and simulated motion must continue after selecting or clearing joint
highlights. For the pinned attached OVRTX backend, refresh the local transforms
of previously highlighted renderable descendants when publishing an ancestor
pose; ancestor-only writes otherwise leave highlighted meshes visually frozen.
Keep local offsets and runtime edits intact and clear refresh identities on scene
replacement. Verify substantial arm silhouette changes after highlight, motion,
and deselection; noise-only frame differences do not satisfy motion acceptance.

Device Manager provides role- and port-labelled Calibrate buttons that preselect
that exact attachment in the wizard. Remove the separate scene setup action.
Keep RTX, the reference diagram, selected-joint progress and navigation in one
window, with scrolling limited to instructions and controls. Transfer the embedded
RTX view to hardware controls after saving. A stable return at or beyond the first
held endpoint counts as a return sweep: an early interior pause must not require
hitting an invisible narrow target. Show directional remaining travel and retain
the held return endpoint in the captured range. Require the existing minimum span,
stable dwell, fresh selected-joint samples, torque off and a current RTX frame.

During active torque-off calibration capture only, wrist-roll feedback may span
-2047..6142 encoder ticks because firmware reports signed positions beyond one
turn. Preserve those coordinates for sweep continuity and provisional preview;
do not modulo-wrap them. Other joints and all normal telemetry/commands retain
0..4095 validation. Intersect the wrist binding with commandable 0..4095 travel.
Before committing calibration, require all joints back inside normal coordinates
and explain how to return the wrist; do not discard progress for a rejected UI
save attempt. Out-of-envelope readings and torque-on samples still fault.
Support and reference alignment are dedicated wizard steps with prominent primary
actions, not checkboxes hidden in scrolling instructions. The support action
explicitly confirms support and, if needed, releases torque; wait for fresh
acknowledged OFF feedback before advancing. The reference action explicitly
confirms alignment and captures it only once a current guide is visible.
