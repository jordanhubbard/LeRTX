# Milestone acceptance audit

This is a requirement audit, not an admission receipt. The roadmap retains
milestones one and two and the operator's explicit milestone-three scope:
Astra photo-to-USD reconstruction. Physical robot synchronization is follow-on.

| Requirement | Current evidence | Remaining acceptance |
| --- | --- | --- |
| Litai-created harness | HARNESS-001 records generation, build, 13 tests, independent acceptance and launch | Historical harness success does not make the current desktop receipt valid |
| Exact native dependencies | Linux and Windows `native/*/qualified-install-review.json` record offline installation, payload verification, revalidation and cleanup | Bind the retained application and its actual distribution to current target closures |
| Real RTX/OVStage frames and Newton | `test_runtime_native`, `test_physics_native`, `test_window_native`; current full 157-test Linux/Windows passes and Windows mixed-order startup/shutdown pass in `usd-bootstrap-review.json` | Independent retained-application admission remains pending |
| Editable local USD workspace | Document isolation, asset policy, native edit/save/reopen, untitled Save As and failure-path tests | Final requirement-level review and independently admitted artifact |
| Native UI usability | Nested hierarchy, search, selection safety, readable inspector; settings transaction and stale-error repair verified by `settings-transaction-review.json` | Review remaining interaction and failure-path gaps |
| Configurable LLM with blank shipped key | `config.DEFAULT_PROFILE`, portable persistence tests and direct fresh-dialog blank-key assertion with file reads forbidden; `photo-failure-review.json` passes on both platforms | Bind current tested source into admitted application evidence |
| Astra photo-to-USD | `live-photo-response.json`, strict validation, actual UI success/cancellation/failure preservation, and `native/linux/live-edit-review/review.json` proving edit/save/reopen and changed RTX output | Functional gates pass; prerequisite application admission remains open. No measured reconstruction accuracy is claimed |
| Honest lifecycle provenance | Original source archive and reviewable retained-source diff; exact test snapshot identities | Current source/resolved SBOM and verifier-owned admission/receipt remain unresolved; do not relabel edited source as untouched generation |
| Linux and Windows delivery | Running development application evidence on provisioned GPU targets; both complete native suites and Windows order-dependent startup regression pass after full renderer-system shutdown | No end-user package or complete retained-application installation acceptance yet |

Additional observed gaps remain recorded in the owning roadmap items. This table
does not waive specification requirements, substitute injected tests for native
tests, or promote the mock to physical-device verification. The existing
`spec merge` preview only proposes a new source-inventory Component; it was not
applied. The retained-source admission proposal is published for review as
[issue #463](https://github.com/NVIDIA-dev/literate-ai/issues/463) and draft
[PR #464](https://github.com/NVIDIA-dev/literate-ai/pull/464); publication is not
application admission.
