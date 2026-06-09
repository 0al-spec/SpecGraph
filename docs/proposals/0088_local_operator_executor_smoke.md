# Local Operator Executor Smoke

## Status

Draft proposal

## Source Material

This proposal implements the first bounded local executor smoke after `0087`
readiness.

Source draft:

- `docs/archive/proposal_sources/0088_local_operator_executor_smoke.md`

## Context

`0084` separated static publish from local operator executor semantics.
`0087` then added the local-only readiness artifact:

```text
runs/local_operator_executor_readiness.json
```

When readiness reports `ready_for_local_smoke`, the next bounded step is not a
real agent task. It is a smaller proof that the supervisor can invoke the
declared executor backend boundary in the local operator environment.

## Goals

- Add a local-only smoke artifact:

  ```text
  runs/local_operator_executor_smoke.json
  ```

- Add a Makefile shortcut:

  ```bash
  make executor-smoke
  ```

- Consume `runs/local_operator_executor_readiness.json`.
- Refuse to run the probe unless the consumed readiness status is
  `ready_for_local_smoke`.
- Run only the policy-declared backend probe, currently `codex --version`.
- Record sanitized probe outcome without raw logs or absolute executable paths.
- Verify the probe did not change tracked worktree status.
- Keep the artifact out of public static publish.

## Non-Goals

- Running a real Codex task.
- Creating proposals or reports with Codex.
- Granting canonical mutation authority.
- Implementing sandbox/runtime enforcement.
- Implementing Pi integration.
- Adding a SpecSpace UI surface.
- Publishing `runs/local_operator_executor_smoke.json` to `specgraph.tech`.

## Artifact Contract

The artifact is report-only and local-only:

```json
{
  "artifact_kind": "local_operator_executor_smoke",
  "schema_version": 1,
  "local_only": true,
  "source_readiness_artifact": "runs/local_operator_executor_readiness.json",
  "summary": {
    "status": "passed",
    "backend_id": "codex",
    "consumed_readiness_status": "ready_for_local_smoke",
    "next_gap": "define_bounded_executor_task_smoke"
  },
  "entries": [
    {
      "backend_id": "codex",
      "readiness_status": "ready_for_local_smoke",
      "smoke_status": "passed",
      "probe": {
        "args": ["--version"],
        "timeout_seconds": 15,
        "exit_code": 0,
        "timed_out": false,
        "command": {
          "command_name": "codex",
          "resolution_source": "path",
          "path_persisted": false
        },
        "stdout_persisted": false,
        "stderr_persisted": false
      },
      "checks": [
        {
          "check_id": "readiness_artifact_present",
          "status": "passed"
        },
        {
          "check_id": "readiness_allows_local_smoke",
          "status": "passed"
        },
        {
          "check_id": "executor_probe_invocation_completed",
          "status": "passed"
        },
        {
          "check_id": "no_canonical_mutation_attempted",
          "status": "passed"
        }
      ],
      "safe_next_action": "define_bounded_executor_task_smoke"
    }
  ]
}
```

## Smoke Statuses

The smoke status values are:

```text
passed
blocked_readiness_not_ready
failed_probe_invocation
blocked_policy_contract
```

`passed` means only that the local supervisor process could invoke the declared
backend probe and observe a clean exit without tracked worktree mutation. It
does not mean Codex can perform SpecGraph work, does not prove sandbox
enforcement, and does not grant canonical mutation authority.

## Acceptance

This slice is complete when:

- `make executor-smoke` writes `runs/local_operator_executor_smoke.json`;
- the command refuses to run the probe when readiness is missing or not
  `ready_for_local_smoke`;
- the passed path runs only the policy-declared probe command;
- the artifact contains no absolute executable path and no raw stdout/stderr;
- tracked worktree status is compared before and after the probe;
- `tools/build_static_artifact_bundle.py` excludes
  `runs/local_operator_executor_smoke.json` from the public bundle;
- proposal gates, focused smoke tests, static bundle tests, `make
  executor-readiness`, `make executor-smoke`, and the full Python suite pass.
