# Proposed next slice of the SpecGraph core ontology

**Status: review proposal; no ontology mutation or canonical acceptance.**
This comparison continues the [core inventory](../core-inventory-20261107/README.md)
and the operator's request to improve the whole ontology. It recommends one
bounded first slice and records what remains for later review. The
[combined review projection](../../../../specs/models/review/ontology-overview/README.md)
provides the visual context; it does not merge the packages or approve them.

The scope and source digests are recorded in [comparison.json](comparison.json),
and the conversational provenance in [source.md](source.md). The proposal is
linked through the [proposal lane](graph-links.json) to the existing user
intent and to [SG-SPEC-0053](../../../../specs/nodes/SG-SPEC-0053.yaml).
It is not a new RFC or a decision to publish changes.

## Baseline and recommendation

The publicly available `org.0al.specgraph.core@0.1.0` is itself a **draft**
package: 14 classes and 16 relations, plus its policy and state machine. It
already defines `Intent`, `Spec`, `Decision`, `Evidence` and `Release`, but it
does not define the four other primary pre-spec kinds or their adjacency.

Start by reviewing the following additions to core, preserving the existing
`sgcore:Intent` rather than introducing another `Intent`. These are candidates
for a subsequent version, not accepted declarations in this review:

| Candidate | Why it belongs in the first review | Boundary |
| --- | --- | --- |
| `IntentFragment` | Small observable piece extracted from a source | Not a complete draft or a verified statement |
| `IntentDraft` | Synthesized observed intent | Still pre-canonical; may inform an intent or proposal |
| `Hypothesis` | Epistemic context for interpreting a draft or proposal | May support, challenge or contextualize; it is not intent or approval |
| `Proposal` | Reviewable candidate operationalization | Does not replace its motivating intent and does not itself authorize promotion |

The six candidate relations are `fragmentContributesToDraft`,
`hypothesisInformsIntentDraft`, `hypothesisInformsProposal`,
`intentDraftSourceForIntent`, `intentDraftMotivatesProposal` and
`intentMotivatesProposal`. They mirror the adjacency described in
SG-SPEC-0053 and in the existing draft model. Their presence is conditional on
the relevant source and target; the two routes to `Proposal` are not both
mandatory. `informs` alone does not encode whether a hypothesis supports or
challenges a target, nor prove that it is true.

The present core describes `Intent` as a governed product representation;
SG-SPEC-0053 also discusses a stabilized but still **pre-canonical** intent.
Before reusing the core type for both contexts, review whether its wording and
authority model actually cover both. Do not silently equate stabilization
with canonical acceptance.

## Remaining candidates

The [machine-readable inventory](comparison.json) accounts for all 19
candidate classes and 14 candidate relations in the three domain packages.
It excludes the two classes and one relation of the review projection's
`sgreview` scaffolding.

| Source | Recommendation | Reason and open boundary |
| --- | --- | --- |
| [Intent to proposal](../../../../specs/models/SG-SPEC-0053/intent-to-proposal/domain-ontology-package.yaml) | Review the four kinds and six relations above for core. Keep `RawInput`, `IntentSynthesizer`, `ProposalAuthor`, `InterpretFragmentForDraft`, `InterpretIntentForProposal` and their three remaining relations in the draft package for now. | The spec names raw input, but whether it is an entity, payload or provenance reference needs a decision. Actor roles and interpretation actions are useful but need a clear scope and authority model. Source lineage must remain available regardless of representation; see [SG-SPEC-0052](../../../../specs/nodes/SG-SPEC-0052.yaml). |
| [Proposal promotion](../../../../specs/models/SG-SPEC-0051/proposal-promotion/domain-ontology-package.yaml) | Keep all six classes and four relations together as a bounded draft; review `SpecDraft` and `TransitionRecord` as likely next shared concepts. | A draft is not automatically a `Spec`; a record is not automatically core's `Decision` command. The current model shows proposal ingress, while [SG-SPEC-0051](../../../../specs/nodes/SG-SPEC-0051.yaml) also covers other ingress and separately recorded materialization. Actor, target, actions and transitions need review without inferring authority or an existing canonical destination. |
| [Publication verification](../../../../specs/models/SG-SPEC-0071/verification-action/domain-ontology-package.yaml) | Keep its four classes and one relation together in the publication-verification package. | The verifier compares the published HTTPS bundle with the retained expected bundle. Neither bundle automatically equals core `Release`; a verification observation does not by itself establish accepted `Evidence` or a trusted receipt. [SG-SPEC-0071](../../../../specs/nodes/SG-SPEC-0071.yaml) is the behavior source. |

This is a sequencing recommendation, not a claim that actions or roles do not
belong in the ontology. A later slice should model them where their ownership,
inputs, consequences and authority are established. The shared core and
bounded packages can remain connected without copying every local concept into
one package solely to affect the layout.

## Migration and compatibility questions

Moving a declaration changes its identity: for example,
`ontology://org.0al.specgraph.intent-proposal/0.2.0-draft.1/classes/Proposal`
is not automatically the same URI as a future core `Proposal`. The promotion
package currently imports `sgproposal:Proposal`. A subsequent implementation
must decide the explicit identity/mapping and migration policy, update imports
and dependent models, preserve provenance, and check for dependency cycles.
Do not infer an alias or silently keep two independent concepts with the same
meaning.

The source packages also import distinct foundations:
`specgraph.foundation@0.1.0` and `ontology.foundation@0.2.0`. Matching type
names do not establish equivalence. Verify their contracts and consumers
before selecting the core's parent types or changing an import.

Do not assign the next core version yet. An existing draft
[compatibility fixture](../../../../ontology/packages/specgraph-core/compatibility/specgraph-core-0.2.0-claim-calibration.yaml)
already advertises `org.0al.specgraph.core@0.2.0` for different content. Check
its identity, current pins and fixtures, and resolve that collision before
selecting a version for a different package. The core's compatibility policy
allows additions in a minor version, but changing an existing concept's
meaning or a relation's endpoints has a different compatibility impact.

## Proposed review and implementation sequence

1. Review the four kinds, six relations and the scope of existing `Intent`
   against SG-SPEC-0053 and the originating draft. Decide whether they belong
   in core and whether names, direction and definitions need adjustment.
2. Decide identity mapping, foundation compatibility, version and migration of
   the existing `sgproposal` and `sgpromotion` consumers. Preserve the old
   source identities as provenance and explicitly decide how old references
   resolve; a digest identifies bytes, not approval or authorship.
3. Only after the appropriate human decision, implement the smallest accepted
   package change. Recompile the affected packages and combined projection;
   update generated artifacts, pins and locks where applicable. Check both a
   correct migration and rejection/reporting of missing or stale references.
4. Review promotion semantics and publication evidence as separate bounded
   slices. Inspect the combined graph in the Viewer, but assess the definitions
   and relationships on their merits rather than treating appearance or a
   successful compile as proof of semantic correctness.

Questions for review: should `Intent` cover both pre-canonical and governed
contexts; how should old candidate identifiers resolve after a move; which
foundation should own the parent types; and which later promotion concepts
are truly shared rather than local to their workflow? No answer is presumed
by this packet.
