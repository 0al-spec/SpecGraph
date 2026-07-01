# 0195 SpecSpace Real Idea Answer Continuation Handoff

Status: implemented.

## Problem

Proposal `0194` added first-class answer authoring for real-idea intake and
repair. SpecSpace then added a UI that can collect operator answers from the
published `real_idea_answer_template.json`.

However, the bridge back from SpecSpace-owned answer state to the SpecGraph
continuation pipeline was still manual. Operators could save answers in
SpecSpace, but then had to know how to export and validate that state as a
compatible `idea_to_spec_clarification_answer_set` before continuing the
intake session.

That left one product-flow gap:

```text
SpecSpace UI answers
  -> SpecSpace-owned mutable state
  -> ? manual JSON wiring
  -> SpecGraph clarified intake / active candidate
```

## Proposal

Add a deterministic SpecGraph handoff for SpecSpace-owned real-idea intake
answers:

```bash
make specspace-real-idea-answer-import-preview
make real-idea-intake-materialize-specspace-answers
make real-idea-intake-continue-from-specspace-answers
```

The new `tools/specspace_real_idea_answer_handoff.py` reads:

- `specspace_idea_intake_clarification_answer_state`;
- `real_idea_answer_template`;
- `idea_intake_clarification_requests`;
- `user_idea_intake_session`.

It emits a read-only import preview:

```text
specspace_real_idea_answer_import_preview.json
```

and, only when the preview is ready, materializes the existing compatible
answer artifacts:

```text
real_idea_answer_set.json
idea_intake_clarification_answers.json
clarified_user_idea_intake_session.json
idea_intake_clarification_rerun_report.json
real_idea_answer_continuation_report.json
```

The full continuation target then reuses the existing real-idea active-candidate
pipeline to build:

```text
user_idea_intake_source.json
idea_event_storming_seed.json
idea_event_storming_intake.json
candidate_spec_graph.json
active_idea_to_spec_candidate.json
```

## Validation Boundary

The import preview validates:

- SpecSpace state ownership;
- workspace and candidate identity against the intake session;
- answer template refs;
- clarification request refs;
- typed answer-set compatibility through the existing clarification answer
  validator;
- truthy `may_*` authority fields;
- raw/private/local trace leakage.

Failed preview or failed materialization must not overwrite ready clarified
intake or candidate artifacts.

## Authority Boundary

This proposal does not grant SpecSpace execution authority.

It does not:

- execute prompt agents;
- let SpecSpace run SpecGraph;
- apply answers directly to source artifacts;
- mutate raw user intent;
- mutate candidate artifacts or canonical specs;
- write Ontology packages or lockfiles;
- accept Ontology terms globally;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models.

## Acceptance Criteria

- SpecSpace-owned answer state can be preview-imported without manual JSON
  wiring.
- Cross-workspace or cross-candidate answer state is blocked.
- Stale template/request refs are blocked.
- Authority-expanding fields are blocked.
- Raw idea text and local state paths are not published in the preview/report.
- Ready import preview can materialize compatible answer artifacts.
- The continuation target can proceed to the existing active-candidate flow.
- Failed import does not overwrite existing ready artifacts.

## Validation

- `tests/test_specspace_real_idea_answer_handoff.py`
- `make specspace-real-idea-answer-import-preview`
- `make real-idea-intake-materialize-specspace-answers`
- `make real-idea-intake-continue-from-specspace-answers`
