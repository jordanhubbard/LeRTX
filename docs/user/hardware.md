# Connecting the SO-101 arms

The setup header and embedded RTX view always name the selected arm: **Leader**
is the hand-operated controller; **Follower** is the robot hand. Their color key
matches the rendered printed parts. Before connecting, choose a role and use
**Match printed-part color…** to match your own prints. Colors are saved for future
sessions; labels still distinguish the arms when their colors are the same.
Outlined badges identify roles in selectors, buttons, simulation controls, device
assignments and status messages: a controller for Leader and a gripper for Follower.
The symbol uses contrasting black or white ink; surrounding text keeps the theme
color. Light and dark rings keep badges visible against either theme, and the
different shapes distinguish roles even with identical printed-part colors.
Device Manager names each role and USB port on its control button. Close existing
hardware controls before changing assignments; an old window cannot be reused
for a different role or device.

LeRTX now implements manual USB reads and writes for a configured SO-101 arm with
six Feetech STS3215 motors, IDs 1–6, position mode and a 1 Mbps bus. Software tests
use an emulated arm; physical qualification on the user's arms is still pending.

## First connection

For an assembled arm with motor IDs already assigned, open **Devices**, assign
its role, then choose **Calibrate Leader** or **Calibrate Follower** beside its
USB port. The wizard preselects that device and walks through connection,
support/torque release, a reference pose, six joints, review and saving.
The RTX view and reference diagram stay together in one window. RTX displays the
stationary **Reference guide**, then switches to **LIVE** after reference capture
and mirrors all six measured joints. Use its turn, zoom and framing buttons to
inspect the motion while keeping instructions and progress visible.
The always-visible reference-only numbered diagram locates
each joint: base turn, upper-arm hinge, middle hinge, wrist tilt, wrist twist and
claw (or the leader's trigger). The role color identifies the selected diagram joint.

First support the arm with its power switch within reach, then choose the
prominent **Arm supported — continue** action. If motors are engaged, this
releases them and waits for verified OFF feedback before advancing.

The reference pose is initially stationary: copy it with the physical arm, then
choose **Arm matches reference — capture pose**. Neither step uses a checkbox. Live 3D mirroring begins after that capture. For each
selected joint, move gently to one comfortable end and pause, move to the opposite
end and pause, then return to the first end and pause. Returning farther toward that end also
counts, so an early pause does not trap you at a narrow encoder target. Holds take about a second.
The wizard advances automatically after a repeatable sweep and a current 3D frame.
Support the arm naturally: other joints may move, but only the selected joint
counts toward the step. Small encoder jitter and incidental movement do not count
as a sweep. If more travel is needed, continue toward the opposite comfortable
end without forcing it. Use **Reverse** if the preview direction is wrong.
The app records the endpoints you demonstrate; it does not detect hard stops.
Wrist feedback may cross zero during torque-off calibration without losing your
completed joints. If it is outside normal command coordinates at final review,
the wizard asks you to turn the wrist back toward the reference pose before saving.

Review all six joints, then choose **Save calibration to arm and files**. This
action confirms your review; there is no extra checkbox. Use Back to correct a
joint. **All 6 joints captured** means capture is complete; **Calibration saved**
confirms the hardware commit. If Save is blocked, the pinned guidance explains
which joint to return, shows its reading and highlights it in the diagram.
**Finish and open live hardware controls** keeps the embedded 3D view,
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
The measured torque state appears above one control: **Engage motors** when all
six are off, or **Release motors** when any are on. Engage seeds goals from current
readings before enabling torque and asks for confirmation. If unavailable, the
reason appears beside it; disabled controls have a muted fill and dashed border.
During calibration, the support step reports measured torque state and its
**Arm supported — continue** action waits for verified release.
If torque was already on, use **Release motors** first; LeRTX will not adopt another
controller's existing goals. Arming uses at most 100 encoder ticks/second
(about 8.8 degrees/second), acceleration value 10, and torque-limit value 300/1000.
These conservative initial limits are not mechanical or collision qualification.

Enter a target beside a joint and click **Set target**. Hold **Move to targets**
to execute it. Releasing the button cancels remaining travel and holds the current
measured position. **Release motors** releases torque on all six motors and requires a new
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
The control explains missing calibration, binding or fresh telemetry. A raw
read-only connection alone cannot establish physical-to-virtual joint coordinates.

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
middle-drag pans; the wheel zooms. There is no free-space gripper IK gizmo yet.

The joint diagram stays above the scrolling instructions throughout setup. Back
buttons name the parent panel. Leaving setup cancels it with the existing register
recovery; leaving hardware controls closes its session before reopening Device
Manager. Leaving setup also returns to Device Manager after register recovery.

You can open setup while this arm's read-only hardware panel is open. Both use the
same device connection. During setup, the hardware panel shows shared telemetry
and names setup as the controller; its motor commands are unavailable. Release
engaged motors explicitly before entering setup. Closing an observing panel does
not interrupt calibration. Cancel restores the prior registers before returning
control; finishing setup reuses the hardware panel with the new calibration.
Use Back to revisit support or the reference pose; returning from the first joint
restores original calibration before another reference capture.

## Camera selection on Windows and Linux

Device Manager lists camera inputs supplied by Qt Multimedia. Select a candidate
and click **Preview selected camera**. Move an object in front of the camera mounted
on your arm to identify its live feed, then click **Use this camera**. The same feed
appears beside RTX in the workspace and integrated arm previews. **Disable camera**
stops capture; no audio is opened and preview does not record or upload video.

Windows device interface IDs and Linux `/dev/v4l/by-id` identities are remembered.
Linux cameras without a stable identity are labelled session-only: select them again
after reconnecting or restarting. Device numbers such as `/dev/video0` are never
remembered as permanent assignments. A remembered selection does not automatically
start capture. Explicitly preview it after startup. Unplugging clears the image;
another camera is never silently substituted. Permission, busy-device and missing
frame errors appear in the camera panel.

## Record, follow and replay

Open **Robot session** from Devices or the toolbar. Choose leader, follower, or both,
then **Connect assigned arms**. The session shares the application's device controllers
and loads saved calibration and binding by device identity. Finish calibration or
release engaged motors before changing controllers.

**Start joint recording** records measured joint positions without engaging motors.
Stop and **Save sequence** to write a portable JSON recording, with device identities,
calibration, binding and timestamps. Recordings are bounded to 72,000 frames or one
hour. **Open sequence** and **Preview sequence in RTX** work without moving hardware.

**Start follower following leader** asks before engaging the follower; the leader
remains torque-free. **Play sequence on follower** requires recorded follower data
matching that device and calibration. Playback is slowed where necessary to respect
the motor speed limit. **The Signal** and **Danger** are available in Robot action
profiles: preview in RTX, or explicitly run the pose on the follower. Pose/follow
targets are restricted to measured travel; this is not collision avoidance.

Keep the session focused during physical motion. **STOP**, loss of focus, stale
telemetry or closing the session stops motion and requests motor release. Support
the arm before release. The leader receives no motor commands from this session.
