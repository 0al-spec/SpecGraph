---
name: specgraph-supervisor-runtime-debug
description: Diagnose whether a SpecGraph supervisor result is a runtime failure or a real spec-structure blocker. Use when a run shows broken YAML, transport or startup issues, timeout residue, noisy stderr, unexpected lifecycle drift, or any case where it is unclear whether the supervisor runtime or the target spec is at fault.
---

# SpecGraph Supervisor Runtime Debug

Read first:

- `/Users/egor/Development/GitHub/0AL/SpecGraph/docs/supervisor_manual.md`

Assume repo root:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
```

Start here:

```bash
cat runs/latest-summary.md
```

Then inspect the exact run payload:

```bash
python3 - <<'PY'
from pathlib import Path
import json
runs = sorted(Path('runs').glob('*-SG-SPEC-*.json'))
print(runs[-1])
print(json.loads(runs[-1].read_text())['outcome'])
PY
```

Classify as runtime first when you see:

- invalid worktree YAML
- executor transport/startup/sandbox failures
- timeout residue without accepted canonical content change
- profile mismatch or noisy stderr without validator failure

Classify as real spec blocker when you see:

- clean `split_required`
- clean reconciliation complaints
- repeated no-op tightening with no runtime anomalies

Default rule:

- `split_required` plus clean validation is not a runtime failure
- malformed candidate YAML is usually a runtime failure first

If you change runtime code, run:

```bash
pytest -q tests/test_supervisor.py
ruff check tools/supervisor.py tests/test_supervisor.py
python3 -m compileall tools/supervisor.py
```
