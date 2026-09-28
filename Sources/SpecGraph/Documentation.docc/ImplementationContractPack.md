# Implementation Contract Pack

Proposal `0047`, Slice 4 provides the `explicit_node_observability_v1` profile.
Run `make implementation-contract-pack` with `CONTRACT_WORKSPACE_ROOT` and
`CONTRACT_TARGET_SPEC` to project a structured `specification.observability`
declaration into `implementation_contract_pack_preview`.

The artifact pins source SHA-256, preserves full target specification and
acceptance, validates local scenario references, and carries expected observations
into an `implementation_work_preview`. Output is scoped to
`runs/implementation-contract-packs/<id>.json` in the selected product workspace.
It is not automatically inserted into the Implementation Work backlog or dispatched.

Successful projection remains `review_required` (exit 0). Missing obligations,
an unresolved source gate, or unsuitable source status produce `blocked` (exit 2).
Malformed input or output errors exit 1; a prior output may remain. Consumers
must check the current invocation and regenerate after source changes.

Every preview declares `canonical_mutations_allowed: false` and
`runtime_code_mutations_allowed: false`; evidence and inheritance are
`not_evaluated`. This profile grants no approval or readiness authority. Review
the exact digest and bind obligations to implementation objects, call sites and
tests before the bounded implementation handoff. Existing code remains prior work.

Feature Passport remains independent. Runtime observation ingestion, production
storage, inherited-policy propagation and automatic task dispatch are future work.

Nested Codex refinement reads the explicit `--output-last-message` artifact;
diagnostic transcript text cannot replace final executor protocol markers.


## Evidence claim admission

`make evidence-claim-gate` invokes the bounded `local_source_v1` consumer of live
Feature Passport source resolution. Optional `evidence_claims` are declarations;
Supervisor and YAML lint reject self-authored verdicts. Exact spec/passport/request
and adapter/policy digests bind each derived report. Canonical declarations require
complete request coverage; legacy explicit requests are exploratory only.

`source_anchored` confirms pinned syntactic source identity. A canonical
`runtime_verified` declaration may pin the bounded `runtime_verified_v1`
Feature Passport aggregate-decision
identity; the gate freshly invokes the digest-pinned `verify-decision` CLI and
admits only a trusted `accepted` result whose signed identity and digest links
match. Trusted `not_satisfied` remains unknown. Tests, effect and outcome claims
remain `unknown / evidence_evaluator_unavailable`. A review-pending source blocks
aggregate admission even when claims resolve. Exit codes are 0 admitted, 2
denied/unknown, 1 invalid input/execution failure. The local gate never mutates
canonical lifecycle status and adds no Feature Passport dependency on SpecGraph.
See repository `docs/evidence_claim_admission.md` for the full contract.
