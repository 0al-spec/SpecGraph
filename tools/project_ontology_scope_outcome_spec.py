"""Completion requires a nonempty request with every requested scope analyzed."""

from specification_core import PredicateSpec

from project_ontology_check_scopes import ScopeFacts

REQUESTED_SCOPES_ANALYZED_SPEC = PredicateSpec[ScopeFacts](
    lambda facts: (
        bool(facts.requested)
        and len(facts.requested) == len(facts.outcomes)
        and all(outcome == "analyzed" for outcome in facts.outcomes)
    ),
    name="project_ontology_report.requested_scopes_analyzed",
)
