---
schema: "literate-ai/flavor-markdown@1"
namespace: "lertx"
name: "desktop-python"
version: "1.0.0"
display_name: "LeRTX native Python desktop"
primary_axis: "implementation.language-ecosystem"
target: "python"
secondary_constraints: []
applicable_capabilities: ["application.portable-json"]
provides:
  - name: "implementation.language.python"
    version: "1.0.0"
    contract: null
requires: []
specification_roots: ["openspec/spec.md", "openspec/native-interfaces.md"]
authoring_inputs: []
contributions:
  - contribution_id: "desktop-python-toolchain"
    kind: "toolchain"
    merge_operator: "exact-singleton"
    slot: "python"
    content:
      kind: "toolchain-constraint"
      uri: "toolchain.json"
  - contribution_id: "desktop-python-command-profile"
    kind: "builder"
    merge_operator: "exact-singleton"
    slot: "standard-language-command"
    content:
      kind: "standard-command-profile"
      uri: "standard-command-profile.json"
conflicts: []
co_requisites: []
order_before: []
order_after: []
---
# Native desktop Python

Project-owned native dependency policy, separate from the framework's
standard-library-only Python Flavor. It does not weaken lifecycle admission.
