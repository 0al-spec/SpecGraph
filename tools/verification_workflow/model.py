"""Immutable inputs, operation descriptors and stage records for the fixed profile."""

import json
import re
from dataclasses import dataclass, replace
from enum import Enum

from traceability.criterion import CriterionEvidence, CriterionSource, FilePin, PassportIdentity


class Stage(str, Enum):
    PIN = "pin"
    EXECUTE = "execute"
    COLLECT = "collect"
    REPORT = "report"


class Port(str, Enum):
    REQUEST = "verification_request"
    PINNED = "pinned_verification_inputs"
    EXECUTION = "test_execution_record"
    COLLECTION = "criterion_evidence"
    REPORT = "verification_report"


class Effect(str, Enum):
    READ_SOURCE = "read_source"
    EXECUTE_TEST = "execute_test"
    READ_OUTPUT = "read_output"
    WRITE_OUTPUT = "write_output"


class Status(str, Enum):
    NOT_RUN = "not_run"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    INCOMPLETE = "incomplete"
    SKIPPED = "skipped"


def revision(value: str) -> None:
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value):
        raise ValueError("a full Git revision is required")


@dataclass(frozen=True)
class ToolPin:
    identity: str
    version: str
    sha256: str

    def __post_init__(self) -> None:
        if not self.identity or not self.version or not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("tool identity, version and SHA-256 are required")


@dataclass(frozen=True)
class Operation:
    identity: str
    version: str
    stage: Stage
    input_port: Port
    output_port: Port
    adapter: ToolPin
    effects: frozenset[Effect]

    def __post_init__(self) -> None:
        object.__setattr__(self, "effects", frozenset(self.effects))


@dataclass(frozen=True)
class OperationRegistry:
    version: str
    operations: tuple[Operation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "operations", tuple(self.operations))


@dataclass(frozen=True)
class WorkflowStep:
    stage: Stage
    operation_id: str
    operation_version: str
    input_from: Stage | None
    mandatory: bool = True


@dataclass(frozen=True)
class WorkflowDefinition:
    profile: str
    steps: tuple[WorkflowStep, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))


@dataclass(frozen=True)
class ExpectedMeasurement:
    assertion_id: str
    media_type: str
    expected_json: str

    def __post_init__(self) -> None:
        value = json.loads(self.expected_json)
        if not self.assertion_id or not self.media_type or not isinstance(value, dict):
            raise ValueError("assertion identity, media type and a JSON object are required")
        object.__setattr__(self, "expected_json", json.dumps(value, sort_keys=True))


@dataclass(frozen=True)
class CriterionTarget:
    source: CriterionSource
    criterion_id: str
    contract_ref_id: str
    passport_binding_id: str
    expectations: tuple[ExpectedMeasurement, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "expectations", tuple(self.expectations))


@dataclass(frozen=True)
class PassportPin:
    artifact: FilePin
    identity: PassportIdentity


@dataclass(frozen=True)
class VerificationScope:
    workspace: str
    repository_id: str
    spec_id: str
    declaration_revision: str
    execution_revision: str
    test_revision: str
    spec: FilePin
    passport: PassportPin
    binding_template: FilePin
    criteria: tuple[CriterionTarget, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "criteria", tuple(self.criteria))
        for value in (self.declaration_revision, self.execution_revision, self.test_revision):
            revision(value)


@dataclass(frozen=True)
class VerificationRequest:
    request_id: str
    scope: VerificationScope
    definition: WorkflowDefinition
    registry: OperationRegistry


@dataclass(frozen=True)
class RunScope:
    request: VerificationRequest
    run_id: str


@dataclass(frozen=True)
class StageArtifact:
    owner: RunScope
    stage: Stage
    artifact_id: str
    file: FilePin


@dataclass(frozen=True)
class PinRecord:
    owner: RunScope
    status: Status
    inventory_complete: bool
    sources_compatible: bool


@dataclass(frozen=True)
class ExecutionRecord:
    owner: RunScope
    status: Status
    execution_revision: str
    producer_run_id: str | None
    exit_code: int | None
    journals: tuple[StageArtifact, ...]
    binding_plan: StageArtifact | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "journals", tuple(self.journals))
        revision(self.execution_revision)


@dataclass(frozen=True)
class CollectionRecord:
    owner: RunScope
    status: Status
    consumed_journals: tuple[StageArtifact, ...]
    consumed_plan: StageArtifact | None
    evidence: CriterionEvidence | None
    artifact: StageArtifact | None
    exit_code: int | None
    provider: ToolPin

    def __post_init__(self) -> None:
        object.__setattr__(self, "consumed_journals", tuple(self.consumed_journals))
        if self.evidence is not None:
            object.__setattr__(self, "evidence", frozen_evidence(self.evidence))


@dataclass(frozen=True)
class ReportRecord:
    owner: RunScope
    status: Status
    consumed_collection: StageArtifact | None
    artifact: StageArtifact | None


@dataclass(frozen=True)
class Finalization:
    owner: RunScope
    inputs_unchanged: bool


def frozen_evidence(evidence: CriterionEvidence) -> CriterionEvidence:
    """Capture nested provider collections, including direct Python API callers."""

    def binding(value):
        return replace(value, assertions=tuple(value.assertions))

    rows = []
    for row in evidence.rows:
        observation = row.observation
        if observation is not None:
            observation = replace(
                observation,
                steps=tuple(observation.steps),
                case_step_statuses=tuple(tuple(item) for item in observation.case_step_statuses),
                findings=tuple(observation.findings),
            )
        rows.append(
            replace(
                row,
                bindings=tuple(binding(b) for b in row.bindings),
                findings=tuple(row.findings),
                observation=observation,
            )
        )
    return replace(
        evidence,
        rows=tuple(rows),
        findings=tuple(evidence.findings),
        declared_journals=tuple(evidence.declared_journals),
        unmatched_bindings=tuple(binding(b) for b in evidence.unmatched_bindings),
    )


@dataclass(frozen=True)
class RunRecords:
    owner: RunScope
    pin: PinRecord | None = None
    execution: ExecutionRecord | None = None
    collection: CollectionRecord | None = None
    report: ReportRecord | None = None
    finalization: Finalization | None = None

    @property
    def statuses(self) -> tuple[Status, ...]:
        return tuple(
            record.status if record else Status.NOT_RUN
            for record in (
                self.pin,
                self.execution,
                self.collection,
                self.report,
            )
        )


@dataclass(frozen=True)
class CompletionFacts:
    rejected: bool
    finalized: bool
    linkage_valid: bool
    collection_valid: bool
    statuses: tuple[Status, ...]
    producer_exit: int | None
    collector_exit: int | None
    inventory_complete: bool
    criterion_count: int
    outcomes: tuple[str, ...]
    bindings_checked: bool
