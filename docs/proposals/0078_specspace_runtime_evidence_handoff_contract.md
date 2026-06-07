# SpecSpace Runtime Evidence Handoff Contract

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded external-consumer slice after
`0077 Agent Runtime Enforcement Evidence Registry`.

Source draft:

- `docs/archive/proposal_sources/0078_specspace_runtime_evidence_handoff_contract.md`

## Context

SpecGraph now emits report-only Agent Passport runtime enforcement evidence:

```text
runs/agent_runtime_enforcement_evidence_index.json
runs/agent_runtime_enforcement_evidence/supervisor-executor-adapter-smoke.json
```

The evidence index is still producer-owned. SpecSpace should not infer its
contract from proposal markdown or from ad hoc artifact probing. The existing
`external_consumer_handoff_packets` plane is the correct handoff surface for
the next consumer implementation slice.

## Goals

- Extend the stable SpecSpace consumer contract with
  `runs/agent_runtime_enforcement_evidence_index.json`.
- Make runtime enforcement evidence status display requirements explicit for
  SpecSpace.
- Keep the handoff in the existing external-consumer handoff packet plane.
- Preserve the privacy boundary: no machine-local paths, raw supervisor logs,
  raw validator logs, raw prompts, secrets, or raw passport material.

## Non-Goals

- Implementing SpecSpace UI or API changes.
- Accepting downstream SpecSpace evidence.
- Changing Platform deploy packaging.
- Claiming observed runtime enforcement.
- Introducing a new handoff artifact family.

## Contract Delta

The SpecSpace handoff artifact contract now includes:

```text
runs/agent_runtime_enforcement_evidence_index.json
```

The stable consumer-facing fields include:

- `artifact_kind`;
- `schema_version`;
- `summary`;
- `entries`;
- `viewer_projection`;
- `status`;
- `evidence_ref`;
- `safe_evidence_ref`;
- `required_checks`;
- `policy_required_checks_satisfied`.

SpecSpace is expected to render runtime evidence states as:

- `passed`;
- `failed`;
- `missing`.

Missing producer artifacts must degrade to a visible fallback state instead of
breaking the operator surface.

## Expected Runtime Behavior

`make external-handoffs` emits the existing SpecSpace handoff packet as
`ready_for_handoff` when the SpecSpace bridge is ready and the producer contract
is stable. The packet points to the runtime evidence index in addition to the
existing Agent Passport posture artifacts.

## Acceptance

This slice is complete when:

- the SpecSpace handoff packet includes
  `runs/agent_runtime_enforcement_evidence_index.json`;
- `tools/agent_passport_adoption_policy.json` declares the same consumer
  artifact and display states;
- focused tests prove the registry-level SpecSpace handoff remains
  `ready_for_handoff`;
- generated handoff JSON contains no local-only paths or raw logs;
- proposal tracking gates, `make agent-runtime-evidence`,
  `make external-handoffs`, and the full Python suite pass.
