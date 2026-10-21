"""Immutable inputs and results for the existing verifiability proxy."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ScoreThreshold:
    score: float | None
    minimum_score: float


@dataclass(frozen=True)
class AcceptanceCoverage:
    status: str
    score: float | None


@dataclass(frozen=True)
class VerifiabilityContext:
    observations: tuple[AcceptanceCoverage, ...]
    minimum_score: float
    trigger_signal: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))


@dataclass(frozen=True)
class VerifiabilityResult:
    score: float | None
    minimum_score: float
    threshold_gap: float | None
    status: str
    trigger_signal: str
    relevant_spec_count: int
    status_counts: tuple[tuple[str, int], ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "metric_id": "specification_verifiability",
            "title": "Specification Verifiability",
            "score": self.score,
            "minimum_score": self.minimum_score,
            "threshold_gap": self.threshold_gap,
            "status": self.status,
            "trigger_signal": self.trigger_signal,
            "signal_emitted": self.status == "below_threshold",
            "basis": (
                "Derived from acceptance coverage in the trace plane. "
                "This remains a weak bootstrap measure until "
                "criterion-level evidence mapping exists."
            ),
            "input_summary": {
                "relevant_spec_count": self.relevant_spec_count,
                "acceptance_status_counts": dict(self.status_counts),
            },
        }


class VerifiabilityMetric(Protocol):
    def evaluate(self, context: VerifiabilityContext) -> VerifiabilityResult: ...
