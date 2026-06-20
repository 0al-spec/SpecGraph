# 0144 Ontology Model Applicability Import

Origin: follow-up to Ontology `ONT-040` and SpecGraph proposals `0141` and
`0142`.

## Intent

Ontology compiler normalized IR can now carry package-level
`modelApplicability`, and compatibility reports can carry
`changes.changeClassification`.

SpecGraph should consume both as read-only review data:

- package index exposes applicability scope, assumptions, and invalidation
  triggers;
- compatibility diff preview exposes structural, annotation, and applicability
  change buckets;
- summary counters make the data visible to SpecSpace without reading raw IR.

## Boundaries

This slice must not:

- infer applicability from prose;
- write upstream Ontology repository packages or lockfiles;
- mutate non-project-local ontology package fixtures;
- mutate canonical specs;
- accept or reject ontology terms;
- import owner decisions;
- execute prompt agents;
- close semantic gates;
- add SpecSpace UI.

## Acceptance

- `ontology/packages/specgraph-core` declares package-level applicability data.
- `runs/ontology_package_index.json` can expose `model_applicability` and
  `model_applicability_summary`.
- `runs/ontology_compatibility_diff_preview.json` can expose
  `change_classification`.
- Regression tests cover package applicability, structural classification, and
  applicability / annotation classification.
