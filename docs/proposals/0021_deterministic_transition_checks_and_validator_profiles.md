# Deterministic Transition Checks and Validator Profiles

## Status

Draft proposal

## Problem

SpecGraph is increasingly defining meaningful transitions between artifact
surfaces:

- informal draft material
- pre-spec artifacts
- proposals
- canonical specs
- downstream implementation-facing artifacts

The project is also increasingly relying on these transitions for real work:

- self-evolution of SpecGraph
- proposal creation and review
- retrospective refactor flows
- future product-spec development inside the same system

However, the transition logic is still only partially formalized.

Today, the project has several useful checks:

- YAML validity
- linting
- acceptance/evidence alignment
- bounded supervisor write scope
- lineage and reconciliation rules

But those checks do not yet amount to one explicit deterministic transition
engine.

This creates several problems:

- promotion and application workflows are still partly procedural rather than
  explicitly validated transitions
- repository folders and human ritual still carry meaning that should belong to
  governed artifact state
- the system cannot yet say, in one deterministic way, why one transition is
  allowed or denied
- product-spec graphs built inside SpecGraph would have to reinvent the same
  promotion checks instead of inheriting a shared transition framework
- semantic review and structural validity are still too easy to conflate

In short:

the project needs formal, deterministic transition checks that can validate how
artifacts move from one governed surface to another.

## Why This Matters

SpecGraph should not only describe systems.

It should also describe and enforce how its own artifacts evolve.

That matters for two reasons.

### 1. Trustworthy Self-Governance

If SpecGraph cannot deterministically validate its own promotion and apply
steps, then parts of its governance model remain dependent on custom operator
judgment or implicit runtime behavior.

### 2. Reusable Product-Spec Runtime

If product graphs are later developed inside SpecGraph, they should inherit a
reusable transition framework rather than relying on one-off scripts for every
new domain.

That means the transition engine should be:

- graph-owned
- deterministic
- profile-driven
- reusable across spec families

This is how SpecGraph stops being just a documentation graph and becomes a
governed artifact system.

## Goals

- Define a deterministic transition-checking model for governed artifact
  transitions.
- Distinguish semantic review from structural transition validity.
- Introduce normalized transition packets instead of relying on raw prose or
  folder movement.
- Separate core transition invariants from profile-specific validation rules.
- Make the system reusable for both SpecGraph self-specs and future product
  spec graphs.
- Provide a basis for scriptable validators and transition CLIs.
- Make denied transitions explainable in structured terms.

## Non-Goals

- Replacing human review of semantic quality
- Defining the final serialization format for every packet on day one
- Auto-applying transitions without review
- Encoding all product-specific semantics in the core validator
- Requiring every existing artifact to be migrated immediately
- Defining the final UI for transition inspection

## Core Proposal

SpecGraph should define a **deterministic transition engine** for governed
artifact movement.

The engine should validate transitions between artifact surfaces such as:

- draft -> proposal
- proposal -> apply packet
- apply packet -> canonical spec mutation
- canonical spec -> downstream handoff artifact

The engine should not judge whether a proposal is wise.

It should judge whether a proposed transition is structurally legitimate,
bounded, traceable, and authorized.

This preserves a crucial distinction:

- semantic quality remains a reviewer, evaluator, or proposal concern
- transition legality becomes a deterministic script concern

## Transition Packet Principle

Deterministic checks should operate on **normalized transition packets**, not
directly on arbitrary prose files.

This means the project should move toward explicit packet types such as:

- `PromotionPacket`
- `ProposalPacket`
- `ApplyPacket`
- `HandoffPacket`

These names are illustrative rather than final, but the rule should be firm:

> Validators should consume declared transition artifacts, not guess intent
> from free-form text alone.

This is necessary for deterministic behavior.

## Transition Packet Responsibilities

Each packet type should declare at least:

- source artifact reference(s)
- target artifact class or target scope
- motivating concern or lineage root
- actor or authority class
- declared change surface
- required provenance links
- transition intent

Some packet types may also carry:

- canonical target ids
- expected diff scope
- predecessor/supersession references
- reviewer-facing justification
- verification or evidence requirements

## Deterministic Check Families

The transition engine should support several families of checks.

### 1. Shape and Schema Checks

These verify that the packet itself is well-formed.

Examples:

- required fields exist
- references are syntactically valid
- value spaces are allowed
- one bounded transition intent is declared

### 2. Transition Legality Checks

These verify that the requested transition is allowed at all.

Examples:

- draft is eligible for promotion
- proposal is in a state that can be applied
- target spec is allowed to accept this class of mutation
- forbidden transition pairs are rejected

### 3. Provenance Checks

These verify that lineage and motivating concern remain inspectable.

Examples:

- source refs exist
- lineage root is preserved
- predecessor or supersession links are explicit when required
- the transition does not silently discard source provenance

### 4. Boundedness Checks

These verify that one packet is not attempting too much at once.

Examples:

- one bounded concern
- one target region or clearly declared target set
- no multi-concern promotion without explicit split semantics
- no silent broad canonical mutation

### 5. Authority Checks

These verify that the actor and declared transition class are compatible.

Examples:

- packet actor may request promotion but not canonical apply
- proposal reviewer may approve but not rewrite source provenance
- runtime tool may prepare packet but not self-authorize canonical mutation

### 6. Reconciliation Checks

These verify that the resulting artifact graph remains structurally coherent.

Examples:

- no broken `depends_on`
- no illegal `refines` topology
- no historical node left in an active path
- no invalid presence or supersession combination

### 7. Diff-Scope Checks

These verify that actual mutations match the declared packet scope.

Examples:

- changed files match declared target paths
- canonical changes remain inside allowed target set
- proposal packet does not mutate canonical spec unexpectedly
- apply packet does not exceed declared mutation surface

## Semantic Review vs Deterministic Validity

This proposal intentionally draws a hard line between two questions.

### Deterministic Validity

This asks:

- is the transition legal?
- is the packet well-formed?
- is provenance preserved?
- is the diff bounded and authorized?

This should be scriptable.

### Semantic Review

This asks:

- is the proposal good?
- is the split wise?
- is the boundary meaningful?
- is the implementation strategy sound?

This should remain reviewable and explainable, but it is not the same thing as
deterministic legality.

This distinction is necessary so that validators do not pretend to solve
judgment, while reviewers do not carry the whole burden of structural safety.

## Core Validator and Profile Validators

The engine should be split into two layers.

### Core Validator

The core validator owns transition rules that are reusable across artifact
families.

Representative concerns:

- packet schema validity
- provenance preservation
- authority shape
- transition legality framework
- diff scope
- generic lineage and reconciliation invariants

### Profile Validators

Profile validators own domain-specific or family-specific rules.

Representative profiles may later include:

- `specgraph_core`
- `product_spec`
- `techspec`
- `implementation_trace`

A profile validator may add rules such as:

- product-spec required acceptance sections
- domain-specific invariants
- required handoff fields
- required verification anchors

This keeps the shared engine stable while allowing multiple governed graph
families to evolve on top of it.

## Why Profiles Matter

SpecGraph should be able to govern:

- its own self-specs
- product specs authored within the same environment
- later implementation-facing or handoff artifacts

These domains should not all fork the transition engine.

They should share:

- the same transition grammar
- the same provenance logic
- the same authorization model

while differing in profile rules.

That is what makes SpecGraph reusable as a meta-spec and not only as a
bootstrap self-documentation repository.

## Product-Spec Implication

This proposal explicitly supports the future case where SpecGraph governs
product-spec graphs developed inside the same environment.

In that world:

- product ideas may begin as drafts
- become proposals
- become product specs
- hand off into code or implementation overlays

The project should not have to write a brand-new transition philosophy for each
new product graph.

Instead, product graphs should inherit:

- deterministic packet validation
- provenance checks
- authority checks
- boundedness checks

and then layer product-specific rules through profile validators.

## CLI and Script Implication

This proposal implies a future script surface, not necessarily one exact
command name yet.

Representative future commands might validate:

- packet schema
- transition legality
- profile-specific rules
- resulting diff scope

The important part is not the exact CLI syntax.

The important part is that transition checking becomes:

- deterministic
- explainable
- repeatable
- automatable in CI or local workflows

## Failure Reporting

Deterministic transition checks should fail with structured findings rather
than only ad hoc error strings.

At minimum, failure reporting should distinguish:

- malformed packet
- forbidden transition
- missing provenance
- authority violation
- boundedness violation
- reconciliation failure
- profile-specific failure

This aligns naturally with the existing direction toward typed validation
findings.

## Adoption Order

The natural rollout order is:

1. Define packet families and transition semantics.
2. Define core check families and failure classes.
3. Implement a core validator.
4. Implement the first profile validator for `specgraph_core`.
5. Extend the system to product-spec profiles.
6. Only later let supervisor or other tools rely on the engine for automated
   transition gating.

This order matters because the semantics should be governed before the runtime
starts depending on them.

## Why This Is Useful

The strongest value in this proposal is not "add more validation."

The strongest value is:

- making artifact evolution governable
- separating legal transition checks from semantic judgment
- turning promotion and apply steps into explicit, inspectable transitions
- enabling SpecGraph to govern not only itself but later product-spec graphs
- giving the project a reusable deterministic backbone for artifact movement

This is the missing layer between "we have documents and scripts" and "we have
a governed artifact system."

## Open Questions

- Which packet families are truly minimal for the first useful rollout?
- Should transition packets live as files, derived records, or both?
- How strict should boundedness checks be before they become a usability
  burden?
- Which invariants belong in the core validator, and which belong only in
  profiles?
- How should profile versioning work when product-spec families evolve?
- At what point should supervisor rely on transition validation instead of
  bespoke runtime checks?
