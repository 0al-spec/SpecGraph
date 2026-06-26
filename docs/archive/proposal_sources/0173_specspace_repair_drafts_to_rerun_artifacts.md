# 0173 SpecSpace Repair Drafts to Rerun Artifacts

## Status

Implemented

## Summary

SpecSpace can keep repair answers as draft-only state, and proposal `0172`
lets SpecGraph validate those drafts through a read-only import preview. The
next boundary is a deterministic builder that turns a ready import preview into
the standard idea-to-spec rerun artifacts, without making SpecSpace or the
preview itself authoritative.

This proposal adds:

```bash
make product-workspace-repair-draft-rerun
make specspace-repair-draft-rerun
```

The target reads:

```text
runs/specspace_repair_draft_import_preview.json
runs/idea_to_spec_repair_session.json
runs/idea_to_spec_clarification_requests.json
runs/active_idea_to_spec_candidate.json
runs/idea_event_storming_intake.json
runs/candidate_spec_graph.json
runs/idea_to_spec_promotion_gate.json
```

and writes:

```text
runs/idea_to_spec_clarification_answers.json
runs/product_ontology_gap_review_decisions.json
runs/idea_to_spec_answer_rerun_input.json
runs/idea_to_spec_rerun_preview.json
runs/idea_to_spec_rerun_materialization.json
runs/idea_to_spec_repair_session.json
runs/specspace_repair_draft_rerun_report.json
```

The output is still review-only. It does not apply SpecSpace drafts, mutate
SpecGraph source artifacts, accept ontology terms, or call Git Service.
If the import preview is not ready, the command writes only
`runs/specspace_repair_draft_rerun_report.json` and leaves the shared rerun
chain artifacts untouched.

## Motivation

Proposal `0172` deliberately stops at import preview. That keeps the SpecSpace
draft state non-authoritative, but it also means an operator still needs a
separate step to produce the standard rerun chain:

- clarification answers;
- typed product ontology decisions;
- answer rerun input overlay;
- rerun preview;
- rerun materialization preview;
- updated repair-session journal.

Without a deterministic bridge, downstream consumers would either inspect only
draft import candidates or manually reconstruct the rerun chain from multiple
commands. SpecGraph needs a single review-only command that consumes a ready
preview and replays those candidates through the existing validated artifacts.

## Implementation

The implemented surface is:

- `tools/specspace_repair_drafts_to_rerun_artifacts.py`;
- `make product-workspace-repair-draft-rerun`;
- `make specspace-repair-draft-rerun`;
- `runs/specspace_repair_draft_rerun_report.json`;
- standard rerun outputs under `runs/`;
- focused regression coverage in
  `tests/test_specspace_repair_drafts_to_rerun_artifacts.py`;
- registry, roadmap, and DocC tracking for proposal `0173`.

The builder validates that the import preview uses artifact kind
`specspace_repair_draft_import_preview`, contract ref
`specgraph.idea-to-spec.specspace-repair-draft-import-preview.v0.1`, schema
version `1`, read-only authority flags, and `readiness.ready: true`.

Ready clarification answer candidates are converted into an in-memory
`idea_to_spec_clarification_answer_set` and then passed through the existing
answer, ontology decision, rerun input, rerun preview, rerun materialization,
and repair-session journal builders. Deferred or invalid import-preview state
does not become accepted answers.

## Contract

The orchestration report artifact kind is:

```text
specspace_repair_draft_rerun_report
```

The contract ref is:

```text
specgraph.idea-to-spec.specspace-repair-draft-rerun.v0.1
```

The default report output is:

```text
runs/specspace_repair_draft_rerun_report.json
```

The report records:

- imported workspace, candidate, and repair-session identity;
- source refs and digests for the import preview and source artifacts;
- generated artifact refs and digests;
- generated artifact readiness state;
- draft provenance linking replayed requests back to SpecSpace draft ids;
- blocking findings from preview validation or downstream builders;
- an explicit authority boundary.

Custom paths can be threaded through Make variables such as
`SPECSPACE_REPAIR_DRAFT_RERUN_IMPORT_PREVIEW`,
`SPECSPACE_REPAIR_DRAFT_RERUN_REPAIR_SESSION`,
`IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT`,
`PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT`,
`IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT`,
`IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT`,
`IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT`, and
`IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT`.

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

The bridge is a review-only conversion from a ready import preview to the
standard rerun artifacts.

On failure or review-required inputs, the bridge writes only its report. It
does not overwrite existing `idea_to_spec_clarification_answers`,
`product_ontology_gap_review_decisions`, rerun, materialization, or
repair-session artifacts.

## Validation

- `tests/test_specspace_repair_drafts_to_rerun_artifacts.py`
- `make product-workspace-repair-draft-rerun`
- `make specspace-repair-draft-rerun`
- `make proposal-tracking-gate`
- `make docc-sync`

## Follow-Ups

- Teach SpecSpace to present the rerun report next to its draft state and
  repair-session journal.
- Let a future controlled approval artifact distinguish draft-derived rerun
  success from candidate approval.
- Keep Platform Git Service promotion blocked until a separate candidate
  approval decision exists.
- Extract common idea-to-spec JSON/public-safe helper utilities shared across
  the 0171-0173 tool family.
