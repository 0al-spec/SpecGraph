# Ontology decision-state counts pilot

## Contract and hypothesis

Baseline: `425078cc74e1c2cccbff259b5505b1b958b8e904`.

Three blocks in `ontology_imports.py` and
`ontology_owner_decision_import_v2.py` independently count `accepted`,
`rejected`, and `needs_clarification`. This pilot extracts only those counts.
Operator authority, source validation, readiness, import eligibility, CLI
behavior, JSON fields, and timestamps retain their existing contracts.

Hypothesis: one shared definition removes repeated interpretation from report
assembly and narrows the edit surface for a change to an existing bucket.
The conventional control isolates extraction from the use of SpecificationCore.
No claim is made about a reduction in bugs or long-term churn from this snapshot.

## Implementations

- Baseline: three inline blocks, each with three filtered sums.
- Conventional: one frozen `DecisionStateCounts` value and a shared function
  containing the same three filtered sums.
- SpecificationCore: the same value and function, with three named
  `PredicateSpec` definitions in `tools/ontology_decision_state_spec.py`.

Both extracted variants use identical caller code and preserve three passes over
the prepared rows. State matching is exact, unknown values are ignored, and a
missing `decision_state` still raises `KeyError`. The functions accept a sequence
of mappings, matching the lists assembled by the existing callers.

The conventional control and frozen baseline blocks are experimental fixtures
under `tests/fixtures/ontology_decision_counts/`, not production dependencies.
They load under distinct module names in the behavior matrix.

## Snapshot results

Tools: radon 6.0.1 (CC), complexipy 8.0.1 (Cog), jscpd 5.0.11
(Python, 30 tokens / 3 lines, default mode).

| Function | Baseline CC / Cog | Conventional CC / Cog | SpecificationCore CC / Cog |
| --- | ---: | ---: | ---: |
| `build_ontology_owner_decision_report` | 21 / 29 | 15 / 23 | 15 / 23 |
| `build_ontology_decision_import_preview` | 37 / 47 | 31 / 41 | 31 / 41 |
| `build_owner_decision_import_v2` | 38 / 42 | 32 / 36 | 32 / 36 |
| Shared `count_decision_states` | absent | 7 / 0 | 7 / 0 |
| Sum over these functions | 96 / 118 | 85 / 100 | 85 / 100 |

These are selected-function sums, not whole-project sums. The shared function
retains its three loops and filters. The SpecificationCore variant also has
three predicate lambdas, each a single equality expression with no conditional
branch. They are listed separately rather than treating unreported lambda
complexity as eliminated work.

Source cohort: the two complete consumer modules and, for extracted variants,
the new shared module. Test and measurement fixtures are excluded.

| Measure | Baseline | Conventional | SpecificationCore |
| --- | ---: | ---: | ---: |
| Production source lines | 8309 | 8330 | 8344 |
| Modules | 2 | 3 | 3 |
| Imports between cohort modules | 1 | 3 | 3 |
| Inline counting blocks in consumers | 3 | 0 | 0 |
| State equality definitions for counting | 9 | 3 | 3 |
| jscpd clone pairs | 23 | 23 | 23 |
| jscpd duplicated lines / tokens | 161 / 978 | 161 / 978 | 161 / 978 |

The manual count of repeated state definitions is supported by the behavior
matrix; it is not a clone-detector metric. jscpd does not identify the selected
blocks as clones at this configuration, so its unchanged totals do not measure
this semantic deduplication. A smaller percentage due to additional source lines
is not an improvement in absolute duplication.

The local complexity reduction and narrowed criterion edit surface are shared
by both extracted variants. SpecificationCore adds 14 source lines over the
conventional control and gives predicates explicit reusable identities. This
experiment does not demonstrate a complexity advantage for SpecificationCore
over conventional extraction.

## Behavior and change footprint

The behavior matrix enumerates all sequences of length 0 through 4 over five
values: the three known states, an unknown string, and `None` (781 cases).
Every case matches all three frozen baseline blocks and both extracted variants.
Additional cases cover case/whitespace sensitivity, booleans, numbers,
unhashable unknown values, missing keys, and result immutability. Artifact parity
tests compare complete report dictionaries against the original counting logic;
the v2 test fixes the clock and covers all three supported states.

For a criterion-only change to an existing bucket, the code edit surface goes
from three blocks across two files to one shared definition in one file. This
is a structural observation, not a timed maintenance experiment. Both extracted
variants have the same benefit. Tests and policy validation may also need edits.

Adding a fourth externally visible counter is a different change: it requires
the result type, shared aggregation, all affected JSON summaries, validation,
and consumers to evolve. It cannot honestly be described as a one-file change.
Other checks of `decision_state` remain in validation and import policy because
they serve different responsibilities.

## Reproduce

Run from the repository root with its Python environment:

```bash
.venv/bin/python -m pytest -q tests/test_ontology_decision_state_spec.py \
  tests/test_ontology_import_policy.py tests/test_ontology_owner_decision_import_v2.py

uv run --no-project --with complexipy==8.0.1 --with radon==6.0.1 \
  --python .venv/bin/python python tests/fixtures/ontology_decision_counts/measure.py \
  --output-dir /tmp/specgraph-decision-counts-benchmark

for variant in baseline conventional specification; do
  npx --yes jscpd@5.0.11 /tmp/specgraph-decision-counts-benchmark/$variant \
    --format python --min-tokens 30 --min-lines 3 --reporters json \
    --output /tmp/specgraph-decision-counts-benchmark/clones-$variant --silent
done
```

Use a fresh output directory for each experiment. The runner reads the pinned
baseline through Git and the current working-tree production sources. Therefore
these recorded numbers apply to this pilot revision; later source changes will
produce a different snapshot. Metrics dependencies are optional and do not enter
production dependencies or the blocking CI test environment.

## Next experiment

The criterion-only exercise is now recorded in
[Controlled change to an ontology count criterion](ontology_decision_change.md).
It measures real patches and distinguishes edit surface from behavioral impact.

Choose a repeated behavioral dispatch, rather than another three-counter
aggregate. Confirm semantic equivalence first, then use the same before/ordinary/
SpecificationCore comparison. Exercise a controlled change to an existing rule
and record actual changed files, lines, and affected consumers, together with
parity, complexity, and absolute duplication.
