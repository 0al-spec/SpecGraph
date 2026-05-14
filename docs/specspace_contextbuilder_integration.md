# SpecSpace / ContextBuilder Integration

This document describes the local integration between SpecGraph and
ContextBuilder, which is evolving into SpecSpace.

It is an operator setup guide, not a viewer contract. The individual JSON
contracts remain in the dedicated `*_viewer_contract.md` documents.

## Roles

- **SpecGraph** owns canonical specs, supervisor policy, derived `runs/*.json`
  artifacts, and viewer-facing contract docs.
- **ContextBuilder / SpecSpace** owns the browser UI, operator panels, local
  API passthrough endpoints, and read-only rendering of SpecGraph surfaces.
- **SpecSpace must not infer graph truth from Git history or filesystem
  heuristics** when a SpecGraph artifact exists. SpecGraph owns the mapping
  from graph state to viewer-ready read models.

## Default Local Ports

Use these defaults unless a local session explicitly overrides them:

| Component | URL | Notes |
| --- | --- | --- |
| ContextBuilder / SpecSpace UI | `http://127.0.0.1:5173/` | Vite dev server. |
| ContextBuilder API | `http://127.0.0.1:8001/` | Python API server. |
| SpecGraph repo root | `/Users/egor/Development/GitHub/0AL/SpecGraph` | Passed as `SPECGRAPH_DIR` / `--specgraph-dir`. |
| SpecGraph specs | `/Users/egor/Development/GitHub/0AL/SpecGraph/specs/nodes` | Passed as `SPEC_DIR` / `--spec-dir`. |

Do not assume `http://127.0.0.1:8766/` is the active viewer. That port can be
left over from an older app-browser session or a custom launch. The current
Makefile defaults are `5173` for UI and `8001` for API.

## Refresh SpecGraph Surfaces

Before checking the viewer after supervisor runs or PR merges, refresh the
derived SpecGraph surfaces:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
make viewer-surfaces
```

This rebuilds the common viewer-facing read models, including:

- `runs/graph_dashboard.json`
- `runs/graph_backlog_projection.json`
- `runs/graph_next_moves.json`
- `runs/proposal_runtime_index.json`
- `runs/proposal_promotion_index.json`
- `runs/proposal_spec_trace_index.json`
- `runs/spec_activity_feed.json`
- metric-pack, conversation-memory, SpecPM, review-feedback, and related
  derived surfaces included in the current `viewer-surfaces` build report.

For only the Recent Changes feed:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
make spec-activity
```

`runs/*.json` artifacts are local derived read models by default. Do not stage
or commit them unless a task explicitly promotes a curated artifact.

## Start ContextBuilder / SpecSpace

From the ContextBuilder checkout:

```bash
cd /Users/egor/Development/GitHub/0AL/ContextBuilder
make dev \
  PYTHON=/path/to/python3.10-or-newer \
  SPECGRAPH_DIR=/Users/egor/Development/GitHub/0AL/SpecGraph \
  SPEC_DIR=/Users/egor/Development/GitHub/0AL/SpecGraph/specs/nodes \
  API_PORT=8001 \
  UI_PORT=5173
```

If `python3` points to the macOS/Xcode Python 3.9 runtime, the API can fail on
newer typing features such as `typing.TypeGuard`. Use Python 3.10+ for the
ContextBuilder API process.

You can also run the API and UI separately:

```bash
cd /Users/egor/Development/GitHub/0AL/ContextBuilder
make api \
  PYTHON=/path/to/python3.10-or-newer \
  SPECGRAPH_DIR=/Users/egor/Development/GitHub/0AL/SpecGraph \
  SPEC_DIR=/Users/egor/Development/GitHub/0AL/SpecGraph/specs/nodes \
  API_PORT=8001
```

```bash
cd /Users/egor/Development/GitHub/0AL/ContextBuilder
make ui UI_PORT=5173
```

The UI dev server proxies `/api/*` to the API server. Browser checks should
normally open:

```text
http://127.0.0.1:5173/
```

## Verify The Connection

Check that the API is reading the intended SpecGraph checkout:

```bash
curl -sS 'http://127.0.0.1:8001/api/spec-activity?limit=3'
```

The response should include a metadata envelope whose `path` points at:

```text
/Users/egor/Development/GitHub/0AL/SpecGraph/runs/spec_activity_feed.json
```

The nested `data.generated_at` value should match the most recent
`make spec-activity` or `make viewer-surfaces` run.

For the dashboard:

```bash
curl -sS 'http://127.0.0.1:8001/api/graph-dashboard'
```

For the global backlog projection:

```bash
curl -sS 'http://127.0.0.1:8001/api/graph-backlog-projection'
```

## Recent Changes Data Flow

The Recent Changes panel should use the SpecGraph activity feed when available:

```text
SpecGraph
  make spec-activity
        |
        v
  runs/spec_activity_feed.json
        |
        v
ContextBuilder API
  GET /api/spec-activity?limit=N&since=ISO
        |
        v
SpecSpace UI
  Recent Changes -> Activity source
```

The feed exists because graph activity is broader than canonical
`specs/nodes/*.yaml` edits. It includes events such as:

- `proposal_runtime_realization_attached`
- `proposal_promotion_trace_attached`
- `trace_baseline_attached`
- `evidence_baseline_attached`
- `canonical_spec_updated`

If the UI still shows older trace-only rows after a merge, first rebuild:

```bash
cd /Users/egor/Development/GitHub/0AL/SpecGraph
make viewer-surfaces
```

Then confirm the API response:

```bash
curl -sS 'http://127.0.0.1:8001/api/spec-activity?limit=8'
```

Reload `http://127.0.0.1:5173/` if the browser already had the panel open.

## Viewer-Side Rebuild Button

When ContextBuilder is started with `--specgraph-dir` / `SPECGRAPH_DIR`, it may
expose:

```text
POST /api/viewer-surfaces/build
```

That endpoint delegates to:

```bash
python3 tools/supervisor.py --build-viewer-surfaces
```

Use it as a convenience action for the UI. The source of truth remains the
SpecGraph supervisor and its generated local artifacts.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `curl http://127.0.0.1:8766` fails | Old or custom app-browser URL. | Use `http://127.0.0.1:5173/` unless the session explicitly started another port. |
| `/api/spec-activity` returns `503` | API was started without `--specgraph-dir`. | Restart ContextBuilder with `SPECGRAPH_DIR=/Users/egor/Development/GitHub/0AL/SpecGraph`. |
| `/api/spec-activity` returns `404` | `runs/spec_activity_feed.json` has not been built. | Run `make spec-activity` or `make viewer-surfaces` in SpecGraph. |
| Recent Changes looks stale | Derived surfaces were not rebuilt after merge/supervisor run, or UI was open before rebuild. | Run `make viewer-surfaces`, verify `/api/spec-activity`, then reload the UI. |
| ContextBuilder API fails importing `TypeGuard` | Python runtime is too old. | Use Python 3.10+ for `make api` / `make dev`. |
| UI opens but API data is missing | Vite is running, API is not, or proxy target is unavailable. | Check `lsof -nP -iTCP:8001 -sTCP:LISTEN` and restart API. |

## Related Contract Docs

- [Spec Activity Feed Viewer Contract](./spec_activity_feed_viewer_contract.md)
- [Graph Backlog Projection Viewer Contract](./graph_backlog_projection_viewer_contract.md)
- [Proposal / Spec Trace Viewer Contract](./proposal_spec_trace_viewer_contract.md)
- [Metric Pack Viewer Contract](./metric_pack_viewer_contract.md)
- [Conversation Memory Viewer Contract](./conversation_memory_viewer_contract.md)
- [SpecPM Viewer Contract](./specpm_viewer_contract.md)
