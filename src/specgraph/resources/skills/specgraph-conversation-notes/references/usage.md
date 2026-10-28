# Installed SpecDraft CLI

Supported hosts for this slice: macOS and Linux, Python 3.10 or newer. Native
Windows support is not claimed: NotesStore uses Unix file locks. Docker is a
separate future distribution.

Run the tool from the consumer project. Its code, static preview assets and
this skill come from the installed runtime; its data comes from the explicitly
selected workspace.

For the standalone SpecDraft installation:

```sh
specgraph --version
specgraph notes read_notes --workspace conversation_memory/sketches/design
specgraph notes update_notes --workspace conversation_memory/sketches/design --input request.json
specgraph notes read_notes --workspace conversation_memory/sketches/design --history-limit 10
specgraph preview --workspace conversation_memory/sketches/design --port 0
```

For an installed native SpecGraph runtime, use its launcher and select an
existing product workspace separately from the sketch directory. The launcher
may be addressed by its absolute path; it need not be on `PATH`:

```sh
SPECGRAPH_RUNTIME=/absolute/path/to/specgraph-runtime
PRODUCT_WORKSPACE=/absolute/path/to/product-workspace
SKETCH=/absolute/path/to/sketch
REQUEST_JSON=/absolute/path/to/request.json
"$SPECGRAPH_RUNTIME" --workspace "$PRODUCT_WORKSPACE" draft -- --version
"$SPECGRAPH_RUNTIME" --workspace "$PRODUCT_WORKSPACE" draft -- notes read_notes --workspace "$SKETCH"
"$SPECGRAPH_RUNTIME" --workspace "$PRODUCT_WORKSPACE" draft -- notes update_notes --workspace "$SKETCH" --input "$REQUEST_JSON"
"$SPECGRAPH_RUNTIME" --workspace "$PRODUCT_WORKSPACE" draft -- notes read_notes --workspace "$SKETCH" --history-limit 10
"$SPECGRAPH_RUNTIME" --workspace "$PRODUCT_WORKSPACE" draft -- preview --workspace "$SKETCH" --port 0
```

The product workspace must already exist. `--workspace` before `draft` selects
the launcher working root; the `notes` or `preview` option selects the notebook.
The initializer currently rejects unknown top-level entries such as a sketch
directory inside its workspace. Choose the sketch path outside that root when
the workspace needs repeat initialization. The launcher resolves a relative
`--input` against the product workspace, not the invoking shell's directory;
use an absolute request path as shown. The two
workspaces can be different paths. Both routes use the same notes protocol; the
launcher does not register tools or install an agent skill automatically.

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

## Git storage contract

For a project sketch intended for Git, preserve the complete published history:

- `<sketch>/CURRENT`, the pointer to the current revision.
- For the current revision and every ancestor reached by `parent_revision` in
  `metadata.json`, all three files: `notes.hc`, `notes.hcs`, and `metadata.json`
  in `<sketch>/revisions/<revision>/`. Metadata includes sources, links and
  recorded reviews. A current snapshot alone cannot restore full history.
- Project-authored proposals, approved specifications and project-local skill
  instructions according to the project's normal Git policy. Drafts remain
  drafts when tracked; a commit is not canonical approval.

Do not track runtime-only `<sketch>/.lock`, incomplete
`<sketch>/revisions/.pending-*` directories, temporary `<sketch>/.CURRENT-*`
files, generated `runs/`, the installed runtime, its virtual environment or
caches. Unreachable revision directories are not published history: preserve
them locally for investigation rather than automatically deleting or committing
them. Do not commit credentials or secrets.

Prefer durable project Git storage for project-owned sketches when consistent
with the user's instructions and repository policy. Do not add a blanket
`conversation_memory/sketches/` ignore merely because notes are pre-canonical.
Respect existing exclusions and explicit local/private storage choices: do not
silently remove an ignore rule, force-add files or move existing notes. When
the intended destination or permission to share the full history is unclear,
keep the data local, explain the backup limitation and ask before publishing.
For a private sketch, use a user-approved private repository or an explicit
local backup; Git ignore is not access control or backup.

Before staging a sketch, inspect the destination and *all* ancestor metadata
and content for private quotations, credentials or other material unsuitable for
that destination. A correction adds a revision and does not erase earlier
quotations. Never edit immutable snapshots to sanitize history; choose a safe
destination or a separately reviewed export. Keep `CURRENT` and its complete
ancestor chain together in the same commit and verify recovery in a fresh
checkout with `specgraph notes verify_history --workspace <sketch>` or, through
the native launcher, `"$SPECGRAPH_RUNTIME" --workspace "$PRODUCT_WORKSPACE" draft -- notes verify_history --workspace "$SKETCH"`. This walks
and checks every snapshot through `parent_revision: null`; failure returns a
nonzero exit. `read_notes --history-limit` accepts at most 100 and is only a
bounded display, not proof of complete history. Avoid staging while a writer is
active. If concurrent Git branches advance `CURRENT` differently, preserve both
histories and resolve explicitly; Git text merge is not a SpecDraft merge.

## Skill installation

```sh
specgraph skill install --destination .codex/skills/specgraph-conversation-notes
```

Alternatively, with the native launcher and `PRODUCT_WORKSPACE` set as above:

```sh
"$SPECGRAPH_RUNTIME" --workspace "$PRODUCT_WORKSPACE" draft -- skill install \
  --destination "$PRODUCT_WORKSPACE/.codex/skills/specgraph-conversation-notes"
```

The destination contains `SKILL.md` plus this local reference, with no links to
a developer checkout. Repeat installation of matching content is idempotent;
different existing content is refused and preserved. The command does not edit
AGENTS.md, agent settings or ignore rules. Review any existing installation
before replacing it. Installing a skill does not register an MCP server or
automatically intercept conversations.
