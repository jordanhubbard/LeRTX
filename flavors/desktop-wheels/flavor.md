---
schema: "literate-ai/flavor-markdown@1"
namespace: "lertx"
name: "desktop-wheels"
version: "1.0.0"
display_name: "LeRTX verified native Python wheels"
primary_axis: "packaging"
target: "pip"
secondary_constraints:
  - axis: "implementation.language-ecosystem"
    value: "python"
    optional: false
applicable_capabilities: ["application.portable-json"]
provides:
  - name: "package.format.python-wheel"
    version: "1.0.0"
    contract: null
requires: []
specification_roots: ["openspec/spec.md"]
authoring_inputs: []
contributions:
  - contribution_id: "desktop-python-wheel-command-profile"
    kind: "builder"
    merge_operator: "exact-singleton"
    slot: "standard-package-command"
    content:
      kind: "standard-command-profile"
      uri: "standard-command-profile.json"
conflicts: []
co_requisites: ["flavor://lertx/desktop-python"]
order_before: []
order_after: []
---
# Verified native dependencies

Select the framework's offline, binary-only Python wheel lifecycle for LeRTX.
This profile does not provide permission to bypass dependency or execution gates.
