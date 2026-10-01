# RFC 0221 canonical contract approval packet

## Status

Status: pending human approval. This PR proposes [SG-SPEC-0068](../../specs/nodes/SG-SPEC-0068.yaml)
as one child refinement of frozen SG-SPEC-0019. Its `outlined` status records
preparation, not adoption, review completion or runtime readiness. No approval
receipt, supervisor gate decision or runtime conformance is fabricated.

The human authorized preparation of this diff. Review must explicitly approve,
amend, reject or defer the bounded contract before merge. Merely creating the
file, passing checks or producing the earlier supervisor candidate is not approval.

## Decision to review

| Concern | Proposed semantic contract |
| --- | --- |
| Identity | Immutable governed workspace identity plus unique local subject ID; class validates the record, not a second ID namespace |
| Criterion | Independently addressable subject associated with its Requirement through authored acceptance_criteria_refs; no new seed node kind |
| Revision | Positive integer starting at 1, immediate same-identity predecessor, atomic unique next revision and append-only history |
| Move | Preserve identity, advance revision by one, retain old containment; existing frozen-subject restrictions still apply |
| Replacement | Successor identity starts at revision 1; lineage alone changes neither participant disposition nor canonical topology |
| Disposition | Activation and withdrawal are explicit independent transitions; retired Requirements cannot satisfy dependencies but remain queryable |
| Relations | Separately authored same-class decomposes_into and composed_from with every full endpoint reference and directed role; no inferred inverse relation |
| Lookup | Explicit exact/current selection; exact lookup never redirects to latest, successor, matching text or another workspace |
| Ambiguity | Fail closed on identity collisions, conflicting revisions/definitions and ambiguous legacy evidence; distinguish declared replicas from independent forks |
| Compatibility | Existing IDs and legacy strings remain readable in their current scopes; mapping is reviewed, and reads never mint identities |

This child supplements addressing semantics without broadening the frozen
parent's revision_subject or one-to-one successor_mapping. Canonical node/edge
supersession remains the separate SG-SPEC-0019 event with a cross-identity
terminal predecessor reference. The successor's revision-1 origin remains
independent of that event.

## Deferred implementation decisions

Physical criterion/history storage, declaration file location, allocator and
reference token syntax, migration application, writer changes and removal of
legacy support require later bounded decisions. The earlier embedded form and
UUID declaration remain recommendations, not adopted serialization requirements.

After approval, the first implementation slice is read-only typed parsing and
validation over fixtures. It cannot allocate identities, mutate source records,
apply migration or claim complete runtime conformance.

## Recording approval

1. Human reviews this PR's exact contract diff and records explicit approval
   of SG-SPEC-0068 as the bounded RFC 0221 child; rejects or defers are valid.
2. In the same PR, record the actual approval reference and bounded scope,
   remove the pending adoption marker, and update proposal tracking to reflect
   only the approved semantic slice. Do not invent a receipt in advance.
3. Recheck YAML, graph linkage, parent immutability, spec evidence and tracking
   gates, then merge only after user authorization and final-head checks.
4. Open the separate read-model implementation PR. Schema and migration remain
   deferred; semantic approval is not authorization to rewrite existing data.

## Preparation evidence

- Started from main a40a6dffdce73be6c095224f4847c0b51a3b80dd.
- Collision checks cover all local/remote-ref node paths, worktree node paths,
  pending node references, run reservation registries and open PR metadata.
  The next unclaimed node ID was SG-SPEC-0068. A branch named
  codex/0068-specspace-handoff-contract-stabilization uses a proposal number;
  no SG-SPEC-0068 node or pending node reference was found there.
- No LLM refinement or supervisor approval was run for this authored contract.
- The earlier curated candidate and historical run evidence remain unchanged.
- Contract examples are semantic acceptance cases, not executable behavior proof.
