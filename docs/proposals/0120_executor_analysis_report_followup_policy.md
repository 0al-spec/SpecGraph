# Executor Analysis Report Follow-up Policy

## Status

Draft proposal

## Source Material

This proposal realizes the next gap from `0112`:

```text
define_executor_analysis_report_followup_policy
```

Source draft:

- `docs/archive/proposal_sources/0120_executor_analysis_report_followup_policy.md`

## Context

`0112` added the first local-only analysis report review outcome. A ready
outcome gives the operator sanitized findings and evidence refs, but it still
must not become proposal authority, patch authority, or canonical authority.

This slice adds the policy boundary for the next step. It defines how a valid
analysis review outcome may be consumed by a future follow-up packet builder,
without building that packet yet.

## Goals

- Add a policy-only section:

  ```text
  executor_analysis_report_followup_policy
  ```

- Require the source outcome:

  ```text
  runs/local_operator_executor_analysis_report_review_outcome.json
  ```

- Allow only source outcomes with:

  ```text
  summary.status = ready_for_operator_review
  outcome_kind = analysis_report_review_outcome
  summary.report_kind = analysis_report
  ```

- Allow only one future effect:

  ```text
  analysis_report_followup_packet
  ```

- Route valid requests to:

  ```text
  build_executor_analysis_report_followup_packet
  ```

- Preserve the review-only authority boundary:
  executor reports, review packets, review outcomes, and follow-up policy are
  all inputs, not authority.

## Non-Goals

- Building the follow-up packet artifact.
- Running Codex or another executor.
- Creating proposal draft candidates.
- Materializing proposal markdown.
- Mutating proposal registries or proposal status.
- Mutating canonical specs.
- Applying patches.
- Closing gaps.
- Publishing local-only executor artifacts.
- Changing SpecSpace, Platform, Ontology, or deployment.

## Policy Contract

The policy is declared under `tools/supervisor_executor_adapter_policy.json`:

```json
{
  "artifact_kind": "executor_analysis_report_followup_policy",
  "source_outcome_artifact": "runs/local_operator_executor_analysis_report_review_outcome.json",
  "allowed_source_outcome_status": ["ready_for_operator_review"],
  "allowed_source_outcome_kinds": ["analysis_report_review_outcome"],
  "allowed_source_report_kinds": ["analysis_report"],
  "consumer": "analysis_report_followup_planner",
  "transformation": "analysis_review_outcome_to_followup_packet",
  "requested_effects": ["analysis_report_followup_packet"],
  "forbidden_effects": [
    "canonical_spec_mutation",
    "patch_application",
    "gap_closure",
    "proposal_status_mutation",
    "proposal_registry_mutation",
    "proposal_markdown_write",
    "proposal_draft_candidate",
    "static_publish_of_local_outcome",
    "executor_invocation",
    "canonical_fact_assertion",
    "direct_analysis_outcome_to_canonical_change"
  ]
}
```

## Authority Boundary

The request validator must reject attempts to:

- treat the executor report as authority;
- treat the review packet as authority;
- treat the review outcome as authority;
- treat the policy itself as authority;
- allow proposal draft candidate production;
- allow executor invocation;
- allow proposal markdown writes;
- mutate proposal registries or proposal status;
- mutate canonical specs;
- apply patches;
- close gaps;
- publish the local-only source outcome.

## Acceptance

This slice is complete when:

- proposal `0120` is tracked in promotion and runtime registries;
- `executor_analysis_report_followup_policy` is declared;
- validators accept a valid `ready_for_operator_review` analysis outcome;
- validators reject missing outcomes, blocked outcomes, wrong report kinds,
  forbidden effects, empty effects, and authority expansion;
- `0112` still builds the source local outcome through
  `make executor-analysis-report-review-outcome`;
- proposal gates, focused tests, and full Python suite pass.
