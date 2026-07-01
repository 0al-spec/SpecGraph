# 0192 Real Idea Smoke Iteration Isolation

Status: implemented.

## Problem

Real idea smoke runs became usable for live product-idea testing, but two
iteration hazards remained:

1. Reusing the same smoke run directory could preserve an earlier
   `user_idea_intake_session.json`. A later run with new operator-provided
   clarification answers or a different ready idea could silently continue from
   the old session unless the operator manually deleted derived artifacts.
2. Building Idea Maturity for a custom smoke run directory required many manual
   path overrides. If post-approval Platform/Git artifacts were not explicitly
   redirected to an absent directory, the report could accidentally consume
   stale canonical `runs/*.json` artifacts from another flow and overstate the
   lifecycle stage.

Both issues are orchestration hazards, not product-modeling decisions.

## Proposal

Harden the real-idea smoke orchestration layer:

- `make real-idea-smoke` refreshes managed derived outputs in
  `REAL_IDEA_SMOKE_RUN_DIR` by default before invoking the real-intake
  active-candidate chain.
- `REAL_IDEA_SMOKE_REFRESH=0` preserves the old reuse behavior for operators who
  intentionally want to keep existing managed outputs.
- Only known wrapper-owned derived outputs are cleared. Operator-authored answer
  input files remain untouched, but generated answer/rerun/repair/maturity
  artifacts from prior iterations are cleared.
- Add `make real-idea-smoke-idea-maturity`, which builds and validates Idea
  Maturity using artifacts from `REAL_IDEA_SMOKE_RUN_DIR`.
- The new maturity target routes optional post-approval Platform/Git artifacts
  to `REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR` by default, preventing accidental
  fallback to canonical `runs/*.json` from unrelated flows.
- The default absent-dir under the run directory is also cleared during smoke
  refresh so stale synthetic post-approval files cannot survive a new run.

## Authority Boundary

This proposal only changes local smoke orchestration and telemetry path routing.

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

- Re-running `make real-idea-smoke` in the same run directory with a different
  ready idea produces a candidate for the new idea.
- Operators can opt out with `REAL_IDEA_SMOKE_REFRESH=0`.
- Managed output cleanup does not remove operator-authored repair/clarification
  answer inputs, but operators must update or delete those inputs before using
  them with a different idea.
- `make real-idea-smoke-idea-maturity` threads all core and repaired SpecGraph
  inputs through `REAL_IDEA_SMOKE_RUN_DIR`.
- The smoke maturity target sends optional post-approval artifacts to
  `REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR` by default, and the default absent-dir
  is cleared during smoke refresh.
- Idea Maturity for custom smoke runs no longer accidentally consumes default
  `runs/candidate_approval_decision.json`, promotion request, promotion
  execution, review-status, or read-model publication artifacts.

## Validation

- `tests/test_idea_intake_clarification_rerun.py`
- `tests/test_idea_maturity_metrics_report.py`
