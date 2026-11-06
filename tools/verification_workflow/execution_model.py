"""Explicit collaborators for the bounded POSIX, single-journal execution profile."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .model import ToolPin, VerificationRequest
from .run import VerificationResult


@dataclass(frozen=True)
class ExecutionSettings:
    repository: Path
    output_root: Path


@dataclass(frozen=True)
class InvocationIdentity:
    request_id: str
    workflow_run_id: str
    nonce: str

    def to_payload(self) -> dict[str, str]:
        return {
            "profile": "specgraph.execution-invocation/v1",
            "request_id": self.request_id,
            "workflow_run_id": self.workflow_run_id,
            "nonce": self.nonce,
        }


@dataclass(frozen=True)
class ProducerContext:
    request: VerificationRequest
    run_id: str
    snapshot: Path
    output: Path
    invocation: InvocationIdentity | None = None


@dataclass(frozen=True)
class ProducerCommand:
    argv: tuple[str, ...]
    cwd: Path
    environment: tuple[tuple[str, str], ...]
    timeout_seconds: float
    executable_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "argv", tuple(self.argv))
        object.__setattr__(self, "environment", tuple(tuple(p) for p in self.environment))


@dataclass(frozen=True)
class BoundCriterion:
    pointer: str
    case_id: str
    case_started_id: str
    attempt: int
    steps: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(tuple(p) for p in self.steps))


@dataclass(frozen=True)
class BoundRun:
    producer_run_id: str
    criteria: tuple[BoundCriterion, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "criteria", tuple(self.criteria))


class ProducerAdapter(Protocol):
    identity: ToolPin
    implementation: Path

    def prepare(self, context: ProducerContext) -> None:
        """Explicit reviewed dependency preparation; tracked snapshot must not change."""

    def command(self, context: ProducerContext) -> ProducerCommand:
        """The runtime supplies SPECGRAPH_VERIFICATION_INVOCATION, which must not be overridden.

        The runner must emit this challenge during selected case execution using
        the supported observation transport; see execution_invocation. A wrapper
        copying or annotating retained results does not implement that contract.
        """

    def journals(self, context: ProducerContext) -> tuple[Path, ...]:
        """Return one new journal; its path alone does not prove fresh observations."""

    def bind(self, context: ProducerContext, journal: bytes) -> BoundRun:
        """Return fresh identities only; the operation retains all expectations."""


@dataclass(frozen=True)
class ExecutionOutcome:
    directory: Path
    result: VerificationResult
