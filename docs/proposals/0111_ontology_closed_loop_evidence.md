# Ontology Closed-Loop Evidence

RFC: SG-RFC-0111
Version: 0.1.0

## Status

Implemented

Decision scope: deterministic SpecGraph-facing evidence surface derived from
the `0110` Ontology delta draft intake artifact.

This document does not write Ontology packages, update ontology lockfiles,
mutate canonical SpecGraph specs, accept candidate terms, close semantic gates,
invoke prompt agents, or require access to the Ontology repository.

## Source Material

This proposal implements the next bounded runtime slice after
`0110_ontology_delta_draft_intake`.

Source draft:

- `docs/archive/proposal_sources/0111_ontology_closed_loop_evidence.md`

## Summary

SpecGraph now emits a deterministic closed-loop evidence artifact:

```text
runs/ontology_closed_loop_evidence.json
```

The artifact turns Ontology delta draft intake requests into SpecGraph review
evidence entries. It carries candidate ids, intake ids, intake states, required
human action, blocking refs, and source artifacts. In the checked-in fixture,
the evidence remains `blocked_by_semantic_gate` because the upstream intake is
blocked by semantic findings.

## Goals

- Add `ontology_closed_loop_evidence` to the semantic policy layout.
- Define a closed-loop evidence contract with source intake artifact, evidence
  states, closed-loop source, and consumer boundary.
- Build evidence entries from `ontology_delta_draft_intake`.
- Preserve empty Ontology decision refs until owner decisions exist.
- Keep all effects non-mutating and local under `runs/`.
- Cover artifact shape, write path, authority boundary, and registry trace in
  tests.

## Non-Goals

- Writing Ontology package drafts.
- Updating ontology lockfiles.
- Applying accepted terms back into SpecGraph specs.
- Marking candidate terms accepted.
- Closing semantic gates.
- Invoking prompt agents or ontologyc.
- Adding SpecSpace mutation UI.

## Runtime Contract

The evidence artifact declares:

```json
{
  "artifact_kind": "ontology_closed_loop_evidence",
  "schema_version": 1,
  "proposal_id": "0111",
  "source_artifacts": {
    "ontology_delta_draft_intake": "runs/ontology_delta_draft_intake.json"
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "evidence_entries": []
}
```

Each evidence entry records:

- candidate id and intake id;
- source intake state;
- SpecGraph review state;
- required human action;
- optional Ontology decision ref, empty until real owner evidence exists;
- explicit false gate-closure and mutation flags.

## Authority Boundary

The evidence artifact may be used as SpecGraph review evidence.

The evidence artifact may not:

- write Ontology packages;
- update ontology lockfiles;
- mutate canonical specs;
- mark candidate terms accepted;
- close semantic gates;
- execute prompt agents;
- become canonical authority for ontology deltas.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `ontology_closed_loop_evidence`;
- `tools/ontology_imports.py` builds `ontology_closed_loop_evidence` from the
  delta draft intake artifact;
- `make ontology-imports` writes `runs/ontology_closed_loop_evidence.json`;
- focused tests cover blocked-gate evidence behavior, write path, and authority
  boundary;
- proposal `0111` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
wire_closed_loop_evidence_into_specgraph_review
```
