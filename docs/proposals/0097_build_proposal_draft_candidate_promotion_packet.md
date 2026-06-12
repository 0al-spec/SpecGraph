# Build Proposal Draft Candidate Promotion Packet

## Status

Draft proposal

## Source Material

This proposal implements the bounded runtime slice after `0096` promotion
policy.

Source draft:

- `docs/archive/proposal_sources/0097_build_proposal_draft_candidate_promotion_packet.md`

## Context

`0095` materialized a local-only proposal draft candidate from a valid executor
report review packet. `0096` then defined the policy boundary for promoting
that candidate into a later proposal-lane step.

The next step is not to write proposal markdown. It is to build a local-only
promotion packet that records authorization, target provenance, and authority
boundaries for a future deterministic materialization step.

## Goals

- Add a local-only promotion packet artifact:

  ```text
  runs/local_operator_executor_proposal_promotion_packet.json
  ```

- Add a Makefile shortcut:

  ```bash
  make executor-proposal-promotion-packet
  ```

- Consume:

  ```text
  runs/local_operator_executor_proposal_draft_candidate.json
  proposal_draft_candidate_promotion_policy
  ```

- Reuse the 0096 promotion request validator.
- Record the safe target proposal source path candidate.
- Record human/supervisor authorization metadata.
- Preserve the candidate-as-input authority boundary.
- Keep the packet out of public static publish.

## Non-Goals

- Writing `docs/proposals/...`.
- Writing `docs/archive/proposal_sources/...`.
- Mutating proposal registries.
- Mutating proposal status.
- Closing gaps.
- Applying patches.
- Mutating canonical specs.
- Running a new executor task.
- Adding SpecSpace or Platform behavior.

## Artifact Contract

The packet is report-only and local-only:

```json
{
  "artifact_kind": "proposal_draft_candidate_promotion_packet",
  "schema_version": 1,
  "local_only": true,
  "source_candidate_artifact": "runs/local_operator_executor_proposal_draft_candidate.json",
  "summary": {
    "status": "ready_for_materialization_review",
    "source_candidate_status": "ready_for_promotion_review",
    "target_path": "docs/archive/proposal_sources/executor_report_proposal_draft_candidate.md",
    "next_gap": "define_deterministic_proposal_draft_materialization"
  },
  "promotion_packet": {
    "packet_kind": "proposal_draft_candidate_promotion_packet",
    "promotion_state": "ready_for_materialization_review",
    "human_review_required": true,
    "materializes_proposal": false,
    "writes_proposal_markdown": false,
    "writes_proposal_registry": false,
    "canonical_mutations_allowed": false
  }
}
```

`ready_for_materialization_review` means the packet can be reviewed by a later
deterministic materialization policy. It does not write the proposal lane and
does not grant the executor or the candidate direct proposal authority.

## Statuses

```text
ready_for_materialization_review
blocked_missing_candidate
blocked_invalid_candidate
blocked_promotion_policy
blocked_authority_boundary
blocked_privacy_boundary
blocked_policy_contract
```

## Acceptance

This slice is complete when:

- `make executor-proposal-promotion-packet` writes
  `runs/local_operator_executor_proposal_promotion_packet.json`;
- a valid candidate and valid promotion request produce
  `ready_for_materialization_review`;
- missing/invalid candidates are blocked;
- missing approval, authority expansion, and unsafe target paths are rejected;
- the artifact contains no raw logs, secrets, or machine-local paths;
- the artifact is excluded from public static publish;
- proposal gates, focused tests, static bundle tests, publish bundle, and the
  full Python suite pass.

## Next Gap

```text
define_deterministic_proposal_draft_materialization
```
