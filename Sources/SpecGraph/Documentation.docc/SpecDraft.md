# SpecDraft Layer

SpecDraft is the proposed name for the pre-canonical authoring layer beneath
SpecGraph. It helps people formulate intent; SpecGraph retains accepted
specifications and their traceable relationships. The full design note is
`docs/specdraft_layer.md`, grounded in proposal 0045 and existing Layer 0 work.

## From conversation to specifications

```text
Conversation → SpecDraft layer → existing review/promotion → SpecGraph
                   ↑                                         ↓
                 feedback ← runtime ← delivery ← tests ← implementation
```

The person explains and reviews while the agent keeps attributed notes, links
ideas, exposes unresolved questions and prepares bounded changes. The space
can contain words, quotations, Hypercode sketches, alternatives, intent drafts,
proposals and specification candidates. A note can be saved before its semantic
kind is known. Refinement can revisit earlier assumptions.

SpecDraft preserves source lineage and distinguishes quotations from agent
interpretations. A canonical candidate has its own identity and source links;
it need not reuse a note's local ID. Rearranging a sketch does not change the
accepted graph.

## Representation and vocabulary

Hypercode `.hc` expresses a sketch's hierarchy and stable local addresses;
`.hcs` carries supported properties. Current note metadata retains quotations,
named links and review observations. Ontology provides shared meanings during
clarification; unresolved terms can remain questions while capture continues.

## Two uses of SpecDraft

The **SpecDraft layer** names the broad authoring space. The existing
**`SpecDraft` / `spec_draft` stage** names a prepared specification draft near
canonical promotion:

```text
raw_input → IntentFragment → IntentDraft → Proposal → SpecDraft → canonical_artifact
```

Use "SpecDraft layer" for the space and "specification draft" or "SpecDraft
stage" for a candidate's position. No stored value, schema, runtime component
or approval gate is changed by this terminology note. Agreement, task
authorization, draft acceptance and canonical approval retain their stated
subjects and scopes through the existing process.

## Current realization

<doc:ConversationNotes> describes the existing `read_notes` / `update_notes`
PoC with revisioned local storage, original quotations and diffs. An agent calls
the tools explicitly; there is no automatic chat hook. Existing memory indexes,
maps and promotion tooling provide other pieces. This proposed layer name does
not assert a complete integrated SpecDraft product or separate deployment.

The next design slice is one walkthrough from a short note to a specification
draft, showing what the person sees, what the agent saves and the exact proposed
change handed to SpecGraph.
