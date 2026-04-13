---
name: specgraph-supervisor-child-materialize
description: Run one explicit SpecGraph supervisor child-materialization pass for a targeted spec when ordinary refinement has reached a clean structural plateau and the next bounded step is to create exactly one new child spec. Use when a node repeatedly returns clean split_required, the remaining concern is nameable, and the run should use operator_note plus run_authority materialize_one_child instead of another ordinary pass.
---

# SpecGraph Supervisor Child Materialize

Read first:

- `/Users/egor/Development/GitHub/0AL/SpecGraph/docs/supervisor_manual.md`
- `/Users/egor/Development/GitHub/0AL/SpecGraph/AGENTS.md`

Assume repo root:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
```

Use this skill only when all are true:

- the target already hit clean `split_required`
- repeated ordinary runs no longer produce meaningful new narrowing
- one remaining bounded concern can be named

Run:

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0027 \
  --operator-note "Materialize one new child spec for the remaining bounded concern." \
  --run-authority materialize_one_child \
  --execution-profile materialize
```

After the run:

1. Read `runs/latest-summary.md`.
2. Read the specific `runs/<RUN_ID>.json`.
3. Confirm a new spec file was created.
4. Validate parent and child YAML.

Minimal checks:

```bash
python3 tools/spec_yaml_format.py specs/nodes/SG-SPEC-0027.yaml specs/nodes/SG-SPEC-0029.yaml
python3 tools/spec_yaml_lint.py specs/nodes/SG-SPEC-0027.yaml specs/nodes/SG-SPEC-0029.yaml
```

Interpretation:

- new child file + clean validation = real structural progress
- clean `split_required` with no child = the node is still at plateau; switch to split proposal or refine the naming of the bounded concern
- invalid YAML or executor issues = runtime/debug path, not child-materialization success
