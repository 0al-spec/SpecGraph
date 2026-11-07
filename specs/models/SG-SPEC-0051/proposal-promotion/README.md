# Proposal promotion: a draft ontology model

This is a **reviewable draft**, not an accepted change to `specgraph-core`, an
approval, or a canonical publication. It models one path in
[SG-SPEC-0051](../../../nodes/SG-SPEC-0051.yaml): an existing Proposal may move
to a SpecDraft only with a recorded approved review; that draft may later be
materialized only with a separate transition decision and a valid recorded
ingress. The direct `intent_draft -> spec_draft` path also exists in the spec
but is outside this example; a Proposal is not mandatory for every SpecDraft.

The operator asked to improve the whole SpecGraph ontology graph. The selected
slice and remaining review questions are recorded in the
[core inventory](../../../../docs/reviews/0232_project_ontology_context/core-inventory-20261107/README.md).
The action names and actor role below are a proposed interpretation of the
source, not new authority or proof that any action actually happened.
The [source](source.md), [operator packet](operator-request.json) and
[graph links](graph-links.json) retain the route through the intent and
proposal lanes. The proposal is under review; the packet did not execute a
supervisor child or authorize a canonical write.

## Proposed interpretation

| Declaration | Meaning |
| --- | --- |
| `sgproposal:Proposal` | Reuses the existing candidate from the SG-SPEC-0053 model. |
| `sgpromotion:SpecDraft` | A pre-canonical draft; its existence does not imply it has a valid ingress or is ready to publish. |
| `sgpromotion:CanonicalTarget` | A selected destination and identity, not proof that a canonical artifact already exists. |
| `sgpromotion:TransitionRecord` | A completed transition decision carrying the fields required by SG-SPEC-0051. Pending templates remain possible, but are not completed records. |
| `sgpromotion:PromotionActor` | A proposed role for whoever attempts a transition. The actor and the recorded reviewer may differ; this declaration grants neither actor authority. |
| `sgpromotion:PromoteProposalToSpecDraft` | A proposed action naming the target draft and its transition record; the Proposal is the relationship object. |
| `sgpromotion:MaterializeSpecDraft` | A separate proposed action naming a destination, the draft's ingress record, and the materialization record; the SpecDraft is the object. |
| `sgpromotion:proposalMotivatesSpecDraft` | A source relation, not a substitute for a transition record or review. |
| `sgpromotion:draftTargetsCanonicalDestination` | A planned destination relation, not a publication receipt. |

The schema requires record fields and typed references. It does **not** prove
that references resolve, records concern the same draft or proposal, a review
is approved, an actor is authorized, or a canonical write occurred. A failed or
pending review does not advance an edge. A schema-valid `rejected` outcome is
not an approval. Existing SpecGraph publication governance performs its own
checks; the SDK example is only a local illustration and is not that executor.

For a proposal-sourced draft, the source requires an approved
`proposal -> spec_draft` review and a complete `spec_draft -> canonical_artifact`
review or confirmation. The latter must bind the same draft and its valid
ingress. Neither an IntentDraft nor a Proposal may bypass the draft and move
directly to a canonical artifact. SG-SPEC-0051 also permits an explicitly
confirmed or reviewed **direct IntentDraft ingress**; this small model does not
claim to cover that alternate path.

The [SDK example](sdk-example.ts) checks typed records and exercises a small
in-memory illustration of this one path, including missing, rejected and
foreign-ingress cases. Its rules are example code, not the project's authority
boundary or evidence that a real transition occurred.

## Reproduce and inspect

With Ontology **0.8.0** and an output directory outside the checkout:

```sh
model=specs/models/SG-SPEC-0051/proposal-promotion/domain-ontology-package.yaml
prior=specs/models/SG-SPEC-0053/intent-to-proposal/domain-ontology-package.yaml
core=ontology/packages/specgraph-core/domain-ontology-package.yaml
ontologyc check "$model"
ontologyc compile "$model" --target typescript --out "$OUT/sdk"
ontologyviz "$model" --view full --format json \
  --import "$prior" --import "$core" --out "$OUT/graph"
```

Open `$OUT/graph/ontology.graph.json` in the local SpecSpace Ontology Viewer.
The root package explicitly declares transitive dependencies needed by the
0.8.0 visualizer. The graph includes the earlier draft and the selected core;
neither their appearance nor compilation establishes acceptance or execution.

Standalone compiler checks do not prove imported symbol membership. Focused
tests bind the imported Proposal to the exact prior package and check its graph
origin; they are not a general ontology-composition verifier. They also verify
that the source's required completed-record fields stay represented in this
candidate. The production publication tests remain separate evidence for the
specific code path that they execute.
