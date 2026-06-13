# Ontology Delta Draft Intake

RFC: SG-RFC-0110
Version: 0.1.0

## Status

Implemented

Decision scope: deterministic, review-only intake for Ontology delta draft
requests derived from the `0109` supervisor semantic gate and `0106` ontology
delta candidate review packet.

This document does not write Ontology packages, update ontology lockfiles,
mutate canonical SpecGraph specs, accept candidate terms, invoke prompt agents,
or require access to the Ontology repository.

## Source Material

This proposal implements the next bounded runtime slice after
`0109_ontology_supervisor_semantic_gate`.

Source draft:

- `docs/archive/proposal_sources/0110_ontology_delta_draft_intake.md`

## Summary

SpecGraph now emits a deterministic Ontology delta draft intake artifact:

```text
runs/ontology_delta_draft_intake.json
```

The artifact turns delta candidates into review-only draft requests for an
Ontology owner workflow. It carries candidate ids, proposed draft delta payload,
semantic gate state, blocking item refs, and required human action. In the
checked-in fixture, the request is `blocked_by_semantic_gate` because the 0109
gate is blocked by semantic findings.

## Goals

- Add `ontology_delta_draft_intake` to the semantic policy layout.
- Define an intake contract with source artifacts, intake states, gate-state
  handling, candidate review-state handling, and consumer boundary.
- Build intake requests from `ontology_delta_candidate_review_packet` and
  `ontology_supervisor_semantic_gate`.
- Preserve the proposed delta payload for Ontology owner review.
- Keep all effects non-mutating and local under `runs/`.
- Cover artifact shape, write path, authority boundary, and registry trace in
  tests.

## Non-Goals

- Writing Ontology package drafts.
- Updating ontology lockfiles.
- Applying accepted terms back into SpecGraph specs.
- Marking candidate terms accepted.
- Bypassing a blocked semantic gate.
- Invoking prompt agents or ontologyc.
- Adding SpecSpace mutation UI.

## Runtime Contract

The intake declares:

```json
{
  "artifact_kind": "ontology_delta_draft_intake",
  "schema_version": 1,
  "proposal_id": "0110",
  "source_artifacts": {
    "supervisor_semantic_gate": "runs/ontology_supervisor_semantic_gate.json",
    "ontology_delta_candidate_review_packet": "runs/ontology_delta_candidate_review_packet.json"
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "draft_requests": []
}
```

Each draft request records:

- candidate id and term;
- proposed draft delta payload;
- intake state;
- required human action;
- blocking semantic gate refs when present;
- explicit false write/mutation/acceptance flags.

## Authority Boundary

The intake may be used as an Ontology owner draft intake handoff.

The intake may not:

- write Ontology packages;
- update ontology lockfiles;
- mutate canonical specs;
- mark candidate terms accepted;
- execute prompt agents;
- become canonical authority for ontology deltas.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `ontology_delta_draft_intake`;
- `tools/ontology_imports.py` builds `ontology_delta_draft_intake` from the
  supervisor semantic gate and delta candidate review packet;
- `make ontology-imports` writes `runs/ontology_delta_draft_intake.json`;
- focused tests cover blocked-gate intake behavior, write path, and authority
  boundary;
- proposal `0110` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
collect_ontology_owner_delta_decisions
```
