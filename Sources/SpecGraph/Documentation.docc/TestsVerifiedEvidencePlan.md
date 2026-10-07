# Tests-Verified Evidence Plan

Proposal 0225 plans a future `tests_verified_v1` evaluator. The current claim
remains `unknown / evidence_evaluator_unavailable`; this proposal adds no
evaluator, receipt issuer, runner adapter, schema change or canonical claim.

The intended evidence path is explicit test assertion and evaluation
correlation from proposal 0224, pinned producer observation, trusted
FeaturePassport-issued receipt/decision, then a fresh digest-pinned SpecGraph
verification. A passing test root alone is insufficient. Each declared target
needs its complete required bound assertion set and artifacts. Failed, skipped,
stale, untrusted or incomplete evidence cannot satisfy the claim.

The evidence must pin the tested application/build and test bundle to the
source revision with provenance. The evaluator must verify the latest attempt
revision through an authoritative live head/finality or revocation contract;
a caller-provided closure cannot establish that no later invalidation exists.
Accepted receipt pairs are necessary but not sufficient: a separate live
aggregate decision must be trusted and `accepted` under the configured decision
trust store.

`tests_verified` would mean only that a configured authority accepted the
explicit pinned assertion set. It does not mean all tests passed, coverage is
exhaustive, code is correct, or production behavior is verified. Keep it
separate from `runtime_verified`.

The proposed delivery order is: review the cross-repository contract; realize a
provider-neutral producer and issuer prerequisite in their owning projects;
implement a separate read-only SpecGraph evaluator; demonstrate one bounded
synthetic pilot; then review any activation separately. Each implementation
phase requires its own PR and validation. See
`docs/proposals/0225_tests_verified_evidence_admission_plan.md` for the planned
contract, acceptance cases and unresolved decisions.

```yaml
canonical_mutations_allowed: false
runtime_code_mutations_allowed: false
evidence_admission_allowed: false
```
