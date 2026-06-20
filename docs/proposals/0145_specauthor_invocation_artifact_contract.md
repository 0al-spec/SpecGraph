# 0145 SpecAuthor Invocation Artifact Contract

## Status

Implemented

## Source

- `docs/archive/proposal_sources/0145_specauthor_invocation_artifact_contract.md`

## Summary

SpecGraph now has a typed, review-only `specauthor_invocation_artifact`
contract for `SpecAuthorAgent`.

The contract links operator intent, active ontology/domain/context/layer/model
applicability frame, generated artifact metadata, the generated artifact
contract report, the ontology write-gate report, and the operator decision
state.

## Motivation

`0126` defines the desired prompt behavior, while `0136`, `0137`, `0143`, and
`0144` establish write-gate, producer contract, layer context, and model
applicability data. The missing boundary is the invocation record that shows
which semantic frame a SpecAuthor draft was produced under and which validation
reports make it review-ready.

Without this boundary, prompt execution, draft output, validation reports, and
operator decisions can blur together.

## Implementation

This slice adds:

- `tools/specauthor_invocation_artifact_contract.py`;
- `make specauthor-invocation-artifact-contract`;
- ready and review-required fixtures;
- regression tests for ready, malformed, missing applicability, and strict CLI
  paths.

The validator checks:

- root contract shape and review-only authority boundary;
- `SpecAuthorAgent` invocation metadata and user intent;
- active ontology/domain/context/layer/model applicability frame;
- model applicability assumption and invalidation trigger refs;
- generated artifact contract report status;
- ontology write-gate report status;
- acknowledgement-only operator decision state.

## Authority Boundary

This proposal does not execute prompt agents.

It does not:

- change active prompts;
- infer missing ontology context or model applicability;
- invoke write gates automatically;
- materialize specs;
- write Ontology packages or lockfiles;
- mutate canonical specs;
- accept or reject ontology terms;
- import owner decisions;
- close semantic gates;
- add SpecSpace UI.

## Validation

- `tests/test_specauthor_invocation_artifact_contract.py::test_specauthor_invocation_artifact_contract_allows_ready_invocation`
- `tests/test_specauthor_invocation_artifact_contract.py::test_specauthor_invocation_artifact_contract_rejects_incomplete_chain`
- `tests/test_specauthor_invocation_artifact_contract.py::test_specauthor_invocation_artifact_contract_rejects_missing_applicability`
- `tests/test_specauthor_invocation_artifact_contract.py::test_specauthor_invocation_artifact_contract_strict_cli_exits_nonzero`

## Follow-ups

- Add the prompt-side `SpecAuthorAgent` behavior that emits this invocation
  artifact.
- Add Agent Passport `x-behaviorPolicies` once the behavior-policy declaration
  format is accepted.
- Feed invocation reports into richer SpecSpace review dashboards.
