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
- `ontologyc-adapter-report.yaml`: typed adapter evidence for the current
  compiler run.
- `ontologyc/`: non-canonical compiler outputs such as concept refs, gaps, and
  lockfile preview.
- `compatibility/`: compatibility preview inputs and reports.

Ontology PR #57 can remain useful as an upstream example or fixture seed, but
this directory is the SpecGraph-local package location used by runtime import
surfaces.
