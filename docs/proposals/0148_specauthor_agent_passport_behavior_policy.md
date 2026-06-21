# 0148 SpecAuthorAgent Agent Passport Behavior Policy

## Status

Implemented

## Summary

SpecAuthorAgent now has a local Agent Passport draft with an experimental
`x-behaviorPolicies` declaration.

The declaration links the agent's `compose_specification` capability to the
SpecGraph authoring contracts introduced by `0126`, `0136`, `0137`, `0143`,
`0144`, `0145`, and `0146`:

- prompt contract: `specgraph.prompt-contract.claim-calibration.v0.1`;
- generated artifact contract: `specgraph.specauthor.generated-spec-artifact.v0.1`;
- invocation artifact contract: `specgraph.specauthor.invocation-artifact.v0.1`;
- ontology write gate: `specgraph.write_gate.claim_calibration.v0.1`.

## Implementation

This slice adds `tools/agent_passports/specauthor-agent.passport.yaml` and
registers it in `tools/agent_passport_adoption_policy.json` as the
`specgraph.specauthor_agent` surface.

The behavior policy requires:

- ontology/domain/context resolution;
- ontology layer refs;
- model applicability refs;
- F/G/R calibration for strong claims;
- `ContextCompletionRequest` when the active frame is incomplete.

## Authority Boundary

The passport declaration is report-only. It does not make
`x-behaviorPolicies` runtime security enforcement, does not execute a prompt
agent, does not mutate canonical specs, does not write Ontology packages, and
does not import owner decisions.

## Validation

- `make agent-passports PYTHON=.venv/bin/python`
- `tests/test_supervisor.py`
