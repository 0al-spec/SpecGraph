# Build Executor Report Proposal Draft Candidate

## Status

Draft proposal

## Source Material

This proposal implements the local-only proposal draft candidate artifact
defined by `0094`.

Source draft:

- `docs/archive/proposal_sources/0095_build_executor_report_proposal_draft_candidate.md`

## Context

`0091` proved that a local executor can produce a contract-valid report.
`0092` defined how such reports may be consumed. `0093` wrapped a valid report
in a human-review-ready review packet. `0094` then defined the policy boundary
for when a review packet may become proposal-draft input.

The next bounded step is to materialize a candidate artifact from that policy.
The candidate is still not a proposal. It is a local-only review artifact that
may later be promoted by a separate human/supervisor-controlled policy.

## Goals

- Add a local-only artifact:

  ```text
  runs/local_operator_executor_proposal_draft_candidate.json
  ```

- Add a Makefile shortcut:

  ```bash
  make executor-proposal-draft-candidate
  ```

- Consume `runs/local_operator_executor_report_review_packet.json`.
- Validate the source packet with
  `executor_report_to_proposal_draft_policy`.
- Require source packets to be:

  ```text
  summary.status = ready_for_review
  review_packet.review_state = ready_for_human_review
  summary.report_kind = proposal_draft
  ```

- Emit a candidate with:

  ```text
  artifact_kind = executor_report_proposal_draft_candidate
  local_only = true
  draft_kind = proposal_draft_candidate
  proposal_status = draft_candidate
  promotion.requires_human_promotion = true
  promotion.target_lane = proposal_lane
  ```

- Preserve the closed authority boundary:

  ```text
  executor report is not authority
  review packet is not authority
  canonical mutations are forbidden
  proposal status mutations are forbidden
  patch application is forbidden
  gap closure is forbidden
  static publication is forbidden
  ```

## Non-Goals

- Writing proposal markdown.
- Mutating proposal registries.
- Changing proposal status.
- Applying patches.
- Mutating canonical specs.
- Closing gaps.
- Running a new executor task.
- Publishing local-only artifacts to `specgraph.tech`.
- Adding SpecSpace UI or Platform deploy behavior.

## Artifact Contract

The draft candidate is a local-only review artifact:

```json
{
  "artifact_kind": "executor_report_proposal_draft_candidate",
  "schema_version": 1,
  "local_only": true,
  "source_review_packet_artifact": "runs/local_operator_executor_report_review_packet.json",
  "source_report_artifact": "runs/local_operator_executor_report.json",
  "draft_kind": "proposal_draft_candidate",
  "proposal_status": "draft_candidate",
  "promotion": {
    "requires_human_promotion": true,
    "target_lane": "proposal_lane",
    "canonical_mutations_allowed": false,
    "proposal_status_mutations_allowed": false
  },
  "summary": {
    "status": "ready_for_promotion_review",
    "next_gap": "define_proposal_draft_candidate_promotion_policy"
  }
}
```

## Statuses

The candidate status values are:

```text
ready_for_promotion_review
blocked_missing_review_packet
blocked_invalid_review_packet
blocked_proposal_draft_policy
blocked_authority_boundary
blocked_privacy_boundary
blocked_policy_contract
```

`ready_for_promotion_review` means only that a local-only candidate can be
reviewed for possible promotion. It does not write a proposal, change proposal
status, mutate canonical specs, apply patches, or close gaps.

## Acceptance

This slice is complete when:

- `make executor-proposal-draft-candidate` writes
  `runs/local_operator_executor_proposal_draft_candidate.json`;
- valid `proposal_draft` review packets produce
  `ready_for_promotion_review`;
- missing, invalid, or `analysis_report` review packets block the candidate;
- authority expansion and unsafe local payloads are rejected;
- the static bundle excludes
  `runs/local_operator_executor_proposal_draft_candidate.json`;
- proposal `0095` is tracked in promotion/runtime registries;
- proposal gates, focused tests, static bundle tests, `make publish-bundle`,
  and the full Python suite pass.
