# Agent Passport Runtime Enforcement Evidence Plan

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded runtime slice after `0075 Agent
Passport Enforcement Next-Gap Consistency`.

Source draft:

- `docs/archive/proposal_sources/0076_agent_passport_runtime_enforcement_evidence_plan.md`

## Context

The Agent Passport line now has stable graph-side surfaces:

- every current graph-facing surface has a declared Agent Passport reference;
- report-only schema validation runs through the Agent Passport CLI;
- runtime enforcement posture is classified as `policy_only`, `boundary_only`,
  or `deferred`;
- SpecSpace consumes and displays the posture artifacts.

The remaining gap is not whether runtime enforcement is implemented. It is the
evidence contract that will allow a future surface to claim `observed`
enforcement without silently upgrading a policy declaration into a runtime
fact.

## Goals

- Define the minimum evidence shape for future runtime enforcement observation.
- Keep `observed` enforcement gated by a safe evidence reference.
- Attach per-gap evidence requirements to the existing
  `agent_verification_gap_index` so operators can see what would close each
  posture gap.
- Preserve report-only semantics: current surfaces remain unobserved until
  runtime evidence exists.
- Keep generated artifacts free of local paths, raw supervisor logs, raw
  prompts, raw passport material, and secrets.

## Non-Goals

- Implementing a sandbox, policy engine, or enforcement daemon.
- Running agents through Agent Passport enforcement.
- Verifying signatures, trust stores, lifecycle, revocation, or integrity.
- Changing SpecSpace UI.
- Changing Platform deploy packaging.
- Creating a new generated artifact family for enforcement evidence.

## Evidence Contract

This slice adds a plan-only `agent_runtime_enforcement_evidence` contract to
the Agent Passport adoption policy. A future observed evidence record must name:

- `agent_surface`;
- `runtime_enforcement_state`;
- `evidence`;
- `result`.

Accepted evidence kinds are intentionally small:

- `policy_decision`;
- `sandbox_trace`;
- `runtime_smoke`;
- `audit_log`;
- `test_report`;
- `operator_attestation`.

The contract also states privacy boundaries: no machine-local paths, raw
supervisor logs, raw prompts, or secrets.

## Runtime Gap Semantics

`runtime_enforcement_policy_only` is eligible for future observed promotion
only after policy-decision and runtime-smoke evidence exists.

`runtime_enforcement_boundary_only` is eligible for observed promotion only
after consumer-boundary policy-decision and audit-log evidence exists.

`runtime_enforcement_deferred` is not eligible for observed promotion until the
runtime surface exists.

`runtime_enforcement_evidence_missing` is emitted when a surface claims
`runtime_enforcement_state: observed` but has no safe evidence reference. This
prevents an `observed` posture from becoming a silent assertion.

## Expected Runtime Behavior

`runs/agent_verification_gap_index.json` continues to be the existing derived
artifact. Runtime posture gaps now include `runtime_enforcement_evidence_plan`
metadata with:

- contract artifact kind and schema version;
- plan status;
- eligibility for observed promotion;
- required evidence kinds;
- next action;
- privacy boundary.

No new `runs/*` artifact is introduced in this slice.

## Acceptance

This slice is complete when:

- `make agent-passports` succeeds;
- current policy data still reports no `runtime_enforcement_unknown` gaps;
- runtime posture gaps include evidence-plan metadata;
- an `observed` surface without evidence produces
  `runtime_enforcement_evidence_missing`;
- an `observed` surface with a safe evidence reference does not produce that
  missing-evidence gap;
- proposal tracking gates and the full Python suite pass.
