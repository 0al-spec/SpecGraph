# Evidence claim admission

Proposal `0047` now supplies bounded `local_source_v1` and
`runtime_verified_v1` admission profiles. SpecGraph consumes Feature Passport's
pinned source-resolution and signed aggregate-decision contracts; Feature
Passport acquires no dependency on SpecGraph. This does not change upstream
proposal `0203`'s historical adoption snapshot or create a competing receipt
schema.

## Declarations and derived verdicts

Canonical nodes may declare an optional nonempty `evidence_claims` list:

```yaml
evidence_claims:
- id: route-source
  kind: source_anchored
  passport_criterion_ids: [ordered-composition, deterministic-selection]
```

Every declaration requires `id`, `kind`, and `passport_criterion_ids`; IDs and
criterion references must be unique and nonempty. `runtime_verified` may add an
exact `feature_passport_decision` identity mapping (`feature_id`, passport and
claim-policy identity/version, `claim_id`, policy digest, predicate profile,
authority ID, and key ID). It contains no verdict. Supervisor validation and YAML
lint reject additional fields and authored verdicts such as `state`, `verified`,
or `satisfied`. Existing nodes without declarations remain valid.

Claims are orthogonal to spec maturity (`linked`, `reviewed`, `frozen`). No source
resolution result changes those statuses. Declarations require the same normal
spec review as other canonical edits. Existing maturity values alone are not
proof of implementation correctness.

## Request and CLI

An explicit `evidence_claim_admission_request` JSON object has `schema_version: 1`,
a `source` object (`spec_id`, raw-byte `spec_sha256`, raw-byte `passport_sha256`),
and a nonempty `claims` list in the declaration format above. When the node has
canonical declarations, the request must reproduce the entire ordered list.
For a legacy node without declarations an explicit request is an exploratory
check; it never installs new canonical obligations.

```sh
make evidence-claim-gate PYTHON=.venv/bin/python \
  CLAIM_REQUEST=/path/request.json CLAIM_PASSPORT=/path/passport.json \
  CLAIM_SPEC=/path/ZEU-SPEC-0016.yaml \
  CLAIM_FP_CLI=/path/feature-passport CLAIM_FP_CLI_SHA256=<reviewed-binary-sha256> \
  CLAIM_REPOSITORY=zeusus=/path/Zeusus
```

The tool snapshots and hashes inputs and invokes the explicitly digest-pinned
Feature Passport executable. Source claims use `resolve-sources`; a mapped runtime
claim invokes `verify-decision` against snapshots of passport, claim policy,
bundle, signed decision, both trust stores, and every referenced observation and
receipt. The request pins their raw-byte SHA-256 digests, including the CLI bytes.
Bundle pair paths must stay below the bundle directory. Input mutations during
evaluation fail closed. Reports are never loaded from a cache. CLI repository
flags may be repeated; the Make shortcut covers the single-repository pilot.

For runtime admission, also pass `CLAIM_POLICY`, `CLAIM_BUNDLE`, `CLAIM_DECISION`,
`CLAIM_RECEIPT_TRUST_STORE`, and `CLAIM_DECISION_TRUST_STORE`. Their raw-byte
digests and the ordered `pair_files` (`observation_path`, `observation_sha256`,
`receipt_path`, `receipt_sha256`) belong in `source.runtime` alongside the
`feature_passport_cli_sha256` pin.

Output is sorted JSON on stdout. Exit `0` means all requested claims admitted;
`2` means a derived denial/unknown or a source review blocker; `1` means invalid
input or execution failure. Redirect each invocation to a fresh artifact rather
than treating an older report as current. Reports bind the spec, passport,
request, adapter binary, policy source, and raw adapter report by SHA-256.

## Current semantics

- `source_anchored` requires valid passport bindings for every requested criterion,
  exact anchor coverage, and matching resolved identities and blob IDs for every
  explicitly bound implementation/test element at pinned commits. It confirms
  **syntactic source identity only**. Finding a test symbol does not run the test.
- An unmapped `runtime_verified` claim remains
  `unknown / evidence_evaluator_unavailable`. A mapped runtime claim is satisfied
  only when the live pinned CLI exits zero, emits strict JSON with `trusted: true`
  and `decision: accepted`, and the signed decision identity, digest links,
  predicate profile, authority and key exactly match the canonical declaration.
  A trusted `not_satisfied` decision remains unknown. Signature and receipt trust
  verification are performed by Feature Passport's live `verify-decision` call.
- `tests_verified`, `effect_committed`, and `outcome_completed` remain
  `unknown / evidence_evaluator_unavailable`. A source pass cannot promote them.
  Unsupported kinds are rejected at declaration validation.
- Missing, duplicate, unresolved, stale, or mismatched evidence never passes.
  Claims may individually be satisfied while aggregate admission is denied.
- All requested claims must pass. No parent/child graph propagation or transitive
  element-use coverage is inferred. Aggregation across specs requires a future
  explicit policy.
- Source gate must be `none`, with status `linked`, `reviewed`, or `frozen`.
  Pending source review remains a blocker even when anchors resolve.

These local profiles trust the operator-selected executable and host. Runtime
admission reruns signed aggregate-decision verification, but is not a hermetic
build attestation, production trace evaluation, typecheck, module-membership proof,
or test result. The source CLI depends on pinned Git object availability; missing
objects fail closed. Reports are historical evidence: consumers must rerun against
current inputs instead of replaying old admission. `review_pending` remains an
aggregate blocker even if source/runtime claims individually pass.

The tool is read-only (`canonical_mutations_allowed: false`,
`runtime_code_mutations_allowed: false`). `feature_passport_decision_trusted` is
true only when live `verify-decision` returns a trusted report for the mapped
claim. It can be true for a trusted `not_satisfied` result even though that claim
remains unknown; source-only admission does not verify receipt signatures. No
lifecycle mutation endpoint consumes this report yet. Future lifecycle enforcement
must invoke current admission rather than trust an authored flag or a report filename.

Validation: `make test-evidence-claim-gate PYTHON=.venv/bin/python` plus the
Supervisor regression `test_canonical_evidence_claims_cannot_assert_verdict`.


## Development evidence

The first stub run produced an observed Red (15 failures, 1 pass), followed by
Green for the initial 16 scenarios. Expanded CLI, malformed-input, canonical-lint,
subset-request, and concurrent-input checks bring the focused gate suite to 30
passing tests; YAML tooling adds 8. The combined Supervisor/Contract Pack/gate
regression run passed 1087 tests before the last three focused hardening cases.
The final focused rerun passed all 38 gate/YAML tests. Live Zeusus evidence lives
in its `docs/evidence/evidence-claim-admission.md`; four anchors resolved, runtime
remained unknown, review_pending blocked admission, and two reports were identical.


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
