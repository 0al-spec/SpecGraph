---
name: specgraph-supervisor-split-proposal
description: Emit one bounded split proposal for a targeted SpecGraph node when the next correct step is proposal-first decomposition rather than another ordinary refinement or direct child-materialization pass. Use when a node is still structurally oversized, the change exceeds one immediate bounded child step, and canonical spec files should not be mutated directly yet.
---

# SpecGraph Supervisor Split Proposal

Read first:

- `/Users/egor/Development/GitHub/0AL/SpecGraph/docs/supervisor_manual.md`

Assume repo root:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
```

Run:

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --split-proposal
```

After the run:

1. Read `runs/latest-summary.md`.
2. Read the exact `runs/<RUN_ID>.json`.
3. Inspect the proposal artifact under `runs/proposals/`.

Interpretation:

- proposal artifact present and canonical specs unchanged = correct result
- direct canonical spec edits during `--split-proposal` = invalid run
- if the node only needs one clearly bounded new child, prefer child-materialization instead
