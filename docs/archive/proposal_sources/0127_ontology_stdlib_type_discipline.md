# Source Draft: Ontology Standard Library Type Discipline

This source draft records the operator-provided proposal intent for
SG-RFC-0127.

## Operator Intent

The operator clarified the desired mental model for Ontology integration:

```text
Entities directly owned by Ontology should be treated like base types or
standard-library types in programming languages. They do not need to inherit
from local SpecGraph concepts, and spec-authoring agents should not redefine
them when they are already available.
```

The practical purpose is to reduce:

- hallucinated terms;
- local aliases that duplicate accepted vocabulary;
- use of terms outside their bounded context;
- accidental promotion of observed terms into accepted ontology terms;
- confusing display of SpecGraph topology edges as ontology relations.

## Requested Process Change

The requested process change is:

```text
accepted Ontology entity -> canonical type symbol / semantic stdlib term
SpecGraph term -> usage or binding in a concrete graph artifact
Proposal term -> candidate concept until reviewed
Practical ontology term -> observed evidence only, never authority
Unknown term -> ontology_gap or candidate_term, not accepted vocabulary
```

Agents should resolve and import the active ontology frame before writing
graph-facing artifacts. If an accepted term exists, the agent should bind to it
instead of inventing a new name. If no accepted term exists, the agent should
emit an explicit gap with reason, evidence, source refs, and review status.

## Requested SpecSpace UX Correction

The operator noticed that practical ontology relations may contain entries like:

```text
<long spec title>--REFINES--<long parent title>
```

Those entries are correct graph topology facts, but they are confusing inside
an ontology view because they look like accepted semantic relations. The
requested correction is to keep them visible as evidence while separating them
from canonical or candidate semantic relations.

The preferred presentation is:

```text
SG-SPEC-0041 refines SG-SPEC-0034
```

with titles, source paths, and evidence details available in the detail view.

## Desired Stacked Work

The desired stack is:

1. Record the process contract in SpecGraph as a bounded proposal.
2. Update SpecSpace practical ontology so it separates semantic vocabulary,
   candidate gaps, canonical bindings, graph topology edges, and proposal refs.
3. Add a SpecGraph policy or gate requiring new generated terms to become
   ontology gaps rather than accepted terms.
4. Later introduce the first real accepted ontology package slice as a semantic
   standard library, once the review boundary is stable.

## Boundary

This proposal is not a request to implement a full programming-language type
system. It is a request for a soft type discipline:

```text
observed term -> proposed term -> accepted term -> deprecated/rejected term
```

The first implementation should remain MVP-sized and review-first.
