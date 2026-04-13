---
name: specgraph-supervisor-apply-split
description: Apply one approved SpecGraph split proposal into canonical parent and child specs. Use when an explicit split proposal already exists, is ready for application, and the next step is deterministic canonical materialization plus parent-child reconciliation rather than emitting a new proposal.
---

# SpecGraph Supervisor Apply Split

Read first:

- `/Users/egor/Development/GitHub/0AL/SpecGraph/docs/supervisor_manual.md`

Assume repo root:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
```

Run:

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --apply-split-proposal
```

After the run:

1. Read `runs/latest-summary.md`.
2. Confirm parent and child canonical files were updated.
3. Validate changed spec YAML.
4. Check that refinement and dependency links are coherent.

Minimal checks:

```bash
python3 tools/spec_yaml_format.py specs/nodes/SG-SPEC-0003.yaml
python3 tools/spec_yaml_lint.py specs/nodes/SG-SPEC-0003.yaml
```

Interpretation:

- changed parent plus new or updated child specs with clean validation = correct apply path
- stale refinement-chain errors after apply mean the next step is graph reconciliation, not another proposal emit
