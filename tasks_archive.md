# Task Archive

Completed tasks moved out of [tasks.md](/Users/egor/Development/GitHub/0AL/SpecGraph/tasks.md) to keep the active backlog short and readable.
Task numbers are preserved for traceability across commits, PRs, and review threads.

1. [done] Implement worktree cleanup to prevent `.worktrees/*` accumulation over time.
2. [done] Add branch/worktree freshness validation in gate resolution (do not blindly trust `last_worktree_path`).
3. [done] Add a command to list and clean stale gate states and stale worktrees.
4. [done] Upgrade `search_kg_json.py` from plain keyword matching to structured requirement extraction.
5. [done] Add integration tests that exercise real `git worktree` commands (beyond monkeypatched fake worktrees).
6. [done] Add semantic acceptance validation that verifies each acceptance criterion is actually satisfied, not only structurally present.
7. [done] Add graph-projection/provenance artifacts beyond run JSON/summary (projection-ready links or derived graph outputs).

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
18. [done] Specify how `supervisor` may update graph structure directly versus when it must emit a proposal for a human-reviewed spec change.
19. [done] Add an explicit application path for approved split proposals so reviewed `split_oversized_spec` artifacts can be deterministically materialized into canonical parent/child spec files.
22. [done] Add viewer-facing overlays or reports for graph health so oversized or weakly linked regions are visible without reading raw run logs.

## Supervisor Runtime Hardening

24. [done] Add an explicit child executor runtime profile for `codex exec` so nested runs do not implicitly inherit global user config for `approval_policy`, `sandbox_mode`, MCP startup, or optional runtime features.
25. [done] Make nested `codex exec` startup deterministic by disabling or minimizing non-essential runtime features for spec refinement runs (for example shell snapshots and unrelated MCP servers).
26. [done] Isolate or reset child executor state so nested runs do not depend on the operator's long-lived `~/.codex` state DB and migration history.
27. [done] Classify executor-environment failures separately from spec-quality failures so transport, MCP, sandbox, or state-runtime problems do not masquerade as graph-health issues.
28. [done] Add a documented bootstrap-runtime troubleshooting path for `supervisor` runs, including expected child executor config, fallback worktree mode, and interpretation of nested executor failures.

## Canonical Spec Writeback

37. [done] Make all `supervisor` writes to canonical spec files use one canonical YAML writer, including runtime-state updates after worktree sync.
38. [done] Add a deterministic post-write normalization/check path so canonical spec files are re-rendered or rejected if a `supervisor` run leaves them non-canonically formatted.
39. [done] Add regression coverage proving that a live-like `supervisor` refinement run leaves edited spec files canonically formatted without requiring a manual `spec_yaml_format.py` pass.

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
48. [done] Distinguish productive `split_required` refinements from real runtime/spec failures in `supervisor` completion status, latest-summary output, and loop accounting.
49. [done] Auto-upgrade ordinary seed-like refinement runs from the heuristic `fast` profile to the materialization profile when bootstrap child guidance is already in force, so central decomposition nodes do not time out before writing a bounded child spec.
50. [done] Preserve exact canonical source text during interrupted source-refinement cleanup so timeout or executor-environment failures cannot leave behind formatting-only spec diffs after runtime-state rollback.
51. [done] Increase nested executor timeout budgets and align the heuristic `fast` profile with `xhigh` reasoning so useful atomicity/split outcomes are not prematurely converted into timeout failures.
52. [done] Fix graph_refactor gate approval when the accepted worktree diff already changed status/maturity but `proposed_status` is null, so `--resolve-gate --decision approve` can clear review_pending instead of failing with an invalid linked->reviewed transition.
53. [done] Make `supervisor` report pending gate actions when no automatic spec gap is eligible, so review_pending, split_required, and blocked queues are not misreported as absence of graph work.
54. [done] Remove generic child-materialization bootstrap guidance from non-seed runs so proposal-only and ancestor-reconciliation prompts do not tell the child executor both to reconcile or emit a proposal artifact and to create canonical child spec files.
55. [done] Make review-gate approval idempotent when the accepted worktree already applied the proposed status, so `proposed_status == current status` clears the gate instead of failing transition validation.
56. [done] Prevent timeout-failed multi-file child-materialization runs from writing any canonical parent diff or escalated runtime-state unless every changed canonical file, including the new child spec, is accepted and synced as one atomic materialization result.
57. [done] Treat long quiet periods during `xhigh` spec-refinement runs as normal deliberation unless repeated progress windows show no stdout, no worktree/file mtime changes, and no other progress signals, so supervisor does not classify slow bounded reasoning as a runtime anomaly too early.
58. [done] Prevent ordinary `split_required` runs caused only by post-run atomicity failure from syncing oversized canonical source diffs; only decomposition-producing `split_required` results should write canonical content.
59. [done] Add regression coverage proving that `RUN_OUTCOME: done` followed by atomicity failure on a source-only diff leaves canonical source content unchanged while still recording `split_required` runtime state in run artifacts.
60. [done] Triage and reduce repeated nested executor stderr noise such as `failed to refresh available models: timeout waiting for child process to exit` so transport/runtime tails do not masquerade as graph-quality signals.
61. [done] Add a `--verbose` supervisor mode so default CLI output stays concise while full executor stdout/stderr, progress-grace diagnostics, and worktree trace remain available on demand.
62. [done] Restore canonical source specs unchanged when an ordinary source-only refinement fails validation before any accepted sync, including invalid YAML in the worktree candidate.
63. [done] Add a bounded worktree-YAML repair pass for recoverable spec-node formatting errors, such as misindented existing keys or multiline plain-sequence scalars with `:` continuations, so valid refinement intent is not discarded by trivial candidate serialization defects.
64. [done] De-prioritize or suppress `linked_continuation` selection for `linked` specs already at `maturity: 1.0` when the only continuation signal is `weak_structural_linkage_candidate`, so long-running `--loop` batches do not burn iterations on effectively complete nodes like `SG-SPEC-0021` or the earlier `SG-SPEC-0005` case.
65. [done] Strip stray patch-transcript markers from parse-failing worktree spec candidates before YAML validation, so nested refinement runs do not fail when a child executor leaves `*** Begin Patch` / `*** End Patch` residue in candidate YAML.
66. [done] Run worktree-YAML repair for parseable spec candidates when `acceptance` and `acceptance_evidence` cardinalities diverge, so nested list-indentation defects that still parse as YAML do not survive into semantic validation as false spec failures.

## Graph Shape Quality

67. [done] Add a graph-health signal and evaluator penalty for excessive one-child refinement ladders, so supervisor can prefer bounded aggregate nodes or sibling groupings over deep serial `refines` chains like the emerging `SG-SPEC-0043` -> `SG-SPEC-0048` subtree.
68. [done] Surface `SG-SPEC-0049` subtree-shape and lower-boundary handoff signals in `supervisor` run artifacts and derived queues as advisory runtime diagnostics, and suppress ordinary linked-continuation selection when active shape/handoff items already indicate rebalance-or-redirect pressure.

## Semantic Shape and Handoff

58. [done] Add refinement-shape signals for serial ladders, one-child delegation chains, and over-atomized subtrees so malformed shape becomes first-class graph health.
59. [done] Extend graph-health guidance with role-first semantic legibility checks so rewrite/merge is preferred when nodes stop reading as meaningful system roles.
60. [done] Define the SpecGraph-to-TechSpec handoff boundary so decomposition can stop at semantic saturation and emit downstream handoff artifacts instead of deeper graph slicing.
61. [done] Teach supervisor and proposal flows to recommend handoff, not further refinement, when a subtree becomes implementation-facing or loses semantic novelty.
