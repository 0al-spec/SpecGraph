# Ontology Gap Review Workflow

RFC: SG-RFC-0138
Version: 0.1.0

## Status

Draft proposal

Decision scope: add a read-only workflow artifact that groups ontology gaps
from package authoring, legacy spec validation, and generated artifacts for
operator and owner review.

## Source Material

Source draft:

- `docs/archive/proposal_sources/0138_ontology_gap_review_workflow.md`

Roadmap:

- `docs/ontology_spec_validation_roadmap.md`

Depends on:

- `0133_project_local_ontology_authoring_commands`
- `0135_spec_ontology_validation_report`
- `0137_specauthor_generated_artifact_contract`

## Problem

SpecGraph now emits several gap-bearing surfaces:

- project-local ontology package gap preview;
- legacy spec ontology validation findings;
- generated artifacts with `ontology_gaps`.

Those gaps are visible, but they are not grouped into a review workflow. An
operator needs to see whether a proposed term or relation appears in legacy
specs, generated artifacts, package previews, or several places at once. The
next action should be explicit and review-scoped.

## Proposal

Add:

```bash
make ontology-gap-review \
  ONTOLOGY_GAP_REVIEW_GENERATED_ARTIFACT=<generated-artifact.json>
```

The command emits:

```text
runs/ontology_gap_review_workflow.json
```

The artifact groups gaps by proposed term or relation and includes:

- `proposed_term` or `proposed_relation`;
- `missing_ref` when known;
- source specs with `spec_id`, path, finding id, and classification;
- affected generated artifacts with source ref, path, target artifact kind, and
  title;
- source gap refs and source findings;
- recommended owner action;
- recommended route;
- read-only or acknowledgement-only operator actions.

## Implemented Slice

This slice adds:

- `tools/ontology_gap_review_workflow.py`;
- `make ontology-gap-review`;
- focused tests for package gaps, spec validation findings, generated artifact
  gaps, empty/clear workflow state, and CLI writes;
- proposal tracking metadata.

The default command builds package gap preview and spec validation report from
the current checkout. Generated artifacts are optional explicit inputs so local
or future invocation wrappers can attach affected generated artifacts without
publishing fixture content by default.

## Acceptance

This proposal is complete when:

- package gap preview rows become grouped review items;
- spec validation findings attach source specs to gap groups;
- generated artifact `ontology_gaps` attach affected generated artifact refs to
  gap groups;
- each group has a recommended owner action;
- the workflow exposes only read-only or acknowledgement-only operator actions;
- ontology package writes, lockfile writes, owner-decision imports, prompt-agent
  execution, and canonical spec mutations remain disabled;
- proposal tracking gates pass.

## Out of Scope

- Accepting, rejecting, deprecating, or renaming ontology terms;
- importing Ontology owner decisions;
- showing before/after owner decision status;
- mutating `ontology/packages/**`;
- mutating `specs/nodes/*.yaml`;
- running SpecAuthorAgent;
- adding SpecSpace UI.
