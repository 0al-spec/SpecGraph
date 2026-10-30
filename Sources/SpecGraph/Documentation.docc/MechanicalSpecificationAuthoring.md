# Mechanically checked specification authoring

SG-RFC-0233 records the agreed direction to connect specification authoring to
existing Ontology, native BDD, Supervisor and SIB checks. It is a draft proposal
with `deferred_until_canonicalized` runtime posture, not a new active gate.

The authoring loop is obligation -> ontology binding -> acceptance/check ->
scoped diagnostic -> bounded refinement. A large specification may remain a
leaf. Concrete missing obligations and structural complexity are reported
separately; a criterion count alone does not prove independent concerns.

## Existing mechanisms and limits

SG-SPEC-0015 supplies delegation semantics; SG-SPEC-0021 supplies the derived
metric boundary; SG-SPEC-0049 diagnoses harmful fragmentation; SG-SPEC-0070
validates native scenario declarations. A valid declaration is not execution.
Ontology package validation and explicit-reference lookup do not establish
complete specification-instance coverage. An authoring profile must explicitly
select applicable obligations instead of requiring every optional relation.

SVC retains the full declared in-scope denominator. Missing inputs and
unsupported checks remain visible; legacy weighted coverage and SIB_FULL
expected-test proxies are not silently promoted to atom-level verification.
Graph coupling distinguishes edge roles and architectural boundaries.

## Pilot and durable return path

The planned pilot uses SG-SPEC-0072 outcome precedence at
`c31b1a332ed1df2fba7d10ad0a215f230d61b97e`, from the open ontology stack when
this proposal was prepared. It is not a canonical main node at the preparation
baseline `ee8cb62f5acca18e884dcc19cf306ca6708ab7c5`.

Source excerpts, draft obligations and an existing intent/proposal registration
retain the conversation as shared project memory. The return handle is
`proposal::0233-mechanical-specification-authoring`; its existing canonical
target is SG-SPEC-0015. Review the pilot inventory/profile, then prepare one
derived report and negative sensitivity probes. Those probes have not run.
The authored proposal's empty `proposal_queue_status` keeps it outside derived
queue retirement; `proposal_authority_state` records its independent review state.

Registration does not execute an agent or approve canonical publication:
`runtime_profile_activation_allowed: false` and
`evidence_admission_allowed: false` remain in effect for this proposal.

## Source documents

- `docs/proposals/0233_mechanical_specification_authoring.md`
- `docs/proposals/0233_mechanical_specification_authoring.intent.yaml`
- `docs/archive/proposal_sources/0233_mechanical_specification_authoring.md`
- `docs/reviews/0233_mechanical_specification_authoring/README.md`
