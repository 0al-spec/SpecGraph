# Supervisor Performance, Yield, and Graph-Impact Measurement

## Status

Draft proposal

## Problem

SpecGraph is already capable of running bounded supervisor passes that:

- refine canonical spec nodes
- emit or apply split-oriented changes
- clear review gates
- materialize new child specs
- improve graph shape over time

This is now valuable enough that simple anecdotal judgment is no longer
sufficient.

Today, the project can observe isolated signals such as:

- timeout or executor failures
- validation errors
- split outcomes
- maturity changes on individual nodes

But it still lacks a formal measurement layer for the supervisor itself.

Without that layer, several questions remain under-specified:

- Is the supervisor getting faster, or just producing more noise?
- Is a run productive because it wrote a diff, or because it improved the
  graph?
- How much effort is wasted on repeated no-op retries, stale tails, or runtime
  anomalies?
- When should a long batch stop because it has reached a plateau?
- How should future quality metrics such as `pre-SIB` or `SIB` relate to more
  basic runtime and yield measurements?

If SpecGraph is to evolve toward guided autonomous improvement, supervisor
performance must become a first-class observable system, not an informal
impression.

## Goals

- Define a structured measurement model for supervisor behavior.
- Separate runtime stability metrics from supervisor effectiveness metrics and
  graph-impact metrics.
- Make per-run and per-batch supervisor yield machine-readable.
- Support future plateau, oscillation, and stop-condition logic in the
  evaluator loop.
- Provide a stable bridge between today's operational measurements and future
  graph-quality metric families such as `pre-SIB` and `SIB`.
- Keep the measurement model implementation-agnostic enough that different
  runtimes or agent models can still be compared under one contract.

## Non-Goals

- Final formulas for `pre-SIB`, `SIB`, or other future graph-quality metrics
- A single magic score that replaces all other measurements
- A finished dashboard or viewer UX
- Full benchmark infrastructure for every model and profile combination
- Immediate automatic optimization of supervisor behavior based on metrics alone

## Core Proposal

Supervisor measurement should be formalized as three distinct layers:

1. Runtime performance
2. Supervisor yield and effectiveness
3. Graph impact

These layers answer different questions and must not be collapsed into one
number too early.

## Layer 1: Runtime Performance

This layer measures whether a supervisor run executed reliably and efficiently
as a runtime process.

Representative metrics:

- `run_duration_sec`
- `time_to_first_output_sec`
- `time_to_first_canonical_diff_sec`
- `timeout_occurred`
- `executor_failure`
- `validation_failure`
- `yaml_repair_applied`
- `worktree_load_failure`
- `child_run_count`
- `child_timeout_budget_sec`

Purpose:

- detect runtime instability separately from graph quality
- compare execution profiles and models on bounded tasks
- identify transport, formatting, or child-executor issues that masquerade as
  spec-quality failures

Important boundary:

This layer says whether the run operated cleanly. It does not by itself say the
run was useful.

## Layer 2: Supervisor Yield and Effectiveness

This layer measures whether the supervisor produced a meaningful bounded result
for the requested work item.

Representative metrics:

- `productive_run`
- `canonical_diff_written`
- `accepted_canonical_diff`
- `new_child_materialized`
- `gate_cleared`
- `split_required`
- `split_required_productive`
- `no_op_run`
- `same_spec_repeat_count`
- `retry_loop_count`
- `review_required`
- `proposal_emitted`

Purpose:

- distinguish useful runs from merely completed runs
- measure waste caused by repeated retries or empty canonical results
- separate productive `split_required` decomposition from failed ordinary runs
  that only ended in `split_required` after validation pressure

Important boundary:

A run can be runtime-clean but still low-yield. For example:

- no runtime errors
- valid YAML
- but no accepted canonical delta

That should count as low effectiveness, not as runtime failure.

## Layer 3: Graph Impact

This layer measures whether the graph became healthier after one run or one
batch.

Representative metrics:

- `status_delta`
- `maturity_delta`
- `blocked_nodes_delta`
- `review_pending_delta`
- `frozen_nodes_delta`
- `reviewed_nodes_delta`
- `new_atomic_child_specs_count`
- `root_pressure_delta`
- `weak_linkage_signal_delta`
- `stalled_maturity_signal_delta`

Purpose:

- quantify whether supervisor work actually improves the graph
- compare targeted interventions by graph effect rather than only by local diff
- support future plateau and stop-condition logic in evaluator loops

Important boundary:

Graph impact is the most important layer, but it should be interpreted using
the lower layers.

Example:

- a run that improves one node but creates two new blockers is not equivalent
  to a clean monotonic improvement
- a run that freezes one spec after three wasteful retries should not be scored
  the same as a clean one-pass freeze

## Required Per-Run Metrics

Every supervisor run should eventually emit a normalized measurement record
containing at least:

- `run_id`
- `target_spec_id`
- `run_kind`
- `execution_profile`
- `child_model`
- `run_duration_sec`
- `productive_run`
- `canonical_diff_written`
- `accepted_canonical_diff`
- `new_child_materialized`
- `split_required`
- `split_required_productive`
- `validation_failed`
- `runtime_failed`
- `yaml_repair_applied`
- `status_before`
- `status_after`
- `maturity_before`
- `maturity_after`
- `graph_signal_delta_summary`
- `same_spec_repeat_count`

This should be treated as a first-class runtime artifact rather than inferred
later from loosely structured logs.

## Batch Aggregation

Per-run metrics are necessary but not sufficient.

The system should also aggregate bounded batches, for example:

- one targeted intervention sequence
- one `--loop` batch
- one stress test using a specific model/profile pair

Batch-level metrics should minimally support:

- `runs_total`
- `runs_productive`
- `runs_no_op`
- `runs_runtime_failed`
- `runs_validation_failed`
- `new_specs_materialized`
- `gates_cleared`
- `frozen_delta`
- `reviewed_delta`
- `blocked_delta`
- `median_run_duration_sec`
- `same_spec_repeat_hotspots`

This makes it possible to answer:

- whether a whole batch was worth the time it consumed
- which nodes repeatedly absorb iterations without meaningful return
- when a batch is nearing a plateau

## Waste and Plateau Semantics

The proposal assumes that supervisor performance is not only about positive
yield, but also about bounded waste.

Candidate waste indicators:

- repeated no-op runs on the same spec
- runtime-clean runs with no accepted canonical result
- validation failures caused by preventable serialization defects
- repeated `review_required` without subsequent gate resolution
- repeated continuation on already mature linked nodes with no net graph gain

Candidate plateau indicators:

- low or zero graph-impact delta across several consecutive runs
- repeated same-spec continuation with diminishing maturity or status returns
- positive local diffs that no longer improve global blocked/reviewed/frozen
  balance

These indicators should later feed evaluator stop conditions, but the
measurement proposal should define them before the evaluator begins optimizing
against them.

## Composite Scores Should Come Later

The system may eventually want composite indicators such as:

- `supervisor_yield_score`
- `batch_efficiency_score`
- `graph_progress_score`

But this proposal argues that composites should be derived only after the raw
measurements are stable.

Premature single-score optimization would make it too easy to:

- overweight speed over graph quality
- count any diff as success
- hide repeated waste behind one aggregate number

## Relationship to Existing Work

### Evaluator Loop

This proposal gives the evaluator loop a measurable substrate.

Without per-run and per-batch supervisor metrics, the evaluator cannot
meaningfully classify:

- progress
- regression
- oscillation
- plateau
- wasted intervention budget

### Vocabulary Proposal

Terms such as:

- `productive_run`
- `no_op_run`
- `runtime_failed`
- `graph_impact`
- `plateau`
- `waste_rate`

should eventually become part of the machine-readable vocabulary layer rather
than remain informal operator jargon.

### Typed Validation

Typed validation findings are a natural input into the measurement layer.

For example:

- validation findings can feed `validation_failed`
- safe repair can feed `yaml_repair_applied`
- graph validators can feed signal-delta summaries

### Future `SIB` / `pre-SIB`

Operational performance metrics should not replace future graph-intelligence
metrics.

Instead, they should provide the stable lower layer on top of which those more
semantic metrics can later be interpreted.

## Suggested Next Spec Slices

- `Supervisor run measurement record`
- `Batch aggregation and hotspot detection`
- `Waste-rate and plateau classification`
- `Graph-impact delta contract`
- `Stop-condition semantics for metric-guided batches`

## Open Questions

- Which metrics must be persisted in canonical tracked artifacts versus
  ephemeral run logs only?
- When should a proposal-lane improvement count as graph-impact improvement if
  canonical graph state is unchanged?
- Should `maturity_delta` be interpreted differently for `outlined ->
  specified`, `specified -> linked`, and `reviewed -> frozen` transitions?
- What is the minimum viable composite score, if any, before `pre-SIB` and
  `SIB` exist?
- How should the system compare two runs that both improve the graph, but with
  different runtime cost and different waste profiles?
