# Graph Next Moves Game-Master Surface

## Status

Initial runtime slice implemented

Runtime realization:

- `tools/graph_next_moves_policy.json` defines the read-only next-move policy,
  scene vocabulary, move vocabulary, and viewer-facing fields.
- `tools/supervisor.py` exposes `--build-graph-next-moves` and writes only
  `runs/graph_next_moves.json`.
- `make next-move` gives operators a compact shortcut for refreshing the
  advisory surface.
- `tests/test_supervisor.py` covers branch-preview prioritization, backlog
  fallback, steady-state fallback, standalone dispatch, and mutation boundary.
- `tools/proposal_runtime_registry.json` links this proposal to its bounded
  runtime slice.

## Context

SpecGraph now has many derived surfaces:

- graph health and trends;
- graph dashboard and backlog projection;
- proposal runtime and promotion indexes;
- review-feedback learning-loop records;
- exploration and branch rewrite previews;
- SpecPM and Metrics bridge surfaces.

That is enough observability, but it leaves an operator question open:

> What should I do next?

Previously that answer came from chat history and human memory. That is not
native to SpecGraph. If the graph is supposed to guide the operator, the graph
needs an explicit derived "current scene" surface: one bounded recommended move,
plus alternatives and blocked moves.

The metaphor is a game master: it does not play the character for the user, but
it describes the current scene, highlights pressure, and offers a lawful next
move.

## Problem

The graph can expose many gaps at once. A dashboard may show hundreds of
backlog rows, multiple proposal follow-ups, review-feedback records, and preview
artifacts. That is accurate but not directive.

Without a next-move layer:

- operators ask chat to reconstruct process state from conversation history;
- viewers can show counts but not the next bounded scene;
- supervisor runs can be technically available but hard to sequence;
- important review-first artifacts, such as branch rewrite previews, can remain
  visible only as standalone JSON rather than entering the work rhythm.

## Goals

- Add one read-only derived surface that recommends one bounded next move.
- Base recommendations on graph-derived artifacts, not chat memory.
- Prefer review-first preview projection when a preview artifact is ready.
- Fall back to the normalized graph backlog when no special scene is active.
- Keep alternatives and blocked moves visible without letting them override the
  primary recommendation.
- Make the output directly consumable by ContextBuilder or another viewer.
- Preserve the human merge/review boundary.

## Non-Goals

- Autonomous looping until the graph is "done".
- Auto-applying branch rewrites.
- Mutating `specs/nodes/*.yaml`, proposal-lane nodes, intent-layer nodes, or
  queues.
- Reading GitHub or chat history.
- Replacing the graph dashboard or backlog projection.
- Turning all possible heuristics into hard policy.

## Core Proposal

Add a supervisor command:

```bash
python3 tools/supervisor.py --build-graph-next-moves
```

The command writes:

```text
runs/graph_next_moves.json
```

The artifact contains:

- `current_scene`: the selected graph scene;
- `scene_confidence`: advisory confidence;
- `recommended_next_move_kind`: compact move category;
- `recommended_next_move`: full move object with reason, next gap, source
  artifacts, bounded scope, command hint, and success condition;
- `alternatives`: lower-priority possible moves;
- `blocked_moves`: useful but currently blocked moves;
- `source_facts`: compact source summaries from branch rewrite preview, graph
  backlog projection, and proposal runtime index;
- `canonical_mutations_allowed: false`;
- `tracked_artifacts_written: false`.

Initial scene order:

1. `source_artifact_blocked`
2. `branch_rewrite_preview_ready`
3. `high_priority_backlog`
4. `runtime_realization_backlog`
5. `steady_state`

This first slice intentionally favors ready branch rewrite preview over generic
backlog pressure because preview artifacts represent a human-review scene that
can otherwise fall out of the normal dashboard flow.

Within one backlog priority bucket, concrete runtime gaps should outrank broad
draft-reference review rows. For example, a `metric_pack_runs` row with
`next_gap: "define_metric_value_adapter"` is more actionable than an
`external_consumer_handoffs` row with `next_gap: "review_draft_reference"`.
This keeps the game-master surface pointed at bounded implementation follow-ups
once downstream artifacts have already exposed specific missing adapters.

## Output Contract

Minimal shape:

```json
{
  "artifact_kind": "graph_next_moves",
  "schema_version": 1,
  "current_scene": "branch_rewrite_preview_ready",
  "scene_confidence": "high",
  "recommended_next_move_kind": "project_branch_rewrite_preview",
  "recommended_next_move": {
    "move_id": "next_move::branch_rewrite_preview::project",
    "kind": "project_branch_rewrite_preview",
    "title": "Project branch rewrite preview into visible work",
    "reason": "...",
    "next_gap": "project_branch_rewrite_preview",
    "source_artifacts": ["runs/branch_rewrite_preview.json"],
    "bounded_scope": ["SG-SPEC-0026"],
    "subject": {},
    "command_hint": "...",
    "success_condition": "...",
    "review_required": true,
    "blocked_by": []
  },
  "alternatives": [],
  "blocked_moves": [],
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

## Viewer Guidance

A viewer should treat this as an advisory panel, not a mutation engine.

Recommended UI:

- top chip for `current_scene`;
- main card for `recommended_next_move`;
- smaller cards for `alternatives`;
- muted list for `blocked_moves`;
- source fact footer showing branch preview status, backlog count, and proposal
  runtime backlog count;
- visible boundary copy: "Advisory game-master surface; not canonical."

## Acceptance Criteria

- `--build-graph-next-moves` writes only `runs/graph_next_moves.json`.
- The artifact recommends branch rewrite projection when
  `runs/branch_rewrite_preview.json` is ready with candidates.
- The artifact falls back to the highest-priority graph backlog entry when no
  branch preview scene is active.
- The artifact emits `steady_state` with move kind `none` when no derived gap is
  visible.
- Summary output stays compact.
- Tests cover standalone dispatch and rejection of combined refinement flags.
