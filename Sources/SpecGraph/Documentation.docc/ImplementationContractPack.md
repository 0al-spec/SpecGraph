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
