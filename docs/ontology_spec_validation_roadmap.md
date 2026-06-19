# Ontology-Backed Spec Validation Roadmap

This roadmap tracks the staged adoption of project-local Ontology packages for
SpecGraph and SpecSpace.

## Baseline

Proposal `0132` establishes the project-local package boundary:

- Ontology repository: compiler, schemas, stdlib primitives, package format,
  validation utilities, examples, and fixtures.
- SpecGraph: project-local ontology packages under `ontology/packages/`.
- SpecSpace: read-only review surfaces over published artifacts.

Existing `specs/nodes/*.yaml` files predate the ontology layer and are treated
as a legacy corpus. They are not bulk-rewritten when ontology support expands.

## Five-PR Stack

1. `0133_project_local_ontology_authoring_commands`
   - Add review-only authoring commands for package validate/preview/gap
     inspection.
   - Emit typed `runs/` artifacts without accepting terms, writing lockfiles, or
     mutating canonical specs.
2. `0134_legacy_spec_ontology_binding_index`
   - Build a report-only binding index over existing specs.
   - Classify accepted bindings, unknown terms, candidate relations, and gaps.
3. `0135_spec_ontology_validation_report`
   - Add typed validation over spec artifacts against the current ontology.
   - Keep legacy specs report-only while making generated/new artifacts eligible
     for review-required gate status.
4. `0136_specspace_ontology_compliance_review_surface`
   - Publish a stable compliance review artifact contract for SpecSpace.
   - Show spec status, bindings, gaps, conflicts, and suggested owner actions in
     a read-only UI surface.
5. `0137_specauthor_ontology_write_gate`
   - Gate generated spec/proposal writes on active ontology/domain/context,
     term bindings or gaps, and calibrated strong claims.
   - Reject or mark review-required outputs that invent terms silently or
     persist low-reliability claims as decisions.

## Adoption Rules

- Existing specs stay canonical until an ordinary reviewed SpecGraph change
  updates them.
- Observed terminology from old specs is evidence, not ontology authority.
- Unknown useful terms become ontology gaps instead of silent vocabulary drift.
- New generated artifacts adopt ontology-aware validation before old specs are
  backfilled.
- SpecSpace remains read-only until owner-decision import and mutation contracts
  are explicitly accepted.

