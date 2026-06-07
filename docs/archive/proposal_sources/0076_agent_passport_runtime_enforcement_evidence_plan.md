# Agent Passport Runtime Enforcement Evidence Plan

## Draft Intent

Close the next small Agent Passport gap after `0075`: define how a future
runtime surface may claim observed enforcement without implementing runtime
enforcement in this PR.

## Bounded Scope

- Add a plan-only runtime enforcement evidence contract to
  `tools/agent_passport_adoption_policy.json`.
- Attach evidence-plan metadata to existing runtime posture gaps in
  `runs/agent_verification_gap_index.json`.
- Treat `runtime_enforcement_state: observed` without a safe evidence reference
  as `runtime_enforcement_evidence_missing`.
- Preserve current report-only posture gaps and avoid any SpecSpace or Platform
  changes.

## Out of Scope

- No sandbox/enforcement runtime.
- No agent launches.
- No signature, revocation, lifecycle, or trust-store validation.
- No new generated evidence artifact.
- No SpecSpace UI or Platform deploy change.

## Acceptance Notes

The slice is valid if focused tests prove the evidence contract, evidence-plan
metadata, and observed-without-evidence guard, and the usual proposal gates plus
full tests pass.
