# Metric Pack Viewer Contract

## Status

Draft viewer contract for the metric-pack surfaces introduced by proposal 0043.

## Source Artifacts

ContextBuilder should treat these SpecGraph artifacts as read-only JSON
surfaces:

| Artifact | Producer | Consumer Use |
| --- | --- | --- |
| `runs/metric_pack_index.json` | `make metric-packs` or `make viewer-surfaces` | Primary metric-pack overlay and browse panel source. |
| `runs/metric_pack_registry_drift.json` | `make metric-pack-drift` or `make viewer-surfaces` | Optional drift panel comparing SpecGraph's registry with Metrics `METRIC_PACKS.md`. |
| `runs/metric_pack_adapter_index.json` | `make metric-pack-adapters` or `make viewer-surfaces` | Optional adapter/computability panel for metric-pack inputs. |
| `runs/metric_pack_runs.json` | `make metric-pack-runs` or `make viewer-surfaces` | Optional read-only run snapshot for computable pack values and gaps. |
| `runs/graph_dashboard.json` | `make dashboard` or `make viewer-surfaces` | Summary counts and headline card source. |
| `runs/graph_backlog_projection.json` | `make backlog` or `make viewer-surfaces` | Reviewable metric-pack gaps in global backlog. |

No ContextBuilder write path is implied by this contract.

## Primary Artifact

`runs/metric_pack_index.json` has this stable top-level shape:

```json
{
  "artifact_kind": "metric_pack_index",
  "schema_version": 1,
  "generated_at": "2026-04-30T23:03:06.642914+00:00",
  "review_state": "ready_for_review",
  "next_gap": "review_metric_pack_index",
  "source_snapshot": {
    "registry_path": "tools/metric_pack_registry.json",
    "registry_hash": "...",
    "external_consumer_index": {
      "artifact_path": "runs/external_consumer_index.json",
      "generated_at": "..."
    }
  },
  "summary": {
    "pack_count": 3,
    "status_counts": {},
    "authority_state_counts": {},
    "missing_input_counts": {}
  },
  "entry_count": 3,
  "entries": [],
  "viewer_projection": {},
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

`source_snapshot` and `summary` are structured metadata. Consumers may render
the documented keys above, but should treat additional nested fields as
pass-through metadata because producer-side provenance can grow over time.

Viewer guardrails:

- Render only when `artifact_kind == "metric_pack_index"`.
- Treat any missing artifact as "not built yet", not as graph failure.
- Treat `canonical_mutations_allowed !== false` or
  `tracked_artifacts_written !== false` as a boundary warning.
- Do not infer threshold authority from pack labels or source paths.

## Entry Contract

Each `entries[]` item describes one metric pack:

```json
{
  "metric_pack_id": "sib_full",
  "title": "SIB Full Metrics",
  "consumer_id": "metrics_sib_full",
  "pack_status": "draft_visible_only",
  "review_state": "draft_visible",
  "next_gap": "review_draft_metric_pack",
  "reference_state": "draft_reference",
  "consumer_reference_state": "draft_reference",
  "pack_authority_state": "not_threshold_authority",
  "lifecycle_state": "active",
  "source": {
    "repository": "0al-spec/Metrics",
    "path": "SIB_FULL/sib_full_metrics.tex",
    "compiled_path": "SIB_FULL/sib_full_metrics.pdf"
  },
  "source_availability": {
    "consumer_found": true,
    "consumer_contract_status": "ready",
    "checkout_status": "available",
    "source_artifact_status": "verified"
  },
  "adapter": {
    "status": "deferred",
    "next_gap": "add_metric_pack_adapter"
  },
  "metric_count": 2,
  "metrics": [
    {
      "metric_id": "sib_eff_star",
      "label": "Effective Pre-Implementation SIB",
      "kind": "diagnostic",
      "phase": "pre_implementation",
      "requires": [
        "intent_atoms",
        "expected_implementation_potential"
      ]
    }
  ],
  "missing_inputs": ["intent_atoms"],
  "contract_errors": [],
  "projection_hints": {
    "lens": "extended_diagnostic",
    "show_as_baseline": false
  }
}
```

`metrics[]` is a normalized list of metric declarations from the source pack.
For compact tables, prefer `metric_count`; use `metrics[]` only for detail
drawers or expanded rows. Unknown metric fields should pass through without
breaking the table.

Recommended columns for a first browse panel:

| Column | Field |
| --- | --- |
| Pack | `metric_pack_id` + `title` |
| Status | `pack_status` |
| Review | `review_state` |
| Authority | `pack_authority_state` |
| Source | `source.path` |
| Next Gap | `next_gap` |
| Missing Inputs | `missing_inputs.length` |

## Status Vocabulary

Known `pack_status` values:

- `ready_for_index_review`: source and authority state are coherent; human can
  review the index entry.
- `draft_visible_only`: draft source is visible but not threshold authority.
- `missing_external_consumer`: registry references a consumer not visible in
  `external_consumer_index`.
- `missing_source_artifact`: source path is missing or not verified in the
  sibling checkout.
- `invalid_pack_contract`: malformed metric-pack registry entry.
- `adapter_missing`: pack requires an adapter before execution.
- `blocked_by_authority_state`: source authority state requires review before
  stronger use.

Known `review_state` values:

- `ready_for_review`
- `draft_visible`
- `not_ready`

Known `pack_authority_state` values:

- `not_threshold_authority`
- `promotion_candidate`
- `operational_source_after_review`

Unknown future values should render as neutral chips and pass through raw text.

## Viewer Projection

`viewer_projection` groups pack IDs by stable dimensions:

```json
{
  "pack_status": {
    "draft_visible_only": ["sib_full"],
    "ready_for_index_review": ["sib"]
  },
  "review_state": {},
  "authority_state": {},
  "reference_state": {},
  "missing_inputs": {},
  "named_filters": {
    "ready_for_index_review": ["sib"],
    "draft_visible_only": ["sib_full"],
    "non_authoritative": ["sib_full"],
    "economic_observability": ["sib_economic_observability"],
    "needs_repair": []
  }
}
```

Use `viewer_projection` for counts and filters. Use `entries[]` for row data.
Known named filters may be present with empty arrays to keep zero-count UI
states stable. Unknown future named filters should be treated as neutral
pass-through filters, not as rendering errors.

## Registry Drift Artifact

`runs/metric_pack_registry_drift.json` is a read-only observation artifact. It
compares SpecGraph's `tools/metric_pack_registry.json` with the sibling Metrics
`METRIC_PACKS.md` contract. It is intended to surface source registry drift, not
to sync either repository automatically.

Top-level shape:

```json
{
  "artifact_kind": "metric_pack_registry_drift",
  "schema_version": 1,
  "generated_at": "...",
  "review_state": "clean",
  "next_gap": "none",
  "source_snapshot": {
    "artifact_path": "runs/metric_pack_registry_drift.json",
    "registry_path": "tools/metric_pack_registry.json",
    "registry_hash": "...",
    "source_registry": {
      "repository": "0al-spec/Metrics",
      "contract_path": "METRIC_PACKS.md",
      "checkout_status": "available",
      "repo_revision": "...",
      "contract_status": "parsed",
      "contract_error": ""
    },
    "external_consumer_index": {
      "artifact_path": "runs/external_consumer_index.json",
      "generated_at": "..."
    }
  },
  "summary": {
    "drift_count": 0,
    "status_counts": {},
    "severity_counts": {}
  },
  "entry_count": 0,
  "entries": [],
  "viewer_projection": {
    "drift_status": {},
    "severity": {},
    "named_filters": {
      "in_sync": ["0al-spec/Metrics"],
      "needs_review": []
    }
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

Known `entries[].drift_status` values:

- `missing_checkout`: the Metrics checkout is not locally observable.
- `missing_metrics_contract`: `METRIC_PACKS.md` is absent in the Metrics checkout.
- `unreadable_metrics_contract`: the contract file could not be read.
- `empty_metrics_contract`: no `metric_pack_id` rows were found in the Pack Registry table.
- `missing_in_metrics_contract`: SpecGraph declares a pack that Metrics does not list.
- `missing_in_specgraph_registry`: Metrics lists a pack that SpecGraph does not declare.
- `source_path_mismatch`: both sides list a pack, but source paths differ.
- `display_name_mismatch`: both sides list a pack, but display names differ.
- `missing_source_artifact`: Metrics lists a source path that is absent locally.

Viewer guidance:

- Render the artifact only when `artifact_kind == "metric_pack_registry_drift"`.
- Treat missing artifact as "drift not built yet".
- Treat `entry_count == 0` as green/neutral "in sync".
- Treat `severity == "high"` as review-needed, not as policy failure.
- Do not expose local checkout paths; use `repo_revision`, `contract_path`, and
  pack IDs for display.

## Adapter Index Artifact

`runs/metric_pack_adapter_index.json` is the read-only computability layer
between pack declarations and future metric execution. It maps each declared
pack input to an existing SpecGraph source artifact when possible and emits
not-computable gaps when an adapter contract is missing.

Top-level shape:

```json
{
  "artifact_kind": "metric_pack_adapter_index",
  "schema_version": 1,
  "generated_at": "...",
  "review_state": "ready_for_review",
  "next_gap": "review_metric_pack_adapter_index",
  "source_snapshot": {
    "artifact_path": "runs/metric_pack_adapter_index.json",
    "metric_pack_index": {
      "artifact_path": "runs/metric_pack_index.json",
      "generated_at": "...",
      "entry_count": 3
    },
    "input_catalog_version": 1
  },
  "summary": {
    "pack_count": 3,
    "input_binding_count": 18,
    "status_counts": {},
    "computability_counts": {},
    "missing_input_counts": {}
  },
  "entry_count": 3,
  "entries": [],
  "adapter_backlog": {
    "entry_count": 0,
    "items": [],
    "grouped_by_next_gap": {}
  },
  "viewer_projection": {},
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

Each `entries[]` item describes one pack adapter surface:

```json
{
  "metric_pack_id": "sib_full",
  "title": "SIB Full Metrics",
  "adapter_status": "missing_input_adapters",
  "review_state": "ready_for_review",
  "next_gap": "define_intent_atom_extraction",
  "input_count": 6,
  "missing_input_count": 3,
  "missing_inputs": ["expected_implementation_potential", "intent_atoms"],
  "inputs": [
    {
      "input_id": "intent_atoms",
      "computability": "not_computable",
      "source_artifact": "",
      "source_field": "",
      "required_by_metric_ids": ["sib_eff_star"],
      "required_by_pack": false,
      "next_gap": "define_intent_atom_extraction"
    }
  ],
  "adapter_execution": {
    "status": "deferred",
    "next_gap": "add_metric_pack_execution_runtime"
  }
}
```

Known `adapter_status` values:

- `ready_for_adapter_review`: all declared inputs have a current source-artifact
  mapping; execution is still deferred.
- `missing_input_adapters`: one or more declared inputs are not computable yet.
- `stale_input_adapters`: reserved for future freshness checks.
- `invalid_pack_contract`: the pack has no usable input contract.

Known `inputs[].computability` values:

- `available`: SpecGraph has a source-artifact binding for this input.
- `not_computable`: no adapter/source contract exists yet.
- `stale`: reserved for future freshness checks.

Viewer guidance:

- Use `summary.computability_counts` for compact dashboard counts.
- Use `adapter_backlog.items[]` for "what input do we need to define next?"
  overlays.
- Treat `adapter_execution.status == "deferred"` as a guardrail, not a failure.
- Do not add external execution UI; `metric_pack_runs.json` is a read-only
  snapshot, not a command surface.

## Run Snapshot Artifact

`runs/metric_pack_runs.json` is the first read-only run surface. It does not
execute external code; it projects metric-pack values that can already be
derived from existing SpecGraph metric signals and records gaps for the rest.

Top-level shape:

```json
{
  "artifact_kind": "metric_pack_runs",
  "schema_version": 1,
  "generated_at": "...",
  "review_state": "ready_for_review",
  "next_gap": "review_metric_pack_runs",
  "source_snapshot": {
    "artifact_path": "runs/metric_pack_runs.json",
    "metric_pack_index": {"artifact_path": "runs/metric_pack_index.json"},
    "metric_pack_adapter_index": {
      "artifact_path": "runs/metric_pack_adapter_index.json"
    },
    "metric_signal_index": {"artifact_path": "runs/metric_signal_index.json"}
  },
  "summary": {
    "pack_count": 3,
    "run_status_counts": {"computed": 1, "not_computable": 2},
    "computed_value_count": 1,
    "gap_count": 9
  },
  "entry_count": 3,
  "entries": [],
  "viewer_projection": {},
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

Each `entries[]` item describes one pack snapshot:

```json
{
  "run_id": "metric_pack_run::sib::latest",
  "metric_pack_id": "sib",
  "title": "SIB",
  "run_status": "computed",
  "review_state": "ready_for_review",
  "next_gap": "review_metric_pack_run_snapshot",
  "adapter_status": "ready_for_adapter_review",
  "input_snapshot": {
    "adapter_inputs": [],
    "missing_inputs": [],
    "adapter_next_gap": "review_metric_pack_adapter_index"
  },
  "computed_values": [
    {
      "metric_id": "sib",
      "value_status": "computed_from_existing_signal",
      "score": 0.82,
      "status": "healthy",
      "threshold_authority_state": "canonical_threshold_authority"
    }
  ],
  "gaps": [],
  "finding_projection": {
    "status": "deferred",
    "next_gap": "add_metric_pack_finding_index"
  },
  "threshold_authority_granted": false,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

Known `run_status` values:

- `computed`: at least one value is projected and no run gaps remain.
- `partial`: values exist, but some metric value adapters are still missing.
- `not_computable`: missing input adapters or missing value adapters prevent a
  useful run snapshot.
- `invalid_pack_contract`: the pack has no usable adapter contract.

Viewer guidance:

- Render this as "Run snapshot" or "Computed preview", not as executable
  runtime.
- Treat `finding_projection.status == "deferred"` as the guardrail that pack
  findings are not yet proposal pressure.
- Do not expose promote/apply/threshold buttons from this artifact.
- Use `computed_values[].threshold_authority_state` only as provenance; this
  artifact itself never grants authority.

## Dashboard Additions

When `runs/graph_dashboard.json` is generated by a SpecGraph version with
metric-pack support, ContextBuilder may read:

```json
{
  "source_artifacts": {
    "metric_pack_index": {
      "artifact_path": "runs/metric_pack_index.json",
      "generated_at": "..."
    },
    "metric_pack_adapter_index": {
      "artifact_path": "runs/metric_pack_adapter_index.json",
      "generated_at": "..."
    }
  },
  "sections": {
    "metrics": {
      "metric_pack_entry_count": 3,
      "metric_pack_status_counts": {},
      "metric_pack_review_state_counts": {},
      "metric_pack_authority_counts": {},
      "metric_pack_named_filter_counts": {},
      "metric_pack_adapter_entry_count": 3,
      "metric_pack_adapter_status_counts": {},
      "metric_pack_adapter_computability_counts": {},
      "metric_pack_adapter_named_filter_counts": {},
      "metric_pack_adapter_backlog_count": 0
    }
  },
  "viewer_projection": {
    "named_filters": {
      "metric_packs_review_ready": 1,
      "metric_packs_draft_visible": 2,
      "metric_pack_adapter_gaps": 0
    }
  }
}
```

Headline card:

- `card_id: "metric_packs_review_ready"`
- `section: "metrics"`
- `value`: count of `ready_for_index_review` packs
- `card_id: "metric_pack_adapter_gaps"`
- `section: "metrics"`
- `value`: count of `adapter_backlog.items[]`

## Backlog Projection Additions

`runs/graph_backlog_projection.json` may include entries where:

```json
{
  "source_artifact": "metric_pack_index",
  "domain": "metrics",
  "subject_kind": "metric_pack",
  "subject_id": "sib_full",
  "status": "draft_visible_only",
  "review_state": "draft_visible",
  "next_gap": "review_draft_metric_pack"
}
```

Adapter backlog entries use:

```json
{
  "source_artifact": "metric_pack_adapter_index",
  "domain": "metrics",
  "subject_kind": "metric_pack_input",
  "subject_id": "metric_pack_adapter::sib_full::intent_atoms",
  "status": "not_computable",
  "review_state": "ready_for_review",
  "next_gap": "define_intent_atom_extraction"
}
```

Viewer affordance:

- Show these in the existing backlog overlay under the `metrics` domain.
- Group by `next_gap` the same way as other backlog entries.
- Prefer amber/review styling for `review_*` gaps.
- `status` is populated from the metric pack's `pack_status`.
- Do not style draft packs as errors unless `status` is
  `invalid_pack_contract`, `missing_external_consumer`, or
  `missing_source_artifact`.

## Suggested UI

First useful viewer slice:

- Add a "Metric Packs" section under Graph Dashboard metrics.
- Add a "Browse packs" button when `runs/metric_pack_index.json` is present.
- Render one row per `entries[]` item.
- Add chips for `pack_status`, `pack_authority_state`, and `reference_state`.
- Add an optional "Adapter Inputs" panel when `runs/metric_pack_adapter_index.json`
  is present.
- Add a guardrail note: "Metric packs are diagnostic lenses; they do not grant
  threshold authority by themselves."

Out of scope for the first viewer slice:

- Running metric packs.
- Editing `tools/metric_pack_registry.json`.
- Promoting draft sources.
- Turning missing inputs into canonical intents automatically.
