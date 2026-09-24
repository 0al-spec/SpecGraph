# Source: canonical Decision nodes in product workspaces

Captured from the Zeusus decision-ledger discussion on 2026-09-23/24. The
operator asked whether SpecGraph's Decision node could be used to keep an
architectural decision ledger, then authorized a bounded proposal to check and
address the integration gap before returning to Zeusus engine work.

## Evidence gathered

- SpecGraph documents a canonical node envelope and `metadata.type: decision`
  in `docs/schema/node-format.md` (`Kind: decision`).
- Zeusus's product-workspace pilot currently records three accepted decisions
  as entries inside a project `kind: spec` node.
- The current SpecGraph YAML lint contract requires project-spec timestamp fields
  `created_at` / `updated_at`. A canonical Decision fixture with
  `metadata.createdAt` / `metadata.updatedAt` fails those checks.
- The current Supervisor `SpecNode` reads `id` and `title` from top-level keys;
  the canonical format nests them under `metadata`, so the fixture has no
  selectable Supervisor identity.

This is implementation evidence for the current checkout, not a claim that the
canonical Decision schema is absent. The operator requested that the proposal
cover a narrow bridge and validation path, without changing SpecGraph core in
this proposal-authoring task.

## Follow-up clarification on 2026-09-24

The operator clarified that Zeusus's embedded project-spec ledger and reliance
on ADRs and constitution as the detailed authority are a forced workaround for
the missing product-workspace Decision path, not an intended permanent
SpecGraph authority model. Decision was already present in SG-SPEC-0001's seed
ontology. The proposal should preserve that ontology, treat the Zeusus pilot as
evidence of an implementation gap, and avoid turning a product-specific
workaround into a general rule. Any move from existing Zeusus sources to a
canonical Decision record needs an explicit owner-approved authority and
migration contract; parsing alone cannot make that move.
