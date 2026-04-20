# 0026 SpecGraph-to-Metrics Handoff Artifacts

Status: Draft proposal

## Problem

`0024` and `0025` established:

- a tracked external-consumer registry
- a bridge index for `Metrics/SIB` and `Metrics/SIB_FULL`
- a viewer-facing overlay with bridge readiness and backlog pressure

What is still missing is a derived handoff artifact that says:

- which sibling consumer is currently ready to receive a reviewable downstream packet
- which stable bridge is still blocked by checkout or contract gaps
- which draft reference is visible but not yet operational
- which metric pressure is being handed off, if any

Today this boundary still exists only implicitly inside:

- `sib_proxy`
- `metric_threshold_proposals`
- the external-consumer overlay backlog

There is no dedicated `SpecGraph -> Metrics` handoff artifact yet.

## Why This Matters

SpecGraph now has a meaningful sibling-consumer bridge, but no explicit packet
that carries current metric pressure and bridge readiness into a reviewable
downstream handoff surface.

Without that artifact:

- sibling-consumer integration remains observational only
- `Metrics`-facing pressure cannot be inspected as its own governed packet
- downstream work stays hidden inside dashboard numbers and threshold proposals

This should remain proposal-first and derived. It should not become direct
cross-repo mutation in the same slice.

## Goals

- Add a derived handoff artifact for external sibling consumers.
- Reuse the existing governed `handoff` transition family instead of inventing
  a parallel packet type.
- Emit reviewable handoff packets only for stable-ready external consumers.
- Keep `Metrics/SIB_FULL` visible as draft-only input, not threshold-driving
  or handoff-authoritative.
- Surface handoff readiness and next gaps in viewer/report form.

## Non-Goals

- Creating cross-repo pull requests into `Metrics`.
- Making `SIB_FULL` operational threshold authority.
- Adding a brand-new transition family.
- Letting handoff packets mutate canonical SpecGraph state or policy.

## Core Proposal

Introduce a derived artifact:

- `runs/external_consumer_handoff_packets.json`

Each entry should describe one external consumer and classify it into one of:

- `ready_for_handoff`
- `blocked_by_bridge_gap`
- `draft_reference_only`

For `ready_for_handoff` consumers, the artifact should include a normalized
transition packet that reuses:

- `packet_type: handoff`
- an existing validator profile
- a bounded source/provenance contract

The first target is `Metrics/SIB`:

- it is the stable reviewable sibling-consumer bridge
- it may receive bridge-backed handoff packets
- its packet may carry threshold pressure for `sib_proxy`

`Metrics/SIB_FULL` should still appear in the artifact, but only as:

- `draft_reference_only`
- a visible next-gap reminder
- non-authoritative supplemental context

## Viewer Implication

The graph dashboard should incorporate this new handoff layer so the visualizer
can distinguish:

- stable bridges that are merely ready
- bridges that now have a reviewable handoff packet
- draft references that are visible but not operational

## Adoption Order

1. Add a declarative handoff policy for external consumers.
2. Add the derived handoff packet artifact.
3. Feed handoff counts into the graph dashboard.
4. Use that packet as the future basis for explicit `SpecGraph -> Metrics`
   delivery or cross-repo review workflows.
