# Draft-to-Proposal Promotion Boundary and Workflow

## Status

Draft proposal

## Problem

SpecGraph already has growing semantics for:

- intent mediation
- pre-spec lineage
- operator requests
- proposal-lane artifacts

But one important workflow is still mostly implicit:

> How does an informal working draft become a reviewable proposal artifact?

Today, the repository can project the distinction through visible document
surfaces such as:

- `docs/proposals_drafts/`
- `docs/archive/proposal_sources/`
- `docs/proposals/`

In practice, the project is already using a real distinction:

- a rough draft is allowed to be exploratory, uneven, and implementation-heavy
- a proposal is expected to be normalized, reviewable, bounded, and reusable

However, that distinction is not yet formalized as part of SpecGraph itself.

This creates several problems:

- the transition from draft to proposal can feel ad hoc
- a reader cannot always tell whether a document is merely a working note or a
  graph-facing proposal candidate
- provenance from the original draft into the proposal is not formal
- proposal promotion risks looking like manual curation rather than a governed
  workflow
- repository folders begin to encode semantics that the graph does not yet own

The result is similar to the earlier "sky-born proposal" problem:

proposal documents appear, but the project does not yet state what makes one
promotion legitimate and reviewable.

## Why This Matters

SpecGraph is trying to become a system where:

- meaning is inspectable
- transitions are reviewable
- pre-canonical material has traceable lineage
- proposals do not arrive by magic

If the project cannot explain how a working draft becomes a proposal, then an
important pre-canonical transition remains outside the graph's own governance
model.

That weakens:

- proposal provenance
- reviewer trust
- reproducibility of proposal authoring
- future viewer support for "where did this proposal come from?"
- the ability to eventually automate bounded proposal promotion safely

In short:

the project needs a formal promotion boundary between informal draft material
and graph-facing proposal artifacts.

## Goals

- Define the semantic boundary between a working draft and a reviewable
  proposal.
- Formalize a bounded workflow for draft-to-proposal promotion.
- Preserve provenance from original draft material into the promoted proposal.
- Keep promotion reviewable without forcing rough draft text directly into
  canonical or proposal-lane truth.
- Make repository folders an implementation detail rather than the sole source
  of lifecycle semantics.
- Provide a basis for later viewer support and supervisor-assisted proposal
  preparation.

## Non-Goals

- Requiring every idea to begin as a file in `docs/proposals_drafts/`
- Defining the final storage engine for all pre-spec artifacts
- Replacing normal authoring freedom for rough working notes
- Requiring immediate proposal-lane persistence for every promoted proposal
- Turning every proposal document into a canonical spec node automatically
- Defining the final GUI affordance for promotion review

## Core Proposal

SpecGraph should explicitly recognize a **draft-to-proposal promotion
workflow**.

This workflow should distinguish two different things:

- `working draft`
- `reviewable proposal`

The distinction is semantic, not merely folder-based.

### Working Draft

A working draft is an exploratory artifact that may contain:

- rough wording
- implementation-heavy notes
- mixed concerns
- unresolved boundaries
- vendor-specific suggestions
- partial arguments or thought fragments

A working draft is useful, but it is not yet a proposal artifact that the
graph can rely on as a stable review surface.

### Reviewable Proposal

A reviewable proposal is a normalized artifact that:

- states one bounded problem
- explains why it matters to SpecGraph
- defines goals and non-goals
- states a clear boundary
- names the proposed layer, workflow, or contract
- is traceable to its motivating inputs

It may still be a draft in acceptance status.

But it is no longer merely a rough working note.

## Semantic Boundary

The promotion boundary should be governed by one principle:

> Promotion is not a file move. Promotion is normalization into a reviewable
> proposal contract.

That means the project should not treat:

- "`docs/proposals_drafts/*.md`"

and

- "`docs/proposals/*.md`"

as merely two storage folders.

Instead, those should be understood as one possible repository projection of a
more important transition:

- informal draft material
- becomes a bounded, reviewable proposal artifact

## Promotion Packet

Promotion from draft to proposal should require a minimal **promotion packet**.

This packet need not be finalized as a storage schema yet, but it should
semantically carry at least:

- source draft reference(s)
- motivating concern or lineage root
- normalized proposal title
- problem statement
- goals
- non-goals
- core proposal summary
- scope or boundary notes

This ensures that proposal promotion is explainable and inspectable rather than
depending on tacit human judgment alone.

## Promotion Eligibility

A working draft should be considered eligible for promotion only when:

- it addresses one bounded concern
- its core distinction is understandable to a reviewer
- its scope is narrow enough not to collapse several unrelated proposals
- enough normalization has happened that the result can be discussed as a
  contract candidate rather than as free-form brainstorming

The key criterion is not polish.

The key criterion is reviewability.

## Provenance Preservation

Promotion must preserve provenance explicitly.

At minimum, a promoted proposal should remain traceable to:

- the source draft artifact or artifacts
- the motivating intent or concern
- any significant normalized restatement introduced during promotion

This means the project should be able to answer:

- which draft did this proposal come from?
- what concern did that draft express?
- what changed during normalization?

Without that, the proposal still feels partly "sky-born."

## Orthogonality to Canonical Status

This workflow should remain separate from canonical graph acceptance.

Promoting a draft into a proposal means:

- the idea is now reviewable in proposal form

It does **not** mean:

- the idea is accepted as canonical truth
- the proposal must be applied
- the proposal has already entered the canonical graph

This separation is important because the system already needs clean boundaries
between:

- pre-spec semantics
- proposal artifacts
- canonical specs

## Repository Projection

The repository may continue to project this distinction through directories such
as:

- `docs/proposals_drafts/`
- `docs/archive/proposal_sources/`
- `docs/proposals/`

But the folders themselves should not be the only source of meaning.

The graph-level semantics should be:

- draft material is exploratory and not yet review-ready
- promoted proposal material is normalized and review-ready enough to track as
  a proposal candidate

This makes the file layout replaceable later without losing the underlying
contract.

## Relation to Existing Pre-Spec Semantics

This proposal deliberately sits next to the existing pre-spec lineage work.

In particular:

- `SG-SPEC-0052` already defines orthogonal axis semantics for `Intent`,
  `IntentFragment`, `IntentDraft`, and `Proposal`
- but `SG-SPEC-0052` explicitly keeps concrete promotion boundaries and
  proposal-facing transition policy out of scope

This proposal covers that missing workflow boundary.

It should not replace pre-spec axis semantics.

It should add the rule for how rough draft material becomes a reviewable
proposal-facing artifact.

## Relation to Intent-to-Proposal Workflow

This proposal is narrower than the broader
`Intent -> mediated artifact -> OperatorRequest -> supervisor -> Proposal`
workflow.

Its concern is specifically:

- how informal design writing becomes a proposal artifact that the rest of that
  workflow can actually consume or reference

That makes it a useful bounded slice rather than another cross-cutting
everything-document.

## Viewer and Tooling Implications

Once formalized, the project should eventually be able to show:

- which proposals were promoted from drafts
- which proposals still lack promotion provenance
- which working drafts have not yet been normalized into proposals
- which proposals were superseded or split after promotion

This can later support:

- proposal preparation dashboards
- reviewer context overlays
- proposal lineage inspection

## Supervisor Implications

Supervisor should not immediately own this whole workflow.

But once the boundary is formalized, supervisor and related tools can
eventually help with bounded tasks such as:

- checking whether a proposed promotion packet is complete
- warning when a proposal lacks clear source provenance
- helping normalize draft text into proposal form
- avoiding silent direct jumps from raw draft notes into canonical proposal
  artifacts

That should come later.

The first step is to define the semantics cleanly.

## Adoption Order

The natural rollout order is:

1. Define the semantic boundary between working draft and reviewable proposal.
2. Define the minimal promotion packet and provenance expectations.
3. Decide how repository projections map to that semantic distinction.
4. Add tooling or viewer support for promotion provenance.
5. Only later automate bounded parts of the promotion workflow.

This order matters because the project should own the meaning of the transition
before it automates the transition.

## Why This Is Useful

The strongest value of this proposal is not "organize the docs folder better."

The strongest value is:

- turning an implicit authoring ritual into a governed workflow
- keeping proposal provenance inspectable
- making promotion from rough note to proposal legible
- preventing repository layout from silently becoming the only semantics
- preparing the ground for future graph-native proposal tracking

It gives SpecGraph one more missing bridge in the path from informal thought to
reviewable structured artifacts.

## Open Questions

- Should working drafts remain completely outside the graph, or should some
  later pre-spec artifact mirror them explicitly?
- Is promotion best modeled as a new pre-spec transition, or as a proposal-lane
  boundary event?
- What is the minimal promotion packet that provides real value without making
  authoring too heavy?
- Should promoted proposals always reference one motivating concern, or can one
  promotion packet intentionally split into several bounded proposals?
- Which layer should own eventual automation: mediator tooling, supervisor, or
  a distinct proposal-preparation actor?
