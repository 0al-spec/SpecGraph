# 0222 Workspace Structural Limits

RFC: SG-RFC-0222
Version: 0.1.0

## Status

Proposed contract with a bounded runtime realization in this PR. Canonical
specifications and repository defaults are unchanged. Merge is through review.

## Source Material

- [Pilot request](../archive/proposal_sources/0222_workspace_structural_limits.md)
- [Declarative supervisor policy](0016_declarative_supervisor_policy_and_decision_inspection.md)
- [Project environment](0052_product_workspace_governance_profile.md)

## Problem

Repository policy supports global thresholds, but different products cannot
configure structural budgets independently. Narrowing honest behavior solely
to fit five acceptance criteria can encourage artificial decomposition.

## Contract

An optional `supervisor.structural_limits` section in `specgraph.project.yaml`
has schema version 1 and an allowlisted `thresholds` mapping. Missing settings
inherit `tools/supervisor_policy.json`. Explicit workspace values take precedence.

Six count thresholds accept strict positive integers: acceptance, blocking
children, one-child chain, direct-child fan-out, exhausted chain and
over-atomized acceptance counts. Three graph coverage ratios accept finite
numbers in [0,1]. Unknown keys, unknown schema versions, bools, null values,
wrong mappings, and malformed configs fail closed before execution.

Raising or lowering structural counts is permitted without an arbitrary upper
ceiling. This is a structural budget, not a complexity proof. Governance,
selection priorities, review/admission gates and maturity cutoffs cannot be
changed through this section. Canonical constraints continue to apply.

The supervisor resolves a snapshot once at its entry boundary, restores that
scope on every exit, and uses it in candidate validation, changed-spec and
sync-back validation, reconciliation, split proposals, graph-shape diagnostics,
prompts and decision inspector. It does not change global defaults. Direct
library calls resolve their current root or share an explicit scope.

SpecificationCore for Python owns threshold-kind routing and value eligibility:
an ordered `FirstMatch` classifies count and ratio inputs, then named
`PredicateSpec` rules enforce their value contracts. The stable
`SG-RFC-0222.structural_limits.*` rule identifiers and trace outcomes are
included in the effective configuration evidence. YAML parsing and schema
version extraction remain at the I/O boundary.

Run evidence records effective thresholds and their deterministic digest,
per-key source, source-config digest/status and repository-policy digest.
Historical diagnosis consumes recorded limits and checks their digest. Legacy
runs lacking this field use repository defaults; their original workspace
configuration is unknown, not reconstructed or claimed verified. A digest
identifies bytes; it is not a signed or trusted receipt.

`--build-project-environment` exposes these values read-only. Configuration is
an operator-owned project artifact; a refinement prompt does not authorize its
mutation. Mid-run file changes take effect only at the next invocation.

## Acceptance and Evidence

1. Existing unconfigured atomicity behavior remains 5 criteria and 3 blocking
   children, proved by characterization and existing supervisor tests.
2. A configured workspace accepts seven criteria with limit eight and rejects
   nine; unrelated workspaces retain defaults.
3. Invalid configuration fails before loading specs or invoking an executor.
4. Prompts, validation, inspector and persisted run evidence agree; historical
   diagnostics remain stable when the current config changes.
5. Existing split/reconciliation/sync-back and governance behavior stays covered
   by the supervisor suite; focused tests cover override and corrupt evidence.

Runtime: `tools/supervisor_structural_limits.py`, `tools/supervisor.py`.
Tests: `tests/test_workspace_structural_limits.py`, `tests/test_supervisor.py`.

## Out of Scope

Automatic budget tuning, per-node overrides, disabling atomicity, execution
resource budgets, signed config approval, and changing Zeusus product behavior.
