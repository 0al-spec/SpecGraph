# 0193 Real Idea Smoke Session Continuation

Status: implemented.

## Problem

After proposal `0192`, `make real-idea-smoke` safely refreshes managed outputs
inside a smoke run directory. That made iteration safer, but it left one
operator friction point: when a real idea stops at `needs_clarification`, the
operator must manually remember to preserve the existing intake session while
applying answers and continuing the smoke.

The old continuation path required implicit knowledge of refresh semantics:

```bash
make real-idea-smoke REAL_IDEA_SMOKE_RUN_DIR=runs/<id>
make real-idea-intake-clarification-rerun ...
REAL_IDEA_SMOKE_REFRESH=0 make real-idea-smoke REAL_IDEA_SMOKE_RUN_DIR=runs/<id>
```

That is too easy to misuse. A wrong refresh can delete the session that needs
clarification; a wrong preserve can reuse stale downstream artifacts.

## Proposal

Add an explicit session-aware continuation target:

```bash
make real-idea-smoke-continue \
  REAL_IDEA_SMOKE_RUN_DIR=runs/<id> \
  REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_INPUT=<json>
```

The continuation target preserves intake/session state but clears downstream
candidate, repair, repaired handoff, and maturity outputs before continuing.

The smoke wrapper now emits:

```text
real_idea_smoke_session_state_report.json
```

The report records:

- selected original or clarified intake session;
- review state;
- whether a clarification answer input exists;
- continuation path;
- blockers;
- next safe action;
- explicit authority and privacy boundaries.

If the run directory has a `needs_clarification` intake session and no answer
set is supplied, the target builds the clarification request surface, writes a
blocked session-state report, and exits non-zero with a concrete next action.

If a matching answer set is supplied, the target runs the existing
clarification-rerun path, materializes a clarified intake session, and then
continues through the existing active-candidate pipeline.

If a clarified intake session is already present, the target uses it directly.

## Authority Boundary

This proposal only changes local smoke orchestration and report-only telemetry.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models.

## Acceptance Criteria

- `make real-idea-smoke-continue` preserves intake/session state while clearing
  downstream generated outputs.
- `needs_clarification` without answer input writes
  `real_idea_smoke_session_state_report.json` with a blocked status and next
  action.
- `needs_clarification` with an accepted answer set produces a clarified intake
  session and continues to active-candidate generation without requiring
  `REAL_IDEA_SMOKE_REFRESH=0`.
- A stale active candidate from an earlier attempt is removed before
  continuation.
- `REAL_IDEA_SMOKE_RUN_DIR=runs` remains rejected.
- Raw idea text remains local-only and is not published in continuation reports.

## Validation

- `tests/test_idea_intake_clarification_rerun.py`
