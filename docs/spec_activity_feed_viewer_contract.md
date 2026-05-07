# Spec Activity Feed Viewer Contract

This document defines the ContextBuilder/viewer-facing contract for
`runs/spec_activity_feed.json`.

The feed exists because node activity is broader than canonical YAML
`updated_at` changes. Trace/evidence baselines, proposal-lane updates,
implementation-work emissions, and review-feedback fixes can all update a
spec's practical state without editing `specs/nodes/*.yaml`.

## 1. Source Artifact

Build command:

```bash
python3 tools/supervisor.py --build-spec-activity-feed
```

Make shortcut:

```bash
make spec-activity
```

The artifact is also refreshed by:

```bash
make viewer-surfaces
```

Read:

- `runs/spec_activity_feed.json`

The artifact is a derived read model. It is not canonical graph truth and it
must not mutate specs, proposal-lane nodes, or runtime code.

## 2. Recommended ContextBuilder Endpoint

Recommended route:

```text
GET /api/spec-activity?limit=N&since=ISO
```

Server behavior:

- read only `SpecGraph/runs/spec_activity_feed.json`;
- return the artifact as raw `data` inside the same metadata envelope used by
  other SpecGraph runs artifacts;
- apply optional `limit` and `since` filters on `data.entries[]` if needed;
- return `404` when the artifact has not been built;
- return `422` when the JSON cannot be parsed;
- return `503` when the server is not configured with a SpecGraph root.

The viewer should not run `git log` or infer spec activity from path
heuristics. SpecGraph owns the mapping from repository activity to spec-node
activity.

## 3. Top-Level Fields

Stable fields:

- `artifact_kind`
- `schema_version`
- `generated_at`
- `source_artifacts`
- `entry_count`
- `entries`
- `summary`
- `viewer_projection`
- `viewer_contract`
- `canonical_mutations_allowed`
- `tracked_artifacts_written`

Expected shape:

```json
{
  "artifact_kind": "spec_activity_feed",
  "schema_version": 1,
  "generated_at": "2026-05-08T00:00:00+00:00",
  "source_artifacts": {
    "policy": "tools/spec_activity_feed_policy.json",
    "git_paths": []
  },
  "entry_count": 0,
  "entries": [],
  "summary": {
    "entry_count": 0,
    "event_type_counts": {},
    "spec_event_counts": {}
  },
  "viewer_projection": {
    "event_type": {},
    "spec_id": {},
    "named_filters": {}
  },
  "viewer_contract": {
    "contract_doc": "docs/spec_activity_feed_viewer_contract.md",
    "recommended_endpoint": "GET /api/spec-activity?limit=N&since=ISO",
    "source_artifact": "runs/spec_activity_feed.json"
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

`entry_count`, `summary.entry_count`, and `entries.length` should agree.

## 4. Entry Contract

Each `entries[]` item is one normalized activity event.

Stable fields:

- `event_id`
- `event_type`
- `spec_id`
- `title`
- `occurred_at`
- `summary`
- `source_kind`
- `source_ref`
- `source_paths`
- `viewer`

`spec_id` is empty for graph-level process events that cannot be honestly
attached to a single canonical spec node, such as review-feedback records that
do not mention an `SG-SPEC-####` id. Those events remain available through
`viewer_projection.event_type` and `viewer_projection.named_filters`.

Expected entry:

```json
{
  "event_id": "spec_activity::abc123",
  "event_type": "trace_baseline_attached",
  "spec_id": "SG-SPEC-0026",
  "title": "SpecGraph - Reflective Mechanics Integration",
  "occurred_at": "2026-05-07T21:00:00+00:00",
  "summary": "Attach SG-SPEC-0026 trace baseline",
  "source_kind": "git_commit",
  "source_ref": {
    "sha": "abcdef...",
    "short_sha": "abcdef1",
    "subject": "Attach SG-SPEC-0026 trace baseline"
  },
  "source_paths": [
    "tools/spec_trace_registry.json",
    "tools/runtime_evidence_registry.json"
  ],
  "viewer": {
    "tone": "trace",
    "label": "trace baseline attached"
  }
}
```

## 5. Event Types

Initial event vocabulary:

- `canonical_spec_updated`
- `trace_baseline_attached`
- `evidence_baseline_attached`
- `proposal_emitted`
- `implementation_work_emitted`
- `review_feedback_applied`
- `stack_only_merge_observed`

Viewer tone guidance:

- `canonical_spec_updated` -> existing node/spec accent
- `trace_baseline_attached` -> trace/evidence accent
- `evidence_baseline_attached` -> trace/evidence accent
- `proposal_emitted` -> proposal accent
- `implementation_work_emitted` -> implementation/work accent
- `review_feedback_applied` -> process/review accent
- `stack_only_merge_observed` -> process/review accent

`stack_only_merge_observed` is a graph-level process warning: the commit was
reachable from a remote stacked branch but not yet from `origin/main` when the
feed was generated. Treat it as delivery-topology evidence, not as a canonical
spec mutation.

Unknown future event types should be displayed as neutral activity rows rather
than treated as parse failures.

## 6. Viewer Integration Guidance

Once this artifact exists, ContextBuilder can add a third source toggle such as
`Activity` next to the existing node-update and run-update sources.

Recommended behavior:

- default to `Activity` when the feed is present;
- keep existing YAML/recent-run modes as narrower diagnostic views;
- use `viewer_projection.spec_id` to attach recent events to node detail panels;
- use `viewer_projection.event_type` for filters and legend counts;
- show `generated_at` or file `mtime` so stale feeds are visible.

The current inline notice in ContextBuilder can be removed once the Activity
source is available and selected by default.
