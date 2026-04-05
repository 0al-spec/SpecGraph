# TODO

1. Implement worktree cleanup to prevent `.worktrees/*` accumulation over time.
2. Add branch/worktree freshness validation in gate resolution (do not blindly trust `last_worktree_path`).
3. Add a command to list and clean stale gate states and stale worktrees.
4. Upgrade `search_kg_json.py` from plain keyword matching to structured requirement extraction.
5. Add integration tests that exercise real `git worktree` commands (beyond monkeypatched fake worktrees).
6. Add semantic acceptance validation that verifies each acceptance criterion is actually satisfied, not only structurally present.
7. Add graph-projection/provenance artifacts beyond run JSON/summary (projection-ready links or derived graph outputs).

## Reflective Evolution Loop

8. [done] Specify the reflective loop boundary explicitly: what is governed by SpecGraph specs, what is executed by `supervisor`, and what always requires human approval.
9. [done] Add `observe_graph_health(...)` to `supervisor` so each run emits derived observations about graph quality, not only pass/fail validation.
10. [done] Define the first derived graph-health signals for oversized specs, repeated `split_required`, deep ancestor reconcile waves, stalled maturity, and weak structural linkage.
11. [done] Persist observations and signals in run artifacts first, without writing them back into canonical spec nodes.
12. [done] Add a derived `refactor_queue` artifact that can schedule graph refactors separately from ordinary spec refinement runs.
13. [done] Introduce a distinct work-item model in `supervisor`: `spec_refine`, `graph_refactor`, and `governance_proposal`.
14. [done] Define how local graph refactors can be auto-executed while governance/runtime changes still require a review gate.
15. [done] Add proposal generation for recurring graph pathologies so repeated signals produce explicit refactor or policy proposals instead of ad hoc changes.
16. [inprogress] Define the rules for graph refactoring passes that split oversized specs into multiple atomic child specs while preserving stable parent terminology and lineage.
17. Add support for retrospective spec refactoring after a graph has already grown suboptimally, not only at creation time.
18. [done] Specify how `supervisor` may update graph structure directly versus when it must emit a proposal for a human-reviewed spec change.
19. Introduce metric-driven signals later, using SIB, Specification Verifiability, Process Observability, Structural Observability, and related measures as derived inputs rather than canonical facts.
20. Define how metric thresholds become proposals first, and only later become normative policy in SpecGraph after human approval.
21. Add viewer-facing overlays or reports for graph health so oversized or weakly linked regions are visible without reading raw run logs.
22. Add longitudinal graph-health reporting so repeated structural problems can be seen as trends rather than isolated failures.
