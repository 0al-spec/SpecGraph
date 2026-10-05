# 0224 Compositional Test Context and Evidence Binding

RFC: SG-RFC-0224
Version: 0.1.0

## Status

Draft proposal; contract preparation only. Runtime realization is
`deferred_until_canonicalized`. This document proposes execution bindings and
metadata propagation; it does not implement `SpecificationTest`, activate a
test adapter, adopt a canonical spec, or admit evidence.

```yaml
canonical_mutations_allowed: false
runtime_code_mutations_allowed: false
evidence_admission_allowed: false
```

## Source Material

- [Operator request and source inspection](../archive/proposal_sources/0224_compositional_test_context_and_evidence_binding.md)
- [0223: BDD Scenario Contract and Gherkin Exchange](0223_bdd_scenario_contract_and_gherkin_exchange.md), execution-binding follow-up
- [0221: Stable Requirement Identity and Lineage](0221_stable_requirement_identity_and_lineage.md), exact historical references
- [0019: Spec-to-Code Trace Plane](0019_spec_to_code_trace_plane.md), linkage and coverage distinctions
- [0047: Evidence-Backed Build Protocol](0047_evidence_backed_build_protocol.md), reviewed implementation handoff
- [0058: Feature Runtime Evidence Layer](0058_feature_runtime_evidence_layer.md), external evidence ownership

## Problem

The Zeusus legacy sprite pilot needs a snapshot assertion explicitly bound to a
scenario, together with the SpecificationCore evaluations that precede rendering.
A test name containing a spec ID cannot preserve structured identity, exact
source pins, nested composition, execution provenance and artifact integrity.
Copying IDs into trace names also leaves the assertion and its actual test-runner
outcome unconnected. Existing evaluation tracing is useful input, but is not a
test execution or evidence-admission protocol.

The operator proposes composition: a test establishes context, nested
specifications add their own bindings, assertions attach outcomes/artifacts, and
the entire metadata lineage survives export. This proposal defines that seam.

## Proposed Contract

### 1. Composition and ownership

`SpecificationTest` is a candidate API name for a test execution composition,
not a new Boolean domain predicate. A provider-neutral descriptor identifies the
test and its declared verification targets. An execution scope combines that
descriptor with run provenance, a scoped evaluation recorder and an observation
sink. Evaluation, assertion and artifact nodes retain explicit parentage:

```text
test execution / attempt
  ├─ specification composition
  │    ├─ bound rule evaluation
  │    └─ bound rule evaluation
  └─ snapshot assertion
       ├─ actual image digest
       └─ baseline image digest
            ↓
     producer test observation
            ↓
     FeaturePassport adapter / existing admission policy
            ↓
     SpecGraph evidence projection
```

The expression tree describes evaluation. The execution tree describes test
steps and artifacts. Correlation connects the two without equating their
semantics or forcing every test step to implement `Specification`.

Cross-tree correlation uses a stable, producer-assigned `correlation_id` on each
rule-evaluation-to-assertion edge. The edge also names its source evaluation,
target assertion, relation (for example, `supports` or `contradicts`) and
applicable obligation binding. IDs are unique within the immutable execution
attempt and are preserved in the export closure; consumers MUST reject dangling
or conflicting edges rather than infer correlation from shared ancestry,
target IDs, names or timestamps. One assertion may cite several evaluations,
and one evaluation may inform several assertions.

| Owner | Responsibility |
| --- | --- |
| SpecificationCore | Provider-neutral rule bindings and compositional trace context; optional test-support surface whose packaging is reviewed in its repository. Core predicates stay independent of test runners. |
| Swift Testing / XCTest adapter | Observe actual assertion/issue and runner completion, manage test scopes, finalize producer test results and artifact references. |
| FeaturePassport | Own observation envelope, implementation/probe mapping and acceptance/receipt policy. A SpecGraph reference remains optional. |
| SpecGraph | Resolve its references and exact source pins, connect scenarios to execution bindings and project evidence under existing gates. |
| Zeusus | Own gameplay/render fixtures, assertions, synthetic images, product bindings and pilot evidence. |

### 2. Identity and metadata lineage

The root records stable test identity separately from run ID, attempt ID and
parameter-case identity. It pins the tested source/build, test descriptor,
environment, adapter version and the exact resolved contract content used by
the run. A retry is a new attempt, not an overwrite of an earlier failure.

Bindings are separate identified records with a subject, a relation and a target.
They support several targets per test and several tests per target. A neutral
target uses a provider key plus adapter-owned locator and resolved revision/digest;
SpecificationCore does not prescribe `ZEU-SPEC-*`, SpecGraph URLs or passport IDs.
Local targets remain usable without a provider. Scenario bindings qualify the
scenario with its immutable workspace identity, owning spec and pinned source,
following the applicable 0221/0223 contracts. Human aliases alone are insufficient.

Every emitted node MUST retain its immutable effective context and binding
lineage. This may be represented inline or by references to context records that
are included in the same export closure. Export cannot require mutable ambient
state to recover metadata. Recorder-local evaluation IDs MUST be qualified by
their execution/recorder scope; they are not durable rule or scenario IDs.

Root provenance cannot be overwritten by descendants. Descendants add scoped
bindings and namespaced, typed annotations; conflicting protected fields produce
a finding. Multiple bindings accumulate by identity with conflict detection,
not dictionary last-write-wins. Root scenario context does not automatically
declare that every descendant verifies that scenario. A rule binding identifies
the rule; an assertion binding declares which obligation it checks.

Declaring a verification target is not evidence that it was verified: each
target projected as verified MUST have at least one completed, successful
assertion binding explicitly addressing that target, with its applicable
evaluation-to-assertion edges and required artifacts present. Missing, skipped,
failed, ambiguous or incomplete assertions leave the target unverified, even
when the root runner outcome is passed. A passing root with no bound assertion
verifies no declared target.

The metadata allowlist and serialization version MUST be reviewed before SDK
implementation. Unknown extension namespaces are retained as opaque bounded
data or explicitly rejected under the selected profile, never silently dropped.
Inherited metadata must remain attributable to the scope that authored it.
Credentials, candidate values and full world snapshots are not recorded by
default; artifacts use explicit capture and product privacy/retention policy.

### 3. Scope propagation and lifecycle

The scope is passed explicitly; task-local propagation may be an ergonomic
adapter for structured asynchronous work. Sibling scopes receive immutable
contexts and cannot mutate each other's bindings. Parallel tests use independent
recorders/sinks. A process-wide default recorder cannot supply formal test scope.
Detached tasks and callbacks crossing an executor/process boundary require an
explicit captured context; absent context produces uncorrelated diagnostics,
not invented parentage or verification evidence.

Test finalization waits for registered child work and runner completion. Work
that may emit attributed events after the wait boundary must hold an outstanding
scope lease; finalization cannot publish a successful observation while any
lease remains open. If an attributable failure or assertion event nevertheless
arrives after closure, the producer emits a superseding invalidation record
with a strictly higher attempt-local revision. Admission consumers MUST use the
latest revision and MUST invalidate any earlier successful observation in the
same attempt; exports include both the prior observation and invalidation in
their closure. Unattributed late events remain diagnostics and cannot be used
as evidence. Cancellation and thrown failures
preserve completed child observations and the actual terminal outcome. A
short-circuited rule remains skipped. Export failure, overflow or dropped required
events marks evidence incomplete; successful test behavior alone cannot hide
collection failure. Buffer/resource limits and sink failure policy are explicit.

Concurrency ordering records causality and scoped sequence; wall-clock timings
and racing sibling completion order are diagnostics. Deterministic comparison
uses the pinned bindings, node roles, outcomes and artifact digests, excluding
run-specific IDs/timings under a reviewed normalization profile. No canonical
digest byte format is invented by this draft.

### 4. Outcomes and evidence strength

Predicate outcomes and test outcomes are different. A specification returning
`false` may be the expected result of a passing rejection test. The runner adapter
must observe assertion issues, including non-throwing Swift Testing failures;
closure return without an error is insufficient to report a passed test.

Evaluation outcomes retain existing satisfied/unsatisfied, selected/no-match,
skipped, error and cancellation distinctions. Test execution preserves passed,
failed, skipped, cancelled and incomplete distinctions. A passing snapshot proves
only its declared fixture, view, camera and comparison policy. It does not prove
an entire gameplay scenario, all device layouts, or the live renderer generally.

Artifact references pin exact bytes, media kind and capture/comparison profile.
Snapshots retain actual and baseline digests, dimensions, camera/viewport and
tolerance policy. Baseline replacement is a reviewed change with its own source
provenance, not automatic recovery from a failing assertion. Missing baselines,
unresolved required targets and unavailable artifacts cannot become verified
bindings. Numeric anchor assertions and renderer images remain different evidence.

The export is a producer observation. A metadata binding, trace, passing test,
valid schema or artifact hash does not issue an accepted receipt. The existing
SpecGraph evidence path requires separate issuance, a pinned receipt, policy,
trust-store and aggregate-decision inputs for `runtime_verified`; the current
`tests_verified` evaluator is unavailable. Therefore this proposal's pilot can
produce and inspect observations but cannot claim that test evidence has
traversed admission. Any future end-to-end pilot must separately implement and
validate those issuance, receipt, decision and trust stages. FeaturePassport
adapters validate declared probe/element mappings and preserve applicability
pins; existing authorities separately evaluate admission. Split/merge lineage
and newer spec revisions cannot silently inherit historical test evidence.

## Zeusus Pilot and Bounded Realization

1. Review this execution-binding seam and prepare a bounded canonical contract
   through the existing SpecGraph process. Do not infer adoption from this PR.
2. In SpecificationCore, review provider-neutral descriptor/context packaging,
   preserve current tracing behavior and add focused propagation/lifecycle tests.
   Choose one runner adapter first; XCTest and Swift Testing stay separate adapters.
3. Bind a synthetic legacy-sprite fixture to `ZEU-SPEC-0024` /
   `ZEU-LEGACY-ANCHOR-001`, pinning the actual workspace identity and source digest
   at execution. Add separate preview/committed evidence for scenario
   `ZEU-LEGACY-ANCHOR-003` only when the fixture exercises both paths.
4. Export producer observations and inspect their mapping without claiming
   accepted or `tests_verified` evidence. End-to-end admission remains blocked
   until issuance, receipt, policy, trust-store, aggregate-decision and test
   evaluator stages are implemented and validated independently.

Synthetic asymmetric images and anchor markers are suitable committed fixtures.
Extracted GOG assets and their golden snapshots remain local-only and outside
distribution/CI. No asset path or numeric sprite selection becomes gameplay spec
semantics. Current Zeusus tests/builds are prior work, not generated evidence of
this proposed contract.

## Proposed BDD Acceptance Cases

These cases specify future checks; none has been executed by this proposal.

| ID | Given / When / Then obligation |
| --- | --- |
| CTX-01 | Given a test with two rule bindings and one snapshot binding, when composed and exported, then each node resolves its original root provenance and local binding without inferring coverage for sibling nodes. |
| CTX-01a | Given several rule evaluations and assertions, when exported, then stable attempt-scoped correlation edges identify the evaluations supporting or contradicting each assertion; dangling or conflicting edges are rejected. |
| CTX-02 | Given two concurrent tests and concurrent children, when evaluated, then run/recorder identities and immutable contexts prevent cross-test leakage while causal parentage survives. |
| CTX-03 | Given a descendant overwrites root build provenance or conflicts with a binding ID, when scope creation is attempted, then an attributed finding prevents a valid bound observation. |
| CTX-04 | Given an expected rejection and an unsatisfied rule, when the assertion confirms rejection, then the test passes; a non-throwing assertion issue instead produces failure. |
| CTX-05 | Given short circuit, thrown failure or cancellation, when finalizing, then executed children and distinct skipped/error/cancelled outcomes survive without fabricated execution. |
| CTX-06 | Given detached work without context or an event after finalization, when collecting, then it cannot inherit a verification binding or alter completed evidence. |
| CTX-06a | Given registered asynchronous work holding a scope lease, when finalization begins, then no success is published until the lease closes; an attributed late failure creates a higher-revision invalidation that consumers must honor. |
| CTX-07 | Given a retry or parameterized case, when recording, then stable test identity and distinct attempt/case identities preserve all prior results. |
| CTX-08 | Given a snapshot with missing baseline, changed comparison policy, missing artifact or overflow/export failure, when emitting evidence, then applicability/incompleteness findings prevent verified snapshot evidence. |
| CTX-08a | Given declared verification targets but no successful bound assertion for one target, when projecting a passing root test, then that target remains unverified. |
| CTX-09 | Given a changed scenario revision, split/merge or unresolved target, when projecting an old passed result, then historical pins remain and no current applicability is inferred. |
| CTX-10 | Given a provider-free test and supported namespaced annotations, when exported and adapted, then metadata survives without a SpecGraph dependency or an accepted receipt fabricated by the producer. |
| CTX-10a | Given producer observations without issuance, pinned receipt, policy, trust-store, aggregate decision and an available test-evidence evaluator, when the pilot reports results, then admission remains unavailable and is not described as complete. |

## Preparation Validation and Remaining Decisions

Run `make proposal-tracking-gate`, `make docc-sync`, registry JSON parsing,
local Markdown-link checks and `git diff --check`. These checks prove document
and tracking coherence only, not SDK propagation or runtime conformance.

Review exact neutral DTOs, relation vocabulary, test-support packaging, runner
issue capture, metadata extension policy, serialization/digest profile and bounded
sink policy in the owning repositories before implementation. A new universal
test DSL, mandatory Cucumber, automatic coverage inference, production storage
and changes to issuer trust/admission are outside this contract slice.
