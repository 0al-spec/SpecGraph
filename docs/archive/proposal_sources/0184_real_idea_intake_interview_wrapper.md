# 0184 Real Idea Intake Interview Wrapper

Status: implemented.

## Problem

Proposal `0162` added the deterministic `user_idea_intake_session` gate, but an
operator still had to prepare a `user_idea_raw_input` JSON artifact manually or
call the session builder directly with only `--idea-text`. That proved the
validation contract, but it was not a practical first product-facing intake
surface.

The next slice needs a small CLI wrapper that can capture raw operator intent,
workspace hints, active frame hints, event-storming hints, and accepted
clarification answers, then feed the existing session gate without inventing
missing product semantics.

## Proposal

Add `tools/user_idea_intake_interview.py` and the `make real-idea-intake` alias.

The wrapper can:

- capture `--idea-text` plus optional workspace metadata;
- capture explicit ontology/domain/context/layer/model-applicability refs;
- capture simple event-storming entries for actors, events, commands,
  constraints, policies, systems, risks, assumptions, and vocabulary questions;
- consume a matching pair of `idea_to_spec_clarification_requests` and
  `idea_to_spec_clarification_answer_set` artifacts, applying accepted
  `answer_question` / `provide_candidate_context` answers to the raw intake;
- write a local-only raw input artifact;
- run the existing `user_idea_intake_session` builder;
- write a public-safe `user_idea_intake_interview_report`.

The default raw input path is:

```text
runs/local_operator_user_idea_raw_input.json
```

The `local_operator_` prefix keeps raw idea text out of public static artifact
bundles. The report and session expose digests, readiness, findings, and
clarification counts, not the full raw idea text.

## Authority Boundary

This proposal does not grant write or execution authority.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate candidate source artifacts through SpecSpace;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

If the base input or clarification answers contain authority-expanding fields,
the wrapper marks the interview as `blocked_authority_boundary` and does not
write a prepared intake source.

## Acceptance Criteria

- A raw idea with missing context writes a local raw input artifact, a
  public-safe interview report, and an intake session with
  `needs_clarification`.
- A raw idea with complete explicit hints writes
  `runs/user_idea_intake_source.json`.
- Accepted clarification answers can fill missing active-frame and
  event-storming fields.
- Raw idea text is not published in the interview report.
- Authority-expanding input is blocked.

## Validation

- `tests/test_user_idea_intake_interview.py`
- `tests/test_user_idea_intake_session.py`
- `make real-idea-intake`
