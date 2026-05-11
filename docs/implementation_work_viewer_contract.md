# Implementation Work Viewer Contract

This document defines the planned viewer-facing contract for the
Implementation Work layer.

The layer sits between canonical specifications and runtime/code work:

```text
Exploration -> Specification -> Implementation Work -> Runtime / Evidence
```

It is a planning and handoff surface. It must not be rendered as canonical
SpecGraph truth and must not directly mutate code.

## 1. Intended Viewer Jobs

ContextBuilder should eventually let a user:

1. select a canonical spec or graph region;
2. request implementation planning for that target;
3. inspect what has already been implemented;
4. inspect the delta between implemented baseline and target spec state;
5. review proposed implementation work items;
6. decide whether to hand the work to a coding agent.

The first implementation should be read-only after artifact generation.

## 2. Planned Source Artifacts

Policy:

- `tools/implementation_delta_policy.json`

Planned read models:

- `runs/implementation_delta_snapshot.json`
- `runs/implementation_work_index.json`
- `runs/graph_backlog_projection.json` for normalized backlog rows sourced
  from `implementation_work_index.implementation_backlog.items[]`
- `runs/graph_dashboard.json` for headline and section-level Implementation
  Work counts

These artifacts are derived supervisor outputs. They are rebuildable planning
surfaces, not canonical spec truth and not runtime code.

## 3. Planned Supervisor Commands

Commands:

```bash
python3 tools/supervisor.py \
  --build-implementation-delta-snapshot \
  --target-scope-kind spec \
  --target-spec-ids SG-SPEC-0001

python3 tools/supervisor.py \
  --build-implementation-delta-snapshot \
  --target-scope-kind active_subtree \
  --target-spec-ids SG-SPEC-0001 \
  --operator-intent "Plan implementation work for this active region."

python3 tools/supervisor.py --build-implementation-work-index
```

Both commands should be standalone derived-artifact modes.

The CLI should map directly onto the JSON target contract:

- `--target-scope-kind spec` -> `target.target_scope_kind = "spec"`
- `--target-spec-ids SG-SPEC-0001,SG-SPEC-0002` ->
  `target.target_spec_ids = ["SG-SPEC-0001", "SG-SPEC-0002"]`
- `--target-scope-kind active_subtree` treats `target_spec_ids` as region roots
  and expands `target.resolved_target_spec_ids` through active `refines`
  descendants.

Supported target scopes:

- `spec`: exact list of canonical spec ids.
- `active_subtree`: graph-region selector; includes each requested root spec
  plus active descendants connected by `refines` edges, excluding historical or
  superseded descendant specs.

Region scopes use the same `target_scope_kind` vocabulary rather than a second
target model.

They must reject ordinary refinement flags unless a future
operator-request-packet contract explicitly authorizes the combination.

## 4. Recommended ContextBuilder Endpoints

Follow the same pattern as existing `SpecPM` and exploration-preview endpoints.

### `GET /api/implementation-delta-snapshot`

Reads `SpecGraph/runs/implementation_delta_snapshot.json`.

Recommended success response:

```json
{
  "path": "/abs/path/to/SpecGraph/runs/implementation_delta_snapshot.json",
  "mtime": 1777184450.0,
  "mtime_iso": "2026-04-26T06:20:50+00:00",
  "data": {
    "artifact_kind": "implementation_delta_snapshot"
  }
}
```

Recommended errors:

- `503` when the server was not started with `--specgraph-dir`;
- `404` when the artifact was not built yet;
- `422` when JSON cannot be read or parsed.

### `POST /api/implementation-delta-snapshot/build`

Request body:

```json
{
  "target_scope_kind": "spec",
  "target_spec_ids": ["SG-SPEC-0001"],
  "operator_intent": "Plan implementation work for this ready spec region."
}
```

The server should validate:

- `target_scope_kind` is supported;
- `target_spec_ids` is non-empty for `spec` scope;
- `target_spec_ids` is non-empty and names valid root specs for
  `active_subtree` scope;
- `operator_intent` is non-empty.

Missing trace or evidence baselines should not prevent a delta snapshot from
being displayed. They should surface as readiness states such as
`blocked_by_trace_gap` or `blocked_by_evidence_gap`.

### `GET /api/implementation-work-index`

Reads `SpecGraph/runs/implementation_work_index.json`.

### `POST /api/implementation-work-index/build`

Builds work items from the latest implementation delta snapshot.

The server should return `422` when the delta snapshot is missing or invalid.

## 5. Delta Snapshot Contract

Viewer code should treat these fields as stable:

- `artifact_kind`
- `schema_version`
- `generated_at`
- `policy_reference`
- `layer`
- `baseline`
- `target`
- `delta`
- `status`
- `review_state`
- `next_gap`
- `canonical_mutations_allowed`
- `runtime_code_mutations_allowed`

For delta baseline purposes, `implementation_state: "verified"` is treated as
already implemented. Verification is a stronger implementation state, so a
verified spec must not re-enter the implementation work backlog merely because
it is not listed under the weaker `implemented` projection bucket.

Expected top-level shape:

```json
{
  "artifact_kind": "implementation_delta_snapshot",
  "schema_version": 1,
  "layer": "implementation_work",
  "baseline": {
    "git_commit": "abc123",
    "graph_version": "abc123",
    "implemented_spec_ids": ["SG-SPEC-0001"],
    "trace_baseline_status": "available",
    "evidence_baseline_status": "partial"
  },
  "target": {
    "target_scope_kind": "spec",
    "target_spec_ids": ["SG-SPEC-0042"],
    "valid_target_spec_ids": ["SG-SPEC-0042"],
    "resolved_target_spec_ids": ["SG-SPEC-0042"],
    "missing_target_spec_ids": [],
    "target_git_commit": "def456",
    "operator_intent": "Plan implementation work for this ready spec.",
    "scope_resolution": {
      "selector": "exact_spec_list",
      "expanded": false,
      "root_spec_ids": ["SG-SPEC-0042"],
      "resolved_count": 1,
      "excludes_historical_or_superseded": false
    }
  },
  "delta": {
    "new_spec_ids": [],
    "changed_spec_ids": ["SG-SPEC-0042"],
    "changed_contract_refs": [],
    "changed_acceptance_refs": [],
    "missing_trace_refs": [],
    "required_test_refs": [],
    "evidence_gap_refs": [],
    "likely_affected_code_refs": [],
    "likely_affected_code_refs_by_spec": {
      "SG-SPEC-0042": []
    }
  },
  "status": "ready_for_planning",
  "review_state": "ready_for_planning",
  "next_gap": "review_implementation_delta",
  "canonical_mutations_allowed": false,
  "runtime_code_mutations_allowed": false
}
```

## 6. Work Index Contract

Viewer code should treat these fields as stable:

- `artifact_kind`
- `schema_version`
- `generated_at`
- `policy_reference`
- `source_delta_snapshot`
- `entry_count`
- `entries`
- `viewer_projection`

Each `entries[]` item should have:

- `work_item_id`
- `affected_spec_ids`
- `implementation_reason`
- `delta_refs`
- `required_tests`
- `expected_evidence`
- `likely_code_refs`
- `readiness`
- `blockers`
- `next_gap`

Expected entry shape:

```json
{
  "work_item_id": "implementation_work::SG-SPEC-0042::contract-delta",
  "affected_spec_ids": ["SG-SPEC-0042"],
  "implementation_reason": "changed_acceptance",
  "delta_refs": ["changed_acceptance_refs::SG-SPEC-0042"],
  "required_tests": [],
  "expected_evidence": [],
  "likely_code_refs": [],
  "readiness": "ready_for_planning",
  "blockers": [],
  "next_gap": "review_implementation_delta"
}
```

## 7. Status Vocabulary

Initial readiness values:

- `ready_for_planning`
- `blocked_by_trace_gap`
- `blocked_by_evidence_gap`
- `blocked_by_spec_quality`
- `ready_for_coding_agent`
- `in_progress`
- `implemented_pending_evidence`
- `implemented`

Recommended tones:

- `ready_for_coding_agent`: ready/green
- `ready_for_planning`: neutral/blue
- `blocked_by_trace_gap`: amber
- `blocked_by_evidence_gap`: amber
- `blocked_by_spec_quality`: red
- `in_progress`: active/blue
- `implemented_pending_evidence`: amber
- `implemented`: muted green

Special delta-only states:

- `empty_delta`: neutral; nothing new to implement for the selected target.
- `invalid_target_scope`: red; target input must be repaired before planning.

## 8. Recommended UI

First slice:

- Add an `Implementation Work` panel.
- Add target input by spec id.
- Show the selected target scope.
- For `active_subtree`, show both root spec ids and
  `resolved_target_spec_ids` so the user can inspect the expanded region before
  any coding-agent handoff.
- Show baseline summary.
- Show delta counts:
  changed specs, new specs, changed contracts, changed acceptance, missing
  trace, evidence gaps, required tests.
- Show work item cards from `implementation_work_index.entries[]`.
- Show boundary label:
  `Planning only: no canonical spec or code mutation`.

Useful filters:

- `ready_for_planning`
- `ready_for_coding_agent`
- `blocked_by_trace_gap`
- `blocked_by_evidence_gap`
- `blocked_by_spec_quality`
- `implemented_pending_evidence`

## 9. Non-Goals

Do not implement these in the first viewer slice:

- no automatic coding-agent run;
- no automatic PR creation;
- no direct code mutation;
- no direct canonical spec mutation;
- no `implementation_lane/nodes/*.json`;
- no permanent markdown task queue.

## 10. Acceptance Criteria

The ContextBuilder implementation is complete for the first slice when:

- the viewer can build and read the delta snapshot once the supervisor command
  exists;
- the viewer can build and read the work index once the supervisor command
  exists;
- target scope is visible;
- baseline and delta summaries are visible;
- work items are visible as cards or rows;
- readiness and blockers are visible;
- the UI clearly distinguishes implementation planning from canonical graph
  truth and from runtime code mutation.
