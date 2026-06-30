# 0188 Real Idea Intake Orchestration Hardening

Status: implemented.

## Problem

Proposal `0186` added the real-idea intake clarification loop, and proposal
`0187` connected ready intake sessions to the active candidate pipeline. During
manual smoke runs, one orchestration edge remained unsafe for operators:

```bash
make real-idea-intake-clarification-requests
```

The target rebuilt `real-idea-intake` as a prerequisite every time. When an
operator had already materialized a scoped intake session and only wanted to
emit clarification requests, the target could silently overwrite the session if
the same Make invocation did not repeat every raw-idea/frame argument.

This made isolated real-idea smoke runs fragile: a product-specific session
could be replaced by a generic `idea-candidate` session before clarification
requests were emitted.

## Proposal

Harden the target so it treats an existing intake session as authoritative input
by default:

```text
if USER_IDEA_INTAKE_SESSION_OUTPUT exists:
  build clarification requests from that session
else:
  run real-idea-intake first
```

Operators can still force a rebuild explicitly:

```bash
make real-idea-intake-clarification-requests REAL_IDEA_INTAKE_REFRESH=1
```

This preserves the convenience path for first-time runs while preventing
accidental session overwrite during staged smoke/debug workflows.

## Authority Boundary

This proposal does not grant write or execution authority.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate user intent;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models.

The target only changes Make orchestration around already review-only artifacts.

## Acceptance Criteria

- `make real-idea-intake-clarification-requests` preserves an existing
  `USER_IDEA_INTAKE_SESSION_OUTPUT` artifact.
- The target still creates a session when no session exists.
- `REAL_IDEA_INTAKE_REFRESH=1` explicitly restores the previous rebuild
  behavior.
- Non-ASCII raw idea text passed through
  `SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT` remains supported.
- Regression tests cover existing-session preservation and non-ASCII env input.

## Validation

- `tests/test_idea_intake_clarification_rerun.py`
- `tests/test_user_idea_intake_interview.py`
