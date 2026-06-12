# Ontology Delta Candidate Review Packet

RFC: SG-RFC-0106
Version: 0.1.0

## Status

Implemented

Decision scope: deterministic review packet for ontology delta candidates
reported by the `0105` semantic lint report.

This document does not write Ontology packages, update ontology lockfiles,
mutate canonical SpecGraph specs, invoke prompt agents, or build SpecSpace UI.

## Source Material

This proposal implements the next bounded runtime slice after
`0105_ontology_semantic_lint_report`.

Source draft:

- `docs/archive/proposal_sources/0106_ontology_delta_candidate_review_packet.md`

## Summary

SpecGraph now emits a deterministic review packet:

```text
runs/ontology_delta_candidate_review_packet.json
```

The packet consumes the semantic lint report candidate terms and turns them into
explicit ontology delta candidates with review actions. It is suitable as
supervisor gate evidence or SpecSpace review-surface input, but it does not
write ontology deltas or mutate canonical graph specs.

## Goals

- Add `ontology_delta_candidate_review_packet` to the semantic policy layout.
- Define a review packet contract with candidate source, target scope, review
  actions, and consumer boundary.
- Build the packet from `runs/ontology_semantic_lint_report.json`.
- Preserve candidate payloads for Ontology owner review.
- Keep all effects non-mutating and local under `runs/`.
- Cover packet shape, review actions, write path, and registry trace in tests.

## Non-Goals

- Writing Ontology package drafts.
- Updating ontology lockfiles.
- Applying accepted terms back into SpecGraph specs.
- Resolving relation conflicts automatically.
- Adding SpecSpace review UI or mutation APIs.
- Invoking prompt agents.

## Runtime Contract

The packet declares:

```json
{
  "artifact_kind": "ontology_delta_candidate_review_packet",
  "schema_version": 1,
  "proposal_id": "0106",
  "source_lint_report": "runs/ontology_semantic_lint_report.json",
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "candidates": [],
  "review_actions": []
}
```

In the checked-in fixture, the packet contains one candidate:

```text
examcalc:CASFunction
```

The available review actions are:

- `approve_for_ontology_package_draft`;
- `reject_candidate`;
- `request_clarification`.

Each action records a non-mutating effect. Approval routes a candidate to an
Ontology owner package draft workflow; it does not write that package.

## Authority Boundary

The review packet may be used as supervisor gate evidence and SpecSpace review
surface input.

The review packet may not:

- write Ontology packages;
- update ontology lockfiles;
- mutate canonical SpecGraph specs;
- mark candidate terms accepted without Ontology governance;
- become canonical authority for ontology deltas.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `ontology_delta_candidate_review_packet`;
- `tools/ontology_imports.py` builds the packet from the lint report;
- `make ontology-imports` writes
  `runs/ontology_delta_candidate_review_packet.json`;
- focused tests cover candidate payloads, review actions, and authority
  boundary;
- proposal `0106` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and the Python test suite pass.

## Next Gap

```text
build_specspace_semantic_review_surface
```
