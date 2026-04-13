---
name: specgraph-supervisor
description: Operate the SpecGraph supervisor for bounded refinement, explicit targeted runs, loop mode, gate resolution, split proposal flows, child materialization, and supervisor runtime diagnosis. Use when working in the SpecGraph repository and you need to choose the correct supervisor command, run it safely, interpret outcome or gate state, or continue a spec branch without losing supervisor context.
---

# SpecGraph Supervisor

Read these files before the first supervisor action in the repo:

- `/Users/egor/Development/GitHub/0AL/SpecGraph/docs/supervisor_manual.md`
- `/Users/egor/Development/GitHub/0AL/SpecGraph/CONSTITUTION.md`
- `/Users/egor/Development/GitHub/0AL/SpecGraph/AGENTS.md`

Assume repository root:

```bash
/Users/egor/Development/GitHub/0AL/SpecGraph
```

## Core Rules

- Prefer `--target-spec` over broad loop mode unless the user explicitly wants a batch run.
- Work on one spec node at a time unless the supervisor itself materializes one bounded child.
- Treat clean `split_required` as a structural signal, not as a runtime failure.
- Treat invalid worktree YAML, transport issues, and timeout residue as runtime problems first.
- Read `runs/latest-summary.md` and the specific `runs/<RUN_ID>.json` after every meaningful run.

## Default Commands

Dry-run selection:

```bash
python3 tools/supervisor.py --dry-run
```

One targeted refinement:

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --execution-profile standard
```

Targeted refinement with model override:

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --execution-profile standard --child-model gpt-5.3-codex-spark
```

Explicit child materialization:

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0027 \
  --operator-note "Materialize one new child spec for the remaining bounded concern." \
  --run-authority materialize_one_child \
  --execution-profile materialize
```

Split proposal emission:

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --split-proposal
```

Apply approved split proposal:

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --apply-split-proposal
```

Resolve a review gate:

```bash
python3 tools/supervisor.py --resolve-gate SG-SPEC-0003 --decision approve
```

Verbose runtime debugging:

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --verbose
```

## Interpretation Rules

Use this interpretation order:

1. Read `completion_status`.
2. Read `outcome`.
3. Read `gate_state`.
4. Read `validation_errors`.
5. Read `required_human_action`.

Apply these defaults:

- `completion_status: progressed` means the run moved the graph forward, even if `outcome: split_required`.
- `gate_state: split_required` with clean validation means the next move is structural decomposition, not cosmetic tightening.
- `gate_state: blocked` with executor-environment issues means repair runtime first.
- Repeated small policy-text diffs with repeated clean `split_required` usually mean the node reached plateau and needs child materialization or split proposal flow.

## Minimal Post-Run Checks

For one or two changed spec files:

```bash
python3 tools/spec_yaml_format.py specs/nodes/SG-SPEC-0003.yaml
python3 tools/spec_yaml_lint.py specs/nodes/SG-SPEC-0003.yaml
```

When changing supervisor runtime code:

```bash
pytest -q tests/test_supervisor.py
ruff check tools/supervisor.py tests/test_supervisor.py
python3 -m compileall tools/supervisor.py
```

## Decision Heuristic

- Continue ordinary targeted refinement when the node still yields bounded, non-repetitive semantic tightening.
- Switch to explicit child materialization when clean `split_required` repeats and the remaining concern is nameable.
- Switch to split proposal mode when the restructuring exceeds one direct bounded child step.
- Stop and report a blocker when the next correct move would change ontology, policy, or supervisor authority.
