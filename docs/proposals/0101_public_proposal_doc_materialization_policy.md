# Public Proposal Doc Materialization Policy

## Status

Draft proposal

## Source Material

This proposal defines the public proposal document materialization policy after
`0099` source draft materialization.

Source draft:

- `docs/archive/proposal_sources/0101_public_proposal_doc_materialization_policy.md`

## Context

`0099` added a local-only deterministic materializer that writes a reviewed
proposal source draft under:

```text
docs/archive/proposal_sources/
```

That source draft is durable input material, not a public proposal document.
The next bounded step is to define the policy for turning a valid source
materialization report into a future `docs/proposals/...` materialization
request. This slice still does not implement the public proposal doc writer.

## Goals

- Add a policy-only surface:

  ```text
  public_proposal_doc_materialization_policy
  ```

- Require a valid source materialization report:

  ```text
  runs/local_operator_executor_proposal_materialization_report.json
  ```

- Require:

  ```text
  artifact_kind = proposal_source_draft_materialization_report
  local_only = true
  summary.status = materialized_source_draft
  summary.source_draft_written = true
  ```

- Require explicit human authorization:

  ```text
  human_authorization.approval_state = approved_for_public_proposal_doc_materialization
  human_authorization.materializer_required = true
  human_authorization.source_draft_review_required = true
  ```

- Allow only the future materialization effect:

  ```text
  public_proposal_doc_materialization
  ```

- Require target paths under:

  ```text
  docs/proposals/
  ```

- Require the public proposal target filename to match the source draft
  filename under `docs/archive/proposal_sources/`.
- Require the target `proposal_id` to match both the source report and current
  deterministic allocator:

  ```bash
  make proposal-id
  ```

## Non-Goals

- Building the public proposal doc materializer.
- Writing `docs/proposals/...`.
- Updating `tools/proposal_promotion_registry.json`.
- Updating `tools/proposal_runtime_registry.json` from generated output.
- Changing proposal status.
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
  "source_materialization_report_artifact": "runs/local_operator_executor_proposal_materialization_report.json",
  "materializer": "deterministic_public_proposal_doc_materializer",
  "transformation": "proposal_source_draft_to_public_proposal_doc_materialization",
  "requested_effects": ["public_proposal_doc_materialization"],
  "target": {
    "target_lane": "proposal_lane",
    "target_artifact_kind": "public_proposal_doc",
    "proposal_id": "0102",
    "target_path": "docs/proposals/0102_executor_report_proposal_draft_materialization.md"
  },
  "human_authorization": {
    "approval_state": "approved_for_public_proposal_doc_materialization",
    "reviewer": "human_operator",
    "reason": "Allow deterministic public proposal doc materialization from the reviewed local proposal source draft.",
    "materializer_required": true,
    "source_draft_review_required": true
  },
  "authority_boundary": {
    "source_report_is_authority": false,
    "source_draft_is_authority": false,
    "materialization_request_is_authority": false,
    "human_review_required": true,
    "deterministic_materialization_only": true,
    "executor_invocation_allowed": false,
    "policy_request_writes_public_proposal": false,
    "writes_proposal_registry": false,
    "canonical_mutations_allowed": false,
    "proposal_status_mutations_allowed": false,
    "gap_closure_allowed": false,
    "patch_application_allowed": false,
    "static_publish_of_local_materialization_allowed": false
  }
}
```

The shown `proposal_id` is illustrative. In the normal materialized-source
flow, the validator requires the public proposal target id and filename to match
the already-written source materialization report. The deterministic allocator
is only a fallback when a source report does not provide an id; it is not used to
reject the source draft's already-consumed proposal id.

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
source_report_as_authority
direct_source_draft_to_canonical_apply
proposal_lane_status_write
```

## Acceptance

This slice is complete when:

- `public_proposal_doc_materialization_policy` is declared;
- a valid source materialization report plus explicit authorization passes
  validation;
- blocked or invalid source reports are rejected;
- missing human authorization is rejected;
- forbidden effects are rejected with stable effect indices;
- authority expansion is rejected;
- unsafe targets outside `docs/proposals/` are rejected;
- missing source proposal ids are rejected;
- source/target id and filename drift are rejected;
- source report artifact path or write-marker drift is rejected;
- proposal `0101` is tracked in promotion/runtime registries;
- focused validator tests, proposal gates, `publish-bundle`, `docc-sync`, and
  the full Python suite pass.

## Next Gap

```text
build_public_proposal_doc_materializer
```
