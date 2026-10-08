"""Operator help for the current workspace and physical-device workflow."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton
from .role_ui import role_html

HELP_HTML = """
<h1>Getting started with LeRTX</h1>
<p><a href="#devices">Connect and calibrate</a> · <a href="#save">Review and save</a> ·
<a href="#controls">Hardware controls</a> · <a href="#scene">Simulation and workspace</a></p>
<a name="devices"></a><h2>Connect and calibrate real arms</h2>
<p><b>Leader</b> is the hand-operated controller; <b>Follower</b> is the robot hand.
Role badges, names and printed-part colors identify both, even when their colors
match. Choose <b>Match printed-part color…</b> in setup before connecting to change colors.</p>
<ol>
<li>Open <b>Devices</b>, scan USB adapters and assign each role explicitly.
Each control names its role and USB port. Choose <b>Calibrate Leader</b> or
<b>Calibrate Follower</b> for that device.</li>
<li>Choose <b>Connect and check six motors</b>. This is for assembled SO-101 arms
with motor IDs 1–6 already configured at 1 Mbps; LeRTX does not assign motor IDs.</li>
<li>Support the arm and keep its power switch within reach. Choose
<b>Arm supported — continue</b>. If needed, this releases motors and waits for
verified torque OFF before advancing.</li>
<li>Match the stationary reference pose, then choose
<b>Arm matches reference — capture pose</b>. This explicit action backs up the
original registers and sets homing offsets. Live mirroring begins after capture.</li>
<li>For each highlighted joint, move to a comfortable endpoint and pause, move to
the opposite endpoint and pause, then return to the first end and pause. Holds take
about a second. Returning farther toward the first end also counts. Only the selected
joint advances the step; other joints may move while you support the arm.</li>
</ol>
<p>The wizard advances automatically after sufficient selected-joint data and a
current RTX frame. The numbered reference diagram and live RTX view share one
window. Use the camera controls to inspect the arm and <b>Reverse this joint in
the preview</b> if needed. The diagram is a reference, not a live pose display.
Never force travel or wind the wrist cable around the arm.</p>
<a name="save"></a><h2>Review and save</h2>
<p><b>All 6 joints captured · Save to finish</b> means measurement is complete.
Review the live motion, then choose <b>Save calibration to arm and files</b>.
Save confirms your review; there is no additional checkbox. Use <b>Back</b> to
correct a joint.</p>
<p>If Save is disabled, read the visible requirement above the controls. Wrist
feedback can extend beyond one turn during torque-off capture. Before saving,
return wrist twist toward its reference pose until its reading is within
<b>0–4095</b>. The diagram highlights it and the instruction shows its current
reading. All captured joints are retained while you do this. This is not a missing
joint or an unfinished sweep.</p>
<p><b>Calibration saved</b> confirms the hardware save and exported files.
<b>Finish and open live hardware controls</b> keeps the connection, verified
calibration, binding and embedded RTX view. Motors remain off.</p>
<p>Each run stores <code>calibration.json</code>, <code>binding.json</code>,
<code>setup.json</code> and <code>original-registers.json</code> under the application
configuration directory's <code>calibration</code> folder. The hardware panel shows
the saved calibration path. The binding belongs to that device, role and calibration;
keep leader and follower files separate. Workspace <b>Save As</b> saves the USD scene,
not robot calibration. Cancelling unfinished setup restores original registers
when communication permits; it does not save the new captures.</p>
<a name="controls"></a><h2>Hardware controls</h2>
<p>In <b>Devices</b>, choose the named arm's <b>Open controls</b> button. For an
existing calibration, connect read-only and use <b>Import LeRobot calibration…</b>.
The file must match the motor registers. For a physical-to-virtual mapping created
outside the wizard, use <b>Measure virtual binding</b>.</p>
<p><b>Show measured physical joints in the scene</b> requires fresh telemetry and
a matching calibration and binding. Live physical viewing pauses simulation;
viewport gestures never directly command hardware.</p>
<p>Support the arm before releasing torque. The motor control reflects measured
state: <b>Engage motors</b> when off, <b>Release motors</b> when on. Engagement asks
for confirmation and requires verified calibration. Set joint targets, then hold
<b>Move to targets</b> to execute them. Releasing Move holds the current position;
Release motors makes the arm free. <b>Use virtual pose as targets</b> only loads
targets; held Move is still required.</p>
<p>Setup and hardware views share one device connection. During calibration,
other hardware views observe telemetry while setup owns control. Back buttons
return to the parent panel after required cleanup. If telemetry becomes stale,
check USB and power. If <b>STOP UNCONFIRMED</b> appears, support the arm and use its
physical power switch.</p>
<h2>USB camera</h2>
<p>In <b>Devices</b>, select a camera and choose <b>Preview selected camera</b>.
Move something in front of the mounted camera to identify its live image, then
choose <b>Use this camera</b>. The feed appears above the RTX view. <b>Disable camera</b>
stops capture. Stable selections are remembered on Windows and Linux; Linux cameras
without a stable USB identity are marked session-only. Preview explicitly after
restart or reconnect. Camera preview does not record video.</p>
<h2>Robot sessions and action profiles</h2>
<p>Open <b>Robot session</b> from Devices or the toolbar, choose which arms to use,
then <b>Connect assigned arms</b>. Saved calibration is loaded by device identity.
<b>Start joint recording</b> captures measured motion without engaging motors.
Stop recording, then <b>Save sequence</b>. Open a saved sequence to preview it in RTX.</p>
<p><b>Start follower following leader</b> explicitly engages the follower after
confirmation. Keep the leader free. <b>Play sequence on follower</b> requires a
recording containing this follower with its current calibration. Playback slows
as needed to respect motor speed limits. <b>STOP</b>, loss of focus, or stale
telemetry stops motion and requests follower release.</p>
<p><b>The Signal</b> and <b>Danger</b> are available under Robot action profiles.
Preview poses in RTX, or explicitly run a pose on the calibrated follower.
Targets are limited to measured travel. Support the arm before releasing motors.
These are joint motions, with no collision avoidance.</p>
<a name="scene"></a><h2>Simulation and workspace</h2>
<p>Use <b>Robot simulation</b> to choose joint targets, then Play. The simulated
follower can track the simulated leader; disable following to move it independently.
Pause holds the pose; Reset restores the workspace.</p>
<p>Drag an arm link with the left or right mouse button to move its selected joint,
or use its labelled joint slider. Controls also work while paused. Alt-left-drag
orbits, middle-drag pans, and wheel or trackpad scroll zooms. Select other objects
to edit Translate/Rotate/Scale in the Inspector, then Apply transform.</p>
<p>Use <b>File → Save As</b> for workspace edits. Photo reconstruction uploads only
after explicit confirmation and produces a draft with unverified dimensions.
Models, contact hulls and workspace registration do not establish collision-safe
physical motion.</p>
<p><a href="https://github.com/jordanhubbard/LeRTX/blob/main/docs/user/hardware.md">Detailed online hardware guide</a> ·
<a href="https://github.com/jordanhubbard/LeRTX/blob/main/docs/user/live-debugging.md">Live debugging guide</a></p>
"""


def build_help_dialog(owner):
    dialog=QDialog(owner)
    dialog.setWindowTitle('Getting started · LeRTX')
    dialog.resize(860,720)
    layout=QVBoxLayout(dialog)
    browser=QTextBrowser(dialog)
    browser.setAccessibleName('LeRTX user guide')
    browser.setOpenExternalLinks(True)
    browser.setHtml(role_html(HELP_HTML,owner.profile,rich=True))
    layout.addWidget(browser)
    close=QPushButton('Back to workspace',dialog)
    close.clicked.connect(dialog.close)
    layout.addWidget(close)
    return dialog
