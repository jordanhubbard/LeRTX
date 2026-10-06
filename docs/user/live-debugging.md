# Live co-session debugging

Launch the normal app with local diagnostics enabled:

```powershell
$env:LERTX_DEBUG='1'
make run
$env:PYTHONPATH='desktop/source'
.venv/Scripts/python.exe -m lertx.debug_client state
```

On Linux use `LERTX_DEBUG=1 make run` and `PYTHONPATH=desktop/source
.venv/bin/python -m lertx.debug_client state` (on one line). Diagnostics are opt-in
and stop with the application. Settings / Diagnostics shows whether they are active.
The existing installation-preflight diagnostics remain separate.

The client discovers the newest responsive process in the user configuration
folder's `debug` directory. Use `--pid` when several instances are open. Discovery
files contain a per-run credential: do not paste or commit them. The endpoint
listens only on loopback, requires that token, and rejects browser-origin requests.
There is no remote execution or physical motor command endpoint.

## Observe while the operator works

- `state`: current device roles/ports, sample sequence/age, raw encoders, torque,
  calibration state, control ownership, wizard progress and native frame data.
- `ui`: visible control labels, checked/disabled states and progress values.
- `events`: bounded recent state, command queue/work/delivery timings and frames.
- `watch --seconds 30 --output trace.jsonl`: sample state five times per second.
- `frame --output frame.png`: exact latest RTX image delivered to the GUI.
- `window --window ID --output wizard.png`: capture an application window using
  an ID from `state`, including dialogs covered by other desktop windows.

Snapshots are versioned JSON. Times use the process's monotonic clock. State
samples and frames have their own timestamps: compare ages rather than assuming
that a state request and rendered image are simultaneous. GPU utilization and
memory are whole-GPU readings including other applications, refreshed every two
seconds; unavailable metrics have an explicit error. CPU seconds are process
user plus system time. Queued camera commands report acceptance; their completion
or error appears in events. `command.completed` splits queue, work and UI delivery
latency. `frame.presented` includes the OVStage ordinal, frame hash and requested
versus independently measured virtual joint angles.

To diagnose physical coupling, trace raw encoder change -> mapped radians ->
measured virtual pose -> increasing publication ordinal -> visibly changed RTX
pixels. A changing frame hash alone is insufficient because RTX sampling noise
can change pixels in a stationary scene. Keep a pair of captures with substantial
joint movement and inspect the arm silhouette. The static reference diagram is
intentionally a pose to copy, not a live-pose indicator.

## Tune during a session

Use the command endpoint with JSON, for example:

```powershell
.venv/Scripts/python.exe -m lertx.debug_client command --json '{"command":"target_fps","value":20}'
.venv/Scripts/python.exe -m lertx.debug_client command --json '{"command":"camera","role":"follower","orbit":[0.25,0],"zoom":0}'
```

Frame rate accepts integers 1–120; camera deltas are bounded. Changes are temporary
and do not save settings. Renderer-busy responses require a retry. Use the normal
Settings UI for resolution/quality changes that rebuild the native scene; close
hardware sessions first. No debug command can engage torque, move a physical arm,
change calibration, replace a device owner, or bypass its confirmation controls.

Diagnostic screenshots and traces may contain local device identities and user
scene contents. Keep raw traces local and sanitize evidence before committing.
