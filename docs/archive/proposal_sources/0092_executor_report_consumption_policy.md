# Executor Report Consumption Policy

## Draft Plan

Add the policy layer that defines how a valid
`runs/local_operator_executor_report.json` may be consumed after `0091`.

The report is useful evidence, but it is not authority. This slice must define
allowed consumers, allowed transformations, allowed effects, forbidden effects,
and the authority boundary before any proposal-producing or patch-producing
workflow is implemented.

## Scope

- Add `executor_report_consumption_policy` to
  `tools/supervisor_executor_adapter_policy.json`.
- Define allowed consumers for local executor reports.
- Define allowed transformations from report input to reviewable downstream
  candidates.
- Define allowed effects and forbidden effects.
- Preserve the invariant that reports are input/evidence, not canonical truth.
- Add supervisor validation helpers for consumers, transformations, effects,
  authority boundary, and source report validation.
- Do not run a new executor task.
- Do not create proposals from reports.
- Do not apply patches.
- Do not mutate canonical specs.
- Do not add SpecSpace or Platform behavior.

## Validation Intent

- focused executor report consumption policy tests
- existing executor report smoke tests
- proposal tracking gates
- full Python suite
