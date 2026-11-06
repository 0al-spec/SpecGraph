"""Synthetic policy/state-machine controls, not claims of actual test-process execution."""

import json
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from traceability.criterion import (  # noqa: E402
    AttemptObservation,
    CriterionBinding,
    CriterionEvidence,
    CriterionFinding,
    CriterionRow,
    CriterionSelection,
    CriterionSource,
    ExpectedAssertion,
    FilePin,
    JournalDeclaration,
    PassportIdentity,
    StepObservation,
)
from traceability.criterion_provider import criterion_row  # noqa: E402
from verification_workflow.model import (  # noqa: E402
    CollectionRecord,
    CriterionTarget,
    ExecutionRecord,
    ExpectedMeasurement,
    Finalization,
    Operation,
    OperationRegistry,
    PassportPin,
    PinRecord,
    ReportRecord,
    Stage,
    StageArtifact,
    Status,
    ToolPin,
    VerificationRequest,
    VerificationScope,
    WorkflowDefinition,
    WorkflowStep,
)
from verification_workflow.profile_spec import SIGNATURES  # noqa: E402
from verification_workflow.run import VerificationRun  # noqa: E402


def pin(path):
    return FilePin(path, "a" * 64)


@pytest.fixture
def workflow_request():
    operations = tuple(
        Operation(
            stage.value, "1", stage, source, target, ToolPin(stage.value, "1", "b" * 64), effects
        )
        for stage, source, target, _, effects in SIGNATURES
    )
    definition = WorkflowDefinition(
        "verify-criteria/v1",
        tuple(
            WorkflowStep(stage, stage.value, "1", parent) for stage, _, _, parent, _ in SIGNATURES
        ),
    )
    passport = PassportIdentity(
        "passport.parcel", "feature.parcel", "0.1.0", "draft", "c" * 64, "d" * 40, "e" * 64
    )
    targets = tuple(
        CriterionTarget(
            CriterionSource("spec.yaml", "1" * 40, "a" * 64, f"/acceptance/{i}", text),
            f"criterion-{i}",
            f"ref-{i}",
            f"binding-{i}",
            (ExpectedMeasurement(f"assertion-{i}", "application/json", '{"count": 1}'),),
        )
        for i, text in enumerate(("Возврат закрывает выдачу", "Новая выдача сохраняется"))
    )
    return VerificationRequest(
        "workflow_request-1",
        VerificationScope(
            "workspace",
            "owner/project",
            "SPEC-1",
            "1" * 40,
            "2" * 40,
            "3" * 40,
            pin("spec.yaml"),
            PassportPin(pin("passport.json"), passport),
            pin("template.json"),
            targets,
        ),
        definition,
        OperationRegistry("registry/v1", operations),
    )


def stages(workflow_request, run_id="run-1"):
    run = VerificationRun.begin(workflow_request, run_id, used_run_ids=frozenset())
    owner = run.records.owner

    def artifact(stage, name):
        return StageArtifact(owner, stage, name, pin(name))

    journal = artifact(Stage.EXECUTE, "journal.ndjson")
    plan = artifact(Stage.EXECUTE, "plan.json")
    execution = ExecutionRecord(
        owner,
        Status.COMPLETED,
        workflow_request.scope.execution_revision,
        "producer-1",
        0,
        (journal,),
        plan,
    )
    declaration = JournalDeclaration(
        journal.artifact_id,
        journal.file.sha256,
        "producer-1",
        workflow_request.scope.test_revision,
        workflow_request.scope.execution_revision,
        pin("parcel.feature"),
    )
    rows = []
    for target in workflow_request.scope.criteria:
        assertions = tuple(
            ExpectedAssertion(
                e.assertion_id, f"step-{e.assertion_id}", e.media_type, e.expected_json
            )
            for e in target.expectations
        )
        binding = CriterionBinding(
            target.source.pointer,
            target.criterion_id,
            target.contract_ref_id,
            target.passport_binding_id,
            journal.artifact_id,
            "case-1",
            "case-start-1",
            0,
            assertions,
        )
        observation = AttemptObservation(
            "pickle-1",
            True,
            True,
            False,
            tuple((a.step_id, "PASSED") for a in assertions),
            tuple(
                StepObservation(a, "pickle-step", "Observed step", "PASSED", a.expected_json)
                for a in assertions
            ),
        )
        rows.append(
            CriterionRow(
                target.source,
                (binding,),
                "checked",
                "passed",
                journal=declaration,
                observation=observation,
            )
        )
    selection = CriterionSelection(
        workflow_request.scope.workspace,
        workflow_request.scope.spec,
        workflow_request.scope.passport.artifact,
        plan.file,
        Path("/synthetic/run-local"),
        ((journal.artifact_id, journal.file),),
    )
    evidence = CriterionEvidence(
        selection,
        True,
        tuple(rows),
        workflow_request.scope.passport.identity,
        declared_journals=(declaration,),
    )
    collection = CollectionRecord(
        owner,
        Status.COMPLETED,
        (journal,),
        plan,
        evidence,
        artifact(Stage.COLLECT, "collection.json"),
        0,
        workflow_request.registry.operations[2].adapter,
    )
    report = ReportRecord(
        owner, Status.COMPLETED, collection.artifact, artifact(Stage.REPORT, "report.json")
    )
    return run, PinRecord(owner, Status.COMPLETED, True, True), execution, collection, report


def finish(bundle, *, finalization=None):
    run, pinned, execution, collection, report = bundle
    return (
        run.with_pin(pinned)
        .with_execution(execution)
        .with_collection(collection)
        .with_report(report)
        .finalized(finalization or Finalization(run.records.owner, True))
    )


def test_complete_run_keeps_passport_and_separate_authority(workflow_request):
    run = finish(stages(workflow_request))
    result = run.result()
    assert (result.workflow_outcome, result.verification_outcome) == ("completed", "passed")
    assert run.next_stage is None
    payload = json.loads(json.dumps(result.to_payload()))
    assert payload["pinned_scope"]["passport"]["identity"]["feature_id"] == "feature.parcel"
    assert len(payload["criteria"]) == len(workflow_request.scope.criteria)
    assert payload["admission"] == "not_evaluated" and payload["receipt"] is None
    assert payload["scope"] == "local_test"
    assert payload["execution_source_provenance"] == "producer_declared"
    assert payload["canonical_mutations_allowed"] is False


@pytest.mark.parametrize(
    "change",
    [
        "removed",
        "optional",
        "disconnected",
        "wrong_port",
        "unknown",
        "duplicate",
        "version",
        "profile",
        "effects",
    ],
)
def test_preflight_exposes_no_operation_for_bypassing_graph(workflow_request, change):
    steps = list(workflow_request.definition.steps)
    operations = list(workflow_request.registry.operations)
    if change == "removed":
        del steps[1]
    if change == "optional":
        steps[1] = replace(steps[1], mandatory=False)
    if change == "disconnected":
        steps[2] = replace(steps[2], input_from=Stage.PIN)
    if change == "wrong_port":
        operations[2] = replace(operations[2], input_port=operations[0].input_port)
    if change == "unknown":
        steps[1] = replace(steps[1], operation_id="retained-file")
    if change == "duplicate":
        operations.append(operations[1])
    if change == "version":
        steps[1] = replace(steps[1], operation_version="other")
    if change == "effects":
        operations[1] = replace(operations[1], effects=frozenset())
    workflow_request = replace(
        workflow_request,
        definition=replace(
            workflow_request.definition,
            steps=tuple(steps),
            profile="unknown/v1" if change == "profile" else "verify-criteria/v1",
        ),
        registry=replace(workflow_request.registry, operations=tuple(operations)),
    )
    run = VerificationRun.begin(workflow_request, "new", used_run_ids=frozenset())
    assert run.next_stage is None
    assert run.result().workflow_outcome == "rejected"
    with pytest.raises(ValueError, match="rejected preflight"):
        run.with_pin(PinRecord(run.records.owner, Status.COMPLETED, True, True))


def test_duplicate_run_id_is_rejected_against_explicit_inventory(workflow_request):
    run = VerificationRun.begin(workflow_request, "used", used_run_ids=frozenset({"used"}))
    assert run.next_stage is None
    assert "run_id_unavailable" in run.result().findings


def test_stages_cannot_be_skipped_repeated_or_reopened(workflow_request):
    run, pinned, execution, collection, report = stages(workflow_request)
    assert run.next_stage == Stage.PIN
    with pytest.raises(ValueError, match="expected stage"):
        run.with_execution(execution)
    run = run.with_pin(pinned)
    assert run.next_stage == Stage.EXECUTE
    with pytest.raises(ValueError, match="expected stage"):
        run.with_pin(pinned)
    run = run.with_execution(execution).with_collection(collection).with_report(report)
    assert run.result().verification_outcome == "incomplete"
    final = run.finalized(Finalization(run.records.owner, True))
    with pytest.raises(ValueError, match="finalized"):
        final.with_report(report)


@pytest.mark.parametrize("stage_index", [1, 2, 3, 4])
def test_foreign_or_replayed_stage_cannot_pass_even_at_same_commit(workflow_request, stage_index):
    bundle = list(stages(workflow_request))
    old = stages(workflow_request, "old-run")
    bundle[stage_index] = old[stage_index]
    if stage_index == 1:
        assert bundle[0].with_pin(bundle[1]).next_stage is None
        with pytest.raises(ValueError, match="current-run pin"):
            finish(bundle)
    else:
        result = finish(bundle).result()
        assert result.verification_outcome != "passed"
        assert "run_linkage_incomplete_or_invalid" in result.findings


@pytest.mark.parametrize(
    "change",
    [
        "revision",
        "journal_owner",
        "journal_stage",
        "plan",
        "consumed",
        "missing_journal",
        "overwritten_output",
    ],
)
def test_execution_output_chain_is_exact(workflow_request, change):
    run, pinned, execution, collection, report = stages(workflow_request)
    if change == "revision":
        execution = replace(execution, execution_revision="9" * 40)
    if change == "journal_owner":
        execution = replace(
            execution,
            journals=(
                replace(execution.journals[0], owner=replace(execution.owner, run_id="previous")),
            ),
        )
    if change == "journal_stage":
        execution = replace(execution, journals=(replace(execution.journals[0], stage=Stage.PIN),))
    if change == "plan":
        execution = replace(execution, binding_plan=None)
    if change == "consumed":
        collection = replace(collection, consumed_journals=())
    if change == "missing_journal":
        execution = replace(execution, journals=())
    if change == "overwritten_output":
        report = replace(report, artifact=replace(report.artifact, file=execution.journals[0].file))
    assert (
        finish((run, pinned, execution, collection, report)).result().verification_outcome
        != "passed"
    )


@pytest.mark.parametrize(
    "change",
    [
        "feature",
        "passport",
        "criterion",
        "contract",
        "binding",
        "expectation",
        "source",
        "missing_row",
        "producer_run",
        "provider",
        "observation",
    ],
)
def test_passport_and_criterion_scope_cannot_drift(workflow_request, change):
    run, pinned, execution, collection, report = stages(workflow_request)
    evidence = collection.evidence
    if change in {"feature", "passport"}:
        key = "feature_id" if change == "feature" else "passport_id"
        evidence = replace(evidence, passport=replace(evidence.passport, **{key: "other"}))
    if change in {"criterion", "contract", "binding", "expectation"}:
        row = evidence.rows[0]
        binding = row.bindings[0]
        if change == "expectation":
            binding = replace(
                binding,
                assertions=(replace(binding.assertions[0], expected_json='{"count": 999}'),),
            )
        else:
            key = {
                "criterion": "criterion_id",
                "contract": "contract_ref_id",
                "binding": "passport_binding_id",
            }[change]
            binding = replace(binding, **{key: "other"})
        evidence = replace(evidence, rows=(replace(row, bindings=(binding,)), *evidence.rows[1:]))
    if change == "source":
        evidence = replace(evidence, selection=replace(evidence.selection, spec=pin("other.yaml")))
    if change == "missing_row":
        evidence = replace(evidence, rows=evidence.rows[:1])
    if change == "producer_run":
        evidence = replace(
            evidence,
            declared_journals=(replace(evidence.declared_journals[0], run_id="old-producer"),),
        )
    if change == "provider":
        collection = replace(collection, provider=replace(collection.provider, version="2"))
    if change == "observation":
        evidence = replace(
            evidence, rows=(replace(evidence.rows[0], observation=None), *evidence.rows[1:])
        )
    collection = replace(collection, evidence=evidence)
    result = finish((run, pinned, execution, collection, report)).result()
    assert result.verification_outcome != "passed"
    assert len(result.to_payload()["criteria"]) == 2


@pytest.mark.parametrize(
    "status", [Status.ABORTED, Status.INCOMPLETE, Status.FAILED, Status.SKIPPED, Status.NOT_RUN]
)
def test_green_journal_does_not_compensate_unfinished_producer(workflow_request, status):
    bundle = list(stages(workflow_request))
    bundle[2] = replace(bundle[2], status=status)
    result = finish(bundle).result()
    assert result.verification_outcome != "passed"
    assert result.workflow_outcome != "completed"


def test_finished_nonzero_tests_are_completed_but_failed_verification(workflow_request):
    bundle = list(stages(workflow_request))
    bundle[2] = replace(bundle[2], exit_code=1)
    result = finish(bundle).result()
    assert (result.workflow_outcome, result.verification_outcome) == ("completed", "failed")


def test_missing_process_outcome_cannot_complete_the_workflow(workflow_request):
    bundle = list(stages(workflow_request))
    bundle[2] = replace(bundle[2], exit_code=None)
    result = finish(bundle).result()
    assert (result.workflow_outcome, result.verification_outcome) == ("incomplete", "incomplete")


@pytest.mark.parametrize("outcome", ["failed", "skipped", "pending", "partial", "unavailable"])
def test_zero_collector_exit_does_not_override_criterion_outcome(workflow_request, outcome):
    bundle = list(stages(workflow_request))
    evidence = bundle[3].evidence
    evidence = replace(
        evidence, rows=(replace(evidence.rows[0], observed_outcome=outcome), *evidence.rows[1:])
    )
    bundle[3] = replace(bundle[3], evidence=evidence)
    assert finish(bundle).result().verification_outcome != "passed"


def test_empty_complete_inventory_is_not_applicable(workflow_request):
    workflow_request = replace(workflow_request, scope=replace(workflow_request.scope, criteria=()))
    assert finish(stages(workflow_request)).result().verification_outcome == "not_applicable"


def test_incomplete_inventory_and_changed_inputs_cannot_pass(workflow_request):
    bundle = list(stages(workflow_request))
    bundle[1] = replace(bundle[1], inventory_complete=False)
    assert finish(bundle).result().verification_outcome == "incomplete"
    bundle = stages(workflow_request)
    assert (
        finish(bundle, finalization=Finalization(bundle[0].records.owner, False))
        .result()
        .verification_outcome
        == "incomplete"
    )


def test_inputs_and_nested_provider_evidence_are_immutable_snapshots(workflow_request):
    bundle = list(stages(workflow_request))
    evidence = bundle[3].evidence
    caller_rows = list(evidence.rows)
    bundle[3] = replace(bundle[3], evidence=replace(evidence, rows=caller_rows))
    caller_rows.clear()
    assert len(bundle[3].evidence.rows) == 2
    with pytest.raises(FrozenInstanceError):
        workflow_request.scope.passport.identity.feature_id = "changed"
    result = finish(bundle).result()
    result.to_payload()["pinned_scope"]["passport"]["identity"]["feature_id"] = "changed"
    assert (
        result.to_payload()["pinned_scope"]["passport"]["identity"]["feature_id"]
        == "feature.parcel"
    )


def test_changed_request_passport_cannot_finalize_an_old_chain(workflow_request):
    bundle = stages(workflow_request)
    changed = replace(
        workflow_request,
        scope=replace(
            workflow_request.scope,
            passport=replace(
                workflow_request.scope.passport,
                identity=replace(workflow_request.scope.passport.identity, feature_id="new"),
            ),
        ),
    )
    finalization = Finalization(replace(bundle[0].records.owner, request=changed), True)
    assert finish(bundle, finalization=finalization).result().verification_outcome != "passed"


@pytest.mark.parametrize("relabel_passed", [False, True])
def test_existing_c2c_projection_owns_failed_measurement_outcome(workflow_request, relabel_passed):
    bundle = list(stages(workflow_request))
    evidence = bundle[3].evidence
    row = evidence.rows[0]
    observation = replace(
        row.observation,
        steps=(replace(row.observation.steps[0], measurement_json='{"count": 999}'),),
    )
    failed = criterion_row(row.source, row.bindings, [], row.journal, observation)
    assert failed.observed_outcome == "failed"
    if relabel_passed:
        failed = replace(failed, observed_outcome="passed")
    bundle[3] = replace(bundle[3], evidence=replace(evidence, rows=(failed, *evidence.rows[1:])))
    result = finish(bundle).result()
    if relabel_passed:
        assert result.verification_outcome == "incomplete"
        assert "collection_scope_incomplete_or_invalid" in result.findings
    else:
        assert (result.workflow_outcome, result.verification_outcome) == ("completed", "failed")


@pytest.mark.parametrize("position", [0, 1, 2, 3])
def test_interrupted_run_keeps_expected_inventory_and_unrun_stages(workflow_request, position):
    run, pinned, execution, collection, _ = stages(workflow_request)
    if position >= 1:
        run = run.with_pin(pinned)
    if position >= 2:
        run = run.with_execution(execution)
    if position >= 3:
        run = run.with_collection(collection)
    result = run.result()
    assert (result.workflow_outcome, result.verification_outcome) == ("incomplete", "incomplete")
    assert len(result.to_payload()["criteria"]) == len(workflow_request.scope.criteria)
    assert result.to_payload()["stages"]["report"] == "not_run"


@pytest.mark.parametrize(
    "mutation",
    [
        "individual_failure",
        "foreign_case_step",
        "hidden_conflict",
        "retry",
        "missing_retry_state",
        "duplicate_agreeing_step",
        "duplicate_conflicting_step",
    ],
)
def test_inconsistent_nested_observations_cannot_pass(workflow_request, mutation):
    bundle = list(stages(workflow_request))
    evidence = bundle[3].evidence
    row = evidence.rows[0]
    observation = row.observation
    if mutation == "individual_failure":
        observation = replace(
            observation, steps=(replace(observation.steps[0], producer_status="FAILED"),)
        )
    if mutation == "foreign_case_step":
        observation = replace(observation, case_step_statuses=(("unrelated-step", "PASSED"),))
    if mutation == "hidden_conflict":
        observation = replace(
            observation, findings=(CriterionFinding("conflict", "conflicting_step_result"),)
        )
    if mutation == "retry":
        observation = replace(observation, will_be_retried=True)
    if mutation == "missing_retry_state":
        observation = replace(observation, will_be_retried=None)
    if mutation.startswith("duplicate_"):
        step_id, status = observation.case_step_statuses[0]
        duplicate_status = status if mutation == "duplicate_agreeing_step" else "FAILED"
        observation = replace(
            observation,
            case_step_statuses=(*observation.case_step_statuses, (step_id, duplicate_status)),
        )
    changed = replace(row, observation=observation)
    bundle[3] = replace(bundle[3], evidence=replace(evidence, rows=(changed, *evidence.rows[1:])))
    result = finish(bundle).result()
    assert result.verification_outcome == "incomplete"
    assert "collection_scope_incomplete_or_invalid" in result.findings
    assert result.evidence.rows[0].observation == observation


@pytest.mark.parametrize("producer_status", ["PASSED", "FAILED"])
def test_consistent_selected_step_results_preserve_provider_outcome(
    workflow_request, producer_status
):
    bundle = list(stages(workflow_request))
    evidence = bundle[3].evidence
    row = evidence.rows[0]
    step = replace(row.observation.steps[0], producer_status=producer_status)
    observation = replace(
        row.observation,
        steps=(step,),
        run_success=producer_status == "PASSED",
        case_step_statuses=((step.assertion.step_id, producer_status),),
    )
    projected = criterion_row(row.source, row.bindings, [], row.journal, observation)
    bundle[3] = replace(bundle[3], evidence=replace(evidence, rows=(projected, *evidence.rows[1:])))
    result = finish(bundle).result()
    assert (result.workflow_outcome, result.verification_outcome) == (
        "completed",
        "passed" if producer_status == "PASSED" else "failed",
    )
