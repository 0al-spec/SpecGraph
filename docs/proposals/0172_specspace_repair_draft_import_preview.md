# 0172 SpecSpace Repair Draft Import Preview

## Status

Implemented

## Summary

SpecSpace can now keep product repair answers as draft-only, SpecSpace-owned
state. SpecGraph needs a deterministic boundary that can inspect that state and
turn valid drafts into review-only import candidates before any later rerun
artifact consumes them.

This proposal adds:

```bash
make specspace-repair-draft-import-preview
```

The target reads:

```text
runs/idea_to_spec_repair_drafts.json
runs/idea_to_spec_repair_session.json
runs/idea_to_spec_clarification_requests.json
  -> runs/specspace_repair_draft_import_preview.json
```

The output is a preview only. It does not apply SpecSpace drafts, mutate
SpecGraph artifacts, accept ontology terms, or call Git Service.

## Motivation

Proposal `0171` gave downstream consumers one durable repair-session journal.
SpecSpace then added draft-only UI state for answering clarification requests
and choosing ontology-gap actions such as `bind_existing_term`, `alias`,
`propose_project_local_term`, `reject`, and `defer`.

Those drafts are useful operator intent, but they are not SpecGraph authority.
Before any future conversion into `idea_to_spec_clarification_answers` or
`product_ontology_gap_review_decisions`, SpecGraph needs a typed import preview
that:

- proves the draft state belongs to SpecSpace;
- validates the draft state against the current repair session and
  clarification requests;
- rejects stale source refs and authority expansion;
- emits sanitized answer and ontology decision candidates;
- shows which blocking requests would be resolved or left unresolved.

## Implementation

The implemented surface is:

- `tools/specspace_repair_draft_import_preview.py`;
- `make specspace-repair-draft-import-preview`;
- `runs/specspace_repair_draft_import_preview.json`;
- focused regression coverage in
  `tests/test_specspace_repair_draft_import_preview.py`;
- registry, roadmap, and DocC tracking for proposal `0172`.

The preview records:

- selected workspace/candidate/session identity;
- input artifact refs and digests;
- root artifact validation findings;
- valid import candidates;
- invalid drafts;
- deferred drafts;
- superseded duplicate drafts;
- clarification answer candidates;
- product ontology decision candidates;
- blocking request ids that would be resolved;
- ontology gaps that would remain unresolved.

## Contract

The artifact kind is:

```text
specspace_repair_draft_import_preview
```

The contract ref is:

```text
specgraph.idea-to-spec.specspace-repair-draft-import-preview.v0.1
```

The default output is:

```text
runs/specspace_repair_draft_import_preview.json
```

The builder validates that the draft state uses
`artifact_kind: specspace_idea_to_spec_repair_draft_state`,
`schema_version: 1`, and `state_owner: SpecSpace`. It rejects write-capable
authority flags on the root state and on individual drafts.

Drafts must reference the imported repair-session journal, match the current
workspace/candidate/session identity, reference an existing clarification
request, use an allowed action for that request, and provide the expected
answer shape. Duplicate drafts for the same workspace/request are resolved
deterministically by newest timestamp and reported as superseded warnings.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- import drafts into canonical SpecGraph state;
- apply answers to source artifacts;
- apply ontology decisions to source artifacts;
- mutate candidate source artifacts;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- mark candidate graphs accepted;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation authority.

The preview is a review-only import candidate surface.

## Validation

- `tests/test_specspace_repair_draft_import_preview.py`
- `make specspace-repair-draft-import-preview`
- `make proposal-tracking-gate`
- `make docc-sync`

## Follow-Ups

- Add a controlled builder that converts a ready import preview into
  `idea_to_spec_clarification_answers` and
  `product_ontology_gap_review_decisions`.
- Teach SpecSpace to show import-preview readiness and invalid draft findings
  next to its local draft state.
- Keep Platform Git Service promotion blocked until the repair session reflects
  accepted, replayed decisions rather than draft-only state.
