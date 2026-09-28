# Evidence claim admission

Proposal `0047` now supplies the bounded `local_source_v1` gate. This is a
SpecGraph consumer of Feature Passport's existing pinned Swift source-resolution
contract. Feature Passport acquires no dependency on SpecGraph. The runtime
receipt model in upstream proposal `0001` v0.3.0 remains future evaluator work;
this adapter does not create a competing receipt schema or update proposal
`0203`'s historical upstream adoption snapshot implicitly.

## Declarations and derived verdicts

Canonical nodes may declare an optional nonempty `evidence_claims` list:

```yaml
evidence_claims:
- id: route-source
  kind: source_anchored
  passport_criterion_ids: [ordered-composition, deterministic-selection]
```

Every declaration has exactly these three fields; IDs and criterion references
must be unique and nonempty. Supervisor validation and YAML lint reject authored
verdicts such as `state`, `verified` or `satisfied` in this surface. Existing nodes
without declarations remain valid. This is an additive reserved surface, not a
scan for arbitrary product fields named `verified` elsewhere in a specification.

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

The tool snapshots and hashes inputs, invokes the explicitly digest-pinned
Feature Passport executable against those exact passport bytes, checks for
concurrent input/binary changes, and interprets its live source-resolution report.
It accepts no cached success-report path. CLI repository flags may be repeated;
the Make shortcut covers the single-repository pilot.

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
- `tests_verified`, `runtime_verified`, `effect_committed`, and `outcome_completed`
  yield `unknown / evidence_evaluator_unavailable`. A source pass cannot promote
  these claims. Unsupported kinds are rejected at declaration validation.
- Missing, duplicate, unresolved, stale, or mismatched evidence never passes.
  Claims may individually be satisfied while aggregate admission is denied.
- All requested claims must pass. No parent/child graph propagation or transitive
  element-use coverage is inferred. Aggregation across specs requires a future
  explicit policy.
- Source gate must be `none`, with status `linked`, `reviewed`, or `frozen`.
  Pending source review remains a blocker even when anchors resolve.

This local profile trusts the operator-selected executable and host. It is not a
signed receipt, hermetic build attestation, production trace evaluation, typecheck,
module-membership proof, or test result. The pure evaluator is deterministic for
fixed inputs; the CLI also depends on pinned Git object availability and the host
adapter environment. Missing objects fail closed. Reports are historical evidence:
consumers must rerun against current inputs instead of replaying old admission.

The tool is read-only (`canonical_mutations_allowed: false`,
`runtime_code_mutations_allowed: false`, `receipt_signature_verified: false`).
No lifecycle mutation endpoint consumes it yet. Future lifecycle enforcement must
invoke current admission rather than trust an authored flag or a report filename.

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
