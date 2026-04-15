# TODO

Active backlog only. Completed tasks were moved to [tasks_archive.md](/Users/egor/Development/GitHub/0AL/SpecGraph/tasks_archive.md).
Task numbers are preserved for traceability across commits and PRs.

1. [todo] Implement worktree cleanup to prevent `.worktrees/*` accumulation over time.
2. [todo] Add branch/worktree freshness validation in gate resolution (do not blindly trust `last_worktree_path`).
3. [todo] Add a command to list and clean stale gate states and stale worktrees.
4. [todo] Upgrade `search_kg_json.py` from plain keyword matching to structured requirement extraction.
5. [todo] Add integration tests that exercise real `git worktree` commands (beyond monkeypatched fake worktrees).
6. [todo] Add semantic acceptance validation that verifies each acceptance criterion is actually satisfied, not only structurally present.
7. [todo] Add graph-projection/provenance artifacts beyond run JSON/summary (projection-ready links or derived graph outputs).

## Reflective Evolution Loop

17. [inprogress] Add support for retrospective spec refactoring after a graph has already grown suboptimally, not only at creation time.
20. [todo] Introduce metric-driven signals later, using SIB, Specification Verifiability, Process Observability, Structural Observability, and related measures as derived inputs rather than canonical facts.
21. [todo] Define how metric thresholds become proposals first, and only later become normative policy in SpecGraph after human approval.
22. [todo] Add viewer-facing overlays or reports for graph health so oversized or weakly linked regions are visible without reading raw run logs.
23. [todo] Add longitudinal graph-health reporting so repeated structural problems can be seen as trends rather than isolated failures.

## Proposal Lane

29. [todo] Add a tracked proposal lane between canonical spec nodes and ephemeral runtime artifacts so `supervisor` can grow proposal subgraphs without mutating canonical truth.
30. [todo] Define proposal-lane node semantics, including stable provisional IDs, authority or approval state, and lineage between proposal nodes and canonical nodes.
31. [todo] Let `supervisor` autonomously create and refresh tracked proposal nodes while keeping canonical writeback behind explicit review/apply flow.
32. [todo] Extend graph and viewer projections so proposal-lane nodes can be shown as an overlay or secondary layer on top of the canonical graph.

## Intent Layer

33. [todo] Define an intent-facing layer and mediated discovery path between raw user goals and canonical SpecGraph specs.
34. [todo] Distinguish `UserIntent` and `OperatorRequest` from canonical `spec` and proposal-lane nodes.
35. [todo] Add a bounded operator-request bridge so GUI selections and chat instructions can steer one supervisor run without mutating canonical specs directly.
36. [todo] Define how mediator outputs become canonical specs or proposals through reviewable supervisor-driven refinement instead of raw chat-to-spec mutation.

## Supervisor Runtime Hardening

64. [todo] De-prioritize or suppress `linked_continuation` selection for `linked` specs already at `maturity: 1.0` when the only continuation signal is `weak_structural_linkage_candidate`, so long-running `--loop` batches do not burn iterations on effectively complete nodes like `SG-SPEC-0021` or the earlier `SG-SPEC-0005` case.
