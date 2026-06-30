# 0186 Real Idea Intake Clarification Loop

Status: implemented.

## Problem

Proposals `0184` and `0185` made real idea intake usable from a raw operator idea:
the wrapper can capture local-only raw text and the bridge can materialize a
public-safe `user_idea_intake_source` from a ready intake session.

The missing piece was the controlled path for under-specified ideas. A raw idea
can legitimately produce `needs_clarification`, but operators need a bounded
loop that asks typed intake questions, validates accepted answers, applies them
to a clarified intake session, and only then allows the candidate-source bridge.

## Proposal

Add a deterministic, review-only intake clarification loop around the existing
intake session and clarification-answer contracts.

The loop uses the existing `idea_to_spec_clarification_requests` and
`idea_to_spec_clarification_answers` contracts, but gives real-intake flows their
own run artifacts and Make targets:

```text
runs/idea_intake_clarification_requests.json
runs/idea_intake_clarification_answers.json
runs/idea_intake_answer_rerun_input.json
runs/clarified_user_idea_intake_session.json
runs/idea_intake_clarification_rerun_report.json
```

The main new tool is:

```text
tools/idea_intake_clarification_rerun.py
```

It validates an `idea_to_spec_clarification_answer_set`, writes a public-safe
`idea_intake_answer_rerun_input`, applies accepted intake answers through the
existing `user_idea_intake_interview` wrapper, and emits a clarified intake
session plus a rerun report.

The bridge now supports an optional fallback session. This enables:

```bash
make real-idea-intake-ready-candidate-source
```

to prefer `runs/clarified_user_idea_intake_session.json` when present and fall
back to `runs/user_idea_intake_session.json` otherwise.

## Authority Boundary

This proposal does not grant write or execution authority.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- silently mutate user intent;
- mutate candidate source artifacts through SpecSpace;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

Raw idea text remains local-only in `local_operator_*` artifacts. Public rerun
reports carry source refs, answer target refs, value types, digests, readiness,
and findings, not the raw operator prompt.

## Acceptance Criteria

- `make real-idea-intake-clarification-requests` emits intake-only
  clarification requests from an under-specified real intake session.
- `make real-idea-intake-clarification-answers` validates an operator answer set
  against those request ids.
- `make real-idea-intake-clarification-rerun` writes
  `runs/idea_intake_answer_rerun_input.json` and
  `runs/clarified_user_idea_intake_session.json`.
- A complete accepted answer set can make the clarified session ready for
  candidate source materialization.
- Incomplete answers fail strict mode and do not write a clarified source.
- `make real-idea-intake-ready-candidate-source` prefers the clarified session
  when it exists, but keeps the original session as a fallback.
- Raw idea text and local raw-input refs are not published in public-safe
  reports.

## Validation

- `tests/test_idea_intake_clarification_rerun.py`
- `tests/test_user_idea_intake_interview.py`
- `tests/test_intake_session_candidate_source.py`
- `tests/test_idea_to_spec_clarification_requests.py`
- `tests/test_idea_to_spec_clarification_answers.py`
- `make real-idea-intake-clarification-rerun`
- `make real-idea-intake-ready-candidate-source`
