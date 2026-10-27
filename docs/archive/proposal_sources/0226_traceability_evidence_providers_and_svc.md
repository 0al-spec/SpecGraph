# Source: Traceability Evidence Providers and SVC

## Operator Intent

The operator requested modularity and replaceable providers for the place where
SpecGraph joins implementation/requirement traces to SIB measurements, then said:

> Пиши proposal через супервизор и запускай цикл self-improvement самого SpecGraph

This is authority to prepare the proposal and run a bounded improvement cycle.
It is not a recorded approval of new metric thresholds or canonical semantics.

## Source Inspection

Inspected SpecGraph commit: `3ffde36401dca3fa7da05fff6ec16a78f9b204ed`.

- `tools/supervisor.py::derive_acceptance_coverage`: legacy criteria/evidence and
  linked test mentions produce coarse statuses.
- `tools/supervisor.py::build_spec_trace_index`: collects trace and freshness.
- `tools/supervisor.py::build_metric_signal_index`: gathers subsystems and
  averages acceptance status scores for specification_verifiability.
- `tools/supervisor.py::METRIC_PACK_ADAPTER_INPUT_CATALOG`: SVC input points at
  that existing signal.
- `tools/supervisor.py::build_metric_pack_runs`: copies available signals into
  metric-pack runs and reports missing inputs.
- `tools/metric_pack_registry.json`: package/input metadata.
- `tools/metric_signal_policy.json`: existing scoring and threshold policy.
- `tools/intent_decision_review/report.py` and `sources.py`: exact change and
  declaration coverage; semantic_approval remains false.
- `tools/feature_passports/static-publication-bindings.json` and
  `specs/nodes/SG-SPEC-0071.yaml`: current bounded atom/policy/test inventory.
- `docs/publication_delivery_pilot.md`: PB execution observations and PE tests
  have different observation scopes.
- `Metrics/SIB_FULL/sib_full_metrics.tex`: SVC counts verifiable Intent Atoms;
  aggregate SIB observables do not reconstruct explicit trace links themselves.

The proposed package architecture and SVC qualification profile are author
curation of this evidence and operator intent. They are not attributed as an
independent Supervisor verdict or as already implemented behavior.

## Supervisor Cycle

The first three standalone CLI attempts rejected model IDs before generation.
They ended in protocol failure because no final response was produced. Their
run IDs and raw digests are retained in the [cycle observation](../../reviews/0226_supervisor_cycle.json).
The initial dry run also exposed a lexical child-request heuristic reacting to
a negated instruction; the operator note was reworded without broadening authority.

The standard Supervisor executor callback then ran the real Codex child agent.
After the operator said "Нужно поднять до Sol 6.1 Medium", the previous child was
interrupted and GPT-6.1-Sol / Medium inspected and completed its pending edits.
The actual response passed the unchanged Supervisor protocol and diff validation.

- Run: `20261021T193422Z-SG-SPEC-0021-6ca26a10`.
- Completion: `ok`; outcome: `done`; gate: `review_pending`.
- Validation errors: zero; accepted canonical diff: false; auto-approval disabled.
- [Supervisor-generated curated packet](../../evidence/supervisor-runs/20261021T193422Z-SG-SPEC-0021-6ca26a10.json).
- [Review-only semantic candidate](../../reviews/0226_metric_verifiability_candidate.patch).
- [Transport, failure and candidate digest observation](../../reviews/0226_supervisor_cycle.json).

The candidate distinguishes declared/resolved/executed verification facts,
source/revision/provenance/completeness, failure versus unknown input, and the
limited scope of historical review. Existing acceptance criteria, family roles,
admissible input classes and topology are preserved. The patch is author curation
of the real child output with baseline lifecycle metadata; it has not been applied
to canonical SG-SPEC-0021 in this PR. Local generated pending-review state and raw
runs remain available separately. The packet records a review boundary, not
semantic acceptance or a successful standalone CLI deployment.

The operator-request and captured user-intent nodes emitted by the Supervisor are
retained in `intent_layer/nodes/`. They remain pre-canonical lineage.

## Requested Executor Profile Correction

The shared execution policy now requests `gpt-6.1-sol`; all named profiles retain
`medium` reasoning. The existing isolated-home regression was updated. This is
the operator's explicit configuration correction; it does not establish that the
standalone CLI backend now accepts the requested model. The successful run used
the injected executor transport described above.

## Proposal Boundary

Continue proposal 0043's existing metric-pack architecture. The draft is a
SpecGraph-owned integration proposal. Runtime implementation and metric-profile
activation remain follow-up slices requiring review.

## Bounded Compatibility Extraction

After merging PR 782, the operator asked to start implementation and noted that
the metric tools were ready. The first slice extracts the current proxy under
`tools/metric_packs/`, with immutable prepared facts and an explicit
`verifiability_metric` composition hook. A named score-status Specification is
reused through the existing Supervisor facade.

Eight fixed-input JSON projections were captured from the exact production block
at `2e33ce2d51b01080f25e592c9232185e01004d34` before editing it. They include
unknown/malformed statuses, numeric coercion, empty input and threshold rounding.
The fixture records the source digest; tests compare complete serialized entries.
CLI/isolated import and injected-composition checks exercise the actual module
boundary. The trusted PR metrics workflow supplies the separate code-shape and
S/U measurements; compatibility tests do not establish metric improvement.

This is implementation of the existing behavior, without applying the semantic
candidate above or activating a new SVC qualification profile. Evidence providers,
the general TraceSnapshot and metric-profile migration remain subsequent slices.

## Exact-link prerequisite authorized on 2026-10-22

After the Zeusus observability feedback triage, the operator authorized an exact
reference resolver for the existing publication pilot. The bounded deliverable
is a pinned source-declaration diagnostic, before EvidenceProvider/TraceSnapshot
and atom SVC integration. It does not depend on the compatibility extraction PR.

The six intake observations distinguish identity vocabulary omissions, missing
mapping-reference validation, executor tool locations, a quoted-source transport
false positive, retained candidate lifecycle drift and a correctly rejected
operator target-count error. This slice addresses exact references and preserves
source lifecycle explicitly. The other runtime/authoring seams remain separate.

The implemented profile is `specgraph.publication-exact-links/v1`; its public
contract is [Exact publication trace links](../../publication_trace_links.md).
The common resolver has small synthetic regressions inspired by Zeusus's
nonexistent obligation, scenario ranges and missing planned target. No Zeusus
source is adopted, no whole-product adapter is claimed, and no gameplay test is
executed by this work. Identity aliases remain product/profile-specific.

The [pinned observation](../../evidence/0226_publication_link_resolution.json)
records 13 unique atoms and 55 resolved link occurrences at one Git revision.
It establishes direct declaration resolution, not fulfilled intent, runtime
confirmation or canonical approval. The SG-SPEC-0021 semantic candidate remains
separate and unapplied.

## Declaration provider authorized on 2026-10-22

The operator requested green-check/review merges of PRs 784 and 785, followed
by EvidenceProvider work. PR 785 merged as `58bbf297`; after preserving both
realization notes, current CI and a successful replacement HyperReview, PR 784
merged as `24004833`. The failed automatic gate was released by the review
service after replacement completion, without a merge bypass.

Slice C1 implements an explicit in-process provider Protocol/registry and a
declaration-only immutable TraceSnapshot on that merged base. Publication source
collection happens once. The existing diagnostic remains compatible; metric
qualification, execution artifacts, viewer migration and the SG-SPEC-0021
semantic candidate remain separate. See [EvidenceProvider](../../evidence_provider.md)
and the [pinned observation](../../evidence/0226_publication_provider_snapshot.json).

Slice C2a subsequently adds `PublicationExecutionEvidenceProvider` for explicitly
selected retained tests/delivery reports and a complete selected GitHub Actions
identity. Source manifests are checked against Git objects at the artifact's
actual revision; nested observer/runtime bindings and original producer outcomes
stay distinct. Real build artifacts from run 39757869156 attempt 1 retain five
successful pytest obligations and missing deploy/runtime signals. They used PR
merge-checkout SHA `5ccf69e8ad5da8a82b63c035090ebfbf5481c4f0`, not the branch head.
No tests/network/inference are executed by this provider. SVC qualification,
trusted admission, canonical semantic changes and viewer activation remain
separate. See the [execution observation](../../evidence/0226_publication_execution_snapshot.json).

## Recovered boundary clarification prepared on 2026-10-27

PR #809 retained the source-grounded recovery review and v2 semantic candidate;
it merged as `8945b021c49fbc08f50da8b93db9ba53d530e4d8`. After the operator
requested merging PRs #807–809, the next proposed task was to prepare a focused
PR applying that candidate to SG-SPEC-0021. The operator replied “Подготовь”.
This authorizes preparation of the canonical-spec PR, not a claim of final
semantic approval or profile activation.

The prepared change applies the v2 semantic delta to the current node and
updates its modification timestamp. Existing acceptance criteria, family roles,
subject/input classes, invariant IDs and lifecycle fields are preserved. The
[recovery review](../../reviews/0226_metric_verifiability_recovery_review.md)
and [v2 patch](../../reviews/0226_metric_verifiability_candidate_v2.patch)
remain historical review artifacts. The patch SHA-256 is
`df8f1bc4037a698ddf4fb57630b5b2ee6bbf4409a768577ba1797fde34c37728`.

No Supervisor executor or old gate resolution is needed to reapply that bounded
delta. No new metric profile, direct derived-input admission, threshold, writer
permission or trusted-evidence claim is introduced. The current Intent Atom
profile does not count `boundary_notes`; an unchanged count does not mean that
these five semantic clarifications are absent.
