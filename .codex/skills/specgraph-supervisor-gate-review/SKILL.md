---
name: specgraph-supervisor-gate-review
description: Inspect and resolve SpecGraph supervisor gate states for one bounded spec. Use when a target is in review_pending, blocked, retry_pending, split_required, or another gate state and you need to decide the next bounded action, prepare a human review decision, or run the correct resolve-gate command.
---

# SpecGraph Supervisor Gate Review

Read first:

- `/Users/egor/Development/GitHub/0AL/SpecGraph/docs/supervisor_manual.md`

Assume repo root:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
```

Inspect the target spec and latest run:

```bash
cat runs/latest-summary.md
python3 - <<'PY'
from pathlib import Path
import yaml
spec = yaml.safe_load(Path('specs/nodes/SG-SPEC-0003.yaml').read_text())
print(spec['gate_state'], spec.get('required_human_action'))
PY
```

Use this decision map:

- `review_pending`: resolve with `approve` or `retry`
- `blocked`: repair the blocker first; do not approve around it
- `retry_pending`: rerun after fixing the specific invalid or empty refinement cause
- `split_required`: do not blindly clear it; choose child materialization, split proposal, or another structural step

Resolve only when the right action is clear:

```bash
python3 tools/supervisor.py --resolve-gate SG-SPEC-0003 --decision approve
python3 tools/supervisor.py --resolve-gate SG-SPEC-0003 --decision retry
python3 tools/supervisor.py --resolve-gate SG-SPEC-0003 --decision split
```

Rule:

- resolving a gate is not a substitute for structural work
- use `approve` only for a review gate
- use `split` only when the correct next step is genuine decomposition
