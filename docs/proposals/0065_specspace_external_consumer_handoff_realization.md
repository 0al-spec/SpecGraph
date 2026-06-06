# SpecSpace External Consumer Handoff Realization

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded slice of `0064 Supervisor External
Consumer Handoff Loop` for SpecSpace without moving work into deprecated
`tasks.md`.

Source draft:

- `docs/archive/proposal_sources/0065_specspace_external_consumer_handoff_realization.md`

## Context

SpecGraph already has an external consumer handoff plane:

```text
tools/external_consumers.json
tools/external_consumer_handoff_policy.json
runs/external_consumer_handoff_packets.json
make external-handoffs
```

Proposal `0064` defines the responsibility boundary: SpecGraph remains the
supervisor-centric gap finder and contract producer, while SpecSpace remains an
external UI/runtime consumer that implements product behavior and returns
evidence.

The next practical step is not a new handoff surface. It is a realization slice
that lets the existing external-consumer packet builder emit SpecSpace-oriented
handoffs from current derived inputs.

## Problem

SpecSpace-facing work can be identified by SpecGraph, but before this proposal
the existing external-consumer handoff artifact is primarily metric/SIB shaped.
That leaves the first SpecSpace handoff under-specified:

- no dedicated SpecSpace consumer profile;
- no typed producer artifact contract for agent/executor/passport visibility;
- no expected consumer behavior fields;
- no report-only evidence contract shape;
- no explicit privacy boundary preventing local-only paths or raw supervisor
  logs from leaking into handoff packets.

Without this realization slice, SpecGraph can describe the meta-plan but cannot
emit a concrete reviewable handoff packet that SpecSpace can implement against.

## Goals

- Track this work as proposal `0065`, not as a `tasks.md` item.
- Extend the existing `external_consumer_handoff_packets` plane for SpecSpace.
- Add a SpecSpace consumer category/profile and stable packet filters.
- Add producer artifact contract fields for the 0056/0059 agent/executor/passport
  visibility line.
- Add expected consumer behavior fields.
- Add a report-only evidence contract shape.
- Keep current Metrics/SIB external handoff behavior unchanged.
- Avoid local-only paths and raw supervisor logs in SpecSpace handoff packets.

## Non-Goals

- Implementing SpecSpace UI.
- Mutating SpecSpace from SpecGraph.
- Adding Platform or deployment changes.
- Implementing cross-repository evidence ingestion.
- Creating `runs/external_consumer_handoff_index.json`.
- Treating draft 0056/0059 producer artifacts as ready for handoff.

## Realization

The realization extends the existing external consumer registry and policy:

```text
tools/external_consumers.json
  -> consumer profile: graph_operator_surface_consumer
  -> consumer: specspace
  -> draft producer artifact contract for 0056/0059

tools/external_consumer_handoff_policy.json
  -> SpecSpace consumer profile mapping
  -> default artifact contract
  -> expected consumer behavior defaults
  -> evidence contract defaults
  -> privacy boundary
```

`build_external_consumer_handoff_packets()` continues to produce:

```text
runs/external_consumer_handoff_packets.json
```

For SpecSpace consumers, each packet includes:

- `consumer_category`;
- `artifact_contract`;
- `expected_consumer_behavior`;
- `evidence_contract`;
- `privacy_boundary`.

The packet becomes `ready_for_handoff` only when the external bridge is ready
and the producer artifact contract is explicitly stable. If the consumer bridge
is ready but the producer artifact contract is still draft or missing, the packet
is emitted as `blocked_by_bridge_gap` with:

```text
next_gap: stabilize_specspace_handoff_contract
```

## First Handoff Target

The first practical SpecSpace handoff targets the agent/executor/passport
visibility line:

```text
0056 Supervisor Executor Adapter Gateway
0059 Agent Passport Adoption
```

The initial producer contract is intentionally draft because the corresponding
runtime artifacts are not all stable yet:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
runs/agent_verification_gap_index.json
```

That means SpecSpace becomes visible as a handoff consumer now, while actual UI
implementation waits for stable producer artifacts.

## Evidence Contract

This proposal adds only a report-only evidence shape. It does not ingest or
validate cross-repo evidence yet.

Minimal evidence fields:

```json
{
  "artifact_kind": "external_consumer_evidence",
  "schema_version": 1,
  "handoff_id": "external_consumer_handoff::specspace",
  "consumer": "SpecSpace",
  "implementation_ref": "https://github.com/0al-spec/SpecSpace/pull/<id>",
  "consumed_artifacts": [
    "runs/agent_surface_index.json"
  ],
  "evidence": [
    {
      "kind": "test",
      "ref": "SpecSpace test or smoke command"
    }
  ],
  "result": "implemented"
}
```

Accepted result values:

- `implemented`;
- `blocked`;
- `deferred`.

## Privacy Boundary

SpecSpace handoff packets must not expose:

- machine-local checkout paths;
- raw supervisor logs;
- local-only runtime paths.

Repository-relative producer artifact paths are allowed.

## Validation

This slice is valid when:

- `make proposal-id` still allocates deterministically after `0065`;
- `proposal-tracking-gate` sees proposal `0065`;
- `proposal-work-claims-gate` remains clean;
- `make external-handoffs` writes a packet set with a SpecSpace entry;
- focused handoff tests prove both ready and draft SpecSpace contract behavior;
- existing Metrics/SIB external handoff tests remain unchanged.

