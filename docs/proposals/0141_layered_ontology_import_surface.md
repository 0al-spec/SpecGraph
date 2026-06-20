# 0141 Layered Ontology Import Surface

## Status

Implemented

## Source

- `docs/archive/proposal_sources/0141_layered_ontology_import_surface.md`

## Summary

Ontology now supports first-class semantic layers on ontology elements:
`objective`, `mechanics`, `execution`, `meta`, and `multi_agent`.

This proposal adds the first SpecGraph read-only consumer slice for that
metadata. When normalized IR entries contain a `layer` field, SpecGraph preserves
it on resolved refs and publishes a package-level `ontology_layer_summary` in
`runs/ontology_package_index.json`.

## Motivation

SpecGraph and SpecSpace need to distinguish different meanings of "ontology
support":

- `objective`: product/domain intent and goals;
- `mechanics`: deterministic model structure and relations;
- `execution`: runtime behavior, commands, checks, and enforcement;
- `meta`: specification/governance/process concepts;
- `multi_agent`: agent collaboration and invocation semantics.

Without a read-only import surface, downstream tools can only see flat classes
and relations. That blocks layer-aware gap reports, review dashboards, and
future SpecAuthorAgent write gates.

## Implementation

This slice updates `tools/ontology_imports.py`:

- `ontology_ref_map()` preserves `layer` on resolved refs when present;
- `ontology_layer_summary()` aggregates layer usage across normalized IR
  sections: classes, relations, policies, protocols, and state machines;
- each package entry includes `ontology_layer_summary`;
- `ontology_package_index.summary` includes layered/unlayered counts and used
  layer count.

The implementation is forward-compatible with current packages that do not yet
contain layer metadata: summaries report zero layered entries and keep all
existing import behavior read-only.

## Authority Boundary

This proposal does not make SpecGraph an ontology authority.

It does not:

- write ontology packages;
- update ontology lockfiles;
- mutate canonical specs;
- accept or reject ontology terms;
- infer missing layers for legacy specs;
- execute prompt agents;
- close semantic gates.

## Validation

- `tests/test_ontology_import_policy.py::test_ontology_import_surfaces_preserve_layered_normalized_ir`
  verifies layer preservation and package summary aggregation using a temporary
  normalized IR fixture.
- Existing SpecGraph Core import tests verify the zero-layer fallback for
  current fixtures.
- `make ontology-imports` continues to emit the declared read-only surfaces.

## Follow-ups

- Add layer-aware gap/diff report surfaces.
- Add a SpecSpace layer lens grouped by ontology layer.
- Extend SpecAuthorAgent write gates to require explicit layer context for
  strong ontology-bound claims.
