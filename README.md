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

With GNU Make installed, from the checkout on Windows or Linux:

```sh
make run
```

This prepares dependencies when needed and launches LeRTX. Windows uses the
PowerShell launcher below; Linux uses `python3` (override with `make run
PYTHON=python3.11` if needed). On macOS the same target exits with an explanation:
the pinned NVIDIA renderer has no Mac build. It does not create an environment
or download incompatible SDKs there.

On Windows, from PowerShell in the checkout, build and run with one command:

```powershell
.\run.ps1
```

This prepares the isolated environment and checks a real GPU frame on first run,
then opens LeRTX. Later runs reuse successful setup until the pinned dependency
inputs change. Requires a real Python 3.11/3.12 or `uv` and an NVIDIA driver.
If PowerShell blocks scripts, use `python desktop/manage.py run` instead.
To open a scene: `.\run.ps1 -Scene C:\scenes\workspace.usda`.

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
draft. **Devices** assigns leader/follower USB roles, opens calibration and hardware
controls, and selects a USB camera using its live preview. The enabled camera appears
above the RTX view. **Robot session** records and saves measured joint sequences,
previews poses/sequences, and explicitly starts follower tracking or playback.

Use `python3` if needed on Linux. `doctor` checks the installation, `test` runs
the full suite, and `package` creates a reproducible source/setup ZIP. Baseline
160-test suites passed on Windows 11, Linux x86-64, Linux ARM64 and Omarchy;
see the [platform evidence](verification/prototype-platform-review.json).

See [desktop notes](desktop/README.md) for prerequisites and limitations. This is
a development prototype. Baseline fresh Windows 11 and Omarchy installations passed the
160-test suite and native desktop launch checks.
Physical calibration, measured RTX synchronization and bounded follower motion are
implemented. Both real-arm calibrations were saved and the operator confirmed the
interactive workflow. Broad hardware qualification and collision-aware autonomous
execution remain separate work. See the [hardware guide](docs/user/hardware.md).

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
