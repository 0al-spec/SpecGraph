from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "user_idea_intake_interview.py"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def output_args(tmp_path: Path) -> list[str]:
    return [
        "--raw-output",
        str(tmp_path / "local_operator_user_idea_raw_input.json"),
        "--session-output",
        str(tmp_path / "user_idea_intake_session.json"),
        "--source-output",
        str(tmp_path / "user_idea_intake_source.json"),
        "--report-output",
        str(tmp_path / "user_idea_intake_interview_report.json"),
    ]


def test_real_idea_interview_captures_incomplete_idea_without_public_raw_text(
    tmp_path: Path,
) -> None:
    raw_text = "Build a tiny app for subscription tracking."

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--idea-text",
            raw_text,
            *output_args(tmp_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    raw_input = load_json(tmp_path / "local_operator_user_idea_raw_input.json")
    session = load_json(tmp_path / "user_idea_intake_session.json")
    report = load_json(tmp_path / "user_idea_intake_interview_report.json")
    assert raw_input["idea"]["text"] == raw_text
    assert session["readiness"]["review_state"] == "needs_clarification"
    assert report["summary"]["ready_for_event_storming_intake"] is False
    assert report["raw_input"]["local_only"] is True
    assert report["privacy_boundary"]["raw_idea_text_published_in_report"] is False
    assert raw_text not in json.dumps(report)
    assert not (tmp_path / "user_idea_intake_source.json").exists()


def test_real_idea_interview_cli_hints_write_ready_source(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--idea-text",
            "Local app for tracking subscriptions and upcoming renewal payments.",
            "--idea-summary",
            "Track local subscription renewals.",
            "--candidate-id",
            "local-subscription-control",
            "--display-name",
            "Local Subscription Control",
            "--public-route",
            "/local-subscription-control",
            "--ontology-ref",
            "ontology://specgraph-core",
            "--ontology-layer-ref",
            "objective",
            "--ontology-layer-ref",
            "mechanics",
            "--domain-ref",
            "domain.subscription_control",
            "--context-ref",
            "context.idea_to_spec",
            "--context-ref",
            "context.subscription_control",
            "--model-applicability-ref",
            "model-applicability://specgraph-core/product-spec-mvp",
            "--actor",
            "Subscription Owner",
            "--domain-event",
            "Subscription Recorded",
            "--command",
            "Add Subscription",
            "--constraint",
            "Data remains local to the device.",
            *output_args(tmp_path),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    source = load_json(tmp_path / "user_idea_intake_source.json")
    report = load_json(tmp_path / "user_idea_intake_interview_report.json")
    assert source["artifact_kind"] == "user_idea_intake_source"
    assert source["workspace"]["candidate_id"] == "local-subscription-control"
    assert source["event_storming_hints"]["actors"][0]["name"] == "Subscription Owner"
    assert source["event_storming_hints"]["constraints"][0]["statement"] == (
        "Data remains local to the device."
    )
    assert report["summary"]["status"] == "ready_for_event_storming_intake"
    assert report["summary"]["source_written"] is True


def test_real_idea_interview_applies_clarification_answers(tmp_path: Path) -> None:
    base_input = {
        "artifact_kind": "user_idea_raw_input",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.user-idea-raw-input.v0.1",
        "idea": {"text": "Build a small product for team decisions."},
        "workspace": {
            "candidate_id": "team-decision-log",
            "display_name": "Team Decision Log",
            "public_route": "/team-decision-log",
        },
    }
    requests = {
        "artifact_kind": "idea_to_spec_clarification_requests",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.clarification-requests.v0.1",
        "clarification_requests": [
            {
                "id": "q.ontology",
                "target_ref": "active_frame_hints.ontology_refs",
            },
            {
                "id": "q.layers",
                "target_ref": "active_frame_hints.ontology_layer_refs",
            },
            {"id": "q.domain", "target_ref": "active_frame_hints.domain_refs"},
            {"id": "q.context", "target_ref": "active_frame_hints.context_refs"},
            {
                "id": "q.applicability",
                "target_ref": "active_frame_hints.model_applicability_refs",
            },
            {"id": "q.actor", "target_ref": "event_storming_hints.actors"},
            {"id": "q.event", "target_ref": "event_storming_hints.domain_events"},
            {"id": "q.command", "target_ref": "event_storming_hints.commands"},
            {"id": "q.constraint", "target_ref": "event_storming_hints.constraints"},
        ],
    }
    answers = {
        "artifact_kind": "idea_to_spec_clarification_answer_set",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.clarification-answer-set.v0.1",
        "answers": [
            {
                "request_id": "q.ontology",
                "answer_kind": "answer_question",
                "status": "accepted_for_candidate",
                "value": {"refs": ["ontology://specgraph-core"]},
            },
            {
                "request_id": "q.layers",
                "answer_kind": "answer_question",
                "status": "accepted_for_candidate",
                "value": {"refs": ["objective", "mechanics"]},
            },
            {
                "request_id": "q.domain",
                "answer_kind": "answer_question",
                "status": "accepted_for_candidate",
                "value": {"refs": ["domain.team_decision_log"]},
            },
            {
                "request_id": "q.context",
                "answer_kind": "answer_question",
                "status": "accepted_for_candidate",
                "value": {"refs": ["context.idea_to_spec", "context.team_decision_log"]},
            },
            {
                "request_id": "q.applicability",
                "answer_kind": "answer_question",
                "status": "accepted_for_candidate",
                "value": {"refs": ["model-applicability://specgraph-core/product-spec-mvp"]},
            },
            {
                "request_id": "q.actor",
                "answer_kind": "answer_question",
                "status": "accepted_for_candidate",
                "value": {"entries": ["Decision Maker"]},
            },
            {
                "request_id": "q.event",
                "answer_kind": "answer_question",
                "status": "accepted_for_candidate",
                "value": {"entries": ["Decision Recorded"]},
            },
            {
                "request_id": "q.command",
                "answer_kind": "answer_question",
                "status": "accepted_for_candidate",
                "value": {"entries": ["Record Decision"]},
            },
            {
                "request_id": "q.constraint",
                "answer_kind": "answer_question",
                "status": "accepted_for_candidate",
                "value": {"entries": ["Accepted decisions require an owner."]},
            },
        ],
    }
    base_path = tmp_path / "base.json"
    requests_path = tmp_path / "requests.json"
    answers_path = tmp_path / "answers.json"
    write_json(base_path, base_input)
    write_json(requests_path, requests)
    write_json(answers_path, answers)

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(base_path),
            "--clarification-requests",
            str(requests_path),
            "--clarification-answers",
            str(answers_path),
            *output_args(tmp_path),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = load_json(tmp_path / "user_idea_intake_interview_report.json")
    source = load_json(tmp_path / "user_idea_intake_source.json")
    assert report["clarification_answer_application"]["applied_count"] == 9
    assert source["active_frame_hints"]["domain_refs"] == ["domain.team_decision_log"]
    assert source["event_storming_hints"]["domain_events"][0]["name"] == ("Decision Recorded")


def test_real_idea_interview_blocks_authority_expansion(tmp_path: Path) -> None:
    base_path = tmp_path / "malicious_base.json"
    write_json(
        base_path,
        {
            "artifact_kind": "user_idea_raw_input",
            "schema_version": 1,
            "contract_ref": "specgraph.idea-to-spec.user-idea-raw-input.v0.1",
            "idea": {"text": "Build a product."},
            "authority_boundary": {"may_create_branch_or_commit": True},
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(base_path),
            *output_args(tmp_path),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    report = load_json(tmp_path / "user_idea_intake_interview_report.json")
    session = load_json(tmp_path / "user_idea_intake_session.json")
    raw_input = load_json(tmp_path / "local_operator_user_idea_raw_input.json")
    assert report["summary"]["status"] == "blocked_authority_boundary"
    assert "user_idea_interview_authority_expanded" in {
        finding["finding_id"] for finding in report["findings"]
    }
    assert session["readiness"]["review_state"] == "blocked_authority_boundary"
    assert not (tmp_path / "user_idea_intake_source.json").exists()
    assert "may_create_branch_or_commit" not in json.dumps(raw_input)


def test_real_idea_intake_make_target_writes_custom_outputs(tmp_path: Path) -> None:
    raw_output = tmp_path / "local_operator_user_idea_raw_input.json"
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"
    report_output = tmp_path / "user_idea_intake_interview_report.json"

    result = subprocess.run(
        [
            "make",
            "real-idea-intake",
            f"PYTHON={sys.executable}",
            "USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT=Build a tool for team decisions.",
            "USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID=team-decision-log",
            "USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME=Team Decision Log",
            "USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE=/team-decision-log",
            f"USER_IDEA_RAW_INPUT_OUTPUT={raw_output}",
            f"USER_IDEA_INTAKE_SESSION_OUTPUT={session_output}",
            f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={source_output}",
            f"USER_IDEA_INTAKE_INTERVIEW_REPORT_OUTPUT={report_output}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert raw_output.exists()
    assert session_output.exists()
    assert report_output.exists()
    assert not source_output.exists()
    report = load_json(report_output)
    assert report["summary"]["status"] == "needs_clarification"
