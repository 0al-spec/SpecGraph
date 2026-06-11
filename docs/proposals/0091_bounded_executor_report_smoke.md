# Bounded Executor Report Smoke

## Status

Draft proposal

## Source Material

This proposal implements the first bounded local executor report smoke after
`0089` task smoke and `0090` report contract.

Source draft:

- `docs/archive/proposal_sources/0091_bounded_executor_report_smoke.md`

## Context

`0089` proved that the local operator environment can run a bounded executor
task and receive a strict acknowledgement. `0090` then defined a generic
executor/producer report contract that is compatible with future Codex, Pi,
SpecHarvester, and operator-tool producer flows.

The next bounded step is to run one real local report task and write a
contract-valid local report artifact without granting canonical mutation
authority.

## Goals

- Add a local-only report smoke artifact:

  ```text
  runs/local_operator_executor_report.json
  ```

- Add a Makefile shortcut:

  ```bash
  make executor-report-smoke
  ```

- Consume both source artifacts:

  ```text
  runs/local_operator_executor_task_smoke.json
  runs/local_operator_executor_report_contract.json
  ```

- Refuse to run unless task smoke is `passed` and report contract is
  `ready_for_report_smoke`.
- Run the policy-declared executor report task command, currently a bounded
  `codex exec` invocation using read-only sandbox.
- Require the executor response to pass the generic report validator from
  `0090`.
- Persist the valid report plus sanitized smoke metadata.
- If the executor returns an invalid report, persist only a sanitized
  `invalid_report` fallback with validation findings, not the raw invalid
  payload.
- Verify tracked worktree status is unchanged before/after the report task.
- Keep the artifact out of public static publish.

## Non-Goals

- Creating proposals with Codex.
- Creating or applying patches.
- Mutating canonical specs.
- Granting executor authority above `report_only`.
- Implementing full sandbox/runtime enforcement.
- Implementing Pi or SpecHarvester runtime integration.
- Adding a SpecSpace UI surface.
- Publishing `runs/local_operator_executor_report.json` to `specgraph.tech`.

## Artifact Contract

The report remains a `0090` report artifact. The smoke outcome lives in
`smoke_summary` so the report's own `summary.status` can stay within
`valid_report` / `invalid_report`.

```json
{
  "artifact_kind": "local_operator_executor_report",
  "schema_version": 1,
  "local_only": true,
  "source_task_smoke_artifact": "runs/local_operator_executor_task_smoke.json",
  "source_report_contract_artifact": "runs/local_operator_executor_report_contract.json",
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
  "smoke_summary": {
    "status": "passed",
    "backend_id": "codex",
    "source_task_smoke_status": "passed",
    "source_report_contract_status": "ready_for_report_smoke",
    "report_valid": true,
    "next_gap": "define_executor_report_consumption_policy"
  },
  "report": {
    "report_kind": "analysis_report",
    "status": "completed",
    "findings": [],
    "source_evidence_refs": [
      "runs/local_operator_executor_task_smoke.json"
    ],
    "proposed_artifacts": []
  }
}
```

## Smoke Statuses

The report smoke status values are:

```text
passed
blocked_task_smoke_not_passed
blocked_report_contract_not_ready
blocked_executor_unavailable
failed_executor_nonzero
failed_invalid_report
failed_mutation_guard
blocked_policy_contract
```

`passed` means only that the local supervisor process could invoke the declared
executor report task boundary, receive a valid generic report, and observe no
tracked worktree mutation. It does not mean the executor may create proposals,
apply patches, mutate canonical specs, or bypass supervisor review.

The passed `next_gap` is:

```text
define_executor_report_consumption_policy
```

That next slice should define how supervisor/runtime consumers may use a valid
local report before any proposal-producing or patch-producing workflow is
allowed.

## Acceptance

This slice is complete when:

- `make executor-report-smoke` writes
  `runs/local_operator_executor_report.json`;
- the command refuses to run when task smoke is missing/not passed or report
  contract is missing/not ready;
- the passed path runs only the policy-declared bounded report command;
- valid reports pass the generic report validator from `0090`;
- invalid reports are not persisted raw;
- the artifact contains no absolute executable path and no raw stdout/stderr;
- tracked worktree status is compared before and after the bounded report task;
- `tools/build_static_artifact_bundle.py` excludes
  `runs/local_operator_executor_report.json` from the public bundle;
- proposal gates, focused report-smoke tests, static bundle tests, `make
  executor-readiness`, `make executor-smoke`, `make executor-task-smoke`,
  `make executor-report-contract`, `make executor-report-smoke`, and the full
  Python suite pass.
