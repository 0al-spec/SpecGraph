# Executor Analysis Report Follow-up Policy

## Draft Plan

Define the policy-only boundary after `0112` for deciding what may consume a
local analysis report review outcome.

The source input is:

```text
runs/local_operator_executor_analysis_report_review_outcome.json
```

This slice intentionally stops before building a follow-up packet. It only
declares and validates which request shape is safe enough for the next runtime
slice.

## Scope

- Add `executor_analysis_report_followup_policy`.
- Require a valid source outcome with:
  - `summary.status=ready_for_operator_review`;
  - `outcome_kind=analysis_report_review_outcome`;
  - `summary.report_kind=analysis_report`.
- Allow only the future effect:

  ```text
  analysis_report_followup_packet
  ```

- Preserve the authority boundary:
  - executor report is not authority;
  - review packet is not authority;
  - review outcome is not authority;
  - follow-up policy is not authority;
  - human/supervisor review remains required;
  - proposal draft candidate production remains forbidden;
  - executor invocation, canonical mutation, proposal mutation, patch
    application, and gap closure remain forbidden.

## Non-Scope

- Do not build the follow-up packet artifact.
- Do not create proposal draft candidates.
- Do not materialize proposal markdown.
- Do not mutate proposal registries or proposal status.
- Do not mutate canonical specs.
- Do not invoke an executor.
- Do not apply patches.
- Do not close gaps.
- Do not publish local-only executor artifacts.
- Do not change SpecSpace, Platform, Ontology, or deployment.

## Validation Intent

- Focused supervisor tests for valid ready outcomes, missing outcomes,
  forbidden effects, authority expansion, blocked outcomes, and report-kind
  spoofing.
- Proposal tracking and work-claim gates.
- `make executor-analysis-report-review-outcome` remains the current local
  source artifact producer.
- Full Python suite before merge.
