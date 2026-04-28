# Graph Backlog Projection Viewer Contract

This document fixes the ContextBuilder/viewer-facing contract for
`runs/graph_backlog_projection.json` and its dashboard drill-down relationship.

Use this contract when implementing:

- dashboard backlog drill-down rows;
- backlog priority/domain/next-gap filters;
- graph-wide "what should I look at next?" panels;
- viewer warnings for stale or inconsistent generated artifacts.

## 1. Source Artifact

Build command:

```bash
python3 tools/supervisor.py --build-graph-backlog-projection
```

Alternative viewer refresh command:

```bash
python3 tools/supervisor.py --build-viewer-surfaces
```

Read:

- `runs/graph_backlog_projection.json`

The artifact is a derived read model. It is not canonical graph truth and it is
not a replacement for `specs/nodes/*.yaml`.

The artifact is static until rebuilt. Viewers should expose `generated_at` or
file `mtime` when available so users can tell whether the backlog projection is
fresh.

## 2. Recommended ContextBuilder Endpoint

Recommended route:

```text
GET /api/graph-backlog-projection
```

Server behavior:

- read only `SpecGraph/runs/graph_backlog_projection.json`;
- do not accept an arbitrary path or query-param path;
- return `404` when the artifact has not been built;
- return `422` when the JSON cannot be parsed;
- return `503` when the server is not configured with a SpecGraph root;
- return the artifact as-is without server-side transformation.

Capability detection is optional. If the server has a configured SpecGraph
root, the endpoint may be present even before the artifact exists.

## 3. Top-Level Stable Fields

Viewer code may rely on these top-level fields:

- `artifact_kind`
- `schema_version`
- `generated_at`
- `source_artifacts`
- `entry_count`
- `entries`
- `summary`
- `viewer_projection`

Expected top-level shape:

```json
{
  "artifact_kind": "graph_backlog_projection",
  "schema_version": 1,
  "generated_at": "2026-04-28T12:00:00Z",
  "source_artifacts": {},
  "entry_count": 204,
  "entries": [],
  "summary": {
    "entry_count": 204,
    "priority_counts": {},
    "domain_counts": {},
    "next_gap_counts": {},
    "source_artifact_counts": {},
    "subject_kind_counts": {}
  },
  "viewer_projection": {
    "priorities": {},
    "domains": {},
    "next_gap": {},
    "source_artifacts": {},
    "subject_kinds": {},
    "named_filters": {}
  }
}
```

`entry_count`, `summary.entry_count`, and `entries.length` should agree. If a
viewer observes a mismatch, it should render a warning instead of silently
trusting one value.

## 4. Entry Contract

Each `entries[]` item is one backlog row.

Stable fields:

- `backlog_id`
- `domain`
- `source_artifact`
- `source_artifact_path`
- `subject_kind`
- `subject_id`
- `title`
- `status`
- `review_state`
- `next_gap`
- `priority`
- `details`

Minimum rendering subset:

- `subject_id`
- `domain`
- `priority`
- `next_gap`
- `source_artifact`

Recommended React key:

- `backlog_id`
- fallback: `${source_artifact}:${domain}:${subject_id}:${next_gap}`

Example:

```json
{
  "backlog_id": "graph_health_overlay::health::SG-SPEC-0001::resolve_review_gate",
  "domain": "health",
  "source_artifact": "graph_health_overlay",
  "source_artifact_path": "runs/graph_health_overlay.json",
  "subject_kind": "spec",
  "subject_id": "SG-SPEC-0001",
  "title": "Root Spec",
  "status": "review_pending",
  "review_state": "",
  "next_gap": "resolve_review_gate",
  "priority": "high",
  "details": {
    "signals": ["refinement_fan_out_pressure"]
  }
}
```

Viewers should tolerate extra fields and unknown values.

## 5. Priority Contract

Current priority values:

- `high`
- `medium`
- `low`
- `info`

Future priority values are allowed.

Recommended display order:

1. `high`
2. `medium`
3. `low`
4. `info`
5. unknown future priorities, sorted by label

`info` is currently used for visible but non-urgent rows such as accepted-risk
review-feedback follow-up.

## 6. Domain Contract

Current domains:

- `health`
- `proposals`
- `implementation`
- `evidence`
- `external_consumers`
- `specpm`
- `metrics`
- `process_feedback`

Future domains are allowed. Viewers should not drop unknown domains; render them
as ordinary groups with a neutral label.

## 7. Summary Contract

Use `summary` for counts:

- `summary.entry_count`
- `summary.priority_counts`
- `summary.domain_counts`
- `summary.next_gap_counts`
- `summary.source_artifact_counts`
- `summary.subject_kind_counts`

These are count maps. Missing keys mean zero.

Viewers should use `summary.entry_count` or top-level `entry_count` for a
"Browse entries" button, but should warn when either count disagrees with
`entries.length`.

## 8. Viewer Projection Contract

Use `viewer_projection` for id groups and quick filters:

- `viewer_projection.priorities`
- `viewer_projection.domains`
- `viewer_projection.next_gap`
- `viewer_projection.source_artifacts`
- `viewer_projection.subject_kinds`
- `viewer_projection.named_filters`

Each group value is a list of `backlog_id` strings.

Known named filters:

- `ready_for_review`
- `blocked_by_repo_state`
- `human_review_required`
- `missing_trace_contract`
- `missing_evidence_contract`
- `metric_threshold_pressure`
- `proposal_runtime_realization`
- `promotion_review_ready`
- `review_feedback_open`
- `review_feedback_invalid`
- `review_feedback_accepted_risk`

Future named filters are allowed.

## 9. Dashboard Relationship

The graph dashboard remains the summary source:

- `runs/graph_dashboard.json`
- `sections.backlog.backlog_entry_count`
- `sections.backlog.priority_counts`
- `sections.backlog.domain_counts`
- `sections.backlog.next_gap_counts`

The backlog projection remains the row source:

- `runs/graph_backlog_projection.json`
- `entries[]`

Viewers should not reconstruct `entries[]` from dashboard counts. Use dashboard
counts for overview cards and use the backlog projection for drill-down rows.

## 10. Metrics Alias Companion Rule

Metric headline counts come from `runs/graph_dashboard.json`.

For dashboard metric headlines:

- use `sections.metrics.below_threshold_authoritative_metric_ids`;
- do not count `sections.metrics.below_threshold_metric_ids` directly.

`below_threshold_metric_ids` may include compatibility aliases such as
`sib_proxy`. `below_threshold_authoritative_metric_ids` excludes alias-only
metrics and is the stable count source for threshold score headlines.

For detailed metric rows, use `runs/metric_signal_index.json` when available.
Alias rows are identified there by fields such as:

- `alias_of`
- `threshold_authority_state: alias_only`

Alias rows should be rendered as compatibility signals, not as additional
authoritative threshold failures.

## 11. Error And Staleness Handling

Recommended UI states:

- `missing`: endpoint returns `404`; show a "build backlog projection" hint.
- `invalid`: endpoint returns `422`; show parse error and do not render stale
  rows as current.
- `stale`: `generated_at` or file `mtime` is older than the dashboard artifact;
  show a warning but allow inspection.
- `count_mismatch`: `entry_count`, `summary.entry_count`, and `entries.length`
  disagree; show a warning and prefer `entries.length` for rendered row count.

