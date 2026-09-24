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

## Initial implementation direction on 2026-09-24

The operator authorized starting the proposal's initial runtime slice. Begin
with a standalone, read-only product-workspace index that validates canonical
Decision envelopes and supports separate lookup by immutable machine ID and
stable key. Keep ordinary project-spec parsing and Supervisor refinement
unchanged. Do not enable authoring, adoption, executor selection, or migration
of the Zeusus ledger in this slice.

## Zeusus pilot snapshot pin on 2026-09-24

The referenced pilot evidence is pinned to Zeusus commit
`bc425a7295be2bf5b6b58b8a770047a441019e93`; the file
`docs/evidence/specgraph-decision-ledger-pilot.md` at that commit has SHA-256
`710bc7bdc9a82c9c868252bf968a9f6cc7069b3140f286cb092665fea34710b7`.
