# Implementation Contract Pack

## Proposed opt-in identity declarations

Proposal `0047` now includes `observability_identity_declarations_v1`,
**contract preparation only**, with runtime realization
`deferred_until_canonicalized`. See repository
`docs/observability_identity_profile.md` and portable definition
`docs/contracts/observability_identity_profile_v1.json`.

The proposed `identity_profile` selector is retained in immutable authoring
context as well as the node. Both absent means legacy behavior; an unknown
version, invalid selector or removal from an opted-in candidate cannot silently
fall back. Every obligation must declare `specification_id`, `rule_id`,
`component_id`, `implementation_id` and `scenario_id_if_tagged`. Extra attributes
are preserved; the accepted alias map is empty. A union across obligations
cannot cover missing names. Conditional harness binding requires no fabricated
runtime scenario ID.

Future attributed diagnostics pin source and definition bytes; one shared check
must reach authoring review capture and explicit contract projection. These
declarations do not prove actual identity resolution, runtime propagation,
mapping completeness or verified execution. Current tooling **does not enforce
`identity_profile`**; the sixteen acceptance cases are future checks. This
preparation declares `canonical_mutations_allowed: false`,
`runtime_code_mutations_allowed: false` and `evidence_admission_allowed: false`.

## Implemented explicit-node projection

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

Proposal 0225 prepares a separate, read-only `tests_verified_v1` plan. It does
not implement the evaluator or enable the claim. The planned contract requires
source-to-build provenance, an authoritative latest-attempt proof, accepted
receipt pairs, and a separate live trusted `accepted` aggregate decision. See
<doc:TestsVerifiedEvidencePlan> and
`docs/proposals/0225_tests_verified_evidence_admission_plan.md`.


## Cross-repository receipt issuance handoff

The 2026-09-30 amendment to proposal `0047` is `proposal_only`. Existing
`runtime_verified_v1` verification does not implement receipt issuance.
FeaturePassport owns the generic issuer API/CLI and signer abstraction, without
any dependency on SpecGraph. Zeusus owns product requirements, trace adaptation
and pilot runner orchestration. SpecificationCore owns generic tracing;
SpecSpace only presents evidence. An explicit runner/CI role operates the
authority and holds its signing capability outside Git; no new repository is
required by the pilot.

A receipt policy describes the authority's checks; a claim policy describes the
evidence required for a bounded assertion; SpecGraph owns the admission policy
and canonical mapping. Each verifier selects its own receipt/decision trust
stores. A public key in the payload or a valid signature cannot install trust.
The first proposed local receipt scope is exact contract-match acceptance, not
independent origin, successful execution, production delivery or user outcomes.
Historical unsigned observations are not issuer-controlled runs retroactively.

Implementation order: FeaturePassport issuer contract/implementation PR ->
Zeusus reviewed local configuration and fresh capture pilot -> SpecGraph reviewed
claim mapping and live admission. Missing inputs, trusted `not_satisfied`, stale
bytes or unresolved review gates cannot pass. This amendment creates no issuer,
keys, adopted policies or lifecycle mutations. See the proposal's ownership table
and bounded acceptance criteria before routing implementation work.


## CLI delivery and read-model publication

Proposal `0047` extends the handoff with a `proposal_only` delivery contract.
FeaturePassport owns the versioned CLI release and target-specific executable
digests. Platform owns the reviewed runner dependency lock, compatible binary
installation and digest-pinned runner image delivery. That dependency lock is
separate from the existing SpecSpace API/UI service image lock. SpecGraph owns
live admission and curated public-safe read-model publication; SpecSpace consumes
the data through its provider and does not receive a runnable receipt authority.

A macOS executable cannot serve a Linux runner. Source commit, executable digest,
runner image digest, signing authority and verifier trust inputs are independent
pins/roles. Installation verifies approved bytes and capabilities; unavailable
signer, incompatible target or digest mismatch fails closed. A checksum alone
does not authenticate the publisher or grant authority. Private keys stay outside
images, release assets and Git. Installing a CLI does not enable managed execution.

Retain exact signed input bytes, separate producer/issuer/verifier pins, and
operation/evaluation identities. SpecGraph's publication is a public-safe
projection, not a replacement for complete verification inputs. Historical
published results do not authorize current admission. Local, hosted and
production evidence remain distinct. Implementation PRs, target-specific release,
authority configuration and deployment approval are still subsequent work; this
documentation amendment installs no executable and triggers no deployment.

## Zeusus second-pass feedback triage

The 2026-10-22 four-entry triage is documented in
`docs/reviews/zeusus_second_pass_feedback_triage_20261022.md` and its hashed JSON
evidence. All four collector SHA-256 receipts match. No raw product specs,
transcripts or machine-local paths are published. This is triage only, not
runtime prevention, canonical adoption or trusted execution evidence.

- ZST-01 routes Markdown protocol-marker friction to proposal 0056. Existing
  plain-line final-response rejection worked; child exit 0 is not approval.
  Clarified output instructions and a separately reviewed typed transport are
  follow-ups; diagnostic transcripts cannot supply missing final markers.
- ZST-02 routes complete `rule_to_obligation_mapping` scope and exact references
  to proposal 0047, with 0226 resolver concepts and 0223 scenario identity as
  supporting work. A saved candidate mapped 10/15 rules despite eight true
  supervisor validators. Those validators do not establish mapping completeness.
- ZST-03 links the corrected operator seed-filter error to the related 0054
  direction. Native unadopted-candidate continuation is not implemented by 0054
  initialization or 0193 session continuation. Provenance and pending-candidate
  history need a bounded continuation contract; resetting a gate is not approval.
- ZST-04 routes per-obligation identity spelling/required fields to proposal 0047;
  proposal 0224 concerns later context propagation. The explicit parser checks
  an attributes list, not an identity profile. The pilot requests
  `specification_id`, `rule_id`, `component_id`, `implementation_id` and
  `scenario_id_if_tagged`; actual scenario values remain absent without a tagged
  harness. These names are not imposed globally by this triage.

`explicit_node_observability_v1` is unchanged between the old `92ee71cf` and
`c46d58ad` pilots. The final product packet has 49/49 participant rules mapped,
37 obligations with the requested names, and 100 preserved BDD scenarios.
Those product-side fixes do not mean that SpecGraph gained new checks; no BDD
or gameplay tests were executed by the triage. All candidates remain
`review_pending`. First prepare an opt-in identity profile, then full/partial
rule coverage, and wire the selected checks before review capture.
