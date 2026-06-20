# Ontology Owner Decision Import v2

RFC: SG-RFC-0139
Version: 0.1.0

## Status

Draft proposal

Decision scope: add a richer read-only owner-decision import review artifact that
connects owner accepted/rejected decisions to gap groups, compliance findings,
write-gate findings, linked evidence, and before/after semantic status.

## Source Material

Source draft:

- `docs/archive/proposal_sources/0139_ontology_owner_decision_import_v2.md`

Roadmap:

- `docs/ontology_spec_validation_roadmap.md`

Depends on:

- `0111_ontology_closed_loop_evidence`
- `0115_ontology_decision_import_preview`
- `0135_spec_ontology_validation_report`
- `0136_specauthor_ontology_write_gate`
- `0138_ontology_gap_review_workflow`

## Problem

SpecGraph can already emit an owner-decision import preview from closed-loop
evidence, but the preview is intentionally small. It tells an operator whether an
owner decision is accepted, rejected, needs clarification, or unmatched. It does
not show enough review context to answer practical questions:

- which ontology gap group does this decision affect?
- which legacy specs or generated artifacts are tied to the decision?
- which compliance findings remain before the decision is acknowledged?
- which write-gate findings are linked to affected generated artifacts?
- what semantic status changes before and after the owner decision?

Without that richer surface, SpecSpace can show that a decision exists, but it
cannot show a useful review dashboard for operator acknowledgement.

## Proposal

Add:

```bash
make ontology-owner-decision-import-v2
```

The command emits:

```text
runs/ontology_owner_decision_import_v2.json
```

The artifact reads existing review surfaces:

- `runs/ontology_decision_import_preview.json`
- `runs/ontology_closed_loop_evidence.json`
- `runs/ontology_gap_review_workflow.json` or a freshly built gap workflow
- `runs/spec_ontology_validation_report.json` or a freshly built validation
  report
- optional `specauthor_ontology_write_gate_report` artifacts

For each owner decision preview, the v2 surface links:

- owner decision state and public decision reference;
- matched closed-loop evidence;
- matched gap-review groups;
- affected source specs and generated artifacts;
- compliance findings from spec ontology validation;
- write-gate findings for affected generated artifacts;
- before semantic status;
- after semantic status;
- required operator action.

## Implemented Slice

This slice adds:

- `tools/ontology_owner_decision_import_v2.py`;
- `make ontology-owner-decision-import-v2`;
- focused tests for accepted decisions, rejected decisions, public tombstone/no
  decision fallback, public-safe redaction, and CLI writes;
- static publish refresh wiring so clean CI/deploy builds generate both
  `ontology_gap_review_workflow.json` and
  `ontology_owner_decision_import_v2.json` before public placeholders are written;
- proposal tracking metadata.

The artifact is public-safe by design: it carries decision state and decision
refs, but does not publish raw owner identity or free-form owner rationale. It
does not treat the owner decision as automatic authority.

## Acceptance

This proposal is complete when:

- accepted owner decisions link to matching closed-loop evidence and gap groups;
- rejected owner decisions become acknowledgement-only review items;
- source specs, generated artifacts, validation findings, and write-gate findings
  are visible when they can be matched;
- before/after semantic status is explicit for every decision review;
- public tombstone or missing owner-decision artifacts produce a stable
  `no_decisions` report instead of a runtime failure;
- `make publish-bundle` generates and publishes
  `runs/ontology_owner_decision_import_v2.json` from a clean checkout;
- ontology package writes, ontology lockfile writes, canonical spec mutations,
  prompt-agent execution, semantic-gate closure, and automatic decision imports
  remain disabled;
- proposal tracking gates pass.

## Out of Scope

- Writing or editing project-local ontology packages;
- accepting, rejecting, deprecating, or renaming ontology terms;
- applying owner decisions to canonical SpecGraph nodes;
- closing semantic gates;
- executing SpecAuthorAgent or other prompt agents;
- adding SpecSpace UI.
