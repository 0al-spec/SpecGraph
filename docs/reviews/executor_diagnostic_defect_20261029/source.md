# Executor diagnostic false positive: source and defect scope

The operator requested on 2026-10-29:

> Ложные предупреждения нужно проводить как дефекты тоже через граф со всеми вытекающими процедурами

Then explicitly authorized delegation:

> Можешь например запустить subagent на обнаруженный дефект

These are locally attributed excerpts from the active conversation, not signed
approval or independently authenticated message identities. The scoped defect
below is the first application of that process direction.

## Observed defect

Supervisor run `20261029T182812Z-SG-SPEC-0064-40f74cb3` produced valid YAML and
returned child `RUN_OUTCOME: split_required`. Its executor-environment finding
matched documentation examples printed by the child, rather than runtime errors:

```text
`failed to open state db`, `failed to initialize state runtime`, or
`state db discrepancy`; keep ordinary migration plans and successful migration
```

These lines occur in CONTRIBUTING.md's Executor transcript diagnostics section.
They were copied into the human-readable child transcript on stderr and
substring-matched by `classify_executor_environment`. The first run retained a
`state_runtime_failure` issue, a validation error, and `primary_failure: false`.
The child return code was zero. Supervisor's own nonzero exit for split-required
is a separate convention; this defect does not explain or change that exit rule.

The successful follow-up run
`20261029T183152Z-SG-SPEC-0064-356a72ac` had no such issues. Its candidate remains
review-pending. The observation was first retained in PR #827 and logged in the
local collector; that coordination note alone did not create graph-visible work.

## Existing contract and proposed repair

The existing CONTRIBUTING.md rule already requires narrative text to remain
outside runtime findings and calls for classifier plus run-artifact regressions.
The repair restores this implementation boundary. It does not create a new
canonical spec, redefine successful refinement, approve previous candidates or
discard the original finding from historical artifacts.

Separate Codex runtime diagnostics from model/tool transcript data at launch.
Continue reading authoritative protocol markers from the final-message file.
Retain transcript data for inspection, while keeping it outside classification.
Preserve actual state errors, usage/transport diagnostics and supervisor timeout
handling, including genuine diagnostics accompanying a successful child.

## Graph routing and closure

Use the existing native `user_intent`, `operator_request` and proposal-lane
formats. SG-SPEC-0003 is the affected observation/governance boundary; proposals
0039 (feedback/prevention), 0048 (run retention) and 0056 (executor adapter) are
related engineering context. This relationship does not claim those canonical
nodes define every parser detail.

The defect observation links reproduction, expected behavior, implementation and
regression evidence. A prepared fix remains review-pending until merged and
does not approve ontology candidates from the original runs. Historical raw
artifacts are retained, and replay under new code is labeled as a replay.
