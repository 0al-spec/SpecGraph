# Conversation Memory

This directory is a pre-canonical Layer 0 storage area for structured
conversation memory. It gives `make conversation-memory` real source and note
records to index without mining archives automatically.

Nothing in this directory is canonical specification truth by itself.

## Sources

Put source boundary records under `sources/*.json`.

Example:

```json
{
  "source_id": "pageindex-chat-2026-05-01-example",
  "source_type": "pageindex_conversation",
  "source_state": "declared",
  "source_ref": "pageindex://chatgpt/example",
  "captured_at": "2026-05-01T00:00:00Z",
  "selection_rationale": "operator-selected discussion",
  "source_boundary": "curated excerpt"
}
```

## Notes

Put structured memory notes under `notes/*.md`. Each note must use frontmatter
that matches `tools/conversation_memory_policy.json`.

Example:

```markdown
---
memory_note_id: cmem-2026-05-01-0001
note_kind: assumption
title: Metric packs need adapter gaps
promotion_state: proposal_pressure_candidate
source_refs:
  - pageindex-chat-2026-05-01-example
links:
  related_specs: []
  related_proposals:
    - "0043_metric_pack_plugin_architecture"
  related_memory_notes: []
---

Metric-pack execution should not run until adapter computability gaps are
visible in the graph.
```

## Build

```bash
make conversation-memory
```

The generated artifact is local:

```text
runs/conversation_memory_index.json
```

Use `make viewer-surfaces` when ContextBuilder needs all common viewer-facing
surfaces refreshed together.
