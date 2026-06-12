# Ontology Semantic Control Policy

RFC: SG-RFC-0103
Version: 0.1.0

## Status

Implemented

Decision scope: machine-readable semantic control policy and deterministic
smoke classification over the existing `0060` ontology import fixture.

This document does not build the full agent context pack, run prompt agents,
invoke `ontologyc`, generate ontology deltas, mutate canonical specs, create an
ontology lockfile, or build SpecSpace UI.

## Source Material

This proposal implements the first bounded runtime slice after
`0100_ontology_grounded_semantic_control`.

Source draft:

- `docs/archive/proposal_sources/0103_ontology_semantic_control_policy.md`

The proposal id intentionally starts at `0103` because `0101` and `0102` are
reserved for parallel proposal work in neighboring worktrees.

## Summary

SpecGraph now has a machine-readable semantic control policy:

```text
tools/ontology_semantic_control_policy.json
```

The existing `make ontology-imports` pipeline also emits a deterministic smoke
artifact:

```text
runs/ontology_semantic_lint_smoke.json
```

The smoke consumes the existing `0060` ontology import surfaces and classifies a
small generated-text fixture into:

- `accepted_term`;
- `accepted_alias`;
- `unknown_term`;
- `deprecated_term`;
- `relation_conflict`.

The smoke proves the first useful guardrail: generated text can be checked
against accepted ontology refs and review-only ontology gaps without granting
the generated terms canonical authority.

## Goals

- Add `ontology_semantic_control_policy`.
- Define accepted term classifications and lint statuses.
- Define authority boundaries for context packs, lint reports, smoke reports,
  and ontology delta candidates.
- Reuse the existing `0060` package, binding, gap, and governance surfaces.
- Emit a deterministic smoke report from `make ontology-imports`.
- Keep all outputs under `runs/` and non-canonical.

## Non-Goals

- Building `runs/ontology_semantic_context_pack.json`.
- Building the full `runs/ontology_semantic_lint_report.json`.
- Parsing arbitrary natural language.
- Invoking an LLM or prompt pack.
- Invoking `ontologyc`.
- Writing ontology packages or ontology lockfiles.
- Mutating `specs/nodes/*.yaml`.
- Adding SpecSpace UI or API routes.

## Runtime Contract

The policy declares:

```text
tools/ontology_semantic_control_policy.json
```

The first runtime smoke declares:

```json
{
  "artifact_kind": "ontology_semantic_lint_smoke",
  "schema_version": 1,
  "proposal_id": "0103",
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "term_results": [],
  "summary": {
    "status": "blocked_relation_conflict"
  }
}
```

The summary status follows the priority declared in policy. In the checked-in
fixture, `relation_conflict` outranks deprecated and unknown terms because a
wrong relation can invert the model semantics.

## Source Surfaces

The smoke consumes the existing `0060` surfaces:

- `ontology_package_index`;
- `ontology_binding_preview`;
- `ontology_import_gap_index`;
- `ontology_governance_evidence_index`.

The smoke does not require those surfaces to be tracked files. They are derived
inside the `make ontology-imports` run and written under ignored `runs/` paths
for local or CI verification.

## Authority Boundary

The smoke report is evidence only:

- context pack is not authority;
- lint report is not authority;
- smoke report is not authority;
- ontology delta candidate is not authority;
- Ontology governance remains required for accepted ontology changes;
- SpecGraph proposal review remains required for graph-side changes;
- canonical mutations are forbidden.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` exists;
- `make ontology-imports` writes `runs/ontology_semantic_lint_smoke.json`;
- the smoke classifies accepted, alias, unknown, deprecated, and relation
  conflict terms;
- policy validation rejects authority expansion;
- focused tests cover the smoke and write path;
- proposal `0103` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and the Python test suite pass.

## Next Gap

```text
build_ontology_semantic_context_pack
```
