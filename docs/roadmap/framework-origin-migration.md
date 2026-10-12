# Framework origin migration blocker

- **Status:** partial
- **Owning queue item:** [FRAMEWORK-001](active-work.md#framework-001-migrate-to-published-literate-ai-120).
- **Completion / archival evidence:** pending while FRAMEWORK-001 remains open.

## Upstream issue draft

Title: Provide a reviewed initialization-origin migration across forge hosts

A derived project initialized from a previous GitLab distribution cannot update
with the published GitHub distribution. `FilesystemProjectUpdateAdapter.plan`
returns `project.update_origin_changed`. The repository succession table only
recognizes the previous GitHub organization. Changing the repository parent does
not migrate the separate initialization origin and baseline.

Provide an explicit plan/apply migration that preserves the original origin and
baseline, binds the expected old and proposed new identities, and requires review
before accepting a new publisher. Do not silently treat arbitrary repository URLs
as equivalent. Historical commits may be unavailable in the destination, so the
plan must report that limitation and require explicit treatment of unresolved
three-way bases and local changes.

An upstream fixture should use synthetic old/new repository URLs and prove that
ordinary update still rejects an unrecognized origin, a reviewed migration preserves
local edits and provenance, stale plans fail, and failed validation rolls back.

## Downstream evidence

The official Literate AI 1.2.0 wheel SHA-256 is
`e6ece36ee714ce30b4b63fc19dc880ce4838ca157e45607a3e524850d80c9686`.
The release tag resolves to `04d033b9ba0379bb70f0de54bcbc6d7f244d3831`.
The recorded initialization commit `143c268914e7168f5ded3e1271b08cefd71c2ad4`
is unavailable through the destination GitHub commits API (HTTP 422).
The original initialization origin and baseline remain unchanged.

Upstream searches for GitLab origin migration and initialization origin found no
matching open issue. Closed issue #36 concerns SCP transport/base recovery rather
than cross-forge publisher migration. Filing this draft requires external-write
authorization; no upstream repository changes or issue posts were made.
