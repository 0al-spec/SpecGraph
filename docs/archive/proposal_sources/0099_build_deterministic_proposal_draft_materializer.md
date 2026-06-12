# Build Deterministic Proposal Draft Materializer

## Draft Plan

Implement the bounded local materializer defined by `0098`. The materializer
consumes a valid local proposal promotion packet, validates the deterministic
materialization request, writes exactly one proposal source draft under
`docs/archive/proposal_sources/`, and records a local-only materialization
report.

## Scope

- Add `runs/local_operator_executor_proposal_materialization_report.json`.
- Add `make executor-proposal-source-materialize`.
- Consume `runs/local_operator_executor_proposal_promotion_packet.json`.
- Require `deterministic_proposal_draft_materialization_policy` validation.
- Write only the requested `docs/archive/proposal_sources/...` target.
- Reject existing target paths.
- Fail closed when git mutation scope cannot be proven.
- Exclude the report from public static publishing.
- Do not write `docs/proposals/`.
- Do not mutate proposal registries or proposal status.
- Do not mutate canonical specs, apply patches, close gaps, or invoke executors.

## Validation Intent

- focused supervisor tests for successful source draft materialization
- focused tests for existing target, invalid source packet, and mutation guard
- report contract validation tests
- standalone CLI/Make target coverage
- static bundle exclusion tests
- proposal tracking gates
- publish bundle safety gate
- DocC sync
- full Python suite
