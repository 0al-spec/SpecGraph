# Metrics And Visualization Guide

This guide is for consumers that need a compact, machine-readable view of
SpecGraph state for dashboards, badges, graph coloring, or external
visualizers.

For the dedicated `SpecPM` package-export/import viewer contract, see
[specpm_viewer_contract.md](./specpm_viewer_contract.md).

The important boundary is:

- canonical specs stay in `specs/nodes/*.yaml`
- metrics, overlays, trends, trace, evidence, and sibling-consumer state stay
  in derived JSON artifacts under `runs/`

Use the derived artifacts as read models. Do not scrape canonical YAML for UI
state that the supervisor already computes.

## 1. Recommended Artifact Stack

Use these artifacts in layers.

### Global summary

Build:

```bash
python3 tools/supervisor.py --build-graph-dashboard
```

Read:

- `runs/graph_dashboard.json`

Use this for:

- top-line cards
- sidebar counts
- filter badges
- high-level health and progress numbers

Most visualizers can treat `graph_dashboard.json` as the default compact report.

The key surfaces are:

- `headline_cards`: ready-to-render summary cards
- `sections`: grouped counts for `graph`, `health`, `proposals`,
  `implementation`, `evidence`, `external_consumers`, and `metrics`
- `viewer_projection.named_filters`: compact filter counts for UI chips or
  quick toggles

`graph_dashboard.json` now also carries downstream `SpecPM` feedback counts in:

- `sections.external_consumers.specpm_feedback_status_counts`
- `sections.external_consumers.specpm_feedback_review_state_counts`
- `viewer_projection.named_filters.specpm_adoption_visible`

### Global metric panel

Build:

```bash
python3 tools/supervisor.py --build-metric-signal-index
```

Read:

- `runs/metric_signal_index.json`

Use this for:

- metric score tables
- threshold bars
- warning lists
- trend-entry links into remediation proposals

The key surfaces are:

- `metrics[]`: one object per metric with `metric_id`, `score`,
  `minimum_score`, `status`, and `threshold_gap`
- `viewer_projection.metric_status`: groupings by `healthy` and
  `below_threshold`
- `viewer_projection.named_filters`: compact metric-driven filters

### Supervisor performance panel

Build:

```bash
python3 tools/supervisor.py --build-supervisor-performance-index
python3 tools/supervisor.py --build-bootstrap-smoke-benchmark
```

Read:

- `runs/supervisor_performance_index.json`
- `runs/bootstrap_smoke_benchmark.json`

Use this for:

- throughput cards
- runtime failure monitors
- per-profile duration charts
- run-yield tables
- repeat-hotspot warnings
- bootstrap smoke status cards

The key surfaces are:

- `entries[]`: one normalized supervisor run record
- `aggregates`: counts, duration summaries, and repeat hotspots
- `batches.by_day_utc`: compact day-level trend buckets
- `viewer_projection`: grouped run ids for `runtime_status`, `yield_status`,
  `graph_impact_status`, `run_kind`, `execution_profile`, and named filters
- `bootstrap_smoke_benchmark.benchmark_status`: `not_run`, `passed`,
  `failed`, `blocked_by_runtime`, or `insufficient_data`
- `bootstrap_smoke_benchmark.criteria_results[]`: structural pass/fail checks
  for minimal-seed yield without exact text matching

### Node overlays for the graph itself

Build:

```bash
python3 tools/supervisor.py --build-graph-health-overlay
python3 tools/supervisor.py --build-spec-trace-projection
python3 tools/supervisor.py --build-evidence-plane-overlay
```

Read:

- `runs/graph_health_overlay.json`
- `runs/spec_trace_projection.json`
- `runs/evidence_plane_overlay.json`

Use these for:

- node coloring
- per-node badges
- hover tooltips
- graph-layer toggles such as health, implementation, and evidence

### Sibling-consumer bridge panels

Build:

```bash
python3 tools/supervisor.py --build-external-consumer-index
python3 tools/supervisor.py --build-external-consumer-overlay
python3 tools/supervisor.py --build-external-consumer-handoffs
```

Read:

- `runs/external_consumer_index.json`
- `runs/external_consumer_overlay.json`
- `runs/external_consumer_handoff_packets.json`
- `runs/specpm_feedback_index.json`

Use these for:

- external consumer status cards
- bridge readiness
- backlog pressure for sibling repos
- downstream handoff review queues
- downstream `SpecPM` review/adoption observation panels

This is not node-level graph data. Treat it as a separate panel or side rail.

## 2. What To Render From Each Artifact

### `graph_dashboard.json`

Best for the first screen or the top bar.

Recommended mappings:

- card strip: `headline_cards`
- section summary table: `sections.*`
- quick filters: `viewer_projection.named_filters`

Good examples of stable card ids:

- `total_specs`
- `active_specs`
- `gated_specs`
- `structural_pressure_specs`
- `retrospective_refactor_candidates`
- `proposal_lane_active`
- `verified_specs`
- `complete_evidence_chains`
- `stable_bridges_ready`
- `ready_external_handoffs`
- `specpm_adoption_visible`
- `metrics_below_threshold`

### `metric_signal_index.json`

Best for metric widgets.

Recommended mappings:

- bar chart: `metrics[].score` vs `metrics[].minimum_score`
- warning table: `metrics[]` where `status = "below_threshold"`
- metric filters: `viewer_projection.named_filters`

Notes:

- `sib_proxy` may report `derivation_mode = "bridge_backed"` or
  `derivation_mode = "bootstrap_fallback"`
- if `derivation_mode = "bridge_backed"`, the metric is using the declared
  `Metrics/SIB` bridge instead of pure internal surrogate inputs

### `graph_health_overlay.json`

Best for structural pressure on spec nodes.

Recommended mappings:

- node danger badge: `gate_state != "none"`
- node action badges: `recommended_actions`
- graph filters: `viewer_projection.named_filters`

Useful filters include:

- `gated_specs`
- `shape_pressure`
- `clustering_pressure`
- `oversized_or_atomicity_pressure`
- `retrospective_refactor_candidates`
- `handoff_boundary_pressure`
- `techspec_ready_regions`

### `spec_trace_projection.json`

Best for implementation-state and freshness overlays.

Recommended mappings:

- implementation color: `viewer_projection.implementation_state`
- freshness accent: `viewer_projection.freshness`
- implementation backlog list: `implementation_backlog`

Useful filters include:

- `implementation_in_progress`
- `missing_trace_contract`
- `verified_fresh`
- `verified_stale_spec`
- `drifted`

### `evidence_plane_overlay.json`

Best for evidence-chain visibility.

Recommended mappings:

- evidence badge: `viewer_projection.chain_status`
- stage-specific warning badge:
  - `artifact_gap`
  - `observation_gap`
  - `outcome_gap`
  - `adoption_gap`
- evidence backlog panel: `evidence_backlog`

### `external_consumer_overlay.json`

Best for bridge status and sibling backlog pressure.

Recommended mappings:

- bridge state panel: `viewer_projection.bridge_state`
- readiness chips: `viewer_projection.named_filters`
- consumer row detail: `entries[]`

Useful filters include:

- `stable_ready`
- `draft_visible`
- `metric_pressure`
- `threshold_driver_ready`
- `identity_unverified`
- `missing_checkout`

### `external_consumer_handoff_packets.json`

Best for showing whether SpecGraph is ready to emit downstream reviewable
handoffs.

Recommended mappings:

- handoff queue: `entries[]`
- review queue counts: `viewer_projection.review_state`
- handoff readiness counts: `viewer_projection.handoff_status`
- backlog grouping: `handoff_backlog.grouped_by_next_gap`

The main statuses are:

- `ready_for_handoff`
- `blocked_by_bridge_gap`
- `draft_reference_only`

## 3. Practical Visualizer Layout

If you want one compact but useful UI, this layout works well:

1. Top row from `graph_dashboard.json`
2. Left-side filters from `graph_dashboard.viewer_projection.named_filters`
3. Graph node coloring from:
   - `graph_health_overlay.json`
   - `spec_trace_projection.json`
   - `evidence_plane_overlay.json`
4. Right-side metric panel from `metric_signal_index.json`
5. Secondary runtime/performance panel from:
   - `supervisor_performance_index.json`
   - `bootstrap_smoke_benchmark.json`
6. Bottom sibling-consumer panel from:
   - `external_consumer_overlay.json`
   - `external_consumer_handoff_packets.json`

This keeps node-level and non-node-level data separate.

## 4. Minimal Node Overlay Merge Strategy

If your visualizer wants one overlay object per `spec_id`, merge the three
node-facing artifacts:

- `graph_health_overlay.json`
- `spec_trace_projection.json`
- `evidence_plane_overlay.json`

Recommended per-node shape:

```json
{
  "spec_id": "SG-SPEC-0049",
  "health": {
    "gate_state": "none",
    "recommended_actions": [],
    "filters": ["shape_pressure"]
  },
  "implementation": {
    "state": "in_progress",
    "freshness": "dirty_worktree"
  },
  "evidence": {
    "chain_status": "observation_backed"
  }
}
```

You do not need the supervisor to emit this merged form yet. It can be built in
the visualizer by joining on `spec_id`.

## 5. Compact Report Recommendation

If you need exactly one file first, use:

- `runs/graph_dashboard.json`

If you need one global file plus one node-overlay layer, use:

- `runs/graph_dashboard.json`
- `runs/graph_health_overlay.json`

If you need the full but still clean visualization stack, use:

- `runs/graph_dashboard.json`
- `runs/metric_signal_index.json`
- `runs/graph_health_overlay.json`
- `runs/spec_trace_projection.json`
- `runs/evidence_plane_overlay.json`
- `runs/external_consumer_overlay.json`
- `runs/external_consumer_handoff_packets.json`

## 6. Rebuild Commands

For a complete refresh before rendering:

```bash
python3 tools/supervisor.py --build-graph-health-overlay
python3 tools/supervisor.py --build-spec-trace-projection
python3 tools/supervisor.py --build-evidence-plane-overlay
python3 tools/supervisor.py --build-external-consumer-overlay
python3 tools/supervisor.py --build-external-consumer-handoffs
python3 tools/supervisor.py --build-metric-signal-index
python3 tools/supervisor.py --build-supervisor-performance-index
python3 tools/supervisor.py --build-graph-dashboard
```

If the UI only needs global cards and metric panels:

```bash
python3 tools/supervisor.py --build-metric-signal-index
python3 tools/supervisor.py --build-supervisor-performance-index
python3 tools/supervisor.py --build-graph-dashboard
```

## 7. Important Caveats

- Derived artifacts are read models, not canonical truth.
- `runs/` artifacts can change shape faster than canonical specs, so prefer
  `artifact_kind` and `schema_version` checks in the visualizer.
- `external_consumer_*` artifacts are not spec nodes and should not be rendered
  as canonical graph vertices unless you intentionally want a multi-layer graph.
- `sib_proxy` is still the compatibility name of the sibling-consumer metric.
  Its basis is now bridge-aware, but the identifier has not yet been renamed.
