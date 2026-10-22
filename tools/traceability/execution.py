"""Immutable selection and retained execution observations; no collection."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from publication_evidence.context import ExecutionIdentity


@dataclass(frozen=True)
class PublicationExecutionSelection:
    identity: ExecutionIdentity
    tests_report: Path | None = None
    delivery_report: Path | None = None

    def __post_init__(self) -> None:
        paths = (self.tests_report, self.delivery_report)
        if not any(paths) or any(p is not None and not p.is_absolute() for p in paths):
            raise ValueError("select at least one explicit absolute execution report path")


@dataclass(frozen=True)
class ExecutionBindingFacts:
    repository: str
    expected: ExecutionIdentity
    observed: ExecutionIdentity


@dataclass(frozen=True)
class RetainedRuntimeBindingFacts:
    expected_revision: str
    observed_revision: str
    execution: ExecutionBindingFacts
    expected_bundle: tuple[str, str]
    observed_bundle: tuple[str, str]
    expected_origin: str
    observed_origin: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected_bundle", tuple(self.expected_bundle))
        object.__setattr__(self, "observed_bundle", tuple(self.observed_bundle))


@dataclass(frozen=True)
class ExecutionSignal:
    stage: str
    producer_result: str
    binding_status: str
    evaluated_result: str | None = None

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RetainedExecutionArtifact:
    role: str
    binding_status: str
    signals: tuple[ExecutionSignal, ...] = ()
    payload_json: bytes | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "signals", tuple(self.signals))
        if self.payload_json is not None:
            object.__setattr__(self, "payload_json", bytes(self.payload_json))

    def to_payload(self) -> dict[str, object]:
        return dict(
            role=self.role,
            binding_status=self.binding_status,
            signals=[s.to_payload() for s in self.signals],
            producer_report=json.loads(self.payload_json)
            if self.payload_json is not None
            else None,
        )


@dataclass(frozen=True)
class ExecutionEvidence:
    selected_run: ExecutionIdentity
    artifacts: tuple[RetainedExecutionArtifact, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(sorted(self.artifacts, key=lambda a: a.role)))
        if not self.artifacts or len({a.role for a in self.artifacts}) != len(self.artifacts):
            raise ValueError("execution evidence requires distinct explicitly selected artifacts")

    def to_payload(self) -> dict[str, object]:
        return dict(
            selected_run=asdict(self.selected_run),
            freshness="selected_revision_and_run_only",
            trust_model="provider_reported_not_attested",
            artifacts=[a.to_payload() for a in self.artifacts],
        )
