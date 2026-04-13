# Supervisor Manual

This document is the practical operator and contributor guide for `tools/supervisor.py`.

Use it when you need to:

- understand what the supervisor is allowed to do
- run bounded refinement safely
- interpret run outcomes and gates
- debug runtime failures versus real spec-quality blockers
- continue work on an existing branch of the graph without losing context

For constitutional limits, see [CONSTITUTION.md](/Users/egor/Development/GitHub/0AL/SpecGraph/CONSTITUTION.md).
For repository editing rules, see [AGENTS.md](/Users/egor/Development/GitHub/0AL/SpecGraph/AGENTS.md).

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

## 3. Main Modes

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

### Gate resolution

```bash
python3 tools/supervisor.py --resolve-gate SG-SPEC-0003 --decision approve
```

Use this after human review of a gated spec.

## 4. Important Targeted-Run Controls

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

## 5. How To Read Outcomes

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

## 6. Completion Status

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

## 7. Runtime Failure Versus Spec Failure

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

## 8. Current Best-Practice Workflow

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

## 9. Practical Heuristics

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

## 10. Current Known Patterns

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

## 11. Recommended Document Map

Use the documents in this order:

1. [CONSTITUTION.md](/Users/egor/Development/GitHub/0AL/SpecGraph/CONSTITUTION.md)
2. [AGENTS.md](/Users/egor/Development/GitHub/0AL/SpecGraph/AGENTS.md)
3. this manual
4. [tools/README.md](/Users/egor/Development/GitHub/0AL/SpecGraph/tools/README.md)
5. relevant spec nodes and current run artifacts

This manual should stay practical and process-oriented.

It should not replace:

- spec governance in canonical spec nodes
- constitutional rules in `CONSTITUTION.md`
- repository editing rules in `AGENTS.md`
