# 0025 Metrics Bridge Overlays and Backlog Pressure

Status: Draft proposal

## Problem

`0024` introduced the first external-consumer bridge to the sibling
`Metrics` repository, but the resulting surface is still too low-level for
operators and viewers.

Today we can inspect:

- the raw external consumer registry
- the raw external consumer index
- the bridge-backed effect on `sib_proxy`

What is still missing is a reviewable projection that answers:

- which sibling consumer contracts are ready
- which ones are blocked by missing checkout or wrong repo identity
- which ones are partial because declared artifacts drifted
- which draft references are visible but not yet operational
- what the next bounded remediation gap is for each consumer

Without that layer, bridge pressure remains implicit inside metric behavior.

## Why This Matters

SpecGraph now has multiple derived planes:

- graph health
- proposal lane
- implementation trace
- evidence plane
- metric signals
- graph dashboard

The external-consumer bridge should participate in that same review surface.
Otherwise sibling-consumer readiness stays hidden behind `sib_proxy` and
cannot be inspected as its own evolving contract.

## Goals

- Add a first-class external-consumer overlay derived from the external
  consumer index and metric signal index.
- Surface bridge state separately from canonical graph truth.
- Emit bounded backlog pressure such as:
  - missing local checkout
  - unverified repository identity
  - partial declared artifact contract
  - visible draft reference follow-up
- Feed the overlay into the graph dashboard so the visualizer can show
  sibling-consumer numbers directly.

## Non-Goals

- Defining a full SpecGraph-to-Metrics handoff artifact.
- Letting external consumer overlays mutate canonical specs or policy.
- Making `SIB_FULL` threshold-authoritative.
- Replacing `sib_proxy` with a fully new metric family in the same change.

## Core Proposal

Introduce a derived artifact:

- `runs/external_consumer_overlay.json`

This overlay should:

- group entries by bridge state
- group entries by bound metric status
- expose viewer-friendly named filters
- emit `next_gap` backlog items per consumer

Example backlog gaps:

- `attach_local_checkout`
- `verify_repo_identity`
- `repair_artifact_markers`
- `restore_required_artifacts`
- `review_draft_reference`

The overlay should treat stable and draft references differently:

- `Metrics/SIB` remains the stable threshold-driving bridge
- `Metrics/SIB_FULL` remains visible as draft/extended input only

## Dashboard Implication

The graph dashboard should gain a dedicated external-consumer section, rather
than forcing sibling-consumer state to be inferred indirectly from
`metric_signal_index` alone.

That section should at minimum show:

- entry count
- ready stable bridge count
- bridge-state distribution
- bound metric pressure distribution
- external-consumer backlog size

## Adoption Order

1. Add the external-consumer overlay artifact and policy.
2. Add dashboard aggregation for the new overlay.
3. Use that surface as the operator-facing basis for later
   `SpecGraph -> Metrics` handoff artifacts.
