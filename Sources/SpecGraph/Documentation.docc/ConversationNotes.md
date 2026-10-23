# Conversation Notes

Keep a short Hypercode sketch during a conversation, before formal requirements.

The person speaks and reviews. The agent calls `read_notes` and `update_notes`
through `tools/conversation_notes_cli.py`, using one explicit sketch directory.
The repo-local `specgraph-conversation-notes` skill describes the conversational
workflow. This is a CLI/API PoC under proposal 0045, not an installed MCP server
or automatic chat integration.

## Capture and resume

```bash
.venv/bin/python tools/conversation_notes_cli.py read_notes --workspace conversation_memory/sketches/example
.venv/bin/python tools/conversation_notes_cli.py update_notes --workspace conversation_memory/sketches/example --input request.json
```

An update includes `expected_revision`, `source` (`ref`, `quote`, `speaker`),
and a small ordered `changes` array. Operations are `add`, `revise`, `move`,
`link` and `approve`. Labels and details are single-line strings; exact source
quotations can be multiline. Citations distinguish human words from agent
interpretations. Source identity and quotation accuracy remain caller claims.

Notes have stable IDs through rename and move. A fresh session reads the same
directory, optionally selecting a branch with `--node-id` or history with
`--history-limit`. Branch reads include `omitted_nodes`; incident links can
reference nodes outside that branch. The update response contains a small diff.

## Stored sketch

Each revision holds `notes.hc`, `notes.hcs` and `metadata.json`. Hypercode holds
the note hierarchy and text; metadata holds sources, links and review records.
The adapter reads its emitted `Note#id` / exact ID selector subset. HCS strings
are literal, without YAML escape decoding. General language extensions and
manual snapshot edits are outside this PoC.

The atomic `CURRENT` pointer selects one complete revision. POSIX locking and
revision comparison prevent concurrent writers from losing edits. An interrupted
write before publication leaves the previous version readable. After an I/O
error, reread before retrying: publication may already have occurred. History
follows published parent revisions and ignores orphan snapshots.

## Human review

Capture proceeds without approving every save. At a natural pause the agent
shows the sketch or a short diff. `approve` records an attributed human quotation
against the exact displayed revision, in a batch separate from edits. Later
changes do not inherit that approval. The result always reports `canonical: false`;
this observation does not publish canonical Intent, requirements or ontology.

Local sketches are Git-ignored; copy the directory before removing its checkout.
Existing Markdown conversation-memory indexes do not yet ingest these sketches.
The PoC adds no automatic agent orchestration, GUI, deletion or semantic merging.

## Verification

Run `tests/test_conversation_notes.py` for persistence, source retention,
concurrency, failure recovery and review scope. Set `HYPERCODE_BIN` to include the
optional native Hypercode compatibility check. The detailed JSON request and
storage contract is maintained in `docs/conversation_notes.md`.
