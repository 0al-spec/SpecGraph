# Verified Project Ontology Context

RFC: SG-RFC-0232
Version: 0.1.0

## Status and source

Draft proposal; planning contract only. Runtime realization is
`deferred_until_canonicalized`. The operator endorsed the product direction;
the schema, migration and enforcement design below remain proposed.

[Source draft](../archive/proposal_sources/0232_verified_project_ontology_context.md),
[captured note](../reviews/0232_project_ontology_context/source-notes.json) and
[draft obligations](0232_verified_project_ontology_context.intent.yaml) preserve
the origin and scope. The [preparation observation](../reviews/0232_project_ontology_context/preparation.json)
records the bounded Supervisor dry-run and document checks. This package adds no runtime enforcement, accepted ontology
terms, canonical specification changes or SpecSpace UI changes.

```yaml
canonical_mutations_allowed: false
runtime_profile_activation_allowed: false
evidence_admission_allowed: false
```

## Problem and intended result

Every project specification should ground its domain terminology in the
project's explicitly selected, verified ontology context. A context may contain
one large ontology or a composed set of packages. Selecting a compiler release
alone does not select the project's vocabulary or approve its terms.

Today stored IR can be consumed without running the compiler. The snapshot
helper merged through PR #822 provides a checked immutable source/IR pair, while
PR #825 proposes adoption by two report consumers. Neither establishes a shared
project context, complete terminology coverage or freshness for Supervisor
decisions. A report's existence and a graph's appearance cannot supply that
missing guarantee.

The desired result is inspectable: for a specification, a person or agent can
see its context revision, term definitions, unresolved meanings and the exact
inputs checked. Drafts remain available while that information is developed.

## Reuse and responsibilities

| Existing boundary | Proposed responsibility |
| --- | --- |
| Ontology and `ontologyc` | Package format, supported structural checks and compiled IR |
| SpecGraph project | Select the context; record term bindings, reviews and migration decisions |
| `OntologySnapshot` | Capture checked ontology bytes and compiler identity for a consumer |
| SpecGraph reports and Supervisor | Use the selected inputs; distinguish checked, unavailable and stale results |
| SpecSpace workspace panels | Display the selected context, scoped checks, spec bindings and gaps |
| SpecSpace `/ontology` | Explore locally loaded packages, retaining its independent read-only import contract |
| `TraceSnapshot` from proposal 0226 | Collect scoped trace facts; reference ontology identity when relevant |

`OntologySnapshot` and `TraceSnapshot` are distinct read models. An ontology
snapshot does not prove that an implementation or test preserves a requirement.
Reuse the [0226 evidence boundary](0226_traceability_evidence_providers_and_svc.md)
and the Ontology intent-preservation contract in a later bounded pilot. A future
skill teaches the agent how to prepare that review; it does not replace checks
or make missing mappings successful.

Related proposals: [0132](0132_project_local_ontology_package_boundary.md),
[0134](0134_legacy_spec_ontology_binding_index.md),
[0135](0135_spec_ontology_validation_report.md),
[0138](0138_ontology_gap_review_workflow.md),
[0140](0140_legacy_spec_ontology_backfill_plan.md),
[0144](0144_ontology_model_applicability_import.md), and
[0231](0231_native_specgraph_runtime.md).
These retain their original implemented/report-only scopes.

## Proposed contract

### Project selection and immutable inputs

The project selects a versioned context. Each member identifies a package,
namespace, exact version, source and content hashes; dependency closure and the
selected compiler/profile identity are part of the context identity. One package
is a valid context. Multiple packages require explicit compatible dependency and
name-resolution rules. Duplicate identities, incompatible requirements, missing
imports and ambiguous unqualified names remain diagnostics; there is no implicit
last-package-wins or silent latest-version selection.

Physical manifest layout is intentionally undecided. Reuse the existing project
package/import contracts where they fit before adding a schema. The compiler
release pin is separate from a package pin. An implementation must distinguish
compiler-checked members from dependency checks not supported by the selected
tooling. Unsupported closure verification makes that guarantee unavailable; it
must not be inferred from separate successful compilations.

Build one immutable context snapshot for an operation and pass captured data to
all consumers. A composed context may hold several `OntologySnapshot` values.
Consumers do not reopen mutable IR paths. Source, IR, package set, compiler and
profile identities bind the result. Compiler hashes identify executable bytes;
compiler trust and package semantic approval require separate recorded origins.

### Terminology coverage for every specification

Every current specification is associated with an explicit context revision.
The project default may select that revision, but a saved verification result
always records the resolved selection. Historical spec/context revisions remain
inspectable. A context change triggers reassessment, not silent rewriting of
the specification's words, bindings or history.

Ground domain concepts and relations, including terms in normative prose,
against definitions and contextual meanings. Use stable qualified references
and source locations. A matching name or alias is only a candidate until its
meaning fits; imported namespace collisions require explicit resolution.
Ordinary grammar and presentation labels need not become ontology classes.

Coverage is an explicit inventory with a declared extraction/review profile.
Record considered terminology, exact field/span, context and disposition;
unexamined prose remains unassessed. A deterministic parser may establish
structural references; a model may suggest semantic bindings or missed terms.
Neither may certify complete semantic coverage from spelling matches. Human
review and bounded profiles establish what was actually assessed. A partial
inventory cannot produce a whole-specification conformance claim.

### Valid package, unresolved term and action-specific readiness

Keep structural validity, terminology coverage, freshness and semantic approval
separate. A structurally valid package with gaps remains usable for its resolved
vocabulary. Gaps are source-attributed review work, not automatic rejection of
the whole package. Canonical project specifications remain subject to the target
grounding rule; a particular unresolved required term prevents that
specification from being reported as fully grounded.

| Condition | Proposed behavior |
| --- | --- |
| Capture a thought before terminology exists | Save attributed draft; linking may follow later |
| Selected context checked, required term resolved | Use binding within its reviewed scope |
| Unknown or ambiguous term | Retain candidate and gap; request review; do not assert resolved meaning |
| Unrelated gap in an otherwise usable package | Continue operations whose required vocabulary is resolved |
| Compiler or required dependency check unavailable | Explain unavailable verification; allow drafts; withhold dependent verification/action |
| Source/IR mismatch, invalid package or context conflict | Report failure; do not substitute old IR as the current checked context |
| Stale report or different project/spec inputs | Recompute or expose stale/unknown; do not use as current success |
| Existing unassessed specification | Keep historical content accessible and show migration debt; do not relabel it grounded |

The later enforcement slice must name which operation requires which term set
and evidence. It must not introduce a global ban on note taking or block an
unrelated concern because another specification has a gap. Canonical promotion
under the new policy requires assessed terminology and resolution of its required
gaps; historical migration exceptions must be explicit review decisions with
scope and a return task, never implied conformance.

### Freshness, reuse and Supervisor

Bind each report to its project/workspace identity, selected context and the
actual specification/binding/policy inputs affecting that report. An unchanged
ontology hash is insufficient when the specification changed. Reuse only when
all influencing inputs and profiles match; timestamps alone do not establish
freshness. Content-addressed caching can avoid recompiling unchanged inputs,
with cache admission rules and negative tests defined in the implementation.

Supervisor consumes these statuses for the named ontology-dependent step.
Missing, stale, failed or partial evidence cannot become current verified
success or be replaced with an arbitrary latest report. The first implementation
should refresh the required local inputs or return a concrete next action.
It does not acquire authority to accept new meanings or to update canonical
specifications just because a compiler or model returned success.

### SpecSpace integration

Reuse the existing workspace endpoints `/api/v1/practical-ontology` and
`/api/v1/ontology-workbench`. Show the selected package set and context revision,
check scope, freshness, terminology coverage, semantic review status, and links
from a specification to definitions and unresolved gaps. Presence of IR, an
`accepted_bindings` field in a report, or successful graph rendering must not
be displayed as verified/approved terminology without the corresponding data.

Preserve `/ontology` as independent browser-local artifact exploration. Loading
a ZIP there does not select the active project context, run the compiler, or
approve vocabulary. A later explicit comparison/navigation feature may relate
the two surfaces while preserving this boundary. Do not make workspace panels
depend on browser-local drag/drop state.

## Delivery sequence and future acceptance cases

These cases plan future verification; none has been executed by this proposal.

1. Finish the two report consumers from PR #825; prove one checked snapshot is
   used throughout a report, and missing requested compilers/mismatched IR fail.
2. Define the minimal project selection and report provenance seam. Test one
   package and a composed set; missing imports, incompatible pins, duplicate
   names and unsupported checks must not report verified context closure.
3. Migrate candidate graph and Supervisor consumers. Change ontology/spec/policy
   independently; stale reports must be rejected for the dependent action.
4. Inventory the existing corpus using 0134/0135/0138/0140. Pilot one spec with a
   resolved term, one genuine gap and one unassessed prose term; retain all IDs,
   source attribution and history. Report counts only over the stated inventory.
5. Supply a pinned trusted compiler through a documented native-runtime path;
   validate macOS and Linux, offline/reuse behavior and unavailable-tool output.
   Automatic downloads, building and trusted-binary selection need explicit
   implementation design; the source release supplies no prebuilt executable.
6. Add SpecSpace display against producer fixtures for checked, stale, partial,
   invalid and missing contexts. Keep graph/import route tests independent.

The rollout is complete only when all selected current specifications have an
assessed context and coverage, unresolved cases are explicit, and the declared
ontology-dependent actions actually enforce the policy. A report count, this
proposal, the optional #825 mode or a rendered graph cannot satisfy that alone.

## Separate follow-ups

Intent preservation across ontology, specification, Hypercode, implementation,
tests and observations is a distinct concern. Prepare its own bounded proposal
and Ontology-owned skill using the existing image/cancellation profiles. It
consumes this context identity and 0226 facts without turning those facts into
a universal semantic-equivalence or trusted-runtime claim.

Ontology owns shared vocabulary and compiler contracts; each product owns its
domain packages. SpecGraph owns project selection and specification readiness;
SpecSpace renders their status. No remote registry dependency solver, new storage
backend, compulsory class-per-term code structure or new claim issuer is proposed.
