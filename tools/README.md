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

Supervisor modes:

- Default: pick the next eligible bounded refinement run.
- `--loop --auto-approve`: keep processing eligible work until the queue is empty.
- `--resolve-gate SPEC_ID --decision ...`: apply a human review decision.
- `--target-spec SPEC_ID --split-proposal`: run the explicit proposal-first split pass for one
  oversized non-seed spec and emit a structured artifact under `runs/proposals/` without editing
  canonical spec files.

Canonical YAML helpers for spec nodes:

```bash
python tools/spec_yaml_format.py
python tools/spec_yaml_lint.py
```

Both commands default to `specs/nodes/*.yaml`. The formatter rewrites files into the
repository's canonical YAML style; the linter enforces syntax, rejects duplicate keys,
and fails when a file has drifted from canonical formatting.


## JSON Knowledge Search MVP

Use `tools/search_kg_json.py` to extract and search structured requirement statements from nested
conversation archives stored as JSON files.

Example:

```bash
python tools/search_kg_json.py "success criteria limitations" --json-dir /path/to/jsons --limit 15
```

The script traverses each JSON tree, extracts requirement-like lines, classifies them (`goal`,
`constraint`, `acceptance`, `risk`, `scope`, `assumption`), and prints ranked matches with:
- filename
- JSON path
- requirement kind
- matched text preview

Filter by kind when needed:

```bash
python tools/search_kg_json.py "acceptance evidence" --json-dir /path/to/jsons --kind acceptance
```

The tool also stores a request-response cache at `<json-dir>/.search_kg_cache.json` by default for fast repeated queries.
Use `--cache-file` to override location or `--no-cache` to disable it.

## PageIndex Conversation Search

Use `tools/search_pageindex.py` to search indexed ChatGPT conversations through the local PageIndex API.
It is the companion search tool for the PageIndex manual in `tools/docs/PAGEINDEX_SEARCH_MANUAL.md`.

Example:

```bash
python3 tools/search_pageindex.py "agent orchestration" --top-k 10 --context
```

The script expects the PageIndex API to be running on `http://localhost:8765` and uses the
`~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json` catalog by default.
