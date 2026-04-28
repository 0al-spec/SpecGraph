# Branch Rewrite Preview Mode

## Status

Initial runtime slice implemented

Runtime realization:

- `tools/branch_rewrite_preview_policy.json` defines the preview-only mode
  contract, status mapping, selection limits, and viewer-facing fields.
- `tools/supervisor.py` exposes `--build-branch-rewrite-preview --target-spec
  SG-SPEC-XXXX` and writes only `runs/branch_rewrite_preview.json`.
- `tests/test_supervisor.py` covers input validation, mutation boundary,
  node-limit handling, malformed references, gate blocking, and standalone CLI
  dispatch.
- `tools/proposal_runtime_registry.json` links this proposal to its first
  synchronous runtime slice.

## Context

SpecGraph now has enough graph-health, role-legibility, topology-prose, and
review-feedback surfaces to see a new class of refinement problem.

A single node can be locally valid while a whole branch reads poorly as a
semantic story. The symptom is visible when a subtree is read as a compact
"book":

- neighboring specs repeat edge, gateway, and handoff facts;
- boundary nodes describe their graph placement more than their system role;
- historical cleanup pressure remains mixed into current active prose;
- local refinements improve one node but leave the branch narrative fragmented.

Proposal 0036 already defines the principle:

> topology facts are not spec prose.

The missing capability is a bounded supervisor mode that can look at a branch
as one reviewable semantic projection before any canonical rewrite happens.

## Problem

Today the supervisor mostly works node-by-node. That is safe, but it makes
branch-level readability issues hard to repair.

If the operator wants to "rewrite a branch", there are two unsafe extremes:

- continue ordinary single-node refinement forever and miss the branch-level
  story;
- let the supervisor directly rewrite many canonical specs at once.

The first path preserves safety but under-fixes the problem.

The second path is too much authority: it can change multiple specs, stable
boundaries, maturity signals, and review expectations before a human has seen
the proposed branch-level narrative.

## Goals

- Introduce a review-first branch rewrite preview mode.
- Let the supervisor inspect one bounded active subtree as a readable semantic
  projection.
- Detect topology-prose, role-obscured, historical-lineage, and duplicated
  relationship narration across the branch.
- Emit one derived artifact that proposes rewrite pressure per node without
  mutating canonical specs.
- Give the viewer enough structure to show branch rewrite candidates, risk,
  and next actions.
- Preserve stable spec IDs, graph edges, statuses, and timestamps until a
  later explicit apply path exists.

## Non-Goals

- Directly rewriting `specs/nodes/*.yaml`.
- Applying multi-node patches automatically.
- Creating, deleting, merging, archiving, or superseding spec nodes.
- Replacing ordinary targeted refinement, split proposal flow, or child
  materialization.
- Solving every legacy topology-prose issue in one pass.
- Making branch rewrite preview a hard validator.

## Core Proposal

Add a supervisor mode:

```bash
python3 tools/supervisor.py \
  --build-branch-rewrite-preview \
  --target-spec SG-SPEC-0026
```

The mode builds a derived, review-only artifact:

```text
runs/branch_rewrite_preview.json
```

The artifact answers:

- what branch was inspected;
- which active nodes are semantically clear;
- which nodes mostly restate graph topology;
- where historical semantics should be visually or narratively de-emphasized;
- where a node should be rewritten, merged, split, preserved, or left alone;
- what the proposed branch story would read like if accepted.

The artifact must not modify:

- `specs/nodes/*.yaml`
- `proposal_lane/nodes/*.json`
- `intent_layer/nodes/*.json`
- `runs/proposals/*.json`
- git worktrees

This first slice is preview-only.

## Input Contract

Initial inputs:

- `root_spec_id`: required active branch root, supplied through the existing
  `--target-spec` selector.
- `max_depth`: optional depth limit, default bounded by policy.
- `include_historical`: optional boolean, default `false`.
- `include_descendants`: optional traversal mode, default active `refines`
  descendants.
- `operator_note`: optional human instruction for the preview lens.

The supervisor should reject or degrade gracefully when:

- the root spec is missing;
- the selected branch exceeds the configured node limit;
- the branch contains broken references;
- the branch has unresolved gate states that make rewrite preview misleading.

Invalid input should produce a structured artifact with `preview_status` such as
`invalid_root`, `branch_too_large`, or `blocked_by_unresolved_gate`, not a crash.

### Status Mapping

`preview_status`, `review_state`, and `next_gap` should be derived together so
viewers do not need to infer blocked states.

Initial mapping:

- `ready_for_review` -> `review_state: preview_only`,
  `next_gap: human_review_before_apply`
- `no_candidates` -> `review_state: preview_only`,
  `next_gap: no_branch_rewrite_needed`
- `invalid_root` -> `review_state: blocked`,
  `next_gap: repair_branch_rewrite_target`
- `branch_too_large` -> `review_state: blocked`,
  `next_gap: narrow_branch_rewrite_scope`
- `blocked_by_unresolved_gate` -> `review_state: blocked`,
  `next_gap: resolve_branch_gate_before_preview`
- `broken_reference` -> `review_state: blocked`,
  `next_gap: repair_graph_reference`
- `empty_branch` -> `review_state: blocked`,
  `next_gap: choose_nonempty_branch`

## Output Contract

The artifact should include:

```json
{
  "artifact_kind": "branch_rewrite_preview",
  "schema_version": 1,
  "generated_at": "...",
  "preview_status": "ready_for_review",
  "review_state": "preview_only",
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "target": {
    "root_spec_id": "SG-SPEC-0026",
    "resolved_spec_ids": []
  },
  "provenance": {
    "source_graph_ref": "",
    "source_git_commit": "",
    "selected_spec_ids": [],
    "inspected_edges": [],
    "policy_refs": [
      "docs/proposals/0036_topology_facts_are_not_spec_prose.md"
    ]
  },
  "review_evidence": {
    "candidate_class_counts": {},
    "recommendation_basis": [],
    "blocked_by": []
  },
  "branch_story": {
    "current_summary": "",
    "proposed_summary": "",
    "story_gaps": []
  },
  "node_rewrite_candidates": [],
  "next_gap": "human_review_before_apply"
}
```

### Node Candidate Shape

Each `node_rewrite_candidates` item should include:

- `spec_id`
- `title`
- `presence_state`
- `current_role_summary`
- `rewrite_recommendation`
- `rewrite_classes`
- `findings`
- `suggested_action`
- `risk_level`
- `proposed_summary`
- `proposed_patch_preview`
- `blocked_by`

Initial `rewrite_classes`:

- `remove_graph_topology_prose`
- `clarify_boundary`
- `archive_historical_semantics`
- `merge_bookkeeping_slice`
- `preserve_boundary_contract`
- `split_needed`
- `no_change`

Initial `suggested_action`:

- `rewrite_node_role_boundary`
- `merge_bookkeeping_slice`
- `emit_split_proposal`
- `preserve_as_boundary_contract`
- `deemphasize_historical_lineage`
- `no_change`

## Review Boundary

Branch rewrite preview is not a write authority.

It may recommend edits, but those edits are only review material. A human must
choose one of the follow-up paths:

- run ordinary targeted refinement for one node;
- emit a split proposal;
- create a future branch-rewrite apply packet;
- decline the preview and keep the current branch.

The preview should therefore preserve enough evidence for review:

- `provenance.source_graph_ref` and `provenance.source_git_commit` for the
  source graph version;
- `provenance.selected_spec_ids` for the selected branch;
- `provenance.inspected_edges` for inspected topology;
- `review_evidence.candidate_class_counts` plus each candidate's
  `rewrite_classes` for candidate classes;
- each candidate's `findings`, `rewrite_recommendation`, and `blocked_by` for
  why the node is or is not recommended for rewrite;
- `provenance.policy_refs` and `review_evidence.recommendation_basis` for
  whether the recommendation follows proposal 0036 topology-prose guidance.

## Viewer Surface

ContextBuilder should be able to show this artifact without understanding the
full supervisor runtime.

Minimum viewer projection:

- branch root and selected node count;
- `preview_status`, `review_state`, and `next_gap`;
- current branch story versus proposed branch story;
- per-node rewrite cards grouped by `suggested_action`;
- risk chips for multi-node rewrite pressure;
- explicit "preview only, not canonical" warning.

The viewer should not merge this preview into the canonical force graph as if it
were a real spec layer. It is an inspection overlay.

## Relationship To Existing Work

### Proposal 0017

[0017_role_first_semantic_bias_for_supervisor.md](0017_role_first_semantic_bias_for_supervisor.md)
defines role-first semantic bias and role-obscured/bookkeeping-only signals.

Branch rewrite preview uses those signals as input but raises the scope from
one node to a readable branch projection.

### Proposal 0036

[0036_topology_facts_are_not_spec_prose.md](0036_topology_facts_are_not_spec_prose.md)
defines the topology-prose rule.

Branch rewrite preview is the review-first operational surface for applying
that rule across a bounded branch.

### Exploration Preview

Exploration preview is assumption-mode for raw intent.

Branch rewrite preview is different: it operates on existing canonical specs,
but only emits derived review material. It must therefore be stricter about
source references, stable IDs, and mutation boundaries.

## Runtime Realization Path

Phase 1:

- Add this proposal.
- Keep implementation out of scope.

Phase 2:

- Add `tools/branch_rewrite_preview_policy.json`.
- Add `--build-branch-rewrite-preview`.
- Emit `runs/branch_rewrite_preview.json`.
- Add tests for input validation, mutation boundary, node-limit handling, and
  malformed graph references.

Status: implemented as the first preview-only runtime slice.

Phase 3:

- Add a viewer contract and ContextBuilder overlay.
- Show branch-story summary and per-node rewrite candidates.
- Add dashboard/backlog projection for branch rewrite pressure.

Phase 4:

- Consider a separate apply mechanism only after preview semantics stabilize.
- Any apply path must be gated, deterministic, and scoped to an approved packet.

## Acceptance Criteria

- The proposal defines branch rewrite as preview-first, not direct mutation.
- The initial artifact contract includes a hard mutation boundary.
- The mode can express per-node rewrite pressure without changing canonical
  specs.
- The viewer has enough structure to show a readable branch story and node
  rewrite candidates.
- Future runtime work can implement the preview without redefining authority,
  input, or output semantics.
