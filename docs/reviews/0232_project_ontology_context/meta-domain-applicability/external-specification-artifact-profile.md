# External specification artifact profile — design candidate

This is a proposed consumer contract under SG-SPEC-0072 and proposal 0232.
Profile ID: `specgraph-external-specification-artifact-v1`.
It describes a document handled by SpecGraph, separately from the product that
the document describes. It does not add a vocabulary authority or ontology package.

```yaml
status: design_candidate
runtime_implemented: false
applicability_approved: false
canonical_mutations_allowed: false
global_policy_activation_allowed: false
```

The operator authorized preparation of this contract after the applicability
audit, not activation or publication of a metamodel. [Source notes and static
characterization](external-profile-source-notes.json) bind the request, inspected
inputs and GitView example. The [consumer closeout](consumer-closeout.json)
remains evidence for the earlier mixed-warning fix, not execution of this profile.
The original proposal, canonical specs and historical review packets are unchanged.

## Purpose and applicability

The proposed interpretation is: the document may be represented as an
`sgcore:Spec`; GitView's Project, Repository and other product concepts continue
to resolve only against its selected `domain_vocabulary` context. A document
about GitView does not make GitView a `specgraph_core` product domain.

The candidate metamodel source is the existing local draft
`org.0al.specgraph.core@0.1.0`, namespace `sgcore`, source SHA-256
`5bfa2ff40b6174def589546ab2fea2501e1f256c4f1446f36c45c7f3fffcd929`.
Its authored `modelApplicability` names `specgraph_core`, excludes
`unrelated_product_domain`, and retains `project_local_authority`. Those facts
must be preserved from compiler IR using the existing Ontology vocabulary.
This document does not edit, override or widen them.

Before activation, review must explicitly resolve whether processing an external
specification **artifact within SpecGraph** fits that authored scope. A contrary
or unresolved disposition leaves this profile unavailable. Neither `kind: spec`,
successful compilation nor the profile's presence supplies that decision. If the
source's declaration needs changing, propose that separately; an adapter cannot
silently waive an exclusion. The decision concerns this bounded interpretation,
not acceptance of GitView's domain model or trusted publication of sgcore.

This is one profile-level review and an explicit operation/workspace selection,
not a new per-file approval ceremony. No signatures or approval registry are
introduced by this proposal. Ontology ONT-040 applicability metadata remains
review data, not an application-specific evaluator or runtime permission.

## Inputs and evidence binding

An eventual operation needs:

- Explicit `specification_metamodel` request and this selected profile/revision.
- A captured metamodel context with exact package identity/version, source and
  IR hashes, compiler identity and declared checking profile. The compiler pin
  alone does not select the metamodel.
- The captured applicability metadata and the source-bound disposition above.
- Exact document bytes/digest, normalized workspace-relative path, document ID
  and a mapping revision. ID/path agreement and path confinement retain their
  existing checks; an ID is not evidence of graph membership or acceptance.

Metamodel context and domain context occupy separate report roles. Reuse the
existing capture machinery; do not add sgcore to GitView's domain package set
or export its unqualified symbols into domain resolution. A domain context is
not required for a meta-only request. No CLI selection flag or physical manifest
schema for these proposed inputs exists yet.

## Field mapping and bounded checks

| Document input | Proposed interpretation/check | Boundary |
| --- | --- | --- |
| Explicit artifact mapping plus `kind: spec` | Candidate representation as `sgcore:Spec`; check that the selected metamodel exports the class | Neither inference from the product vocabulary nor semantic approval |
| `id` and captured source path/digest | Identify the document being checked using existing project ID/path rules | Do not infer `sgcore:Node`, graph membership or canonical acceptance |
| `acceptance[]`, when explicitly selected and present | Each declared occurrence is an AcceptanceCriterion candidate; check `hasAcceptanceCriterion` endpoints against Spec/AcceptanceCriterion | Preserve field location; do not judge natural-language satisfiability |
| `acceptance_evidence[]`, when explicitly selected and present | Evidence candidate and `evidenceSupportsCriterion` only for an explicitly resolved criterion reference | A list or matching type alone does not establish support, execution or `tests_verified` |
| `status`, `draft_status` | Preserve authored values; do not map implicitly to `SpecReviewState` | Review state and authoring maturity/canonical status are separate dimensions |
| `specification.review_examples`, free prose, `sources` | Outside this first structural mapping | No implicit conversion to criteria, Intent instances or verified evidence |

Class/relation lookup and endpoint compatibility are mechanical checks against
captured IR. They check only explicitly represented occurrences and references;
they do not invent requirement/criterion identities or graph relations.

The first profile does **not** evaluate lifecycle transitions. `draft/reviewed`
is sgcore's review-state machine, while `idea` and `specified` are existing
document states. A later authored mapping must name its source dimension,
covered values and evidence for transitions. Unknown values remain unmapped;
they are not coerced into `draft` or `reviewed`.

`hasAcceptanceCriterion` has `min: 0` in this source package. An absent or empty
acceptance list therefore supplies no observed criterion and no completeness
failure. If a future maturity policy requires criteria, cite that separate policy;
do not attribute such a requirement to sgcore. Malformed present mapped fields
are diagnosed as malformed input, not counted as absent. Unresolved explicit
criterion references are reported as findings, not successful Evidence links.

## Outcomes and freshness

Keep the existing scope outcomes: `not_requested`, `analyzed`, `unavailable`,
`invalid`. An unrequested assessment has no passing summary. Missing/unsupported
metamodel checks or unresolved/out-of-scope applicability yield `unavailable`
with the reason. A detected pin, identity, malformed mapping or input conflict
is `invalid`, retaining invalid-before-unavailable precedence.

`analyzed` means supported, requested structural rules ran; individual rule
findings may remain. Report per-rule results, input locations, source/profile
identity and limitations beside the aggregate. It is not a clean-result,
completeness, semantic-approval, publication or implementation claim. Excluded
lifecycle/prose checks are visibly `not_assessed`, never implicit passes.
Domain results survive an unavailable meta assessment; aggregate completion still
requires all requested scopes analyzed and at least one requested scope.

Meta support requires a versioned report/profile extension before it can run.
Freshness must bind the metamodel capture, profile/mapping revision, applicability
disposition and its evidence, document bytes, requested rules/scopes and producer.
Changed/missing bindings cannot reuse old domain-only or combined bundles as
successful meta evidence. Previous inventory freshness remains `not_assessed`.
This proposal does not preassign a new schema number or relabel schema 2 results.

## Characterization and future acceptance matrix

The following are **expected future controls**, not executed profile tests.

| Case | Required result |
| --- | --- |
| No meta request | Meta `not_requested`; current domain results unchanged |
| Request with source, supported evaluator or applicability disposition missing | Meta `unavailable`; preserve any analyzed domain output |
| Pinned source/hash mismatch plus missing applicability | `invalid` takes precedence; do not substitute another package |
| Only an `id` supplied | No implicit Node or Spec binding |
| Explicit Spec mapping with matching `kind` and usable context | Class check can run; no graph-admission claim |
| Mapped `kind` conflicts with source document or mapped list is malformed | Diagnose invalid input; do not silently skip it |
| No `acceptance` or empty list | No criterion occurrences or sgcore completeness failure |
| Explicit criterion reference is unresolved | Visible reference finding; no Evidence-support pass |
| `idea`, `pre_canonical` or `specified` encountered | Preserve value; lifecycle `not_assessed` |
| Meta-only request | No domain inventory; use the independently selected meta context |
| Applicability/mapping/source/document changes | Old successful meta evidence cannot remain fresh |

The real GitView draft has `kind: spec`, a provisional ID, `status: idea`,
`draft_status: pre_canonical`, no top-level acceptance/evidence lists, and three
`review_examples`. Static inspection predicts a Spec candidate only after an
explicit mapping/applicability decision, no inferred Node/criteria and no review
state assertion. SG-SPEC-0072's `specified` status is a second control against
accidentally equating document status with review state. Neither document has
been checked by an implementation of this candidate profile.

## Next implementation slice

After profile review and the applicability disposition, implement one opt-in
Spec-artifact identity/class check with explicit metamodel capture and versioned
report/freshness support. Keep lifecycle, graph admission, full criterion/evidence
mapping and maturity gates outside that first slice. Characterize legacy outputs
and the existing domain-only contract before adding the evaluator; do not enable
it merely because this design is merged. No Ontology library change is required
by the source audit; a demonstrated package applicability conflict is a separate
proposal, not a compiler workaround.
