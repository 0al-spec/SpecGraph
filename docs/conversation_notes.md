# Conversation Notes PoC

The person speaks and reviews; the agent keeps short, persistent notes. This
implements a bounded capture slice of [proposal 0045](proposals/0045_conversation_memory_exploration_vault.md).
It saves a sketch before ontology linking, requirements or Supervisor execution.

The [SpecDraft layer design note](specdraft_layer.md) places this capture PoC
in a broader pre-canonical authoring space beneath SpecGraph. That layer name
is distinct from the existing `SpecDraft` promotion stage.

## Agent entry point

Use the repo-local [conversation notes skill](../.codex/skills/specgraph-conversation-notes/SKILL.md).
The tools `read_notes` and `update_notes` are Python functions in
`tools/conversation_notes/api.py`, exposed through a JSON CLI. They are callable
with an agent's shell tool; this PoC does not install an MCP server or chat hook.
The host agent decides when to call them. No model or network access is used by
either tool.

From the SpecGraph checkout, with its Python environment:

```bash
.venv/bin/python tools/conversation_notes_cli.py read_notes \
  --workspace conversation_memory/sketches/my-conversation
.venv/bin/python tools/conversation_notes_cli.py update_notes \
  --workspace conversation_memory/sketches/my-conversation --input request.json
```

`update_notes` also accepts the request on stdin. Success is JSON on stdout,
exit 0. Invalid requests, stale revisions and storage errors return a JSON error
on stderr, exit 2. An empty `read_notes` creates no files and returns a null
revision. Workspace paths are explicitly selected local directories.

## Update request

```json
{
  "expected_revision": null,
  "source": {
    "ref": "operator-excerpt:conversation-pilot/1",
    "speaker": "human",
    "quote": "А человек просто говорит и одобряет."
  },
  "changes": [
    {"op": "add", "id": "person", "label": "Человек"},
    {"op": "add", "id": "speaks", "label": "Говорит", "parent_id": "person"},
    {"op": "add", "id": "reviews", "label": "Одобряет", "parent_id": "person"}
  ]
}
```

For subsequent calls, copy the revision returned by the last read/update into
`expected_revision`. A conflict requires reading and reconsidering the patch.
All 1–100 operations in one batch apply together, in order; references must
already exist at their point of use. Unknown fields/operations are errors.

| Operation | Fields after `op` | Meaning |
| --- | --- | --- |
| `add` | `label`, optional `id`, `detail`, `parent_id` | Add a note; generate an ID when omitted |
| `revise` | `id`, optional `label`, `detail` | Refine text and/or append attribution |
| `move` | `id`, `parent_id` (null for a root) | Move a subtree to the end of the destination's children |
| `link` | `source_id`, `target_id`, `label` | Record an explicitly named directed relationship |
| `approve` | none | Record an attributed human approval of `expected_revision` |

`source.ref` is an opaque, nonempty reference supplied by the caller;
`source.quote` retains the exact nonempty, possibly multiline excerpt.
`source.speaker` is `human` or `agent`. References/quotations are attributed
claims, not independently verified source retrieval or authenticated identity.
Use `agent` for an inference rather than misquoting it as the person's words.

IDs start with an ASCII letter, followed by letters/digits/underscores/hyphens
(128 characters maximum); identity is scoped to this sketch directory. Labels
and details are single-line Unicode strings; labels must be nonempty. Original
multiline text belongs in the quotation. Adding the same ID fails; repeating a
link appends new attribution without duplicating the edge. A completely unchanged
request returns `No changes to save` without advancing the revision.
This comparison uses stored tree order: moving an already-last subtree to the
same parent with its existing quotation creates no snapshot or history entry.
A new quotation remains a real attribution change and is saved even when the
visible tree stays the same.

`approve` must be the only operation in its batch and requires a human quotation
and an existing revision. It records the entire displayed revision; partial
approval is not inferred. Later edits retain the record with its original
revision. Recording approval does not create canonical specs, grant authority,
or mark the current edited sketch approved.

## Read and resume

```bash
.venv/bin/python tools/conversation_notes_cli.py read_notes \
  --workspace conversation_memory/sketches/my-conversation \
  --node-id person --history-limit 10
```

The result includes revision, nodes with parent IDs and sources, named links,
recorded reviews, snapshot path and `canonical: false`. A branch read reports
`omitted_nodes`; incident links may refer to nodes outside the selected branch.
History follows published parent revisions (limit 0–100), not directory listings.
The update response is a small diff of added/revised notes, changed links and
recorded reviews. Rename and move preserve IDs and existing quotations.

For an existing note whose position among siblings changes, `diff.updated`
includes `fields.sibling_index` with zero-based `before` and `after` indices.
Roots are siblings under `parent_id: null`. The diff includes neighbors shifted
by a move; descendants whose own sibling position is unchanged are not reported
as reordered. A move within the same parent remains visible even when its
source quotation is already attached. Indices describe the before/after
snapshots, not a sequence of imperative edits.

## Hypercode and persistence

```text
<sketch>/
  CURRENT
  .lock
  revisions/<revision>/
    notes.hc
    notes.hcs
    metadata.json
```

`.hc` contains only `Note#id` and two-space nesting. `.hcs` contains exact ID
selectors with `label` and `detail` string properties. These two files are the
stored text/topology source, not exports of a second editable node database.
`metadata.json` retains citations, arbitrary graph links, review observations,
parent revision, capture time and content hashes. The capture time is not a
claim about the original utterance time. Nesting does not imply execution order.

The adapter deliberately supports only its emitted Hypercode subset. Hypercode's
reference HCS reader removes outer quotes literally; this adapter preserves
quotes and backslashes without YAML escape interpretation. General selectors,
imports, contracts and direct snapshot editing are outside this PoC. Future
ontology/architecture annotations require an explicit adapter extension.

Each successful update writes a complete snapshot, then atomically replaces
`CURRENT`. A local POSIX file lock and revision comparison prevent lost updates
between processes. Readers open one immutable revision. Interruption before
pointer publication leaves the previous revision usable; orphan snapshots are
excluded from history. A storage failure after publication may have committed
the new revision: reread before retrying. No automatic cleanup deletes history.

`specgraph notes verify_history --workspace <sketch>` validates every published
snapshot and follows parent revisions to the root. It rejects missing, malformed
or changed snapshots and cycles. `read_notes --history-limit` is limited to 100
entries and does not prove completeness beyond the displayed history. This
structural check does not authenticate quotations or approve their publication.

Local sketches under `conversation_memory/sketches/` are Git-ignored and survive
process/session restart; copying the directory preserves their history. They
are not a backup and must be copied before removing the checkout. Existing
Markdown memory indexes, canonical sources, and SpecSpace remain unchanged.
There is no delete/merge operation, automatic semantic deduplication, model
orchestration, GUI, or existing-memory-index integration in this slice.

## From a sketch to a proposed graph change

The [dogfooding amendment to proposal 0045](proposals/0045_conversation_memory_exploration_vault.md#dogfooding-from-conversation-notes-to-a-proposed-graph-change)
describes the next manual handoff: select attributable notes, identify the
existing graph region, prepare a bounded proposed delta and use the existing
promotion process. Its primary target is SG-SPEC-0050; SG-SPEC-0051 governs the
later review and materialization transitions. This is a prepared proposal,
not an implemented exporter or completed canonical application.

Distinguish approval of an action from approval of the displayed whole sketch.
For example, "prepare the proposal" is recorded as a source quotation and a
scoped note using `revise`; it must not be represented by `approve`, which
records a whole-sketch review. The proposal can preserve the selected source
excerpts for review without publishing the Git-ignored sketch. Semantic
agreement, action authorization and canonical acceptance retain their subjects.

## CN-CAPTURE trace pilot

The [bounded pilot](reviews/0045_cn_capture/README.md) follows one curated
`notes` node from the local conversational sketch through proposal atom
`CN-CAPTURE`, a pending Requirement/criterion candidate, existing Python
declarations and an executable CLI test. The replay saves the note without
choosing a semantic kind and reads it in a fresh process.

CI retains `cn-capture-evidence`: JUnit, selected source inputs, raw CLI results,
an observation with source/run identities and the HC/HCS snapshot. The original
sketch remains local. The test observes capture behavior; Requirement adoption,
fulfillment and evidence admission remain pending or not evaluated. Source-file
hashes and run IDs retain provenance rather than authenticate it.

The [adoption review preparation](reviews/0045_cn_capture/adoption/README.md)
collects both unchanged candidates, the human quotation and its proposed Intent
interpretation, four pending transition records and historical CI identity.
Workspace allocation, final publication records and the Intent relation's
canonical binding remain pending. Merging the preparation does not adopt subjects.

The operator's agreement with the three displayed meanings is retained in a
separate [semantic decision](reviews/0045_cn_capture/adoption/semantic-review.json)
bound to the unchanged preparation. It preserves the response and its context;
publication decisions remain pending.

The [complete CN-CAPTURE materialization package](reviews/0045_cn_capture/materialization/README.md)
contains full proposed records, one exact `derived_from` relation, workspace and
topology selection, the version-2 writer request and pending decision templates.
An isolated preview rehearses the four-file source without changing a production
ref. Recording actual ingress reviews requires a new packet scope before final
publication approval; historical CI evidence is not automatically admitted.

The [CN-CAPTURE source review](reviews/0045_cn_capture/source-review/README.md)
recommends accepting the two ingress lineages, retaining before-kind selection
and fresh-process recovery as disclosed agent interpretations. Its recorded
agent decisions and task authorization are separate from human ingress review
and publication permission; the original materialization inputs stay unchanged.

The [confirmed CN-CAPTURE SpecDraft](reviews/0045_cn_capture/publication/README.md)
retains actual human confirmation of both source lineages and the two
`proposal -> spec_draft` transitions. A new final publication packet binds those
reviews and the unchanged writer payload. Canonical transitions, effects and
exact publication permission remain pending; accepted ingress is not re-reviewed.

## Validation

`tests/test_conversation_notes.py` exercises new-process recovery, rename/move
identity, exact quotations, branch reads, malformed batches, concurrent writers,
stale revisions, interrupted publication, approval scope and literal HCS text.
Set `HYPERCODE_BIN` to the reference CLI to also validate the saved `.hc`/`.hcs`
with `hypercode emit --ir-version 2`. Ordinary Python CI does not build Swift.

```bash
.venv/bin/python -m pytest -q tests/test_conversation_notes.py
```

The first local conversation replay on 2026-10-23 retained 11 short nodes,
two named links and three published revisions. The first two updates used
operator quotations; the third attributed the `.hc`/`.hcs` storage interpretation
to the assistant. A fresh CLI process recovered the notes and source history.
No approval record was manufactured from the instruction to implement the PoC.
The live sketch is local at `conversation_memory/sketches/hypercode-conversation-poc`;
its content has not been adopted as canonical intent.

Reference compatibility was checked with Hypercode source
`cb577e1bf68db79da34e465f63656c3cd79a7d53`: all 26 focused cases passed, including
the optional native compiler case, and the live replay also emitted IR v2.
These checks establish persistence and format compatibility. Whether the sketch
faithfully captures the person's meaning remains a conversational review task.
