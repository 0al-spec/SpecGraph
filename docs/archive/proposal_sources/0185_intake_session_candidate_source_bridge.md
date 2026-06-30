# 0185 Intake Session Candidate Source Bridge

Status: implemented.

## Problem

Proposal `0184` added a real idea intake wrapper that can accept raw operator
idea text, explicit frame hints, event-storming hints, and accepted
clarification answers. The wrapper runs the `user_idea_intake_session` gate and
can write `runs/user_idea_intake_source.json` when the session is ready.

That proved the first real-intake input path, but downstream candidate
generation still depended on the source file being written as a side effect of
the intake wrapper. The next slice needs an explicit bridge from a ready,
public-safe intake session to the existing `user_idea_intake_source` contract.
That bridge must not publish raw idea text or treat the local raw-input artifact
as downstream authority.

## Proposal

Add `tools/intake_session_candidate_source.py` and the
`make intake-session-candidate-source` target.

The bridge reads `runs/user_idea_intake_session.json`, validates that the
session is ready, and materializes the standard:

```text
runs/user_idea_intake_source.json
```

It also writes:

```text
runs/intake_session_candidate_source_report.json
```

The session now embeds a public-safe `candidate_source_input` payload when it is
ready. The bridge uses that payload rather than the local raw input artifact.
The emitted source rewrites `source_session.source_ref` to the intake session
artifact, not to `runs/local_operator_user_idea_raw_input.json`.

## Authority Boundary

This proposal does not grant write or execution authority.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate user intent;
- mutate candidate source artifacts through SpecSpace;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

If the intake session, embedded payload, or emitted source contains
authority-expanding fields, the bridge marks the report as
`candidate_source_review_required` and does not write the source artifact.

## Acceptance Criteria

- A ready intake session can materialize `runs/user_idea_intake_source.json`
  through `make intake-session-candidate-source`.
- A not-ready session fails strict mode and removes stale source output.
- Raw idea text, raw prompt/model traces, private notes, and local operator raw
  input refs are not copied into the emitted source.
- Authority-expanding fields block source materialization.
- Unsafe privacy boundaries block source materialization.
- The emitted source can feed the existing
  `user_idea_intake_source -> idea_event_storming_intake` chain.

## Validation

- `tests/test_intake_session_candidate_source.py`
- `tests/test_user_idea_intake_session.py`
- `tests/test_user_idea_intake_interview.py`
- `make intake-session-candidate-source`
