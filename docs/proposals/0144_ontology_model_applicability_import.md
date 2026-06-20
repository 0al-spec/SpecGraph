# 0144 Ontology Model Applicability Import

## Status

Implemented

## Source

- `docs/archive/proposal_sources/0144_ontology_model_applicability_import.md`

## Summary

SpecGraph now consumes the compiler-side `ONT-040` model applicability and
change-classification contracts as read-only ontology import metadata.

Package entries can expose `model_applicability` and
`model_applicability_summary` from normalized IR. Compatibility diff previews
can expose compiler-provided `change_classification` buckets:
`structural_changes`, `annotation_changes`, and `applicability_changes`.

## Motivation

Layer metadata narrows *where* a concept sits in the ontology model, but it does
not explain when the whole package model applies or when a diff invalidates the
model's assumptions. Downstream SpecGraph and SpecSpace review surfaces need to
show:

- applies-to scope and exclusions;
- authored assumptions;
- invalidation triggers;
- whether a diff is structural, annotation-only, or applicability drift.

This should be visible without giving SpecGraph authority to edit the ontology
package or mutate canonical specs.

## Implementation

This slice updates `tools/ontology_imports.py`:

- reads `modelApplicability` from normalized IR;
- publishes `model_applicability` and `model_applicability_summary` on package
  index entries;
- includes aggregate applicability counters in `ontology_package_index.summary`;
- parses `compatibility_report.changes.changeClassification`;
- publishes `change_classification` and summary counts in compatibility diff
  previews;
- preserves fallback behavior for older compatibility reports without
  `changeClassification`.

The project-local `ontology/packages/specgraph-core` package now declares a
minimal applicability profile and regenerated compiler evidence.

## Authority Boundary

This proposal does not make SpecGraph an ontology authority.

It only updates the project-local SpecGraph Core package fixture and generated
compiler evidence needed to consume the `ONT-040` contract.

It does not:

- infer applicability from prose;
- write upstream Ontology repository packages;
- update upstream Ontology repository lockfiles;
- mutate canonical specs;
- accept or reject ontology terms;
- import owner decisions;
- execute prompt agents;
- close semantic gates;
- add SpecSpace UI.

## Validation

- `tests/test_ontology_import_policy.py::test_specgraph_core_import_fixture_projects_compiler_backed_gaps_and_diffs`
  verifies the project-local package applicability profile and structural
  change classification.
- `tests/test_ontology_import_policy.py::test_ontology_diff_preview_preserves_compiler_change_classification`
  verifies structural, annotation, and applicability change buckets.
- `ontologyc check`, `ontologyc compile`, `ontologyc validate-specgraph`, and
  `ontologyc diff` were used to refresh project-local compiler artifacts.

## Follow-ups

- Add SpecSpace Ontology Workbench rendering for applicability assumptions and
  invalidation triggers.
- Feed applicability frame into SpecAuthor prompt/runtime invocation once the
  prompt-side behavior is implemented.
