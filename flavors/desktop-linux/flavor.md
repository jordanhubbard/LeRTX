---
schema: "literate-ai/flavor-markdown@1"
namespace: "lertx"
name: "desktop-linux"
version: "1.0.0"
display_name: "LeRTX verified Linux native target"
primary_axis: "platform.os"
target: "linux"
secondary_constraints: []
applicable_capabilities: ["application.portable-json"]
provides:
  - name: "platform.os.linux"
    version: "1.0.0"
    contract: null
requires: []
specification_roots: ["openspec/spec.md"]
authoring_inputs: []
contributions:
  - contribution_id: "desktop-linux-command-profile"
    kind: "builder"
    merge_operator: "exact-singleton"
    slot: "standard-platform-command"
    content:
      kind: "standard-command-profile"
      uri: "standard-command-profile.json"
conflicts: []
co_requisites: ["flavor://lertx/desktop-python", "flavor://lertx/desktop-wheels"]
order_before: []
order_after: []
---
# Verified Linux native target

This project-owned target binds the observed CPython 3.12 Linux interpreter and
the separately verified native wheel closure. It is not Windows evidence.
