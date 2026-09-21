---
namespace: lertx
version: 0.1.0
display_name: LeRTX application harness
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
---
# LeRTX application harness

Provide a small executable entry point that identifies the application and its
milestone boundaries before native integration. Accept one JSON object as the
first argument. It must contain `command`, with the sole supported value `info`.
Reject malformed JSON, non-object input, unknown fields, missing command, or an
unsupported command with nonzero exit and a concise diagnostic on stderr.

For `{"command":"info"}`, emit exactly one JSON object on stdout:

```json
{
  "application": "LeRTX",
  "milestone": "harness",
  "creation_system": "literate-ai",
  "product_platforms": ["linux", "windows"],
  "robot_family": "so101",
  "integrations": {
    "renderer": "ovrtx",
    "scene": "ovstage",
    "physics": "newton",
    "robot": "lerobot"
  },
  "runtime_ready": false
}
```

The integration names describe planned composition. This entry point performs no
device access, network requests, rendering, physics stepping, or robot motion.
`runtime_ready` must remain false for this milestone. The command must work on a
development machine without a GPU or any native SDK installed.
