# Build Executor Analysis Report Review Outcome

## Status

Draft proposal

## Source Material

This proposal realizes the next gap from `0107`:

```text
build_executor_analysis_report_review_outcome
```

Source draft:

- `docs/archive/proposal_sources/0112_build_executor_analysis_report_review_outcome.md`

## Context

`0107` added a policy-only path for consuming local executor
`analysis_report` review packets. That policy intentionally stopped before
building an output artifact.

This slice adds the bounded runtime surface that consumes:

```text
runs/local_operator_executor_report_review_packet.json
```

and writes:

```text
runs/local_operator_executor_analysis_report_review_outcome.json
```

The outcome is operator review input. It is not proposal authority, not
canonical authority, and not patch authority.

## Goals

- Add `executor_analysis_report_review_outcome_contract` to
  `tools/supervisor_executor_adapter_policy.json`.
- Add a local-only artifact:

  ```text
  runs/local_operator_executor_analysis_report_review_outcome.json
  ```

- Add a Make/CLI surface:

  ```text
  make executor-analysis-report-review-outcome
  tools/supervisor.py --build-local-operator-executor-analysis-report-review-outcome
  ```

- Build the outcome only from a review packet accepted by
  `executor_analysis_report_consumption_policy`.
- Preserve sanitized findings, safe evidence refs, source report kind,
  review state, and policy validation summaries.
- Reject wrong source kinds such as `proposal_draft`.
- Reject authority expansion, privacy leakage, missing packets, and invalid
  source packets.
- Exclude the local-only outcome artifact from public static publishing.

## Non-Goals

- Running a new executor task.
- Creating proposal draft candidates.
- Materializing proposal markdown.
- Mutating proposal registries or proposal status.
- Mutating canonical specs.
- Applying patches.
- Closing gaps.
- Changing SpecSpace, Platform, Ontology, or deployment.

## Runtime Contract

The outcome artifact uses:

```json
{
  "artifact_kind": "local_operator_executor_analysis_report_review_outcome",
  "schema_version": 1,
  "source_review_packet_artifact": "runs/local_operator_executor_report_review_packet.json",
  "source_report_artifact": "runs/local_operator_executor_report.json",
  "local_only": true,
  "outcome_kind": "analysis_report_review_outcome",
  "summary": {
    "status": "ready_for_operator_review",
    "report_kind": "analysis_report",
    "authority_level": "review_only",
    "human_review_required": true,
    "canonical_mutations_allowed": false,
    "proposal_draft_candidate_allowed": false,
    "next_gap": "define_executor_analysis_report_followup_policy"
  }
}
```

Blocked outcomes use explicit statuses such as
`blocked_missing_review_packet`, `blocked_invalid_review_packet`,
`blocked_consumption_policy`, `blocked_authority_boundary`,
`blocked_privacy_boundary`, or `blocked_policy_contract`.

## Authority Boundary

The artifact must preserve these invariants:

- executor report is not authority;
- review packet is not authority;
- review outcome is not authority;
- human/operator review remains required;
- canonical mutations are forbidden;
- proposal draft candidate production is forbidden;
- proposal status mutations are forbidden;
- gap closure is forbidden;
- patch application is forbidden;
- local outcome publication in the public static bundle is forbidden.

## Acceptance

This slice is complete when:

- proposal `0112` is tracked in promotion and runtime registries;
- `executor_analysis_report_review_outcome_contract` is declared;
- `make executor-analysis-report-review-outcome` writes the local-only outcome;
- valid `analysis_report` review packets produce `ready_for_operator_review`;
- missing or invalid packets block without traceback;
- `proposal_draft` review packets block on consumption policy;
- authority expansion and privacy leakage are rejected;
- static bundle tests prove the outcome artifact is excluded;
- proposal gates, focused tests, static bundle tests, DocC sync, publish bundle,
  and full Python suite pass.
