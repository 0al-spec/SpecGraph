# Metric Pack Plugin Architecture

## Status

Draft proposal

## Context

SpecGraph already has the foundations needed for metric-driven observability:

- graph nodes and typed edges;
- trace and evidence planes;
- implementation work and review-feedback surfaces;
- runtime events and dashboard/backlog projections;
- an external-consumer bridge to `Metrics/SIB` and `Metrics/SIB_FULL`;
- Metrics-facing handoff and delivery artifacts.

The sibling `Metrics` repository is also evolving beyond one compact SIB paper.
It now contains multiple metric methods:

- `SIB` as a compact baseline;
- `SIB_FULL` as a broader draft diagnostic framework;
- `SIB_ECONOMIC_OBSERVABILITY` as a pricing/cost lens;
- future metric families such as trace health, review fatigue, security, or
  product-value overlays.

SpecGraph should not hard-code any one metric family as the single truth.
Instead, it should treat metrics as read-only interpretive plugins over stable
SpecGraph core state.

## Problem

The current bridge model can make external metric references visible, but it
does not yet define a general plugin architecture for metric methods.

Without that architecture:

- `SIB` can become implicitly privileged as the only operational metric family;
- draft papers such as `SIB_FULL` can be mistaken for policy or scoring
  authority;
- cost-oriented methods can be confused with direct policy targets;
- dashboard overlays have no uniform way to show metric provenance, gaps, or
  authority state;
- metric-derived pressure can blur into enforcement instead of remaining
  proposal-first;
- source material from conversation archives can be useful context but has no
  explicit curation boundary before becoming canonical graph intent.

The missing concept is a governed **metric pack**: a declared method source plus
an input contract, adapter boundary, run artifact, and projection contract.

## Goals

- Introduce metric packs as plugin-style, read-only interpreters over SpecGraph
  core artifacts.
- Keep SpecGraph core state stable and metric-family agnostic.
- Distinguish metric source, metric contract, adapter, run artifact, and viewer
  projection.
- Reuse existing Metrics bridge and source-promotion authority vocabulary instead
  of creating a parallel authority system.
- Let metric packs produce findings, gaps, overlays, and proposal pressure
  without directly mutating canonical graph state.
- Make provenance and computability explicit for every metric run.
- Support conversation archives as optional research/source material without
  hard-coding PageIndex as an architectural dependency.
- Keep future value-weighted and graph-native defect-root metrics possible
  without forcing them into the first runtime slice.

## Non-Goals

- Making `Metrics` a Git submodule.
- Treating any draft paper as immediate operational scoring authority.
- Letting metric packs auto-enforce graph policy.
- Auto-promoting conversation excerpts into canonical intents or specs.
- Replacing the existing external-consumer registry in one step.
- Requiring PageIndex as the only conversation archive implementation.
- Computing all SIB_FULL or economic metrics in the first implementation slice.

## Core Proposal

SpecGraph should introduce a **Metric Pack Plugin Architecture**.

The architecture has five layers.

### 1. Metric Source

A metric source records where the method came from.

Examples:

- `0al-spec/Metrics:SIB`
- `0al-spec/Metrics:SIB_FULL`
- `0al-spec/Metrics:SIB_ECONOMIC_OBSERVABILITY`
- a future SpecPM package;
- a local paper draft;
- a tracked proposal, spec, or source document derived from a curated
  conversation-archive excerpt.

The source is provenance, not authority by itself.

### 2. Metric Pack Contract

A metric pack contract is a machine-readable declaration of:

- `metric_pack_id`
- `reference_state`
- `pack_authority_state`
- source provenance
- required inputs
- declared metrics
- output categories
- computability states
- calibration profile requirements
- dashboard/projection hints

Example shape:

```json
{
  "metric_pack_id": "sib_full",
  "source": {
    "consumer_id": "metrics_sib_full",
    "repository": "0al-spec/Metrics",
    "path": "SIB_FULL/sib_full_metrics.tex"
  },
  "reference_state": "draft_reference",
  "pack_authority_state": "not_threshold_authority",
  "inputs": [
    "spec_graph",
    "trace_plane",
    "implementation_work",
    "review_feedback"
  ],
  "metrics": [
    {
      "metric_id": "sib_eff_star",
      "label": "Effective Pre-Implementation SIB",
      "kind": "diagnostic",
      "phase": "pre_implementation",
      "requires": [
        "intent_atoms",
        "spec_verifiability_coverage",
        "expected_implementation_potential"
      ]
    }
  ]
}
```

### 3. Metric Adapter

A metric adapter maps SpecGraph artifacts into the metric pack input contract.

The adapter boundary is important because metric definitions may use terms such
as `intent_atoms`, `expected_implementation_potential`, `pricing_surface`, or
`defect_root`. SpecGraph should not pretend these exist operationally until an
adapter can either compute them or report them as gaps.

Adapters should be allowed to emit:

- computed input bindings;
- missing input gaps;
- stale input gaps;
- invalid contract gaps;
- authority-state warnings.

### 4. Metric Run Artifact

A metric run artifact captures one concrete computation attempt against one
input snapshot.

Future metric-execution shape:

```json
{
  "artifact_kind": "metric_pack_run",
  "schema_version": 1,
  "metric_pack_id": "sib_full",
  "run_id": "metric_run::sib_full::2026-04-30T20:00:00Z",
  "generated_at": "2026-04-30T20:00:00Z",
  "input_snapshot": "specgraph-main@example",
  "source_snapshot": {
    "registry_hash": "sha256:...",
    "source_git_commit": "..."
  },
  "reference_state": "draft_reference",
  "pack_authority_state": "not_threshold_authority",
  "review_state": "draft_visible",
  "next_gap": "review_draft_metric_source",
  "values": [],
  "gaps": [
    {
      "metric_id": "sib_eff_star",
      "status": "not_computable",
      "missing_inputs": ["intent_atoms"]
    }
  ],
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

Runtime output paths for future metric execution should be declared outside the
run payload, such as in derived-artifact policy or supervisor build
configuration. The run payload itself must keep the standard read-only boundary
flags.

Initial computability states:

- `computed`
- `not_computable`
- `stale_input`
- `invalid_input`
- `draft_only`
- `blocked_by_authority_state`

### 5. Metric Projection

A metric projection is the viewer/dashboard-facing surface.

It should display:

- pack identity and authority state;
- values and confidence/provenance;
- missing inputs and next gaps;
- cost provenance when economic metrics are present;
- whether each quantity is observed spend or a derived proxy;
- whether findings are proposal pressure only.

Projection must not turn a draft pack into policy.

## Authority States

Metric packs must not introduce a parallel authority system.

They should reuse the existing bridge and source-promotion vocabulary:

`reference_state` is the same field used by `tools/external_consumers.json`.
Metric pack declarations should reference or mirror that field rather than
introduce a separate `source_reference_state` alias.

| Layer | Field | Values | Meaning |
| --- | --- | --- | --- |
| External source availability | `reference_state` | `draft_reference`, `stable_reference` | Existing external-consumer source state from `tools/external_consumers.json`. |
| Metric pack authority | `pack_authority_state` | `not_threshold_authority`, `promotion_candidate`, `operational_source_after_review` | Existing Metrics source-promotion authority state. |
| Lifecycle compatibility | `lifecycle_state` | `active`, `deprecated` | Compatibility marker only; not threshold authority. |

The important boundary is:

- `draft_reference` sources are visible as reference material only.
- `stable_reference` sources may anchor bridge-backed metrics, but do not become
  threshold authority by source availability alone.
- `promotion_candidate` means human review is required before stronger use.
- `operational_source_after_review` means the source has passed the existing
  Metrics source-promotion path, not that it may enforce policy by itself.

Threshold authority remains controlled by existing metric signal and source
promotion policies. A metric pack label alone must never alter thresholds,
backlog priority, proposal queues, or enforcement behavior.

Any transition from draft visibility to threshold-affecting behavior requires:

- stable-family anchoring where the source-promotion policy requires it;
- human review;
- a promotion artifact such as `runs/metrics_source_promotion_index.json`;
- a separate policy proposal before enforcement or threshold semantics change.

## Interpretation Contract

Metric packs should share these interpretation rules.

### Intended Use

Metrics are diagnostic observability signals. They are for drift analysis,
anomaly detection, graph self-diagnosis, economic transparency, and forecasting.

They are not people or team ranking mechanisms.

Absolute values are secondary. Deltas, drift velocity, distribution shifts, and
trend reversals are the primary interpretation mode.

### Agent-Centric Measurement

The primary measurement subject is the agentic workflow and graph process:

- attempts;
- rollbacks;
- failed runs;
- token and tool footprint;
- stabilization time;
- graph impact radius;
- review feedback loops.

This reduces Goodhart pressure compared with people-oriented productivity
metrics, but dashboard copy should still state that these are diagnostic
signals, not performance targets.

### Versioned Cost Provenance

Economic metrics must preserve:

- pricing surface identifier;
- model and provider versions;
- tool versions;
- currency or unit convention;
- time window;
- whether a quantity is observed spend or derived proxy.

This allows transparent cost accounting without confusing provider-price drift
with structural project drift.

### Calibration Profiles

Weights such as `alpha`, `beta`, `gamma`, `delta`, `lambda`, and `kappa` are
calibration parameters, not universal constants.

Metric packs should prefer named calibration profiles such as:

- `default`
- `conservative`
- `cost_sensitive`
- `latency_sensitive`

Future empirical work may define reference coefficients for recurring project
classes.

### Value-Weighted Intent Future Layer

Intent value is a future layer.

Once product telemetry connects intent atoms to shipped features and
user-visible outcomes, metric packs may add value-weighted variants such as:

- value-weighted SIB;
- value-weighted false progress mass;
- value-weighted review pressure.

Until that telemetry exists, value should not be guessed into core formulas.

### Graph-Based Defect Roots

Linear defect trajectories are acceptable as an MVP projection, especially when
changes land through a main-branch sequence.

SpecGraph should eventually support graph-native retrospective analysis:

- multiple root nodes;
- weighted influence paths;
- premise paths;
- branch contribution.

Defect-root metric contracts should remain compatible with both linear and
multi-root graph interpretations.

## Conversation Archive Source Boundary

Conversation archives can be valuable research memory.

They may contain:

- original rationale;
- candidate metric definitions;
- critique and counterarguments;
- source lineage for intents or proposals;
- discarded alternatives.

However, the architecture should not require PageIndex specifically.

Instead, SpecGraph should define an abstract `conversation_archive_source`.
PageIndex may be the first local implementation, but another indexed archive,
compiled markdown export, or future exploration-memory backend should also be
valid.

Suggested source fields:

- `source_type: conversation_archive`
- `backend: pageindex | compiled_markdown | other`
- `source_path`
- `conversation_id`
- `message_id`
- `curation_state`
- `derived_from`

Suggested curation states:

- `raw`
- `candidate`
- `reviewed`
- `accepted_as_rationale`
- `rejected`

Archive material must not become canonical metric authority by itself. It can
support rationale and lineage, but it cannot populate declared metrics or metric
pack contracts until converted into a tracked proposal, spec, source document, or
metric-pack declaration through an explicit review/curation step.

## Derived Artifacts

First runtime slices should use compact artifacts rather than a full plugin
runtime.

Metric-pack artifacts should extend, not duplicate, the existing external
consumer registry.

`tools/external_consumers.json` remains the source-availability bridge:

- repository identity;
- optional local checkout hints;
- declared external artifacts;
- `stable_reference` and `draft_reference` source state.

The metric pack registry should reference existing `consumer_id` values where
possible and add method-level declarations only:

- metric IDs;
- required SpecGraph inputs;
- adapter availability;
- authority state from the source-promotion vocabulary;
- projection hints.

Required tracked declaration:

```text
tools/metric_pack_registry.json
```

Required first derived surface:

```text
runs/metric_pack_index.json
```

`runs/metric_pack_runs.json` is a later metric-execution surface and is out of
scope for the first implementation slice.

### Input Contract

The first index builder should read:

- `tools/metric_pack_registry.json`
- `tools/external_consumers.json`
- external-consumer bridge/index artifacts when present
- existing metric signal/source-promotion policies

It should not read conversation archives in the first slice.

### Output Contract

The first index should include:

```json
{
  "artifact_kind": "metric_pack_index",
  "schema_version": 1,
  "generated_at": "...",
  "review_state": "not_ready",
  "next_gap": "review_metric_pack_contracts",
  "source_snapshot": {
    "registry_hash": "sha256:...",
    "external_consumers_hash": "sha256:..."
  },
  "summary": {
    "pack_count": 0,
    "status_counts": {},
    "authority_state_counts": {},
    "missing_input_counts": {}
  },
  "entries": [],
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

Each `entries[]` item should report:

- declared packs;
- source availability;
- authority state;
- adapter availability;
- computability summary;
- missing input counts;
- proposal-pressure counts;
- viewer projection hints.

### Status Mapping

Initial pack statuses:

- `ready_for_index_review`
- `draft_visible_only`
- `missing_external_consumer`
- `missing_source_artifact`
- `invalid_pack_contract`
- `adapter_missing`
- `blocked_by_authority_state`

Initial `next_gap` mapping:

- `ready_for_index_review` -> `review_metric_pack_index`
- `draft_visible_only` -> `review_draft_metric_pack`
- `missing_external_consumer` -> `declare_external_consumer`
- `missing_source_artifact` -> `repair_metric_source_reference`
- `invalid_pack_contract` -> `repair_metric_pack_contract`
- `adapter_missing` -> `add_metric_pack_adapter`
- `blocked_by_authority_state` -> `review_metric_source_promotion`

### Mutation Boundary

The builder must not mutate:

- `specs/nodes/*.yaml`
- `proposal_lane/nodes/*.json`
- `intent_layer/nodes/*.json`
- external repositories
- conversation archives
- threshold policies

The only allowed runtime write in the first slice is:

```text
runs/metric_pack_index.json
```

### Validation Failures

Invalid contracts should become structured index entries, not crashes.

Validation failures include:

- missing `metric_pack_id`
- unknown `consumer_id`
- unknown `reference_state`
- unknown `pack_authority_state`
- draft source declaring threshold authority
- missing required input declarations
- invalid conversation archive source promoted without tracked curation

## First Implementation Slice

The first bounded runtime slice should avoid full metric execution and viewer
dashboard changes.

It should:

1. Add a declarative metric pack registry.
2. Register only metadata for `sib`, `sib_full`, and
   `sib_economic_observability`.
3. Reference existing external-consumer IDs where possible.
4. Preserve `sib_full` as `draft_reference` and
   `not_threshold_authority`.
5. Preserve economic observability as a separate lens, not a replacement for
   SIB.
6. Add `runs/metric_pack_index.json` that validates pack metadata and reports
   gaps.

Dashboard projection, metric execution, pricing real inference events,
conversation archive ingestion, and graph-native defect roots should remain
follow-up work.

## Viewer Guidance

A viewer should show metric packs as lenses:

- pack cards grouped by authority state;
- source/provenance chips;
- computability badges;
- gaps and missing inputs;
- observed-spend versus derived-proxy labels for economic values;
- proposal-pressure badges that are visually distinct from policy.

Draft packs should be visibly marked as draft/reference-only.

## Acceptance Criteria

- SpecGraph has a proposal-level architecture for metric packs as plugins.
- Draft metric sources cannot be confused with operational policy.
- Metric findings are explicitly proposal pressure, not canonical mutation.
- Metric pack authority vocabulary is aligned with existing external-consumer
  and Metrics source-promotion policies.
- The first runtime slice is limited to a registry and read-only index.
- Conversation archives are available as optional source memory, not required
  infrastructure.
- PageIndex is named only as one possible backend, not as a hard dependency.
- Cost metrics preserve pricing and execution provenance.
- Future value-weighted and graph-native defect-root metrics have a clear
  extension path.
