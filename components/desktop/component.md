---
namespace: lertx
version: 0.1.0
display_name: LeRTX desktop digital-twin workspace
profiles: ["application", "portable"]
sample: false
inheritable: true
provides:
  - name: application.portable-json
    version: 1.0.0
requires: []
authoring_inputs:
  - kind: specification-to-source-skill
    uri: skills/specification-to-source/portable-application-implementation/SKILL.md
  - kind: specification-to-source-skill
    uri: skills/specification-to-source/portable-specification-planning/SKILL.md
workflow_definition: workflows/production/staging/dev/workflow.md
routing_policy: routing/production/staging/dev/routing.json
flavor_slots:
  - slot_id: build-system
    axis: build.system
    cardinality: zero-or-one
    capability_contract: application.portable-json
  - slot_id: language
    axis: implementation.language-ecosystem
    cardinality: exactly-one
    capability_contract: application.portable-json
  - slot_id: os
    axis: platform.os
    cardinality: exactly-one
    capability_contract: application.portable-json
  - slot_id: package
    axis: packaging
    cardinality: bounded
    capability_contract: application.portable-json
    minimum: 0
    maximum: 6
  - slot_id: toolchain
    axis: toolchain
    cardinality: zero-or-one
    capability_contract: application.portable-json
entrypoints:
  - name: run
    kind: portable-application
    path: run
acceptance_contracts: []
source_dependencies: []
specification_roots: ["component.md", "telemetry-mock.md", "desktop-application.md", "hardware-control.md"]
---
# LeRTX desktop workspace

Implement the RENDER-001 and CONFIG-001 application, not a mock viewport or a
command-line substitute. All behavior below is required; SDK or GPU absence is
an actionable unavailable state, never a simulated successful native result.

## Entry points and lifecycle

`main(payload)` accepts exactly one object. `{"command":"launch"}` opens the
desktop and returns `{"application":"LeRTX","closed":true}` only after its
window and native worker have shut down. An optional `scene` string opens an
existing local USD file. Reject unknown commands, fields, and invalid types.
`{"command":"defaults"}` returns the nonsecret default profile defined below,
without importing Qt or native SDKs, accessing a GPU, or reading any credential.
SDK logs belong on stderr, never mixed with the final JSON result on stdout.

For portable configuration diagnostics, also accept
`{"command":"validate-settings","profile":{...}}`. Validate a complete profile
using the same validation used by the settings dialog, without saving, network,
native imports or GPU access. Return exactly `{"valid":true,"errors":[]}` when
valid, otherwise `{"valid":false,"errors":["section.field",...]}` with unique
sorted field paths and no field values. Missing or unknown sections/fields are
invalid; reference the default profile for its complete shape. Check all types,
the ranges below, finite gravity, substeps 1..64, nonnegative GPU index,
theme `dark` or `light`, units `m`, `cm` or `mm`, quality `balanced` or `high`,
telemetry 1..240 Hz, an array of string asset paths, and literal false for
actuation_enabled and remember_key. A non-object profile is a `profile` error.
Unknown top-level command fields remain invocation errors, not profile errors.

Native work has one dedicated worker owner. Initialize, mutate, render, map,
detach, and destroy OVRTX/OVStage on that owner, not on the Qt UI thread. Bound
pending commands and retain only the latest display frame. Shutdown stops work,
releases mapped tensors and outstanding stage work, detaches and destroys the
stage and renderer, then joins the worker. Repeated open/close must work.

## Visual application

Use a native Qt main window titled LeRTX, initially 1440 by 900 where the screen
allows, with a restrained charcoal theme, teal selection accents, generous
spacing, legible typography, and accessible focus states. Center the actual RTX
viewport between a searchable scene hierarchy and an object inspector. Put
Open USD, Save, Save As, Settings and camera framing in a top toolbar and
Play/Pause, Reset, simulation time, frame rate and native status below.
Provide clear empty, loading, error and ready states; never show placeholder
pixels as an RTX frame. Resize the viewport maintaining image aspect ratio.

Selection through the hierarchy populates prim path/type and editable local
translation, rotation and scale in the inspector. Label units. Unsupported
editable prims display an explanation instead of silently doing nothing. Orbit,
pan, zoom, and frame-selection controls update the rendering camera while paused.
Keyboard navigation and text editing must work without accidental viewport
shortcuts. Unsaved changes prompt Save / Discard / Cancel on open and close.

## Shared USD and Newton scene

Create an original default metric Z-up scene containing a work surface, a static
box obstacle, an orange dynamic sphere above the surface, a perspective camera
and illumination. Use OpenUSD authored state plus a distinct OVStage runtime
stage. OVRTX must render the runtime stage. Map each Newton body index to its
actual USD prim path during model construction; never zip independently ordered
arrays. Import supported collision and rigid-body schemas from loaded USD. If
unsupported geometry cannot be simulated, identify the affected prim and keep
physics disabled for that scene; still allow visual inspection and editing.

One coordinator assigns increasing write ordinals to edit, camera and simulation
publications. A fixed-step Newton accumulator advances only when playing, with
bounded catch-up to keep the UI responsive. Publish body world matrices to
`omni:xform`, wait for the OVStage write floor, and render that ordinal. Matrix
conversion must preserve USD units, up axis and parent transforms. Pause leaves
camera rendering active without advancing physics. Reset restores authored poses
and zero simulation time. Editing stops physics and rebuilds affected simulation
state before another step. Saving persists authored USD, not transient simulated
poses. No implicit baking or remote asset downloads.

Use the pinned public APIs: `ovrtx.Renderer`, `ovstage.Stage`,
`renderer.attach_ovstage`, `ovstage.population.open_usd`,
`stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()`, and
`renderer.step(render_products={product_path}, delta_time=dt, ordinal=ordinal)`.
Copy mapped CPU DLPack frame bytes before unmapping; Qt images may not retain
borrowed native memory. Newton 1.6 uses `newton.CollisionPipeline(model)`, its
`contacts()` allocation, `collide(state, contacts)`, and
`SolverXPBD.step(state, next_state, control, contacts, dt)`. Release old states and
scene resources on reload. SDK initialization alone is not native acceptance.

Construct the Newton model inside the native worker, using ModelBuilder and the
actual integer returned by add_body for every supported USD rigid body. Store
the matching USD path at that point, then finalize the model and allocate its
two states, control and CollisionPipeline once per rebuild. Do not assume an
SDK helper can infer an OpenUSD body map from OVStage; `newton.body_prim_records`
does not exist. Clear forces, collide, step, and swap state/next_state each
substep. Retain fractional accumulator time across frames. Body indices in a
selected mapping need not be contiguous. Reset reconstructs from authored poses.

For transform publication use PathDictionary, a path list built from the exact
mapped paths, query_from_path_list, and write_attribute with an interned
`omni:xform` token, float64 4x4 matrices and is_array=False, then the write-floor
barrier. renderer.step returns a dictionary of products; iterate product.frames
and map the selected frame.render_vars entry with Device.CPU. Convert its DLPack
view to an owned NumPy copy, release the view, unmap, then deliver an owned Qt
image. Converting the renderer's dictionary with bytes() is not frame extraction.
Build an actual default USD fixture before open_usd; never pass None as a scene.

Every visible action must have a working handler and every displayed ready state
must follow successful initialization. The viewport receives frames periodically;
transport controls are buttons, not decorative text. Never report ready merely
because a worker thread started. Thread failures propagate an actionable UI error
and execute cleanup in finally; a failed worker must not leave the UI hanging.

## Configuration and intelligence

The defaults command returns exactly this object:

```json
{"llm":{"endpoint":"https://inference-api.nvidia.com/v1/responses","model":"azure/openai/gpt-6-astra","api_key":"","max_output_tokens":512,"timeout_seconds":60,"remember_key":false},"general":{"theme":"dark","display_units":"m"},"rendering":{"device":0,"width":1280,"height":720,"target_fps":30,"quality":"balanced"},"physics":{"timestep_hz":240,"substeps":4,"gravity_m_s2":"-9.81","reset_on_edit":true},"devices":{"discovery_enabled":false,"telemetry_hz":30,"actuation_enabled":false},"workspace":{"asset_search_paths":[],"reconstruction_status":"unverified"}}
```

Settings has General, Rendering, Physics, Devices, Workspace, Intelligence and
Diagnostics sections. Show workspace/cache directories, discovered GPU and SDK
versions, renderer resolution/quality/frame-rate controls, Newton timestep and
substeps/gravity, asset search paths and metric scale. Unimplemented device role,
calibration and reconstruction controls are visibly unavailable with explanation.
No settings action enables robot actuation. Changing display units never changes
authored scene scale. Renderer changes require confirmed restart; physics changes
stop simulation and rebuild without losing authored edits.

Intelligence contains editable full endpoint URL, model, masked API key, token
limit and timeout. Ship a blank key. Never scan developer files or environment
variables for keys. Provide reveal/hide, clear, Test connection, Save, Cancel and
Restore defaults. Keep key session-only and display that policy; do not offer
Remember key until a platform credential-store implementation exists. Ordinary
settings persist atomically in the platform user configuration directory; keys
must never appear in that JSON, diagnostics, exports or logs.

Stage form edits until Save; validate fields inline and preserve the prior valid
profile on failure. Require HTTPS without userinfo, fragment or query credentials,
a nonempty model, integer tokens 1..131072, timeout 1..300 seconds, positive
render dimensions, frame rate 1..240 and physics timestep 1..2000 Hz. Changing
endpoint clears its credential association and invalidates connection status.
Do not silently reuse a key for a new service. Cancel discards edits and invalidates
late asynchronous results; clear removes the session credential. Defaults clears
credentials and restores all default values only after Save.

Test uses the visible form's endpoint/model/key, JSON POST with `model`, `input`
and `max_output_tokens`, and Bearer authorization. Do not append `/responses` to
the full URL. Use a short text prompt; never send a workspace image or launch a
coding CLI. Bound timeout and response size (4 MiB), reject redirects, validate
JSON and inspect Responses output message text blocks. Distinguish completed,
incomplete and failed responses; HTTP 200 alone is not success. Report missing
key, testing, successful text access, auth failure, unknown model, timeout, rate
limit and service failure without raw response bodies or secret-bearing details.
Cancellation ignores stale completions and explicitly does not promise server
cancellation. Keep the window responsive throughout all requests.

## Photo scene interchange (milestone three)

Before constructing USD from model output, accept only a strict JSON object with
`schema: "lertx.photo-scene.v1"`, `units: "m"`, `objects` and `unobserved`.
Units label model estimates, not measurements. Limit UTF-8 input to 4 MiB,
objects to 256, and unobserved-region descriptions to 64 strings of at most
512 characters. Reject duplicate keys, nonfinite numbers, excessive nesting,
unknown fields and unsupported schema versions without changing the active scene.

Each object has `id` (unique ASCII USD-safe identifier, at most 64 characters),
`label` (1..128 characters), `translation` (three finite estimated meters within
±1000), `rotation` (three XYZ degrees within ±360), `color` (three values in
0..1), `confidence` (0..1), and `geometry`. Geometry is exactly one of:
`{"type":"box","size":[x,y,z]}`, `{"type":"sphere","radius":r}`, or
`{"type":"mesh","points":[[x,y,z],...],"triangles":[i,j,k,...]}`.
Dimensions/radius must lie in 0.0001..100 meters. Meshes contain 3..20000 points,
coordinates within ±100 meters, and 1..40000 nondegenerate indexed triangles;
the scene contains at most 100000 points and 200000 triangles in total. No
references, payloads, file paths, shaders, external assets or code are accepted.

Build an anonymous metric Z-up USD stage locally, with named editable objects
under `/World/Objects`, display colors and confidence metadata. Persist source
image SHA256, model identifier, unobserved descriptions, and explicit
`unverified` reconstruction and `estimated` dimension metadata. Do not attach
rigid-body/collision APIs or mark the scene safe for planning based on this
response. Construction failure must not mutate the existing document. Native
tests must export, reopen, edit and save reconstructed boxes, spheres and meshes
while preserving provenance. These tests do not replace actual image inference,
UI preview/cancellation, measured registration or hardware acceptance.

## USB discovery and roles (follow-on, outside milestone three)

Provide a Devices toolbar panel that scans USB serial metadata without opening
ports. Label results unverified candidates, not confirmed robots. Opening the
panel performs a scan; the configured discovery_enabled setting enables periodic
rescans while the panel is open. A Scan now action remains available. Use the
existing Qt serial-port metadata API and never probe unrelated legacy ports.
Keep at most one background scan in flight per window. Display enumeration
failure distinctly from no devices and discard results after panel closure.

Leader/follower assignment is explicit, never based on enumeration order. Persist
only unique USB vendor/product/serial identities, not COM numbers or tty paths.
Missing or duplicate serial identities require session-only confirmation and
must lose their assignment on disappearance. A port cannot occupy both roles.
Show missing and ambiguous remembered devices; do not reconnect to a substitute.
Role changes use atomic configuration writes; a failed write preserves previous
assignments. This panel must not enable actuation or imply telemetry is connected
before the separately qualified LeRobot adapter actually reports readings.

## Hardware-free telemetry mock (follow-on)

The explicit specification root `telemetry-mock.md` defines this independent
hardware-free boundary, its visible controls and read-only sample validation.

## Photo reconstruction workflow (milestone three)

The photo workflow, request feedback and explicit quality presets are specified
in `desktop-application.md`.

## Required tests

Generated unit tests must exercise configuration validation and transactional
persistence, default blank keys, endpoint-key association, redacted failures,
response parsing and cancelled/stale results with injected transport responses.
Test simulation play/pause/reset and prim identity mapping independently of frame
rate. Native integration tests separately verify real frames, Newton motion,
pause with live camera, reset, edit/save/reopen and repeated cleanup on both
Linux and Windows NVIDIA targets. UI tests cover actual visible controls and
keyboard navigation, not only underlying functions. Missing native dependencies
must not cause these integration tests to report a pass.

## Installed application and articulated robot workspace

`desktop-application.md` defines APP-001 and extends the default scene with the
SO-101 leader and follower pair. It supersedes the simple demonstration scene
only for the application default; basic rigid-body fixtures remain valid tests.
