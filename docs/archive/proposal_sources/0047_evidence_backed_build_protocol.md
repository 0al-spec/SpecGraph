# Evidence-Backed Build Protocol Source Draft

## Source Class

Working draft.

## Historical Concern

SpecGraph needed to distinguish raw local `runs/` noise from curated evidence
packets and to define a build protocol that carries mature specs toward
implementation work, tests, runtime evidence, and graph feedback without
committing all run artifacts or jumping directly from spec to code.

## Promotion Note

This archived source preserves the draft concern that was normalized into
`docs/proposals/0047_evidence_backed_build_protocol.md`.


## Zeusus pilot follow-up — 2026-09-28

The product owner asked that durable tracing requirements originate in formal
SpecGraph orchestration and reach Zeusus through implementation tasks. Inspection
identified proposal 0047 Slice 4 as the existing owner; no duplicate proposal ID
was allocated. The pilot already had a bounded in-memory trace sink before this
request. Preserve that chronology. The first realization projects explicit-node
observability obligations into a reviewable contract pack; it does not infer
requirements from implementation or introduce a Feature Passport dependency on
SpecGraph. Inherited principles and automatic task dispatch remain future work.
