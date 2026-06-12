# Build Executor Report Proposal Draft Candidate

## Draft Plan

Build the first local-only proposal draft candidate artifact from a reviewed
executor report packet. This slice materializes the candidate contract from
`0094`, but it must not write proposal markdown, mutate proposal registries,
change canonical specs, close gaps, or promote the candidate automatically.

## Scope

- Add `runs/local_operator_executor_proposal_draft_candidate.json`.
- Add `make executor-proposal-draft-candidate`.
- Consume `runs/local_operator_executor_report_review_packet.json`.
- Require the source packet to satisfy
  `executor_report_to_proposal_draft_policy`.
- Allow only human-review-ready `proposal_draft` review packets.
- Preserve the boundary that executor reports and review packets are inputs,
  not authority.
- Include promotion metadata that requires explicit human promotion into the
  proposal lane.
- Exclude the local-only candidate artifact from public static publishing.

## Non-Scope

- Do not create or edit files under `docs/proposals/` as executor output.
- Do not mutate proposal registries.
- Do not change proposal status.
- Do not apply patches.
- Do not mutate canonical specs.
- Do not close gaps.
- Do not run a new executor task.
- Do not change SpecSpace or Platform.
- Do not publish local-only executor artifacts.

## Validation Intent

- Proposal gates.
- Focused supervisor tests for valid candidates and blocked source packets.
- Static bundle tests proving the candidate artifact is excluded.
- A local standalone command check.
- Full Python suite.
