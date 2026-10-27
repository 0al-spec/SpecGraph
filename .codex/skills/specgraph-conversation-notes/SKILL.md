---
name: specgraph-conversation-notes
description: Keep source-attributed SpecDraft notes with the installed runtime, or the compatible checkout CLI during development.
---

# Conversational notes

Read the [versioned portable instructions](../../../src/specgraph/resources/skills/specgraph-conversation-notes/SKILL.md)
and their self-contained usage reference. That resource is what
`specgraph skill install --destination <skill-directory>` exports from the
installed wheel. Consumer projects use the installed command and persistent
project-owned workspaces, independently of this developer checkout.

When developing SpecGraph before installing its candidate wheel, the compatible
source interfaces remain available with the repository Python environment:

```bash
.venv/bin/python tools/conversation_notes_cli.py read_notes --workspace <sketch>
.venv/bin/python tools/conversation_notes_cli.py update_notes --workspace <sketch> --input <request.json>
.venv/bin/python tools/specdraft_preview_cli.py --workspace <sketch>
```

For the existing live notebook, retain its recorded path and revision. Do not
move notebook data into an installation or a temporary worktree. The source
API and JSON contract are also documented in [Conversation Notes](../../../docs/conversation_notes.md).
