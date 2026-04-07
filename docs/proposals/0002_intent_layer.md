# Intent Layer and Mediated Discovery

## Status

Draft proposal

## Problem

SpecGraph currently grows best when the input is already close to a bounded spec
refinement task. Real users do not usually start there.

Typical entrypoints look more like:

- "We are building a simple calculator."
- "Split this node into two specifications."
- "The current proposal lane is too vague around ownership."
- "Let's brainstorm the product shape before writing specs."

These are valuable inputs, but they are not yet canonical specs. If they are
forced directly into `kind: spec` nodes, the graph mixes discovery, intent,
proposal, and accepted structure too early.

At the same time, keeping this material only in chat history makes it hard to
resume reasoning, align terminology, or drive deterministic supervisor runs
from GUI interactions.

## Goals

- Introduce a persistent intent-facing layer that can capture raw or
  semi-normalized user goals without pretending they are already executable
  specs.
- Define a mediator role that conducts discovery, clarification, DDD-style
  terminology alignment, and bounded-context surfacing before canonical spec
  refinement begins.
- Provide a bridge from GUI actions and free-form chat into bounded supervisor
  runs.
- Keep the result compatible with the emerging proposal lane in
  [`SG-SPEC-0006`](../../specs/nodes/SG-SPEC-0006.yaml) and with the
  vocabulary/meta-ontology direction captured in
  [`0001_vocabulary.md`](./0001_vocabulary.md).

## Non-Goals

- Final repository layout for all future intent artifacts
- Full mediator implementation
- A finished meta-ontology for every possible domain
- Final viewer UX for discovery workflows

## Proposed Layers

### 1. User Intent Layer

Persistent, tracked artifacts or graph nodes that capture what the user is
trying to achieve before the system has agreed on canonical spec structure.

Examples:

- raw product goal
- selected-node action request from GUI
- exploratory domain notes
- unresolved terminology or context questions

This layer should preserve ambiguity rather than erasing it too early.

### 2. Mediated Discovery Layer

A mediator agent or workflow sits between the human and the supervisor.

Its job is to:

- collect and restate user intent
- identify bounded concerns or contexts
- align vocabulary
- surface open questions
- normalize the result into a bounded operator request

This layer behaves more like a DDD facilitator than a deterministic executor.

### 3. Supervisor Execution Layer

The supervisor should continue to operate on bounded, deterministic work:

- refine one spec
- emit one proposal
- split one oversized spec
- apply one reviewed proposal

The supervisor should not be the primary place where ambiguity is explored or
product discovery is performed.

## Key Entities

### UserIntent

A persistent representation of what the user wants, before it becomes an
accepted spec or accepted graph proposal.

Candidate properties:

- source statement
- normalized goal
- selected node or graph region, if any
- open questions
- agreed terms
- related domains or bounded contexts

### OperatorRequest

A normalized bounded execution request derived from mediated discovery.

Candidate properties:

- mode
- target node or region
- bounded instruction
- authority boundary
- scope limit
- optional viewer context

This is the object the supervisor should ultimately consume.

### Mediator

A discovery-oriented agent role that can:

- interview the user
- brainstorm possibilities
- clarify intent
- translate raw intent into one or more bounded operator requests

## GUI Scenarios

### Empty graph bootstrap

User action:

- "We are building a simple arithmetic calculator."

Expected flow:

1. Capture a `UserIntent`
2. Run mediated discovery
3. Emit one bounded `OperatorRequest`
4. Let supervisor create or refine the first seed/root spec

### Node-scoped refinement

User selects a node and says:

- "Split this node into two specifications."

Expected flow:

1. Capture the selected node plus instruction as `UserIntent`
2. Mediator normalizes it into a bounded split request
3. Supervisor executes one explicit targeted run with that request

## Relationship to Proposal Lane

The intent layer is not the same as the proposal lane.

- Proposal lane holds reviewable candidate graph structure.
- Intent layer holds pre-spec or pre-proposal intent and discovery artifacts.

However, the two layers should compose:

- mediator may transform an intent into a proposal-producing supervisor run
- proposal lane may preserve reviewable structure derived from intent
- viewer should eventually be able to expose both as separate overlays

## Relationship to Ubiquitous Language

This proposal is tightly connected to the vocabulary proposal:

- mediator needs a place to align terms
- user intent should not silently invent canonical terminology
- normalized operator requests should use canonical terms where available and
  explicitly mark unresolved language where not

This suggests the future ontology/language layer and the intent layer should be
designed to cooperate rather than evolve independently.

## Suggested Next Spec Slices

- `Intent Layer and UserIntent node semantics`
- `Mediator role and bounded discovery contract`
- `OperatorRequest contract for GUI and supervisor`
- `Viewer projection for intent and proposal overlays`

## Open Questions

- Should `UserIntent` be a new graph node kind, a tracked file family, or both?
- Should mediated discovery outputs live in canonical YAML, tracked proposals,
  or a separate intent directory?
- What is the minimal `OperatorRequest` schema needed before GUI integration?
- How should unresolved vocabulary be represented so later ontology work can
  absorb it cleanly?
