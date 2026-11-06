"""Build a fresh plan without changing expectations, then use the real C2c registry."""

from pathlib import Path

from criterion_observation_report import report_payload
from intent_decision_review.sources import strict_json
from traceability.criterion import CriterionSelection
from traceability.criterion_inputs import PROFILE, sha256
from traceability.criterion_passport import PassportValidation
from traceability.criterion_provider import PROVIDER_ID, RetainedCriterionEvidenceProvider
from traceability.criterion_report_html import render_html
from traceability.evidence import EvidenceRequest, EvidenceScope
from traceability.providers import EvidenceRegistry

from .execution_binding_spec import EXECUTION_BINDING_SPEC, BindingSelection
from .execution_files import RunFiles
from .execution_model import BoundRun
from .model import CollectionRecord, ExecutionRecord, ReportRecord, Stage, StageArtifact, Status
from .run import VerificationRun


def binding_plan(template: bytes, run: VerificationRun, bound: BoundRun, journal_sha: str) -> dict:
    scope = run.records.owner.request.scope
    if not EXECUTION_BINDING_SPEC.is_satisfied_by(BindingSelection(scope.criteria, bound)):
        raise ValueError("consumer binding differs from the immutable criterion selection")
    plan = strict_json(template)
    journal = plan["journals"][0]
    journal.update(
        artifact_id="producer-journal",
        sha256=journal_sha,
        run_id=bound.producer_run_id,
        execution_source_revision=scope.execution_revision,
        test_source_revision=scope.test_revision,
    )
    for binding in plan["bindings"]:
        selected = next(row for row in bound.criteria if row.pointer == binding["pointer"])
        binding.update(
            artifact_id="producer-journal",
            case_id=selected.case_id,
            case_started_id=selected.case_started_id,
            attempt=selected.attempt,
        )
        steps = dict(selected.steps)
        for assertion in binding["assertions"]:
            assertion["step_id"] = steps[assertion["id"]]
    return plan


def record_execution(
    run: VerificationRun,
    files: RunFiles,
    template: bytes,
    raw: bytes,
    bound: BoundRun,
    status: Status,
    exit_code: int | None,
) -> VerificationRun:
    owner = run.records.owner
    journal = files.write(".verification/journal.ndjson", raw)
    plan = files.json(
        ".verification/binding-plan.json", binding_plan(template, run, bound, sha256(raw))
    )
    return run.with_execution(
        ExecutionRecord(
            owner,
            status,
            owner.request.scope.execution_revision,
            bound.producer_run_id,
            exit_code,
            (StageArtifact(owner, Stage.EXECUTE, "producer-journal", journal),),
            StageArtifact(owner, Stage.EXECUTE, "binding-plan", plan),
        )
    )


def collect_and_report(
    run: VerificationRun, files: RunFiles, repository: Path, validator: PassportValidation
) -> VerificationRun:
    owner, execution = run.records.owner, run.records.execution
    scope = owner.request.scope
    selection = CriterionSelection(
        scope.workspace,
        scope.spec,
        scope.passport.artifact,
        execution.binding_plan.file,
        files.root,
        tuple((a.artifact_id, a.file) for a in execution.journals),
    )
    snapshot = EvidenceRegistry((RetainedCriterionEvidenceProvider(validator),)).collect(
        EvidenceRequest(
            repository,
            EvidenceScope(
                scope.repository_id, scope.declaration_revision, (scope.spec_id,), PROFILE
            ),
            criterion_selection=selection,
        ),
        (PROVIDER_ID,),
    )
    report = report_payload(snapshot)
    collection_pin = files.json(".verification/collection.json", report)
    collection_artifact = StageArtifact(owner, Stage.COLLECT, "collection", collection_pin)
    selected_provider = next(
        op.adapter for op in owner.request.registry.operations if op.stage == Stage.COLLECT
    )
    run = run.with_collection(
        CollectionRecord(
            owner,
            Status.COMPLETED,
            execution.journals,
            execution.binding_plan,
            snapshot.reports[0].criterion,
            collection_artifact,
            0,
            selected_provider,
        )
    )
    html = files.write(".verification/report.html", render_html(report).encode())
    files.json(".verification/trace-snapshot.json", snapshot.to_payload())
    return run.with_report(
        ReportRecord(
            owner,
            Status.COMPLETED,
            collection_artifact,
            StageArtifact(owner, Stage.REPORT, "report", html),
        )
    )
