# LeRTX

A digital-twin workspace for LeRobot devices, beginning with the SO-101 leader
and follower. Product targets are Linux and Windows machines with NVIDIA GPUs.

Created with Literate AI. Specifications remain authoritative; the operator has
approved retaining and directly repairing the generated desktop source. See
[project goals](PROJECT.md), [active work](docs/roadmap/active-work.md),
and the [runtime contract](docs/architecture/runtime.md).

## Milestones

1. Application harness created, generated, and verified through `litai`.
2. A running application rendering with OVRTX and OVStage, with Newton physics.
3. Astra photo-to-USD reconstruction, with editable drafts and explicit uncertainty.

## Run the development desktop

Use Windows 11 x86-64 or Linux x86-64/ARM64 with a working NVIDIA driver and
Python 3.11 or `uv`. From the repository root:

```sh
python desktop/manage.py setup
python desktop/manage.py install
python desktop/manage.py run
```

This opens the actual Qt/RTX workspace, not the harness below. Wait for
`Native: ready`. Use Play/Reset for Newton physics, the hierarchy and inspector
to edit objects, and Save As to retain an untitled scene. Settings configures the
LLM; its API key starts blank. Reconstruct Photo imports an explicitly unverified
draft. Devices includes USB candidate discovery and a hardware-free telemetry mock.

Use `python3` if needed on Linux. `doctor` checks the installation, `test` runs
the full suite, and `package` creates a reproducible source/setup ZIP. Current
160-test suites pass on Windows 11, Linux x86-64, Linux ARM64 and Omarchy;
see the [platform evidence](verification/prototype-platform-review.json).

See [desktop notes](desktop/README.md) for prerequisites and limitations. This is
a development prototype. Fresh Windows 11 and Omarchy installations pass the full
160-test suite and native desktop launch checks.
Mock telemetry does not yet drive rendered robot joints; physical
servo synchronization, calibration and actuation are not implemented.

## Harness workflow

```sh
litai project validate
litai lock components/harness --target host
litai rebuild components/harness --allow-host-execution --update-receipt
litai verify
litai build components/harness --target host
litai run components/harness --target host -- '[{"command":"info"}]'
```

The harness reports planned integrations and `runtime_ready: false`; it is not
the graphical application. The macOS bootstrap host cannot run the NVIDIA desktop.
