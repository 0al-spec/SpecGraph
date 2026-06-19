# Project-Local Ontology Package Boundary

RFC: SG-RFC-0132
Version: 0.1.0

## Status

Draft proposal

Decision scope: define and implement the first project-local ontology package
storage boundary for SpecGraph.

## Source Material

Source draft:

- `docs/archive/proposal_sources/0132_project_local_ontology_package_boundary.md`

Related proposal context:

- `0060_external_ontology_import_plane`
- `0100_ontology_grounded_semantic_control`
- `0119_ontology_canonicalization_backlog`
- `0127_ontology_stdlib_type_discipline`
- `0128_ontology_term_binding_policy`
- `0131_ontology_normalized_ir_viewer_surface`

## Problem

The current compiler-backed SpecGraph Core ontology path was bootstrapped from
an Ontology repository package fixture. That proved the import and viewer
pipeline, but it also implies the wrong long-term product model: the shared
Ontology repository could become a repository of every product ontology built
with SpecGraph and SpecSpace.

That is not the desired boundary.

The Ontology repository should provide the compiler, schemas, stdlib
primitives, package format, validation utilities, and examples. Product and
project ontology data should live beside the owning graph, where review,
evidence, candidate terms, and domain vocabulary are scoped to that project.

## Proposal

Introduce `ontology/packages/` as the project-local ontology package root for
SpecGraph.

The first package is:

```text
ontology/packages/specgraph-core/
```

It contains:

- `domain-ontology-package.yaml`;
- `generated/ontology.normalized.json`;
- `import-fixture.yaml`;
- `ontologyc-adapter-report.yaml`;
- non-canonical `ontologyc/` output previews;
- compatibility preview inputs and reports.

`tools/ontology_import_policy.json` should use this project-local package as
its default SpecGraph Core source. The old `tests/fixtures/ontology_import`
tree remains test-only fixture material and must not be the default runtime
source.

## Authority Boundary

The Ontology repository may be used for:

- compiler behavior;
- schemas;
- stdlib primitive definitions;
- package format;
- validation utilities;
- examples and fixtures.

SpecGraph project-local packages are used for:

- project vocabulary;
- bounded context terms;
- project/domain relations;
- candidate and accepted local package data;
- compiler outputs consumed by SpecGraph/SpecSpace surfaces.

This proposal does not allow:

- automatic writes to `specs/nodes/*.yaml`;
- canonical `specs/imports/ontology.lock.yaml` adoption;
- SpecSpace mutation UI;
- prompt-agent execution;
- owner-decision import as a mutation;
- promotion of project packages into the Ontology repository.

## Existing Graph Adoption

SpecGraph already has a large canonical spec corpus that predates the ontology
layer. This proposal treats that corpus as legacy input, not as invalid data.

The adoption sequence is:

- keep existing `specs/nodes/*.yaml` canonical and unchanged by default;
- derive observed terminology from existing specs as non-authoritative evidence;
- bind observed terms to accepted ontology entities where the mapping is clear;
- emit ontology gaps where a term is useful but not yet accepted;
- record diffs and conflicts for human review instead of rewriting specs;
- apply ontology-aware authoring and term-binding rules to new proposals first;
- backfill old specs only through bounded, reviewed slices.

This preserves the current graph while allowing the ontology to narrow future
semantic drift. The ontology is therefore a stabilizing layer over the existing
graph before it becomes a stronger write gate for new generated artifacts.

## Implemented Slice

This slice:

- creates `ontology/packages/specgraph-core/`;
- switches the default import policy from `tests/fixtures/...` to the
  project-local package;
- marks the package as `project_local_draft`;
- changes public materialized IR publication to
  `ontology/packages/specgraph-core/generated/ontology.normalized.json`;
- updates the SpecSpace external consumer handoff artifact contract;
- adds regression coverage that the default package source is project-local.

## Acceptance

This contract slice is complete when:

- proposal `0132` has source draft provenance;
- `tools/ontology_import_policy.json` points default SpecGraph Core imports at
  `ontology/packages/specgraph-core/import-fixture.yaml`;
- `runs/ontology_package_index.json` publishes a materialized IR path under
  `ontology/packages/`, not under `tests/fixtures/`;
- the SpecSpace external consumer handoff lists the project-local materialized
  IR path;
- tests assert the default package source is project-local;
- proposal tracking gates pass.

## Next Gap

```text
project_local_ontology_authoring_commands
```

Future slices can add explicit authoring commands for candidate term creation,
package edits, ontologyc invocation, and owner review. Those commands should
still produce typed artifacts first and avoid direct mutation of canonical specs.
