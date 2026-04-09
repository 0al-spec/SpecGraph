# Intent-to-Proposal Workflow and Provenance

## Status

Draft proposal

## Problem

The current SpecGraph runtime can already:

- refine bounded specs through `supervisor`
- emit or manage tracked proposal-lane structures
- preserve some project-memory policy
- accept explicit single-run steering through the emerging `OperatorRequest`
  layer

However, a proposal can still appear to arrive "from the sky."

From a user point of view, this is unsatisfying because a reviewable proposal
should feel like the result of an explicit, inspectable workflow rather than an
opaque output of one runtime agent.

From a graph point of view, this means the lineage between:

- raw user intent
- mediated clarification
- run steering
- supervisor execution
- proposal emission

is not yet fully first-class.

## Goals

- Define the expected workflow by which a simple user intent becomes a
  reviewable proposal.
- Identify which parts of that workflow already exist in SpecGraph and which do
  not.
- Make proposal provenance an explicit architectural concern rather than an
  implied runtime behavior.
- Keep this document as a cross-cutting draft artifact until the workflow can be
  decomposed into narrower spec nodes.

## Non-Goals

- Final repository layout for every pre-canonical artifact
- Final viewer UX for all workflow stages
- Full mediator implementation
- Full orchestration implementation
- Immediate conversion of the whole workflow into canonical spec nodes

## Desired Workflow

The intended normal path is:

1. `Raw intent`
2. `UserIntent` or equivalent pre-canonical artifact
3. `Mediated artifact`
4. `OperatorRequest`
5. `Supervisor run`
6. `Proposal`
7. `Review`
8. `Apply or reject`

In compact form:

`Raw intent -> mediated artifact -> OperatorRequest -> supervisor run -> Proposal -> review/apply`

This makes the proposal a traceable result of a bounded workflow rather than a
floating artifact emitted by runtime magic.

## Existing Pieces

### 1. Intent Mediation Boundary

[`SG-SPEC-0007`](../../specs/nodes/SG-SPEC-0007.yaml) already defines the
pre-canonical mediation boundary between raw user goals and canonical intent or
spec nodes.

What it already gives us:

- raw user goals are not forced directly into canonical spec form
- mediated discovery is a distinct concern
- canonicalization has a boundary and provenance expectations

### 2. Project Memory Consultation

[`SG-SPEC-0008`](../../specs/nodes/SG-SPEC-0008.yaml) defines policy for
explicit project-memory consultation during intent mediation.

What it already gives us:

- PageIndex-backed recall can be treated as declared project memory
- memory use must remain attributable
- local project memory may be preferred before external browsing for
  project-internal ambiguity

### 3. OperatorRequest

[`SG-SPEC-0009`](../../specs/nodes/SG-SPEC-0009.yaml) defines the normalized
single-run request contract for steering one supervisor run.

What it already gives us:

- explicit target selection
- execution mode declaration
- scope and authority declaration
- one-run override semantics relative to heuristics

### 4. Proposal Lane

[`SG-SPEC-0006`](../../specs/nodes/SG-SPEC-0006.yaml) defines tracked proposal
lane semantics.

What it already gives us:

- proposal-lane identity
- proposal review state
- proposal targeting and lineage within the proposal lane
- separation between canonical graph, proposal lane, and runtime artifacts

### 5. Supervisor Governance

[`SG-SPEC-0003`](../../specs/nodes/SG-SPEC-0003.yaml),
[`SG-SPEC-0004`](../../specs/nodes/SG-SPEC-0004.yaml), and
[`SG-SPEC-0005`](../../specs/nodes/SG-SPEC-0005.yaml) already constrain how the
supervisor behaves, especially around bounded refinement, proposal-first
refactors, and application paths.

## Missing or Weakly Defined Pieces

### 1. First-Class UserIntent Artifact

We still lack a stable first-class artifact representing user intent before
mediated normalization.

Without this, the chain begins too late and the graph cannot easily show where
proposal lineage started from the user's point of view.

### 2. Mediator Workflow Contract

We have the idea of a mediator, but not yet a formal contract describing:

- what rituals the mediator performs
- how clarification and brainstorming are bounded
- when mediation is considered complete
- when the mediator must stop and ask the human

### 3. Explicit Promotion Bridge

The transition:

`UserIntent -> mediated artifact -> OperatorRequest`

is not yet formalized as a deterministic bridge.

### 4. Proposal Provenance Back to Intent

Proposal-lane lineage is partly defined, but the full provenance chain from user
intent through mediation and operator request to proposal emission is not yet
expressed as a first-class workflow contract.

### 5. Workflow-State Visibility for Viewer

The viewer can already show canonical graph structure and will likely show
proposal overlays, but we do not yet have a clean contract for visualizing:

- raw intent
- mediated artifact
- operator request
- proposal

as distinct but related stages.

## Why Proposals Currently Feel Sky-Born

A proposal currently feels like it comes "from the sky" when:

- the user never sees a persistent precursor artifact
- the mediator stage is implicit
- the `OperatorRequest` is not shown as an explicit lineage step
- the proposal appears directly as a runtime output rather than as a derivation
  from named inputs

In that situation, even a correct proposal may look arbitrary.

## Proposed Architectural Principle

Proposal emission should always be explainable as the result of a bounded chain
of artifacts and roles.

The roles are:

- `Human`: originates raw intent and remains final review authority
- `Mediator`: reduces ambiguity and creates bounded steering shape
- `Supervisor`: executes one bounded request
- `Proposal lane`: stores reviewable structural results

The artifacts are:

- `Raw intent`
- `UserIntent`
- `Mediated artifact`
- `OperatorRequest`
- `Proposal`

## Why This Document Is a Draft and Not Yet a Spec Node

This workflow cuts across several existing bounded concerns:

- intent mediation
- memory consultation
- operator requests
- proposal lane
- viewer lineage

If it were immediately turned into one canonical spec node, it would likely be
too broad and would duplicate several already-existing nodes.

For now, it is better treated as a cross-cutting draft document from which
narrower spec nodes can be carved out.

## Suggested Next Spec Slices

- `UserIntent as a first-class pre-canonical artifact`
- `Mediator workflow contract`
- `Promotion bridge from mediated artifact to OperatorRequest`
- `Intent-to-proposal lineage contract for viewer and tooling`

## Open Questions

- Should `UserIntent` live as a new graph node kind, tracked draft file family,
  or both?
- Should `OperatorRequest` always be persisted, or may it remain runtime-derived
  in some flows?
- Which artifact should be considered the first review-visible object in the
  workflow?
- How should proposal lineage reference intent artifacts without overloading the
  proposal lane itself?
