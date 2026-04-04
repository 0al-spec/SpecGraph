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


## JSON Knowledge Search MVP

Use `tools/search_kg_json.py` to search nested conversation archives stored as JSON files.

Example:

```bash
python tools/search_kg_json.py "success criteria limitations" --json-dir /path/to/jsons --limit 15
```

The script traverses each JSON tree, indexes all string leaves, and prints ranked matches with:
- filename
- JSON path
- matched text preview


The tool also stores a request-response cache at `<json-dir>/.search_kg_cache.json` by default for fast repeated queries.
Use `--cache-file` to override location or `--no-cache` to disable it.
