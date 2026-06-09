# Local Operator Executor Smoke

## Draft Plan

Add the first bounded local executor smoke after `0087` readiness. The smoke
must consume `runs/local_operator_executor_readiness.json`, refuse when readiness
is not `ready_for_local_smoke`, and run only a safe backend probe such as
`codex --version`.

## Scope

- Add `runs/local_operator_executor_smoke.json`.
- Add `make executor-smoke`.
- Consume the readiness artifact instead of recomputing readiness implicitly.
- Run only the policy-declared local smoke probe.
- Record sanitized status, exit code, timeout state, and checks.
- Do not persist absolute executable paths.
- Do not persist raw stdout/stderr.
- Do not run an agent task.
- Do not mutate canonical specs.
- Do not claim sandbox/runtime enforcement.
- Do not publish the local smoke artifact in the static bundle.

## Validation Intent

- `make executor-readiness`
- `make executor-smoke`
- focused executor smoke tests
- static bundle exclusion test
- proposal tracking gates
- full Python suite
