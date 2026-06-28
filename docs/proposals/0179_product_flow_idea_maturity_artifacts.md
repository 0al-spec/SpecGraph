# 0179 Product Flow Idea Maturity Artifacts

Status: implemented.

## Problem

Proposal `0178` added a Metrics RFC-aligned producer for
`runs/idea_maturity_metrics_report.json` and a validation target for
`runs/idea_maturity_metrics_validation_report.json`. SpecSpace can now show an
`Idea maturity` section, but a normal product repair run can still leave those
artifacts missing unless an operator remembers to run the metrics targets
separately.

That makes the product workspace look stale even when the repair chain itself
has produced enough evidence for the metrics report. The product idea-to-spec
flow should leave behind its own public-safe maturity surface as part of the
standard review output.

## Proposal

Add a small product-lane wrapper:

```bash
make product-workspace-idea-maturity
```

The wrapper runs:

```bash
make idea-maturity-metrics
make idea-maturity-metrics-validate
```

Then append that wrapper to the end of the standard product review targets:

```bash
make product-workspace-decision-backed-repair-chain
make product-workspace-repaired-promotion-handoff
```

This keeps `make product-workspace-active-candidate` narrow. Active candidate
generation remains the fast baseline path, while decision-backed repair and
repaired promotion handoff become dashboard-ready product review paths.

The Metrics repository remains the source of truth for the RFC/schema/validator.
SpecGraph still only produces and validates the report by invoking the Metrics
CLI; it does not copy validator logic or become the metrics contract authority.

## Authority Boundary

This slice is lifecycle wiring only:

- no prompt-agent execution;
- no mutation of canonical specs;
- no mutation of candidate source artifacts;
- no Ontology package writes;
- no ontology term acceptance;
- no candidate approval decision;
- no Git branch, commit, PR, merge, or read-model publication;
- no SpecSpace mutation authority.

The produced maturity report remains observability-only. It can explain whether
the candidate appears ready, blocked, dry-run, published, or not reached, but it
cannot perform approval, promotion, or publication.

## Acceptance Criteria

- `make product-workspace-idea-maturity` builds the metrics report and then
  runs Metrics validation.
- `make product-workspace-decision-backed-repair-chain` ends by producing both
  maturity artifacts.
- `make product-workspace-repaired-promotion-handoff` ends by producing both
  maturity artifacts.
- `make product-workspace-active-candidate` remains unchanged and does not run
  metrics validation.
- The public bundle still includes
  `runs/idea_maturity_metrics_report.json` and
  `runs/idea_maturity_metrics_validation_report.json`.
- SpecSpace can rely on the standard product/repaired flow outputs without
  asking operators to run a separate metrics command.

## Validation

- `tests/test_idea_maturity_metrics_report.py`
- `tests/test_static_artifact_bundle.py`
- `make proposal-tracking-gate`
- `make docc-sync`
- `make publish-bundle`
