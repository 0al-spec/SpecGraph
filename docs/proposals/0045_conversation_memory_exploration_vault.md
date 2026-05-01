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
