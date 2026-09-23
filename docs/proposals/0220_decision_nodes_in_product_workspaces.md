# 0220 Canonical Decision Nodes in Product Workspaces

## Status

Draft proposal. Runtime realization is deferred until the contract is
canonicalized and scheduled. This proposal records an integration gap; it does
not add Decision nodes to Zeusus or change SpecGraph tooling.

## Source Material

- [Discussion and inspection evidence](../archive/proposal_sources/0220_decision_nodes_in_product_workspaces.md)
- [Canonical Node format](../schema/node-format.md), especially “Kind: decision”
- [Product Workspace stable-mode guide](../product_workspace_stable_mode_guide.md)
- Zeusus pilot: `docs/evidence/specgraph-decision-ledger-pilot.md` in the Zeusus repository

## Problem

SpecGraph documents a canonical Node envelope with `metadata.type: decision`,
but its current `product_workspace` authoring and Supervisor path consumes the
older project-spec envelope (`id`, `title`, `kind`, `created_at`, and
`updated_at` at the top level). A canonical Decision document therefore fails
the project-spec timestamp linter and has no top-level identity for targeted
Supervisor operations. Keeping decisions embedded in a project spec works as a
traceability pilot, but does not exercise the documented Decision node format.

## Proposed Contract

Define a narrow interoperability contract for canonical Decision nodes in a
product workspace:

1. The workspace loader, formatter/linter and graph index recognize the
   canonical Node envelope for `metadata.type: decision` without confusing it
   with a legacy project-spec record.
2. Canonical identity comes from `metadata.id` and `metadata.key`; display name,
   status and revision come from their documented `metadata` fields. A targeted
   operation resolves the canonical key deterministically and reports unknown
   or duplicate identities before executor launch.
3. Decision payload validation requires the documented `statement` and
   `rationale`; optional alternatives remain optional and are never synthesized
   from missing historical discussion.
4. Provenance and lifecycle fields retain the canonical schema's authority and
   source semantics. ADRs and project constitution remain authoritative for
   detailed rules unless a separate accepted change explicitly transfers that
   authority.
5. The compatibility boundary is explicit: project-spec records remain valid
   for their existing product-workspace use, and no silent rewrite or inferred
   migration occurs.

The exact operation surface (read-only cataloging versus Decision-node
refinement) must be canonicalized before implementation. A Decision record must
not be sent through ordinary spec refinement unless its contract explicitly
permits that lifecycle.

## Zeusus Acceptance Pilot

After the bridge exists, migrate or mirror Zeusus's three already accepted
records as canonical Decision nodes and demonstrate that the workspace can
load, validate, index and address them. Preserve `ZEU-DEC-0001` through
`ZEU-DEC-0003` as stable project-facing identifiers with an explicit mapping
to canonical machine identity; do not invent alternatives or change the
accepted rules. The ledger remains subordinate to the Zeusus ADRs and
constitution.

## Acceptance Criteria

- A valid canonical Decision node passes a dedicated schema-aware validator
  without requiring legacy top-level project-spec timestamps.
- Missing required decision fields, duplicate canonical keys, invalid lifecycle
  values and malformed provenance fail with actionable diagnostics.
- Existing project-spec fixtures retain their current parsing and validation
  behavior.
- Supervisor indexing can discover canonical Decision identity without silently
  treating it as an ordinary `kind: spec` node.
- Target resolution is deterministic and rejects duplicate or unknown keys
  before starting an executor.
- The Zeusus pilot can be represented and queried through the canonical format
  while retaining source links, authority, status, review trigger, unknown
  historical alternatives and the three stable `ZEU-DEC` references.
- Tests distinguish parser/validator evidence from an actual targeted workflow
  observation.

## Bounded Scope

In scope: one canonical Decision kind in product-workspace parsing,
schema-aware validation, identity indexing, target resolution and the Zeusus
acceptance fixture.

Out of scope: redefining the canonical Node schema, importing every canonical
node kind, changing ontology or approval policy, making a Decision node
automatically authoritative, editing Zeusus gameplay, generating historical
alternatives, immutable event-store semantics, or changing unrelated
Supervisor workflows.

## Authority and Review Boundary

This proposal does not authorize ontology or policy mutation, direct canonical
SpecGraph changes, automated acceptance of decisions, or executor authority
expansion. Any lifecycle or governance change discovered during canonicalization
must be split into a separately reviewed proposal. Implementation must preserve
legacy project-spec behavior and establish a failing validation/selection
scenario before code changes.

## Tracking

Runtime realization is deferred in this slice. The promotion registry links the
source discussion to this proposal; the runtime registry records that only the
proposal and source evidence currently exist. The tracking gate and generated
proposal trace are validation surfaces, not evidence that Decision-node support
has been implemented.
