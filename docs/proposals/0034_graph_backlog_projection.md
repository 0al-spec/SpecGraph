# Graph Backlog Projection From Derived Surfaces

Status: Draft proposal

## Problem

`tasks.md` is useful during bootstrap, but it should not remain the primary way
operators discover what SpecGraph needs next. The graph already emits derived
surfaces for health, proposal runtime, trace coverage, evidence coverage,
external consumers, SpecPM, Metrics, and metric-threshold pressure. The missing
piece is one compact projection that turns those scattered backlog counts into
concrete viewer rows.

Without that projection, dashboards can show numbers such as "missing trace
contracts" or "promotion ready", but a viewer still has to scrape individual
artifacts to build a work queue.

## Proposal

Add a derived `graph_backlog_projection` artifact:

```text
runs/graph_backlog_projection.json
```

The artifact normalizes existing derived backlog surfaces into `entries[]` with:

- `backlog_id`
- `domain`
- `source_artifact`
- `source_artifact_path`
- `subject_kind`
- `subject_id`
- `status`
- `review_state`
- `next_gap`
- `priority`
- `details`

The projection must remain derived-only. It must not mutate canonical specs,
create new proposal-lane nodes, approve downstream feedback, or turn metric
threshold pressure into policy.

## Source Surfaces

Initial sources:

- `graph_health_overlay`
- `proposal_runtime_index`
- `proposal_promotion_index`
- `refactor_queue`
- `proposal_queue`
- `spec_trace_projection`
- `evidence_plane_overlay`
- `external_consumer_overlay`
- `external_consumer_handoff_packets`
- `specpm_delivery_workflow`
- `specpm_feedback_index`
- `metrics_delivery_workflow`
- `metrics_feedback_index`
- `metrics_source_promotion_index`
- `metric_threshold_proposals`

## Viewer Contract

The viewer should use:

- `entries[]` for backlog rows
- `summary.domain_counts` for domain tabs
- `summary.priority_counts` for priority tabs
- `summary.next_gap_counts` for next-gap grouping
- `viewer_projection.named_filters` for quick filters

Useful named filters:

- `ready_for_review`
- `blocked_by_repo_state`
- `human_review_required`
- `missing_trace_contract`
- `missing_evidence_contract`
- `metric_threshold_pressure`
- `proposal_runtime_realization`
- `promotion_review_ready`

## Boundaries

- `graph_backlog_projection` is a read model, not canonical truth.
- `tasks.md` may continue to exist for historical bootstrap traceability, but
  dashboards should prefer the derived projection for current work discovery.
- Any backlog row that implies policy or authority change must still route
  through reviewable proposal or handoff artifacts.
