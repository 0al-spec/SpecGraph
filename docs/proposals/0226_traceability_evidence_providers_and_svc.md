# 0226 Traceability Evidence Providers and SVC

RFC: SG-RFC-0226
Version: 0.1.0

## Status

Draft proposal; architecture and staged realization plan for review.
Compatibility slice B now extracts the existing proxy behind immutable prepared
inputs and a replaceable metric interface. Slice C1 now exposes a declaration-only
EvidenceProvider and immutable TraceSnapshot for the publication pilot. Slice C2a
reads explicitly selected retained execution reports. Atom-level SVC and profile
activation remain `deferred_until_canonicalized`. The bounded
Supervisor cycle and its evidence are recorded in the source draft. This work
does not activate a metric profile, replace the existing proxy, or approve a
canonical semantic change.

The recovered SG-SPEC-0021 boundary clarification merged through PR #810 as
`b4d0f25e`, using the v2 candidate retained by PR #809. Its notes preserve the
existing input classes and distinguish cited observations, completeness,
negative results and historical scope. Atom-SVC qualification and direct
derived-input admission remain separate decisions.

C2b now has a [candidate qualification contract](../pytest_channel_qualification_profile.md),
six explicit [draft obligations](0226_traceability_evidence_providers_and_svc.intent.yaml)
and a [pinned reference worksheet](../evidence/0226_c2b_reference_worksheet.json).
This defines the proposed rules; a runtime qualifier is not implemented or
activated by this contract-only slice.

C2c now has a bounded [retained Cucumber provider](../evidence_provider.md#retained-cucumber-criterion-observations-c2c)
and opt-in report CLI. The earlier local pilot and its limits remain in the
[source record](../archive/proposal_sources/0226_criterion_observation_report.md).
The implemented profile reads one complete pinned specification inventory and
one run per journal with an explicitly selected case and attempt. Trusted
admission and profile activation remain
deferred.

```yaml
canonical_mutations_allowed: false
runtime_profile_activation_allowed: false
evidence_admission_allowed: false
```

## Source Material

- [Operator intent, source inspection and Supervisor cycle](../archive/proposal_sources/0226_traceability_evidence_providers_and_svc.md)
- [0043 Metric Pack Plugin Architecture](0043_metric_pack_plugin_architecture.md)
- [SG-SPEC-0021: Derived Metric Family Boundary](../../specs/nodes/SG-SPEC-0021.yaml), primary semantic target
- [SG-SPEC-0020: Executable Layer Traceability Boundary](../../specs/nodes/SG-SPEC-0020.yaml), executable anchors and outcomes
- [SG-SPEC-0071: Publication delivery pilot](../../specs/nodes/SG-SPEC-0071.yaml), first bounded cohort
- [Intent decision review](../intent_decision_review.md), historical change dispositions
- [Publication delivery pilot](../publication_delivery_pilot.md), current test and HTTP observations
- [0221 Stable Requirement Identity](0221_stable_requirement_identity_and_lineage.md)
- [0225 Tests-Verified Evidence Admission Plan](0225_tests_verified_evidence_admission_plan.md)
- [Supervisor cycle observation](../reviews/0226_supervisor_cycle.json) and [review-only semantic candidate](../reviews/0226_metric_verifiability_candidate.patch)

## Problem

SpecGraph already has a declarative metric-pack registry and adapter index, but
its verifiability input is still a bootstrap proxy. In the inspected main
snapshot, `build_spec_trace_index` derives legacy `acceptance_coverage` and
`build_metric_signal_index` averages scores assigned to those statuses. The
input catalog labels that result `spec_verifiability_coverage`. Pack runs copy
existing metric signals; registration alone does not execute a new provider.

The publication pilot now has explicit atom IDs, real test selectors, named
Specifications and revision-bound observations. Intent decision review records
bind changed obligations to exact source declarations. These sources have
useful but different meanings and are not joined into an atom-level SVC input.
Adding all collection, mapping and scoring to `tools/supervisor.py` would
increase coupling in an already large orchestration function.

## Goal and Scope

Introduce replaceable evidence sources, a shared immutable trace snapshot and
independent metric interpretations. Use the publication pilot to characterize
the boundary before broad adoption. Preserve existing CLI/Make entry points,
legacy proxy values and viewer contracts during extraction.

Scope is SpecGraph's evidence-to-metric integration. Metrics owns research
formula definitions. SpecificationMetrics owns its separate source-code
analyzers. Neither repository requires a change for the first SpecGraph slice.
The snapshot is a derived read model; it does not add canonical graph kinds or
claim that source declarations prove behavior.

## Proposed Architecture

```mermaid
flowchart LR
    Y[YAML atoms and bindings] --> P[Evidence providers]
    C[Exact source declarations] --> P
    T[Existing CI and delivery artifacts] --> P
    R[Historical decision records] --> P
    P --> S[Immutable TraceSnapshot]
    S --> M[SIB metric adapter]
    S --> D[Traceability diagnostics]
    M --> O[Existing metric artifacts]
    D --> Q[Review findings]
```

### 1. EvidenceProvider

A provider reads one explicitly selected source and returns typed facts plus
source provenance and completeness. Collection receives an explicit repository,
revision, bounded subject selection, artifact selection and profile. It does not
implicitly read process-wide roots, select an arbitrary latest report or run
tests to create its own evidence.

The first implementation uses an explicit in-process registry of reviewed
provider implementations behind one Python `Protocol`. Selection is declarative;
provider IDs and configuration versions are included in provenance. Unknown or
duplicate IDs are configuration errors. Provider order cannot change results.
Dynamic import strings, directory auto-loading, network services and subprocess
plugin discovery are deferred until a concrete second integration requires them.

Initial sources reuse existing parsers and artifacts: canonical atoms and
`verifiable_by`, exact Python declaration resolution, publication bindings,
existing test/delivery reports, and intent review records. They are capability
roles, not a requirement to introduce five implementations in the first PR.

### 2. TraceSnapshot

The snapshot carries an explicit subject set and these separate fact classes:

- **Declared link:** an authored obligation names a verification channel or
  implementation anchor.
- **Resolved link:** the selected declaration or check is resolvable at the exact
  measured source revision under the named resolver profile.
- **Execution observation:** a selected producer reports execution for explicit
  target bindings, source and invocation identity.
- **Result:** success, failure, skipped, missing or another producer-defined
  outcome with its original meaning retained.

Every fact has source references/digests, provider identity/version and its
subject/revision binding. Existing obligation addresses are reused, including
node ID plus explicit atom ID where currently available; a whole-file reference
must not impersonate an exact criterion revision. Stable Requirement identity
from 0221 can be consumed where present without imposing a new ID migration.

Facts are immutable, including nested collections. Multiple provider reports for
the same authored link preserve their origins without counting the atom twice.
Conflicting reports remain explicit; an arbitrary provider order cannot select a
winner. Snapshot identity is deterministic for the same selected inputs;
collection timestamps remain metadata outside that content identity.

Completeness is scoped to a capability and subject set. Missing optional
execution data does not invalidate a complete declaration-resolution inventory.
Incomplete atom enumeration makes an exact SVC denominator unavailable. A stale
or invalid required source never becomes a successful observation or an empty
complete inventory. Partial findings and missing-input diagnostics remain
available when an exact value is unavailable.

A decision review record is historical coverage of a base/head change. Providers
must retain those pins and the PR-body context. It is not perpetual confirmation
of later source code. Reusing its declarations requires resolving them at the
measured snapshot, and never upgrades `covered` to semantic approval.

### 3. Metric Adapter and Checks

Metric adapters are pure interpretations of a prepared snapshot and a versioned
metric profile. They perform no collection, execution or publication. Trace
checks consume the same facts independently and report missing, ambiguous or
stale links. Any decision about blocking CI remains in an explicit reviewed
policy, separate from the measurement.

For the first candidate SVC profile:

- The denominator is the complete selected Intent Atom inventory.
- The numerator counts each atom at most once when at least one operational
  verification channel has a valid, resolved binding under the profile.
- For Python bindings, merely providing a nonempty string does not qualify.
- A completed failing check can establish structural verifiability; retain its
  test failure separately. This profile does not evaluate fulfillment. SVC must
  not silently become the pass rate.
- Missing or stale execution remains visible independently of a structurally
  valid verification channel.
- Empty subject selection yields `not_applicable` with no ratio in this profile;
  incomplete denominator yields `not_computable`, not zero. This convention must
  be explicit in the profile rather than changing the research formula silently.

The qualification rule is a proposal for review; it is not activated here and
does not establish that a test is semantically sufficient. Distinct declaration,
resolution and execution counts accompany the ratio. `tests_verified_v1`, trusted
receipt admission, runtime verification and product outcome remain separate.

The C2b profile makes channel and atom qualification three-valued: `qualified`,
`unqualified` and `unknown`. An uncontested good alternative is sufficient;
otherwise unknown alternatives prevent a negative conclusion. An exact fraction
requires a complete selected atom inventory and no unknown atom qualifications.
The profile resolves links statically and does not prove pytest collection or
execution. Its six draft obligations cover pins, channel/atom decisions,
computability, conflict handling and separation from execution/admission.

Stable eligibility and interpretation policies should use named SpecificationCore
specifications with immutable contexts, each in its own module. Parsing, Git and
artifact I/O remain procedural adapters. Do not introduce specifications only to
increase the S counter.

### 4. Composition and Compatibility

The composition root selects providers and metric adapters explicitly. It
collects once for the selected snapshot, then passes facts to calculations and
checks. A provider may supply several metrics; a metric may require several
provider capabilities. Required and optional capabilities are declared rather
than inferred from file presence.

Proposed package boundaries live under `tools/traceability/` and
`tools/metric_packs/`; exact filenames are an implementation decision. Existing
`tools/supervisor.py` commands remain façades. Existing registry/index surfaces
continue to describe source and computation readiness. An available adapter
contract alone does not imply successfully collected inputs or a computed value.

The new atom-level result uses its own profile ID/version and input digests. The
legacy `specification_verifiability` proxy and its thresholds remain unchanged
until an explicit migration is reviewed. Historical values from different
profiles cannot be presented as one comparable trend without qualification.

## Bounded Self-Improvement Cycle

1. **Observe:** pin the current implementation and publication bindings; identify
   the proxy-versus-atom input gap.
2. **Propose:** capture the operator request and run one bounded Supervisor pass
   on SG-SPEC-0021; retain the actual outcome and validation, including failures.
3. **Review:** curate this architecture and any semantic candidate with source
   provenance. Supervisor execution does not constitute human approval.
4. **Improve tools:** after the bounded contract is reviewed, extract the existing
   computation behind an unchanged façade, then add the publication provider and
   candidate SVC profile in separate focused PRs.
5. **Observe again:** compare the legacy proxy and the new detailed result for
   SG-SPEC-0071 at one pinned revision; inspect disagreements and negative cases.

The original proposal completed preparation and launched the bounded Supervisor
cycle. The operator subsequently requested implementation, authorizing the
compatibility extraction in slice B. Declaration provider runtime is implemented
in C1; C2a adds retained execution-artifact inputs. Atom-level SVC remains future
work. The recovered v2 semantic patch merged as a bounded refinement of
SG-SPEC-0021 through PR #810. The [recovery review](../reviews/0226_metric_verifiability_recovery_review.md)
and [v2 patch](../reviews/0226_metric_verifiability_candidate_v2.patch) retain
their original scope and provenance; no historical run gate is replayed.

## Realization Slices

| Slice | Deliverable | Verification |
| --- | --- | --- |
| A | Reviewed provider/snapshot/profile contracts and semantic input boundary | Source-grounded review and explicit compatibility decisions |
| B | Implemented: extract existing verifiability computation with immutable prepared inputs and the optional `verifiability_metric` hook | Pre-refactor JSON fixtures, shared-policy boundaries, injectable composition and isolated imports |
| C1 | Implemented: publication declaration EvidenceProvider, explicit registry and immutable TraceSnapshot | Pinned inventories, partial/missing sources, duplicate/conflicting reports and independent CLI |
| C2a | Implemented: explicit retained publication tests/delivery artifacts and run binding | Existing producer contracts, exact Git file inventory/run/attempt, negative nested provenance cases and a real CI artifact |
| C2b | Proposed structural test-channel qualification contract; runtime qualifier pending | Decision tables, 16 proposed acceptance cases and a pinned 13-atom / 18-link reference worksheet; execution remains separate |
| C2c | Implemented diagnostic slice for one full pinned criterion inventory and retained Cucumber Messages 34.2.1, an explicitly selected case without retries | Independent synthetic fixtures cover exact source/run/step/measurement joins, failed/partial evidence and conflicts; native passport checks run with an explicitly supplied validator |
| D | Connect to existing metric-pack artifacts with explicit provenance | Consumer compatibility, profile-separated comparisons and one real pilot |

Each slice has its own focused PR. Failure or incompleteness stays visible;
activation does not follow automatically from merging the proposal.

## Implemented Compatibility Boundary (Slice B)

`tools/metric_packs/` now contains `VerifiabilityContext`, immutable observations
and results, the `VerifiabilityMetric` protocol, and `LegacyVerifiabilityMetric`.
The legacy JSON adapter prepares the input; the metric performs pure arithmetic
and projection. `SCORE_STATUS_SPEC` names the existing three-way threshold
policy and is also used through the existing Supervisor score-status facade.

`build_metric_signal_index(specs, *, verifiability_metric=None)` selects the
legacy implementation by default. Supplying another implementation of that
protocol is an explicit composition hook; it receives the same prepared context.
This specialized input is not the proposed general TraceSnapshot, and no dynamic
plugin loading or new metric profile is enabled.

The extraction preserves unknown-status counting, numeric coercion, empty-input
behavior, rounding before threshold comparison, the complete serialized metric
entry and existing threshold consumers. Eight golden projections were captured
from the exact pre-refactor production block at commit
`2e33ce2d51b01080f25e592c9232185e01004d34` before editing it. They are retained in
`tests/fixtures/metric_packs/legacy_verifiability.json`; focused tests also check
immutable inputs, trace branch skips, shared score policy, injected composition
and isolated file imports.

A live local trace snapshot of 71 spec entries also produced identical serialized
entries before and after: the legacy proxy stayed at 0.993 (70 `covered`, one
`evidence_linked_unmapped`). This is an acceptance-status proxy, not atom-level
SVC or confirmation that 99.3% of requirements passed tests. The pinned
[compatibility observation](../evidence/0226_legacy_verifiability_compatibility.json)
records both results and source digests.

TP-08 now has compatibility characterization. C1 adds declaration-provider
characterization; C2a adds retained execution observations. Atom-level metric portions below remain planned.
Measurement results and local observations are reported
with the implementing PR; no complexity or S/U improvement is presumed.

## Acceptance Cases for Future Realization

The [EvidenceProvider contract](../evidence_provider.md) describes implemented
slice C1 and retained execution slice C2a. C1 consumes one exact-link collection without changing the diagnostic
facade. Typed scope checks, capability-specific completeness, immutable nested
facts, deterministic identity, duplicate subject coalescing and explicit atom/link
conflicts have focused tests. The [pinned snapshot observation](../evidence/0226_publication_provider_snapshot.json)
records the actual declaration inventory. The [execution observation](../evidence/0226_publication_execution_snapshot.json)
binds real retained CI pytest results while leaving skipped deploy/runtime missing.
SVC qualification, generalized execution-event collection and trusted admission
remain future work in the cases below.

| ID | Case | Expected result |
| --- | --- | --- |
| TP-01 | Atom names a nonexistent test | Declared link retained, resolution fails, atom excluded from qualified numerator |
| TP-02 | Bound test completes with failure | Structural qualification retained; observed test failure stays separate from fulfillment evaluation |
| TP-03 | Optional execution report absent | Resolution-based SVC remains computable; execution observation missing |
| TP-04 | Required inventory incomplete or stale | Exact ratio unavailable; diagnostics and partial facts retained |
| TP-05 | Historical review cites an earlier implementation | Historical pins retained; current resolution required; no approval inference |
| TP-06 | Two providers repeat one link or disagree | One atom counted once; provenance and conflict preserved; order-independent result |
| TP-07 | New provider added | Existing profile and consumer behavior unchanged; no edit to SVC formula required |
| TP-08 | Existing proxy extracted | Fixed-input values, statuses and serialized public fields remain unchanged |
| TP-09 | Code changes while intent is unchanged | Current resolution/freshness reflects selected source; no reuse of stale confirmation |
| TP-10 | Empty selected atom set | Explicit not_applicable result, no invented zero coverage |

TP-08 has executable compatibility characterization in slice B. C1 tests the
provider declaration/scope, missing-input, order and conflict boundaries; C2a
tests producer outcomes, selected revision/run/attempt, nested runtime provenance
and explicit missing signals. Metric qualification remains future work.
Local checks and observations are
reported separately in the implementing PR.

## Open Decisions for Review

- Review `specgraph.pytest-channel-qualification/v1`, including three-valued
  qualification and empty/incomplete conventions, before runtime implementation
  and any later non-Python extension or default metric activation.
- Select the minimal existing artifact inventory consumed by the first provider.
- Decide the additive result field/schema version for existing viewers in slice D.
- Review any Supervisor semantic candidate independently of this tooling design.

## C2c: Criterion observation report

### User-visible result

Given a selected specification and an explicit evidence package, the author
sees every selected acceptance criterion, its declared test binding, the
observed test step and measurement, and any missing or inconsistent inputs.
The report answers **what was observed for this criterion, at which inputs?**
It does not answer whether the criterion is semantically sufficient or admitted.

One author-curated example of the intended presentation is:

| Criterion | Observed step | Measurement | Binding / observation |
| --- | --- | --- | --- |
| Returning an issue closes it | Press using the returned issue | calculation count 1 → 1; result unknown | checked / passed |
| A late return preserves a newer issue | Press using the newer issue after the old return | count 2 → 3; result available | checked / passed |
| A new issue works while the returned issue stays closed | New-issue press, then old-issue press | 1 → 2 available; 3 → 3 unknown | checked / passed |

These are summarized local pilot observations, not executable fixtures or
SpecGraph output. Every actual row retains machine-readable criterion, source,
passport, plan, provider, run, attempt, step and artifact identities. A missing
journal would retain the row with unavailable observation, not reuse this table.

### Ownership and integration seam

- [0224](0224_compositional_test_context_and_evidence_binding.md) supplies the
  producer-side binding and execution-context direction. The first adapter is
  bounded to a declared Cucumber Messages profile; its support matrix must be
  explicit. Other runners remain replaceable producers, not new requirements
  on how a person phrases intent.
- FeaturePassport owns provider-neutral feature/passport/criterion identities,
  implementation bindings and the generic receipt contract. A SpecGraph locator
  stays inside an optional provider-owned contract reference. Validate the
  passport against its pinned supported schema and preserve its draft status.
  Do not invent an L0–L8 level for local tests or embed SpecGraph identity rules
  into the generic passport schema.
- SpecGraph owns exact spec/criterion resolution and the derived report through
  the explicit `EvidenceRegistry` / `EvidenceProvider` / `TraceSnapshot` seam.
  Add a reviewed typed criterion-observation selection and facts; the existing
  `PublicationExecutionSelection` and SG-SPEC-0071-specific providers do not
  already accept arbitrary passports or Cucumber journals. Preserve their
  contracts and keep parsing/I/O in the adapter, report decisions in named
  policies over immutable facts. No dynamic plugin loading is proposed.
- [0225](0225_tests_verified_evidence_admission_plan.md) remains the separate
  path from observations and FeaturePassport receipts to claim admission.
  C2c neither issues receipts nor creates a second acceptance authority.

### Explicit inputs and output boundary

The standalone report request selects one workspace/repository,
spec ID, exact source revision, criterion inventory, passport revision/digest,
binding-plan revision/digest, adapter ID/version/profile, and retained artifact
paths with digests and run/attempt identity. Paths alone and mutable `latest`
selection are insufficient. File ingestion is read-only and bounded to the
explicit allowed inputs; it must not execute code or commands from artifacts.

Criterion identity includes its owning spec, exact source revision, file digest
and pointer, with a stable local criterion ID when available. A list index
alone cannot identify a criterion across edits. Preserve distinct declaration,
test-source and execution-source revisions; prove their compatibility under the
selected profile rather than requiring their commits to be numerically equal.
Keep source-build linkage labeled `producer_declared` unless independently
established. Matching bytes and a successful run do not establish attestation.

The expected criterion set comes from the pinned specification inventory, not
from whichever evidence files are present. Every criterion gets a row, including
unbound, unavailable and failed cases. If an explicit subset is selected, label
that scope and list exclusions; do not call it whole-spec coverage. For every
criterion the pinned binding plan declares the expected observations/assertions;
a passing subset cannot satisfy that declared set. Reviewing that plan's semantic
sufficiency remains a human/agent task, not a consequence of structural validity.

The additive derived `criterion_observation_report/v1` is available through
`tools/criterion_observation_report.py` with the documented profile. It retains
request/plan/provider/source digests, original lifecycle, full findings and
separate axes for **binding integrity**, **observed outcome** and **admission**.
Checked binding can accompany a failed test. Missing evidence is unavailable;
malformed or inconsistent evidence is invalid; conflicting facts stay visible.
None of these may become a passing observation through text similarity.

An optional `--format html` presents the same freshly collected report as a
standalone local page. It displays all criteria, selected measured steps,
expected/observed values and findings, with exact identities in expandable
details. Missing measurements retain expectations; an incomplete inventory has
an unknown total. JSON stays the default. The view formats existing decisions
and does not reconstruct the full scenario, infer source URLs, reinterpret
intent or confer trust. See the [readable report contract](../evidence_provider.md#readable-local-report).

Repeated agreeing records do not multiply criteria. Conflicts cannot be
resolved by arrival order or selecting a convenient passing retry. Attempt
selection and run-completion policy are explicit; unsupported retries,
versions or unresolved selections remain unavailable. Partial/failed runs
retain observations and findings but cannot be represented as wholly passed.

The first report is diagnostic: `scope: local_test`, admission `not_evaluated`
and no receipt. The proposed envelope is a derived observation view, not a
FeaturePassport receipt format. It changes neither legacy `acceptance_coverage`
nor C2b structural SVC, S/U, canonical status, UI defaults or CI merge policy.
The ASCII-only legacy coverage heuristic is a separately observed defect;
C2c uses exact identity and pointers and does not hide it by translating specs.

### Acceptance controls for implementation

These controls define the bounded implementation checks. Independent synthetic
fixtures live in `tests/test_criterion_observation_provider.py`. The native
FeaturePassport checks require the operator-supplied validator:

| ID | Input/control | Expected report |
| --- | --- | --- |
| CER-01 | Three pinned criteria, valid passport/plan and matching completed run observations | Three rows retain exact step identities and measurements; admission remains not_evaluated |
| CER-02 | Journal absent from a fresh checkout, although a previous report says passed | Explicit unavailable row; no inherited success |
| CER-03 | Wrong source, passport, plan or journal digest | Invalid affected binding; mismatched inputs remain identifiable |
| CER-04 | Foreign run/case/step, or a modified measurement projection with a newly computed projection hash | Reject the join against the authoritative selected journal |
| CER-05 | A declared observation is missing, failed, skipped, pending or belongs to an unfinished/unsupported attempt | Preserve outcome/diagnostic; criterion is not wholly passed |
| CER-06 | A criterion is unbound, duplicated, or omitted from input evidence | Keep complete inventory, detect duplicates and show the gap; no smaller denominator |
| CER-07 | Same facts repeated in a different order, then conflicting outcomes supplied | Agreeing duplicates are idempotent; conflicts remain visible and order independent |
| CER-08 | Russian criterion text and unrelated English keywords | Exact identity/text/source checks work without lexical coverage inference |
| CER-09 | Correct FeaturePassport envelope with a wrong binding target or test role | Native passport validation fails; no collection success is inferred from envelope presence |
| CER-10 | Complete successful local observations without independent source attestation or trusted receipt | Producer-declared provenance stays explicit; no tests_verified, runtime_verified or receipt |

The local ExamCalc prototype demonstrated one concrete three-row output and
nine adapter controls plus three passport-validation controls. It does not
demonstrate every control above, a general 0224 implementation, or C2c integration.
Its raw artifacts remain local-only; source records state their availability.
The implemented provider uses independent synthetic inputs. Subset selection,
selected-case retries, alternative producers, general 0224 bindings and
trusted admission remain separate follow-ups.

### Bounded next implementation

1. Review the input/row contract and expected binding plan against the pilot;
   retain this proposal's authority boundaries and named draft obligations.
2. Add the minimal typed selection/facts and a single explicit retained-test
   provider behind the existing registry. Use independently committed synthetic
   fixtures; public CI must not depend on the local ExamCalc checkout.
3. Add the diagnostic projection and the controls above, then repeat the local
   consumer pilot using the native SpecGraph entry point. Retain missing inputs
   and unsupported cases; do not infer that the old local adapter is activated.

The receipt/admission step is deferred to 0225. A useful local observation report
does not require implementing trusted receipt infrastructure first.

## Authority and Non-Goals

Metrics remain diagnostic. This proposal changes no merge thresholds, graph
lifecycle, canonical acceptance, runtime claims, S/U counting or receipt trust.
There is no automatic policy adoption, whole-project gate, new canonical graph
kind, generalized middleware runtime or mandatory instrumentation framework.
