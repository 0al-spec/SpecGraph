# Ontology Delta Candidate Review Packet

## Source Intent

The `0105` semantic lint report can identify candidate ontology delta terms, but
those candidates still need an explicit review packet before any Ontology owner,
SpecSpace surface, or supervisor gate can act on them.

The next bounded slice should package candidates and review actions without
writing Ontology packages, lockfiles, or SpecGraph canonical specs.

## Requested Work

- Build `ontology_delta_candidate_review_packet` from the `0105` lint report.
- Include candidate identity, missing concept metadata, proposed draft delta,
  source lint action, and explicit review actions.
- Preserve review-only authority: approval routes a candidate to Ontology owner
  package drafting, but this artifact itself performs no writes.
- Keep the output deterministic and local under `runs/`.

## Follow-Up Shape

The following slice should expose the semantic review surface boundary for
SpecSpace and supervisor gate consumers, still without adding mutation UI.
