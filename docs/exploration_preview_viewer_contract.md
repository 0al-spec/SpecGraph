# Exploration Preview Viewer Contract

This document is the implementation-facing contract for adding an
exploration/assumption-mode panel to the ContextBuilder viewer.

The feature lets a user enter a root intent and receive a review-only
placeholder graph before any canonical SpecGraph mutation happens.

## 1. Goal

ContextBuilder should expose a lightweight exploration panel for early product
thinking:

1. user enters a root intent;
2. viewer asks SpecGraph supervisor to build an exploration preview;
3. viewer renders the returned placeholder graph;
4. user can inspect assumptions, hypotheses, proposal directions, and review
   boundary;
5. no canonical spec, intent-layer node, or proposal-lane node is created.

This is deliberately a `mindmap` or `preview` surface, not a full spec authoring
flow.

## 2. Source Artifact

Build command:

```bash
python3 tools/supervisor.py \
  --build-exploration-preview \
  --exploration-intent "Explore SpecGraph visual editor layers from root intent to production runtime."
```

Read:

- `runs/exploration_preview.json`

Policy:

- `tools/exploration_preview_policy.json`

Important boundary:

- `canonical_mutations_allowed` must be `false`;
- `tracked_artifacts_written` must be `false`;
- `review_state` must be treated as advisory UI state, not canonical graph
  state;
- promotion is explicitly out of scope for this first viewer slice.

## 3. Recommended ContextBuilder Endpoints

Follow the same server pattern already used for `SpecPM` artifacts.

### `GET /api/exploration-preview`

Reads `SpecGraph/runs/exploration_preview.json`.

Recommended success response:

```json
{
  "path": "/abs/path/to/SpecGraph/runs/exploration_preview.json",
  "mtime": 1777184450.0,
  "mtime_iso": "2026-04-26T06:20:50+00:00",
  "data": {
    "artifact_kind": "exploration_preview"
  }
}
```

Recommended errors:

- `503` when the server was not started with `--specgraph-dir`;
- `404` when the artifact was not built yet;
- `422` when JSON cannot be read or parsed.

### `POST /api/exploration-preview/build`

Request body:

```json
{
  "intent": "Explore SpecGraph visual editor layers from root intent to production runtime."
}
```

Server action:

```python
cmd = [
    sys.executable,
    str(specgraph_dir / "tools" / "supervisor.py"),
    "--build-exploration-preview",
    "--exploration-intent",
    intent,
]
```

Use `subprocess.run(..., capture_output=True, text=True, timeout=60)`.
Do not use `shell=True`.

Recommended success response:

```json
{
  "exit_code": 0,
  "stderr_tail": "",
  "path": "/abs/path/to/SpecGraph/runs/exploration_preview.json",
  "artifact_exists": true,
  "built_at": "2026-04-26T06:20:50+00:00"
}
```

Recommended errors:

- `400` when `intent` is missing or blank;
- `503` when `--specgraph-dir` is not configured;
- `422` when `supervisor.py` is missing or exits non-zero;
- `500` on timeout or invocation failure.

## 4. JSON Contract

Viewer code should treat these top-level fields as stable:

- `artifact_kind`
- `schema_version`
- `generated_at`
- `policy_reference`
- `mode`
- `mode_contract`
- `input`
- `review_state`
- `next_gap`
- `canonical_mutations_allowed`
- `tracked_artifacts_written`
- `node_count`
- `edge_count`
- `nodes`
- `edges`
- `promotion_candidates`
- `viewer_contract`

### Happy-path example

```json
{
  "artifact_kind": "exploration_preview",
  "schema_version": 1,
  "mode": "assumption",
  "input": {
    "source_kind": "inline_operator_intent",
    "text": "Explore SpecGraph visual editor layers from root intent to production runtime.",
    "text_sha256": "44797b550fe56ee5029ea556dc7a5d473d549bbb711b32da20c389ca71e57ed5",
    "input_status": "root_intent_provided"
  },
  "review_state": "preview_only",
  "next_gap": "human_review_before_promotion",
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "node_count": 5,
  "edge_count": 4
}
```

### Missing-input example

The supervisor can still emit a blocked artifact if no intent is provided:

```json
{
  "input": {
    "source_kind": "none",
    "text": "",
    "text_sha256": "",
    "input_status": "missing_root_intent"
  },
  "review_state": "blocked",
  "next_gap": "provide_root_intent_text",
  "node_count": 0,
  "edge_count": 0,
  "nodes": [],
  "edges": [],
  "promotion_candidates": []
}
```

ContextBuilder should normally prevent blank submission client-side and return
`400` server-side.

## 5. Node Contract

Each `nodes[]` entry has this shape:

```json
{
  "id": "exploration:44797b550fe5:intent",
  "kind": "intent",
  "label": "Explore SpecGraph visual editor layers from root intent to production runtime.",
  "text": "Explore SpecGraph visual editor layers from root intent to production runtime.",
  "status": "captured",
  "authority": "operator",
  "confidence": "explicit",
  "layer": "intent"
}
```

Current node kinds:

- `intent`
- `assumption_cluster`
- `hypothesis_cluster`
- `proposal_cluster`
- `review_gate`

Recommended rendering:

- `intent`: root card; use `label` as title and `text` as body.
- `assumption_cluster`: amber or dotted placeholder; emphasize unclaimed
  assumptions.
- `hypothesis_cluster`: neutral/blue placeholder; candidate interpretations.
- `proposal_cluster`: purple or proposal-colored placeholder; not a tracked
  proposal yet.
- `review_gate`: locked/review badge; human approval required before any
  promotion.

Do not map these preview nodes into canonical `SpecNode` IDs. They have
synthetic IDs and should stay in a separate preview graph.

## 6. Edge Contract

Each `edges[]` entry has this shape:

```json
{
  "source": "exploration:44797b550fe5:intent",
  "target": "exploration:44797b550fe5:assumptions",
  "edge_kind": "structures_assumptions"
}
```

Current edge kinds:

- `structures_assumptions`
- `raises_hypotheses`
- `suggests_proposals`
- `requires_human_review`

Recommended visual treatment:

- use directed edges;
- do not color these as canonical `depends_on` / `refines` edges;
- use a distinct preview style such as dashed lines or a separate canvas layer;
- if rendered near the canonical graph, keep preview edges opt-in via a layer
  toggle.

## 7. UI Behavior

Recommended first slice:

1. Add an `Exploration Preview` button or panel near existing SpecGraph tools.
2. Show a textarea for root intent.
3. On submit, call `POST /api/exploration-preview/build`.
4. After success, call `GET /api/exploration-preview`.
5. Render a small graph or ordered cards from `nodes[]` and `edges[]`.
6. Show summary chips:
   - `input.input_status`
   - `review_state`
   - `node_count`
   - `edge_count`
   - `next_gap`
7. Show a boundary warning when:
   - `canonical_mutations_allowed !== false`;
   - `tracked_artifacts_written !== false`;
   - `artifact_kind !== "exploration_preview"`.

Recommended labels:

- button: `Build Exploration Preview`
- panel title: `Exploration Preview`
- subtitle: `Assumption-mode draft, not canonical`
- empty state: `Enter a root intent to generate a preview`
- blocked state: `Root intent required`

## 8. TypeScript Types

Minimal client-side types:

```ts
export type ExplorationNodeKind =
  | "intent"
  | "assumption_cluster"
  | "hypothesis_cluster"
  | "proposal_cluster"
  | "review_gate";

export type ExplorationEdgeKind =
  | "structures_assumptions"
  | "raises_hypotheses"
  | "suggests_proposals"
  | "requires_human_review";

export interface ExplorationPreviewNode {
  id: string;
  kind: ExplorationNodeKind;
  label: string;
  text: string;
  status: string;
  authority: string;
  confidence: string;
  layer: string;
}

export interface ExplorationPreviewEdge {
  source: string;
  target: string;
  edge_kind: ExplorationEdgeKind;
}

export interface ExplorationPreview {
  artifact_kind: "exploration_preview";
  schema_version: 1;
  generated_at: string;
  mode: "assumption";
  input: {
    source_kind: "inline_operator_intent" | "none";
    text: string;
    text_sha256: string;
    input_status: "root_intent_provided" | "missing_root_intent";
  };
  review_state: "preview_only" | "blocked";
  next_gap: "human_review_before_promotion" | "provide_root_intent_text";
  canonical_mutations_allowed: false;
  tracked_artifacts_written: false;
  node_count: number;
  edge_count: number;
  nodes: ExplorationPreviewNode[];
  edges: ExplorationPreviewEdge[];
  promotion_candidates: Array<{
    target_kind: string;
    review_required: true;
    auto_promote: false;
  }>;
}
```

## 9. Non-Goals

Do not implement these in the first ContextBuilder slice:

- no automatic creation of `intent_layer/nodes/*.json`;
- no automatic creation of `proposal_lane/nodes/*.json`;
- no canonical `specs/nodes/*.yaml` mutation;
- no merge into the main SpecGraph force graph by default;
- no promotion workflow;
- no LLM synthesis beyond the deterministic placeholder preview currently
  emitted by SpecGraph.

## 10. Acceptance Criteria

The ContextBuilder implementation is complete for the first slice when:

- `GET /api/exploration-preview` returns the artifact or a clear missing-state
  error;
- `POST /api/exploration-preview/build` accepts non-empty `intent` and invokes
  the supervisor safely without shell interpolation;
- blank intent is rejected before invoking the supervisor;
- the panel renders `node_count`, `edge_count`, `review_state`, and `next_gap`;
- all `nodes[]` are visible as cards or graph nodes;
- all `edges[]` are visible or inspectable;
- UI explicitly says the preview is not canonical;
- no ContextBuilder action writes canonical SpecGraph files.
