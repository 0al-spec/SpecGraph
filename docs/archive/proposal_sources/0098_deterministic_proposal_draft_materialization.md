# Deterministic Proposal Draft Materialization

## Draft Plan

Define the policy boundary for a future deterministic proposal source draft
materializer. The policy consumes a valid local promotion packet from `0097`,
requires explicit human authorization, allocates the next proposal id
deterministically, and allows only a future proposal source draft
materialization request.

## Scope

- Add `deterministic_proposal_draft_materialization_policy`.
- Consume `runs/local_operator_executor_proposal_promotion_packet.json`.
- Require source packet status `ready_for_materialization_review`.
- Require target paths under `docs/archive/proposal_sources/`.
- Require the current `make proposal-id` next proposal id.
- Reject executor invocation.
- Reject direct `docs/proposals/` writes.
- Reject proposal registry and proposal status mutation.
- Reject canonical mutation, patch application, and gap closure.
- Do not build the materializer in this slice.
- Do not write proposal markdown in this slice.

## Validation Intent

- focused supervisor tests for valid packet/request acceptance
- focused tests for missing approval, blocked packet, forbidden effects,
  authority expansion, unsafe targets, registry targets, and non-next ids
- proposal tracking gates
- publish bundle safety gate
- DocC sync
- full Python suite
