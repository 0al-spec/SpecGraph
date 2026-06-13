# Executor Analysis Report Consumption Policy

## Draft Plan

Define the policy boundary for consuming human-review-ready `analysis_report`
executor review packets. This is a policy-only slice: it must not build the
analysis review outcome yet, convert analysis reports into proposal drafts, run
a new executor task, mutate canonical specs, or change proposal status.

## Scope

- Add `executor_analysis_report_consumption_policy`.
- Require `runs/local_operator_executor_report_review_packet.json` as the source
  review packet.
- Require `runs/local_operator_executor_report.json` as the source report.
- Allow only source packets with `summary.status=ready_for_review` and
  `review_packet.review_state=ready_for_human_review`.
- Allow only review packets whose `summary.report_kind` is `analysis_report`.
- Route ready analysis packets to
  `build_executor_analysis_report_review_outcome`.
- Preserve the authority boundary:
  - executor report is not authority;
  - review packet is not authority;
  - human or supervisor review remains required;
  - canonical mutations are forbidden;
  - proposal status mutations are forbidden;
  - gap closure and patch application are forbidden;
  - proposal draft candidate production is forbidden.
- Add validators and focused tests.
- Keep `proposal_draft` review packets on the existing proposal-draft policy
  path.

## Non-Scope

- Do not create analysis review outcome artifacts.
- Do not convert analysis reports into proposal draft candidates.
- Do not run Codex or another executor.
- Do not write patches.
- Do not mutate canonical specs.
- Do not close gaps.
- Do not change SpecSpace or Platform.
- Do not publish local-only executor artifacts.

## Validation Intent

- Proposal gates.
- Focused supervisor tests for accepted and rejected analysis-report policy
  requests.
- Focused routing test proving `proposal_draft` review packets keep their
  existing next gap.
- Static bundle remains unchanged.
- Full Python suite.
