# Proposal Draft Candidate Promotion Policy

## Status

Draft proposal

## Source Material

This proposal defines the promotion policy boundary after `0095` proposal draft
candidate materialization.

Source draft:

- `docs/archive/proposal_sources/0096_proposal_draft_candidate_promotion_policy.md`

## Context

`0095` added a local-only proposal draft candidate artifact:

```text
runs/local_operator_executor_proposal_draft_candidate.json
```

That candidate is reviewable, but it is not a proposal and does not have
proposal-lane authority. The next bounded step is to define the policy that
decides whether a valid candidate may become input to a future promotion packet.

## Goals

- Add a policy-only surface:

  ```text
  proposal_draft_candidate_promotion_policy
  ```

- Require a valid source candidate with:

  ```text
  summary.status = ready_for_promotion_review
  draft_kind = proposal_draft_candidate
  proposal_status = draft_candidate
  promotion.requires_human_promotion = true
  ```

- Require explicit human authorization:

  ```text
  human_authorization.approval_state = approved_for_promotion_packet
  human_authorization.promotion_packet_required = true
  ```

- Allow only a future promotion packet effect:

  ```text
  promotion_packet_candidate
  ```

- Allow only proposal source draft target paths under:

  ```text
  docs/archive/proposal_sources/
  ```

- Keep executor report and candidate output as input evidence, not authority.

## Non-Goals

- Creating a promotion packet artifact.
- Writing proposal markdown.
- Mutating proposal registries.
- Changing proposal status.
- Mutating canonical specs.
- Applying patches.
- Closing gaps.
- Running an executor.
- Adding SpecSpace or Platform behavior.

## Policy Contract

The policy accepts a request shaped like:

```json
{
  "source_candidate_artifact": "runs/local_operator_executor_proposal_draft_candidate.json",
  "consumer": "proposal_lane_operator",
  "transformation": "proposal_draft_candidate_to_promotion_packet",
  "requested_effects": ["promotion_packet_candidate"],
  "target": {
    "target_lane": "proposal_lane",
    "target_artifact_kind": "proposal_source_draft",
    "target_path": "docs/archive/proposal_sources/executor_report_proposal_draft_candidate.md"
  },
  "human_authorization": {
    "approval_state": "approved_for_promotion_packet",
    "reviewer": "human_operator",
    "reason": "Promote candidate into a future promotion packet for review.",
    "promotion_packet_required": true
  },
  "authority_boundary": {
    "candidate_is_authority": false,
    "promotion_request_is_authority": false,
    "human_or_supervisor_review_required": true,
    "writes_proposal_markdown": false,
    "writes_proposal_registry": false,
    "canonical_mutations_allowed": false,
    "proposal_status_mutations_allowed": false,
    "gap_closure_allowed": false,
    "patch_application_allowed": false,
    "static_publish_of_local_candidate_allowed": false
  }
}
```

## Forbidden Effects

The policy rejects:

```text
canonical_spec_mutation
patch_application
gap_closure
proposal_status_mutation
proposal_registry_mutation
proposal_markdown_write
static_publish_of_local_candidate
direct_candidate_to_canonical_proposal
```

## Acceptance

This slice is complete when:

- `proposal_draft_candidate_promotion_policy` is declared;
- valid source candidate plus explicit human authorization passes validation;
- missing human authorization is rejected;
- invalid candidate status is rejected;
- forbidden effects are rejected;
- authority expansion is rejected;
- unsafe target paths are rejected;
- proposal `0096` is tracked in promotion/runtime registries;
- focused validator tests, proposal gates, static bundle tests, `publish-bundle`,
  `docc-sync`, and the full Python suite pass.

## Next Gap

```text
build_proposal_draft_candidate_promotion_packet
```
