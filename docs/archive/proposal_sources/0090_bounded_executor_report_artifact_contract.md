# Bounded Executor Report Artifact Contract

## Draft Plan

Define the generic report artifact contract that follows `0089` bounded
executor task smoke. The goal is contract-first: validate the shape and safety
boundary for future executor/producer reports without running a new agent task
or allowing canonical mutation.

## Scope

- Add `runs/local_operator_executor_report_contract.json`.
- Add `make executor-report-contract`.
- Define the future local-only report target:
  `runs/local_operator_executor_report.json`.
- Support generic producer categories:
  `coding_agent`, `harvester`, `operator_tool`, `external_harness`.
- Support report kinds:
  `analysis_report`, `package_candidate_report`, `proposal_draft`,
  `patch_suggestion`, `validation_summary`.
- Validate that reports remain `report_only` or `proposal_only`.
- Require `canonical_mutation_attempted=false`.
- Require safe repo-relative evidence refs.
- Reject raw logs, raw prompts, raw responses, secrets, and absolute paths.
- Do not run Codex, Pi, SpecHarvester, or any other producer in this slice.
- Do not publish the local contract or future local reports in the static
  bundle.

## Compatibility Pressure

The contract must not be Codex-specific. Codex is the first local executor, but
SpecHarvester already acts as a real producer of package candidate evidence for
SpecPM. The contract therefore needs neutral names such as `producer_kind`,
`authority_level`, `report_kind`, and `source_evidence_refs`.

## Validation Intent

- `make executor-report-contract`
- focused executor report contract tests
- static bundle exclusion test
- proposal tracking gates
- full Python suite
