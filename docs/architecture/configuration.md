# Application configuration

This contract belongs to CONFIG-001 in [active work](../roadmap/active-work.md)
and is subordinate to the root `PROJECT.md`. It specifies the configuration UI
for the application under construction; the UI and inference adapter are not
implemented by this document.

## Inference defaults

Use the [nonsecret defaults](configuration.defaults.json) when creating a fresh
application profile. The endpoint is the complete request URL, not a base URL:
do not append another `/responses`. Preserve the exact provider-qualified model.

```json
{
  "model": "azure/openai/gpt-6-astra",
  "input": "Explain quantum computing in simple terms.",
  "max_output_tokens": 512
}
```

Send authenticated JSON POST requests to
`https://inference-api.nvidia.com/v1/responses`. Use the Responses output message
content blocks for text, and distinguish completed, incomplete, and failed
responses. A 200 response by itself is not proof of completed output. The output
limit must be editable: 512 is the supplied initial value, not a scene-size limit
or a claim that a full workspace can fit in that budget. Never interpret a
truncated scene as a valid reconstruction.

The remote coding CLI is development tooling, independent of this runtime API.
The app must not invoke a shell or coding agent to perform ordinary inference.

## LLM panel

Provide a clearly labelled Intelligence / LLM section with endpoint URL, model,
masked API key, maximum output tokens, request timeout, and connection status.
Prepopulate the endpoint and model above. The API-key value must be empty on a
fresh install; a placeholder is not a credential. Require a nonempty key before
enabling authenticated requests and explain the missing field inline.

Provide explicit reveal/hide, clear credential, Test connection, Save, Cancel,
and Restore defaults controls. Test connection uses the current visible form
values and an inexpensive text request, not a workspace photo. Show testing,
success, timeout, authentication failure, unavailable model, rate limit, and
service failure states without blocking the interface. Make clear that a text
connection test does not establish image-input or reconstruction support.

Keep edits staged until Save. Validate before saving, preserve the previous valid
profile on failure, and explain errors next to the relevant field. Changing the
endpoint invalidates its previous connection result and credential association;
never silently send a stored key to a newly selected service. Honor Cancel and
discard late test results for superseded form values. An aborted UI request must
not claim that already-submitted remote inference was cancelled.

## Credentials and persistence

The operator has authorized a private key file for explicit development and
testing only. Do not auto-read it from the application, scan common key locations,
copy its bytes into a profile, or prefill the UI from a developer environment.
Builds, fixtures, documentation, diagnostic output, request logs, screenshots,
source caches, and exported settings must not contain the key.

Persist ordinary settings separately from credentials. Keep credentials in memory
for the current session by default. If a Remember key option is provided, make it
opt-in and use the platform credential store; if unavailable, offer session-only
use rather than silently writing plaintext. An existing saved credential is
represented by a status indicator, never its value in an API readback or export.
Clearing a credential also clears its saved platform-store entry when present.

Do not follow an authenticated redirect to another endpoint. Use bounded network
timeouts and response sizes. Sanitize remote failure details; never show or log
Authorization headers or raw credential-bearing request objects.

## Other useful configuration

Organize settings into a consistent navigation panel with clear units and concise
help text. Show unsupported or unavailable runtime options with an explanation.

| Section | Controls |
| --- | --- |
| General | Appearance, display units, workspace and cache locations |
| Rendering | NVIDIA device, viewport resolution, frame-rate target, quality |
| Physics | Newton timestep, substeps, gravity, simulation reset preferences |
| Devices | USB discovery, leader/follower role assignments, telemetry rate, calibration status |
| Workspace | USD asset search paths, scene scale, reconstruction review and calibration state |
| Diagnostics | SDK/driver versions, connection status, redacted diagnostic export |

Settings changes must not arm robot motion or reinterpret existing scene units
silently. Explicitly identify changes requiring a renderer restart or physics
rebuild. Preserve the authored scene and stop simulation before applying such
changes. Keep physical actuation disabled until its later calibration/arming
workflow is implemented.

## Verification

On 2026-09-15, an explicit development-only request using the supplied endpoint,
model, example input, and 512-token limit returned HTTP 200, `status: completed`,
and the exact requested model. It produced 1700 text characters with 13 input
tokens and 379 output tokens (392 total). The key and response text were not
written to the repository. This verifies text access, not photo reconstruction.

UI acceptance must cover a fresh blank credential field, invalid input, unsaved
edits, save/reload, clear/reset, endpoint changes, accessible keyboard navigation,
and responsive connection testing. Inspect persistence, exports, diagnostics,
and generated artifacts for credential leakage. Run the UI tests on Linux and
Windows when the graphical application is available.

The [official Responses text guide](https://developers.openai.com/api/docs/guides/text)
describes the generic request/response structure. The NVIDIA endpoint and model
identifier above are supplied by the operator and verified directly.

The photo workflow follows the [official image-input format](https://developers.openai.com/api/docs/guides/images-vision):
a user message containing input_text and a base64 data-URL input_image. A separate
development-only image probe succeeded against the configured NVIDIA Astra model,
using an original synthetic workspace render and 4096 output tokens. See
`verification/live-photo-response.json`; the application's default remains 512.
This proves image transport and schema-compatible output, not metric reconstruction.
