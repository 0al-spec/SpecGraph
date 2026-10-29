"""A required unavailable check prevents verified context."""

from specification_core import PredicateSpec

from .model import ContextFacts

UNAVAILABLE_SPEC = PredicateSpec[ContextFacts](
    lambda facts: any(check.outcome == "unavailable" for check in facts.checks),
    name="project_ontology_context.unavailable",
)
