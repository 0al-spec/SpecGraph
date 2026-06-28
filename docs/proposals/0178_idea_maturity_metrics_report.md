# 0178 Idea-to-Spec Maturity Metrics Report

Status: implemented.

## Problem

The product `idea_to_spec` lane now emits a durable chain of review-only
artifacts: intake, candidate graph, clarification requests and answers,
ontology decisions, rerun preview/materialization, repaired handoff, repaired
active candidate, repaired promotion gate, and repaired repair-session journal.

Those artifacts prove the workflow can move a raw product idea toward an
approval-ready candidate, but SpecSpace and downstream operators still need a
single metrics surface that explains where the candidate matured, where it
stalled, and which handoffs still require action. Reconstructing that state
from many `runs/*.json` files in each consumer would duplicate policy logic and
risk collapsing distinct states such as `not_reached`, `not_available`,
`blocked`, and `dry_run`.

The Metrics repository now carries the draft
`idea_to_spec_maturity` RFC. SpecGraph needs a producer-side adapter that emits
that lifecycle telemetry without claiming approval or write authority.

## Proposal

Add a deterministic, read-only metrics producer:

```bash
make idea-maturity-metrics
make idea-maturity-metrics-validate
```

The producer target writes:

```text
runs/idea_maturity_metrics_report.json
```

The validation target invokes the sibling Metrics repository CLI and writes:

```text
runs/idea_maturity_metrics_validation_report.json
```

The report carries:

- `artifact_kind: idea_maturity_metrics_report`;
- `metric_pack_id: idea_to_spec_maturity`;
- `contract_ref: specgraph.idea-to-spec.maturity-metrics-report.v0.1`;
- source refs for the selected SpecGraph, SpecSpace, and Platform lifecycle
  artifacts;
- the closed Metrics RFC authority boundary with all write-capable flags set to
  boolean `false`;
- clarification load metrics;
- answer materialization metrics;
- ontology grounding metrics;
- candidate repair and blocker-closure metrics;
- workflow friction metrics;
- partial temporal metrics when timestamps exist;
- promotion, review, and publication states when downstream Platform artifacts
  are present;
- policy and invariant findings without discarding observed reality.

The report may be partial. Missing downstream stages should become
`not_reached` or `not_available`, not malformed output. Broken or stale source
refs become blocked telemetry so operators can see why the lifecycle should not
be trusted for approval.

The Metrics repository remains the source of truth for the RFC, schema, and
reference validator. SpecGraph must not copy validator logic. Instead it uses a
configurable external command:

```bash
METRICS_CLI="python3 ../Metrics/scripts/metrics.py" \
  make idea-maturity-metrics-validate
```

CI may point `METRICS_REPO` at a checked-out sibling such as
`external/Metrics`. The validation report records validator identity, schema
reference, report status, diagnostics, and the closed read-only authority
boundary without persisting machine-local binary paths or raw private logs.

## Authority Boundary

This slice is observability only:

- no prompt-agent execution;
- no mutation of canonical specs;
- no mutation of candidate source artifacts;
- no Ontology package writes;
- no ontology term acceptance;
- no candidate approval decision;
- no Git branch, commit, PR, merge, or read-model publication.

The metrics report can say that a candidate is approval-ready, promotion-ready,
blocked, dry-run, or published according to available evidence. It must not
perform any of those handoffs.

## Acceptance Criteria

- `make idea-maturity-metrics` writes
  `runs/idea_maturity_metrics_report.json`.
- The report uses `metric_pack_id: idea_to_spec_maturity` and references the
  Metrics RFC contract.
- The report preserves distinct state semantics for `not_reached`,
  `not_available`, `blocked`, `ready`, `dry_run`, and related lifecycle states.
- A repaired candidate with all ontology/product gaps resolved reports
  approval-ready lifecycle telemetry.
- Stale source refs are surfaced as blocked telemetry.
- Cross-field metric invariants are checked and reported.
- Zero-denominator rates are `null`, not `0`.
- The report is public-safe and included in the static bundle refresh.
- `make idea-maturity-metrics-validate` writes
  `runs/idea_maturity_metrics_validation_report.json` by invoking the Metrics
  CLI rather than copying validation logic into SpecGraph.
- Static bundle refresh publishes both the metrics report and its Metrics
  validation report.

## Validation

- `tests/test_idea_maturity_metrics_report.py`
- `make idea-maturity-metrics`
- `make idea-maturity-metrics-validate`
- `make proposal-tracking-gate`
- `make publish-bundle`
