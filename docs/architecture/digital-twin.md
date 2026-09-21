# Photo reconstruction and follow-on physical twin

Owners: TWIN-001 (photo reconstruction) and ROBOT-001 (physical follow-on) in
[active work](../roadmap/active-work.md). This is the implementation contract
for milestone-three Astra photo-to-USD reconstruction and separately scoped
follow-on physical synchronization, not a claim of implemented behavior.

## Workspace from a photo

The user explicitly selects and previews one image before sending it to the
configured Intelligence endpoint. Show the destination and session-only key
policy. Never upload automatically on open or connection testing. Requests run
off the UI thread, are size/time bounded, and support cancellation that discards
late replies without claiming server cancellation.

The model returns a bounded scene description, not executable Python, arbitrary
USD source, plugin declarations, or remote asset references. Validate the complete
response before local USD construction. The scene interchange must describe named
objects, transforms, estimated dimensions, confidence/uncertainty, geometric
representations (including bounded meshes), and any occluded/unobserved regions.
Malformed data must leave the current workspace untouched. Locally constructed
USD remains editable through the existing inspector and Save workflow.

Every photo-derived scene carries persistent unverified provenance. Estimated
dimensions are not measurements. User-entered measured references and
registration controls belong to follow-on physical-twin work; changing geometry
must invalidate affected verification when that workflow is implemented.
Never infer that a verified scale establishes complete collision geometry or safe
robot movement. Display uncertainty and missing geometry in the workspace.

## USB and joint telemetry (follow-on, outside milestone three)

Enumerate serial USB candidates without opening arbitrary ports. Use stable USB
identity where available; ambiguous or missing serial identities require user
confirmation. Do not infer leader/follower role from enumeration order or a COM
number. Persist confirmed identity-role assignments, show hotplug/disconnect
status, and reacquire only an unambiguous matching device. Discovery and polling
must not block rendering or the UI.

Use a pinned LeRobot motor-bus adapter, not a replacement servo protocol.
Inspection of upstream revision
`30074f7f1358b3c015ae1750017200e86e9c4eb6` found that the high-level
[SO follower connection](https://github.com/huggingface/lerobot/blob/30074f7f1358b3c015ae1750017200e86e9c4eb6/src/lerobot/robots/so_follower/so_follower.py)
configures motor registers even when calibration is skipped. The adapter must
therefore use the reviewed bus-level read path. Connection failure and disconnect
must close the serial handle without torque writes; the upstream
[bus disconnect](https://github.com/huggingface/lerobot/blob/30074f7f1358b3c015ae1750017200e86e9c4eb6/src/lerobot/motors/motors_bus.py)
defaults to disabling torque, which is not read-only. Do not invoke setup,
calibration writes, goal-position writes, or high-level robot connect/disconnect.
Dependency installation still requires a verified, pinned closure; this reviewed
revision is not yet an admitted runtime dependency.

Import operator-selected calibration without changing motor registers. Check
model, IDs, calibration compatibility and finite readings before publishing.
Five arm joints and the gripper need explicit unit and joint-limit conversion;
gripper percentage is not a rotational degree measurement. The robot geometry
must use a sourced, licensed SO-101 kinematic model with reviewed joint axes,
zero offsets and frame registration, not a generic six-link illustration.

Keep only the latest complete timestamped sample per device. Stale/disconnected
poses remain visibly stale and never masquerade as current telemetry. Publish
robot transforms through the same native worker and ordinal coordinator as
camera/physics changes. Physical telemetry controls the twin only: it does not
command a follower to track a leader. Newton must not independently drive links
currently controlled by telemetry.

Acceptance requires both injected failure-path tests and actual leader/follower
joint motion observed against rendered poses. Missing hardware or calibration
is an unverified physical gate, not an excuse to pass using synthetic readings.
