# Legacy Spec Ontology Backfill Plan

RFC: SG-RFC-0140
Version: 0.1.0

## Status

Draft proposal

Decision scope: add a review-first backfill planning artifact for legacy specs
that predate project-local ontology adoption.

## Source Material

Source draft:

- `docs/archive/proposal_sources/0140_legacy_spec_ontology_backfill_plan.md`

Roadmap:

- `docs/ontology_spec_validation_roadmap.md`

Depends on:

- `0134_legacy_spec_ontology_binding_index`
- `0135_spec_ontology_validation_report`
- `0138_ontology_gap_review_workflow`
- `0139_ontology_owner_decision_import_v2`

## Problem

SpecGraph has a legacy corpus of specs that predates the ontology layer. The
current validation report is useful, but it produces many report-only findings.
Bulk-rewriting the corpus would blur review boundaries and make it hard to tell
which changes are safe terminology cleanup, which require ontology owner
decisions, and which should wait for relation contract review.

The next step is not mutation. It is a stable plan that answers:

- which specs are clean against the current ontology;
- which specs have only report-only warnings;
- which specs need new-term or alias/deprecation decisions;
- which specs need relation review;
- which specs are small enough for reviewed PR batches.

## Proposal

Add:

```bash
make legacy-spec-ontology-backfill-plan
```

The command emits:

```text
runs/legacy_spec_ontology_backfill_plan.json
```

The artifact reads:

- `runs/spec_ontology_validation_report.json` or a freshly built validation
  report;
- `runs/ontology_gap_review_workflow.json` or a freshly built gap workflow.

For every legacy spec, it records:

- validation status;
- finding counts and classification counts;
- unknown terms;
- relation findings;
- missing required binding findings;
- matched gap-review groups;
- backfill category;
- recommended owner/operator action.

It also emits small PR batch candidates bounded by configurable thresholds:

- max findings per candidate spec;
- max specs per batch;
- max findings per batch.

## Implemented Slice

This slice adds:

- `tools/legacy_spec_ontology_backfill_plan.py`;
- `make legacy-spec-ontology-backfill-plan`;
- tests for clean specs, warning-only specs, new-term decision needs, relation
  review, small PR batch grouping, and CLI writes;
- static publish refresh wiring so clean CI/deploy builds publish
  `runs/legacy_spec_ontology_backfill_plan.json`;
- proposal tracking metadata.

## Acceptance

This proposal is complete when:

- clean legacy specs are identified;
- warning-only legacy specs are counted separately from clean specs;
- specs that require new-term/alias decisions are visible;
- specs that require relation review are visible;
- small PR batch candidates are grouped without exceeding configured thresholds;
- source validation findings and gap-review groups remain linked;
- the artifact remains plan-only and does not write ontology packages, ontology
  lockfiles, or canonical specs;
- `make publish-bundle` generates and publishes
  `runs/legacy_spec_ontology_backfill_plan.json`;
- proposal tracking gates pass.

## Out of Scope

- Bulk rewriting legacy specs;
- applying any backfill batch;
- accepting, rejecting, deprecating, or renaming ontology terms;
- writing project-local ontology packages;
- writing ontology lockfiles;
- closing semantic gates;
- executing prompt agents;
- adding SpecSpace UI.
