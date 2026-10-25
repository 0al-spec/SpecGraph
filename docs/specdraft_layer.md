# SpecDraft: the layer beneath SpecGraph

Design note for the operator-requested name and conceptual boundary. This
describes the pre-canonical authoring space using existing Layer 0 and promotion
concepts; it adds no runtime component, schema, lifecycle state or approval gate.

**SpecDraft helps people formulate intent. SpecGraph retains accepted
specifications and their traceable relationships.**

```text
Conversation and other sources
             ↓
SpecDraft: capture → explore → clarify → prepare specification changes
             ↓ existing review and promotion
SpecGraph: accepted Intent, requirements, rules and relationships
             ↓
Implementation → tests → delivery → runtime → feedback
                                             ↓
                                   further SpecDraft work
```

## Purpose and contents

SpecDraft is the working space where a word or rough thought can gradually
become a specification. The person continues explaining; the agent keeps
attributed notes, connects ideas, exposes questions and prepares small changes
for review. Refinement can revisit any earlier assumption or sketch.

This space can contain short notes and original quotations, Hypercode sketches,
links between ideas, unresolved questions, competing interpretations, intent
drafts, proposals and typed specification drafts. A note can be saved before
choosing whether it is an Intent, Requirement, criterion or another semantic
kind. Incompleteness and alternatives are useful authoring states here.

SpecDraft names the broader authoring layer around the existing Layer 0
exploration and pre-canonical promotion work. Its placement is an authority
boundary, not a requirement for a separate repository, process or deployment.

## Responsibilities across the boundary

| Concern | SpecDraft layer | SpecGraph |
| --- | --- | --- |
| Meaning | Explore, distinguish sources from interpretations, resolve questions | Retain accepted formulations and their governing semantics |
| Structure | Grow and rearrange a sketch while preserving note identity and quotations | Retain accepted node identities, revisions and relationships |
| Change | Prepare bounded proposals and specification candidates | Apply the specifically reviewed canonical change |
| Traceability | Preserve the path from source through interpretation to proposed records | Connect accepted intent/specifications to implementation and evidence |
| Feedback | Capture new observations, contradictions and proposed revisions | Retain the accepted revision history |

Rearranging a sketch does not change the accepted graph. Each canonical
candidate has its own identity and links to its sources; it need not reuse a
note's local ID. Source lineage survives even when the accepted wording differs
from the quotation.

## Hypercode and Ontology

Hypercode provides an economical representation for sketches: `.hc` captures
hierarchy and stable local addresses; `.hcs` carries supported properties.
The current note PoC keeps quotations, named links and review observations in
metadata. A sketch can grow from a word into a more detailed design without
requiring a complete specification up front.

Ontology supplies shared meanings when clarification needs them. A draft can
reference an existing term or expose an unresolved vocabulary question. Capture
does not depend on settling every term, and a draft interpretation does not
create an accepted ontology definition.

## Layer name versus promotion stage

**SpecDraft layer** is the architectural name for the whole working space.
The existing **`SpecDraft` / `spec_draft` stage** is narrower: a prepared
specification draft near the canonical promotion boundary.

```text
raw_input → IntentFragment → IntentDraft → Proposal → SpecDraft → canonical_artifact
```

That existing sequence keeps its current contract. In explanatory prose, use
"SpecDraft layer" for the space and "specification draft" or "SpecDraft stage"
for an individual candidate's position. The name does not assign a stage to
every note or rename stored values.

## One reviewable change at a time

Saving preserves material for later work. Agreement with an interpretation,
authorization to prepare a change, acceptance of a specification draft and
approval of a canonical change each retain their stated subject and scope.
The agent records the corresponding sources using the existing process; this
layer description introduces no additional human checkpoints.

The CN-CAPTURE example illustrates the separation: a conversational note about
taking notes informed an Intent formulation, the Requirement to save before
choosing a kind, and a fresh-process recovery criterion. A confirmed
specification draft can still await canonical publication. Tests and runtime
observations remain separately attributed evidence.

## Current realization and next slice

The [conversation notes PoC](conversation_notes.md) already provides `read_notes`
and `update_notes`, revisioned local Hypercode storage, quotations and reviewable
diffs. The agent explicitly calls these operations; there is no automatic chat
hook. Existing conversation-memory indexes/maps and the pre-spec promotion
process provide other parts of this authoring space. This design note does not
claim that they form a complete integrated SpecDraft product.

The next useful design slice is one human-agent walkthrough from a short note
to a specification draft: show what the person sees, what the agent saves and
the exact proposed change at the handoff to SpecGraph. Existing IDs, sources and
review mechanisms can support that walkthrough.

Related foundations: [proposal 0045](proposals/0045_conversation_memory_exploration_vault.md),
the [conversation-memory viewer contract](conversation_memory_viewer_contract.md),
and SG-SPEC-0007, SG-SPEC-0008, SG-SPEC-0050 and SG-SPEC-0051.

## Naming source

Recorded from the current development conversation on 2026-10-25 UTC. These are
agent-curated excerpts, not native message identifiers or canonical decisions:

> Мне просто нравится название
>
> Как будто это нижележаший слой под SpecGraph

The operator then requested:

> Ok
> Давай опишем

This authorizes describing the layer; executable promotion terminology and
authority retain their current contracts.
