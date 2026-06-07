# Agent Runtime Enforcement Evidence Registry

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded runtime slice after `0076 Agent
Passport Runtime Enforcement Evidence Plan`.

Source draft:

- `docs/archive/proposal_sources/0077_agent_runtime_enforcement_evidence_registry.md`

## Context

The Agent Passport line now has:

- declared Agent Passport references for current graph-facing surfaces;
- report-only schema validation through the Agent Passport CLI;
- classified runtime enforcement posture;
- per-posture evidence requirements in `runs/agent_verification_gap_index.json`.

`0076` intentionally did not introduce a new generated evidence family. This
slice adds the first one, still in report-only mode.

## Goals

- Materialize a generated `agent_runtime_enforcement_evidence_index` surface.
- Emit one safe runtime-smoke evidence detail artifact for
  `specgraph.supervisor.executor_adapter`.
- Keep evidence refs repository-relative and safe for downstream consumers.
- Make missing or contradictory producer state visible as non-passing evidence.
- Preserve the distinction between report-only evidence and observed runtime
  enforcement.

## Non-Goals

- Implementing runtime enforcement, sandboxing, policy engines, or agent launch
  control.
- Verifying Agent Passport signatures, lifecycle, revocation, trust stores, or
  integrity.
- Claiming `runtime_enforcement_state: observed` or
  `V8_runtime_enforcement_observed`.
- Changing SpecSpace UI.
- Changing Platform deploy packaging.

## Runtime Contract

The new builder writes:

```text
runs/agent_runtime_enforcement_evidence_index.json
runs/agent_runtime_enforcement_evidence/supervisor-executor-adapter-smoke.json
```

The detail artifact has `artifact_kind:
agent_runtime_enforcement_evidence` and records:

- `evidence_id`;
- `agent_surface`;
- `evidence_kind`;
- `runtime_enforcement_state`;
- `posture_claim`;
- `status`;
- `safe_evidence_ref`;
- `evidence.checks`;
- `result`.

The index has `artifact_kind:
agent_runtime_enforcement_evidence_index` and summarizes evidence entries by
status, evidence kind, and viewer filters.

## Smoke Semantics

The initial smoke target is `specgraph.supervisor.executor_adapter`.

It passes only when:

- the Agent Passport surface is present;
- an Agent Passport reference is declared;
- the supervisor executor adapter index is present;
- the evidence artifact path is a safe repository-relative reference;
- the record does not claim observed runtime enforcement.

This smoke is useful evidence for `runtime_enforcement_policy_only`, but it does
not close the policy-only runtime posture gap by itself.

## Expected Runtime Behavior

`make agent-runtime-evidence` builds current Agent Passport derived surfaces,
writes the existing Agent Passport artifacts, then writes the runtime evidence
detail and index.

If producer state is missing or contradictory, the evidence entry remains
visible with `status: missing` or `status: failed`, and the index summary emits
`next_gap: repair_runtime_enforcement_evidence`.

If the smoke passes, the index summary emits
`next_gap: review_runtime_enforcement_evidence`.

## Acceptance

This slice is complete when:

- `make agent-runtime-evidence` succeeds;
- `runs/agent_runtime_enforcement_evidence_index.json` is produced;
- the supervisor executor adapter smoke detail artifact is produced;
- focused tests cover passed and missing evidence states;
- generated JSON contains no machine-local paths, raw supervisor logs, raw
  prompts, secrets, or raw passport material;
- proposal tracking gates and the full Python suite pass.
