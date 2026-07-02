# 0196 Idea Maturity Aggregate Answer Accounting

Status: implemented.

## Problem

Idea Maturity previously treated accepted repair answers as either
per-gap-materialized or unmaterialized. That was too coarse for real idea flows.

Some accepted answers are aggregate or control answers. They can be consumed by
the rerun overlay as closure evidence for the intake or repair process without
producing a node-scoped `ontology_gap_resolution` or `candidate_gap_resolution`
record. Counting those answers as ordinary unmaterialized debt creates false
readiness noise.

## Proposal

Extend `idea_maturity_metrics_report` answer materialization accounting so it
distinguishes:

- per-gap materialized answers;
- answers consumed by the rerun input overlay;
- aggregate/control answers;
- closure evidence answers;
- ordinary unmaterialized answers that still need action.

The report keeps existing summary fields compatible while making
`unmaterialized_answer_count` represent ordinary blocking debt, not aggregate
closure evidence.

Detailed accounting is emitted under:

```text
groups.answer_materialization
metrics.answer_accounting
```

## Authority Boundary

This proposal is report-only. It does not:

- apply answers to source artifacts;
- mutate candidate artifacts or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms globally;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models;
- execute prompt agents.

## Acceptance Criteria

- Aggregate/control answers consumed by the rerun overlay are counted as
  closure evidence.
- Aggregate/control answers are not counted as ordinary unmaterialized answer
  debt.
- Per-gap materialization remains counted separately.
- Existing summary fields remain backward-compatible.
- Metrics-owned schema/docs/examples describe the additive accounting fields.
- Existing Metrics validator accepts the updated examples.

## Validation

- `tests/test_idea_maturity_metrics_report.py`
- `python3 scripts/validate_idea_maturity_examples.py` in Metrics
