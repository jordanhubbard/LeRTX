---
name: SO-101 USB hardware controls
summary: Explicit telemetry, bounded motor writes and torque-off guided calibration
kind: feature
---
# SO-101 USB hardware controls

Setup must persistently name the selected Leader (hand-operated controller) or
Follower (robot hand), including during joint capture and in the RTX companion
window. Use the same role palette in the diagram, selection banner, viewport
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
