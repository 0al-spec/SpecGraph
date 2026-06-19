# Project-Local Ontology Authoring Commands Source Draft

SpecGraph now stores its working ontology package under
`ontology/packages/specgraph-core`, but operators still need stable commands for
reviewing that package without editing YAML by hand and without accidentally
granting canonical mutation authority.

The first implementation slice should add three review-only commands:

- validate the current project-local ontology package and adapter evidence;
- preview resolved refs, unresolved refs, and compatibility diff summary;
- preview gaps that require owner or operator review.

The commands should write typed artifacts under `runs/`, preserve the 0132
boundary, and explicitly reject canonical spec mutation, ontology lockfile
updates, accepted-term decisions, prompt-agent execution, and SpecSpace writes.

This source draft also fixes the five-PR plan for ontology-backed spec
validation: authoring commands, legacy binding index, validation report,
SpecSpace compliance surface, and SpecAuthor write gate.

