# Supervisor Manual

This document is the practical operator and contributor guide for `tools/supervisor.py`.

Use it when you need to:

- understand what the supervisor is allowed to do
- run bounded refinement safely
- interpret run outcomes and gates
- debug runtime failures versus real spec-quality blockers
- continue work on an existing branch of the graph without losing context

For constitutional limits, see [CONSTITUTION.md](../CONSTITUTION.md).
For repository editing rules, see [AGENTS.md](../AGENTS.md).

## 1. Supervisor Role

The supervisor is an execution layer, not a governance layer.

It may:

- refine one bounded spec node at a time
- run targeted local graph refactors already allowed by current specs
- emit derived observations, signals, summaries, queues, and proposals
- materialize one bounded child spec when current policy and run authority allow it

It may not:

- silently redefine ontology
- silently redefine policy
- silently expand its own authority
- silently convert proposals into canonical truth

Short formula:

- SpecGraph governs
- supervisor executes
- run artifacts inform
- human approval resolves constitutional change

## 2. Core Working Model

The default loop is:

1. select one bounded target
2. create an isolated worktree
3. run a nested child executor
4. validate changed files and graph reconciliation
5. classify the result
6. sync accepted canonical changes
7. write run artifacts

The supervisor is intentionally narrow:

- one spec node at a time
- one bounded concern per run
- no silent scope expansion
- no broad opportunistic cleanup

## 3. Capability Map

Use this map first when you need to decide what the supervisor is for a
particular task.

- refine one bounded spec: `--target-spec SG-SPEC-XXXX`
- inspect what default selection would do: `--dry-run`
- batch bounded work aggressively: `--loop --auto-approve`
- inspect subtree shape and reflective signals without mutation:
  `--target-spec SG-SPEC-XXXX --observe-graph-health`
- emit one structured split proposal without canonical mutation:
  `--target-spec SG-SPEC-XXXX --split-proposal`
- apply one approved split proposal into canonical parent/child specs:
  `--target-spec SG-SPEC-XXXX --apply-split-proposal`
- resolve a human review gate:
  `--resolve-gate SG-SPEC-XXXX --decision approve`
- validate one normalized transition packet JSON file:
  `--validate-transition-packet path/to/packet.json`
  with optional profile override:
  `--validate-transition-packet path/to/packet.json --transition-profile specgraph_core`
- build a derived spec-to-code trace index:
  `--build-spec-trace-index`
- build a derived proposal runtime index:
  `--build-proposal-runtime-index`
- inspect stale review/runtime residue without refinement:
  `--list-stale-runtime`
- clean stale review/runtime residue:
  `--clean-stale-runtime`

## 4. Main Modes

### Default selection

```bash
python3 tools/supervisor.py
```

Uses selector heuristics to choose the next eligible bounded refinement.

### Explicit targeted refinement

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003
```

Use this when the operator already knows which spec to work on.

### Loop mode

```bash
python3 tools/supervisor.py --loop --auto-approve
```

Use only when you want an aggressive autonomous batch. It is effective, but it can stall on repeated no-op or structural blockers if the graph still has unresolved decomposition points.

### Graph-health observation

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --observe-graph-health
```

Non-mutating subtree inspection. Use this when you want to understand:

- shape pressure such as `depth_without_breadth`
- role-legibility signals such as `role_obscured_node`
- whether a subtree still contains active versus historical descendants
- what rewrite/merge action the current graph health recommends

### Split proposal mode

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --split-proposal
```

Generates a structured split artifact under `runs/proposals/` without mutating canonical specs.

### Apply split proposal mode

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --apply-split-proposal
```

Materializes an approved split proposal into canonical parent/child specs.

### Transition-packet validation

```bash
python3 tools/supervisor.py --validate-transition-packet transition-packet.json
```

Validates one normalized transition packet JSON file and prints structured
findings. This is a deterministic legality check, not a semantic-quality judge.

The validator now exposes:

- packet families: `promotion`, `proposal`, `apply`, `handoff`
- check families: `schema`, `legality`, `provenance`, `boundedness`,
  `authority`, `reconciliation`, `diff_scope`, `profile`
- validator profiles: `specgraph_core`, `product_spec`, `techspec`,
  `implementation_trace`

Use `--transition-profile ...` when you want to validate the same packet under
another governed artifact family without changing the packet file itself.

### Spec trace index

```bash
python3 tools/supervisor.py --build-spec-trace-index
```

Builds `runs/spec_trace_index.json` from literal `SG-SPEC-XXXX` mentions in
`tools/` and `tests/`, then enriches that graph-bound index with weak
`commit_refs`, `pr_refs`, `verification_basis`, and `acceptance_coverage`.

Use it as the first weak derived view of spec-to-code coverage. It is still not
an implementation-state oracle.

`implementation_state` is now derived conservatively from
`tools/spec_trace_registry.json`:

- no explicit trace contract: `unclaimed`
- declared contract with no matched anchors yet: `planned`
- declared contract with local changes on tracked surfaces: `in_progress`
- declared contract with implementation anchors only: `implemented`
- declared contract with both implementation and verification anchors: `verified`
- declared contract blocked by review or unresolved dependencies: `blocked`

The `drifted` state is reserved for freshness-aware derivation and is not yet
emitted by this command.

### Proposal runtime index

```bash
python3 tools/supervisor.py --build-proposal-runtime-index
```

Builds `runs/proposal_runtime_index.json` from `docs/proposals/`,
`tools/proposal_runtime_registry.json`, `tasks.md`, and repository markers in
`tools/` and `tests/`.

Use it when you want to inspect, for each proposal:

- processing posture
- runtime realization status
- validation closure
- observation coverage
- next reflective backlog gap

### Gate resolution

```bash
python3 tools/supervisor.py --resolve-gate SG-SPEC-0003 --decision approve
```

Use this after human review of a gated spec.

### Runtime residue inspection

```bash
python3 tools/supervisor.py --list-stale-runtime
python3 tools/supervisor.py --clean-stale-runtime
```

Use these when gates or worktrees look stale after interrupted runs. Inspect
first; clean second.

## 5. Important Targeted-Run Controls

### Operator note

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0027 \
  --operator-note "Materialize one new child spec for the remaining bounded concern."
```

`--operator-note` is ephemeral guidance for one run. It does not edit canonical specs.

Use it to:

- constrain scope
- request a narrower interpretation
- direct explicit child materialization
- bias a run toward a specific already-known concern

### Mutation budget

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0027 \
  --mutation-budget policy_text,schema_required_addition
```

Use `--mutation-budget` when an explicit targeted run should stay inside a
declared change surface. This is especially useful when you want a bounded pass
to tighten a node without allowing broad opportunistic edits.

### Run authority

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0027 \
  --operator-note "Materialize one new child spec for the remaining bounded concern." \
  --run-authority materialize_one_child
```

Authority matters. If the run asks for a new child but the authority does not grant it, child materialization is rejected.

Current high-value authority:

- `materialize_one_child`

### Execution profile

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --execution-profile standard
python3 tools/supervisor.py --target-spec SG-SPEC-0027 --execution-profile materialize
```

Current profiles:

- `fast`
- `standard`
- `materialize`

Use `materialize` when the run is expected to create a new child or do a heavier structural step.

### Child model and timeout

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0003 \
  --child-model gpt-5.3-codex-spark \
  --child-timeout 1200
```

Useful when:

- a branch is structurally heavy
- a root or near-root node needs longer bounded reasoning
- you want to compare model speed/quality tradeoffs

## 6. Derived Artifacts And Diagnostic Surfaces

The supervisor writes several different surfaces. They are not all equally
authoritative.

### Fast operator surfaces

- `runs/latest-summary.md`
  - quickest human snapshot of the last run
- `runs/<RUN_ID>.json`
  - full authoritative run payload for that run
- `runs/decision_inspector/<RUN_ID>.json`
  - standalone decision explanation artifact for that run

### Queue and proposal surfaces

- `runs/proposal_queue.json`
  - derived queue of proposal-oriented next moves
- `runs/refactor_queue.json`
  - derived queue of refactor-oriented next moves
- `runs/proposals/*.json`
  - structured proposal artifacts emitted by split-proposal mode
- `runs/spec_id_reservations.json`
  - temporary in-flight reservations for explicit child-materialization IDs

These runtime artifacts are now written with atomic replace plus a short-lived
sidecar lock. If a queue file is malformed, ordinary supervisor runs stop
instead of silently treating it as an empty queue.
Run logs and isolated worktree identities also carry a nonce so concurrent
runs do not collide on timestamp-only names.

Explicit child-materialization runs now reserve one child `SG-SPEC-XXXX` ID
for the active run and require the produced child file to use that reserved
path.

### Trace and inspection surfaces

- `runs/spec_trace_index.json`
  - first graph-bound spec trace artifact with `code_refs`, `test_refs`,
    `commit_refs`, `pr_refs`, `verification_basis`, weak
    `acceptance_coverage`, and a conservative `implementation_state`
- `tools/spec_trace_registry.json`
  - explicit strong trace contracts for deriving `implementation_state`
- `runs/proposal_runtime_index.json`
  - derived proposal runtime index with posture, realization, validation, and
    re-observation status
- `tools/supervisor_policy.json`
  - declarative policy layer for thresholds, priorities, queue defaults,
    mutation classes, and execution profiles
- `graph_health` payload in run logs
  - reflective signals, subtree-shape pressure, and recommended actions
- `decision_inspector` payload in run logs
  - compact explanation of how the supervisor classified one run

Use `runs/<RUN_ID>.json` when you need to answer:

- why this spec was selected
- why the gate state ended where it did
- which validators failed
- what queue items were emitted, cleared, or updated
- whether graph-health signals came from accepted canonical state or only from a
  candidate view

## 7. How To Read Outcomes

The supervisor writes authoritative run data to:

- `runs/latest-summary.md`
- `runs/<RUN_ID>.json`

Important fields:

- `outcome`
- `completion_status`
- `gate_state`
- `required_human_action`
- `validation_errors`
- `executor_environment`
- `refinement_acceptance`
- `reconciliation`
- `graph_health`
- `graph_health_truth_basis`
- `decision_inspector`

Machine-protocol invariant:

- a successful child executor run must emit both `RUN_OUTCOME:` and `BLOCKER:`
  markers on stdout
- missing markers are treated as executor protocol failure, not as an implicit
  `done`

### `done`

The run produced an accepted refinement path. Depending on approval mode, the spec may end in:

- `gate_state: review_pending`
- or directly `gate_state: none` after auto-approve

### `split_required`

This is not automatically a failure.

Interpretation:

- the run found a real decomposition boundary
- the current node still needs structural splitting or an intermediate child
- productive `split_required` may still contain valid canonical refinement

Important nuance:

- productive `split_required` may sync valid content changes
- but source lifecycle fields must remain canonical and coherent
- it must not leave impossible mixed states such as `reviewed + split_required`

### `retry`

Use when the run did not yield a usable refinement and should be attempted again after adjustment.

### `blocked`

There is a real blocker. Read `required_human_action`.

### `escalate`

The supervisor has reached a case that should move to a higher-authority review path.

## 8. Reading `decision_inspector`

`decision_inspector` is the compact operator-facing explanation layer in each
run log, and the same content is also written to
`runs/decision_inspector/<RUN_ID>.json`.

It has four slices:

- `selection`
  - which mode selected the spec, and with what rule inputs
- `gate`
  - final `outcome`, `gate_state`, `required_human_action`, `blocker`, and
    failing validators
- `diff_classification`
  - changed files, changed spec files, validation pressure, refinement
    acceptance, and the truth basis used for graph health
- `queue_effects`
  - signals, recommended actions, and queue transitions for proposal/refactor
    items

Each slice now includes `applied_rules`:

- `supervisor_policy` rules point back into `tools/supervisor_policy.json`
- `runtime_guard` rules explain procedural decisions such as validator failure,
  mutation-budget overflow, or blocker propagation

At top level, `policy_reference` records the policy artifact path and SHA-256
used for the run.

When queue state changed, look at:

- `emitted_ids`
- `cleared_ids`
- `updated_ids`

`updated_ids` matters because a queue item can stay present while its payload or
status changes.

## 9. Completion Status

The most important distinction is:

- `completion_status: progressed`
- `completion_status: failed`

`progressed` means the run moved the graph forward, even if it still ended in `split_required`.

Typical examples:

- a useful bounded refinement plus `split_required`
- a child spec materialized but the parent still needs another structural pass

`failed` means the run did not produce an authoritative step forward.

Typical examples:

- invalid worktree YAML with no accepted canonical writeback
- executor environment failure
- validation failure that blocks sync

## 10. Runtime Failure Versus Spec Failure

This distinction is critical.

Treat it as a runtime problem first when you see:

- broken worktree YAML
- transport or startup issues in child executor
- isolated worktree drift only
- timeout residue with no accepted canonical content change
- profile mismatch or child runtime drift

Treat it as a real spec-structure problem when you see:

- `split_required` with clean validation
- repeated no-op tightening on the same node
- reconciliation complaints about missing refinement chain
- persistent atomicity pressure after legitimate narrowing

In practice:

- invalid YAML is usually a runtime repair problem
- repeated clean `split_required` is usually a graph decomposition problem

## 11. Current Best-Practice Workflow

For one branch of the graph:

1. pick one target spec
2. use `--target-spec` instead of broad loop mode
3. if the run returns clean `split_required`, do not keep polishing forever
4. decide whether the next step is:
   - another bounded ordinary refinement
   - explicit child materialization
   - split proposal emission
   - parent/child refinement-chain reconciliation
5. validate canonical YAML
6. commit stable progress in small batches

Recommended validation after meaningful spec edits:

```bash
python3 tools/spec_yaml_format.py specs/nodes/SG-SPEC-XXXX.yaml
python3 tools/spec_yaml_lint.py specs/nodes/SG-SPEC-XXXX.yaml
```

For runtime changes:

```bash
pytest -q tests/test_supervisor.py
ruff check tools/supervisor.py tests/test_supervisor.py
python3 -m compileall tools/supervisor.py
```

## 12. Practical Heuristics

### When to continue ordinary refinement

Keep ordinary refinement when:

- the node still yields new bounded policy text
- validation is clean
- no repeated no-op behavior appears
- no new child is clearly implied yet

### When to switch to child materialization

Switch when:

- the same node repeats clean `split_required`
- the remaining concern is clearly nameable
- the parent has become an integration or gateway node
- one new intermediate spec would reduce direct child pressure or clarify refinement chain

### When to stop and declare plateau

You are likely at plateau when:

- repeated runs only restate the same boundary in different words
- no new child is created
- validation stays clean
- `split_required` persists with small policy-text diffs only

That usually means the next move is structural, not textual.

## 13. Current Known Patterns

These patterns have appeared repeatedly during bootstrap:

### Productive `split_required`

Useful and expected. Do not classify it as failure when:

- validation is clean
- canonical diff is meaningful
- the result narrows the next structural step

### Runtime YAML repair

The supervisor now repairs several recoverable malformed candidate-YAML cases before validation, but this should still be treated as runtime hardening, not as evidence that the target spec is conceptually weak.

### Refinement-chain reconciliation after subtree split

When a new intermediate node is added, the next blocker is often not the new child itself, but stale `refines` edges on its descendants.

Typical example:

- old chain: `A -> C`
- new intended chain: `A -> B -> C`
- required next step: change `C.refines` from `A` to `B`

### Selector plateau

Loop mode can waste time when it keeps selecting:

- already mature linked nodes
- repeated no-op refinements
- nodes that really need explicit split/materialization rather than more ordinary tightening

## 14. Recommended Document Map

Use the documents in this order:

1. [CONSTITUTION.md](../CONSTITUTION.md)
2. [AGENTS.md](../AGENTS.md)
3. this manual
4. [tools/README.md](../tools/README.md)
5. relevant spec nodes and current run artifacts

This manual should stay practical and process-oriented.

It should not replace:

- spec governance in canonical spec nodes
- constitutional rules in `CONSTITUTION.md`
- repository editing rules in `AGENTS.md`
