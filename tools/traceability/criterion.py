"""Immutable criterion selections, assertions and observations."""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from intent_decision_review.sources import normalized_path

FindingKind = Literal["invalid", "unavailable", "conflict"]
BindingIntegrity = Literal["checked", "unbound", "unavailable", "invalid", "conflict"]
Outcome = Literal["passed", "failed", "skipped", "pending", "partial", "unavailable"]


@dataclass(frozen=True)
class FilePin:
    path: str
    sha256: str

    def __post_init__(self) -> None:
        normalized_path(self.path)
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("file pin requires a lowercase SHA-256")


@dataclass(frozen=True)
class CriterionSelection:
    workspace: str
    spec: FilePin
    passport: FilePin
    plan: FilePin
    retained_root: Path
    journals: tuple[tuple[str, FilePin], ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "journals",
            tuple(sorted(((key, pin) for key, pin in self.journals), key=lambda p: p[0])),
        )
        if not self.workspace or not self.retained_root.is_absolute():
            raise ValueError("criterion selection requires a workspace and absolute retained root")
        ids = [key for key, _ in self.journals]
        if not all(ids) or len(ids) != len(set(ids)):
            raise ValueError("select each explicit journal ID at most once")

    def to_payload(self) -> dict:
        return dict(
            workspace=self.workspace,
            spec=asdict(self.spec),
            passport=asdict(self.passport),
            plan=asdict(self.plan),
            journals={key: asdict(pin) for key, pin in self.journals},
        )


@dataclass(frozen=True)
class CriterionSource:
    path: str
    revision: str
    sha256: str
    pointer: str
    text: str


@dataclass(frozen=True)
class PassportIdentity:
    passport_id: str
    feature_id: str
    version: str
    status: str
    validator_sha256: str
    validator_contract_revision: str
    schema_sha256: str


@dataclass(frozen=True)
class PassportBindingFacts:
    selected_text: str
    passport_text: str | None
    provider: str | None
    relation: str | None
    selected_locator: tuple[tuple[str, str], ...]
    passport_locator: tuple[tuple[str, str | None], ...]
    criterion_id: str
    contract_ref_id: str
    declared_criteria: tuple[str, ...]
    declared_contracts: tuple[str, ...]
    test_elements: tuple[str, ...]


@dataclass(frozen=True)
class JournalDeclaration:
    artifact_id: str
    sha256: str
    run_id: str
    test_source_revision: str
    execution_source_revision: str
    feature: FilePin

    def to_payload(self) -> dict:
        return {**asdict(self), "execution_source_provenance": "producer_declared"}


@dataclass(frozen=True)
class ExpectedAssertion:
    id: str
    step_id: str
    media_type: str
    expected_json: str

    def to_payload(self) -> dict:
        return dict(
            id=self.id,
            step_id=self.step_id,
            media_type=self.media_type,
            expected_measurement=json.loads(self.expected_json),
        )


@dataclass(frozen=True)
class CriterionBinding:
    pointer: str
    criterion_id: str
    contract_ref_id: str
    passport_binding_id: str
    artifact_id: str
    case_id: str
    case_started_id: str
    attempt: int
    assertions: tuple[ExpectedAssertion, ...]

    def to_payload(self) -> dict:
        return {
            **{key: value for key, value in vars(self).items() if key != "assertions"},
            "assertions": [a.to_payload() for a in self.assertions],
        }


@dataclass(frozen=True, order=True)
class CriterionFinding:
    kind: FindingKind
    code: str
    detail: str = ""


@dataclass(frozen=True)
class StepObservation:
    assertion: ExpectedAssertion
    pickle_step_id: str | None = None
    step_text: str | None = None
    producer_status: str | None = None
    measurement_json: str | None = None

    def to_payload(self) -> dict:
        return {
            **self.assertion.to_payload(),
            "pickle_step_id": self.pickle_step_id,
            "step_text": self.step_text,
            "producer_status": self.producer_status,
            "observed_measurement": (
                json.loads(self.measurement_json) if self.measurement_json is not None else None
            ),
        }


@dataclass(frozen=True)
class AttemptObservation:
    pickle_id: str | None = None
    run_success: bool | None = None
    case_finished: bool = False
    will_be_retried: bool | None = None
    case_step_statuses: tuple[tuple[str, str | None], ...] = ()
    steps: tuple[StepObservation, ...] = ()
    findings: tuple[CriterionFinding, ...] = ()

    def to_payload(self) -> dict:
        return {
            "pickle_id": self.pickle_id,
            "run_success": self.run_success,
            "case_finished": self.case_finished,
            "will_be_retried": self.will_be_retried,
            "case_step_statuses": dict(self.case_step_statuses),
            "steps": [s.to_payload() for s in self.steps],
        }


@dataclass(frozen=True)
class CriterionDecisionFacts:
    has_binding: bool
    findings: frozenset[FindingKind]
    run_success: bool | None = None
    case_finished: bool = False
    step_statuses: frozenset[str | None] = frozenset()
    measurements_complete: bool = False
    measurement_mismatch: bool = False


@dataclass(frozen=True)
class CriterionRow:
    source: CriterionSource
    bindings: tuple[CriterionBinding, ...]
    binding_integrity: BindingIntegrity
    observed_outcome: Outcome
    findings: tuple[CriterionFinding, ...] = ()
    journal: JournalDeclaration | None = None
    observation: AttemptObservation | None = None

    def to_payload(self) -> dict:
        return dict(
            source=asdict(self.source),
            bindings=[b.to_payload() for b in self.bindings],
            binding_integrity=self.binding_integrity,
            observed_outcome=self.observed_outcome,
            admission="not_evaluated",
            findings=[asdict(f) for f in self.findings],
            journal=self.journal.to_payload() if self.journal else None,
            observation=self.observation.to_payload() if self.observation else None,
        )


@dataclass(frozen=True)
class CriterionEvidence:
    selection: CriterionSelection
    inventory_complete: bool
    rows: tuple[CriterionRow, ...]
    passport: PassportIdentity | None = None
    findings: tuple[CriterionFinding, ...] = ()

    declared_journals: tuple[JournalDeclaration, ...] = ()
    unmatched_bindings: tuple[CriterionBinding, ...] = ()

    def to_payload(self) -> dict:
        return dict(
            selection=self.selection.to_payload(),
            inventory=dict(
                scope="whole_spec",
                complete=self.inventory_complete,
                criterion_count=len(self.rows) if self.inventory_complete else None,
            ),
            passport=asdict(self.passport) if self.passport else None,
            findings=[asdict(f) for f in self.findings],
            declared_journals=[journal.to_payload() for journal in self.declared_journals],
            unmatched_bindings=[binding.to_payload() for binding in self.unmatched_bindings],
            criteria=[row.to_payload() for row in self.rows],
        )
