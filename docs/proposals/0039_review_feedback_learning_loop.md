# 0039. Review Feedback Learning Loop

## Status

Accepted for implementation.

## Context

SpecGraph already treats many derived surfaces as feedback loops:

- trace/evidence surfaces expose implementation and runtime gaps;
- dashboard/backlog projections make graph gaps visible;
- external-consumer feedback surfaces prevent downstream state from becoming
  invisible process knowledge.

Pull request review feedback is another high-signal feedback source. Today it
can be handled as a local patch: reply, resolve the thread, and move on. That
fixes the symptom but does not reliably improve the process that allowed the
defect.

Recent review feedback on the Implementation Work layer showed this pattern:

- per-target data was not scoped tightly enough for multi-target work items;
- loaded artifact sections were not fully type-checked before `.get()` access;
- CLI diagnostics were semantically imprecise;
- runtime behavior drifted from declarative policy flags.

Those comments should become process evidence.

## Problem

If review comments do not feed back into root-cause and prevention surfaces,
SpecGraph loses the opportunity to learn from reviewers.

The missing loop is:

```text
review comment
-> fix
-> root cause classification
-> prevention action
-> verification
-> durable rule/test/policy/accepted-risk record
```

Without that loop:

- repeated defect classes remain invisible;
- review closure can mean "patched" rather than "prevented";
- policy/runtime drift can recur in nearby code;
- reviewer knowledge stays trapped inside GitHub threads.

## Proposal

Introduce a Review Feedback Learning Loop.

Every actionable review thread handled for SpecGraph should be classified
before closure:

- what symptom was reported;
- what root cause allowed it;
- what prevention action was added or explicitly deferred;
- what verification proves the fix and prevention path.

The first slice added:

- `tools/review_feedback_policy.json`
- a repository rule in `AGENTS.md`
- tests that keep the policy and operational rule present

The runtime realization adds:

```text
runs/review_feedback_index.json
```

That artifact summarizes explicit review-feedback records, root causes,
prevention actions, verification status, and recurring defect families.

## Required Closure Fields

For each actionable review thread, the handling record should include:

- `source_thread_url`
- `reviewer`
- `review_comment_summary`
- `fix_summary`
- `root_cause_class`
- `prevention_action`
- `verification`
- `residual_risk`

The PR thread reply should be concise, but it should still make the prevention
path visible when one exists.

## Root Cause Vocabulary

Initial root cause classes:

- `scope_isolation_gap`
- `artifact_contract_validation_gap`
- `policy_runtime_drift`
- `diagnostic_wording_gap`
- `test_coverage_gap`
- `viewer_contract_gap`
- `process_rule_gap`
- `accepted_design_tradeoff`

## Prevention Actions

Initial prevention action types:

- `regression_test_added`
- `validator_added`
- `policy_rule_added`
- `agent_instruction_added`
- `viewer_contract_updated`
- `documentation_rule_added`
- `accepted_risk_recorded`

At least one `prevention_action` value should be attached. If prevention is
intentionally deferred, use `accepted_risk_recorded` as the prevention-action
value and record the residual risk.

## Boundaries

This proposal does not require:

- automatic GitHub review parsing;
- automatic thread resolution;
- automatic reviewer replacement;
- automatic canonical spec mutation;
- a permanent markdown task queue.

The first implementation is process and policy. Runtime indexing can follow
once the vocabulary proves stable.

## Runtime Realization Path

Phase 1:

- Add this proposal.
- Add `tools/review_feedback_policy.json`.
- Add an `AGENTS.md` operational rule.
- Add tests for the policy/operational contract.

Phase 2:

- Add `runs/review_feedback_index.json`.
- Add a standalone builder that consumes explicit tracked review-feedback
  records.
- Group entries by root cause, prevention action, verification status, and
  next gap.

Phase 3:

- Surface review-feedback gaps in dashboard/backlog projection.
- Use recurring root-cause groups to propose validators, tests, or process
  rules.

## Acceptance Criteria

- Review-thread fixes must no longer be treated as symptom patches only.
- The repo has a stable policy vocabulary for root causes and prevention
  actions.
- Review closure requires a prevention action value; accepted risk is recorded
  explicitly through the `accepted_risk_recorded` prevention-action value.
- Future runtime work can derive review-feedback indexes without redefining the
  process semantics.
