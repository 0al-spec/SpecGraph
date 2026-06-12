# Ontology-Grounded Semantic Control

## Source Intent

The operator clarified that Ontology support in SpecGraph and SpecSpace is not
only an external import or read-only consumer line.

SpecGraph, including agents operating under the supervisor, and the SpecSpace
shell assistant should be able to generate and extend ontologies as reviewable
work. The purpose is to fix the accepted vocabulary, domain boundaries, and
relations that agents should use when producing specs, proposals, and review
surfaces.

The desired product effect is fewer hallucinations, fewer misunderstandings,
and fewer cases where an assistant uses a term that conflicts with already
accepted domain language.

## Existing Context To Preserve

- `0060_external_ontology_import_plane` already defines the read-only import
  boundary for external Ontology packages, concept refs, gaps, governance
  evidence, and binding previews.
- `docs/ontologyc_adapter_report_contract.md` already defines the
  `ontologyc validate-specgraph` adapter report boundary.
- `0062_proto_graph_recursive_refinement` already uses ontology-backed seed
  concepts for proto-graph generation without granting generated scaffolds
  canonical authority.
- `0011_pre_spec_semantic_layer` already keeps user intent and assistant
  synthesis reviewable before canonical promotion.

## Requested Normalization

Add a proposal that makes Ontology a semantic control layer for graph-facing
agents:

- Before generation, agents should receive an accepted vocabulary and relation
  context derived from imported or product-local ontology packages.
- During generation, unknown, ambiguous, deprecated, or out-of-domain terms
  should be classified instead of silently normalized or invented.
- After generation, outputs should be linted against accepted ontology
  concepts, aliases, domain boundaries, and relations.
- Missing concepts should become `OntologyGap`, `ClarificationQuestion`, or
  `OntologyDeltaCandidate` artifacts.
- Ontology deltas produced by agents must remain reviewable candidates until
  accepted by Ontology governance and SpecGraph proposal review.

## Out Of Scope

- Auto-importing ontology locks.
- Auto-mutating `specs/nodes/*.yaml`.
- Executing prompt packs inside the supervisor.
- Writing SpecSpace mutation UI.
- Redefining Ontology package schema in SpecGraph.
