# Conversation Memory Exploration Vault

## Status

Draft proposal

## Context

SpecGraph already has several pieces of the pre-canonical flow:

- `SG-SPEC-0007` defines mediated discovery between raw user goals and
  canonical intent/spec nodes.
- `SG-SPEC-0008` defines explicit project-memory consultation, including
  PageIndex-backed conversation recall as declared mediated context.
- `0011_pre_spec_semantic_layer.md` defines a pre-spec layer for raw
  conversational material before proposal/spec promotion.
- `0037_implementation_work_layer.md` names Layer 0 as Exploration.
- `0041_graph_next_moves_game_master_surface.md` starts turning graph state into
  operator guidance.

The remaining gap is not whether prior conversations may inform mediation.
That is already allowed when declared. The gap is how SpecGraph should
systematically convert raw conversation and session material into structured,
linked, reviewable pre-spec memory before it becomes proposal pressure.

Ars Contexta is a useful reference pattern for this gap because it treats agent
conversation as a source for a persistent markdown knowledge system with
schemas, links, navigation maps, processing phases, and session capture. This
proposal does not adopt Ars Contexta as a dependency or template. It uses that
shape as evidence for a SpecGraph-native layer.

## Problem

Today, many SpecGraph next moves still originate in dialogue:

- the operator explains an architectural concern;
- the assistant interprets it;
- a proposal or runtime slice is created;
- later, the rationale is recovered from chat history if someone remembers it.

This works while one conversation thread is active, but it is not graph-native.

Without a conversation-memory layer:

- repeated ideas stay implicit until manually converted into proposals;
- assumptions and decisions can be lost between sessions;
- PageIndex search remains a recall tool, not a structured pipeline;
- raw chat can be over-promoted directly into specs;
- proposal authors lack a typed source layer for claims, questions, decisions,
  and unresolved assumptions;
- ContextBuilder cannot show where an idea came from before it became a
  proposal or spec.

SpecGraph needs a reviewable path:

```text
raw conversation
  -> structured memory notes
  -> linked exploration maps
  -> intent/proposal pressure
  -> reviewed proposals
  -> canonical specs
```

## Goals

- Define a first-class Conversation Memory / Exploration Vault layer.
- Keep raw conversation distinct from structured memory and canonical specs.
- Support typed markdown notes with machine-readable metadata.
- Preserve links from notes back to source conversations or session captures.
- Turn repeated or high-signal memory into proposal pressure, not direct specs.
- Allow PageIndex as one backend while avoiding a hard PageIndex dependency.
- Give ContextBuilder a future surface for browsing memory-derived exploration
  maps before promotion.
- Preserve human review at every promotion boundary.

## Non-Goals

- Importing Ars Contexta or depending on Claude Code plugin mechanics.
- Replacing PageIndex.
- Auto-promoting chat excerpts into canonical specs.
- Creating a full Zettelkasten or personal knowledge management system inside
  SpecGraph.
- Requiring semantic vector search.
- Defining final storage layout for every possible note type.
- Running autonomous long-form conversation mining without review.

## Layer Placement

This proposal refines Layer 0 rather than creating a new canonical layer.

```text
Layer 0a: Raw Conversation Sources
Layer 0b: Structured Conversation Memory
Layer 0c: Exploration / Intent Pressure
Layer 1: Canonical Specification
Layer 2: Implementation Work
Layer 3: Runtime / Evidence / Metrics
```

Layer 0a is source material. Layer 0b is structured but still pre-canonical.
Layer 0c is reviewable pressure toward proposals or intent nodes.

Nothing in Layer 0 becomes canonical truth by being captured.

## Core Model

### 1. Conversation Source

A conversation source records where raw material came from.

Possible source backends:

- PageIndex-backed conversation recall;
- local markdown transcript;
- exported ChatGPT JSON or compiled markdown;
- session capture artifact;
- operator-pasted excerpt;
- future external note system.

The source record should preserve:

- `source_id`;
- `source_type`;
- source path or backend reference;
- capture time;
- optional query or selection rationale;
- source boundary notes;
- whether the material is raw, summarized, or curated.

### 2. Structured Memory Note

A structured memory note is a typed markdown file with a machine-readable block.

Initial note kinds:

- `claim`: a reusable assertion about the product, process, or domain;
- `assumption`: an unverified condition that affects interpretation;
- `decision`: a reviewed or tentative direction;
- `question`: unresolved ambiguity;
- `pattern`: recurring workflow or design shape;
- `constraint`: boundary or prohibition;
- `source_summary`: compact summary of a source conversation or session.

Example:

```markdown
---
memory_note_id: cmem-2026-05-01-0001
note_kind: assumption
source_refs:
  - pageindex://chatgpt/...
status: structured
promotion_state: not_promoted
links:
  related_specs: []
  related_proposals: []
  related_memory_notes: []
---

# Metric Packs Need Adapter Gaps

Metric-pack execution should not be attempted until missing inputs are exposed
as adapter computability gaps.
```

Markdown is useful for review and linking. The metadata block is the contract
that prevents unstructured prose from becoming invisible state.

### 3. Exploration Map

An exploration map groups structured notes into a navigable region.

It is analogous to a Map of Content, but SpecGraph should treat it as a derived
exploration projection rather than a knowledge-management feature.

An exploration map should answer:

- What idea cluster is being explored?
- Which claims/assumptions/decisions/questions are involved?
- Which notes are repeated or high-signal?
- Which proposal candidates are suggested?
- Which memory notes are blocked by missing attribution or review?

Candidate artifact:

```text
runs/conversation_memory_map.json
```

### 4. Promotion Pressure

Structured memory becomes useful to SpecGraph only when it produces reviewable
pressure.

Allowed pressure outputs:

- candidate intent fragments;
- proposal candidates;
- pre-spec semantic drafts;
- open questions for operator review;
- backlog entries;
- next-move suggestions.

Disallowed direct outputs:

- canonical `specs/nodes/*.yaml`;
- policy mutations;
- metric threshold changes;
- implementation work items without intervening proposal/spec review.

## Processing Pipeline

The pipeline should be SpecGraph-native, but it can reuse the useful shape of
record/reduce/reflect/reweave/verify/rethink:

1. `capture`: preserve raw source reference and source boundary.
2. `reduce`: extract typed memory notes.
3. `reflect`: link notes to existing specs, proposals, and notes.
4. `reweave`: update older structured notes when new context changes their
   interpretation.
5. `verify`: validate schema, source attribution, and promotion boundaries.
6. `project`: emit exploration maps and proposal pressure.
7. `rethink`: challenge stale assumptions or overloaded memory regions.

Each phase should be independently repeatable and should not require the full
conversation history to stay in context.

## Derived Artifacts

First implementation slices should be read-only and derived-first.

Suggested tracked policy:

```text
tools/conversation_memory_policy.json
```

Suggested local/derived artifacts:

```text
runs/conversation_memory_index.json
runs/conversation_memory_map.json
runs/conversation_memory_promotion_pressure.json
```

The first index should report:

- source count;
- structured note count;
- note-kind counts;
- promotion-state counts;
- missing-attribution count;
- stale-note count;
- proposed next gaps.

The map should report:

- clusters;
- links;
- source coverage;
- related specs/proposals;
- candidate proposal pressure;
- review blockers.

The promotion-pressure artifact should report:

- candidate target kind: `intent_fragment`, `proposal_candidate`,
  `pre_spec_draft`, or `operator_question`;
- source memory notes;
- promotion rationale;
- review state;
- next gap.

## Storage Boundary

This proposal does not require a final storage path, but it recommends a simple
future layout:

```text
conversation_memory/
  sources/
  notes/
  maps/
  sessions/
```

The key invariant is not the folder name. The key invariant is separation:

- raw sources remain attributable;
- structured notes remain reviewable;
- promotion pressure remains derived;
- canonical specs remain canonical only after proposal/spec review.

## PageIndex Boundary

PageIndex can be the first source backend because it already indexes the user's
conversation archive.

However:

- PageIndex search results are source references, not structured memory notes;
- PageIndex summaries should not be treated as canonical facts;
- any use of PageIndex-backed recall must remain declared project-memory
  consultation under `SG-SPEC-0008`;
- future backends should be able to implement the same source-reference
  contract.

## Viewer Guidance

ContextBuilder should eventually expose this as an exploration surface:

- source list;
- typed memory-note browser;
- exploration maps;
- proposal-pressure candidates;
- source attribution chips;
- warning when a candidate lacks source coverage;
- clear "not canonical" boundary.

The viewer should not provide "promote to spec" as a direct one-click action
until proposal-lane mediation exists for memory-derived candidates.

## Relationship To Existing Proposals

- `0011_pre_spec_semantic_layer.md` defines the semantic pre-spec boundary.
  This proposal defines the conversation-memory substrate that can feed it.
- `0037_implementation_work_layer.md` names Exploration as Layer 0. This
  proposal refines that layer into raw sources, structured memory, and
  exploration pressure.
- `0041_graph_next_moves_game_master_surface.md` can later use conversation
  memory pressure as one advisory input.
- `0044_metric_pack_runtime_followups.md` shows the same pattern after metric
  work: realization is recorded, then next moves become graph-visible instead
  of chat-memory-only.

## First Implementation Slice

The first bounded runtime slice should not mine the full archive.

It should:

1. Add a declarative conversation-memory policy.
2. Define note kinds, promotion states, and source-reference vocabulary.
3. Build an empty or fixture-backed `runs/conversation_memory_index.json`.
4. Validate that source references are declared and that promotion state is
   non-canonical by default.
5. Add a viewer contract for the index shape.

This gives the graph a place to grow without pretending that archive mining is
already solved.

## First Slice Realization

The first bounded runtime slice is realized by:

- `tools/conversation_memory_policy.json`;
- `--build-conversation-memory-index`;
- `make conversation-memory`;
- `runs/conversation_memory_index.json`;
- `docs/conversation_memory_viewer_contract.md`;
- inclusion in `make viewer-surfaces`.

This slice remains read-only. It defines vocabulary, validates declared source
references and non-canonical promotion states, and exposes an empty or
fixture-backed index surface. It still does not mine PageIndex, import chat
archives, create canonical specs, or emit promotion-pressure artifacts.

## Second Slice Realization

The second bounded runtime slice adds tracked storage ingestion:

- `conversation_memory/sources/*.json` for declared source boundaries;
- `conversation_memory/notes/*.md` for structured memory notes with frontmatter;
- `source_snapshot` counts in `runs/conversation_memory_index.json`;
- `storage_path` traceability for loaded sources and notes.

This still remains read-only and manual. It gives operators and future tools a
place to write curated Layer 0 memory records, but it still does not mine
PageIndex, import full chat archives, create canonical specs, or emit
promotion-pressure artifacts automatically.

## Third Slice Realization

The third bounded runtime slice adds a derived exploration map projection:

- `runs/conversation_memory_map.json`;
- `--build-conversation-memory-map`;
- `make conversation-memory-map`;
- inclusion in `make viewer-surfaces`;
- map clusters, links, source coverage, related specs/proposals, candidate
  proposal pressure, and review blockers.

This remains read-only and index-backed. It does not add archive mining, direct
promotion, canonical spec mutation, or autonomous proposal creation. Candidate
promotion pressure is visible for review, but the dedicated
`conversation_memory_promotion_pressure.json` artifact remains a later slice.

## Fourth Slice Realization

The fourth bounded runtime slice adds an explicit promotion-pressure review
queue:

- `runs/conversation_memory_promotion_pressure.json`;
- `--build-conversation-memory-promotion-pressure`;
- `make conversation-memory-pressure`;
- inclusion in `make viewer-surfaces`;
- pressure entries with target kind, source memory notes, source refs, rationale,
  review state, status, and next gap.

This is still derived-only. It turns map-level candidates into a viewer-ready
review queue, but it does not create proposal files, mutate canonical specs, or
skip proposal-lane mediation.

## Conversational Capture PoC (2026-10-23)

The operator clarified that capturing a thought must happen during the
conversation, before formalization: the person speaks and reviews while the
agent keeps short notes. The [conversation notes contract](../conversation_notes.md)
implements this bounded extension through `read_notes` and `update_notes`.

The sketch stores `Note#id` hierarchy in `.hc`, exact-selector labels/details in
`.hcs`, and quotations, named links and review observations in metadata. IDs
survive rename/move. Atomic revision publication and revision comparison prevent
partial snapshots and lost concurrent updates. Human approval is an attributed
observation about one displayed revision, not canonical adoption.

The existing Markdown-note index and its required note kinds remain unchanged.
This capture format can retain a word before a semantic kind has been chosen;
it is not silently converted into a typed memory note. The repo-local skill
guides capture and optional, authorized subagent suggestions. There is no new
Supervisor authority, ontology mutation, automatic delegation, MCP server or UI.

The verification boundary is local CLI/API persistence and native Hypercode
format compatibility. The PoC's useful next observation is whether a person can
recognize their intent in the saved sketch and continue it in a later session.

## Dogfooding: From Conversation Notes to a Proposed Graph Change

### Problem and intended result

The capture PoC now lets the operator discuss and rearrange a sketch. The next
gap is the handoff from that sketch to a specific proposed change in SpecGraph's
own specification graph. The motivating intent is to retain thoughts at
conversation speed, refine them together, and carry their meaning and sources
into a reviewable change to the system being designed.

This amendment is the first manual dogfooding handoff. The
[source excerpts](../archive/proposal_sources/0045_conversation_memory_exploration_vault.md#dogfooding-handoff-source-excerpts)
preserve the operator's request, the assistant's proposed next action, and the
operator's approval to prepare this amendment. Canonical YAML is unchanged;
the proposed delta below is ready for discussion. Automatic sketch ingestion
and proposal generation remain future runtime work.

### One bounded path

1. **Capture:** save a short note with its original quotation. A word is enough
   to start; choosing a semantic kind does not block saving.
2. **Refine:** discuss, rename and regroup notes while keeping their identities
   and sources. Distinguish the operator's words from assistant interpretation.
3. **Select a change:** identify the motivating intent, remaining questions and
   the existing graph region. Propose a bounded update; justify a new child or
   restructuring only when the existing node's scope cannot hold the concern.
4. **Prepare the proposal:** preserve selected source excerpts, the sketch
   revision and note IDs, target spec IDs, the proposed delta, and acceptance
   examples. Reuse an existing proposal covering the same concern.
5. **Review and apply:** use the existing pre-spec promotion and proposal-lane
   process for the specific reviewed change. The conceptual sequence is
   `raw_input -> IntentFragment -> IntentDraft -> Proposal -> SpecDraft -> canonical_artifact`.
   Its transitions retain the records and reviews required by SG-SPEC-0051;
   this explanatory sequence does not itself record those transitions.
6. **Realize and observe:** implement the accepted bounded change, test it and
   use the same conversational scenario again to discover the next gap.

The agent performs the bookkeeping. The person can discuss the meaning and
authorize a next action without approving each saved note. A note may also stay
open or be set aside; reaching consensus does not require promoting every node.

### Selected graph region and proposed delta

The primary target is **SG-SPEC-0050**, the existing Pre-Spec Semantic Layer
under SG-SPEC-0007. It already owns the observed-intent envelope and upstream
promotion boundary. No new canonical node or semantic kind is proposed in this
slice. Hypercode files, CLI commands and agent workflow stay in this proposal
and its technical contract, outside the canonical node's storage-agnostic scope.

Proposed additions to `specs/nodes/SG-SPEC-0050.yaml`, for subsequent review:

- Under `specification.observation_model.retained_parent_role`, add:
  "A conversational sketch may supply attributable raw input to the existing
  observed-intent envelope. Capturing or rearranging its notes alone does not
  assign IntentFragment, IntentDraft, Proposal, or canonical status."
- Under `specification.examples`, add a conversation-refinement example:
  a person and agent refine a short note; selected source material informs an
  IntentDraft; a candidate change identifies an existing spec and explains the
  proposed amendment; downstream promotion follows SG-SPEC-0051. Agreement to
  prepare that amendment is recorded with that action's scope.
- Add an acceptance criterion requiring this example to distinguish capture,
  observed-intent interpretation and downstream promotion, while preserving
  the existing delegated semantic and review boundaries.

Related contracts are reused unchanged:

| Contract | Role in this handoff |
| --- | --- |
| SG-SPEC-0053 | Meaning and separation of IntentFragment, IntentDraft and Proposal |
| SG-SPEC-0052 | Provenance, review axes and traceability |
| SG-SPEC-0051 | Promotion records, review and canonical materialization |
| SG-SPEC-0006 | Repository-tracked proposal scope and application authority |

### Approval scope observed in this conversation

The operator approved **preparing an amendment to proposal 0045 with selected
spec targets and proposed changes**. The live note records this quotation and
scope. It does not use the PoC's whole-sketch `approve` operation: that operation
means approval of one displayed sketch revision, which is a different subject.
The proposed canonical delta above was prepared after the operator's statement
and has not received canonical application approval.

For the PoC, keeping the action and quotation in a note plus this source-backed
amendment is sufficient. No new approval API, authority state or automatic
promotion rule is introduced. Later formal transitions use SG-SPEC-0051's
existing source/target references, outcome and review records.

### Handoff evidence and next verification

The local sketch `hypercode-conversation-poc` preserves
`notes_to_specgraph_proposal` at revision `62ea6b7d435d4bfa9d69eb748dd3a10e`.
Earlier nodes `conversation` and `system_design` retain their identities after
regrouping. These local IDs are scoped to that sketch, not canonical spec IDs.
The curated excerpts in the source archive let a reviewer inspect this handoff
without access to the Git-ignored sketch. They do not publish its full history
or independently authenticate the conversation.

This preparation is complete when the source, motivating intent, target,
proposed delta and authorization scope are readable together. The next review
should assess fidelity to the operator's meaning and the placement in
SG-SPEC-0050. A later accepted application should preserve traceability back
through this proposal to the selected source material. Local persistence tests
and a documentation PR do not establish that end-to-end application yet.

## Declared Draft Obligations Counter

The operator requested proposal obligations as a separate count after observing
that canonical Intent Atoms remained unchanged during this PoC. The
[explicit declaration](0045_conversation_memory_exploration_vault.intent.yaml)
records eight agent-authored draft obligations with stable IDs. They summarize
the bounded capture/handoff behavior above and retain the source archive as
context; declaring them does not grant new human approval or canonical adoption.
Each addition has a source-bound `contract_only` disposition in
`tools/intent_decision_reviews/0045-proposal-declaration.json`. This declaration
changes no production code and does not attest implementation coverage.

The existing Intent Atoms v1 analyzer reads declared YAML in the separate
`docs/proposals` scope. The PR comment renders that count beside the existing
`specs/nodes` count with matching revision/analyzer provenance. Proposals
without declarations remain unassessed. This runtime slice adds measurement
visibility without automatically extracting prose, generating canonical nodes
or changing promotion authority. See the [counting contract](../intent_atoms.md#declared-proposal-obligations).

## CN-CAPTURE source-to-test pilot

The [bounded review package](../reviews/0045_cn_capture/README.md) traces one
existing conversational note through `CN-CAPTURE`, pending SG-SPEC-0069
Requirement/criterion candidates, existing capture code and a real CLI test.
CI retains the input, raw responses, HC/HCS snapshot, source/run identities and
JUnit. This exercises the capture capability while leaving canonical subject
adoption, fulfillment and evidence admission unasserted. The existing eight
proposal obligations and canonical YAML remain unchanged.

## Acceptance Criteria

- SpecGraph has a proposal-level architecture for conversation-derived memory
  before intent/proposal/spec promotion.
- Raw conversation, structured memory, exploration pressure, and canonical specs
  are explicitly separated.
- Ars Contexta is treated as a reference pattern, not as a dependency.
- PageIndex is allowed as a backend but not required.
- Structured notes require source attribution and typed metadata.
- Promotion from memory to proposals remains review-first.
- The first runtime slice is limited to policy, index shape, validation, and
  viewer contract.
