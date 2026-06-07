# Agent Passport Runtime Enforcement Posture

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded runtime slice after `0071 Agent
Passport Report-Only Verification`.

Source draft:

- `docs/archive/proposal_sources/0072_agent_passport_runtime_enforcement_posture.md`

## Context

Proposal `0071` made Agent Passport report-only verification concrete:

```text
missing_passport_count: 0
verification_not_attempted_count: 0
verification_failed_count: 0
runtime_enforcement_unknown_count: 5
```

The remaining gap is no longer about missing references or schema validation.
It is about runtime enforcement posture. Leaving every surface as
`runtime_enforcement_unknown` hides important distinctions:

- some surfaces have declared policy but no enforcement runtime yet;
- some surfaces are external consumer or handoff boundaries;
- some surfaces are future runtime surfaces;
- observed enforcement is a future state, not the current report-only claim.

## Goals

- Replace default `runtime_enforcement_unknown` gaps with explicit runtime
  enforcement postures.
- Preserve honest report-only semantics: schema-valid passports do not imply
  runtime enforcement.
- Keep future and external-consumer surfaces distinguishable from active
  SpecGraph runtime surfaces.
- Keep generated artifacts free of local paths, raw passport material, raw
  validator logs, and secrets.
- Keep `make agent-passports` as the operator command.

## Non-Goals

- Implementing a runtime enforcement engine.
- Launching agents through an enforcement runtime.
- Changing SpecSpace UI.
- Changing Platform packaging or deploy.
- Claiming `V8_runtime_enforcement_observed`.
- Defining Agent Passport signing, trust stores, revocation, or lifecycle
  validation.

## Runtime Enforcement Postures

This slice introduces explicit runtime enforcement states:

| State | Meaning |
| --- | --- |
| `observed` | Enforcement evidence exists for the surface. Not used by this slice. |
| `policy_only` | Passport policy is declared and schema-valid, but no enforcement runtime exists yet. |
| `boundary_only` | The surface is an external consumer/handoff boundary; enforcement belongs to a consumer-boundary contract, not SpecGraph core runtime. |
| `deferred` | The surface is future-facing and enforcement waits for the runtime surface to exist. |
| `unknown` | Fallback for malformed or unclassified policy data. |

The gap index should emit concrete gap kinds for the first three non-observed
states instead of collapsing them into `runtime_enforcement_unknown`.

## Expected Runtime Artifacts

`runs/agent_surface_index.json` should classify surfaces by runtime enforcement
posture.

`runs/agent_verification_gap_index.json` should report:

```text
runtime_enforcement_unknown_count: 0
runtime_enforcement_policy_only_count: >0
runtime_enforcement_boundary_only_count: >0
runtime_enforcement_deferred_count: >0
```

The remaining gaps are still real, but they are now classified:

- policy-only runtime work for SpecGraph-owned executor/supervisor surfaces;
- consumer-boundary work for SpecSpace;
- deferred work for future product workspace agents.

## Acceptance

This slice is complete when:

- `make agent-passports` succeeds;
- `runtime_enforcement_unknown_count` is `0` for current policy data;
- generated gap kinds include `runtime_enforcement_policy_only`,
  `runtime_enforcement_boundary_only`, and `runtime_enforcement_deferred`;
- fallback `unknown` remains tested for malformed policy data;
- no runtime enforcement, SpecSpace UI, or Platform deploy change is introduced.

