"""A detected invalidity in a requested scope takes precedence over completion."""

from specification_core import PredicateSpec

from project_ontology_check_scopes import ScopeFacts

REQUESTED_SCOPE_INVALID_SPEC = PredicateSpec[ScopeFacts](
    lambda facts: "invalid" in facts.outcomes,
    name="project_ontology_report.requested_scope_invalid",
)
