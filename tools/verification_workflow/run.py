"""Pure immutable run transitions for adapters; never invokes an operation itself."""

from dataclasses import asdict, dataclass, replace

from traceability.criterion import CriterionEvidence

from .collection_spec import COLLECTION_SCOPE_SPEC
from .lifecycle_spec import WORKFLOW_LIFECYCLE_SPEC
from .linkage_spec import RUN_LINKAGE_SPEC
from .model import (
    CollectionRecord,
    CompletionFacts,
    ExecutionRecord,
    Finalization,
    PinRecord,
    ReportRecord,
    RunRecords,
    RunScope,
    Stage,
    Status,
    VerificationRequest,
)
from .profile_spec import FIXED_PROFILE_SPEC
from .scope_spec import PINNED_SCOPE_SPEC
from .verdict_spec import VERIFICATION_VERDICT_SPEC


@dataclass(frozen=True)
class VerificationResult:
    records: RunRecords
    workflow_outcome: str
    verification_outcome: str
    findings: tuple[str, ...]

    @property
    def evidence(self) -> CriterionEvidence | None:
        return self.records.collection.evidence if self.records.collection else None

    def to_payload(self) -> dict[str, object]:
        """A diagnostic projection; missing observed rows cannot shrink the inventory."""
        request = self.records.owner.request
        scope = request.scope
        evidence = self.evidence
        rows = evidence.rows if evidence else ()
        return {
            "artifact_kind": "verification_workflow_result",
            "schema_version": 1,
            "request_id": request.request_id,
            "run_id": self.records.owner.run_id,
            "profile": request.definition.profile,
            "workflow_outcome": self.workflow_outcome,
            "verification_outcome": self.verification_outcome,
            "stages": {
                s.value: status.value
                for s, status in zip(Stage, self.records.statuses, strict=True)
            },
            "scope": "local_test",
            "execution_source_provenance": "producer_declared",
            "admission": "not_evaluated",
            "receipt": None,
            "canonical_mutations_allowed": False,
            "findings": list(self.findings),
            "pinned_scope": asdict(scope),
            "criteria": [
                {
                    "target": asdict(target),
                    "observations": [
                        row.to_payload() for row in rows if row.source == target.source
                    ],
                }
                for target in scope.criteria
            ],
            "collection": evidence.to_payload() if evidence else None,
        }


@dataclass(frozen=True)
class VerificationRun:
    records: RunRecords
    used_run_ids: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "used_run_ids", frozenset(self.used_run_ids))

    @classmethod
    def begin(
        cls,
        request: VerificationRequest,
        run_id: str,
        *,
        used_run_ids: frozenset[str],
    ) -> "VerificationRun":
        """The caller supplies its existing run inventory; this is not persistent allocation."""
        return cls(RunRecords(RunScope(request, run_id)), used_run_ids)

    @property
    def rejection_findings(self) -> tuple[str, ...]:
        owner = self.records.owner
        findings = []
        if not owner.run_id or owner.run_id in self.used_run_ids:
            findings.append("run_id_unavailable")
        if not owner.request.request_id:
            findings.append("request_id_missing")
        if not FIXED_PROFILE_SPEC.is_satisfied_by(owner.request):
            findings.append("fixed_profile_invalid")
        if not PINNED_SCOPE_SPEC.is_satisfied_by(owner.request.scope):
            findings.append("pinned_scope_invalid")
        return tuple(findings)

    def _expect(self, stage: Stage) -> None:
        if self.rejection_findings:
            raise ValueError("rejected preflight: " + ", ".join(self.rejection_findings))
        if self.records.finalization is not None:
            raise ValueError("a finalized run cannot accept more stages")
        present = (
            self.records.pin,
            self.records.execution,
            self.records.collection,
            self.records.report,
        )
        next_stage = next(
            (s for s, value in zip(Stage, present, strict=True) if value is None), None
        )
        if next_stage != stage:
            raise ValueError(f"expected stage {next_stage}, received {stage}")

    @property
    def next_stage(self) -> Stage | None:
        """Adapters inspect this before doing work; rejected runs expose no operation."""
        if self.rejection_findings or self.records.finalization is not None:
            return None
        present = (
            self.records.pin,
            self.records.execution,
            self.records.collection,
            self.records.report,
        )
        stage = next((s for s, value in zip(Stage, present, strict=True) if value is None), None)
        pin = self.records.pin
        if stage == Stage.EXECUTE and (
            pin.owner != self.records.owner
            or pin.status != Status.COMPLETED
            or not pin.sources_compatible
        ):
            return None
        return stage

    def with_pin(self, record: PinRecord) -> "VerificationRun":
        self._expect(Stage.PIN)
        return replace(self, records=replace(self.records, pin=record))

    def with_execution(self, record: ExecutionRecord) -> "VerificationRun":
        self._expect(Stage.EXECUTE)
        pin = self.records.pin
        if pin.owner != self.records.owner or pin.status != Status.COMPLETED:
            raise ValueError("execution requires a completed current-run pin")
        if not pin.sources_compatible:
            raise ValueError("execution requires compatible pinned sources")
        return replace(self, records=replace(self.records, execution=record))

    def with_collection(self, record: CollectionRecord) -> "VerificationRun":
        self._expect(Stage.COLLECT)
        return replace(self, records=replace(self.records, collection=record))

    def with_report(self, record: ReportRecord) -> "VerificationRun":
        self._expect(Stage.REPORT)
        return replace(self, records=replace(self.records, report=record))

    def finalized(self, finalization: Finalization) -> "VerificationRun":
        if self.records.finalization is not None:
            raise ValueError("a finalized run cannot be reopened")
        return replace(self, records=replace(self.records, finalization=finalization))

    def result(self) -> VerificationResult:
        records = self.records
        rejected = self.rejection_findings
        linkage = RUN_LINKAGE_SPEC.is_satisfied_by(records)
        collection_valid = not rejected and COLLECTION_SCOPE_SPEC.is_satisfied_by(records)
        evidence = records.collection.evidence if records.collection else None
        facts = CompletionFacts(
            rejected=bool(rejected),
            finalized=records.finalization is not None,
            linkage_valid=linkage,
            collection_valid=collection_valid,
            statuses=records.statuses,
            producer_exit=records.execution.exit_code if records.execution else None,
            collector_exit=records.collection.exit_code if records.collection else None,
            inventory_complete=bool(
                records.pin
                and records.pin.inventory_complete
                and evidence
                and evidence.inventory_complete
            ),
            criterion_count=len(records.owner.request.scope.criteria),
            outcomes=tuple(row.observed_outcome for row in evidence.rows) if evidence else (),
            bindings_checked=bool(
                evidence is not None
                and all(
                    row.binding_integrity == "checked" and not row.findings for row in evidence.rows
                )
            ),
        )
        findings = list(rejected)
        if not linkage:
            findings.append("run_linkage_incomplete_or_invalid")
        if not collection_valid:
            findings.append("collection_scope_incomplete_or_invalid")
        if not facts.inventory_complete:
            findings.append("inventory_incomplete")
        return VerificationResult(
            records,
            WORKFLOW_LIFECYCLE_SPEC.decide(facts).value,
            VERIFICATION_VERDICT_SPEC.decide(facts).value,
            tuple(findings),
        )
