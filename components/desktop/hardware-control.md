# SO-101 USB hardware controls

Implement explicit manual hardware reads/writes, superseding earlier blanket
read-only restrictions. Discovery and role assignment still perform no motor I/O.
Open only an explicitly selected, revalidated USB attachment. Use the pinned
Feetech SDK used by LeRobot: IDs 1..6, STS3215 model 777, protocol 0, 1 Mbps.
Never call high-level robot setup/connect that changes registers implicitly.
Never change motor IDs, baud, operating mode or EEPROM calibration.

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
