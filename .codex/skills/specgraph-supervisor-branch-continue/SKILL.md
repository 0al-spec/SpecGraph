---
name: specgraph-supervisor-branch-continue
description: Reconstruct the current state of one SpecGraph supervisor branch and choose the next bounded step. Use when work resumes after several runs or merges and you need to recover the active parent, child nodes, gates, latest run outcomes, and the most likely next deterministic supervisor action without rereading the whole graph.
---

# SpecGraph Supervisor Branch Continue

Read first:

- `/Users/egor/Development/GitHub/0AL/SpecGraph/docs/supervisor_manual.md`

Assume repo root:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
```

Use this for one branch only.

Start from the current branch root or active node, then inspect:

1. the target spec file
2. direct `depends_on` and `refines` neighbors
3. the latest `runs/<RUN_ID>.json` for the active node
4. current `gate_state`, `last_outcome`, and reconciliation hints

Minimal pattern:

```bash
cat runs/latest-summary.md
python3 tools/supervisor.py --dry-run
```

What to decide:

- ordinary targeted refine
- child materialization
- split proposal
- apply split proposal
- gate resolution
- runtime debug first

Rule:

- do not summarize the whole graph
- recover only the local branch needed for the next bounded move
- if the branch shows repeated clean `split_required`, treat that as a structural continuation signal, not as generic “more refinement”
