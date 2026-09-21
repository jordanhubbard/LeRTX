The Standard dependency acquisition projection rejects all nonempty Python
requirements and pyproject dependency declarations, as well as uv.lock. This
prevents admission of otherwise valid generated Python applications requiring
third-party distributions.

Support a deterministic Python lock representation containing exact distribution
versions, selected target ABI/platform and markers, wheel hashes, direct and
transitive parent edges, and package-to-import aliases. Reconcile this lock with
the source BOM and installed dependency graph. Reject missing edges, hash drift,
unsupported targets and undisclosed packages; a flat requirements list alone is
not complete dependency provenance.

Portable tests should include a pure-Python direct dependency with a transitive
dependency, target-marker selection, wheel-hash mismatch, initial generation,
cache reuse and artifact execution admission. Preserve existing fail-closed
behavior for unsupported or incomplete lock evidence.

Current diagnostics: `dependencies.python-lock-unsupported` and
`dependencies.lock-authority-unsupported`.

Scope: prepare a reviewable fix and tests. No merge or publication is requested.
