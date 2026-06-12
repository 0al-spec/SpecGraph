# Proposal Draft Candidate Promotion Policy

## Draft Plan

Define the policy boundary for promoting a local-only executor proposal draft
candidate into a future proposal-lane promotion packet.

## Scope

- Add `proposal_draft_candidate_promotion_policy`.
- Validate only policy requests; do not materialize a promotion packet yet.
- Require a valid `runs/local_operator_executor_proposal_draft_candidate.json`
  source candidate.
- Require explicit human authorization.
- Allow only a future promotion packet candidate effect.
- Allow only proposal source draft target paths under
  `docs/archive/proposal_sources/`.
- Reject direct proposal markdown writes, proposal registry mutation, proposal
  status mutation, canonical spec mutation, patch application, and gap closure.
- Do not run an executor.
- Do not create proposal markdown.
- Do not mutate proposal registries.
- Do not mutate canonical specs.

## Validation Intent

- focused promotion policy validator tests
- proposal tracking gates
- static bundle regression coverage remains green
- full Python suite
