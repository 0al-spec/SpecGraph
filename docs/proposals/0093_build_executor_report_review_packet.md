# Build Executor Report Review Packet

## Status

Draft proposal

## Source Material

This proposal implements the first local-only review packet over the executor
report consumption policy from `0092`.

Source draft:

- `docs/archive/proposal_sources/0093_build_executor_report_review_packet.md`

## Context

`0091` proved that a local executor can produce a contract-valid
`runs/local_operator_executor_report.json`. `0092` defined who may consume that
report and which effects are allowed before any proposal or patch workflow
exists.

The next bounded step is to build a review packet from the valid report. This
packet makes executor output reviewable, but it is not a proposal, not a patch,
and not a canonical graph mutation.

## Goals

- Add a local-only review packet artifact:

  ```text
  runs/local_operator_executor_report_review_packet.json
  ```

- Add a Makefile shortcut:

  ```bash
  make executor-report-review-packet
  ```

- Consume `runs/local_operator_executor_report.json`.
- Validate the source report with the generic executor report validator.
- Validate the review-packet consumption request against
  `executor_report_consumption_policy`.
- Include a sanitized review projection of report findings, evidence refs, and
  proposed artifacts.
- Require human/operator review.
- Preserve `canonical_mutations_allowed: false`.
- Keep the artifact out of public static publish.

## Non-Goals

- Creating a proposal draft.
- Applying a patch.
- Mutating canonical specs.
- Closing gaps.
- Changing proposal status.
- Publishing the local review packet to `specgraph.tech`.
- Adding a SpecSpace UI surface.
- Running a new executor task.

## Artifact Contract

The review packet is report-only and local-only:

```json
{
  "artifact_kind": "local_operator_executor_report_review_packet",
  "schema_version": 1,
  "local_only": true,
  "source_report_artifact": "runs/local_operator_executor_report.json",
  "policy_reference": {
    "policy_artifact_path": "tools/supervisor_executor_adapter_policy.json",
    "policy_section": "executor_report_consumption_policy",
    "packet_contract_section": "executor_report_review_packet_contract"
  },
  "summary": {
    "status": "ready_for_review",
    "report_kind": "analysis_report",
    "producer_kind": "coding_agent",
    "authority_level": "review_only",
    "human_review_required": true,
    "canonical_mutations_allowed": false,
    "next_gap": "define_executor_report_to_proposal_draft_policy"
  },
  "review_packet": {
    "packet_kind": "executor_report_review",
    "source_report_status": "valid_report",
    "review_state": "ready_for_human_review",
    "findings": [],
    "evidence_refs": [],
    "proposed_artifacts": [],
    "review_questions": [],
    "operator_decision_required": true,
    "report_is_authority": false
  }
}
```

## Statuses

The packet status values are:

```text
ready_for_review
blocked_missing_source_report
blocked_invalid_source_report
blocked_consumption_policy
blocked_forbidden_effect
blocked_authority_boundary
blocked_privacy_boundary
blocked_policy_contract
```

`ready_for_review` means only that the source report is valid and the
consumption policy allows a review-packet candidate. It does not mean report
findings are canonical facts, does not create a proposal, and does not grant
patch or gap-closure authority.

## Acceptance

This slice is complete when:

- `make executor-report-review-packet` writes
  `runs/local_operator_executor_report_review_packet.json`;
- missing or invalid source reports block the packet;
- forbidden effects and authority expansion are rejected;
- packet validation requires human/operator review and no canonical mutation;
- unsafe local paths, raw logs, raw prompts, raw responses, and secrets do not
  leak into the packet;
- the static bundle excludes
  `runs/local_operator_executor_report_review_packet.json`;
- proposal gates, focused review-packet tests, static bundle tests,
  `make executor-report-review-packet`, `make publish-bundle`, and the full
  Python suite pass.
