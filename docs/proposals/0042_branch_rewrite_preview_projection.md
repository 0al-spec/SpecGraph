# Branch Rewrite Preview Projection

## Status

Initial runtime slice implemented

Runtime realization:

- `tools/supervisor.py` projects ready `branch_rewrite_preview` candidates into
  `graph_backlog_projection` entries.
- `tools/supervisor.py` adds branch rewrite counts and source facts to
  `graph_dashboard`.
- `tools/supervisor.py` stops `graph_next_moves` from repeatedly recommending
  preview projection after the preview has reached backlog projection.
- `tests/test_supervisor.py` covers backlog rows, dashboard counts, and
  next-move handoff behavior.
- `docs/graph_backlog_projection_viewer_contract.md` documents the viewer
  contract for branch rewrite rows.
- `tools/proposal_runtime_registry.json` links this proposal to its bounded
  runtime slice.

## Context

Proposal 0040 introduced a review-only branch rewrite preview:

```text
runs/branch_rewrite_preview.json
```

Proposal 0041 introduced a game-master style `graph_next_moves` surface. That
surface now detects when a branch rewrite preview is ready and recommends
projecting it into visible work.

The missing link is the projection itself. Without it, a viewer can see that a
preview exists only by reading a standalone JSON artifact, and `graph_next_moves`
keeps recommending the same projection step.

## Problem

A ready branch rewrite preview contains actionable candidate rows, but before
this proposal those rows were not part of:

- `graph_backlog_projection`
- `graph_dashboard`
- dashboard headline cards
- viewer named filters
- next-move fallback selection

This makes the branch rewrite workflow too dependent on manual JSON reading.

## Goals

- Project ready branch rewrite candidates into normalized backlog rows.
- Keep the projection derived-only and review-first.
- Add dashboard counts and source facts so viewers can show branch rewrite
  pressure without opening the raw artifact.
- Let `graph_next_moves` advance from "project preview" to "review backlog item"
  after projection is complete.
- Preserve canonical specs and branch rewrite preview artifacts unchanged.

## Non-Goals

- Applying branch rewrites.
- Mutating `specs/nodes/*.yaml`.
- Creating proposal-lane nodes for each candidate.
- Replacing branch rewrite preview as the source of candidate details.
- Adding ContextBuilder UI code in this repository.

## Output Contract

Each actionable branch rewrite candidate becomes one backlog row:

```json
{
  "source_artifact": "branch_rewrite_preview",
  "domain": "branch_rewrite",
  "subject_kind": "spec",
  "subject_id": "SG-SPEC-0026",
  "status": "rewrite_node_role_boundary",
  "review_state": "preview_only",
  "next_gap": "review_branch_rewrite_candidate",
  "priority": "high"
}
```

The row `details` include:

- `root_spec_id`
- `preview_status`
- `risk_level`
- `rewrite_classes`
- `findings`
- `rewrite_recommendation`
- `current_role_summary`
- `proposed_summary`
- `proposed_patch_preview`
- `story_gap`

Dashboard adds:

- headline card `branch_rewrite_candidates`
- `sections.health.branch_rewrite_preview_status`
- `sections.health.branch_rewrite_root_spec_id`
- `sections.health.branch_rewrite_candidate_count`
- `sections.health.branch_rewrite_candidate_spec_ids`
- `sections.health.branch_rewrite_story_gap_spec_ids`
- `viewer_projection.named_filters.branch_rewrite_candidates`

## Acceptance Criteria

- Ready branch rewrite candidates appear in `graph_backlog_projection.entries[]`.
- The backlog summary includes `domain_counts.branch_rewrite` and
  `source_artifact_counts.branch_rewrite_preview`.
- The dashboard exposes a headline count and health-section details for branch
  rewrite candidates.
- `graph_next_moves` no longer recommends `project_branch_rewrite_preview` once
  the preview candidates are already projected into backlog.
- All generated surfaces remain derived-only.
