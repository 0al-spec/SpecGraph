# Ubiquitous Vocabulary and Executable Ontology Layer

## Status

Draft proposal

## Problem

SpecGraph is intended to become an executable ontology rather than only a
repository of prose specifications.

During bootstrap, however, terminology is emerging incrementally across specs,
runtime tools, viewer logic, and project-memory workflows. Terms such as:

- `proposal_handle`
- `proposal_authority_state`
- `direct_graph_update`
- `graph_health_signal`
- `refactor_proposal`
- `governance_proposal`

already carry important semantics, but they do not yet live inside a single
machine-readable vocabulary layer.

Without such a layer, drift becomes likely:

- one meaning acquires several names
- similar names drift into different meanings
- specs, tools, and viewers stop speaking the same language
- validators cannot distinguish canonical terms from accidental synonyms

If SpecGraph is to support arbitrary domains in the future, this problem is not
limited to bootstrap governance. The system needs a way to define and execute
vocabularies for many domains, not only for its own internal growth process.

## Goals

- Define a vocabulary layer that supports executable semantic contracts rather
  than prose-only definitions.
- Separate universal semantic primitives from domain-specific vocabularies.
- Make canonical terms, aliases, relation contracts, and state families
  machine-readable enough for tooling.
- Reduce terminology drift between specs, runtime tools, metrics, and viewers.
- Support future user domains without baking current SpecGraph bootstrap terms
  into the permanent universal core.

## Non-Goals

- A complete ontology for all future domains
- Final repository layout for vocabulary artifacts
- A full implementation of ontology-aware validators
- Final viewer UX for semantic overlays
- Immediate normalization of every existing term in the repository

## Core Proposal

SpecGraph should treat ubiquitous language as a first-class layer composed of
two levels:

1. `Meta-ontology`
2. `Domain vocabularies`

The meta-ontology provides universal semantic primitives that can be reused in
any domain. Domain vocabularies instantiate those primitives for a specific
bounded context, including SpecGraph's own bootstrap governance domain.

This makes SpecGraph:

- not an ontology of one project
- but an ontology engine for many ontologies

## Proposed Layers

### 1. Meta-Ontology

The universal layer should define the smallest stable set of semantic building
blocks needed to describe a domain vocabulary.

Candidate primitives:

- `Concept`
- `RelationType`
- `StateFamily`
- `TransitionRule`
- `Constraint`
- `Invariant`
- `Context`
- `Alias`
- `Evidence`
- `DerivationRule`

These primitives should be domain-independent.

### 2. Domain Vocabulary

A domain vocabulary binds actual terms and rules to the meta-ontology.

Examples of domain vocabularies:

- SpecGraph bootstrap governance
- proposal lane semantics
- evaluator loop semantics
- a future calculator domain
- a future API platform domain
- a future robotics or legal-workflow domain

The current internal terms such as `proposal_authority_state` are therefore not
part of the universal layer. They are domain-specific instantiations.

### 3. Machine-Readable Projection

The vocabulary layer should not remain prose only.

Each vocabulary must also be expressible in a machine-readable projection such
as:

- canonical term tables
- alias maps
- relation contracts
- state transition tables
- validator rules

The graph remains the source of truth, while machine-readable projections allow
tooling to execute or validate the semantics.

## Minimum Semantic Contracts

At minimum, the vocabulary layer should be able to express the following
contracts.

### Canonical Term

A canonical term should support:

- stable name
- short definition
- owning context
- allowed aliases
- deprecated aliases
- notes on canonical vs derived meaning

### Relation Type

A relation contract should support:

- direction
- strength
- cardinality
- blocking or non-blocking semantics
- replacement rules relative to stronger or weaker relations
- canonical vs derived status

### State Family

A state family should support:

- allowed values
- transition matrix
- actor or authority allowed to change each state
- distinction between canonical state and derived state

### Context

A bounded context should support:

- primary owning domain
- terms that are only referenced from outside
- places where translation or alias rules are needed

## Hard Rules

The proposal assumes the following invariants.

- One canonical term should represent one meaning within one context.
- Each alias must resolve to one canonical term.
- New policy-level terms should not appear in specs without explicit definition
  or explicit reference to an existing canonical term.
- Every relation kind used as a first-class graph contract should have an
  explicit formal relation contract.
- Every first-class state family should have explicit transition rules.
- Tooling should eventually be able to detect undefined terms, conflicting
  aliases, and misuse of relation or state names.

## Why Prose Alone Is Not Enough

Documentation by itself is not sufficient for an executable ontology.

If a term appears only as narrative prose, tooling cannot reliably answer:

- whether the term is canonical
- whether a synonym is acceptable
- whether two fields mean the same thing
- whether a relation or state is being used correctly

This proposal therefore treats vocabulary as both:

- graph-level semantic truth
- executable projection for validators, viewers, and runtime tools

## Relationship to Existing Work

### Proposal Lane

The proposal lane already demonstrates why terminology drift matters.
Terms such as `proposal_handle`, `proposal_target_region`, and
`proposal_authority_state` need a vocabulary layer if future tooling is to use
them consistently.

### SG-SPEC-0008

Project-memory consultation introduces terms such as
`consulted_project_memory` and `pageindex_backed_conversation_recall`.
These are already domain terms that would benefit from explicit canonical
definitions and alias discipline.

### SG-SPEC-0009

The operator-request layer will need stable vocabulary for request modes,
authority boundaries, scope limits, and run semantics.

### Evaluator Loop

The evaluator loop will eventually need vocabulary support for:

- metrics
- intervention classes
- regressions
- oscillation
- plateau
- stop conditions

So the evaluator proposal should depend on, or evolve alongside, the vocabulary
layer.

## Suggested First Vocabulary Domain

The first dogfooding domain should be the current SpecGraph bootstrap domain.

A minimal first slice could normalize:

- `depends_on`
- `refines`
- `relates_to`
- `gate_state`
- `proposal_authority_state`
- `direct_graph_update`
- `refactor_proposal`
- `governance_proposal`

This is narrow enough to be tractable and broad enough to reduce drift in the
current system.

## Suggested Next Spec Slices

- `Meta-ontology primitives for Concept, RelationType, StateFamily, Alias, and Invariant`
- `Bootstrap vocabulary for current SpecGraph governance terms`
- `Alias and deprecation rules for language evolution`
- `Vocabulary projection contract for validators and viewers`

## Open Questions

- Should vocabulary items become first-class graph node kinds, tracked file
  families, or both?
- What is the minimal machine-readable projection before full ontology-aware
  validators exist?
- How should domain vocabularies refer to the universal meta-ontology without
  over-constraining future user domains?
- How should cross-context translation be represented when two domains use
  similar but non-identical concepts?
