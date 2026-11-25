"""Aggregate prepared scope facts without interpreting or validating report shapes."""

from typing import Literal

from specification_core import FirstMatch, TraceRecorder

from project_ontology_check_scopes import ScopeFacts
from project_ontology_scope_invalid_spec import REQUESTED_SCOPE_INVALID_SPEC
from project_ontology_scope_outcome_spec import REQUESTED_SCOPES_ANALYZED_SPEC

ScopeOutcome = Literal["invalid", "analyzed", "unavailable"]

SCOPE_OUTCOME_SPEC = FirstMatch[ScopeFacts, ScopeOutcome].with_fallback(
    (
        (REQUESTED_SCOPE_INVALID_SPEC, "invalid"),
        (REQUESTED_SCOPES_ANALYZED_SPEC, "analyzed"),
    ),
    "unavailable",
    name="project_ontology_report.scope_outcome",
)


def scope_check_outcome(
    facts: ScopeFacts, *, recorder: TraceRecorder | None = None
) -> ScopeOutcome:
    return SCOPE_OUTCOME_SPEC.decide(facts, recorder=recorder).value
