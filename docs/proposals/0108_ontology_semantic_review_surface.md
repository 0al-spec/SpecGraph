# Ontology Semantic Review Surface

RFC: SG-RFC-0108
Version: 0.1.0

## Status

Implemented

Decision scope: deterministic review surface derived from the `0104` ontology
semantic context pack, `0105` semantic lint report, and `0106` ontology delta
candidate review packet.

This document does not add SpecSpace UI, write Ontology packages, update
ontology lockfiles, mutate canonical SpecGraph specs, accept candidate terms,
invoke prompt agents, or parse arbitrary natural language.

## Source Material

This proposal implements the next bounded runtime slice after
`0106_ontology_delta_candidate_review_packet`.

Source draft:

- `docs/archive/proposal_sources/0108_ontology_semantic_review_surface.md`

## Summary

SpecGraph now emits a deterministic review surface:

```text
runs/ontology_semantic_review_surface.json
```

The surface combines the context pack, lint report, and delta candidate review
packet into one SpecSpace/supervisor-facing artifact. It carries grounding
summary, blocking findings, review-required findings, ontology delta candidates,
unified review items, and non-mutating review actions.

The surface is presentation and gate evidence only. It is not canonical
Ontology authority and it does not perform any write.

## Goals

- Add `semantic_review_surface` to the semantic policy layout.
- Define a `semantic_review_surface_contract` with source artifacts, display
  sections, review item sources, review actions, and consumer boundary.
- Build `ontology_semantic_review_surface` from the `0104`, `0105`, and `0106`
  artifacts.
- Preserve source artifact refs so SpecSpace can trace each review item back to
  the derived evidence that produced it.
- Keep all effects non-mutating and local under `runs/`.
- Cover surface shape, write path, authority boundary, and registry trace in
  tests.

## Non-Goals

- Building SpecSpace UI.
- Adding SpecSpace mutation APIs.
- Writing Ontology package drafts.
- Updating ontology lockfiles.
- Applying accepted terms back into canonical SpecGraph specs.
- Marking candidate terms accepted.
- Invoking prompt agents or ontologyc.

## Runtime Contract

The surface declares:

```json
{
  "artifact_kind": "ontology_semantic_review_surface",
  "schema_version": 1,
  "proposal_id": "0108",
  "source_artifacts": {
    "semantic_context_pack": "runs/ontology_semantic_context_pack.json",
    "semantic_lint_report": "runs/ontology_semantic_lint_report.json",
    "ontology_delta_candidate_review_packet": "runs/ontology_delta_candidate_review_packet.json"
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "review_items": [],
  "review_actions": []
}
```

In the checked-in fixture, the surface exposes:

- blocking findings for `ExamPolicy` and `allows policy`;
- a review-required finding for `CASFunction`;
- one ontology delta candidate for `examcalc:CASFunction`;
- review actions for replacing deprecated terms, using accepted relations,
  emitting ontology gaps, approving for Ontology owner package drafting,
  rejecting candidates, and requesting clarification.

## Authority Boundary

The review surface may be used as supervisor gate evidence and SpecSpace review
surface input.

The review surface may not:

- execute prompt agents;
- write Ontology packages;
- update ontology lockfiles;
- mutate canonical specs;
- mark candidate terms accepted;
- become canonical authority for accepted terms or ontology deltas.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `semantic_review_surface`;
- `tools/ontology_imports.py` builds `ontology_semantic_review_surface` from
  the context pack, lint report, and delta candidate review packet;
- `make ontology-imports` writes
  `runs/ontology_semantic_review_surface.json`;
- focused tests cover review items, review actions, write path, and authority
  boundary;
- proposal `0108` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
build_specspace_semantic_review_surface_consumer
```
