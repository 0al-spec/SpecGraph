---
name: specgraph-conversation-notes
description: Keep short, source-attributed Hypercode notes while a person discusses a product or design with an agent. Use for ongoing conversational capture and resuming a saved sketch, before requirements are formalized.
---

# Conversational notes

Capture what the person said before expanding your interpretation. Keep notes
short enough that the person can recognize their own thought. Reuse existing
nodes when a topic recurs. The person speaks and reviews; the agent operates
the tools. Do not require ontology terms, requirement fields or a model run to
save a note.

Locate the SpecGraph checkout containing `tools/conversation_notes_cli.py` and
use its Python environment. Select one persistent sketch directory and retain
its path across turns. Default inside that checkout:
`conversation_memory/sketches/<conversation-name>/`. This checkout explicitly
ignores that path; tell the user it is not backed up in Git. For consumer
projects, follow the Git storage contract in the packaged
[usage reference](../../../src/specgraph/resources/skills/specgraph-conversation-notes/references/usage.md):
keep the current pointer and complete ancestor snapshots together; do not infer
an ignore rule from draft status. Respect existing storage choices. For the JSON
request contract, read [Conversation Notes](../../../docs/conversation_notes.md).

The two tools are CLI commands returning JSON:

```bash
.venv/bin/python tools/conversation_notes_cli.py read_notes --workspace <sketch>
.venv/bin/python tools/conversation_notes_cli.py update_notes --workspace <sketch> --input <request.json>
```

- Start or resume with `read_notes`. Use its revision as `expected_revision`.
- Save a small batch after a meaningful statement. Preserve the exact source
  quotation separately from your short label/detail. Use a real message reference
  when available; otherwise name the excerpt locally without inventing a native
  message ID. Attribute your own additions with `speaker: agent`.
- Use `add`, `revise`, `move` and `link`. IDs persist through renaming and moving;
  `revise` can attach another quotation without changing the label.
- Resolve a revision conflict by reading again and reconsidering the patch.
  Never replace `expected_revision` blindly or overwrite snapshot files.
- At a natural pause, show the small diff in ordinary language. Do not ask the
  person to approve every write. If they explicitly approve the displayed whole
  sketch, record an `approve` operation against that exact revision, separately
  from edits. Partial or ambiguous assent stays a source quotation until its
  scope is clear. This records a conversation observation, not canonical adoption.
- When a reply agrees with or refuses an earlier proposal, follow the
  [contextual agreement or refusal rule](../../../src/specgraph/resources/skills/specgraph-conversation-notes/SKILL.md#contextual-agreement-or-refusal).
- Read the relevant branch with `--node-id` for bounded context. `omitted_nodes`
  reports excluded nodes; links may point outside the selected branch.

When the user authorizes delegation, a subagent can propose duplicate merges or
grouping using the relevant branch and its sources. Keep the main agent as the
writer; proposals return for review. Capture continues without waiting for that
analysis. Do not spawn an agent for every new word. Destructive merging/deletion
is outside this PoC; suggest a grouping or explicit link instead.

On handoff, report the sketch path and revision. A new session can recover the
structure, citations and recorded reviews with `read_notes --history-limit 10`.
