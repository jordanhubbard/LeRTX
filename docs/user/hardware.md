# Connecting the SO-101 arms

LeRTX now implements manual USB reads and writes for a configured SO-101 arm with
six Feetech STS3215 motors, IDs 1–6, position mode and a 1 Mbps bus. Software tests
use an emulated arm; physical qualification on the user's arms is still pending.

## First connection

For an assembled arm with motor IDs already assigned, choose **Set up real arms**
in the toolbar. The wizard walks through connection, support/torque release, a
reference pose, six individual joints, review and saving. Its right-hand 3D view
shows the same native rendering as the workspace. The numbered diagram locates
each joint: base turn, upper-arm hinge, middle hinge, wrist tilt, wrist twist and
claw (or the leader's trigger). A green ring identifies the joint you actually
move; the gold number identifies the joint for the current step.

The reference pose is initially stationary: copy it with the physical arm, then
confirm and capture it. Live 3D mirroring begins after that capture. Move each
joint gently through both ends of its comfortable travel, check the mirrored
direction, and confirm it. The travel indicator means movement was detected;
you still need to check the full travel yourself. Use **Reverse** if needed.
Review all six joints and save. **Finish and open live hardware controls** keeps
the connection and enables measured live viewing. Motors stay off throughout.
Cancel restores the original calibration when the bus remains available.

To use an existing LeRobot calibration instead:

1. If the motors have not been configured, complete the official
   [LeRobot SO-101 setup and calibration](https://huggingface.co/docs/lerobot/so101)
   first. LeRTX does not assign motor IDs; its explicit wizard can write homing
   offsets and measured limits with torque off and a register backup. Keep the
   separate leader and follower calibration JSON files.
2. Connect motor power and USB. The bus adapter must appear as a COM port on
   Windows or a serial device on Linux. Install the adapter manufacturer's driver
   if Windows does not expose a COM port. On Linux the user needs serial-device
   access; the app does not change device permissions or run as administrator.
3. Open **Devices**, scan, select the adapter and explicitly assign its role.
   Choose **Open hardware controls**, then **Connect read-only**. Verify all six
   encoder readings. Connecting does not change torque or motor settings.
4. Choose **Import LeRobot calibration** for that specific arm. LeRTX checks the
   six IDs, encoder ranges and homing offsets against the motor registers.
   Body-joint readings use LeRobot's degree convention; gripper readings use
   normalized percent. These degrees are not automatically the USD joint angles.

## Manual motor movement

Support the arm, clear its workspace and keep its motor power switch accessible.
**Enable motors** seeds goals from current readings before enabling torque.
If torque was already on, use **Stop** first; LeRTX will not adopt another
controller's existing goals. Arming uses at most 100 encoder ticks/second
(about 8.8 degrees/second), acceleration value 10, and torque-limit value 300/1000.
These conservative initial limits are not mechanical or collision qualification.

Enter a target beside a joint and click **Set target**. Hold **Move to targets**
to execute it. Releasing the button cancels remaining travel and holds the current
measured position. **Stop** releases torque on all six motors and requires a new
explicit enable. Disconnecting or closing an armed panel also attempts torque-off;
a read-only disconnect performs no register writes.

Bus errors, motor fault flags, temperatures at or above 60 °C, excessive tracking
error, stale samples or a missing UI heartbeat cancel motion and attempt torque-off.
An unplugged USB cable can prevent that command from reaching the motors. A
**STOP UNCONFIRMED** message means use the physical power switch. Torque release
does not support the arm against gravity. This software control is not a physical
emergency-stop circuit and cannot guarantee shutdown after a process or power failure.

## Connecting physical joints to the scene

LeRobot encoder calibration does not determine CAD zero and direction. With a
matching calibration loaded and torque off, use **Measure virtual binding**.
For each joint, move it to two distinct known poses, enter the corresponding
virtual angle and capture A and B. The gripper's physical measurements are percent;
its virtual values are radians internally, displayed as degrees in this dialog.
Save the measured binding. It is tied to this USB identity, role and calibration.
Adapters without a unique serial number require a new session binding after reconnect.

**Show measured physical joints in the scene** applies these measurements through
the articulated forward kinematics and pauses simulation. Simulation Play, Reset
and joint manipulation are blocked while live viewing owns the robot poses.
Stale measurements stop live viewing. The authored USD remains unchanged.

To command a virtual pose, turn live viewing off, position the simulated arm,
then choose **Use virtual pose as targets** in its armed hardware panel. This
only loads targets; hold **Move to targets** to execute them. Unmeasured angles
outside the binding or calibration are rejected. Ordinary viewport dragging
never commands hardware directly. Base/world registration and obstacle geometry
remain unverified; this is manual joint control, not collision-safe planning.

## Selecting and manipulating a simulated joint

Click an arm link, then use the **Selected joint** slider in Robot simulation,
or hold the left mouse button on the link and drag right/up or left/down.
The connected links move through the actual articulation and joint limits.
Disable following to manipulate the follower independently. Alt-drag orbits;
right-drag pans; the wheel zooms. There is no free-space gripper IK gizmo yet.
