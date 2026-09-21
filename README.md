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

On a provisioned Linux or Windows NVIDIA GPU machine, use the Python environment
containing the pinned SDKs in `desktop/source/requirements.txt`:

```sh
cd desktop/source
python main.py '[{"command":"launch"}]'
```

This opens the actual Qt/RTX workspace, not the harness below. Wait for
`Native: ready`. Use Play/Reset for Newton physics, the hierarchy and inspector
to edit objects, and Save As to retain an untitled scene. Settings configures the
LLM; its API key starts blank. Reconstruct Photo imports an explicitly unverified
draft. Devices includes USB candidate discovery and a hardware-free telemetry mock.

See [desktop notes](desktop/README.md) for prerequisites and limitations. This is
a development application: verifier-owned admission and end-user packaging are
not complete. Mock telemetry does not yet drive rendered robot joints; physical
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
