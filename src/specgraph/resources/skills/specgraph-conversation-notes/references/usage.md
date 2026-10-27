# Installed SpecDraft CLI

Supported hosts for this slice: macOS and Linux, Python 3.10 or newer. Native
Windows support is not claimed: NotesStore uses Unix file locks. Docker and
full supervisor distribution are later slices.

Run the tool from the consumer project. Its code, static preview assets and
this skill come from the installed runtime; its data comes from the explicitly
selected workspace.

```sh
specgraph --version
specgraph notes read_notes --workspace conversation_memory/sketches/design
specgraph notes update_notes --workspace conversation_memory/sketches/design --input request.json
specgraph notes read_notes --workspace conversation_memory/sketches/design --history-limit 10
specgraph preview --workspace conversation_memory/sketches/design --port 0
```

`update_notes` also accepts the request as JSON on stdin. Read/update return
JSON on stdout; invalid input or stale revision returns exit code 2 and an
error on stderr. Preview prints its selected loopback URL, then serves until
stopped. Port 0 chooses a free port. Existing source-checkout CLI commands are
compatible with these installed interfaces.

## Update request

Read first. A new workspace returns `revision: null`; otherwise copy the exact
returned revision into `expected_revision`.

```json
{
  "expected_revision": null,
  "source": {
    "ref": "conversation:design/excerpt-1",
    "quote": "The exact words being captured",
    "speaker": "human"
  },
  "changes": [
    {"op": "add", "id": "goal", "label": "Short recognizable label", "detail": "Brief detail", "parent_id": null}
  ]
}
```

The source speaker is `human` or `agent`. A request contains 1–100 operations.
Supported changes are:

```json
{"op": "revise", "id": "goal", "label": "Updated label", "detail": "Updated detail"}
{"op": "move", "id": "goal", "parent_id": null}
{"op": "link", "source_id": "goal", "target_id": "other", "label": "relates to"}
{"op": "approve"}
```

IDs start with an ASCII letter and contain letters, digits, `_` or `-`.
Labels/details are single-line text; source quotations can contain newlines.
Moving beneath a missing parent or creating cycles is rejected. A no-op update
is rejected. Exact revisions, quotations, HC/HCS content and recorded reviews
persist in the workspace. `approve` applies only to a human-approved whole
sketch, never merely to a task request or permission to implement it.

## Skill installation

```sh
specgraph skill install --destination .codex/skills/specgraph-conversation-notes
```

The destination contains `SKILL.md` plus this local reference, with no links to
a developer checkout. Repeat installation of matching content is idempotent;
different existing content is refused and preserved. The command does not edit
AGENTS.md, agent settings or ignore rules. Review any existing installation
before replacing it. Installing a skill does not register an MCP server or
automatically intercept conversations.
