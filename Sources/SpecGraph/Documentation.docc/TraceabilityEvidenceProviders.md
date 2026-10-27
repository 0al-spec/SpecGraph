# Traceability Evidence Providers and SVC

RFC 0226 proposes the integration boundary:

```text
EvidenceProvider -> immutable TraceSnapshot -> metric adapter
                                         -> traceability checks
```

Compatibility slice B and declaration-only EvidenceProvider/TraceSnapshot slice
C1 are implemented. C2a adds explicit retained publication execution reports.
Atom SVC and metric-profile activation remain
`deferred_until_canonicalized`. The proposal and bounded Supervisor cycle retain
their separate semantic review boundary. See <doc:EvidenceProvider>.

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

## Implemented compatibility slice B

`tools/metric_packs/` provides immutable `VerifiabilityContext` inputs and results,
the `VerifiabilityMetric` protocol and the pure `LegacyVerifiabilityMetric`.
`build_metric_signal_index` accepts an optional `verifiability_metric` hook, with
the existing proxy selected by default. This is a specialized compatibility
context; C1 adds a separate declaration TraceSnapshot and explicit provider registry.
`SCORE_STATUS_SPEC` is shared by the extracted metric and the existing
Supervisor threshold-status facade.

The serialized metric entry, rounding, unknown-status counts, numeric coercion,
empty-input behavior and existing thresholds remain unchanged. Eight pre-refactor
JSON fixtures plus isolated-import, immutable-input, trace and composition tests
characterize compatibility. TP-08 now has executable characterization.
Retained execution-provider cases are implemented in C2a; atom-level SVC remains planned. C1 characterizes
declaration-provider scope, completeness, ordering and conflict preservation.

## Recovered semantic candidate

The 27 October review of SG-SPEC-0021 is `review_only`, with
`canonical_mutations_allowed: false`. The original candidate and archived raw
salvage remain historical sources; the v2 patch contains only proposed semantic
edits. Its preparation neither resolves an active gate nor adopts the proposal.

Specification Verifiability currently permits canonical evidence records and
trace links. Such records may cite derived observations without making those
observations canonical or admitting a new metric input class. Direct derived
execution inputs still require a reviewed input-boundary decision.

The revised notes distinguish unknown required inputs from conclusive negative
findings, preserve optional execution absence, and allow known zero results only
where the selected metric profile defines them. C1/C2a already separate
resolution, execution results and completeness. Their execution provenance is
`provider_reported_not_attested`; revision/run binding alone does not prove
wall-clock freshness, authenticity or semantic acceptance.

See `docs/reviews/0226_metric_verifiability_recovery_review.md` and
`docs/reviews/0226_metric_verifiability_candidate_v2.patch`. The recovered v2
delta is now prepared in a focused canonical-spec PR for human review, updating
SG-SPEC-0021's boundary notes and acceptance-evidence explanation. Its
modification timestamp is refreshed; acceptance criteria, input classes,
family roles, invariant IDs and lifecycle remain unchanged.

Preparing the PR does not attest final semantic approval. The current Intent
Atom profile does not count `boundary_notes`, so the five clarifications do not
add counted atoms. RFC 0226 C2b qualification and any direct derived-input
admission remain separate decisions; formulas, thresholds and runtime behavior
are unchanged.
