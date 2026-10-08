# Design traceability

<!-- literate-ai:authority-reviewed sha256:b0ad04b5442494ac78e4cfbd8817600dcdc6f6297c98ad91a830fc04850a2caf -->

[Project guide](../README.md) → design traceability

Behavior belongs in Component specifications; target variance belongs in Flavors;
conversion technique belongs in exact skills; execution order belongs in workflows;
model eligibility belongs in routing; validation and authorization remain framework
policy. The manifest selects the source-intelligence provider, while its local database
remains
derived evidence outside source authority. Changes should update the owning artifact,
its nearby explanation or diagram,
and an end-to-end test. Illustrations aid understanding; prose requirements and
acceptance scenarios remain normative. See the [project map](../user/project-layout.md).

The desktop joint-control contract owns right-click sliders and middle-button
panning on every platform. The Qt input regression and native context-window
verification cover that interaction through the existing simulated command path;
physical controls retain their separate hardware workflow.

The desktop application's guided-setup contract owns the integrated reference and live RTX views,
persistent model-derived joint-location diagram, selected-motor sweep detector, automatic joint
advancement and bounded preview queue. The hardware guide describes the same
reference/sweep/final-review workflow. Stable endpoints and a return visit are
operator-demonstrated data, not software detection of hard stops. Emulated
SDK/Qt tests and the native six-joint frame-change regression provide software
evidence; they do not replace qualification on the operator's physical arm.

The hardware contract also owns persistent role identity and configurable printed
part colors. One palette drives Qt labels/diagrams and linear-light USD material
inputs in the runtime snapshot; authored scenes and hardware roles are unchanged.
Legacy profile migration adds only the two new color defaults.

Hardware torque feedback derives from measured registers and serial stop-request
completion, not button intent. The UI exposes unmet engagement/mirroring gates;
the stationary reference remains explicit until capture supplies a mapping.

Reference capture accepts bounded extended encoder feedback only inside its
torque-off homing transaction. It selects a representable offset and carries the
actual per-joint reference into preview and binding math; normal measurements
and commands keep their original bounds. Physical capture/restore checks cover
both arms, including the follower wrist's 4530-tick unoffset feedback.

Device role identity is carried by contrasting controller/gripper badges, readable
text and explicit port labels. Cached hardware panels must match both role and
attachment; active sessions block assignment edits. Device and Qt regressions
and native dark/light screenshots are recorded in `verification/device-role-review.json`.

The setup joint map is pinned outside the scrolling instructions. Explicit parent
navigation preserves RTX progress and waits for hardware shutdown before returning
to Device Manager. Setup/hardware/device Qt verification passes 37 tests.

The application now injects a Qt-independent device registry. Controller-owned
serial sessions, shared calibration/binding, scoped writer access and asynchronous
recovery replace per-window serial ownership. See `application-review.md` for
findings across all application layers and the staged follow-up plan. Controller,
hardware, calibration and Qt verification runs 104 tests (one existing skip),
plus a completed setup handoff to an existing observer panel; see
`verification/device-controller-review.json`.

Scene opening preserves the application device registry; only accepted application
exit and finalization permanently close it. The regression test opens initial and
replacement scenes, then opens controls and connects the emulator read-only.
The hardware/controller/device Qt suite passes 29 tests.

Live co-session diagnostics are application-owned, opt-in and authenticated on
loopback. They marshal Qt capture and validated tuning through existing owners,
record bounded telemetry/command/frame histories and expose a local CLI. The
highlighted-articulation regression requires substantial visual changes through
selection and deselection; refreshing touched mesh-local transforms repairs the
pinned renderer's ancestor-update issue. Guided setup keeps sweep requirements
visible and uses role-specific projected CAD geometry for its reference diagram.
