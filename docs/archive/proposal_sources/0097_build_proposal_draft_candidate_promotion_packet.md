# Build Proposal Draft Candidate Promotion Packet

## Draft Plan

Add the local-only promotion packet that consumes a valid executor proposal
draft candidate and the 0096 promotion policy. The packet records authorization,
target provenance, and authority boundaries for a later deterministic proposal
materialization step, without writing proposal markdown or mutating proposal
registries.

## Scope

- Add `runs/local_operator_executor_proposal_promotion_packet.json`.
- Add `make executor-proposal-promotion-packet`.
- Consume `runs/local_operator_executor_proposal_draft_candidate.json`.
- Reuse `proposal_draft_candidate_promotion_policy` validation.
- Record the safe target proposal source path candidate.
- Record human/supervisor authorization metadata.
- Preserve candidate-as-input authority boundaries.
- Exclude the local-only packet from public static publish.
- Do not write `docs/proposals/`.
- Do not write `docs/archive/proposal_sources/`.
- Do not mutate proposal registries or proposal status.
- Do not mutate canonical specs or apply patches.

## Validation Intent

- focused supervisor tests for ready, blocked, unsafe, and standalone paths
- static bundle exclusion test
- proposal tracking gates
- full Python suite
- publish bundle safety gate
