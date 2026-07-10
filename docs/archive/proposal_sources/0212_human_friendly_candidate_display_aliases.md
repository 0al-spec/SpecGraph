# 0212 Human-Friendly Candidate Display Aliases

## Source Draft

Generated candidate node ids are authoritative machine references but are too
long for Product Workspace, topology review, and promoted candidate documents.
Add one deterministic SpecGraph-owned presentation alias per candidate node.

The alias must remain distinct from ontology aliases and route aliases. It must
never replace canonical node ids, graph refs, materialized filenames, or
promotion paths. SpecSpace may render the alias, but must keep canonical refs
for navigation and managed operations.
