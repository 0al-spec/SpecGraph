# 0146 SpecAuthor Prompt-Side Authoring Flow

## Status

Implemented

## Summary

SpecGraph now has a deterministic, review-only authoring-flow wrapper for
`SpecAuthorAgent`.

The wrapper does not execute an LLM. It represents the prompt-side behavior
boundary that must exist after a draft is produced: the active ontology frame,
model applicability data, generated draft artifact, generated-artifact contract
report, write-gate report, and final invocation artifact contract report are
assembled into one typed chain.

## Implementation

This slice adds:

- `tools/specauthor_prompt_side_authoring_policy.json`;
- `tools/specauthor_authoring_flow.py`;
- `make specauthor-authoring-flow`;
- ready fixtures and regression tests.

The flow writes:

- `runs/specauthor_invocation_artifact.json`;
- `runs/specauthor_invocation_artifact_contract_report.json`;
- `runs/specauthor_authoring_flow_report.json`.

## Authority Boundary

This proposal does not grant new authority.

It does not:

- execute prompt agents;
- publish raw prompts or raw model output;
- write Ontology packages or lockfiles;
- mutate canonical specs;
- accept ontology terms;
- import owner decisions;
- bypass `specauthor-generated-artifact-contract`;
- bypass `specauthor-ontology-write-gate`.

## Validation

- `tests/test_specauthor_authoring_flow.py::test_specauthor_authoring_flow_builds_ready_invocation_artifact`
- `tests/test_specauthor_authoring_flow.py::test_specauthor_authoring_flow_blocks_missing_frame_and_applicability`
- `tests/test_specauthor_authoring_flow.py::test_specauthor_authoring_flow_blocks_low_r_decision_from_write_gate`
- `tests/test_specauthor_authoring_flow.py::test_specauthor_authoring_flow_cli_writes_invocation_and_contract`

## Follow-ups

- Publish the new SpecAuthor invocation artifacts as public-safe `runs/`
  surfaces.
- Add a SpecSpace Ontology Workbench lane for the invocation chain.
- Add experimental Agent Passport `x-behaviorPolicies` for `SpecAuthorAgent`.
