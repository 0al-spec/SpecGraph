# Compare explicit ontology declarations across two specifications

RFC SG-RFC-0238

The [GitView observation](../archive/proposal_sources/0238_ontology_ref_diff.md)
shows a loss of machine-readable declarations at the draft-to-node handoff.
This slice exercises the expected-inventory idea from
[0233](0233_mechanical_specification_authoring.md) with two explicit inputs.
SG-SPEC-0009 anchors operator selection.

```sh
specgraph-runtime --workspace /path/to/project ontology-ref-diff -- \
  docs/drafts/PRODUCT-SPEC-0001.yaml specs/nodes/PRODUCT-SPEC-0001.yaml
```

Select two workspace-relative YAML paths. Both documents may have the same ID.
Read each document once and report its path, ID and SHA-256.
Use the `specgraph-explicit-terms-v1` reader for terminology keys and both
`ontology_refs` lists. Each occurrence retains its field path and YAML location.
Group occurrences by exact spelling and report terms in `retained`, `added`
and `removed`. A moved or repeated declaration keeps its occurrence locations
on both sides. A renamed term appears as a removal and an addition.

`--explain-removal TERM REASON` may be repeated for distinct removed terms.
The resulting `removal_explanation` records author rationale. The
`specgraph_ontology_ref_diff` version 1 report is read-only and exits 0
after a completed comparison, including when declarations disappear.
Malformed inputs or invalid explanations exit 2. Ontology resolution and
the decision to accept a removal belong to their existing review steps.

Verify against the GitView root pair and test retained declarations that move
between fields, added terms, intentional removals, a successor with an empty
inventory and invalid inputs.
