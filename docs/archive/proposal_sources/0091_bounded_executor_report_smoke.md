# Bounded Executor Report Smoke

## Draft Plan

Add the first local-only bounded executor report smoke after `0090`. The smoke
must consume `runs/local_operator_executor_task_smoke.json` and
`runs/local_operator_executor_report_contract.json`, refuse when either source
artifact is not ready, and run a minimal executor task that returns a valid
`local_operator_executor_report`.

## Scope

- Add `make executor-report-smoke`.
- Add `--build-local-operator-executor-report-smoke`.
- Write `runs/local_operator_executor_report.json`.
- Consume and validate the task-smoke source artifact.
- Consume and validate the report-contract source artifact.
- Run only the policy-declared local report smoke command.
- Validate the executor response with the generic report validator from `0090`.
- Record sanitized invocation status, report validation, and mutation guard
  checks.
- Do not persist raw stdout/stderr.
- Do not persist invalid raw report payloads.
- Do not persist absolute executable paths.
- Do not mutate canonical specs.
- Do not claim sandbox/runtime enforcement.
- Do not publish the local report artifact in the static bundle.

## Validation Intent

- `make executor-readiness`
- `make executor-smoke`
- `make executor-task-smoke`
- `make executor-report-contract`
- `make executor-report-smoke`
- focused executor report smoke tests
- static bundle exclusion test
- proposal tracking gates
- full Python suite
