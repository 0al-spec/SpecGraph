# SpecSpace Handoff Contract Stabilization

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded runtime slice after `0066` and `0067`
materialized the producer artifacts needed by the SpecSpace handoff contract.

Source draft:

- `docs/archive/proposal_sources/0068_specspace_handoff_contract_stabilization.md`

## Context

Proposal `0065` added SpecSpace to the existing external consumer handoff plane
and intentionally kept its producer artifact contract in `draft` state. That
prevented SpecSpace UI work from starting before the producer surfaces existed.

The required producer artifacts now exist:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
runs/agent_verification_gap_index.json
```

`0066` materialized the executor adapter index. `0067` materialized the
Agent Passport derived surfaces. The remaining gap is to make the SpecSpace
handoff contract itself stable so the external consumer packet becomes ready.

## Problem

The SpecSpace external consumer bridge is ready, and the producer artifacts have
stable report-only shapes, but `tools/external_consumers.json` still marks the
SpecSpace producer artifact contract as:

```text
status: draft
```

As a result, `runs/external_consumer_handoff_packets.json` continues to emit:

```text
handoff_status: blocked_by_bridge_gap
next_gap: stabilize_specspace_handoff_contract
```

That is now stale coordination state. It correctly blocked SpecSpace before
`0056/0059` producer surfaces existed, but it should no longer block the
handoff once those artifacts are stable.

## Goals

- Stabilize the SpecSpace producer artifact contract in
  `tools/external_consumers.json`.
- Keep the handoff on the existing `external_consumer_handoff_packets` plane.
- Preserve source lineage to `0056` and `0059`.
- Preserve the no-local-path and no-raw-log privacy boundary.
- Add regression coverage that the registry-level SpecSpace handoff emits
  `ready_for_handoff` when the bridge is ready.
- Keep SpecSpace UI implementation out of scope.

## Non-Goals

- Implementing SpecSpace UI panels or routes.
- Ingesting cross-repository evidence.
- Changing Platform packaging or deployment.
- Expanding Agent Passport verification or enforcement.
- Running executor smoke benchmarks.
- Publishing local `runs/*` artifacts as tracked files.

## Runtime Semantics

The stabilized handoff contract remains report-only. It declares that SpecSpace
can consume these producer artifact paths:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
runs/agent_verification_gap_index.json
```

The stable fields are intentionally bounded to the shared artifact envelope and
the collection fields needed by SpecSpace:

```text
artifact_kind
schema_version
summary
entries
surfaces
gaps
```

When the SpecSpace bridge state is `stable_ready`, the handoff packet should
emit:

```text
handoff_status: ready_for_handoff
review_state: ready_for_review
next_gap: review_handoff_packet
```

If the local bridge becomes unavailable or identity-unverified, the existing
bridge-derived gap still wins. Contract stabilization does not hide checkout or
identity blockers.

## Validation

This proposal is complete when:

- `make external-handoffs` emits the SpecSpace packet as ready when the bridge
  is ready;
- focused external handoff tests cover the registry-level stable SpecSpace
  contract;
- proposal tracking and work-claim gates pass;
- the full test suite passes.

