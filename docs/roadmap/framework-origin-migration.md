# Literate AI 1.2.0 migration

- **Status:** completed
- **Owning queue item:** [FRAMEWORK-001](active-work.md#x-framework-001-migrate-to-published-literate-ai-120)
- **Completion / archival evidence:** fresh acceptance, portable/package checks and hosted CI passed; [PR #20](https://github.com/jordanhubbard/LeRTX/pull/20)

## Authority decision

The operator explicitly retired the old GitLab project and initialization origin.
The published public Literate AI 1.2.0 wheel and its exact GitHub release commit
now own framework updates. This is an intentional replacement of publisher
authority, not a claim of historical repository equivalence. The old initialization
baseline hashes are retained only as local merge inputs; ordinary update records
reviewed upstream bases for subsequent upgrades. No upstream issue is required.

The release tag resolves to `04d033b9ba0379bb70f0de54bcbc6d7f244d3831`.
The official wheel SHA-256 is
`e6ece36ee714ce30b4b63fc19dc880ce4838ca157e45607a3e524850d80c9686`.
Standard lifecycle and runner identities were advanced through the reviewed
[rebind plan](../../verification/framework-1.2.0-rebind-plan.json).

## Reconciliation decisions

Keep LeRTX's project guide and getting-started documentation: the upstream
versions are product-description placeholders. Adopt the reviewed Linux and
Windows tool catalog additions for Elixir and Erlang. Apply the remaining
framework updates and new standard catalog files with `litai update`.
Preserve authored desktop source, specifications and project-specific Flavors.

## Evidence

Committed resolution audits, project validation, complete framework verification,
retained desktop acceptance, portable regressions and hosted CI all pass.
FRAMEWORK-001 records the results. Prior release and native qualification
receipts remain historical evidence; this framework migration is not a new
physical-hardware or native-rendering qualification claim.

Fresh acceptance passed all 30 checks under the new lifecycle and local `litai
verify` passes all enabled gates. Portable validation passed 313 tests and 61
subtests, including reproducible packaging and extracted defaults. See
[upgrade evidence](../../verification/framework-1.2.0-upgrade-review.json) and
[framework verification](../../verification/framework-1.2.0-verification.json).
A repeated update has zero conflicts and zero pending upstream changes/additions.
