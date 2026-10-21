# Traceability Evidence Providers and SVC

RFC 0226 proposes the integration boundary:

```text
EvidenceProvider -> immutable TraceSnapshot -> metric adapter
                                         -> traceability checks
```

Status: `deferred_until_canonicalized`. The proposal and bounded Supervisor
cycle prepare a reviewable contract; provider runtime and metric-profile
activation remain future slices.

## Current boundary

The existing `specification_verifiability` signal averages legacy acceptance
coverage status scores. The metric-pack registry and input catalog expose that
proxy, while explicit publication atom/test bindings, source-bound intent review
records and delivery execution observations remain separate sources.

## Replaceable sources and immutable facts

An EvidenceProvider receives an explicit subject scope, source revision and
artifact selection. An initial explicit Python protocol/registry selects built-in
providers. Collection is separated from metric interpretation and performs no
implicit test execution or network inference. External plugin discovery remains
a later concrete integration decision.

TraceSnapshot keeps declared links, resolved declarations, execution observations
and their outcomes distinct. Each fact retains subject identity, source digest,
provider version and completeness. Historical PR review coverage does not confirm
later implementations. Multiple providers preserve provenance and conflicts
without multiplying the count of one atom.

## SVC profile and compatibility

SVC measures the fraction of the complete selected atom inventory with a qualified
verification channel under a versioned profile. The proposed first profile
requires valid resolved bindings. A failing executed check can establish
verifiability while reporting failed fulfillment separately. Missing optional
execution does not erase resolution; incomplete required inventory prevents an
exact ratio. Empty selection is explicitly not applicable in this proposed
profile. This qualification rule still requires review.

Existing proxy values, thresholds, CLI commands and viewer contracts remain
unchanged until a separately reviewed migration. New values retain profile and
input provenance. Trace checks and metric adapters consume the same facts;
blocking policy is a separate reviewed interpretation.

The first runtime cohort is SG-SPEC-0071. Realization proceeds through contract
review, facade-preserving extraction, one pilot provider/profile, then connection
to existing metric artifacts. Future acceptance cases cover unresolved links,
failed and missing execution, stale input, historical records, duplicate/conflicting
providers, unchanged proxy behavior and code-only change freshness.

```yaml
canonical_mutations_allowed: false
runtime_profile_activation_allowed: false
evidence_admission_allowed: false
```

This work does not activate `tests_verified_v1` or change trusted receipt admission.
See `docs/proposals/0226_traceability_evidence_providers_and_svc.md`, its source
draft and the retained Supervisor run evidence for actual outcomes.
