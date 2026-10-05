# Source: Tests-Verified Evidence Admission Plan

Captured: 2026-10-05
Source class: operator-directed follow-up and read-only SpecGraph contract inspection

## Operator intent

After merging proposal 0224, the operator asked to plan the next step and submit
it as a pull request. The next step was identified as preparing the missing
`tests_verified` evidence evaluator plan, not implementing it.

## Inspected baseline

- SpecGraph main at preparation start: `4cfea97b7da737ff24e9d819f58f5c9a01e5766d`.
- `docs/evidence_claim_admission.md` says `tests_verified`, `effect_committed`,
  and `outcome_completed` remain `unknown / evidence_evaluator_unavailable`;
  source evidence does not promote them.
- `Sources/SpecGraph/Documentation.docc/ImplementationContractPack.md` repeats
  the same boundary and describes `runtime_verified_v1` as a separate live
  FeaturePassport `verify-decision` integration.
- Proposal 0224 is contract preparation only. It proposes explicit assertion
  bindings, stable evaluation/assertion correlation, and late-event
  invalidation, but no receipt issuance or admission.
- Proposal 0047 assigns provider-neutral issuance and signing to FeaturePassport
  and admission/mapping to SpecGraph. Receipt issuance and a trusted test-runner
  observation path remain separate prerequisites.

## Preparation boundary

This source and proposal do not claim that a test observation is trusted, that
FeaturePassport currently issues test-specific receipts, or that `tests_verified`
is implemented. The first runner adapter, receipt fields, trust semantics, and
claim mapping remain decisions for later owner-reviewed contracts.
