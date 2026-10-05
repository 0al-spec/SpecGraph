# 0225 Tests-Verified Evidence Admission Plan

RFC: SG-RFC-0225
Version: 0.1.0

## Status

Draft proposal; planning contract only. Runtime realization is
`deferred_until_canonicalized`. This document proposes a bounded plan for a
future `tests_verified_v1` evaluator. It does not implement a test runner,
evidence issuer, verifier, schema change, canonical claim, or admission path.

```yaml
canonical_mutations_allowed: false
runtime_code_mutations_allowed: false
evidence_admission_allowed: false
```

## Source Material

- [Operator request and current admission inspection](../archive/proposal_sources/0225_tests_verified_evidence_admission_plan.md)
- [0224: Compositional Test Context and Evidence Binding](0224_compositional_test_context_and_evidence_binding.md), producer observation and assertion binding prerequisite
- [0047: Evidence-Backed Build Protocol](0047_evidence_backed_build_protocol.md), admission ownership and receipt handoff
- [Evidence Claim Admission](../evidence_claim_admission.md), current `evidence_evaluator_unavailable` behavior
- [Implementation Contract Pack](../implementation_contract_pack.md), current SpecGraph consumer boundary

## Problem

SpecGraph deliberately leaves `tests_verified` as
`unknown / evidence_evaluator_unavailable`. A test name, source anchor, passing
CI summary, producer observation, or signed blob by itself cannot establish
that a particular declared obligation was exercised by the intended test at
the intended source revision and accepted under a trusted evidence policy.

Proposal 0224 supplies a candidate producer-side seam: an assertion names the
obligation it checks, stable `correlation_id` edges connect it to evaluations,
and late attributed failures invalidate prior success. It does not issue a
receipt or admit evidence. Proposal 0047 assigns generic receipt issuance to
FeaturePassport and claim admission to SpecGraph. The missing work is a reviewed
contract that connects those boundaries without making SpecGraph a test runner,
signer, or second receipt authority.

## Goal and Non-Goals

The goal is to prepare a versioned, fail-closed evaluator plan that could derive
`tests_verified` only for explicitly declared obligations covered by trusted,
source-pinned, successful test assertions and their required evidence.

The claim is bounded: it means the configured trusted authority accepted a
specific set of bound test assertions for the pinned inputs. It does not mean
that all tests passed, the tests are exhaustive, the code is correct, or the
product behaves correctly in production. `tests_verified` must remain distinct
from `runtime_verified`.

This proposal does not add a SpecificationCore API, runner adapter, FeaturePassport
issuer or receipt schema, signing keys, test-result parser, SpecGraph schema or
CLI implementation, canonical evidence declaration, lifecycle mutation, CI
merge requirement, or production claim. Those are separate reviewed changes in
the repositories that own them.

## Proposed Ownership and Evidence Flow

```text
declared SpecGraph obligation
          │ exact target binding
          ▼
test assertion + evaluation correlation (0224 producer contract)
          │ pinned source, run, selection and result artifact
          ▼
producer observation ──► trusted FeaturePassport issuer
                                │ signed accepted receipt/decision
                                ▼
                   SpecGraph tests_verified_v1 evaluator
                                │ fresh, digest-pinned verification
                                ▼
                     derived claim result only
```

The producer records what the runner observed. FeaturePassport owns generic
receipt issuance and its signer boundary. SpecGraph owns the claim declaration,
target mapping and admission decision. Each consumer independently selects its
trust stores and current policy. A producer-issued or test-process self-signed
receipt is not independent corroboration. If FeaturePassport cannot yet express
the test-specific assertion set using its provider-neutral receipt contract,
that upstream contract is a blocking dependency; this proposal does not invent a
SpecGraph-specific receipt format to work around it.

## Candidate `tests_verified_v1` Contract

### 1. Explicit claim and target set

The canonical claim names a reviewed test-evidence profile and an explicit,
nonempty set of obligations. The profile maps every obligation to stable
assertion bindings from the 0224 execution contract. A passing test root does
not verify its declared targets by itself. A target is admitted only when every
required assertion binding for that target is present, completed and successful,
and required evaluation correlations and artifacts are present.

The request must resolve and include the entire expected assertion-binding set
for each declared target; a caller cannot submit a passing subset and omit a
required assertion. How that reviewed expected set is versioned and referenced
by a claim remains a contract decision for Phase 1.

No test name, file path, matching string, root scenario, or sibling assertion
implicitly supplies coverage. No parent-child or transitive coverage is
inferred. The claim says only that the reviewed, explicitly selected assertion
set passed; it makes no statement about unnamed tests or overall suite
completeness.

### 2. Immutable execution and source pins

The evidence request binds the exact spec and passport bytes, target declaration,
test profile/version, repository identity, source commit, test-plan/selection
digest, runner identity/profile, invocation identity, execution attempt, and
result artifact digest. When applicable to the chosen runner profile, pin the
platform, device/runtime, toolchain and runner-image identity that can change
the result. The assertion-to-obligation edges use stable 0224
correlation identities and are included in the exported evidence closure.

An adapter must show that its result artifact belongs to the pinned run and
source revision. A test symbol found in source is not proof that the test ran.
A green job with incomplete or opaque selection is not enough. Retries are
separate attempts; a later successful attempt cannot erase a recorded earlier
failure. An attributed late failure supersedes a prior success as specified by
0224, and the evaluator consumes the latest attempt revision.

The first runner/result format is an implementation decision after the producer
contract is reviewed. Keep the SpecGraph claim model independent of XCTest,
Swift Testing, pytest, or any runner's private file format.

### 3. Trusted receipt and current decision

An accepted result requires an authority-issued receipt/aggregate decision that
binds the producer observation and its exact source, target, plan, result and
policy digests. SpecGraph invokes a digest-pinned verifier against fresh
snapshots of the claim request, source artifacts, decision, receipt pairs,
policy, trust stores and verifier executable. Input mutation during evaluation
fails closed; prior reports are not reused as current verdicts.

Receipt acceptance proves only that the configured authority accepted the
record under its pinned policy. It does not independently prove hardware
attestation, runner honesty, test quality, exhaustive selection, or production
behavior. Those guarantees may be claimed only if a future reviewed authority
contract supplies them explicitly. A signature or a public key in the payload
cannot install trust.

### 4. Derived outcomes and failure behavior

Only a live, trusted, accepted decision with exact declaration coverage and all
required assertions successful can produce a satisfied `tests_verified` claim.
Missing, stale, unresolved, skipped, failed, ambiguous or incomplete inputs
remain unknown and block aggregate admission. An accepted receipt for a
non-passing test set cannot satisfy the claim. Invalid input or verifier
execution failure is an error, not a denial disguised as a test result.

The evaluator does not change canonical maturity or lifecycle state. A
`review_pending` source continues to block aggregate admission. Historical
results stay historical and must be re-evaluated against current declarations,
source pins, receipts, policy and trust.

## Bounded Delivery Plan

### Phase 1 — Freeze the cross-repository contract

Review assertion identity, target mapping, test selection completeness, run and
source pins, late-event revisions, and the exact receipt statement with the
owners of 0224, FeaturePassport and the pilot runner. Determine whether the
existing provider-neutral receipt contract can carry the required statement.
Keep `tests_verified` unavailable until this contract is accepted.

### Phase 2 — Realize the producer and issuer prerequisites

In the owning repositories, implement one runner adapter and a trusted issuer
path that binds the complete producer observation. Preserve provider-neutral
FeaturePassport schemas and keep SpecGraph identifiers out of generic receipt
issuance. Publish exact executable, policy and schema versions. This phase
requires its own PRs and review; RFC 0225 authorizes none of them.

### Phase 3 — Implement SpecGraph `tests_verified_v1`

After the upstream contract and executable are available, add a separate
SpecGraph implementation PR for declaration validation, target/ assertion
mapping, request snapshots, live digest-pinned verification, deterministic
reason codes and a read-only CLI. Keep the existing `runtime_verified_v1`
path unchanged. Add focused tests for positive, negative, stale, incomplete and
concurrent-input cases before enabling any canonical declaration.

### Phase 4 — Run one bounded pilot

Use one synthetic fixture and one explicitly bound test assertion. Pin source,
selection, result bytes, runner profile, receipt, policy, trust stores and
verifier. Demonstrate both accepted and rejected/unknown results, including a
missing binding and a stale revision. Keep product assets and secrets out of the
fixture. Do not infer canonical adoption, full suite coverage, or production
behavior from the pilot.

### Phase 5 — Review activation separately

Present the generated request, receipt/decision inputs, derived report and
limitations for human review. Any canonical `tests_verified` declaration,
SpecGraph lifecycle effect, required CI status or broader rollout requires a
separate explicit change and approval.

## Proposed Acceptance Cases

These cases plan future verification; none has been executed by this proposal.

| ID | Given / When / Then obligation |
| --- | --- |
| TV-01 | Given a declared target with its complete set of required bound assertions and a live trusted accepted decision over matching pins, when evaluated, then only that target becomes satisfied. |
| TV-02 | Given a passing root with no target-bound assertion, when evaluated, then the target remains unknown and aggregate admission is blocked. |
| TV-03 | Given one missing, skipped, failed, ambiguous or incomplete required assertion, when evaluating a target with other passing assertions, then the target does not become satisfied. |
| TV-04 | Given an assertion without its required 0224 evaluation correlation or artifact edge, when exported or consumed, then malformed or incomplete evidence is rejected or remains unknown. |
| TV-05 | Given a source commit, test-plan/selection, runner, result artifact, claim, or policy digest that differs from the pinned decision, when verified, then the claim remains unknown. |
| TV-06 | Given an attributed late failure with a higher attempt revision, when a prior successful report is presented, then the evaluator uses the newer revision and the old success cannot satisfy the claim. |
| TV-07 | Given a retry with a later passing attempt after an earlier failure, when evaluated, then both attempts remain attributable and the reviewed policy determines the claim without overwriting history. |
| TV-08 | Given an unsigned, self-issued, untrusted, or trusted-but-not-accepted receipt, when evaluating, then the claim is not satisfied and the reason identifies the failed trust/admission stage. |
| TV-09 | Given any evidence input changes while the verifier is running, when evaluation completes, then it fails closed and emits no satisfied result. |
| TV-10 | Given a previously successful report but changed current source, declaration, receipt, policy, trust store, or verifier, when evaluated, then the old report is not reused as current evidence. |
| TV-11 | Given a valid accepted test receipt, when comparing claims, then `tests_verified` does not imply `runtime_verified`, effect, outcome, exhaustive testing, or production correctness. |
| TV-12 | Given a review-pending source or unresolved target, when all test assertions passed, then aggregate admission remains blocked. |

## Success Criteria and Limits

The future implementation is useful only if a reviewer can trace each admitted
target from its current declaration to exact assertion bindings, evaluation
correlations, pinned run artifacts, trusted receipt/decision and verifier
result. It must fail closed for every listed missing/stale/untrusted condition,
preserve attempt history, produce deterministic reason codes, and leave all
unrequested claim kinds and lifecycle states unchanged.

Passing this profile would establish a bounded accepted test-evidence claim. It
would not establish the correctness of the test itself, exhaustive behavioral
coverage, production runtime behavior, physical-device behavior, or hardware
attestation unless separately evidenced by their own reviewed contracts.

## Preparation Validation and Remaining Decisions

Run `make proposal-tracking-gate`, `make docc-sync`, JSON parsing, proposal ID
collision checks and `git diff --check`. These validate preparation and
tracking only; they do not implement or execute the evaluator.

Before implementation, resolve the upstream receipt fields and issuer trust
boundary, exact test-selection completeness semantics, runner-profile assurance,
claim-to-assertion mapping location, deterministic result artifact profile, and
whether trusted `not_satisfied` remains unknown under the existing claim model.
Do not turn `tests_verified` on while any of those inputs are unresolved.
