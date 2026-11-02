# Applicability of sgcore to an external specification artifact

## Review status

This is a **decision candidate**, not an accepted interpretation or a grant of
authority. It belongs to SG-SPEC-0072 and proposal 0232, following the
[external specification artifact profile](external-specification-artifact-profile.md)
merged in [SpecGraph PR #868](https://github.com/0al-spec/SpecGraph/pull/868).

```yaml
decision: pending_human_review
applicability_approved: false
runtime_profile_activation_allowed: false
canonical_mutations_allowed: false
ontology_publication_authorized: false
```

No affirmative human decision is recorded here. Merging this review candidate,
compiling a package, or executing a diagnostic does not supply that decision.
When the authorized human decides, record the actual decision and its source
against the exact scope and inputs below; do not fill an approval field from a
fixture, model inference, or an earlier endorsement of the profile design.

## Candidate decision

**Recommended for review:** permit the SpecGraph-owned operation to consider a
document about an external product as a *specification artifact processed by
SpecGraph*, and, only through an explicit mapping, check its candidate class
against `sgcore:Spec`. The target of this interpretation is the document's role
within that operation, not the GitView product domain or its entities.

This interpretation is bounded to the named draft package and profile. The
metamodel context is captured separately from the project's selected domain
context, with package/version, source and IR hashes, compiler identity, mapping,
document digest and the actual applicability disposition bound to evidence.
An unresolved, contrary or unavailable disposition keeps the meta assessment
`unavailable`; invalid input remains `invalid`. Domain results can still be
reported for a separately requested domain assessment.

The interpretation does not publish sgcore or extend its authority to GitView's
domain, accept the GitView draft or its terms, declare a graph node from an ID,
approve a lifecycle mapping, or activate a global policy. It does not make
`review_examples` acceptance criteria or evidence. It does not require every
artifact to receive a separate approval ceremony. The first proposed evaluator
is the opt-in artifact identity/class check; it is not implemented by this file.

## Source declaration and alternative

The candidate source is SpecGraph's draft package
`org.0al.specgraph.core@0.1.0`, namespace `sgcore`:
`ontology/packages/specgraph-core/domain-ontology-package.yaml`, source SHA-256
`5bfa2ff40b6174def589546ab2fea2501e1f256c4f1446f36c45c7f3fffcd929`.
Its `modelApplicability` says `appliesTo.domains: [specgraph_core]`, excludes
`unrelated_product_domain`, and states `project_local_authority`: SpecGraph
core packages remain project-local unless explicitly published elsewhere.
The package also requires review of generated/imported ontology changes before
canonical SpecGraph specs are updated. These authored statements remain intact.

The proposed interpretation distinguishes the SpecGraph operation's subject
role from the external product domain. **The declaration does not itself state
that this distinction permits the proposed use.** In particular, running a
SpecGraph distribution for an external project raises a separate question about
the reach of `project_local_authority`; mere availability of a local copy is not
authorization to publish or extend the package's scope.

The reviewer may instead decide that the authored scope does not cover this
use. In that case, keep meta `unavailable` and prepare a separate proposal to
change the source applicability or select a separately governed metamodel.
An adapter or selection profile must not silently waive an exclusion or recast
the existing declaration as an approval. No Ontology library defect is asserted
solely by this question.

## Source-bound consumer observation

GitView's local report commit `5cd14e21b2fb04f0111db9b670b951af92fc66ef`
contains `docs/drafts/sgcore-applicability-3131f3c1.md` (SHA-256
`08d5480919156b4f39a74a21386b15f63ea0754391d8e9750ea96a0fd22b97f2`),
with `docs/drafts/evidence/sgcore-applicability-3131f3c1/inputs.json` (SHA-256
`3167a74bc6e5b2f359c98229f44b7d8fe1aa058300019f2e73eab983f17b2b99`) and
`results.json` (SHA-256
`40f7c782d001241a7ada35bb6138926e2da25d1b2ec9be1fe4ba728ba6d1bab7`).
These are local consumer artifacts; their presence and hashes do not authenticate
an approval. Their complete raw reports remain in the GitView repository.

The consumer froze GitView at `815405d7fc4707afee8c66ba7f8972d15cc3d86c` and
checked byte-identical isolated copies of the real pre-canonical draft
`GITVIEW-SPEC-0001`, SHA-256
`56fd32cf5118687e2b14d8058fa35ca644e19b91f67b2091bb09b5fcd3ca7d4f`, using
SpecGraph runtime `3131f3c170c49fc416ff73745aad076e15ba53f2`. The draft has not
yet incorporated later product agreements and is a reproducible technical
control, not evidence of a complete product specification.

The report observes domain `analyzed` and meta `unavailable` when both are
requested. Meta-only is also `unavailable`, with no domain analysis. These are
results of the current supported scope boundary, not execution or approval of
the candidate profile. `acceptance`, `acceptance_evidence` and `evidence` are
absent in the input; three textual `review_examples` remain examples. The
`motivcore:Motive` reference remains a separate domain concern.

## Decision record to complete

The reviewer must choose and source one of these dispositions:

1. **Accept this bounded interpretation:** name the authorized decision source,
   exact profile and pinned package declaration, and the permitted artifact role.
   This supports a separately reviewed opt-in implementation, not automatic
   canonical publication or blanket package applicability.
2. **Reject or defer:** retain `unavailable`, state the reason and identify the
   separate source-scope proposal or other metamodel needed to proceed.

Until an actual decision is recorded, the status remains
`pending_human_review`. Profile implementation, runtime activation, release and
consumer verification are distinct later events. No compiler or evaluator was
executed by preparing this document.
