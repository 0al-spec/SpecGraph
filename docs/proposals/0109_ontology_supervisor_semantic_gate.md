# Ontology Supervisor Semantic Gate

RFC: SG-RFC-0109
Version: 0.1.0

## Status

Implemented

Decision scope: deterministic supervisor gate evidence derived from the `0108`
ontology semantic review surface.

This document does not run prompt agents, write Ontology packages, update
ontology lockfiles, mutate canonical SpecGraph specs, accept candidate terms,
or wire the gate into ordinary targeted supervisor refinement.

## Source Material

This proposal implements the next bounded runtime slice after
`0108_ontology_semantic_review_surface`.

Source draft:

- `docs/archive/proposal_sources/0109_ontology_supervisor_semantic_gate.md`

## Summary

SpecGraph now emits a deterministic supervisor semantic gate artifact:

```text
runs/ontology_supervisor_semantic_gate.json
```

The gate consumes the semantic review surface and converts review evidence into
a supervisor-style gate decision:

- blocking findings produce `gate_state: blocked`;
- review-required findings or ontology delta candidates produce
  `gate_state: review_pending` when no blocker exists;
- no review items produces `gate_state: clear`.

The artifact carries source artifact refs, review item ids, required human
action, failure modes, and a typed invocation boundary. It is evidence only and
does not perform any write.

## Goals

- Add `supervisor_semantic_gate` to the semantic policy layout.
- Define a `supervisor_semantic_gate_contract` with source review surface,
  supported gate states, review-state mapping, failure modes, and consumer
  boundary.
- Build `ontology_supervisor_semantic_gate` from
  `ontology_semantic_review_surface`.
- Preserve review item ids so a supervisor or UI can route human action back to
  the source finding or candidate.
- Keep all effects non-mutating and local under `runs/`.
- Cover gate shape, write path, authority boundary, and registry trace in tests.

## Non-Goals

- Running prompt agents.
- Wiring this gate into ordinary `--target-spec` supervisor execution.
- Writing Ontology package drafts.
- Updating ontology lockfiles.
- Applying accepted terms back into canonical SpecGraph specs.
- Marking candidate terms accepted.
- Adding SpecSpace UI or mutation APIs.

## Runtime Contract

The gate declares:

```json
{
  "artifact_kind": "ontology_supervisor_semantic_gate",
  "schema_version": 1,
  "proposal_id": "0109",
  "source_artifacts": {
    "semantic_review_surface": "runs/ontology_semantic_review_surface.json"
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "gate": {
    "gate_state": "blocked",
    "required_human_action": "resolve_blocking_ontology_semantic_findings"
  }
}
```

In the checked-in fixture, the gate is blocked by the `ExamPolicy` deprecated
term and the `allows policy` relation conflict. The `CASFunction` review item
and delta candidate remain visible as review-required evidence.

## Authority Boundary

The gate may be used as supervisor semantic gate evidence.

The gate may not:

- execute prompt agents;
- write Ontology packages;
- update ontology lockfiles;
- mutate canonical specs;
- mark candidate terms accepted;
- become canonical authority for accepted terms or ontology deltas.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `supervisor_semantic_gate`;
- `tools/ontology_imports.py` builds `ontology_supervisor_semantic_gate` from
  the semantic review surface;
- `make ontology-imports` writes
  `runs/ontology_supervisor_semantic_gate.json`;
- focused tests cover gate decision, write path, and authority boundary;
- proposal `0109` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
wire_supervisor_semantic_gate_into_targeted_runs
```
