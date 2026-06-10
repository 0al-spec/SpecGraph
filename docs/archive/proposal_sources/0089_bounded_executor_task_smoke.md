# Bounded Executor Task Smoke

## Draft Plan

Add the first local-only bounded executor task smoke after `0088`. The smoke
must consume both `runs/local_operator_executor_readiness.json` and
`runs/local_operator_executor_smoke.json`, refuse when either source artifact is
not ready, and run a minimal executor task that returns a strict JSON
acknowledgement.

## Scope

- Add `runs/local_operator_executor_task_smoke.json`.
- Add `make executor-task-smoke`.
- Consume readiness and probe smoke artifacts instead of recomputing or
  bypassing them.
- Run only after readiness reports `ready_for_local_smoke` and probe smoke
  reports `passed`.
- Ask the configured executor backend for a bounded JSON response:
  `task_kind=bounded_executor_task_smoke`,
  `status=acknowledged`, and
  `canonical_mutation_attempted=false`.
- Record sanitized status, response shape, exit code, timeout state, and
  mutation guard checks.
- Do not persist absolute executable paths.
- Do not persist raw stdout/stderr.
- Do not persist raw executor response text.
- Do not mutate canonical specs.
- Do not claim sandbox/runtime enforcement.
- Do not publish the local task smoke artifact in the static bundle.

## Validation Intent

- `make executor-readiness`
- `make executor-smoke`
- `make executor-task-smoke`
- focused executor task smoke tests
- static bundle exclusion test
- proposal tracking gates
- full Python suite
