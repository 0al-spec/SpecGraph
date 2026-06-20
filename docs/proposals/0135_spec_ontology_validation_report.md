# Spec Ontology Validation Report

RFC: SG-RFC-0135
Version: 0.1.0

## Status

Draft proposal

Decision scope: add a typed report-only ontology validation report for specs.

## Source Material

Source draft:

- `docs/archive/proposal_sources/0135_spec_ontology_validation_report.md`

Roadmap:

- `docs/ontology_spec_validation_roadmap.md`

Depends on:

- `0134_legacy_spec_ontology_binding_index`

## Problem

SpecGraph can now build a binding index over existing specs, but there is not
yet a formal validation report that turns those bindings into typed findings.

The validation must not be pure prose or LLM judgement. It should check
machine-readable artifacts against the current ontology package.

## Proposal

Add:

```bash
make spec-ontology-validation
```

The target emits:

```text
runs/spec_ontology_validation_report.json
```

The report validates:

- required structural binding to `sgcore:Spec`;
- relation existence in the normalized ontology IR;
- relation domain/range compatibility;
- unknown legacy terminology gaps.

Existing specs remain `report_only`. Generated artifacts are declared
`review_required` in the validation-mode contract, but hard gate enforcement is
deferred.

## Implemented Slice

This slice adds:

- `tools/spec_ontology_validation_report.py`;
- `make spec-ontology-validation`;
- tests for legacy report-only behavior, relation contract checks, and finding
  shape;
- proposal tracking metadata.

## Acceptance

This proposal is complete when:

- validation report generation succeeds from current ontology IR and binding
  index;
- existing specs remain report-only;
- SG-SPEC-0001 passes required binding and relation checks while surfacing
  legacy terminology gaps as warnings;
- tests assert that hard gates remain disabled;
- proposal tracking gates pass.

## Out of Scope

- Hard write gate enforcement;
- generated artifact persistence blocking;
- LLM-based semantic judgement;
- canonical spec rewrites;
- SpecSpace UI.

