# Source Draft: Ontology Owner Decision Import v2

Origin: operator request for the next ontology adoption slice after
`0138_ontology_gap_review_workflow`.

Intent:

- wire owner accepted/rejected decisions into a richer SpecGraph/SpecSpace review
  dashboard;
- connect decisions to closed-loop evidence, gap groups, compliance findings, and
  write-gate findings;
- show affected review items and before/after semantic status;
- make clean static artifact publishing generate the v2 review artifact before
  public-unsafe owner-decision surfaces are replaced with tombstones;
- keep the action boundary read-only/acknowledgement-only.

Non-goals:

- no ontology package writes;
- no ontology lockfile writes;
- no canonical spec mutation;
- no prompt-agent execution;
- no automatic import of owner decisions into SpecGraph authority;
- no semantic-gate closure;
- no SpecSpace mutation UI.
