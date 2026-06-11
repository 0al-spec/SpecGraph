# Build Executor Report Review Packet

## Draft Plan

Build the first local-only review packet from a valid bounded executor report
and the executor report consumption policy. The packet must make the report
reviewable by a human/operator or supervisor process without turning report
findings into canonical facts.

## Scope

- Add `runs/local_operator_executor_report_review_packet.json`.
- Add `make executor-report-review-packet`.
- Consume `runs/local_operator_executor_report.json`.
- Validate the source report with the existing executor report contract.
- Validate the review-packet consumption request with
  `executor_report_consumption_policy`.
- Preserve the authority boundary: report is input/evidence, not authority.
- Require human/operator review.
- Do not create proposals.
- Do not apply patches.
- Do not mutate canonical specs.
- Do not publish the local review packet in the static bundle.

## Validation Intent

- `make executor-report-review-packet`
- focused executor report review packet tests
- static bundle exclusion test
- proposal tracking gates
- full Python suite
