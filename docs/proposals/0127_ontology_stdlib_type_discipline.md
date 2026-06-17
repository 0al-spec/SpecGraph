# Ontology Standard Library Type Discipline

RFC: SG-RFC-0127
Version: 0.1.0

## Status

Draft proposal

Decision scope: process and authoring contract for treating accepted Ontology
entities as canonical type symbols for SpecGraph authoring and review.

This document defines a process contract only. It does not implement a full
type system, change the active supervisor prompt, execute prompt agents, add a
write gate, mutate canonical specs, accept ontology terms, write Ontology
packages or lockfiles, import owner decisions, or add SpecSpace mutation UI.

## Source Material

This proposal captures the operator intent that accepted Ontology entities
should constrain spec-authoring agents like base types or standard-library
types constrain programming-language authors.

Source draft:

- `docs/archive/proposal_sources/0127_ontology_stdlib_type_discipline.md`

Related proposal context:

- `0001_vocabulary`
- `0011_pre_spec_semantic_layer`
- `0013_default_deny_write_authority`
- `0060_external_ontology_import_plane`
- `0100_ontology_grounded_semantic_control`
- `0116_ontology_semantic_lint_input`
- `0117_ontology_supervisor_soft_gate_wiring`
- `0118_ontology_prompt_agent_context_artifact`
- `0119_ontology_canonicalization_backlog`
- `0126_specauthor_claim_calibration_prompt_contract`

## Summary

SpecGraph should treat accepted Ontology entities as canonical semantic type
symbols supplied by the active ontology package set. In programming-language
terms, those entities behave like base types or standard-library vocabulary:
they are imported and reused; they are not silently redefined by local
specifications.

The short rule is:

```text
Ontology accepted entity -> canonical type symbol / semantic stdlib term.
SpecGraph term -> usage or binding in a concrete artifact.
Proposal term -> candidate concept until reviewed.
Practical ontology term -> observed evidence only, never authority.
Unknown term -> ontology_gap or candidate_term, not accepted vocabulary.
```

This extends `0126` by making the ontology part of active-frame resolution more
precise: resolving ontology is not just loading context. It also means binding
generated vocabulary to accepted type symbols where they exist.

## Problem

The Ontology and SpecGraph line now has source-backed semantic linting,
supervisor soft-gate evidence, prompt-agent ontology context, owner-decision
contracts, decision previews, and SpecSpace review surfaces. Those artifacts
reduce hallucinated terms, but the process still needs a crisp authoring
model:

- accepted Ontology entities should not be treated as optional hints;
- observed practical ontology terms should not look accepted;
- new local terminology should not be promoted by accidental usage;
- SpecGraph topology edges such as `depends_on`, `relates_to`, and `refines`
  should not be mixed with semantic ontology relations;
- agents need a simple rule for choosing between reuse, aliasing, gap creation,
  and owner review.

Without this distinction, practical ontology can become visually convincing but
semantically ambiguous. A derived edge such as:

```text
SG-SPEC-0041 refines SG-SPEC-0034
```

is a valid SpecGraph topology fact. It is not evidence that either long title
or `refines` relation has been accepted as an Ontology package term.

## Proposal

Introduce `specgraph.ontology-stdlib-type-discipline.v0.1` as a process
contract for ontology-aware SpecGraph authoring and review.

The contract defines four semantic classes:

```yaml
semantic_classes:
  accepted_ontology_entity:
    authority: "Ontology owner decision and accepted package"
    authoring_role: "canonical type symbol"
    mutation_allowed_from_specgraph: false
  specgraph_term_binding:
    authority: "SpecGraph artifact under review"
    authoring_role: "usage of accepted or candidate vocabulary"
    mutation_allowed_from_specgraph: "only through reviewed SpecGraph PR"
  practical_ontology_observation:
    authority: "derived evidence only"
    authoring_role: "observed map of current usage"
    mutation_allowed_from_specgraph: false
  ontology_gap:
    authority: "candidate requiring owner review"
    authoring_role: "request for a missing term, alias, relation, or domain"
    mutation_allowed_from_specgraph: false
```

The process treats accepted Ontology entities as stable symbols in an imported
namespace. SpecGraph may bind to them, cite them, or request gaps around them,
but it must not accept, reject, deprecate, or rewrite them without the Ontology
owner decision path.

## Authoring Rules

Before producing a graph-facing artifact, a spec-authoring agent should:

1. Resolve the active ontology package set, domain, context, lifecycle phase,
   and target artifact.
2. Search accepted ontology entities, aliases, and accepted relations for each
   domain term it intends to use.
3. Bind generated terms to accepted ontology entities when a suitable accepted
   entity exists.
4. Emit `ontology_gap` or `candidate_term` when no suitable accepted entity
   exists.
5. Mark deprecated or rejected terms as lint findings, not as reusable
   vocabulary.
6. Keep SpecGraph topology edges separate from semantic ontology relations.
7. Keep practical ontology observations read-only and non-authoritative.

The minimum machine-readable gap shape is:

```yaml
ontology_gap:
  proposed_term: ""
  proposed_kind: "entity | relation | alias | domain | context"
  reason: ""
  source_refs: []
  candidate_bindings: []
  status: "requires_owner_review"
  canonical_mutations_allowed: false
```

## Practical Ontology Boundary

Practical ontology remains useful as a working map. It should show what terms,
relations, and topology facts are actually present in current specs and
proposals. It must also make the authority class explicit.

The derived view should separate:

```text
semantic vocabulary
candidate gaps
canonical bindings
SpecGraph topology edges
proposal references
```

SpecGraph topology edges should keep stable IDs in the primary display:

```text
SG-SPEC-0041 refines SG-SPEC-0034
```

Long titles and source paths remain evidence details. They should not become
primary relation identifiers that look like accepted ontology symbols.

## Relationship To 0126

Proposal `0126` defines the epistemic and ontological prompt contract for
SpecAuthorAgent, including active-frame resolution and F/G/R calibration.

This proposal narrows one part of that contract:

```text
active ontology resolution means importing canonical type symbols and binding
generated vocabulary to them before writing graph-ready text.
```

The two proposals compose as:

```text
0126: claims must be scoped, calibrated, and context-aware.
0127: terms must bind to accepted ontology type symbols or become gaps.
```

## Future Write Gate

A later implementation should add a term-binding rule to the SpecGraph write
gate for generated artifacts:

```yaml
reject_if:
  - condition: "new_term exists and ontology_gap is missing"
    message: "New terms require ontology_gap or candidate_term review."
  - condition: "accepted ontology term exists but generated artifact creates duplicate local term"
    message: "Reuse the accepted ontology entity or justify a distinct gap."
  - condition: "practical ontology observation is marked accepted"
    message: "Observed practical terms are evidence only, not accepted vocabulary."
warn_if:
  - condition: "SpecGraph topology edge is displayed as semantic relation"
    message: "Separate topology edge from ontology semantic relation."
```

This gate should start in warning or review mode before any hard rejection is
applied to existing artifacts.

## Non-Goals

- Implementing a full programming-language type system.
- Changing the active supervisor prompt in this PR.
- Executing prompt agents.
- Adding a write gate or validator in this PR.
- Accepting, rejecting, deprecating, or renaming ontology terms.
- Writing Ontology packages.
- Writing `specs/imports/ontology.lock.yaml`.
- Mutating `specs/nodes/*.yaml`.
- Importing owner decisions into canonical SpecGraph specs.
- Closing semantic gates from practical ontology observations.
- Adding SpecSpace mutation UI.

## Proposed Child Proposal Sequence

### 0127-A: Practical Ontology Relation Taxonomy

Update SpecSpace and its consuming contract so practical ontology separates
semantic terms, candidate gaps, canonical bindings, graph topology edges, and
proposal references.

Expected boundary:

- read-only derived API or view only;
- no Ontology package writes;
- no canonical SpecGraph spec mutation;
- topology edges displayed with stable spec IDs first.

### 0127-B: Term Binding Policy Artifact

Add a SpecGraph policy artifact that defines accepted-term reuse, duplicate
term warnings, ontology gap shape, and deprecated/rejected term handling.

Expected boundary:

- policy and fixtures first;
- no active prompt execution;
- no hard write gate until warnings are understood.

### 0127-C: Generated Artifact Write-Gate Rule

Add a validation rule for generated graph-facing artifacts so unknown terms
become `ontology_gap` records and duplicate accepted terms are rejected or
flagged for review.

Expected boundary:

- generated artifacts only at first;
- warning/review mode before broad hard blocking;
- no retroactive rejection of existing specs.

### 0127-D: First Real Ontology Standard Library Slice

After the boundary is stable, introduce a small accepted ontology package slice
that contains project vocabulary suitable for import as a semantic standard
library.

Expected boundary:

- Ontology owner decision evidence required;
- source, version, and digest required;
- SpecGraph import remains reviewed and explicit.

## Acceptance

This contract slice is complete when:

- proposal `0127` has source draft provenance;
- promotion registry records the bounded source and scope;
- runtime registry records this as a deferred contract slice rather than an
  implemented runtime behavior;
- proposal tracking gate passes;
- documentation sync passes or reports no required DocC delta;
- future child proposals can cite `0127` without using it as authority for
  canonical mutation, ontology package writes, prompt execution, or SpecSpace
  mutation UI.

## Authority Boundary

This proposal may be used as:

- a process contract for ontology-aware authoring;
- a parent for practical ontology taxonomy work;
- a parent for term-binding policy and write-gate follow-ups;
- evidence that accepted Ontology entities should behave as canonical semantic
  type symbols for SpecGraph authoring.

This proposal may not be used as:

- approval to accept or reject ontology terms;
- approval to write Ontology packages or lockfiles;
- approval to mutate canonical SpecGraph specs;
- approval to execute prompt agents;
- approval to hard-block existing artifacts retroactively;
- approval to treat practical ontology observations as accepted vocabulary;
- approval to add SpecSpace mutation UI.
