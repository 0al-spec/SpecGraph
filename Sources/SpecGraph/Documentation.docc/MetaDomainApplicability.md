# Meta-model and domain check applicability

This work is anchored in SG-SPEC-0072 and proposal 0232, prompted by GitView
feedback at `60c67f7` on runtime `0f0a056a`. The first runtime slice separates
domain reports from unrequested meta checks; it does not approve applicability
or activate a global policy.

Three current sgcore warnings describe two synthesized meta bindings:
`kind: spec` produces `sgcore:Spec`, `id` produces `sgcore:Node`, and validation
also requires the Spec binding. They do not identify three missing domain
concepts. The draft sgcore applicability is project-local; applicability to an
external product's specification artifact remains undecided.

The proposed split names `domain_vocabulary` and `specification_metamodel`
check scopes, separate from existing local/composed context metadata `scope`.
Each requested analysis has its own context/profile/evidence and findings.
Outcomes distinguish `not_requested`, `analyzed`, `unavailable` and `invalid`.
An unrequested check cannot supply passing evidence or a zero-gap claim.
Unresolved applicability is unavailable when requested, not an asserted
not-applicable decision. At least one requested analysis must complete before
aggregate completion can be claimed; a requested unavailable/invalid check
prevents it. Unknown domain terms remain review gaps.

The context-bound command default requests domain analysis and shows meta
checks as `not_requested`. It does not silently import sgcore or treat package
selection as a meta-check request. This is the bounded advisory operation default.
The first implementation separates domain projection from legacy
structural checks; an explicit meta assessment follows a source/applicability
decision. No arbitrary ontology-composition solver is needed for this split.

Legacy no-context 0134/0135 behavior needs characterized compatibility. Changed
analysis semantics require a new profile/report contract and freshness binding
for requested scopes, each context/profile, applicability evidence and spec
bytes in the first implementation slice, without waiting for optional meta
assessment support. Old combined reports are not equivalent to scoped reports.
Existing inventory freshness remains unassessed. Semantic approval, prose
coverage, canonical authority and global gates are unchanged.

The source-bound observation, full proposed contract, acceptance matrix and
decisions are in
`docs/reviews/0232_project_ontology_context/meta-domain-applicability/README.md`.
The original observation remains historical. A separate verification capsule
records a re-executed local comparison with the same original spec bytes and
pinned ontologyc 0.5.0: main GitView has two domain gaps (Activity and unselected
motivcore:Motive), composition has one (Activity), and both explicitly show meta
not_requested. Requesting meta preserves domain results and returns unavailable.
The count reduction is corrected scope attribution, not completed meta coverage.

Bundles and domain children use schema 2 and
`specgraph-scoped-ontology-advisory-v1`; local/composed metadata is v3/v2.
Repeatable `--ontology-context-check-scope` selects scopes in the target-scoped
Supervisor operation. Compact output exposes both outcomes. Freshness binds the
current scope manifest, profiles and captured inputs; old combined reports need
recomputation. Empty requests do not complete and meta-only requests do not run
domain inventory. The native ontology-context route remains capture-only.
