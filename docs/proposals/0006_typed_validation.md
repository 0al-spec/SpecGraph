# Typed Validation, Structured Findings, and Safe Repair

## Status

Draft proposal

## Problem

SpecGraph already relies on several forms of validation:

- YAML and formatting checks
- acceptance/evidence alignment
- relation semantics
- graph reconciliation rules
- mutation-budget and refinement-acceptance checks

These checks are useful, but today they are still too heterogeneous.

In practice, the runtime often handles validation as a mix of:

- raw YAML loading
- ad hoc Python checks
- string-based validation errors
- post-hoc operator interpretation

This creates three problems.

### 1. Weak Structural Contracts

The system has no single strongly typed contract for important runtime
artifacts such as:

- spec nodes
- proposal artifacts
- run payloads
- context packs
- validation findings

This makes it harder to distinguish:

- malformed structure
- valid structure with semantic violations
- graph-level inconsistency

### 2. Validation Without Repair Semantics

Today, a refinement run can produce a useful bounded draft and still fail
because a validator finds a local inconsistency in that same file.

Example:

- a node already `refines` another node
- the same target is redundantly listed in `relates_to`
- the refinement itself is useful
- the whole run is rejected because the final file remains locally invalid

The system currently has almost no formal way to say:

- this finding is real
- this finding is local
- this finding is safe to repair immediately

### 3. No Clear Split Between Schema, Semantics, and Graph Logic

Not all validation is the same kind of validation.

Some rules are about shape:

- required fields exist
- enum values are valid
- lists are non-empty

Some rules are about local semantics:

- `acceptance` and `acceptance_evidence` remain aligned
- `refines` must not be weakened by redundant `relates_to`
- proposal apply-state is not confused with proposal review-state

Some rules are graph-wide:

- missing dependency targets
- lineage inconsistency
- duplicate concepts
- ontology drift and synonym collisions

Without an explicit layered model, the validator surface becomes difficult to
extend and difficult to make more autonomous safely.

## Goals

- Define a layered validation architecture for SpecGraph.
- Introduce typed contracts for key runtime and graph-validation artifacts.
- Use schema validation as a first-class contract layer without pretending it
  solves all graph semantics.
- Make validation findings machine-readable and classifiable.
- Define a narrow class of safe validator-driven repairs.
- Support future context-pack, vocabulary, proposal-lane, and evaluator work
  with cleaner validation boundaries.

## Non-Goals

- Replacing all existing validators in one step
- Full formal logic or theorem proving
- Proving global semantic consistency for arbitrary free text
- A complete implementation of all typed validators now
- Unlimited self-healing autonomous edits after failed validation

## Core Proposal

SpecGraph validation should be formalized as four layers:

1. Typed schema contracts
2. Local semantic validators
3. Graph validators
4. Safe validator-driven repair

These layers are complementary, not interchangeable.

## Layer 1: Typed Schema Contracts

This layer provides strict machine-readable structure for major artifacts.

Candidate artifacts:

- `SpecNodeModel`
- `ProposalArtifactModel`
- `RunPayloadModel`
- `ContextPackModel`
- `ValidationFindingModel`
- `RepairActionModel`

This is the natural place for tools such as Pydantic.

### Purpose

- validate required fields
- validate enums
- validate nested structure
- validate field types and simple invariants
- generate machine-readable schema
- normalize structured output from agents

### Why Pydantic Fits Here

Pydantic is well suited to:

- canonical field shape
- strict parsing
- cross-field invariants inside one object
- typed artifacts passed between runtime stages

If LLM output must be forced into a strict object contract, Instructor can be
used as a frontend adapter for this layer.

### Important Boundary

Pydantic and Instructor are not the whole validation system.

They are a strong front-end contract layer, not a complete engine for:

- graph-wide rules
- ontology reasoning
- duplicate concept detection
- lineage correctness

## Layer 2: Local Semantic Validators

This layer enforces deterministic rules inside one artifact after it is
structurally valid.

Examples:

- `acceptance` and `acceptance_evidence` remain 1:1
- `refines` and `relates_to` do not redundantly target the same spec
- proposal apply semantics do not collapse proposal review semantics
- application refusal is distinguished from review rejection

These rules may still operate on one typed object, but they are not merely
schema constraints. They express local meaning.

## Layer 3: Graph Validators

This layer checks consistency across multiple nodes and artifacts.

Examples:

- dependency targets exist
- cycles are disallowed or explicitly classified
- ancestor/child lineage remains traceable
- canonical terms are not silently duplicated
- aliases do not collide across contexts

This layer should consume typed artifacts where possible, but it remains a
separate graph engine rather than a field-schema concern.

## Layer 4: Safe Validator-Driven Repair

The system should support a narrow repair pass for findings that are:

- local
- deterministic
- semantics-preserving
- explicitly allowlisted

Examples of likely safe repairs:

- remove redundant `relates_to` when the same target already appears in
  `refines`
- restore canonical formatting
- repair purely structural acceptance/evidence alignment where the intended
  mapping is unambiguous

Examples that should remain outside safe repair:

- introducing or renaming ontology terms
- changing scope
- inventing aliases
- redefining relation meaning
- broadening dependencies or lineage across multiple nodes

### Safe Repair Model

The intended flow is:

1. agent produces one bounded draft
2. validators emit structured findings
3. runtime classifies findings
4. if every finding is allowlisted as safe-repairable, run one repair pass
5. revalidate
6. if still invalid, fail normally

This allows more autonomy without collapsing into unconstrained multi-pass
self-editing.

## Structured Validation Findings

Validation findings should become typed artifacts instead of plain strings.

A finding should minimally support:

- `finding_id`
- `layer`
- `severity`
- `artifact_kind`
- `artifact_ref`
- `path`
- `message`
- `repairability`
- `suggested_repair_kind`

Candidate repairability values:

- `none`
- `safe_local_repair`
- `manual_review`

Candidate layers:

- `schema`
- `local_semantics`
- `graph`
- `runtime_environment`

This makes findings usable for:

- runtime gating
- operator review
- evaluator loop quality signals
- future automated repair

## Relationship to Existing Work

### Vocabulary Layer

The vocabulary layer needs validators that can distinguish:

- canonical terms
- aliases
- undeclared terms
- suspicious synonym drift

Typed validation findings make this much easier to implement and reason about.

### Context Pack

The context-pack layer needs typed validation for:

- content classes
- authority ordering
- unresolved-term handling
- duplicate-candidate surfacing

### Proposal Lane

Proposal-lane semantics need typed validation around:

- proposal authority state
- repository presence
- application compatibility
- canonical application event

### Operator Request

Operator requests should eventually be typed artifacts rather than loose CLI
flag bundles.

### Runtime Hygiene

Runtime anomalies such as timeout-driven stale tails should remain clearly
separate from schema and semantic findings. A typed finding model helps enforce
that split.

## Pydantic and Instructor in This Architecture

This proposal recommends using Pydantic and optionally Instructor in a bounded,
explicit role.

### Recommended Uses

- define typed runtime and graph artifacts
- parse and validate structured LLM output
- enforce object-level invariants
- generate machine-readable schemas for tools and tests

### Not Recommended as Sole Mechanism

- global graph consistency
- ontology conflict detection
- semantic duplicate detection across the repository
- final authority on all validation logic

The correct model is:

- Pydantic as contract layer
- semantic validators as rule layer
- graph validators as topology/ontology layer
- safe repair as a constrained post-validation layer

## Suggested Initial Artifact Models

Useful first typed models would be:

- `SpecNodeModel`
- `ValidationFindingModel`
- `RefinementAcceptanceModel`
- `RunSummaryModel`
- `SplitProposalArtifactModel`

These would immediately improve the quality of:

- `supervisor` payload handling
- validation reporting
- runtime troubleshooting
- later evaluator metrics

## Suggested Next Spec Slices

- `Typed spec node contract`
- `Validation finding taxonomy`
- `Safe validator-driven repair policy`
- `Vocabulary-aware term validation`
- `Graph duplicate and alias collision detection`
