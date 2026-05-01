# Metric Pack Runtime Followups

## Status

Draft follow-up proposal

## Context

Proposal `0043_metric_pack_plugin_architecture.md` defined the metric-pack
plugin architecture and named the first bounded runtime slice:

- declarative metric-pack registry;
- read-only metric-pack index;
- source/authority/computability visibility;
- viewer-facing projection without metric execution.

That first slice has now been realized through five small PR layers:

| Layer | Runtime Result |
| --- | --- |
| Registry contract | `tools/metric_pack_registry.json` declares `sib`, `sib_full`, and `sib_economic_observability`. |
| Index builder | `--build-metric-pack-index` writes `runs/metric_pack_index.json`. |
| Shortcut/docs | `make metric-packs` and tools documentation expose the routine build path. |
| Viewer surfaces | `make viewer-surfaces` writes `metric_pack_index` and includes metric-pack counts in dashboard/backlog surfaces. |
| Viewer contract | `docs/metric_pack_viewer_contract.md` defines the ContextBuilder-facing JSON contract. |

The implemented slice is intentionally read-only. It does not execute metric
packs, does not promote draft sources, and does not turn metric findings into
policy.

## Problem

After the first slice, the graph needs an explicit follow-up surface so the next
steps are derived from SpecGraph state instead of remembered from discussion
history.

Without this proposal:

- the completed `0043` runtime slice may be rediscovered repeatedly;
- follow-up work such as adapter contracts and metric run artifacts may blur
  into dashboard-only improvements;
- Metrics repository drift against `METRIC_PACKS.md` may stay implicit;
- economic observability could be shown without the pricing provenance required
  by `0043`;
- future metric-pack findings could accidentally bypass proposal-first review.

## Realized Boundary

The current realized boundary is:

```text
tools/metric_pack_registry.json
        |
        v
tools/supervisor.py --build-metric-pack-index
        |
        v
runs/metric_pack_index.json
        |
        +--> runs/graph_dashboard.json
        +--> runs/graph_backlog_projection.json
```

Documented by the static viewer contract:

```text
docs/metric_pack_viewer_contract.md
```

This boundary is complete enough for viewer observation:

- pack identity;
- source path;
- external consumer availability;
- source artifact status;
- reference state;
- pack authority state;
- review state;
- next gap;
- missing inputs;
- dashboard counts;
- backlog entries.

It is not complete enough for metric computation.

## Goals

- Record that the `0043` first runtime slice is realized.
- Keep metric-pack runtime follow-ups explicit and ordered.
- Preserve the read-only boundary until adapter and run-artifact contracts exist.
- Define drift checks against the Metrics repository source contract.
- Ensure metric findings become proposal pressure, not direct policy.
- Keep economic observability tied to versioned pricing provenance.

## Non-Goals

- Rewriting `0043`.
- Executing any metric pack in this proposal.
- Promoting `sib_full` or `sib_economic_observability` to threshold authority.
- Adding frontend code to ContextBuilder.
- Making Metrics a submodule.
- Treating `METRIC_PACKS.md` as policy authority inside SpecGraph.

## Follow-Up Work

### 1. Metrics Registry Drift Observation

SpecGraph should compare `tools/metric_pack_registry.json` against the sibling
Metrics repository contract:

```text
<metrics_repo>/METRIC_PACKS.md
```

The Metrics repository checkout path must come from runtime configuration such as
the external consumer registry or a local development override. This proposal does
not assume a developer-specific absolute filesystem path.

The first drift artifact should report:

- pack IDs declared by Metrics but missing in SpecGraph;
- pack IDs declared by SpecGraph but missing in Metrics;
- source path mismatches;
- source authority wording changes;
- missing local checkout;
- invalid or unreadable source documents.

This should remain an observation artifact, not an automatic registry rewrite.

Candidate artifact:

```text
runs/metric_pack_registry_drift.json
```

This first follow-up is now represented as a read-only runtime surface:

```text
tools/supervisor.py --build-metric-pack-registry-drift
make metric-pack-drift
```

The artifact reports drift without editing either `tools/metric_pack_registry.json`
or the sibling Metrics `METRIC_PACKS.md` contract.

### 2. Adapter Contract Layer

Metric packs currently expose required inputs but do not define how SpecGraph
maps its artifacts into those inputs.

The next contract should define adapter records such as:

```json
{
  "metric_pack_id": "sib_full",
  "adapter_status": "missing",
  "inputs": [
    {
      "input_id": "intent_atoms",
      "source_artifact": "",
      "computability": "not_computable",
      "next_gap": "define_intent_atom_extraction"
    }
  ]
}
```

The important boundary is that a missing adapter is not a runtime failure. It is
a computability gap.

Candidate artifact:

```text
runs/metric_pack_adapter_index.json
```

This follow-up is now represented as a read-only adapter/computability surface:

```text
tools/supervisor.py --build-metric-pack-adapter-index
make metric-pack-adapters
```

The artifact maps known inputs to existing SpecGraph source artifacts and
reports unknown or immature inputs as `not_computable` backlog items. It does
not execute packs.

### 3. Metric Run Artifact

Once at least one adapter can compute inputs, SpecGraph may add a run artifact.

Candidate artifact:

```text
runs/metric_pack_runs.json
```

The run artifact should preserve:

- `metric_pack_id`;
- run ID;
- input snapshot;
- source snapshot;
- adapter version;
- computed values;
- gaps;
- provenance;
- `canonical_mutations_allowed: false`;
- `tracked_artifacts_written: false`.

Metric run artifacts are derived evidence, not canonical graph state.

The first baseline run surface is now represented as a read-only runtime
snapshot:

```text
tools/supervisor.py --build-metric-pack-runs
make metric-pack-runs
```

This computes only values that can be sourced from existing SpecGraph metric
signals, leaves missing adapters as `not_computable` gaps, and keeps
finding/proposal projection deferred.

### 4. Economic Pricing Provenance

Economic observability must not show cost-like numbers without a pricing
surface.

Before computing economic pack values, SpecGraph needs a pricing provenance
contract:

- provider/model/tool identity;
- unit convention;
- currency or internal proxy unit;
- pricing version;
- time window;
- observed spend versus derived proxy;
- missing-price behavior.

This keeps provider-price drift separate from structural project drift.

This follow-up is now represented as a read-only provenance surface:

```text
tools/supervisor.py --build-metric-pricing-provenance
make metric-pricing
```

The artifact makes `pricing_surface` an explicit adapter input while keeping
observed spend, model usage, node scope, and verification-run adapters as
separate follow-up gaps before economic metric values can become computable.

### 5. Proposal Pressure From Pack Findings

Metric-pack findings may eventually feed the proposal lane, but only through a
reviewable artifact.

The correct path is:

```text
metric_pack_run
  -> metric_pack_finding_index
  -> proposal pressure
  -> human review
  -> policy/spec/runtime change
```

No metric-pack result should directly mutate thresholds, backlog priority,
canonical specs, or enforcement behavior.

### 6. Viewer Evolution

ContextBuilder can now implement the documented first viewer slice:

- "Metric Packs" dashboard section;
- "Browse packs" overlay;
- status, authority, source, and next-gap chips;
- guardrail note that packs are diagnostic lenses;
- backlog overlay grouping by `source_artifact: metric_pack_index`.

The viewer should not add edit, promote, or run buttons until the corresponding
SpecGraph artifacts exist.

## Suggested Ordering

Recommended next PR sequence:

1. `metric_pack_registry_drift.json`
2. adapter contract and adapter index
3. first non-computable adapter report for `sib_full`
4. `metric_pack_runs.json` for one computable baseline pack
5. pricing provenance contract for economic observability
6. proposal-pressure artifact from metric-pack findings

This ordering keeps observation before execution and execution before proposal
pressure.

## Acceptance Criteria

- The graph has a proposal-level record that `0043` first runtime slice is
  realized.
- Remaining metric-pack work is represented as explicit follow-up surfaces.
- `METRIC_PACKS.md` drift is recognized as observation work, not auto-sync.
- Adapter gaps are treated as computability gaps, not runtime failures.
- Economic metrics require pricing provenance before cost-like values are
  shown.
- Metric-pack findings remain proposal-first and non-authoritative by default.
- ContextBuilder can implement the current viewer slice without needing hidden
  conversation context.
