# RFC 0221 canonical contract approval packet

## Status

Human approved the bounded semantic contract in the current Codex conversation
on 2026-10-02 with the message “Одобряю”, after delivery of PR #747 at head
`9be7e294c52c0ae1fac40f61ac285fd1ee8e3fc6`. This is the actual approval source,
not a GitHub review submitted on behalf of the human.

[SG-SPEC-0068](../../specs/nodes/SG-SPEC-0068.yaml) now records
`human_approved_pending_merge`, `status: specified`, and the decision provenance.
Its previous state was pending human approval. The approval gate is cleared
only after recording that decision. Neither lifecycle status nor semantic
approval establishes runtime readiness; `runtime_conformance` is `not_implemented`.
Merge, implementation, storage and migration authorization remain separate.

## Review corrections recorded with approval

- Pending contracts use `review_pending`; a read-only operational check confirmed
  this node appeared in both the review queue and pending gate actions before
  the human decision was recorded and resolved.
- Exact content selection returns revision-specific content and containment,
  plus explicitly labelled current_subject_disposition with observed event or
  origin and observation provenance. This current projection may change after
  withdrawal without changing historical content. An as-of disposition contract
  is deferred rather than guessed from a content revision.
- Promotion scope now names the bounded SG-SPEC-0068 child preparation and
  semantic approval instead of forbidding the canonical artifact it tracks.

## Approved semantic scope

| Concern | Bounded semantic contract |
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

## Approval and remaining delivery steps

1. Human semantic approval is recorded in this packet and the node, with the
   reviewed commit, exact source quote and recorded timestamp.
2. Proposal tracking reflects the approved semantic slice with runtime follow-up
   still unimplemented. The frozen parent and earlier run evidence are unchanged.
3. Merge remains a separate action after user authorization and final-head checks.
4. The next proposed task is read-only typed parsing/validation over fixtures.
   Source migration, writer changes and physical schema decisions remain deferred.

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
