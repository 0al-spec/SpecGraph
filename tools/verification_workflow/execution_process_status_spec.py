"""Process completion and process-group finality are distinct from test success."""

from dataclasses import dataclass

from specification_core import FirstMatch, PredicateSpec

from .model import Status


@dataclass(frozen=True)
class ProcessCompletion:
    exit_code: int
    timed_out: bool
    descendants_remaining: bool


PROCESS_STATUS_SPEC: FirstMatch[ProcessCompletion, Status] = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(lambda c: c.timed_out or c.exit_code < 0, name="producer.interrupted"),
            Status.ABORTED,
        ),
        (
            PredicateSpec(lambda c: c.descendants_remaining, name="producer.children_unfinished"),
            Status.FAILED,
        ),
    ),
    Status.COMPLETED,
    name="verification.process_completion",
)
