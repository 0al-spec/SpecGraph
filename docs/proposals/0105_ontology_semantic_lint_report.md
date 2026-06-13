# Ontology Semantic Lint Report

RFC: SG-RFC-0105
Version: 0.1.0

## Status

Implemented

Decision scope: deterministic semantic lint report derived from the `0104`
ontology semantic context pack.

This document does not parse arbitrary natural language, run prompt agents,
write Ontology packages, generate canonical ontology deltas, mutate canonical
SpecGraph specs, create lockfiles, or build SpecSpace UI.

## Source Material

This proposal implements the next bounded runtime slice after
`0104_ontology_semantic_context_pack`.

Source draft:

- `docs/archive/proposal_sources/0105_ontology_semantic_lint_report.md`

## Summary

SpecGraph now emits a full deterministic semantic lint report:

```text
runs/ontology_semantic_lint_report.json
```

The report consumes the `0104` context pack and classifies deterministic fixture
terms into accepted, alias, unknown, deprecated, and relation-conflict findings.
It groups review-required and blocking findings, emits candidate ontology delta
terms for unresolved gaps, and records recommended actions for later supervisor
or SpecSpace review surfaces.

## Goals

- Add `semantic_lint_report` to the semantic policy layout.
- Define a `semantic_lint_report_contract` with target scope and consumer
  boundary.
- Build `ontology_semantic_lint_report` from the semantic context pack.
- Keep report authority review-only and local under `runs/`.
- Reuse the same deterministic classifier as the `0103` smoke artifact.
- Cover report findings, candidate delta terms, write path, and registry trace
  in tests.

## Non-Goals

- Parsing arbitrary generated text.
- Invoking LLM prompt agents.
- Writing ontology delta packets or ontology packages.
- Updating ontology lockfiles.
- Mutating canonical `specs/nodes/*.yaml`.
- Adding SpecSpace UI or review action APIs.

## Runtime Contract

The report declares:

```json
{
  "artifact_kind": "ontology_semantic_lint_report",
  "schema_version": 1,
  "proposal_id": "0105",
  "source_context_pack": "runs/ontology_semantic_context_pack.json",
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "findings": [],
  "blocking_findings": [],
  "review_required_findings": [],
  "candidate_delta_terms": [],
  "recommended_actions": []
}
```

In the checked-in fixture, the report identifies:

- `Exam` as an accepted term;
- `requires policy` as an accepted alias for `examcalc:requires_policy`;
- `CASFunction` as an unresolved ontology gap and candidate delta term;
- `ExamPolicy` as a deprecated term;
- `allows policy` as a relation conflict.

The summary status is `blocked_relation_conflict`, preserving the policy rule
that wrong relation direction outranks deprecated and unknown terms.

## Authority Boundary

The lint report may be used as supervisor gate evidence and SpecSpace review
surface evidence.

The lint report may not:

- execute prompt agents;
- mutate canonical specs;
- write ontology deltas;
- update ontology packages;
- become canonical authority for accepted terms.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `semantic_lint_report`;
- `tools/ontology_imports.py` builds `ontology_semantic_lint_report` from the
  context pack;
- `make ontology-imports` writes `runs/ontology_semantic_lint_report.json`;
- focused tests cover report findings and authority boundary;
- proposal `0105` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and the Python test suite pass.

## Next Gap

```text
build_ontology_delta_candidate_review_packet
```
