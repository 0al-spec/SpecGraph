# SpecGraph Core Ontology Package

This directory is the project-local ontology package root for SpecGraph.

## Project-Local Authority

The sibling Ontology repository provides ontology tooling, schemas, compiler
behavior, standard-library primitives, and examples. Product or project domain
ontology data should not be stored in the Ontology repository by default.

For SpecGraph itself, the working package source lives here:

```text
ontology/packages/specgraph-core/domain-ontology-package.yaml
```

Compiler outputs and adapter reports under this directory are tracked as
project-local package evidence. They remain reviewable artifacts; they do not
grant automatic permission to mutate `specs/nodes/*.yaml`, update an ontology
lockfile, or accept owner decisions without an explicit SpecGraph change.

## Package Layout

- `domain-ontology-package.yaml`: project-local package source.
- `generated/ontology.normalized.json`: normalized compiler IR consumed by
  SpecGraph and SpecSpace read-only surfaces.
- `generated/ontology.graph.json`: derived read-only visualization projection,
  generated from the 0.1.0 source with the pinned Ontology 0.8.0 `ontologyviz`
  (`--format json --view full`). It does not replace the normalized compiler IR.
- `ontologyc-adapter-report.yaml`: typed adapter evidence for the current
  compiler run.
- `ontologyc/`: non-canonical compiler outputs such as concept refs, gaps, and
  lockfile preview.
- `compatibility/`: compatibility preview inputs and reports.

Ontology PR #57 can remain useful as an upstream example or fixture seed, but
this directory is the SpecGraph-local package location used by runtime import
surfaces.

## Published 0.3.0 and pinned 0.1.0

The public Viewer projection is generated from the versioned draft
[`versions/0.3.0/domain-ontology-package.yaml`](versions/0.3.0/domain-ontology-package.yaml),
with its matching compiler IR and graph under `versions/0.3.0/generated/`. The
existing `generated/` paths continue to describe version 0.1.0. This adds the
four pre-spec concepts and six adjacencies selected for the first slice in the
[core candidate review](../../../docs/reviews/0232_project_ontology_context/core-candidate-comparison-20261108/README.md).
The operator subsequently requested publication in the conversation
("Нужно публиковать тогда"). The retained conversation is attribution, not a
signed identity or an independent timestamp.

`IntentDraft`, `IntentFragment`, `Hypothesis`, and `Proposal` stay distinct;
a relation is not an approval or a promotion. The existing `sgcore:Intent`
retains its governed-product meaning. A draft-to-intent edge represents a
possible provenance relation to that governed intent; it does not assert that
stabilizing a pre-canonical intent grants authority or produces one.

Existing semantic bindings, review evidence, historical URIs and the metamodel
check remain pinned to the unchanged `0.1.0` source and IR. Publication of
`0.3.0` does not update their lockfiles or apply their prior decisions to new
bytes. The draft `sgproposal` and `sgpromotion` packages keep their original
identities, version pins, source references and generated SDK behavior; the
new `sgcore` declarations are source-derived candidates, not automatic URI
aliases. The new core uses its existing `specgraph.foundation@0.1.0` (`sg`);
the source draft uses `ontology.foundation@0.2.0` (`ont`). Their names do not
establish foundation equivalence. Migration of their references and acceptance
of any equivalence remain separate work. The `0.2.0` claim-calibration compatibility fixture is
reserved for its existing test and is not this release.
