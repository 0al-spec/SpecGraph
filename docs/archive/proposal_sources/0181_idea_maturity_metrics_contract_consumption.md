# 0181 Idea Maturity Metrics Contract Consumption

Status: implemented.

## Problem

SpecGraph already produces `runs/idea_maturity_metrics_report.json` and invokes
the Metrics repository CLI to write
`runs/idea_maturity_metrics_validation_report.json`. After Metrics introduced a
versioned validator contract package, SpecGraph should make the consumed
Metrics-owned schema, validator id, validator version, and compatibility policy
explicit in the producer artifact.

Without this metadata, downstream consumers can see that validation passed, but
cannot reliably display which Metrics contract was used or distinguish
SpecGraph-owned report shape from Metrics-owned schema authority.

## Proposal

Add a read-only `contract` object to `idea_maturity_metrics_report`:

```json
{
  "schema_version": 1,
  "schema_ref": "schemas/idea_maturity_metrics_report.schema.json",
  "validation_report_schema_ref": "schemas/idea_maturity_metrics_validation_report.schema.json",
  "validator_id": "metrics.idea_maturity_metrics.validator.v0.1",
  "validator_version": "0.1.0",
  "compatibility_policy": "additive_v1",
  "compatibility_policy_ref": "VALIDATOR_CONTRACT.md#compatibility-policy",
  "metrics_rfc_ref": "Metrics/IDEA_MATURITY_METRICS.md",
  "proposal_id": "0181"
}
```

This preserves existing `contract_ref` for SpecGraph-local consumers while
adding the Metrics-owned contract metadata expected by SpecSpace and Platform.

## Authority Boundary

This slice is metadata-only:

- no Metrics schema ownership transfer from Metrics to SpecGraph;
- no copied Metrics validator logic;
- no prompt-agent execution;
- no candidate approval decision;
- no Git branch, commit, PR, merge, or read-model publication;
- no canonical spec mutation;
- no Ontology package writes;
- no ontology term acceptance;
- no SpecSpace mutation authority.

## Acceptance Criteria

- `runs/idea_maturity_metrics_report.json` carries a `contract` object with
  Metrics schema, validation-report schema, validator id/version, and
  compatibility-policy refs.
- Existing `contract_ref` remains available for legacy SpecGraph consumers.
- `make idea-maturity-metrics-validate` still delegates to `METRICS_CLI`.
- Metrics validation still passes for produced reports.
- Public artifact publication remains report-only.

## Validation

- `tests/test_idea_maturity_metrics_report.py`
- `make idea-maturity-metrics`
- `make idea-maturity-metrics-validate`
- `make proposal-tracking-gate`
- `make docc-sync`
