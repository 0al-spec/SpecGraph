# 0220 Canonical Decision Nodes in Product Workspaces

## Status

Draft proposal. The contract is canonicalized, and its initial runtime slice is
being implemented. This proposal records a gap between the existing SpecGraph
ontology and the current product-workspace implementation. It does not change
the ontology or Zeusus decision authority.

The initial slice adds a standalone, read-only index over canonical Decision
nodes under a product workspace `specs_root`. It validates Decision envelopes,
indexes `metadata.id` and `metadata.key` independently, and supports lookup.
It does not connect Decisions to ordinary Supervisor refinement or executor
selection. Full project-workspace integration and the Zeusus compatibility
pilot remain follow-up work.

## Source Material

- [Discussion and inspection evidence](../archive/proposal_sources/0220_decision_nodes_in_product_workspaces.md)
- [SG-SPEC-0001](../../specs/nodes/SG-SPEC-0001.yaml): Decision is an existing
  Specification-layer node kind; canonical records are user-owned and portable.
- [Canonical Node format](../schema/node-format.md), especially “Kind: decision”
- [Product Workspace stable-mode guide](../product_workspace_stable_mode_guide.md)
- Zeusus pilot: `docs/evidence/specgraph-decision-ledger-pilot.md` in the Zeusus repository

## Problem

Decision is already a seed node kind in SpecGraph. The product-workspace
Supervisor currently operates on a flat project-spec envelope (`id`, `title`,
`kind`, `created_at`, and `updated_at` at the top level), while the documented
canonical Node envelope places identity and timestamps under `metadata`. A
canonical Decision document fails the project-spec timestamp linter and has no
top-level identity for Supervisor selection. The current implementation gap
must not be mistaken for a request to add Decision to the ontology.

Zeusus temporarily records three accepted decisions inside a project `kind:
spec` node and retains its ADRs and constitution as the detailed project
contracts. This is an implementation workaround while canonical Decision nodes
cannot be used in that workspace. It is not a proposed permanent hierarchy in
which a canonical SpecGraph Decision is subordinate to a second decision
ledger. The workaround demonstrates traceability, not canonical Decision-node
support or a reason to change SpecGraph governance for one product.

## Intended Authority Boundary

The target follows the existing SpecGraph model: a Decision node is a
user-owned canonical record in the project graph, traceable to intent and
connected through the governed edge and lifecycle contracts. Whether that
record carries an adopted product rule requires a separate, explicit project
authority contract. A source ADR or constitution section can supply provenance
or a human-readable expression of a rule. A graph record and a source document
must not become competing authorities through an implicit import or copy.

For Zeusus, the existing ADRs and constitution retain their current authority
until the project owner explicitly accepts an authority transition. Merely
loading or indexing a Decision node does not enact that transition. A future
transition must state which accepted rule is canonical, how source documents
relate to it, how conflicts are detected, and how subsequent changes and
supersession are governed. This proposal does not perform or authorize that
transition.

The following terms must remain distinct:

- `metadata.status` is a SpecGraph node lifecycle value; it is not automatically
  Zeusus's `adopted` decision state.
- `provenance.authority` / `authority_class` describes record provenance; it
  does not itself grant authority to adopt a product rule.
- An embedded `spec.decisions` entry, an operator approval, and an ontology
  review decision are not automatically canonical Decision nodes.

## Proposed Contract

Canonicalize the authority and operation boundary before implementing a
Decision-specific adapter:

1. Define how a product workspace recognizes the existing canonical Decision
   kind while preserving legacy project-spec records. Resolve the documented
   Node envelope versus flat runtime representation explicitly; do not make a
   Decision-only format exception appear to solve that broader gap.
2. Validate the documented Decision payload (`statement` and `rationale`),
   identity, lifecycle, and provenance without requiring legacy top-level
   project-spec timestamps. Missing historical alternatives remain unknown;
   the optional `alternativesConsidered` field is never synthesized.
3. Index `metadata.id` and `metadata.key` separately from legacy spec IDs.
   Reject duplicate or unknown keys deterministically. Expose read-only lookup
   first; a Decision must not enter ordinary spec refinement or an executor
   merely because it is indexed.
4. Specify an explicit owner-approved migration or linking contract before
   promoting an external decision ledger to canonical graph authority. Preserve
   the previous sources and stable project-facing references, and report
   disagreement instead of silently selecting one version of a rule.
5. Keep the implementation slice bounded to Decision recognition, validation,
   indexing, and read-only addressing. Decision authoring, adoption, refinement,
   approval, and authority transfer require their own reviewed lifecycle
   contract before any executor is enabled.

## Zeusus Acceptance Pilot

Use `ZEU-DEC-0001` through `ZEU-DEC-0003` as a compatibility fixture for the
three existing records. Demonstrate that their statements, rationales, source
links, and stable project-facing references can be represented and queried
without inventing alternatives or changing accepted project rules. Keep an
explicit mapping between each project-facing reference, canonical key, and
immutable machine ID.

The existing ledger also carries `adopted`, decision authority, consequences,
review triggers, and an explicit unknown-history marker. The current canonical
Decision payload does not define all of these fields. Before any migration,
decide which information belongs in a governed graph contract, an explicit
relation, or linked source evidence. The pilot fails if these distinctions are
lost or if `reviewed`, `authored`, or an imported file is presented as proof of
product-rule adoption. Until that mapping and owner acceptance exist, Zeusus
continues to use its present ledger and source documents.

## Initial Runtime Slice

- A product workspace can point the read-only indexer at its `specs_root`.
- Canonical Decision nodes are validated independently of legacy project-spec
  timestamp fields.
- Duplicate IDs and keys, invalid lifecycle values, malformed provenance, and
  unknown lookup identities fail deterministically with actionable diagnostics.
- Legacy project-spec files are excluded from Decision indexing and retain
  their existing parsing, validation, selection, and refinement behavior.
- The index is immutable and lookup has no write, adoption, or executor path.
- The initial slice is parser/index API and CLI evidence only; it does not prove
  owner-approved rule adoption or the Zeusus migration contract.

## Acceptance Criteria for Full Product-Workspace Integration

- A valid canonical Decision passes a dedicated schema-aware validator without
  legacy top-level project-spec timestamps.
- Missing required Decision fields, duplicate IDs or keys, invalid lifecycle
  values, and malformed provenance fail with actionable diagnostics.
- Existing project-spec fixtures retain their parsing, validation, selection,
  and refinement behavior.
- A read-only graph index discovers canonical Decision identity without
  treating it as `kind: spec` or scheduling ordinary spec refinement.
- Key lookup rejects duplicate or unknown identities before any executor path.
- The Zeusus fixture preserves source links and `ZEU-DEC` references; fields
  without a canonical mapping remain explicit unresolved migration items.
- Tests distinguish parser and validator evidence from a real product-workspace
  lookup observation and from any later owner-approved authority transition.

## Bounded Scope

In scope for this proposal: canonicalizing the authority boundary and defining
one Decision-kind product-workspace recognition, validation, indexing, lookup,
and compatibility pilot. Runtime realization proceeds in stages, beginning
with the standalone read-only index. Supervisor integration and the
compatibility pilot remain separate bounded follow-ups.

Out of scope: changing the seed ontology, importing every canonical kind,
automatically accepting or migrating Zeusus decisions, modifying Zeusus rules,
inventing historical alternatives, immutable event-store semantics, and
expanding Supervisor executor authority. Any needed schema, governance, or
Decision lifecycle change must be reviewed separately rather than hidden in an
adapter.

## Tracking

The promotion registry links the source discussion to this proposal. The
runtime registry records the initial index slice and remaining integration
scope. Proposal tracking and trace gates do not establish Decision adoption or
authority transfer.
