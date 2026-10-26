# RFC 0221: bounded Intent graph source extension

The [retained implementation request](../archive/proposal_sources/0221_intent_graph_source_extension.md#intent-graph-source-follow-up)
authorizes the missing persistence seam found by the CN-CAPTURE pilot: canonical
Intent roots and explicit Requirement-to-Intent `derived_from` relations. These
are existing semantic kinds under SG-SPEC-0001/0023/0061. The
[physical extension contract](../subject_intent_graph.md) is a bounded supplement
to the Requirement/criterion storage implementation, not another subject class
or a change to their approved version-1 records.

The implemented follow-up uses one optional `specs/intent_graph.yaml` file on the
existing dedicated source ref. A version-2 request binds that complete graph and
can publish it with subject origins in one atomic Git transaction. Exact reviewed
graph bytes, original human sources, scoped origin effects and final request
permission use the existing publication gate. First-version operations only add
immutable revision-1 Intent origins and exact revision-pinned links; existing
records cannot be rewritten and criterion membership supplies no implicit path.

`tests/test_subject_intent_graph.py` exercises real temporary Git publication,
explicit path lookup, malformed endpoints, append preservation, complete review
binding, missing permission and concurrent publication. Older subject interfaces
and request digests retain their previous contract. Actual CN-CAPTURE allocation,
canonical adoption and evidence transfer still require their final reviewed scope.
