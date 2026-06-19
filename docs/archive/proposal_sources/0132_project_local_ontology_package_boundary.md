# Project-Local Ontology Package Boundary Source Draft

Ontology PR #57 can remain in the Ontology repository as an example or fixture
seed. It should not establish a pattern where every future product ontology is
stored in the shared Ontology repository.

The intended boundary is:

- Ontology repository: compiler, schemas, stdlib primitives, package format,
  validation utilities, and examples.
- SpecGraph project/workspace: project-local ontology packages, domain
  vocabulary, accepted local terms, candidate terms, relations, gaps, and
  package evidence.
- SpecSpace: read-only review UI for package metadata, normalized IR, gaps,
  diffs, evidence, and decisions.

SpecGraph agents should use Ontology tooling and package semantics, but
product ontology data should live beside the graph unless deliberately promoted
to a shared upstream ontology package.

The first corrective slice should move the SpecGraph Core working ontology
package from `tests/fixtures/ontology_import/specgraph-core` into
`ontology/packages/specgraph-core`, update the import policy and public artifact
handoff paths, and keep test fixtures as fixtures only.

The existing SpecGraph corpus already contains roughly seventy canonical spec
nodes. Those specs should not be bulk-rewritten merely because the ontology
layer arrived later. Treat them as a legacy corpus: derive observed terms,
produce binding and gap reports, and backfill accepted ontology bindings by
bounded context over time. New generated specs and proposals can adopt the
ontology-aware authoring contract first, while old specs remain canonical until
explicitly changed by ordinary SpecGraph review.
