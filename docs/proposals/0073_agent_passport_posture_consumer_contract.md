# Agent Passport Posture Consumer Contract

## Status

Draft proposal

## Source Material

This proposal realizes the SpecGraph producer-side contract needed before
SpecSpace displays Agent Passport verification and runtime enforcement posture.

Source draft:

- `docs/archive/proposal_sources/0073_agent_passport_posture_consumer_contract.md`

## Context

Proposals `0056`, `0059`, `0067`, `0071`, and `0072` now produce stable
report-only Agent Passport artifacts:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_passport_verification_report.json
runs/agent_verification_gap_index.json
```

SpecSpace already consumes the first generation of agent/executor/passport
visibility through the external consumer handoff loop. The next consumer slice
needs the full verification and runtime posture contract, not only surface and
gap indexes.

## Problem

SpecSpace can display agent surfaces, but the handoff contract did not yet make
`known_agent_passport_index` and `agent_passport_verification_report` explicit
consumer artifacts. Without those paths and display-state semantics, SpecSpace
would have to infer verification posture from partial artifacts or proposal
markdown.

The contract must also preserve the report-only boundary:

- schema-valid passports do not imply runtime enforcement;
- `policy_only`, `boundary_only`, and `deferred` are visible posture states, not
  proof of enforced runtime behavior;
- `observed` remains reserved for future evidence-backed enforcement.

## Goals

- Extend the existing SpecSpace external handoff contract to include all
  Agent Passport posture artifacts.
- Declare the verification and runtime posture states SpecSpace may display.
- Require fallback states for missing or schema-mismatched producer artifacts.
- Preserve privacy boundaries for local paths, raw validator logs, raw passport
  material, and raw supervisor logs.
- Keep this as a producer contract slice without implementing SpecSpace UI.

## Non-Goals

- Implementing SpecSpace UI.
- Implementing runtime enforcement.
- Claiming observed enforcement.
- Changing Platform packaging or deploy.
- Changing Agent Passport schema, signing, lifecycle, revocation, or trust
  stores.
- Adding new external handoff artifact families.

## Contract

The SpecSpace consumer contract is declared in:

```text
tools/agent_passport_adoption_policy.json
tools/external_consumers.json
```

SpecSpace should consume these producer artifacts:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_passport_verification_report.json
runs/agent_verification_gap_index.json
```

SpecSpace may display these verification states/statuses:

- `V2_passport_referenced`;
- `V3_schema_valid`;
- `verification_failed`;
- `verification_unavailable`;
- `valid`;
- `invalid`;
- `unavailable`;
- `tool_unavailable`.

SpecSpace may display these runtime enforcement states:

- `policy_only`;
- `boundary_only`;
- `deferred`;
- `observed`;
- `unknown`.

The `observed` state must not be shown as current unless producer artifacts
contain evidence-backed observed enforcement.

## Validation

This slice is valid when:

- the SpecSpace handoff contract includes the full Agent Passport posture
  artifact list;
- the Agent Passport policy declares SpecSpace display and fallback states;
- focused tests prove the registry-level SpecSpace handoff remains
  `ready_for_handoff`;
- `make agent-passports`, `make external-handoffs`, proposal gates, and the full
  test suite pass.

