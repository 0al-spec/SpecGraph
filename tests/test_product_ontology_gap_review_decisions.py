from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSWERS_TOOL_PATH = ROOT / "tools" / "idea_to_spec_clarification_answers.py"
DECISIONS_TOOL_PATH = ROOT / "tools" / "product_ontology_gap_review_decisions.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "idea_to_spec_clarification_answers"
REQUESTS_FIXTURE = FIXTURE_DIR / "clarification_requests_blocking.json"
ANSWERS_READY_FIXTURE = FIXTURE_DIR / "answers_ready.json"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def ready_answer_report() -> dict[str, object]:
    answers_module = load_module(
        ANSWERS_TOOL_PATH,
        "idea_to_spec_clarification_answers_for_decisions_test",
    )
    return answers_module.build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(REQUESTS_FIXTURE),
        answer_set=load_json(ANSWERS_READY_FIXTURE),
        requests_path=REQUESTS_FIXTURE,
        answer_set_path=ANSWERS_READY_FIXTURE,
    )


def answer_report_with_answer(
    *,
    answer_kind: str,
    value: object,
    request_kind: str = "ontology_gap",
    target_ref: str = "candidate-spec.product.gaps.ontology-gap.decision-owner",
    status: str = "accepted_for_candidate",
) -> dict[str, object]:
    report = copy.deepcopy(ready_answer_report())
    answer = report["answers"][0]
    assert isinstance(answer, dict)
    answer["answer_kind"] = answer_kind
    answer["status"] = status
    answer["value"] = value
    answer["request_snapshot"] = {
        "kind": request_kind,
        "severity": "review_required",
        "target_artifact": "runs/candidate_spec_graph.json",
        "target_ref": target_ref,
        "suggested_answer_shape": "test-shape",
    }
    return report


def test_product_ontology_gap_decisions_build_project_local_term_decision() -> None:
    module = load_module(
        DECISIONS_TOOL_PATH,
        "product_ontology_gap_review_decisions_under_test",
    )

    report = module.build_product_ontology_gap_review_decisions(
        answers_report=ready_answer_report(),
        answers_path=ROOT / "runs" / "idea_to_spec_clarification_answers.json",
    )

    assert report["artifact_kind"] == "product_ontology_gap_review_decisions"
    assert report["proposal_id"] == "0168"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "ontology_gap_decisions_ready"
    boundary = report["authority_boundary"]
    assert boundary["may_write_ontology_package"] is False
    assert boundary["may_accept_ontology_terms"] is False

    decisions = report["decisions"]
    assert decisions == [
        {
            "id": "product-ontology-decision.clarification-repair-repair-review-unresolved-gaps.0",
            "decision_type": "propose_project_local_term",
            "status": "accepted_for_candidate_preview",
            "materialization_intent": "rerun_overlay_only",
            "canonical_mutations_allowed": False,
            "writes_ontology_package": False,
            "accepts_ontology_term": False,
            "request_id": "clarification.repair.repair-review-unresolved-gaps",
            "request_kind": "ontology_gap",
            "target_artifact": "runs/candidate_repair_loop_report.json",
            "target_ref": "candidate_graph.gaps",
            "source_answer_kind": "propose_project_local_term",
            "source_answer_status": "accepted_for_candidate",
            "authority": "operator_approved",
            "term": "Decision Owner",
            "term_scope": "project_local",
            "source_value": {
                "term_scope": "project_local",
                "terms": ["Decision Owner"],
            },
        }
    ]
    assert report["summary"]["decision_counts"] == {"propose_project_local_term": 1}


def test_product_ontology_gap_decisions_accept_bind_alias_reject_and_defer() -> None:
    module = load_module(
        DECISIONS_TOOL_PATH,
        "product_ontology_gap_review_decisions_variants_test",
    )
    cases = [
        (
            "bind_existing_term",
            {"term": "Decision Owner", "ontology_ref": "sgcore:Actor"},
            "bind_existing_term",
            {"term": "Decision Owner", "ontology_ref": "sgcore:Actor"},
        ),
        (
            "alias",
            {"term": "Decision Owner", "alias_of": "Decision Maker"},
            "alias_existing_term",
            {"term": "Decision Owner", "alias_of": "Decision Maker"},
        ),
        ("reject", {"reason": "Not part of product domain."}, "reject_non_domain_term", {}),
        ("defer", {"reason": "Needs owner review."}, "defer_requires_owner", {}),
    ]

    for answer_kind, value, decision_type, expected in cases:
        report = module.build_product_ontology_gap_review_decisions(
            answers_report=answer_report_with_answer(answer_kind=answer_kind, value=value),
        )

        assert report["readiness"]["ready"] is True
        decision = report["decisions"][0]
        assert decision["decision_type"] == decision_type
        for key, expected_value in expected.items():
            assert decision[key] == expected_value


def test_product_ontology_gap_decisions_ignore_non_ontology_answers() -> None:
    module = load_module(
        DECISIONS_TOOL_PATH,
        "product_ontology_gap_review_decisions_non_ontology_test",
    )
    report = module.build_product_ontology_gap_review_decisions(
        answers_report=answer_report_with_answer(
            answer_kind="answer_question",
            value={"domain_refs": ["domain.team_decision_log"]},
            request_kind="missing_context",
            target_ref="active_frame.domain_refs",
        ),
    )

    assert report["readiness"]["ready"] is True
    assert report["decisions"] == []
    assert report["summary"]["decision_count"] == 0


def test_product_ontology_gap_decisions_block_incomplete_bindings() -> None:
    module = load_module(
        DECISIONS_TOOL_PATH,
        "product_ontology_gap_review_decisions_incomplete_test",
    )

    report = module.build_product_ontology_gap_review_decisions(
        answers_report=answer_report_with_answer(
            answer_kind="bind_existing_term",
            value={"term": "Decision Owner"},
        ),
    )

    assert report["readiness"]["ready"] is False
    assert "term_binding_value_incomplete" in finding_ids(report)
    assert report["decisions"] == []


def test_product_ontology_gap_decisions_block_unready_answer_report() -> None:
    module = load_module(
        DECISIONS_TOOL_PATH,
        "product_ontology_gap_review_decisions_unready_test",
    )
    answer_report = ready_answer_report()
    answer_report["readiness"]["ready"] = False
    answer_report["readiness"]["blocked_by"] = ["clarification.unresolved"]

    report = module.build_product_ontology_gap_review_decisions(answers_report=answer_report)

    assert report["readiness"]["ready"] is False
    assert "answers_not_ready_for_ontology_decisions" in finding_ids(report)
    assert report["summary"]["decision_count"] == 0


def test_product_ontology_gap_decisions_strip_raw_trace_fields() -> None:
    module = load_module(
        DECISIONS_TOOL_PATH,
        "product_ontology_gap_review_decisions_privacy_test",
    )
    answer_report = answer_report_with_answer(
        answer_kind="propose_project_local_term",
        value={
            "terms": ["Decision Owner"],
            "term_scope": "project_local",
            "raw_prompt": "private prompt trace",
        },
    )

    report = module.build_product_ontology_gap_review_decisions(answers_report=answer_report)

    dumped = json.dumps(report)
    assert "private prompt trace" not in dumped
    assert "Decision Owner" in dumped


def test_product_ontology_gap_decisions_cli_writes_output(tmp_path: Path) -> None:
    answers_report = tmp_path / "idea_to_spec_clarification_answers.json"
    output = tmp_path / "product_ontology_gap_review_decisions.json"

    answer_result = subprocess.run(
        [
            sys.executable,
            str(ANSWERS_TOOL_PATH),
            "--requests",
            str(REQUESTS_FIXTURE),
            "--answers",
            str(ANSWERS_READY_FIXTURE),
            "--output",
            str(answers_report),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert answer_result.returncode == 0

    result = subprocess.run(
        [
            sys.executable,
            str(DECISIONS_TOOL_PATH),
            "--answers",
            str(answers_report),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    report = load_json(output)
    assert report["artifact_kind"] == "product_ontology_gap_review_decisions"
    assert report["readiness"]["ready"] is True
    assert "ontology_gap_decisions_ready" in result.stdout
