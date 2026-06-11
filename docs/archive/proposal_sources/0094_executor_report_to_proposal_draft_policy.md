# Executor Report to Proposal Draft Policy

## Draft Plan

Define the policy boundary for turning a reviewed local executor report packet
into a future proposal draft candidate. This is a policy-only slice: it must not
build the draft candidate yet, run a new executor task, mutate canonical specs,
or change proposal status.

## Scope

- Add `executor_report_to_proposal_draft_policy`.
- Require `runs/local_operator_executor_report_review_packet.json` as the source
  review packet.
- Allow only source packets with `summary.status=ready_for_review` and
  `review_packet.review_state=ready_for_human_review`.
- Allow only review packets whose `summary.report_kind` is `proposal_draft`.
- Define the future `executor_report_proposal_draft_candidate` contract.
- Preserve the authority boundary:
  - executor report is not authority;
  - review packet is not authority;
  - human or supervisor review remains required;
  - canonical mutations are forbidden;
  - proposal status mutations are forbidden;
  - gap closure and patch application are forbidden.
- Add validators and focused tests.

## Non-Scope

- Do not create proposal draft artifacts.
- Do not run Codex or another executor.
- Do not write patches.
- Do not mutate canonical specs.
- Do not close gaps.
- Do not change SpecSpace or Platform.
- Do not publish local-only executor artifacts.

## Validation Intent

- Proposal gates.
- Focused supervisor tests for accepted and rejected proposal-draft policy
  requests.
- Static bundle remains unchanged.
- Full Python suite.
