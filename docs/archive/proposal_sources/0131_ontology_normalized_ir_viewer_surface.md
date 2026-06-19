# Ontology Normalized IR Viewer Surface Source Draft

Operators need the next Ontology UI slice to move beyond raw JSON preview.
SpecGraph now publishes public-safe run artifacts and the normalized Ontology
compiler IR, and SpecSpace already has a generic artifact inspector. The next
slice should be a read-only UI surface that turns `ontology.normalized.json`
into a normal review panel.

The viewer should show:

- package metadata from `runs/ontology_package_index.json`;
- normalized compiler IR from the package `materialized_ir` path;
- classes/entities;
- relations;
- domains or namespaces when present;
- related gap and diff artifacts;
- evidence/source refs;
- raw artifact links back to the generic artifact inspector.

The surface is for inspection, demo, and review. It must not write Ontology
packages, mutate SpecGraph specs, accept or reject terms, import owner
decisions, close semantic gates, or hide that gaps/diffs remain review
evidence.

This work follows:

- `0127_ontology_stdlib_type_discipline`;
- `0128_ontology_term_binding_policy`;
- `0129_generated_term_binding_gate`;
- public bundle publishing of safe `runs/*.json` and normalized ontology IR.
