# Local Operator Executor Readiness

## Status

Draft proposal

## Source Material

This proposal implements the local operator readiness slice after `0084`
separated static publish from local operator executor semantics.

Source draft:

- `docs/archive/proposal_sources/0087_local_operator_executor_readiness.md`

## Context

`0084` made executor availability environment-aware:

```text
static_publish_environment != local_operator_environment
```

That prevents public static artifacts from presenting a missing local Codex
binary as a broken deploy. The remaining local operator gap is different: an
operator still needs a deterministic way to ask whether the current checkout is
ready for the next bounded executor smoke step.

## Goals

- Add a local-only readiness artifact:

  ```text
  runs/local_operator_executor_readiness.json
  ```

- Add a Makefile shortcut:

  ```bash
  make executor-readiness
  ```

- Reuse the existing supervisor executor adapter policy, runtime environment
  semantics, invocation-boundary check, and report-only Agent Passport
  validation.
- Report readiness without launching Codex, running an agent task, or claiming
  runtime enforcement.
- Keep all machine-local paths, raw logs, secrets, and raw environment values
  out of the artifact.
- Explicitly exclude the local-only readiness artifact from public static
  publish.

## Non-Goals

- Running a real Codex task.
- Implementing sandbox/runtime enforcement.
- Implementing Pi integration.
- Mutating SpecSpace or Platform.
- Adding a SpecSpace UI surface in this slice.
- Publishing `runs/local_operator_executor_readiness.json` to `specgraph.tech`.

## Artifact Contract

The artifact is report-only and local-only:

```json
{
  "artifact_kind": "local_operator_executor_readiness",
  "schema_version": 1,
  "local_only": true,
  "producer_environment": "local_operator_environment",
  "summary": {
    "backend_count": 1,
    "ready_backend_count": 1,
    "blocked_backend_count": 0,
    "not_applicable_backend_count": 0,
    "default_backend_id": "codex",
    "default_backend_readiness": "ready_for_local_smoke",
    "next_gap": "run_executor_adapter_smoke_benchmark"
  },
  "entries": [
    {
      "backend_id": "codex",
      "backend_status": "available",
      "readiness_status": "ready_for_local_smoke",
      "checks": [
        {
          "check_id": "local_operator_environment_selected",
          "status": "passed"
        },
        {
          "check_id": "executable_available_in_local_operator_environment",
          "status": "passed"
        },
        {
          "check_id": "executor_adapter_invocation_boundary",
          "status": "passed"
        },
        {
          "check_id": "agent_passport_report_only_valid",
          "status": "passed"
        }
      ],
      "safe_next_action": "run_executor_adapter_smoke_benchmark"
    }
  ]
}
```

## Readiness Statuses

The readiness status values are:

```text
ready_for_local_smoke
blocked_missing_executable
blocked_invalid_runtime_environment
blocked_policy_contract
blocked_passport_validation
not_applicable_non_local_environment
```

`ready_for_local_smoke` means only that the local operator checkout is ready for
the next bounded smoke step. It does not mean runtime enforcement is implemented
or observed.

## Acceptance

This slice is complete when:

- `make executor-readiness` writes
  `runs/local_operator_executor_readiness.json`;
- the artifact reports local Codex readiness as `ready_for_local_smoke` only
  when local environment selection, executable availability,
  invocation-boundary checks, and report-only Agent Passport validation pass;
- missing Codex, invalid runtime override, and static publish/non-local
  environments produce explicit non-ready statuses;
- no local executable path is persisted;
- `tools/build_static_artifact_bundle.py` excludes
  `runs/local_operator_executor_readiness.json` from the public bundle;
- proposal gates, focused readiness tests, static bundle tests, and the full
  Python suite pass.
