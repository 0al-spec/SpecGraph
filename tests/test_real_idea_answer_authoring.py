from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "real_idea_answer_authoring.py"
SMOKE_TOOL = ROOT / "tools" / "real_idea_smoke.py"
INTERVIEW_TOOL = ROOT / "tools" / "user_idea_intake_interview.py"
REQUESTS_TOOL = ROOT / "tools" / "idea_to_spec_clarification_requests.py"
REPAIR_REQUESTS = (
    ROOT
    / "tests"
    / "fixtures"
    / "idea_to_spec_clarification_answers"
    / "clarification_requests_blocking.json"
)
INTAKE_ANSWERS = ROOT / "tests" / "fixtures" / "idea_intake_clarification" / "answers_ready.json"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "real_idea_answer_authoring_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOL_PATH.parent))
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def filled_repair_template(tmp_path: Path) -> Path:
    module = load_module()
    template = module.build_template(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        stage="repair",
        run_dir=tmp_path,
    )
    template["operator_answers"][0]["status"] = "accepted_for_candidate"
    template["operator_answers"][0]["value"] = {
        "terms": ["Decision Owner"],
        "term_scope": "project_local",
    }
    template_path = tmp_path / "real_idea_answer_template.json"
    write_json(template_path, template)
    return template_path


def test_answer_template_exposes_typed_targets(tmp_path: Path) -> None:
    module = load_module()

    template = module.build_template(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        stage="repair",
        run_dir=tmp_path,
    )

    assert template["artifact_kind"] == "real_idea_answer_template"
    assert template["proposal_id"] == "0194"
    assert template["summary"]["target_count"] == 2
    target = template["answer_targets"][0]
    assert target["target_type"] == "ontology_gap"
    assert "propose_project_local_term" in target["accepted_actions"]
    assert target["required_fields_by_action"]["bind_existing_term"] == [
        "value.term",
        "value.ontology_ref",
    ]
    assert template["authority_boundary"]["may_write_ontology_package"] is False


def test_answer_authoring_validate_accepts_filled_template(tmp_path: Path) -> None:
    module = load_module()
    template_path = filled_repair_template(tmp_path)

    answer_set, validated_answers, report = module.build_validation(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        answer_input=load_json(template_path),
        answers_path=template_path,
        stage="repair",
        run_dir=tmp_path,
    )

    assert answer_set["artifact_kind"] == "idea_to_spec_clarification_answer_set"
    assert validated_answers["readiness"]["ready"] is True
    assert report["readiness"]["ready"] is True
    assert report["summary"]["status"] == "answers_ready_for_materialization"
    assert not report["findings"]


def test_answer_authoring_blocks_empty_required_fields(tmp_path: Path) -> None:
    module = load_module()
    template = module.build_template(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        stage="repair",
        run_dir=tmp_path,
    )
    template["operator_answers"][0]["status"] = "accepted_for_candidate"
    template_path = tmp_path / "unfilled_template.json"
    write_json(template_path, template)

    _answer_set, _validated_answers, report = module.build_validation(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        answer_input=load_json(template_path),
        answers_path=template_path,
        stage="repair",
        run_dir=tmp_path,
    )

    assert report["readiness"]["ready"] is False
    assert "answer_required_field_empty" in finding_ids(report)


def test_answer_authoring_blocks_authority_expansion(tmp_path: Path) -> None:
    module = load_module()
    template_path = filled_repair_template(tmp_path)
    template = load_json(template_path)
    template["operator_answers"][0]["value"]["may_write_ontology_package"] = True
    write_json(template_path, template)

    _answer_set, _validated_answers, report = module.build_validation(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        answer_input=load_json(template_path),
        answers_path=template_path,
        stage="repair",
        run_dir=tmp_path,
    )

    assert report["readiness"]["ready"] is False
    assert "authority_field_expanded" in finding_ids(report)


def test_answer_authoring_blocks_raw_alias_and_private_markers(tmp_path: Path) -> None:
    module = load_module()
    template_path = filled_repair_template(tmp_path)
    template = load_json(template_path)
    template["operator_answers"][0]["value"]["operator_note"] = "local-only note"
    template["operator_answers"][0]["value"]["scratch_path"] = "/tmp/private-answer.json"
    template["operator_answers"][0]["value"]["password"] = "opaque"
    write_json(template_path, template)

    _answer_set, _validated_answers, report = module.build_validation(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        answer_input=load_json(template_path),
        answers_path=template_path,
        stage="repair",
        run_dir=tmp_path,
    )

    assert report["readiness"]["ready"] is False
    ids = finding_ids(report)
    assert "raw_trace_field_present" in ids
    assert "private_text_marker_present" in ids


def test_answer_authoring_preserves_supplied_answer_set_metadata(tmp_path: Path) -> None:
    module = load_module()
    template_path = filled_repair_template(tmp_path)
    answer_set = module.answer_set_from_input(load_json(template_path))
    answer_set["contract_ref"] = "specgraph.idea-to-spec.old-answer-set.v0.0"
    answer_set["schema_version"] = 999
    answer_set_path = tmp_path / "old_answer_set.json"
    write_json(answer_set_path, answer_set)

    preserved_set, validated_answers, report = module.build_validation(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        answer_input=load_json(answer_set_path),
        answers_path=answer_set_path,
        stage="repair",
        run_dir=tmp_path,
    )

    assert preserved_set["contract_ref"] == "specgraph.idea-to-spec.old-answer-set.v0.0"
    assert preserved_set["schema_version"] == 999
    assert validated_answers["readiness"]["ready"] is False
    assert report["readiness"]["ready"] is False
    assert "answer_set_contract_ref_unsupported" in finding_ids(validated_answers)


def test_answer_authoring_uses_nested_template_edits(tmp_path: Path) -> None:
    module = load_module()
    template = module.build_template(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        stage="repair",
        run_dir=tmp_path,
    )
    template["answer_targets"][0]["operator_answer"]["status"] = "accepted_for_candidate"
    template["answer_targets"][0]["operator_answer"]["value"] = {
        "terms": ["Decision Owner"],
        "term_scope": "project_local",
    }
    template_path = tmp_path / "nested_edit_template.json"
    write_json(template_path, template)

    answer_set, validated_answers, report = module.build_validation(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        answer_input=load_json(template_path),
        answers_path=template_path,
        stage="repair",
        run_dir=tmp_path,
    )

    assert answer_set["answers"][0]["status"] == "accepted_for_candidate"
    assert validated_answers["readiness"]["ready"] is True
    assert report["readiness"]["ready"] is True


def test_answer_template_uses_refs_for_active_frame_ref_questions(tmp_path: Path) -> None:
    module = load_module()

    value = module._value_template(
        "answer_question",
        {
            "kind": "missing_context",
            "suggested_answer_shape": "ontology_layer_ref[]",
        },
    )
    applicability = module._value_template(
        "answer_question",
        {
            "kind": "missing_context",
            "suggested_answer_shape": "model_applicability_ref[]",
        },
    )

    assert value == {"refs": [""]}
    assert applicability == {"refs": [""]}


def test_answer_authoring_materializes_repair_stage_artifacts(tmp_path: Path) -> None:
    module = load_module()
    template_path = filled_repair_template(tmp_path)
    answer_set_output = tmp_path / "real_idea_answer_set.json"
    validated_output = tmp_path / "idea_to_spec_clarification_answers.json"

    _answer_set, _validated_answers, report = module.build_materialization(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        answer_input=load_json(template_path),
        answers_path=template_path,
        answer_set_output=answer_set_output,
        validated_answers_output=validated_output,
        stage="repair",
        run_dir=tmp_path,
    )

    assert report["readiness"]["ready"] is True
    assert report["summary"]["status"] == "answers_materialized"
    assert answer_set_output.exists()
    assert validated_output.exists()
    ontology_decisions = load_json(tmp_path / "product_ontology_gap_review_decisions.json")
    rerun_input = load_json(tmp_path / "idea_to_spec_answer_rerun_input.json")
    assert ontology_decisions["artifact_kind"] == "product_ontology_gap_review_decisions"
    assert rerun_input["artifact_kind"] == "idea_to_spec_answer_rerun_input"
    assert rerun_input["readiness"]["ready"] is True


def test_answer_authoring_does_not_write_materialized_answers_when_invalid(
    tmp_path: Path,
) -> None:
    module = load_module()
    template_path = filled_repair_template(tmp_path)
    template = load_json(template_path)
    template["operator_answers"][0]["value"]["scratch_path"] = "/Users/operator/private.txt"
    write_json(template_path, template)
    answer_set_output = tmp_path / "real_idea_answer_set.json"
    validated_output = tmp_path / "idea_to_spec_clarification_answers.json"

    _answer_set, _validated_answers, report = module.build_materialization(
        clarification_requests=load_json(REPAIR_REQUESTS),
        requests_path=REPAIR_REQUESTS,
        answer_input=load_json(template_path),
        answers_path=template_path,
        answer_set_output=answer_set_output,
        validated_answers_output=validated_output,
        stage="repair",
        run_dir=tmp_path,
    )

    assert report["readiness"]["ready"] is False
    assert not answer_set_output.exists()
    assert not validated_output.exists()
    assert not (tmp_path / "product_ontology_gap_review_decisions.json").exists()


def build_intake_requests(tmp_path: Path) -> Path:
    raw_input = tmp_path / "local_operator_user_idea_raw_input.json"
    session = tmp_path / "user_idea_intake_session.json"
    source = tmp_path / "user_idea_intake_source.json"
    report = tmp_path / "user_idea_intake_interview_report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(INTERVIEW_TOOL),
            "--idea-text",
            "I want a small tool for team decisions.",
            "--idea-summary",
            "Track team decisions.",
            "--candidate-id",
            "team-decision-log",
            "--display-name",
            "Team Decision Log",
            "--public-route",
            "/team-decision-log",
            "--raw-output",
            str(raw_input),
            "--session-output",
            str(session),
            "--source-output",
            str(source),
            "--report-output",
            str(report),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    requests = tmp_path / "idea_intake_clarification_requests.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REQUESTS_TOOL),
            "--session",
            str(session),
            "--no-intake",
            "--no-candidate-graph",
            "--no-pre-sib",
            "--no-repair-loop",
            "--output",
            str(requests),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return requests


def test_answer_authoring_materializes_intake_stage_artifacts(tmp_path: Path) -> None:
    module = load_module()
    requests = build_intake_requests(tmp_path)
    answer_set_output = tmp_path / "real_idea_answer_set.json"
    validated_output = tmp_path / "idea_intake_clarification_answers.json"

    _answer_set, _validated_answers, report = module.build_materialization(
        clarification_requests=load_json(requests),
        requests_path=requests,
        answer_input=load_json(INTAKE_ANSWERS),
        answers_path=INTAKE_ANSWERS,
        answer_set_output=answer_set_output,
        validated_answers_output=validated_output,
        stage="intake",
        run_dir=tmp_path,
    )

    assert report["readiness"]["ready"] is True
    clarified_session = load_json(tmp_path / "clarified_user_idea_intake_session.json")
    rerun_report = load_json(tmp_path / "idea_intake_clarification_rerun_report.json")
    assert clarified_session["readiness"]["review_state"] == "ready_for_event_storming_intake"
    assert rerun_report["summary"]["ready_for_candidate_source"] is True
    dumped = json.dumps(report)
    assert "I want a small tool for team decisions" not in dumped
    assert "/Users/" not in dumped


def test_answer_authoring_propagates_not_ready_intake_rerun(tmp_path: Path) -> None:
    module = load_module()
    requests = build_intake_requests(tmp_path)
    wrong_shape_answers = load_json(INTAKE_ANSWERS)
    for answer in wrong_shape_answers["answers"]:
        answer["value"] = {"answer": "not a typed rerun value"}
    wrong_shape_path = tmp_path / "wrong_shape_answers.json"
    write_json(wrong_shape_path, wrong_shape_answers)

    _answer_set, _validated_answers, report = module.build_materialization(
        clarification_requests=load_json(requests),
        requests_path=requests,
        answer_input=load_json(wrong_shape_path),
        answers_path=wrong_shape_path,
        answer_set_output=tmp_path / "real_idea_answer_set.json",
        validated_answers_output=tmp_path / "idea_intake_clarification_answers.json",
        stage="intake",
        run_dir=tmp_path,
    )

    assert report["readiness"]["ready"] is False
    assert report["summary"]["status"] == "answers_review_required"
    assert "intake_rerun_not_ready" in finding_ids(report)


def test_answer_authoring_cli_rejects_shared_runs_dir() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "template",
            "--run-dir",
            "runs",
            "--stage",
            "intake",
            "--requests",
            str(REPAIR_REQUESTS),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "REAL_IDEA_SMOKE_RUN_DIR=runs is reserved" in result.stderr


def test_answer_authoring_outputs_are_real_idea_smoke_managed_outputs() -> None:
    spec = importlib.util.spec_from_file_location("real_idea_smoke_under_test", SMOKE_TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SMOKE_TOOL.parent))
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)

    managed = set(module.DERIVED_REPAIR_OUTPUT_NAMES)

    assert "real_idea_answer_template.json" in managed
    assert "real_idea_answer_authoring_report.json" in managed
    assert "real_idea_answer_set.json" in managed
