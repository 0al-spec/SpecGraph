# Executor Analysis Report Consumption Policy

## Status

Draft proposal

## Source Material

This proposal defines the policy boundary for consuming `analysis_report`
executor review packets after `0093` without routing them into the proposal
draft path from `0094`.

Source draft:

- `docs/archive/proposal_sources/0107_executor_analysis_report_consumption_policy.md`

## Context

The local executor chain can now produce a valid local executor report, wrap it
in a review packet, and route `proposal_draft` packets toward a future proposal
draft candidate.

The real local Codex smoke commonly produces:

```text
summary.report_kind = analysis_report
```

That is useful review input, but it is not proposal-draft authority. The
existing `executor_report_to_proposal_draft_policy` correctly rejects
`analysis_report` packets. This slice adds the missing policy-only path for
reviewing analysis reports while keeping proposal production closed.

## Goals

- Add a policy-only section:

  ```text
  executor_analysis_report_consumption_policy
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
  summary.report_kind = analysis_report
  ```

- Route ready `analysis_report` review packets to:

  ```text
  build_executor_analysis_report_review_outcome
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
  proposal draft candidate production is forbidden
  ```

## Non-Goals

- Building the analysis report review outcome artifact.
- Converting `analysis_report` packets into proposal draft candidates.
- Creating or editing files under `docs/proposals/`.
- Applying patches.
- Mutating canonical specs.
- Closing gaps.
- Running a new executor task.
- Changing SpecSpace UI.
- Changing Platform deploy.

## Policy Contract

The policy is declared under `tools/supervisor_executor_adapter_policy.json`:

```json
{
  "artifact_kind": "executor_analysis_report_consumption_policy",
  "schema_version": 1,
  "source_review_packet_artifact": "runs/local_operator_executor_report_review_packet.json",
  "source_report_artifact": "runs/local_operator_executor_report.json",
  "allowed_source_packet_status": ["ready_for_review"],
  "allowed_source_review_states": ["ready_for_human_review"],
  "allowed_source_report_kinds": ["analysis_report"],
  "consumer": "analysis_report_reviewer",
  "transformation": "review_packet_to_analysis_report_review_outcome",
  "requested_effects": ["analysis_report_review_outcome"],
  "forbidden_effects": [
    "canonical_spec_mutation",
    "patch_application",
    "gap_closure",
    "proposal_status_mutation",
    "static_publish_of_local_report",
    "canonical_fact_assertion",
    "direct_executor_report_to_canonical_change",
    "proposal_draft_candidate"
  ],
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
  "next_gap": "build_executor_analysis_report_review_outcome"
}
```

## Important Constraint

This proposal does not weaken the `proposal_draft` gate. `proposal_draft`
review packets continue to use `executor_report_to_proposal_draft_policy`.
`analysis_report` review packets become reviewable through a separate outcome
path and remain non-authoritative.

## Acceptance

This slice is complete when:

- `executor_analysis_report_consumption_policy` is declared;
- validators accept a valid `analysis_report` review packet;
- validators reject a `proposal_draft` review packet for the analysis path;
- validators reject forbidden effects such as `proposal_draft_candidate`;
- validators reject authority expansion and unexpected authority fields;
- ready `analysis_report` review packets route to
  `build_executor_analysis_report_review_outcome`;
- ready `proposal_draft` review packets still route to
  `define_executor_report_to_proposal_draft_policy`;
- proposal `0107` is tracked in promotion/runtime registries;
- proposal gates, focused tests, static bundle tests, and full Python suite pass.
