# LLM-Driven Bootstrap Smoke Benchmark

## Status

Implemented

## Problem

SpecGraph currently has strong unit and targeted integration coverage for
runtime helpers, YAML repair, gate handling, and supervisor selection logic.

What it does not have is a cheap end-to-end benchmark that answers a simpler
question:

- can supervisor still build a structurally acceptable graph from a minimal
  bootstrap seed without human steering?

This gap matters because many regressions are not visible in unit tests:

- a run can be locally valid but produce no useful decomposition
- graph shape can degrade while YAML and validation still pass
- supervisor can become wasteful or stall even when runtime code remains green
- a small prompt or evaluator change can silently reduce graph-building yield

At the same time, a normal deterministic test is the wrong tool:

- LLM output is nondeterministic
- exact node text is not a stable oracle
- model upgrades will change wording without necessarily changing quality

So the project needs a different artifact:

- a cheap, repeatable, LLM-driven smoke benchmark
- judged by structural graph quality and bounded invariants
- not by exact textual snapshots

## Goals

- Define a lightweight bootstrap benchmark for supervisor.
- Verify graph-building from a minimal seed artifact with a fixed run budget.
- Use structural and lifecycle invariants rather than exact text matching.
- Keep the benchmark cheap enough for regular manual or scheduled execution.
- Produce machine-readable summary output that can be compared across runs.
- Detect regressions in yield, graph validity, and graph shape.

## Non-Goals

- A deterministic golden snapshot test for exact spec wording
- A replacement for unit or integration tests
- Full validation of the future intent layer
- A final benchmark framework for every model and every graph region
- A blocking default PR gate in GitHub Actions
- Immediate automatic tuning of supervisor based on benchmark results

## Core Proposal

Introduce one LLM-driven bootstrap smoke benchmark that runs supervisor from a
minimal seed artifact and evaluates the resulting graph by structural
invariants.

This benchmark should:

- run in an isolated temporary graph fixture
- start from one bounded seed artifact, not a raw natural-language user prompt
- use a fixed iteration budget
- use a cheap model profile
- emit a structured benchmark report

The benchmark is successful when the resulting graph is structurally
acceptable, even if the exact phrasing of nodes differs between runs.

## Why It Starts From a Seed Artifact

The project does not yet have a completed intent layer.

Therefore, a benchmark that starts from a raw user sentence would mix several
concerns:

- intent interpretation
- operator mediation
- proposal or bootstrap framing
- supervisor execution
- graph quality evaluation

That would make failures ambiguous and reduce signal quality.

The benchmark should therefore start from a minimal seed artifact that already
represents the initial graph-facing concept.

This keeps the benchmark focused on supervisor's responsibility:

- decomposition
- graph shaping
- lifecycle progression
- runtime stability

## Benchmark Scope

The initial benchmark should use one fixed micro-domain and one fixed budget.

Example envelope:

- one seed root
- `3-5` supervisor iterations
- bounded model budget
- no manual intervention
- no external proposal application step

This is intentionally small.

The benchmark is a smoke path, not a full autonomous graph-growth simulation.

## Structural Oracle

The benchmark should not compare exact text.

Instead it should evaluate a set of structural properties such as:

- all emitted YAML parses and passes canonical validation
- no cycles appear in refinement topology
- at least one meaningful child is materialized
- the seed subtree reaches a non-broken lifecycle state
- no stale runtime residue remains on canonical nodes
- no pathological serialization appears immediately
- supervisor does not spend the whole budget on no-op retries

The output should be judged by graph acceptability, not identical prose.

## Suggested Benchmark Metrics

Per run:

- `graph_valid`
- `runtime_failures`
- `validation_failures`
- `nodes_created`
- `new_child_count`
- `cycles_detected`
- `gate_states`
- `shape_signals`
- `terminal_outcome_mix`
- `productive_run_count`
- `no_op_run_count`

Aggregate summary:

- `bootstrap_success`
- `final_node_count`
- `final_edge_count`
- `final_root_status`
- `final_root_maturity`
- `serial_ladder_detected`
- `lower_boundary_handoff_detected`
- `benchmark_duration_sec`

## Pass Criteria

The benchmark should pass when all of the following hold:

- canonical graph state is valid at the end of the run
- no irrecoverable runtime failure occurred
- at least one productive structural step happened
- the resulting subtree is not trivially degenerate
- the root does not end in a corrupted or incoherent lifecycle state

The benchmark may still pass if:

- exact wording differs from prior runs
- maturity varies within a reasonable band
- the subtree ends in `linked`, `reviewed`, or bounded `split_required`
  depending on the fixed budget

The benchmark should fail if:

- YAML or validation errors survive to canonical state
- the run budget is spent with no meaningful graph progress
- the result is structurally broken
- the result is immediately dominated by pathological shape signals

## Recommended Runtime Position

This benchmark should initially be advisory, not blocking.

Recommended execution positions:

- manual maintainer run
- scheduled nightly or periodic workflow
- optional CI job triggered explicitly

It should not become a default blocking PR check until:

- the fixture is stable
- the benchmark variance is understood
- the pass criteria have proven robust across model drift

## Model Strategy

The benchmark should prefer a cheap model configuration.

The purpose is not maximum graph quality per run.

The purpose is to detect whether supervisor still produces a minimally
acceptable bounded graph under realistic low-cost conditions.

This makes smaller models acceptable, but only if the oracle stays structural
and tolerant to wording drift.

## Evaluator and Supervisor Use

The benchmark report should be consumable by evaluator and maintainers as a
regression signal, but it should not directly mutate canonical graph policy.

It should help answer questions such as:

- did a runtime change reduce productive graph growth?
- did a shape-signal change reduce graph quality?
- did a prompt or selection change increase waste?
- did a model change make bootstrap materially worse?

This makes the benchmark a performance and quality probe, not a source of
canonical truth.

## Risks

- Variance may still be high if the fixture is underspecified.
- A too-small budget may underreport valid progress.
- A too-large budget may hide early waste behind eventual success.
- Weak pass criteria may allow low-quality graphs to pass.
- Overly strict criteria may turn the benchmark into a flaky pseudo-test.

These risks reinforce the need to keep the first version:

- structurally judged
- cheap
- small in scope
- advisory rather than blocking
