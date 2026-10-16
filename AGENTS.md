# Literate AI agent entry point

Read and follow `SKILL.md` before changing this framework or any project that uses its
canonical taxonomy. Treat that file as the provider-neutral onboarding authority.

For RTX viewports, USD robot assets and simulation, also read and follow
`docs/architecture/nvidia-methodology.md` and its pinned NVIDIA skill references.

## Inspect the running app

For calibration, physical-to-virtual motion, camera or UI debugging, first read
`docs/user/live-debugging.md` and inspect the live app before asking the operator
to transcribe status labels. From the repository root on Windows:

```powershell
$env:PYTHONPATH='desktop/source'
.venv/Scripts/python.exe -m lertx.debug_client state
.venv/Scripts/python.exe -m lertx.debug_client ui
.venv/Scripts/python.exe -m lertx.debug_client watch --seconds 30 --output trace.jsonl
```

Use an ignored local work directory for traces and captures. The guide also covers
Linux commands, events, native frames and window captures. Use `--pid` to select
the intended app when multiple instances are running. If no live endpoint exists,
enable diagnostics with `LERTX_DEBUG=1` when launching the app; an existing process
may require an operator-coordinated restart. Never print discovery credentials.

Distinguish USB discovery from an open telemetry session: an empty `devices`
array means the app has no active device controllers, even when Device Manager
lists assigned ports. Enabling diagnostics is the operator's opt-in to full LLM
development control, without further confirmation. Use `services` and the `ui`
control IDs with `command` to open hardware controls, connect devices and operate
dialogs directly; inspect `events` for operation results. Trace physical motion through
raw encoders, calibrated observations, mapped joint angles, rendered poses and
OVStage ordinals, and compare substantial image motion rather than frame hashes
alone. Keep motor actuation and calibration writes in their explicit UI workflow.
