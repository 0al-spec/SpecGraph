# Executor Report to Proposal Draft Policy

## Status

Draft proposal

## Source Material

This proposal defines the policy boundary after `0093` review packets and before
any actual proposal draft builder.

Source draft:

- `docs/archive/proposal_sources/0094_executor_report_to_proposal_draft_policy.md`

## Context

`0091` proved that a local executor can produce a contract-valid report.
`0092` defined how valid reports may be consumed without becoming authority.
`0093` made the report reviewable through a local-only review packet.

The next step is not to create a proposal draft yet. First SpecGraph must define
which review packets may be used as proposal-draft input and which authority
boundaries must remain closed.

## Goals

- Add a policy-only section:

  ```text
  executor_report_to_proposal_draft_policy
  ```

- Require the source packet:

  ```text
  runs/local_operator_executor_report_review_packet.json
  ```

- Require the source report:

  ```text
  runs/local_operator_executor_report.json
  ```

- Allow only review packets with:

  ```text
  summary.status = ready_for_review
  review_packet.review_state = ready_for_human_review
  summary.report_kind = proposal_draft
  ```

- Define the future draft candidate contract:

  ```text
  executor_report_proposal_draft_candidate
  ```

- Preserve the authority boundary:

  ```text
  executor report is not authority
  review packet is not authority
  human/supervisor review remains required
  canonical mutations are forbidden
  proposal status mutations are forbidden
  gap closure is forbidden
  patch application is forbidden
  ```

## Non-Goals

- Building proposal draft artifacts.
- Creating or editing files under `docs/proposals/` as executor output.
- Applying patches.
- Mutating canonical specs.
- Closing gaps.
- Running a new executor task.
- Adding SpecSpace UI.
- Changing Platform deploy.

## Policy Contract

The policy is declared under `tools/supervisor_executor_adapter_policy.json`:

```json
{
  "artifact_kind": "executor_report_to_proposal_draft_policy",
  "schema_version": 1,
  "source_review_packet_artifact": "runs/local_operator_executor_report_review_packet.json",
  "source_report_artifact": "runs/local_operator_executor_report.json",
  "allowed_source_packet_status": ["ready_for_review"],
  "allowed_source_review_states": ["ready_for_human_review"],
  "allowed_source_report_kinds": ["proposal_draft"],
  "consumer": "proposal_draft_builder",
  "transformation": "review_packet_to_proposal_draft_candidate",
  "requested_effects": ["proposal_draft_candidate"],
  "authority_boundary": {
    "executor_report_is_authority": false,
    "review_packet_is_authority": false,
    "human_or_supervisor_review_required": true,
    "canonical_mutations_allowed": false,
    "proposal_status_mutations_allowed": false,
    "gap_closure_allowed": false,
    "patch_application_allowed": false,
    "static_publish_of_local_report_allowed": false
  },
  "next_gap": "build_executor_report_proposal_draft_candidate"
}
```

## Important Constraint

An `analysis_report` review packet remains reviewable, but it must not become a
proposal draft candidate. Only reports that were already typed as
`proposal_draft` may enter the future draft-candidate builder.

## Acceptance

This slice is complete when:

- `executor_report_to_proposal_draft_policy` is declared;
- validators accept a valid `proposal_draft` review packet;
- validators reject an `analysis_report` review packet;
- validators reject missing review packets;
- validators reject forbidden effects such as `canonical_spec_mutation`;
- validators reject authority expansion and unexpected authority fields;
- proposal `0094` is tracked in promotion/runtime registries;
- proposal gates, focused tests, static bundle tests, and full Python suite pass.
