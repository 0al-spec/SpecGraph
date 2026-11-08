# Pre-spec intent and proposal: a draft action model

This is a **reviewable draft**, not an accepted ontology change or a change to
the published SpecGraph core. It models one branch of
[SG-SPEC-0053](../../../nodes/SG-SPEC-0053.yaml): fragments can contribute to
an `IntentDraft`, a draft can lead toward an `Intent` or `Proposal`, and
a `Proposal` can operationalize an `Intent`. These kinds remain distinct
pre-canonical declarations within this spec's scope.

The request motivating this model was to make the SpecGraph ontology more
expressive with entities, actions and relationships, as in the publication
verification example. The source specifies the intent/proposal semantics; it
does not prescribe this particular action or identify an author. The model
proposes those choices for review rather than treating them as established
facts.

## Proposed interpretation

| Declaration | Meaning and source |
| --- | --- |
| `sgcore:Intent` | The existing project-core term, imported from `org.0al.specgraph.core@0.1.0`; this example concerns the pre-spec interpretation in SG-SPEC-0053. |
| `sgproposal:RawInput` | Source material for the observed-intent path; capture does not establish identity or truth. |
| `sgproposal:IntentFragment` | A partial observable signal; one fragment is not a complete intent draft. |
| `sgproposal:IntentDraft` | A synthesis of one or more fragments and optional context, not yet canonical intent. |
| `sgproposal:Hypothesis` | A reviewable epistemic statement, distinct from normative intent. |
| `sgproposal:Proposal` | The candidate operationalization in `specification.kind_roles.proposal`. |
| `sgproposal:IntentSynthesizer` | A proposed contextual role for whoever develops the draft; it may be a person or agent and grants no authority. |
| `sgproposal:InterpretFragmentForDraft` | A proposed action that interprets one fragment for an **existing** draft. `candidateDraft: Ref<IntentDraft>` identifies that draft. |
| `sgproposal:interpretsFragmentForDraft` | Action relationship: subject = synthesizer, action = interpretation, object = the fragment being interpreted. |
| `sgproposal:rawInputSourceForFragment` | A raw input supplies source material for a fragment. |
| `sgproposal:fragmentContributesToDraft` | A fragment contributes partial observed meaning to a draft. Multiple fragments may contribute. |
| `sgproposal:hypothesisInformsIntentDraft` | A hypothesis can support, challenge or contextualize a draft; the relation alone does not select a polarity. |
| `sgproposal:hypothesisInformsProposal` | A hypothesis can also inform a proposal without itself becoming the proposal. |
| `sgproposal:intentDraftSourceForIntent` | A draft supplies observed meaning for a later intent; the relation alone is not approval or canonicalization. |
| `sgproposal:intentDraftMotivatesProposal` | A proposal can be motivated by a draft without a separately stabilized intent. |
| `sgproposal:ProposalAuthor` | A proposed contextual role for whoever develops the candidate; it may be a person or agent and grants no authority. |
| `sgproposal:InterpretIntentForProposal` | A proposed action that interprets an intent for an **existing** candidate. `candidateProposal: Ref<Proposal>` identifies that candidate. |
| `sgproposal:interpretsIntentForProposal` | Action relationship: subject = author, action = interpretation, object = the intent being interpreted. |
| `sgproposal:intentMotivatesProposal` | The separate `intent → proposal` relation required by `specification.kind_separation.required_edges` when this path introduces a candidate. |

The actions read/interpret the fragment or intent; they do not assert that
either is changed. A typed reference names an existing candidate, but does not
create it, resolve its locator, establish that the interpretation succeeded, or
prove semantic preservation. Each action occurrence mentions one fragment or
intent; it does not assert that other sources are absent. Review, promotion,
canonical publication and the actual authoring implementation are outside this
model. The package keeps its original identity and advances its draft version
to `0.2.0-draft.1` for these additive declarations.

The [SDK example](sdk-example.ts) supplies an **in-memory test actor**, not
SpecGraph's production executor. It illustrates two fragments contributing to
one known draft, a proposal gaining a link to an intent, and unknown candidates
leaving the example stores unchanged. The record schema rejects a missing or
incorrectly typed reference.
This demonstrates those bounded sample behaviors, not semantic equivalence or
approval of an actual proposal.

## Reproduce and inspect

With the released Ontology **0.8.0** `ontologyc` and `ontologyviz` on PATH,
from the SpecGraph root, set `OUT` to a build directory outside the checkout:

```sh
model=specs/models/SG-SPEC-0053/intent-to-proposal/domain-ontology-package.yaml
ontologyc check "$model"
ontologyc compile "$model" --target typescript --out "$OUT/sdk"
ontologyviz "$model" --view full --format json \
  --import ontology/packages/specgraph-core/domain-ontology-package.yaml \
  --out "$OUT/graph"
```

Open `$OUT/graph/ontology.graph.json` in SpecSpace's local Ontology Viewer.
The projection includes the existing core and this candidate, so filter by
package to inspect each separately. Select `interpretsFragmentForDraft` or
`interpretsIntentForProposal` to inspect subject, action and object, then
follow the action's typed candidate field. Projection and SDK are derived
artifacts; loading them neither updates the public site nor accepts the
candidate ontology.

## Current tool boundaries

Ontology 0.8.0 accepts `sgcore:Intent` as an imported relation endpoint, but
`Ref<sgcore:Intent>` as an action field is rejected with
`class.field.target.unresolved`: field targets must name a class in the same
package. The existing `Intent` is therefore **not duplicated** to work around
the restriction. A direction that passes an imported intent as an action field
remains an option to revisit when the compiler supports it.

The compiler's standalone check and the full graph export do not prove imported
symbol membership. The focused test compares this model's `sgcore:Intent`
endpoints with the exact imported core source and checks the exported
declaration's origin. A general composition check for this particular pair is
not claimed: the current SpecGraph composition profile is specialized for the
motivation/events packages. Layout direction is also a viewer policy; adding
valid relationships alone does not guarantee the desired left-to-right order.
