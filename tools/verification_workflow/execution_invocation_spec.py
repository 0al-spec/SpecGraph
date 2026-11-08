"""A producer must emit the current challenge within an actually open test step."""

from dataclasses import dataclass

from specification_core import PredicateSpec

from .execution_model import InvocationIdentity


@dataclass(frozen=True)
class InvocationEmission:
    expected: InvocationIdentity
    observed: InvocationIdentity
    run_start: int
    case_start: int
    step_start: int
    attachment: int
    step_finish: int
    case_finish: int


EXECUTION_INVOCATION_SPEC: PredicateSpec[InvocationEmission] = PredicateSpec(
    lambda c: (
        c.observed == c.expected
        and c.run_start < c.case_start < c.step_start < c.attachment < c.step_finish < c.case_finish
    ),
    name="verification.producer_invocation_correlation",
)
