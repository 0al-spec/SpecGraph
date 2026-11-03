"""Authority limits carried by one metamodel assessment, not an attestation."""

from dataclasses import dataclass

from specification_core import PredicateSpec


@dataclass(frozen=True, slots=True)
class MetaAuthorityFacts:
    decision_provenance: object
    node_membership: object
    lifecycle: object
    semantic_approval: object
    canonical_mutations_allowed: object


META_AUTHORITY_BOUNDARY_SPEC = PredicateSpec[MetaAuthorityFacts](
    lambda facts: (
        facts.decision_provenance == "caller_attributed_not_attested"
        and facts.node_membership == "not_assessed"
        and facts.lifecycle == "not_assessed"
        and facts.semantic_approval == "not_established"
        and facts.canonical_mutations_allowed is False
    ),
    name="project_ontology_meta.authority_boundary",
)
