# Intent to proposal: a draft action model

This is a **reviewable draft**, not an accepted ontology change or a change to
the published SpecGraph core. It models one branch of
[SG-SPEC-0053](../../../nodes/SG-SPEC-0053.yaml): a `Proposal` may
operationalize an `Intent`, while the proposal remains a distinct,
pre-canonical candidate. The spec also permits proposals based on an
`IntentDraft`; that path is deliberately outside this slice.

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
| `sgproposal:Proposal` | The candidate operationalization in `specification.kind_roles.proposal`. |
| `sgproposal:ProposalAuthor` | A proposed contextual role for whoever develops the candidate; it may be a person or agent and grants no authority. |
| `sgproposal:InterpretIntentForProposal` | A proposed action that interprets an intent for an **existing** candidate. `candidateProposal: Ref<Proposal>` identifies that candidate. |
| `sgproposal:interpretsIntentForProposal` | Action relationship: subject = author, action = interpretation, object = the intent being interpreted. |
| `sgproposal:proposalOperationalizesIntent` | The separate, persistent proposal-to-intent relation described in `specification.semantic_adjacency`. |

The action reads/interprets the intent; it does not assert that the intent is
changed. A typed reference names the candidate, but does not create it, resolve
its locator, establish that the interpretation succeeded, or prove that a
proposal implements the intent. This single-intent example does not assert that
other motivations are absent. Review, promotion, canonical publication and the
actual authoring implementation are outside this model.

The [SDK example](sdk-example.ts) supplies an **in-memory test actor**, not
SpecGraph's production executor. It illustrates a known candidate gaining a
link to the selected intent and an unknown candidate leaving the store
unchanged. The record schema rejects a missing or incorrectly typed reference.
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
package to inspect each separately. Select `interpretsIntentForProposal` to
inspect its subject, action and object, then follow the action's
`candidateProposal` field. Projection and SDK are derived artifacts; loading
them neither updates the public site nor accepts the candidate ontology.

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
