# Tools

## Minimal Spec-Node Supervisor MVP

This repository includes a local MVP that orchestrates **specification nodes** (not tasks):

- Spec nodes live in `specs/nodes/*.yaml`.
- The supervisor script is `tools/supervisor.py`.
- Run logs are written to `runs/`.

Run locally:

```bash
python tools/supervisor.py
```

The supervisor loop is:

`pick spec gap -> refine spec -> validate -> update state`
