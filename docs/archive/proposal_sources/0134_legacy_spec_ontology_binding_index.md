# Legacy Spec Ontology Binding Index Source Draft

SpecGraph has roughly seventy canonical specs that predate the curated
project-local ontology package. Those specs must not be bulk-rewritten merely
to satisfy a new ontology layer.

The next bounded slice should build a report-only binding index over existing
`specs/nodes/*.yaml`. The index should map obvious structural facts, such as a
spec node, acceptance criteria, and acceptance evidence, to current ontology
refs. Existing terminology that does not match accepted ontology entities should
be emitted as reviewable gaps instead of treated as accepted terms.

This artifact is evidence for later validation and SpecSpace review surfaces.
It must not mutate canonical specs, accept terms, write lockfiles, or block
legacy specs.

