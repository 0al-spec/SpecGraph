# Legacy Spec Ontology Binding Index

RFC: SG-RFC-0134
Version: 0.1.0

## Status

Draft proposal

Decision scope: add a report-only ontology binding index for the existing
SpecGraph spec corpus.

## Source Material

Source draft:

- `docs/archive/proposal_sources/0134_legacy_spec_ontology_binding_index.md`

Roadmap:

- `docs/ontology_spec_validation_roadmap.md`

Depends on:

- `0132_project_local_ontology_package_boundary`
- `0133_project_local_ontology_authoring_commands`

## Problem

The ontology layer appeared after most canonical specs already existed. A strict
validator cannot be enabled safely until SpecGraph can see how the current
legacy corpus maps to accepted ontology entities and where it has gaps.

## Proposal

Add `runs/spec_ontology_binding_index.json`, built by:

```bash
make spec-ontology-bindings
```

The index is report-only. It should:

- scan existing `specs/nodes/*.yaml`;
- bind obvious structural facts to accepted ontology refs;
- surface relation candidates such as `Spec -> AcceptanceCriterion`;
- emit unknown terminology as ontology gaps;
- mark every entry as `legacy_report_only`;
- avoid changing canonical spec files.

## Implemented Slice

This slice adds:

- `tools/spec_ontology_binding_index.py`;
- `make spec-ontology-bindings`;
- focused tests for SG-SPEC-0001 and corpus-level shape;
- proposal tracking metadata.

## Acceptance

This proposal is complete when:

- the binding index emits one entry per canonical spec node;
- existing specs are marked `legacy_report_only`;
- obvious structural bindings include `sgcore:Spec`, `sgcore:Node`,
  `sgcore:AcceptanceCriterion`, and `sgcore:Evidence` where applicable;
- unknown legacy terminology becomes gap evidence;
- tests prove the artifact is report-only and non-mutating;
- proposal tracking gates pass.

## Out of Scope

- Natural-language semantic interpretation;
- LLM-assisted binding suggestions;
- hard validation gates;
- canonical spec rewrites;
- accepting terms into the ontology package;
- SpecSpace UI.

