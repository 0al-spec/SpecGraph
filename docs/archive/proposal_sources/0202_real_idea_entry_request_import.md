# 0202 Real Idea Entry Request Import

## Status

Draft / runtime slice.

## Summary

Add a review-only bridge from SpecSpace-owned raw idea entry request state into
the existing real idea intake pipeline.

SpecSpace may collect a user's raw product idea as local mutable state, but it
must not execute SpecGraph, mutate candidate artifacts, or publish raw idea text.
This proposal adds a SpecGraph import preview and materialization step that can
validate that state, keep raw text local-only, and produce the existing intake
session, clarification requests, and answer template artifacts under a chosen
run directory.

## Decision

Introduce `tools/real_idea_entry_request_import.py` with two subcommands:

- `preview`: read `real_idea_entry_requests.json`, select exactly one submitted
  request, and write
  `specspace_real_idea_entry_request_import_preview.json` without raw idea text.
- `materialize`: verify the preview against the current state and write the
  real idea intake artifacts for that selected request.

Add Make targets:

```bash
make specspace-real-idea-entry-import-preview
make real-idea-intake-from-entry-request
```

`real-idea-intake-from-entry-request` writes into `REAL_IDEA_SMOKE_RUN_DIR`:

- `local_operator_user_idea_raw_input.json`;
- `user_idea_intake_session.json`;
- `user_idea_intake_source.json` when the session is ready;
- `user_idea_intake_interview_report.json`;
- `real_idea_entry_request_intake_report.json`;
- `idea_intake_clarification_requests.json`;
- `real_idea_answer_template.json`.

## Authority Boundary

The bridge remains review-only. It must not:

- execute prompt agents;
- mutate user intent;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept Ontology terms;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models.

If SpecSpace-owned state or a nested request claims expanded authority, the
preview is blocked.

## Privacy Boundary

Raw idea text remains local-only. It may be written only to the local raw input
artifact inside the selected run directory. Public-safe preview/report artifacts
may contain request identity, workspace identity, counts, sanitized hints, and a
digest of the raw idea text, but not the raw text itself.

The materialization step rejects stale previews by checking both the source
state digest and selected raw-text digest before writing intake artifacts.

## Acceptance Criteria

- `make specspace-real-idea-entry-import-preview` writes a sanitized import
  preview and fails in strict mode for missing, ambiguous, stale, or
  authority-expanding entry state.
- `make real-idea-intake-from-entry-request` materializes the selected request
  into real idea intake artifacts in `REAL_IDEA_SMOKE_RUN_DIR`.
- Raw idea text is absent from import preview and intake report artifacts.
- Stale previews do not materialize.
- The target also prepares clarification requests and answer template artifacts
  for the existing SpecSpace answer-authoring continuation flow.

## Non-goals

- Do not add a prompt agent.
- Do not infer missing event-storming structure.
- Do not auto-continue through clarification answers.
- Do not write canonical specs.
- Do not write Ontology packages or accept ontology terms.
- Do not run Platform or Git Service.
