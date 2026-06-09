# Local Operator Executor Readiness

## Draft Plan

Add a local-only readiness surface that tells an operator whether the current
checkout can proceed to a bounded executor adapter smoke step.

## Scope

- Add `runs/local_operator_executor_readiness.json`.
- Add `make executor-readiness`.
- Reuse the existing supervisor executor adapter policy and runtime environment
  boundary from `0084`.
- Treat static publish as not applicable, not as a local executor failure.
- Do not launch Codex or any executor task.
- Do not claim observed runtime enforcement.
- Do not publish this local-only artifact in the static bundle.
- Do not persist absolute executable paths, raw logs, secrets, or environment
  dumps.

## Validation Intent

- focused executor readiness tests
- `make executor-readiness`
- proposal tracking gates
- static bundle test proving the local-only artifact is skipped
- full Python suite
