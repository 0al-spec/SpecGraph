"""Small, explicit wrapper for applying named decisions to one typed context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from specification_core import TraceEvent, TraceRecorder

Context = TypeVar("Context")
DecisionContext = TypeVar("DecisionContext", contravariant=True)


class SpecDecision(Protocol[DecisionContext]):
    def __call__(
        self,
        context: DecisionContext,
        *,
        recorder: TraceRecorder | None = None,
    ) -> str: ...


@dataclass(frozen=True)
class SpecField(Generic[Context]):
    name: str
    decide: SpecDecision[Context]


@dataclass(frozen=True)
class SpecFieldTrace:
    field_name: str
    value: str
    events: tuple[TraceEvent, ...]


@dataclass(frozen=True)
class SpecSet(Generic[Context]):
    fields: tuple[SpecField[Context], ...]

    def __post_init__(self) -> None:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("SpecSet field names must be unique")

    def apply(
        self,
        context: Context,
        *,
        trace: list[SpecFieldTrace] | None = None,
    ) -> dict[str, str]:
        """Evaluate once per field; require a complete event trace when requested."""
        values: dict[str, str] = {}
        for field in self.fields:
            recorder = TraceRecorder() if trace is not None else None
            values[field.name] = field.decide(context, recorder=recorder)
            if trace is not None and recorder is not None:
                if not recorder.events:
                    raise ValueError(f"SpecSet field {field.name!r} did not record a decision")
                trace.append(
                    SpecFieldTrace(
                        field_name=field.name,
                        value=values[field.name],
                        events=recorder.events,
                    )
                )
        return values
