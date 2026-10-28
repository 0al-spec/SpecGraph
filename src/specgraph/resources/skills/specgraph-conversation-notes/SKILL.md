---
name: specgraph-conversation-notes
description: Keep short, source-attributed SpecDraft notes during a human-agent conversation using the installed SpecGraph CLI.
---

# Conversational notes

Use the installed `specgraph` command. Run `specgraph --version` to identify the
selected runtime. Do not locate or depend on a SpecGraph developer checkout.
Read the self-contained [CLI and JSON contract](references/usage.md).

Choose one persistent sketch directory inside the consumer project, for example
`conversation_memory/sketches/design`. Keep that path across sessions. All
commands require the workspace explicitly. Follow the Git storage contract in
[the usage reference](references/usage.md); do not invent
blanket exclusions or treat draft status as a reason to exclude a sketch.

Capture the person's exact source wording separately from your short label and
interpretation. Reuse existing IDs when a topic recurs. The person speaks and
reviews; the agent calls the tools. Saving a note requires no ontology lookup,
requirement fields or model run.

- Start or resume with `specgraph notes read_notes --workspace <sketch>`.
- Use the returned revision as `expected_revision` in `update_notes`.
- Save small batches after meaningful statements; name a real message reference
  when available, otherwise identify the excerpt locally without inventing a
  native message ID. Attribute agent additions with `speaker: agent`.
- Use `add`, `revise`, `move` and `link`. IDs survive renaming and regrouping.
- Resolve stale revisions by reading again and reconsidering the changes.
  Never replace `expected_revision` blindly or edit stored snapshots directly.
- At a natural pause, explain the small diff. Do not ask for approval of every
  write. Record `approve` only for an explicit approval of the displayed whole
  sketch at that exact revision; partial assent remains a source quotation.
- Read a bounded branch with `--node-id`; `omitted_nodes` describes exclusion
  and links may point outside the selected branch.

Use `specgraph preview --workspace <sketch>` for the current saved mind map.
The server is read-only, loopback-only and prints its actual URL. It does not
edit notes, select history, approve requirements or publish canonical records.

On handoff, report the sketch path and revision. Recover citations, history and
recorded conversation reviews with `read_notes --history-limit 10`. Notes stay
`canonical: false`; conversation approval is not canonical adoption.

When delegation is authorized, analysis agents may suggest grouping or links;
keep one main writer using revision checks. Do not start a subagent per word.
Deletion and destructive merging are outside this note interface.
