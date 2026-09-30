# Controlled change to an ontology count criterion

## Question and scope

Does extraction reduce the actual edit surface when an existing criterion
changes, and does SpecificationCore improve it further than ordinary extraction?

The synthetic change counts `accepted_with_conditions` in the existing
`accepted` bucket. It is applied only to disposable copies of the count layer.
The application's taxonomy, validators, readiness, operator actions, and public
schemas are unchanged. This is not an end-to-end adoption of a new decision state.

Sources are pinned to baseline `425078cc74e1c2cccbff259b5505b1b958b8e904` and
extracted revision `38d85167d59f4a77f67235154d8ce3d4caa577a5`. The ordinary control
is the frozen fixture from that extracted revision. The runner produces isolated
before/after cohorts and actual unified patches, formatted by Ruff 0.15.9.

## Results

| Observation | Inline baseline | Ordinary extraction | SpecificationCore |
| --- | ---: | ---: | ---: |
| Edited files | 2 | 1 | 1 |
| Edited criterion definitions | 3 | 1 | 1 |
| Added / removed source lines | 15 / 3 | 5 / 1 | 4 / 1 |
| Edited report-builder files | 2 | 0 | 0 |
| Counting regions with changed behavior | 3 | 3 | 3 |
| After-change matrix mismatches | 0 | 0 | 0 |
| Selected-function CC sum, before → after | 96 → 96 | 85 → 85 | 85 → 85 |
| Selected-function Cog sum, before → after | 118 → 118 | 100 → 100 | 100 → 100 |
| Cohort source lines, before → after | 8309 → 8321 | 8330 → 8334 | 8344 → 8347 |
| Clone pairs, before → after | 23 → 23 | 23 → 23 | 23 → 23 |
| Duplicated lines / tokens, both phases | 161 / 978 | 161 / 978 | 161 / 978 |

CC: radon 6.0.1; Cog: complexipy 8.0.1. The scope is the three report-builder
functions plus the aggregation function where present. Predicate lambdas remain
single comparisons. jscpd 5.0.11 scans the complete two/three-file production
cohorts at 30 tokens / 3 lines. Experimental harnesses and tests are excluded.

Ordinary extraction and SpecificationCore have the same file and definition
edit surface. Their one-line difference reflects formatting of the predicate
expression; it does not establish a meaningful maintainability advantage.

All three count regions change behavior in every variant. **Edit surface**
decreases, while the **behavioral impact scope** remains three consumers. A shared
rule also propagates an incorrect criterion to every consumer, so the regression
contract should cover every use. This exercise does not measure defect rate,
developer time, review difficulty, churn, or production incidents.

## Verification and fault probe

Each before/after variant is checked on all sequences of length 0 through 4
over six state values: 1555 cases per consumer, three consumers per variant.
Before ignores the synthetic alias; after counts it as accepted. Other buckets,
unknown/unhashable values, input immutability, and missing-key errors are checked.

The runner executes the actual assignment regions extracted from the full
production function ASTs. It excludes surrounding validation and I/O, which
would reject the hypothetical state. The shared modules load under distinct
before/after names, preventing accidental reuse of a prior variant's imports.

An intentionally incomplete baseline edit updates only the first of three
definitions. The matrix detects 774 mismatches in each of the two stale regions
(1548 consumer-case failures). Both extracted variants propagate their single
edit correctly to all three regions. A single shared test harness covers the
variants; no claim is made about fewer test-file edits in a real feature change.

The [curated snapshot](data/ontology_decision_change.json) records source refs,
source and runner SHA-256 digests, patches' line counts, matrix outcomes, and
classic metric summaries. `status: pass` requires successful matrices and the
expected detection of the incomplete edit. A result file alone is not a pass.

## Reproduce

Use a fresh output directory and a checkout containing the pinned Git history:

```bash
.venv/bin/python tests/fixtures/ontology_decision_counts/change_exercise.py \
  --output-dir /tmp/decision-change-run

for phase in before after; do
  uv run --no-project --with complexipy==8.0.1 --with radon==6.0.1 \
    --python .venv/bin/python python tests/fixtures/ontology_decision_counts/measure.py \
    --input-dir /tmp/decision-change-run/$phase \
    --output-dir /tmp/decision-change-run/metrics-$phase
  for variant in baseline conventional specification; do
    npx --yes jscpd@5.0.11 /tmp/decision-change-run/$phase/$variant \
      --format python --min-tokens 30 --min-lines 3 --reporters json \
      --output /tmp/decision-change-run/clones-$phase-$variant --silent
  done
done

.venv/bin/python -m pytest -q tests/test_ontology_decision_change_exercise.py
```

CI unit tests use the frozen three-block fixture and current specification module
to exercise transformations, matrices, and missed-edit detection without requiring
Git history in a shallow checkout. They do not recompute the curated production
snapshot. The manual pinned-history run above provides that measurement.

## Next question

Measure a complete domain-rule change in isolated copies, including validation
and all affected projections. That will show how much of the total edit surface
belongs to the shared rule and how much belongs to distinct responsibilities.
