# Conversation Memory Viewer Contract

## Status

Draft viewer contract for the Conversation Memory / Exploration Vault surface
introduced by proposal 0045.

## Source Artifacts

ContextBuilder should treat this as a read-only SpecGraph artifact:

| Artifact | Producer | Consumer Use |
| --- | --- | --- |
| `runs/conversation_memory_index.json` | `make conversation-memory` or `make viewer-surfaces` | Conversation-memory panel, source/note counts, reviewable pre-canonical gaps. |
| `runs/conversation_memory_map.json` | `make conversation-memory-map` or `make viewer-surfaces` | Exploration map projection, clusters, links, source coverage, promotion candidates, review blockers. |

The index is built from:

- `tools/conversation_memory_policy.json`;
- `conversation_memory/sources/*.json`;
- `conversation_memory/notes/*.md`;
- optional fixture records supplied by tests or future tools.

No ContextBuilder write path is implied by this contract.

## Boundary

Conversation memory is Layer 0 structured exploration material.

It is not canonical specification state. It may produce reviewable pressure
toward intents, proposals, pre-spec drafts, or operator questions, but it must
not directly mutate:

- `specs/nodes/*.yaml`;
- proposal-lane tracked nodes;
- implementation work items;
- policies or metric thresholds.

Viewer guardrails:

- Render only when `artifact_kind == "conversation_memory_index"`.
- Treat a missing artifact as "not built yet".
- Show a boundary warning if `canonical_mutations_allowed !== false` or
  `tracked_artifacts_written !== false`.
- Do not expose "promote to spec" as a direct action from this artifact.

## Index Artifact

`runs/conversation_memory_index.json` has this stable top-level shape:

```json
{
  "artifact_kind": "conversation_memory_index",
  "schema_version": 1,
  "generated_at": "2026-05-01T00:00:00Z",
  "policy_reference": {
    "artifact_path": "tools/conversation_memory_policy.json",
    "artifact_sha256": "...",
    "version": 1
  },
  "source_snapshot": {
    "source_dir": "conversation_memory/sources",
    "note_dir": "conversation_memory/notes",
    "policy_source_count": 0,
    "policy_note_count": 0,
    "storage_source_count": 0,
    "storage_note_count": 0
  },
  "layer_boundary": {
    "layer_name": "conversation_memory",
    "canonical_mutations_allowed": false,
    "tracked_artifacts_written": false
  },
  "review_state": "not_ready",
  "next_gap": "capture_conversation_memory_source",
  "source_count": 0,
  "structured_note_count": 0,
  "sources": [],
  "entries": [],
  "summary": {},
  "viewer_projection": {},
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

Use `summary` and `viewer_projection` for counts and filters. Use `sources[]`
and `entries[]` for tables/detail drawers. Unknown future fields should pass
through without breaking rendering.

## Source Contract

Each `sources[]` item describes a declared source boundary:

```json
{
  "source_id": "pageindex-chat-2026-05-01",
  "source_type": "pageindex_conversation",
  "source_state": "declared",
  "source_ref": "pageindex://chatgpt/...",
  "captured_at": "2026-05-01T00:00:00Z",
  "selection_rationale": "operator-selected discussion",
  "source_boundary": "curated excerpt",
  "storage_path": "conversation_memory/sources/pageindex-chat-2026-05-01.json",
  "contract_errors": []
}
```

Known `source_type` values:

- `pageindex_conversation`
- `local_markdown_transcript`
- `chatgpt_export_json`
- `compiled_markdown`
- `session_capture`
- `operator_excerpt`
- `external_note_system`

Known `source_state` values:

- `declared`
- `available`
- `missing`
- `curated`

Unknown future values should render as neutral chips.

## Entry Contract

Each `entries[]` item describes one structured memory note:

```json
{
  "memory_note_id": "cmem-2026-05-01-0001",
  "note_kind": "assumption",
  "title": "Metric packs need adapter gaps",
  "status": "structured",
  "promotion_state": "proposal_pressure_candidate",
  "review_state": "promotion_review_required",
  "next_gap": "review_memory_promotion_pressure",
  "source_refs": ["pageindex-chat-2026-05-01"],
  "links": {
    "related_specs": [],
    "related_proposals": [],
    "related_memory_notes": []
  },
  "staleness": "current",
  "storage_path": "conversation_memory/notes/cmem-2026-05-01-0001.md",
  "summary": "Metric-pack execution should wait for adapter computability gaps.",
  "contract_errors": []
}
```

`storage_path` is optional for policy/fixture-provided records and present for
records loaded from `conversation_memory/`.

Known `note_kind` values:

- `claim`
- `assumption`
- `decision`
- `question`
- `pattern`
- `constraint`
- `source_summary`

Known `status` values:

- `structured`
- `invalid_memory_note`
- `blocked_by_promotion_boundary`

Known `promotion_state` values:

- `not_promoted`
- `proposal_pressure_candidate`
- `intent_fragment_candidate`
- `pre_spec_draft_candidate`
- `operator_question`

Known `review_state` values:

- `not_ready`
- `structured_reviewable`
- `promotion_review_required`
- `blocked`

## Viewer Projection

`viewer_projection` groups IDs by stable dimensions:

```json
{
  "note_kind": {
    "assumption": ["cmem-2026-05-01-0001"]
  },
  "note_status": {
    "structured": ["cmem-2026-05-01-0001"]
  },
  "promotion_state": {},
  "review_state": {},
  "next_gap": {},
  "source_type": {},
  "source_state": {},
  "named_filters": {
    "structured_reviewable": [],
    "promotion_review_required": [],
    "missing_attribution": [],
    "stale_notes": [],
    "invalid_notes": [],
    "source_summaries": []
  }
}
```

Recommended first panel:

- summary chips for `source_count`, `structured_note_count`, `review_state`,
  and `next_gap`;
- source table grouped by `source_type` and `source_state`;
- note table grouped by `note_kind`, `promotion_state`, and `review_state`;
- warning chips for `missing_attribution`, `stale_notes`, and `invalid_notes`;
- copy that clearly says "structured exploration memory, not canonical".

Out of scope for current viewer slices:

- archive mining;
- semantic search UI;
- editing memory notes;
- one-click promotion to proposal/spec;
- merging memory notes into the main force graph.

## Map Artifact

`runs/conversation_memory_map.json` is a derived projection built from the
current index. It is still read-only and pre-canonical:

```json
{
  "artifact_kind": "conversation_memory_map",
  "schema_version": 1,
  "generated_at": "2026-05-01T00:00:00Z",
  "policy_reference": {
    "artifact_path": "tools/conversation_memory_policy.json",
    "artifact_sha256": "...",
    "version": 1
  },
  "index_reference": {
    "artifact_kind": "conversation_memory_index",
    "schema_version": 1,
    "generated_at": "2026-05-01T00:00:00Z",
    "source_count": 1,
    "structured_note_count": 2,
    "next_gap": "review_conversation_memory_index"
  },
  "source_snapshot": {
    "source_dir": "conversation_memory/sources",
    "note_dir": "conversation_memory/notes",
    "policy_source_count": 0,
    "policy_note_count": 0,
    "storage_source_count": 1,
    "storage_note_count": 2
  },
  "layer_boundary": {
    "layer_name": "conversation_memory",
    "canonical_mutations_allowed": false,
    "tracked_artifacts_written": false
  },
  "review_state": "ready_for_review",
  "next_gap": "review_memory_promotion_pressure",
  "cluster_count": 4,
  "link_count": 3,
  "clusters": [],
  "links": [],
  "source_coverage": {},
  "related_specs": {},
  "related_proposals": {},
  "candidate_proposal_pressure": {},
  "review_blockers": {},
  "summary": {},
  "viewer_projection": {},
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "viewer_contract": {
    "contract_doc": "docs/conversation_memory_viewer_contract.md",
    "read_only": true
  }
}
```

Viewer guardrails are the same as the index artifact:

- Render only when `artifact_kind == "conversation_memory_map"`.
- Treat a missing artifact as "not built yet".
- Show a boundary warning if `canonical_mutations_allowed !== false` or
  `tracked_artifacts_written !== false`.
- Do not expose direct "promote to spec" or "create implementation work" actions.

### Clusters

Each `clusters[]` item groups memory notes by a derived dimension:

```json
{
  "cluster_id": "note_kind::assumption",
  "cluster_kind": "note_kind",
  "label": "assumption",
  "member_note_ids": ["cmem-2026-05-01-0001"],
  "member_count": 1
}
```

Known `cluster_kind` values:

- `note_kind`
- `source`
- `related_spec`
- `related_proposal`
- `review_blocker`

Unknown future values should render as neutral map groups.

### Links

Each `links[]` item is a derived edge between a memory note and a source or
declared relation:

```json
{
  "link_id": "cmem-2026-05-01-0001::related_spec::SG-SPEC-0045",
  "link_kind": "related_spec",
  "from_id": "cmem-2026-05-01-0001",
  "from_type": "memory_note",
  "to_id": "SG-SPEC-0045",
  "to_type": "spec_node"
}
```

Known `link_kind` values:

- `source_ref`
- `related_spec`
- `related_proposal`
- `related_memory_note`

### Source Coverage

`source_coverage` summarizes attribution quality:

```json
{
  "declared_source_count": 1,
  "structured_note_count": 2,
  "source_refs_note_count": 2,
  "attributed_note_count": 1,
  "missing_attribution_count": 1,
  "missing_attribution_note_ids": ["cmem-missing-source"],
  "source_ref_counts": {
    "pageindex-chat-2026-05-01": 1
  }
}
```

Use this for attribution warning chips and source-coverage summaries.
`source_refs_note_count` means the note has at least one source ref field.
`attributed_note_count` means all refs on the note resolve to declared sources.

### Promotion Candidates

`candidate_proposal_pressure.entries[]` is a review queue, not a mutation queue:

```json
{
  "candidate_id": "cmem-2026-05-01-0001",
  "target_kind": "proposal_candidate",
  "promotion_state": "proposal_pressure_candidate",
  "source_memory_notes": ["cmem-2026-05-01-0001"],
  "source_refs": ["pageindex-chat-2026-05-01"],
  "rationale": "Metric-pack execution should wait for adapter computability gaps.",
  "review_state": "promotion_review_required",
  "next_gap": "review_memory_promotion_pressure"
}
```

Known `target_kind` values:

- `proposal_candidate`
- `intent_fragment`
- `pre_spec_draft`
- `operator_question`
- `unknown`

### Review Blockers

`review_blockers.entries[]` identifies notes that must be repaired before the
map should be treated as clean:

```json
{
  "memory_note_id": "cmem-missing-source",
  "status": "invalid_memory_note",
  "review_state": "not_ready",
  "next_gap": "repair_conversation_memory_note_attribution",
  "contract_errors": ["undeclared_source_ref"]
}
```

Recommended map UI:

- map-level summary chips for `cluster_count`, `link_count`, `review_state`,
  `next_gap`;
- grouped cluster browser by `cluster_kind`;
- link table grouped by `link_kind`;
- source-coverage warning when `missing_attribution_count > 0`;
- promotion candidate list labeled "review required";
- review blocker list with `next_gap` and `contract_errors`;
- no canonical promotion action.
