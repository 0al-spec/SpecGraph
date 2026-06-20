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

## Next Adoption Slice

Proposal `0137` adds the producer-side `generated_spec_artifact` contract for
SpecAuthorAgent output. It sits before `0136`: the contract checks that agent
output is a typed, review-bound artifact with producer metadata, active
ontology/domain/context, target artifact metadata, draft payload, term/gap
records, calibrated claims, and review-only materialization intent. Only then
should the artifact be handed to the ontology write gate.

Proposal `0145` adds the SpecAuthor invocation wrapper: a typed invocation
artifact that links user intent, active ontology context, model applicability,
generated artifact, contract report, write-gate report, and final operator
decision without executing prompts inside supervisor or mutating canonical
specs directly.

Proposal `0138` adds a read-only ontology gap review workflow before owner
decision import. It groups package gaps, legacy spec validation findings, and
optional generated artifact gaps by proposed term or relation, preserving source
specs, affected generated artifact refs, source findings, and recommended owner
actions. Owner decision import v2 remains the next separate slice.

Proposal `0139` adds that owner decision import v2 slice as a richer read-only
review surface. It links accepted/rejected Ontology owner decisions back to
closed-loop evidence, grouped ontology gaps, spec validation findings,
SpecAuthor write-gate findings, affected review items, and before/after semantic
status. It remains acknowledgement-only: no ontology package writes, lockfile
writes, canonical spec mutations, prompt-agent execution, automatic imports, or
semantic-gate closure.

Proposal `0140` adds that legacy-spec backfill plan. It classifies the current
report-only legacy corpus into clean specs, warning-only specs, new-term or
alias/deprecation decision needs, relation review needs, and small reviewed PR
batch candidates. It remains plan-only: no bulk rewrite, package write, lockfile
write, canonical spec mutation, or prompt-agent execution.

The next bounded slice after `0140` is the SpecSpace Ontology Workbench: consume
the package metadata, normalized IR, gaps, compliance findings, generated
write-gate reports, owner decisions, and legacy backfill batches in one
consolidated read-only UI surface.
