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
4. `SpecSpace#247_ontology_compliance_review_surface`
   - Consume the stable compliance review artifact contract from SpecSpace.
   - Show spec status, bindings, gaps, conflicts, and suggested owner actions in
     a read-only UI surface.
5. `0136_specauthor_ontology_write_gate`
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

## Current State

The original five-PR validation stack has expanded into a broader SpecAuthor
line:

- `0137` defines the producer-side `generated_spec_artifact` contract.
- `0138` and `0139` define read-only gap and owner-decision review surfaces.
- `0140` defines legacy-spec ontology backfill planning.
- `0141` through `0143` add layer-aware import, gap/diff review, and SpecAuthor
  write-gate context.
- `0146` through `0148` add the deterministic SpecAuthor authoring flow,
  public-safe invocation artifacts, and report-only Agent Passport
  `x-behaviorPolicies`.

The next adjacent work is no longer another standalone ontology review panel.
Ontology validation should become part of the product workspace authoring loop:
raw idea intake, candidate graph generation, pre-SIB/coherence metrics,
autonomous repair, and repository-backed materialization.

Graph versioning and production write boundaries are tracked in
[`product_workspace_graph_versioning_roadmap.md`](product_workspace_graph_versioning_roadmap.md).
