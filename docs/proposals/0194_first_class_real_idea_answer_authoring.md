# 0194 First-Class Real Idea Answer Authoring

Status: implemented.

## Problem

After proposal `0193`, real-idea smoke continuation can preserve an intake
session, apply accepted clarification answers, and continue without requiring
operators to remember `REAL_IDEA_SMOKE_REFRESH=0`. However, operators still had
to hand-author JSON answer sets for intake clarification and repair.

That is brittle for product work:

- operators must know the internal `idea_to_spec_clarification_answer_set`
  contract;
- empty placeholder values can look plausible until a later rerun step;
- ontology and product/spec repair answers use different value shapes;
- invalid authority fields or local/raw traces can accidentally enter a hand
  authored answer file.

## Proposal

Add a first-class answer-authoring helper for real-idea smoke runs:

```bash
make real-idea-smoke-answer-template
make real-idea-smoke-validate-answers
make real-idea-smoke-materialize-answers
```

The new `tools/real_idea_answer_authoring.py` reads the current
`idea_to_spec_clarification_requests` surface for an isolated
`REAL_IDEA_SMOKE_RUN_DIR` and produces:

```text
real_idea_answer_template.json
real_idea_answer_authoring_report.json
real_idea_answer_set.json
```

The template turns each request into an operator-editable target with:

- request id;
- target type;
- accepted actions;
- typed value templates per action;
- required fields;
- evidence refs;
- explicit false authority boundary.

Filled templates are validated before materialization. The validator reuses the
existing `idea_to_spec_clarification_answers` contract and adds first-class
guards for required typed values, `may_*` authority expansion, raw trace fields,
and private/local text markers.

Materialization does not introduce a new downstream protocol. It writes the
existing compatible artifacts:

- for intake clarification, `idea_intake_clarification_answers`,
  `idea_intake_answer_rerun_input`, `clarified_user_idea_intake_session`, and
  `idea_intake_clarification_rerun_report`;
- for repair, `idea_to_spec_clarification_answers`,
  `product_ontology_gap_review_decisions`, and
  `idea_to_spec_answer_rerun_input`.

## Authority Boundary

This proposal only adds operator answer authoring, validation, and compatible
review-only materialization.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate raw user intent;
- mutate candidate source artifacts;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms globally;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models.

## Acceptance Criteria

- Operators can generate a typed answer template from the current real-idea
  smoke run directory.
- Filled templates can be validated without hand-authoring the low-level answer
  set contract from scratch.
- Empty required typed fields are blocked before rerun.
- Unknown or truthy `may_*` authority fields are blocked.
- Raw/local/private traces are blocked from answer inputs and reports.
- Intake answer materialization writes the existing clarification rerun
  artifacts and leaves raw idea text local-only.
- Repair answer materialization writes the existing answer, ontology decision,
  and rerun input artifacts.
- `REAL_IDEA_SMOKE_RUN_DIR=runs` remains rejected.
- Existing downstream rerun, repaired handoff, maturity, Platform, and Git
  Service flows do not require a new protocol.

## Validation

- `tests/test_real_idea_answer_authoring.py`
- `make real-idea-smoke-answer-template`
- `make real-idea-smoke-validate-answers`
- `make real-idea-smoke-materialize-answers`
