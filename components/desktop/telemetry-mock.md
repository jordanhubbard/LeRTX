---
name: Hardware-free telemetry mock
summary: Explicit simulated read-only leader and follower streams without physical device access
kind: feature
---
# Hardware-free telemetry mock (follow-on)

### Requirement: Explicit isolated simulated devices

Devices offers an explicit Open telemetry mock action. The mock panel is always
labeled SIMULATED, starts disconnected and is isolated from persistent USB roles.
Provide independent leader/follower connection and frozen-stream controls, five
arm joint degree controls and a gripper-percent control. These values are test
inputs, not physical calibration or robot joint-limit assertions. No serial
ports, network, LeRobot imports or motor commands are used by the mock.

#### Scenario: Operator opens the mock panel

- **WHEN** the operator chooses Open telemetry mock from Devices
- **THEN** both roles start disconnected with visible SIMULATED labels
- **AND** physical USB role assignments and ports remain untouched

### Requirement: Validated read-only streams and lifecycle

Use immutable complete samples with source identity, role, monotonically
increasing sequence and monotonic timestamp. A read-only backend interface
exposes connect, read and disconnect, with no actuator-write operation. Reject
wrong-source/role, out-of-order, nonfinite, incomplete and future-dated samples
before replacing the latest valid reading. Show disconnected, awaiting sample,
live simulated and stale states distinctly; stale samples may remain visible
but never look live. Freeze stops new samples without pretending to disconnect.
Closing the panel disconnects both mock streams and stops its timer. Mock state
must not persist as USB assignments or verified workspace metadata. A mock panel
is not proof of real LeRobot integration or rendered SO-101 joint synchronization.

#### Scenario: Stream freezes or disconnects

- **WHEN** a connected stream stops delivering samples
- **THEN** its last pose becomes visibly stale after one second
- **AND** disconnect and reconnect cannot present the previous sample as live

#### Scenario: Invalid sample or panel closure

- **WHEN** a sample has invalid identity, ordering, timestamp or joint values
- **THEN** it does not replace the latest valid sample
- **AND** closing the panel disconnects both roles and stops polling
