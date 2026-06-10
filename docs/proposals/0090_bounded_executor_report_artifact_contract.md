# Bounded Executor Report Artifact Contract

## Status

Draft proposal

## Source Material

This proposal implements the generic report contract slice after `0089`
bounded executor task smoke.

Source draft:

- `docs/archive/proposal_sources/0090_bounded_executor_report_artifact_contract.md`

## Context

`0087` added local operator executor readiness. `0088` added a bounded executor
probe smoke. `0089` added a bounded executor task smoke that can receive a
strict JSON acknowledgement without canonical mutation.

The next step must not be a real proposal-generating agent workflow yet. Before
any executor or producer can return useful work, SpecGraph needs a stable report
artifact contract that the supervisor can validate.

The contract is intentionally not Codex-specific. Codex is the first local
executor, but SpecHarvester already acts as a real producer of candidate bundle
evidence for SpecPM. Future Pi or operator-tool producers should fit the same
report boundary.

## Goals

- Add a local-only contract preview artifact:

  ```text
  runs/local_operator_executor_report_contract.json
  ```

- Define the future local-only report target:

  ```text
  runs/local_operator_executor_report.json
  ```

- Add a Makefile shortcut:

  ```bash
  make executor-report-contract
  ```

- Validate a generic bounded executor/producer report shape.
- Support these producer kinds:

  ```text
  coding_agent
  harvester
  operator_tool
  external_harness
  ```

- Support these report kinds:

  ```text
  analysis_report
  package_candidate_report
  proposal_draft
  patch_suggestion
  validation_summary
  ```

- Require report authority to remain `report_only` or `proposal_only`.
- Require `canonical_mutation_attempted=false`.
- Require safe repo-relative `source_evidence_refs`.
- Reject raw logs, raw prompts, raw responses, secrets, and absolute paths.
- Keep the contract preview and future local report out of public static
  publishing.

## Non-Goals

- Running a new Codex task.
- Running Pi or SpecHarvester.
- Creating proposals through an agent.
- Applying patches.
- Mutating canonical specs.
- Adding a SpecSpace UI surface.
- Implementing SpecPM publish/intake.
- Publishing local executor report artifacts to `specgraph.tech`.

## Artifact Contract

The contract preview artifact is report-only and local-only:

```json
{
  "artifact_kind": "local_operator_executor_report_contract",
  "schema_version": 1,
  "local_only": true,
  "source_task_smoke_artifact": "runs/local_operator_executor_task_smoke.json",
  "target_report_artifact": "runs/local_operator_executor_report.json",
  "target_report_artifact_kind": "local_operator_executor_report",
  "producer_contract": {
    "producer_kinds": [
      "coding_agent",
      "external_harness",
      "harvester",
      "operator_tool"
    ],
    "authority_levels": [
      "proposal_only",
      "report_only"
    ]
  },
  "report_contract": {
    "report_kinds": [
      "analysis_report",
      "package_candidate_report",
      "patch_suggestion",
      "proposal_draft",
      "validation_summary"
    ],
    "report_status_values": [
      "invalid_report",
      "valid_report"
    ]
  },
  "sample_report_validation": {
    "valid": true,
    "raw_sample_persisted": false
  },
  "summary": {
    "status": "ready_for_report_smoke",
    "source_task_smoke_status": "passed",
    "sample_report_valid": true,
    "next_gap": "run_bounded_executor_report_smoke"
  }
}
```

The future report artifact shape is:

```json
{
  "artifact_kind": "local_operator_executor_report",
  "schema_version": 1,
  "local_only": true,
  "source_task_smoke_artifact": "runs/local_operator_executor_task_smoke.json",
  "producer": {
    "producer_kind": "coding_agent",
    "producer_id": "codex",
    "authority_level": "report_only"
  },
  "summary": {
    "status": "valid_report",
    "report_kind": "analysis_report",
    "curation_required": true,
    "canonical_mutation_attempted": false,
    "next_gap": "run_bounded_executor_report_smoke"
  },
  "report": {
    "report_kind": "analysis_report",
    "status": "completed",
    "findings": [],
    "source_evidence_refs": [
      "runs/local_operator_executor_task_smoke.json"
    ],
    "proposed_artifacts": []
  },
  "privacy_boundary": {
    "absolute_paths_persisted": false,
    "raw_logs_persisted": false,
    "raw_prompt_persisted": false,
    "raw_response_persisted": false,
    "secrets_persisted": false
  }
}
```

## Statuses

The contract preview status values are:

```text
ready_for_report_smoke
blocked_task_smoke_not_passed
invalid_contract
blocked_policy_contract
```

`ready_for_report_smoke` means the report contract is valid, the local task
smoke source artifact passed, and the next bounded step may run a report smoke.
It does not allow canonical mutation and does not prove full runtime
enforcement.

The passed `next_gap` is:

```text
run_bounded_executor_report_smoke
```

## Acceptance

This slice is complete when:

- `make executor-report-contract` writes
  `runs/local_operator_executor_report_contract.json`;
- the artifact reports `ready_for_report_smoke` only after task smoke has
  passed;
- validator accepts a Codex-style `analysis_report`;
- validator accepts a SpecHarvester-style `package_candidate_report`;
- validator rejects unknown report kinds;
- validator rejects `canonical_mutation_attempted=true`;
- validator rejects unsafe evidence refs and raw log/prompt/response fields;
- `tools/build_static_artifact_bundle.py` excludes both
  `runs/local_operator_executor_report_contract.json` and
  `runs/local_operator_executor_report.json`;
- proposal gates, focused report contract tests, static bundle tests,
  `make executor-report-contract`, and the full Python suite pass.
