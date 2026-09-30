"""Apply the named lifecycle state specifications to one artifact context."""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from specification_core import TraceEvent, TraceRecorder

from idea_maturity_candidate_approval_decision_spec import candidate_approval_decision_state
from idea_maturity_candidate_approval_intent_spec import candidate_approval_intent_state
from idea_maturity_candidate_approval_spec import candidate_approval_state
from idea_maturity_lifecycle_context import LifecycleStateContext
from idea_maturity_platform_promotion_spec import platform_promotion_state
from idea_maturity_promotion_execution_spec import promotion_execution_state
from idea_maturity_promotion_request_spec import promotion_request_state
from idea_maturity_read_model_publication_spec import read_model_publication_state
from idea_maturity_review_spec import review_status

T = TypeVar("T")
C = TypeVar("C", contravariant=True)


class Decision(Protocol[C]):
    def __call__(self, context: C, *, recorder: TraceRecorder | None = None) -> str: ...


@dataclass(frozen=True)
class SpecField(Generic[T]):
    name: str
    decide: Decision[T]


@dataclass(frozen=True)
class SpecFieldTrace:
    field_name: str
    value: str
    events: tuple[TraceEvent, ...]


@dataclass(frozen=True)
class SpecSet(Generic[T]):
    fields: tuple[SpecField[T], ...]

    def __post_init__(self) -> None:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("SpecSet field names must be unique")

    def apply(self, context: T, *, trace: list[SpecFieldTrace] | None = None) -> dict[str, str]:
        values = {}
        for field in self.fields:
            recorder = TraceRecorder() if trace is not None else None
            values[field.name] = field.decide(context, recorder=recorder)
            if trace is not None and recorder is not None:
                if not recorder.events:
                    raise ValueError(f"SpecSet field {field.name!r} did not record a decision")
                if not recorder.events:
                    raise ValueError(f"SpecSet field {field.name!r} did not record a decision")
                trace.append(SpecFieldTrace(field.name, values[field.name], recorder.events))
        return values


LIFECYCLE_STATES = SpecSet(
    (
        SpecField("candidate_approval_state", candidate_approval_state),
        SpecField("candidate_approval_intent_state", candidate_approval_intent_state),
        SpecField("candidate_approval_decision_state", candidate_approval_decision_state),
        SpecField("platform_promotion_state", platform_promotion_state),
        SpecField("promotion_request_state", promotion_request_state),
        SpecField("promotion_execution_state", promotion_execution_state),
        SpecField("review_status", review_status),
        SpecField("read_model_publication_state", read_model_publication_state),
    )
)


def lifecycle_state_values(artifacts, *, trace=None):
    return LIFECYCLE_STATES.apply(LifecycleStateContext(artifacts), trace=trace)
