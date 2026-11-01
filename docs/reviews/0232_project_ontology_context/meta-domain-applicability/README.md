# Separate specification meta checks from project vocabulary

## Status and source

Design candidate for review under SG-SPEC-0072 and
[proposal 0232](../../../proposals/0232_verified_project_ontology_context.md).
The original triage recorded feedback and proposed the bounded contract below.
The implementation described at the end realizes its first slice; meta-model
applicability and optional meta checking remain unresolved.

```yaml
canonical_mutations_allowed: false
global_policy_activation_allowed: false
```

GitView's source report is `docs/drafts/sgcore-applicability-0f0a056a.md`,
local commit `60c67f7`. It examines the real precanonical GITVIEW-SPEC-0001
draft on runtime `0f0a056a`, using isolated workspaces and pinned ontologyc
0.5.0. The local intake is
`20261101T100923Z-note-triage-meta-model-versus-domain-vocabulary-applicability-from-gitview.md`.
[The observation capsule](observation.json) retains source hashes, claimed
control outcomes and the distinction between inspection and re-execution.
Private draft text and complete local runtime reports are not published here.

## Confirmed cause and unresolved applicability

The current binding index synthesizes `sgcore:Spec` from `kind: spec` and
`sgcore:Node` from the presence of `id`. Validation additionally requires a
`sgcore:Spec` binding and turns binding gaps into legacy-term warnings.
Thus three findings describe two missing structural bindings. They are not
three missing concepts in GitView's domain vocabulary, and the ID is not proof
of canonical graph membership.

The original [0134](../../../proposals/0134_legacy_spec_ontology_binding_index.md)
and [0135](../../../proposals/0135_spec_ontology_validation_report.md) contracts
addressed the legacy SpecGraph corpus. The draft `org.0al.specgraph.core@0.1.0`
package applies to `specgraph_core`, excludes `unrelated_product_domain` and
retains `project_local_authority`. This does not automatically authorize or
forbid using it to describe an external product's **specification artifact**.
That meta-model applicability question remains unresolved.

Selecting only sgcore removes its warnings but loses GitView's domain vocabulary.
The current profiles do not support a GitView/sgcore pair or sgcore as a fourth
motivation-composition member. Those observations describe bounded profiles;
they do not prove that the ontologies are universally incompatible.

## Proposed report contract

Use two explicit check scopes. This is report scoping, not a requirement to
compose the two ontologies into one package graph.

| Check scope | Input and purpose | Findings |
| --- | --- | --- |
| `domain_vocabulary` | Explicit terminology and ontology_refs against the selected project context | Unknown/ambiguous terms with source locations and candidate provenance |
| `specification_metamodel` | Requested structural rules over kind/id/acceptance/evidence, with a selected meta source and established applicability | Structural binding/relationship diagnostics attributed to that meta profile |

The existing context metadata `scope` already describes local versus composed
symbols. Keep it; use a distinct `check_scope` for this separation. Record each
requested scope's context revision, profile, evidence and findings. A meta
package must not silently supply unqualified candidates to domain analysis.
Sharing identical captured inputs is possible only when explicitly assigned
to both roles, without merging their authority or name-resolution scope.

Proposed outcomes per scope:

| Outcome | Meaning |
| --- | --- |
| `not_requested` | No analysis requested; no passing checks or zero-gap claim |
| `analyzed` | Declared analysis completed; findings may remain |
| `unavailable` | Requested analysis lacks required context/compiler/applicability evidence or supported checking |
| `invalid` | A detected input/pin/identity inconsistency; preserve existing invalid-before-unavailable precedence |

Use a separate applicability diagnostic when applicability is unresolved.
Do not relabel it `not_applicable`: that would itself assert a decision.
For an unrequested assessment, findings/counts are unassessed rather than an
empty collection that could be mistaken for a clean result. Zero domain
occurrences likewise do not establish grounding or whole-spec coverage.

The proposed default for the context-bound vocabulary command is domain analysis
requested and meta analysis `not_requested`, visibly recorded. Explicitly
selecting sgcore as a domain package does not itself request its structural
meta checks or settle their applicability. Requested meta checks with missing
prerequisites remain `unavailable`, while completed domain results stay visible.
The initial triage proposed this default; the first implementation slice below
now realizes it for the bounded advisory operation.

Aggregate completion refers only to the explicitly requested scopes. Any requested
invalid/unavailable scope prevents an overall completed result. At least one
scope must have been requested and analyzed; two `not_requested` scopes cannot
yield `checked`. The report must enumerate the analyzed and unassessed scopes
beside that status. Unknown domain terms remain advisory gaps rather than making
completed analysis invalid. No new merge/promotion gate is proposed.
`semantic_approval: not_established`, unassessed prose and no canonical authority
remain unchanged. A later operation that needs meta checks must explicitly
require/request them instead of inferring readiness from the domain result.

If meta checks are enabled, retain their rule/source provenance. The `Spec`
extraction gap and required-binding finding share one cause; expose that
relationship rather than describing each finding as a distinct missing domain
concept. Redesigning every warning count or deduplication rule is not required
for the initial separation.

## Compatibility and bounded implementation sequence

1. Review the scope split and proposed domain-only default through the existing
   proposal lane. No new ontology package or canonical node is needed to record
   this question. An explicit selection/profile decision is sufficient; this
   design does not add signatures, per-file approval ceremonies or a registry.
2. After acceptance, isolate the context-bound domain projection from the legacy
   structural extraction and required-Spec check. Report meta `not_requested`
   explicitly. Keep the no-context 0134/0135 tools on their identified legacy
   contract until a separate migration is decided.
3. Add an explicit meta assessment only after its source, applicability and
   requested operation are defined. Reuse pinned capture/compiler machinery;
   independent meta and domain contexts do not imply cross-context dependency
   closure or arbitrary package-composition support.
4. Version the changed analysis/report contract. Freshness binds requested scopes,
   per-scope context/profile/producer identity, applicability evidence and exact
   spec bytes. Old combined reports cannot become fresh scoped reports. Do not
   repurpose the existing three-member composition schema to fit a meta package.
   Retain the currently explicit inventory-freshness limitation.

The first implementation slice is step 2 with visible unrequested meta status
and the versioning/freshness requirements of step 4. Those requirements cannot
wait for the optional meta implementation. This is not a general ontology-composition
solver. Every slice preserves requested checks, prerequisites and successful
analysis as distinct facts.

## Proposed acceptance matrix

These are future checks, not tests executed by this documentation PR.

- Default GitView context: `Activity` and unselected `motivcore:Motive` remain
  domain gaps; no synthesized sgcore terms enter those domain counts; meta is
  visibly `not_requested`.
- Motivation composition: `Activity` remains a domain gap; `Motive` resolves;
  unrequested meta assessment produces no success/conformance claim.
- Requested meta check with missing source or unresolved applicability: meta is
  `unavailable`; domain output is retained, aggregate cannot claim completion.
- Two unrequested scopes cannot produce aggregate `checked`.
- Explicit usable meta selection with applicable rules: structural findings and
  their origins are visible in the meta section; domain candidates remain scoped.
- Legacy no-context outputs retain characterized behavior until migration.
- Changed requested scopes, meta source/profile, applicability evidence or spec
  bytes make saved results stale/unavailable as appropriate; do not silently reuse
  historical combined reports or claim inventory freshness.

## Remaining applicability decision

The domain-only default is realized by the first slice below. Before enabling
meta checking, decide whether sgcore can
describe external specification artifacts under an explicit applicability
profile, needs a revised applicability declaration, or needs a separately governed
meta source. This packet does not choose or publish that ontology decision.

The independent audit confirmed the source-level scope leak and compatibility
risks. Retained GitView control summaries were read, and pinned source hashes
were cross-checked; no compiler/runtime probe or note-restoration check was
rerun for this documentation-only triage. Preparation, review, merge and policy
activation remain separate events.

## First implementation slice

The context-bound report operation now requests `domain_vocabulary` by default
and explicitly records `specification_metamodel: not_requested`. Structural
kind/id/acceptance/evidence extraction and the unconditional required-Spec check
remain in the no-context legacy 0134/0135 APIs. They no longer contribute to the
context-bound domain report. Authored sgcore references still participate in
ordinary resolution; selecting sgcore as domain input does not enable meta rules.

Bundles and domain binding/validation artifacts use schema 2 and
`specgraph-scoped-ontology-advisory-v1`. Local/composed vocabulary metadata is
versioned to v3/v2. The report's separate `check_scope` does not change the
existing context `scope` or pretend that meta and domain packages were composed.
A named completion Specification requires at least one requested scope and all
requested scopes analyzed. Existing invalid-before-unavailable precedence is
preserved; parsing, path capture and legacy projections remain boundary code.

The repeatable Supervisor flag `--ontology-context-check-scope` accepts
`domain_vocabulary` and `specification_metamodel`. Full and compact outputs show
the request and both outcomes. Requested meta is currently `unavailable` because
source, applicability and supported checking have not been established. With
both scopes requested, completed domain results remain visible while the
aggregate is unavailable. Meta-only/empty requests do not analyze domain reports
or inventory. No per-file approval ceremony or ontology-composition extension
was added.

Freshness binds the complete assessment manifest, current requested scopes,
profiles, producer source identity and captured inputs. Saved combined bundles
are unavailable for scoped comparison and cannot be relabelled as fresh by
recomputing their attributed binding. Analyzed children carry their own scope,
profile and schema, so extracting a report does not hide its changed semantics.
Previous inventory freshness stays `not_assessed`.

### Re-executed GitView control

[The verification capsule](verification.json) records a local replay using
isolated copies of the original spec and ontology inputs plus the same pinned
release ontologyc 0.5.0. Neither GitView's working files, selected context nor
precanonical graph status changed. The old runtime and this candidate ran over
the same copied workspace inputs; files were hashed before and after.

| Context | Old mixed warnings | Domain warnings | Meta |
| --- | ---: | ---: | --- |
| Main GitView | 5 | 2: Activity, motivcore:Motive | not_requested |
| Motivation composition | 4 | 1: Activity | not_requested |

In both cases, explicitly requesting meta preserved domain output and returned
`unavailable`; old mixed bundles did not become fresh scoped results. The lower
warning count corrects attribution/scope, and does not mean missing meta work
was completed or the product ontology gained concepts.

Regressions cover structural-only documents, explicit sgcore references,
unchanged legacy output, unknown/ambiguous terms, scope combinations and invalid
inputs, CLI summaries, legacy-bundle migration, manifest integrity and changed
current scopes. Full semantic coverage and applicability remain unclaimed.
