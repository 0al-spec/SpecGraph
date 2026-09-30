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


## Evidence admission follow-up — 2026-09-28

The owner clarified that implementation/runtime claims must require deterministic
formal evidence through Feature Passport. Source inspection found a working
upstream pinned-source resolver but no runtime receipt evaluator. The first
realization therefore gates source identity, reserves declaration-only claims,
and fails closed for unsupported runtime/test/effect/outcome evidence. Spec
maturity and implementation proof remain separate; no graph status is promoted.


## Cross-repository ownership follow-up — 2026-09-30

The owner approved preparing a proposal amendment after asking where the missing
issuer and trust inputs should live in the multi-repository project. This source
records authorization to prepare the proposal, not adoption of trust policy or
permission to issue evidence. The requested ownership split is: Zeusus owns game
instrumentation and product intent; SpecificationCore owns generic evaluation
and tracing; FeaturePassport owns provider-neutral receipt issuance contracts and
shared implementation; SpecGraph proposal 0047 owns orchestration, mapping and
admission; SpecSpace presents the results; an explicit runner/CI deployment owns
operated authority configuration and signer custody.

The pilot already captured route/no-path calculations with six matched_untrusted
observations and four resolved source anchors at Zeusus commit 28b3710. Retain
that chronology and unsigned evidence. A signature of an old observation cannot
retroactively prove controlled execution. The proposed first local receipt scope
is acceptance of exact contract-matched bytes, not production or game outcomes.
Receipt policy, claim policy, admission policy and verifier trust stores are
separate responsibilities. No new repository, key, trust adoption, canonical
claim mapping or runtime issuer is created by this documentation amendment.
