---
name: survey-peer-work
description: At the start of a dev cycle, list green open PRs/MRs you may want to start from; at the end, list leftover worktrees and branches to collect into the current PR. Use before beginning work on a branch and before opening or merging a land PR.
metadata:
  author: Literate AI maintainers <literate-ai-maintainers@users.noreply.github.com>
---

# Survey other developers' work

Inherits `../SKILL.md` (dev). Run `litai project guidance --operation develop`
at cycle start and `--operation gc` before cleanup. Execute its named argv and
report failures/skips; do not invent Git cleanup or merge without the operator.

## Start of cycle

Prefer semantically relevant existing issues and green reviews over duplicate
work. Inspect open tracker items as well as reviews, unmerged local and remote
branches, and attached worktrees. Ask before switching branches; never interpret
unknown CI as green.

During a release cycle, this survey feeds `litai release contributions sweep`.
Every open issue or review receives a current-cycle `include` or `defer`
disposition whose machine-readable comment and milestone agree. An included,
open item blocks the release; a deferred item names a later milestone and a
reason. Repeat after merges and immediately before publication because humans
and agents can contribute while the cycle is in progress.

## End of cycle

Collect relevant leftover commits only with operator acknowledgment. Resolve
conflicts deliberately; retained work and unsupported forges remain named skips.
Do not treat a branch as merged merely because a similarly named change landed;
prove ancestry or patch equivalence, or bind it to a reviewed tracker disposition.
Dirty, prunable, or otherwise abandoned worktrees remain explicit blockers until
their owner resolves them or records a supported disposition.

A local pass is not a substitute for this survey.
