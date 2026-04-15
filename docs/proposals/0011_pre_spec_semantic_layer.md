# Pre-Spec Semantic Layer for Observable Intent

## Status

Draft proposal

## Problem

SpecGraph already has partial contracts around:

- intent mediation
- operator requests
- proposal provenance
- proposal-lane structure

But there is still no clear first-class pre-spec layer that captures how raw
user input becomes reviewable, structured graph material before canonical spec
promotion.

Without that layer, the system risks:

- losing traceability from user wording to later specs or proposals
- mixing exploratory framing with canonical structure too early
- making assistant synthesis feel opaque or "sky-born"
- creating premature proposal pressure before intent has stabilized

## Goals

- Define a pre-spec semantic layer that is graph-native and reviewable.
- Distinguish normative intent, epistemic assumptions, and candidate design
  moves.
- Preserve provenance, authority, confidence, and lifecycle status as explicit
  axes.
- Define a promotion pipeline from raw conversational material to spec-facing
  artifacts.
- Keep assistant outputs as draft declarations rather than silent canonical
  truth.
- Provide a foundation for `tasks.md:33-36` and later proposal-lane work.

## Non-Goals

- Full natural-language understanding
- Final repository layout for all future pre-spec artifacts
- Immediate introduction of a tracked Tech Spec layer
- Final viewer UX or canvas layout
- Automatic promotion from raw chat to canonical spec

## Core Principle

SpecGraph should model not only the structure of the system, but also the
structure of how intent becomes specification.

The assistant should act as a producer of reviewable draft declarations, not as
an unquestioned generator of final specifications.

## Primary Pre-Spec Kinds

### Intent

`Intent` is a normative declaration of what should become true, preserved,
prevented, or made possible.

It answers:

- What should become true?
- What should remain possible?
- What should be preserved or avoided?

Examples:

- "The original user intent should survive formalization."
- "The assistant should not push architecture too early."

`Intent` is not true or false. It is evaluated as draft, confirmed, superseded,
rejected, or promoted.

### Hypothesis

`Hypothesis` is an epistemic declaration about what may be true in the problem
space.

It answers:

- What do we currently believe may be true?

Examples:

- "Premature proposals bias framing."
- "Visible provenance increases trust in AI synthesis."

`Hypothesis` is evaluated as supported, contradicted, disputed, or unresolved.

### Proposal

`Proposal` is a candidate design move intended to operationalize one or more
intents under a set of assumptions and constraints.

It answers:

- What could we do about it?

Examples:

- "Introduce ghost nodes for assistant inference."
- "Unlock proposal mode only after intent stabilization."

`Proposal` is evaluated as accepted, rejected, alternative, risky, deferred, or
superseded.

## Auxiliary Kinds

To keep the primary triad semantically clean, the pre-spec layer should also be
able to express:

- `IntentFragment`
- `Constraint`
- `Question`
- `Evidence`
- `Risk`
- `Decision`
- `SpecDraft`

These should remain auxiliary supporting nodes, not replacements for
`Intent` / `Hypothesis` / `Proposal`.

## Intent Observation Model

### IntentFragment

`IntentFragment` is the smallest extracted semantic unit from user input that
appears to express part of an intent but is not stable enough to become a full
draft on its own.

Examples:

- "graph-native thinking"
- "no premature architecture"
- "preserve conversational context"

### IntentDraft

`IntentDraft` is a synthesized pre-spec node assembled from one or more
`IntentFragment` nodes, plus optional linked `Constraint`, `Question`, and
`Hypothesis` nodes.

Informally:

`IntentDraft = synthesize(IntentFragment*, Constraint*, Question*, Hypothesis*)`

This is the primary "observed intent" object that a mediator or assistant
should prepare for later proposal or spec-facing work.

## Orthogonal Axes

The proposal recommends not collapsing all semantics into one `kind` field.

Alongside `kind`, pre-spec nodes should support explicit axes such as:

- `phase`
- `status`
- `authority`
- `confidence`
- `provenance`
- `context_tags`
- `supersedes`

Suggested shape:

```yaml
node:
  id: "psg.intent.01"
  kind: "intent-draft"
  phase: "pre-spec"
  status: "inferred"
  authority: "assistant"
  confidence: 0.82
  text: "Support graph-native ideation while delaying premature solution pressure."
  provenance:
    messages:
      - "conv:142"
      - "conv:143"
    derived_from:
      - "psg.fragment.01"
      - "psg.fragment.02"
  context_tags:
    - "canvas"
    - "assistant"
    - "spec-authoring"
  supersedes: null
```

## Context Modeling

`Context` should not become a peer primary semantic kind next to `Intent`,
`Hypothesis`, and `Proposal`.

By default, context should be represented as:

- metadata
- overlays
- selectors
- filters
- runtime conditions
- weighting lenses

This keeps the semantic graph stable and avoids cloning one intent into many
near-duplicate context-specific nodes.

## Suggested Edge Semantics

Useful edge types for the pre-spec layer:

- `motivates`
- `constrains`
- `assumes`
- `supports`
- `contradicts`
- `answers`
- `operationalizes`
- `alternative_to`
- `risks`
- `refines`
- `derived_from`
- `promoted_to`
- `supersedes`

Examples:

- `IntentFragment --refines--> IntentDraft`
- `Constraint --constrains--> IntentDraft`
- `Proposal --operationalizes--> Intent`
- `Proposal --assumes--> Hypothesis`
- `Question --answers/blocks--> Proposal`
- `IntentDraft --promoted_to--> SpecDraft`
- `Decision --supersedes--> Proposal`

## Promotion Pipeline

The intended promotion path should look like:

1. Raw user utterance
2. `IntentFragment`
3. `IntentDraft`
4. `Proposal` and/or `SpecDraft`
5. Reviewed formal spec artifact

Compactly:

`raw input -> IntentFragment -> IntentDraft -> Proposal/SpecDraft -> formal spec`

Promotion rules should include:

- `IntentFragment` may be synthesized into `IntentDraft`
- `IntentDraft` must remain non-final until explicitly confirmed or reviewed
- `Proposal` must remain linked to motivating intent and assumptions
- `SpecDraft` may be created only from confirmed or explicitly reviewed
  pre-spec material
- assistant-inferred nodes must not be silently promoted into canonical spec
  artifacts

## Assistant Contract

The assistant should:

- continuously structure user thoughts into draft graph material
- preserve provenance to source utterances or source graph elements
- separate intent from assumptions and candidate moves
- avoid premature solution pressure
- present its synthesis as inspectable and reviewable

The assistant must not:

- silently convert exploratory material into canonical spec truth
- erase ambiguity too early
- collapse provenance into generic summaries
- treat inferred pre-spec nodes as already-authoritative decisions

## Relationship to Existing SpecGraph Work

This proposal should refine and strengthen the direction already present in:

- [0002_intent_layer.md](./0002_intent_layer.md)
- [0005_intent_to_proposal_workflow.md](./0005_intent_to_proposal_workflow.md)
- [0003_operator_request.md](./0003_operator_request.md)

Suggested interpretation:

- `0002` introduces the intent-facing layer and mediated discovery boundary
- `0005` defines the workflow from intent to proposal and provenance
- this document makes the pre-spec semantic model explicit and graph-shaped

## Why This Matters Before Proposal Lane

Proposal lane should not become the storage layer for raw user thoughts.

If proposal lane appears before a stable pre-spec semantic contract, proposals
will continue to feel ungrounded. The system needs precursor artifacts that
make proposal lineage visible:

- raw intent
- fragments
- mediated draft
- bounded request
- only then tracked proposal structure

This suggests the sequencing:

1. pre-spec semantic layer
2. distinction between user intent, mediated artifact, and operator request
3. bounded bridge into supervisor
4. tracked proposal lane

## Open Questions

- Should `IntentDraft` and related pre-spec nodes live as tracked files, graph
  projections, or both?
- What is the minimal persistent artifact needed before full mediator
  implementation?
- Which axes belong in canonical pre-spec nodes versus runtime overlays?
- When should `SpecDraft` exist separately from `Proposal`?
- How should viewer overlays expose pre-spec material without confusing it with
  canonical spec status?

## Suggested Next Spec Slices

- `UserIntent` and `IntentDraft` semantics
- mediator role and bounded discovery contract
- promotion bridge from pre-spec material into `OperatorRequest`
- provenance rules from pre-spec nodes into proposals and later specs
- viewer overlays for intent / proposal / canonical distinction
