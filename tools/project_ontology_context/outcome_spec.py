"""Choose the first failure while retaining the caller's success vocabulary."""

from typing import Literal

from specification_core import FirstMatch, TraceRecorder

from .invalid_spec import INVALID_SPEC
from .model import ContextFacts
from .unavailable_spec import UNAVAILABLE_SPEC

CONTEXT_FAILURE_SPEC = FirstMatch[ContextFacts, str | None].with_fallback(
    (
        (INVALID_SPEC, "invalid"),
        (UNAVAILABLE_SPEC, "unavailable"),
    ),
    None,
    name="project_ontology_context.failure_precedence",
)


def context_check_outcome(
    facts: ContextFacts,
    *,
    success: Literal["verified", "checked"],
    recorder: TraceRecorder | None = None,
) -> str:
    return CONTEXT_FAILURE_SPEC.decide(facts, recorder=recorder).value or success
