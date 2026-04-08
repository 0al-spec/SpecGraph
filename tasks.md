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
16. [done] Define the rules for graph refactoring passes that split oversized specs into multiple atomic child specs while preserving stable parent terminology and lineage.
17. [inprogress] Add support for retrospective spec refactoring after a graph has already grown suboptimally, not only at creation time.
18. [done] Specify how `supervisor` may update graph structure directly versus when it must emit a proposal for a human-reviewed spec change.
19. [done] Add an explicit application path for approved split proposals so reviewed `split_oversized_spec` artifacts can be deterministically materialized into canonical parent/child spec files.
20. Introduce metric-driven signals later, using SIB, Specification Verifiability, Process Observability, Structural Observability, and related measures as derived inputs rather than canonical facts.
21. Define how metric thresholds become proposals first, and only later become normative policy in SpecGraph after human approval.
22. Add viewer-facing overlays or reports for graph health so oversized or weakly linked regions are visible without reading raw run logs.
23. Add longitudinal graph-health reporting so repeated structural problems can be seen as trends rather than isolated failures.

## Supervisor Runtime Hardening

24. [done] Add an explicit child executor runtime profile for `codex exec` so nested runs do not implicitly inherit global user config for `approval_policy`, `sandbox_mode`, MCP startup, or optional runtime features.
25. [done] Make nested `codex exec` startup deterministic by disabling or minimizing non-essential runtime features for spec refinement runs (for example shell snapshots and unrelated MCP servers).
26. [done] Isolate or reset child executor state so nested runs do not depend on the operator's long-lived `~/.codex` state DB and migration history.
27. [done] Classify executor-environment failures separately from spec-quality failures so transport, MCP, sandbox, or state-runtime problems do not masquerade as graph-health issues.
28. [done] Add a documented bootstrap-runtime troubleshooting path for `supervisor` runs, including expected child executor config, fallback worktree mode, and interpretation of nested executor failures.

## Proposal Lane

29. [inprogress] Add a tracked proposal lane between canonical spec nodes and ephemeral runtime artifacts so `supervisor` can grow proposal subgraphs without mutating canonical truth.
30. Define proposal-lane node semantics, including stable provisional IDs, authority or approval state, and lineage between proposal nodes and canonical nodes.
31. Let `supervisor` autonomously create and refresh tracked proposal nodes while keeping canonical writeback behind explicit review/apply flow.
32. Extend graph and viewer projections so proposal-lane nodes can be shown as an overlay or secondary layer on top of the canonical graph.

## Intent Layer

33. [inprogress] Define an intent-facing layer and mediated discovery path between raw user goals and canonical SpecGraph specs.
34. Distinguish `UserIntent` and `OperatorRequest` from canonical `spec` and proposal-lane nodes.
35. Add a bounded operator-request bridge so GUI selections and chat instructions can steer one supervisor run without mutating canonical specs directly.
36. Define how mediator outputs become canonical specs or proposals through reviewable supervisor-driven refinement instead of raw chat-to-spec mutation.

## Canonical Spec Writeback

37. Make all `supervisor` writes to canonical spec files use one canonical YAML writer, including runtime-state updates after worktree sync.
38. Add a deterministic post-write normalization/check path so canonical spec files are re-rendered or rejected if a `supervisor` run leaves them non-canonically formatted.
39. Add regression coverage proving that a live-like `supervisor` refinement run leaves edited spec files canonically formatted without requiring a manual `spec_yaml_format.py` pass.

## Child Spec Materialization Path

40. [done] Fix the `supervisor` path for creating one new child spec during explicit targeted refinement so a bounded child can be materialized from an existing parent delegation boundary instead of stalling with no canonical diff.
41. [done] Add deterministic stall/timeout handling for nested child-creation runs so a run that produces no child file and no canonical content diff fails fast as a runtime blocker rather than hanging or leaving only runtime-state noise.
42. [done] Add integration coverage for one-run child spec creation from a non-root parent with `allowed_paths: specs/nodes/*.yaml`, including creation of the child file, minimal parent update, and explicit refinement/dependency linkage.
43. [done] Define cleanup rules for interrupted child-creation runs so parent specs do not retain escalated runtime-state when no canonical child spec or accepted content change was actually materialized.

## Interrupted Refinement Runtime Hygiene

44. [done] Add cleanup rules for interrupted ordinary source-spec refinement runs so a timeout or executor failure does not leave blocked or escalated runtime-state in the canonical source spec when no accepted canonical content change was materialized.
45. [done] Align `supervisor` execution-profile timeout budgets with reasoning effort and expected run depth so `xhigh` targeted refinements do not spuriously time out under the default profile.
46. [done] Add regression coverage for timeout-failed targeted refinements that edit only the selected source spec: canonical source content must remain unchanged while the run log still records the executor failure and partial diff context.
47. [done] Extend bootstrap-runtime troubleshooting docs so timeout-driven stale tails, partial worktree diffs, and profile-selection mismatches are documented as runtime anomalies rather than spec-quality failures.
