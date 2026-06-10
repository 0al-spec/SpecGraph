# Bounded Executor Task Smoke

## Status

Draft proposal

## Source Material

This proposal implements the first bounded local executor task smoke after
`0087` readiness and `0088` probe smoke.

Source draft:

- `docs/archive/proposal_sources/0089_bounded_executor_task_smoke.md`

## Context

`0087` introduced a local-only readiness artifact for the operator execution
environment. `0088` then proved that the supervisor can invoke the configured
executor backend through a bounded probe without persisting raw logs or mutating
the worktree.

The next slice is intentionally still small: run a minimal executor task that
returns a strict JSON acknowledgement. This proves the supervisor can cross the
task invocation boundary, but it does not grant canonical mutation authority and
does not claim full sandbox/runtime enforcement.

## Goals

- Add a local-only task smoke artifact:

  ```text
  runs/local_operator_executor_task_smoke.json
  ```

- Add a Makefile shortcut:

  ```bash
  make executor-task-smoke
  ```

- Consume both source artifacts:

  ```text
  runs/local_operator_executor_readiness.json
  runs/local_operator_executor_smoke.json
  ```

- Refuse to run the task unless readiness is `ready_for_local_smoke` and probe
  smoke is `passed`.
- Run the policy-declared executor task command, currently a bounded
  `codex exec` invocation using read-only sandbox.
- Require a strict JSON response contract:

  ```json
  {
    "task_kind": "bounded_executor_task_smoke",
    "status": "acknowledged",
    "canonical_mutation_attempted": false,
    "message": "<short message>"
  }
  ```

- Record sanitized task outcome without raw logs, raw response text, or absolute
  executable paths.
- Verify tracked worktree status is unchanged before/after the task.
- Keep the artifact out of public static publish.

## Non-Goals

- Creating or applying proposals with Codex.
- Granting direct canonical graph mutation authority.
- Persisting raw executor conversation logs.
- Implementing full sandbox/runtime enforcement.
- Implementing Pi integration.
- Adding a SpecSpace UI surface.
- Publishing `runs/local_operator_executor_task_smoke.json` to
  `specgraph.tech`.

## Artifact Contract

The artifact is report-only and local-only:

```json
{
  "artifact_kind": "local_operator_executor_task_smoke",
  "schema_version": 1,
  "local_only": true,
  "source_readiness_artifact": "runs/local_operator_executor_readiness.json",
  "source_smoke_artifact": "runs/local_operator_executor_smoke.json",
  "summary": {
    "status": "passed",
    "backend_id": "codex",
    "consumed_readiness_status": "ready_for_local_smoke",
    "consumed_smoke_status": "passed",
    "next_gap": "define_executor_report_artifact_contract"
  },
  "entries": [
    {
      "backend_id": "codex",
      "task_smoke_status": "passed",
      "request_contract": {
        "task_kind": "bounded_executor_task_smoke",
        "canonical_mutation_allowed": false,
        "expected_response_format": "json_object",
        "prompt_persisted": false
      },
      "execution": {
        "exit_code": 0,
        "timed_out": false,
        "command": {
          "command_name": "codex",
          "resolution_source": "path",
          "path_persisted": false
        },
        "stdout_persisted": false,
        "stderr_persisted": false,
        "raw_response_persisted": false
      },
      "response": {
        "parsed": true,
        "valid": true,
        "task_kind": "bounded_executor_task_smoke",
        "status": "acknowledged",
        "canonical_mutation_attempted": false,
        "message_length": 42
      },
      "checks": [
        {
          "check_id": "readiness_allows_task_smoke",
          "status": "passed"
        },
        {
          "check_id": "executor_smoke_passed",
          "status": "passed"
        },
        {
          "check_id": "executor_task_invocation_completed",
          "status": "passed"
        },
        {
          "check_id": "executor_task_response_valid",
          "status": "passed"
        },
        {
          "check_id": "no_canonical_mutation_attempted",
          "status": "passed"
        }
      ],
      "safe_next_action": "define_executor_report_artifact_contract"
    }
  ]
}
```

## Task Smoke Statuses

The task smoke status values are:

```text
passed
blocked_readiness_not_ready
blocked_smoke_not_passed
blocked_executor_unavailable
failed_executor_nonzero
failed_invalid_response
failed_mutation_guard
blocked_policy_contract
```

`passed` means only that the local supervisor process could invoke the declared
executor task boundary, receive a valid bounded JSON acknowledgement, and
observe no tracked worktree mutation. It does not mean Codex can perform
SpecGraph work, does not prove sandbox enforcement, and does not grant
canonical mutation authority.

The passed `next_gap` is:

```text
define_executor_report_artifact_contract
```

That next slice should define the report artifact shape for real bounded
executor work before any proposal-producing or patch-producing task is allowed.

## Acceptance

This slice is complete when:

- `make executor-task-smoke` writes
  `runs/local_operator_executor_task_smoke.json`;
- the command refuses to run when readiness is missing/not ready or probe smoke
  is missing/not passed;
- the passed path runs only the policy-declared bounded task command;
- the artifact contains no absolute executable path, no raw stdout/stderr, and
  no raw executor response;
- tracked worktree status is compared before and after the bounded task;
- `tools/build_static_artifact_bundle.py` excludes
  `runs/local_operator_executor_task_smoke.json` from the public bundle;
- proposal gates, focused task-smoke tests, static bundle tests, `make
  executor-readiness`, `make executor-smoke`, `make executor-task-smoke`, and
  the full Python suite pass.
