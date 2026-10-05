# Compositional Test Context

Proposal 0224 prepares a **contract preparation only** follow-up to RFC 0223's
execution-binding boundary. Runtime realization is `deferred_until_canonicalized`.

A proposed test composition carries immutable root provenance, scoped rule and
assertion bindings, and artifact digests through evaluation and export. Recorder
IDs remain local and are qualified by execution scope. Root scenario context
does not automatically mean every child verifies the scenario. A negative
predicate result can belong to a passing rejection test.

SpecificationCore owns provider-neutral binding/context primitives; test-runner
adapters own actual assertion and completion outcomes. FeaturePassport owns the
observation envelope and receipt policy. SpecGraph resolves its own exact
references and projects evidence through existing gates. Zeusus owns fixtures
and the synthetic legacy-anchor pilot. FeaturePassport remains provider-neutral.

Rule evaluations and assertions connect through stable attempt-scoped
correlation edges preserved in the export closure. A declared verification
target remains unverified until it has a completed successful bound assertion;
a passing root alone is insufficient. Open asynchronous scope leases delay
success, and any attributed post-closure failure emits a higher-revision
invalidation that admission consumers must honor.

The pilot produces and inspects observations only. The current SpecGraph
`tests_verified` evaluator is unavailable; issuance, pinned receipt, policy,
trust-store and aggregate-decision stages are separate prerequisites for any
future admission claim.

```yaml
canonical_mutations_allowed: false
runtime_code_mutations_allowed: false
evidence_admission_allowed: false
```

The proposal implements no `SpecificationTest` API. Its future cases cover
context isolation, correlation edges, conflicts, negative expectations,
late-event invalidation, fail-closed target verification, retries, artifact
integrity, stale contract references and provider-free use. Tracking/DocC
checks prove preparation coherence, not runtime conformance or accepted
evidence. The motivating Zeusus source is pinned in the proposal's archived
source record by checkout commit and exact node digest.
