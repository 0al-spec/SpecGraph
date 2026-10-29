"""A detected invalidity takes priority over unavailable verification."""

from specification_core import PredicateSpec

from .model import ContextFacts

INVALID_SPEC = PredicateSpec[ContextFacts](
    lambda facts: any(check.outcome == "invalid" for check in facts.checks),
    name="project_ontology_context.invalid",
)
