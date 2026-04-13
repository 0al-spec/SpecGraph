---
name: specgraph-supervisor-plateau-detect
description: Detect when a SpecGraph node has reached structural refinement plateau under ordinary supervisor runs. Use when repeated targeted runs keep returning clean split_required or only tiny policy-text changes, and you need to decide whether to switch to child materialization, split proposal flow, or stop further ordinary refinement.
---

# SpecGraph Supervisor Plateau Detect

Read first:

- `/Users/egor/Development/GitHub/0AL/SpecGraph/docs/supervisor_manual.md`

Assume repo root:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
```

Inspect:

```bash
cat runs/latest-summary.md
python3 - <<'PY'
from pathlib import Path
import yaml
spec = yaml.safe_load(Path('specs/nodes/SG-SPEC-0003.yaml').read_text())
print(spec['status'], spec['maturity'], spec.get('gate_state'), spec.get('last_outcome'))
PY
```

Treat it as plateau when most are true:

- repeated clean `split_required`
- validation errors are empty
- recent diffs are only small policy-text restatements
- no new child was materialized
- the remaining concern is still structurally nameable

Next move:

- one bounded remaining concern: use child-materialization
- larger restructuring: use split-proposal
- runtime anomalies present: switch to runtime-debug first
