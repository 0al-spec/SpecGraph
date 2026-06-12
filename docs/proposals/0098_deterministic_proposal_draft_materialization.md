# Deterministic Proposal Draft Materialization

## Status

Draft proposal

## Source Material

This proposal defines the deterministic materialization policy boundary after
`0097` promotion packet materialization.

Source draft:

- `docs/archive/proposal_sources/0098_deterministic_proposal_draft_materialization.md`

## Context

`0097` added a local-only promotion packet:

```text
runs/local_operator_executor_proposal_promotion_packet.json
```

That packet records a reviewed proposal draft candidate, target provenance, and
human authorization metadata, but it intentionally does not write proposal
markdown or mutate proposal registries.

The next bounded step is to define the policy that decides whether a valid
promotion packet may become input to a future deterministic proposal source
draft materializer. This slice still does not implement the materializer.

## Goals

- Add a policy-only surface:

  ```text
  deterministic_proposal_draft_materialization_policy
  ```

- Require a valid source promotion packet with:

  ```text
  artifact_kind = proposal_draft_candidate_promotion_packet
  local_only = true
  summary.status = ready_for_materialization_review
  promotion_packet.promotion_state = ready_for_materialization_review
  ```

- Require explicit human authorization:

  ```text
  human_authorization.approval_state = approved_for_deterministic_materialization
  human_authorization.materializer_required = true
  ```

- Allow only the future materialization effect:

  ```text
  proposal_source_draft_materialization
  ```

- Require target paths under:

  ```text
  docs/archive/proposal_sources/
  ```

- Require the target `proposal_id` to match the current deterministic allocator:

  ```bash
  make proposal-id
  ```

- Keep the promotion packet as input evidence, not proposal-lane authority.

## Non-Goals

- Building the deterministic materializer.
- Writing `docs/archive/proposal_sources/...`.
- Writing `docs/proposals/...`.
- Mutating proposal registries.
- Mutating proposal status.
- Mutating canonical specs.
- Applying patches.
- Closing gaps.
- Running an executor.
- Publishing local materialization state.
- Adding SpecSpace or Platform behavior.

## Policy Contract

The policy accepts a request shaped like:

```json
{
  "source_promotion_packet_artifact": "runs/local_operator_executor_proposal_promotion_packet.json",
  "materializer": "deterministic_proposal_draft_materializer",
  "transformation": "promotion_packet_to_proposal_source_draft_materialization",
  "requested_effects": ["proposal_source_draft_materialization"],
  "target": {
    "target_lane": "proposal_lane",
    "target_artifact_kind": "proposal_source_draft",
    "proposal_id": "0099",
    "target_path": "docs/archive/proposal_sources/0099_executor_report_proposal_draft_materialization.md"
  },
  "human_authorization": {
    "approval_state": "approved_for_deterministic_materialization",
    "reviewer": "human_operator",
    "reason": "Allow deterministic materialization from the reviewed local promotion packet.",
    "materializer_required": true
  },
  "authority_boundary": {
    "promotion_packet_is_authority": false,
    "materialization_request_is_authority": false,
    "deterministic_materialization_only": true,
    "executor_invocation_allowed": false,
    "policy_request_writes_proposal_files": false,
    "writes_proposal_registry": false,
    "canonical_mutations_allowed": false,
    "proposal_status_mutations_allowed": false,
    "gap_closure_allowed": false,
    "patch_application_allowed": false,
    "static_publish_of_local_materialization_allowed": false
  }
}
```

The shown `proposal_id` is illustrative. The validator checks the live
deterministic proposal allocator and rejects stale or skipped ids.

## Forbidden Effects

The policy rejects:

```text
canonical_spec_mutation
patch_application
gap_closure
proposal_status_mutation
proposal_registry_mutation
executor_invocation
static_publish_of_local_materialization
direct_candidate_to_canonical_proposal
proposal_markdown_write
```

## Acceptance

This slice is complete when:

- `deterministic_proposal_draft_materialization_policy` is declared;
- valid source promotion packet plus explicit authorization passes validation;
- blocked or invalid promotion packets are rejected;
- missing human authorization is rejected;
- forbidden effects are rejected with stable effect indices;
- authority expansion is rejected;
- unsafe target paths and registry targets are rejected;
- stale or skipped proposal ids are rejected;
- proposal `0098` is tracked in promotion/runtime registries;
- focused validator tests, proposal gates, `publish-bundle`, `docc-sync`, and
  the full Python suite pass.

## Next Gap

```text
build_deterministic_proposal_draft_materializer
```
