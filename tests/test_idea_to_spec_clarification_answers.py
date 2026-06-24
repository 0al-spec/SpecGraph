from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "idea_to_spec_clarification_answers.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "idea_to_spec_clarification_answers"
REQUESTS_FIXTURE = FIXTURE_DIR / "clarification_requests_blocking.json"
ANSWERS_READY_FIXTURE = FIXTURE_DIR / "answers_ready.json"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "idea_to_spec_clarification_answers_under_test",
        TOOL_PATH,
    )
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


def test_clarification_answers_accepts_blocking_request_answer() -> None:
    module = load_module()

    report = module.build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(REQUESTS_FIXTURE),
        answer_set=load_json(ANSWERS_READY_FIXTURE),
        requests_path=REQUESTS_FIXTURE,
        answer_set_path=ANSWERS_READY_FIXTURE,
    )

    assert report["artifact_kind"] == "idea_to_spec_clarification_answers"
    assert report["proposal_id"] == "0164"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "answers_ready_for_rerun"
    assert report["summary"]["accepted_answer_count"] == 1
    assert report["summary"]["unresolved_blocking_count"] == 0
    assert report["unresolved_blocking_requests"] == []


def test_clarification_answers_default_requests_input_uses_current_run_artifact() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert (
        "IDEA_TO_SPEC_CLARIFICATION_ANSWERS_REQUESTS ?= $(IDEA_TO_SPEC_CLARIFICATION_OUTPUT)"
        in makefile
    )


def test_clarification_answers_blocks_unknown_request() -> None:
    module = load_module()
    answers = copy.deepcopy(load_json(ANSWERS_READY_FIXTURE))
    answers["answers"][0]["request_id"] = "clarification.unknown"

    report = module.build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(REQUESTS_FIXTURE),
        answer_set=answers,
    )

    assert report["readiness"]["ready"] is False
    assert "answer_request_unknown" in finding_ids(report)
    assert report["summary"]["unresolved_blocking_count"] == 1


def test_clarification_answers_rejects_disallowed_answer_kind() -> None:
    module = load_module()
    answers = copy.deepcopy(load_json(ANSWERS_READY_FIXTURE))
    answers["answers"][0]["answer_kind"] = "write_ontology_package"

    report = module.build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(REQUESTS_FIXTURE),
        answer_set=answers,
    )

    assert report["readiness"]["ready"] is False
    assert "answer_kind_not_allowed" in finding_ids(report)


def test_clarification_answers_rejects_request_without_allowed_actions() -> None:
    module = load_module()
    requests = copy.deepcopy(load_json(REQUESTS_FIXTURE))
    requests["clarification_requests"][0]["suggested_actions"] = []

    report = module.build_idea_to_spec_clarification_answers(
        clarification_requests=requests,
        answer_set=load_json(ANSWERS_READY_FIXTURE),
    )

    assert report["readiness"]["ready"] is False
    assert "request_suggested_actions_missing" in finding_ids(report)


def test_clarification_answers_preserves_scalar_values_and_redacts_rationale() -> None:
    module = load_module()
    answers = copy.deepcopy(load_json(ANSWERS_READY_FIXTURE))
    answers["answers"][0]["value"] = "Decision Owner"
    answers["answers"][0]["rationale"] = "Reviewed /Users/egor/private; token=abc123"

    report = module.build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(REQUESTS_FIXTURE),
        answer_set=answers,
    )

    answer = report["answers"][0]
    assert answer["value"] == "Decision Owner"
    assert answer["rationale"] == "[redacted unsafe rationale]"
    assert answer["rationale_redacted"] is True
    dumped = json.dumps(report, sort_keys=True)
    assert "/Users/egor/private" not in dumped
    assert "token=abc123" not in dumped


def test_clarification_answers_defer_does_not_resolve_blocking_request() -> None:
    module = load_module()
    answers = copy.deepcopy(load_json(ANSWERS_READY_FIXTURE))
    answers["answers"][0]["answer_kind"] = "defer"
    answers["answers"][0]["status"] = "accepted_for_review"
    answers["answers"][0]["authority"] = "deferred_by_operator"

    report = module.build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(REQUESTS_FIXTURE),
        answer_set=answers,
    )

    assert report["summary"]["accepted_answer_count"] == 1
    assert report["summary"]["unresolved_blocking_count"] == 1
    assert report["readiness"]["ready"] is False
    assert report["unresolved_blocking_requests"][0]["request_id"] == (
        "clarification.repair.repair-review-unresolved-gaps"
    )


def test_clarification_answers_requires_authority() -> None:
    module = load_module()
    answers = copy.deepcopy(load_json(ANSWERS_READY_FIXTURE))
    answers["answers"][0]["authority"] = "anonymous"

    report = module.build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(REQUESTS_FIXTURE),
        answer_set=answers,
    )

    assert report["readiness"]["ready"] is False
    assert "answer_authority_unsupported" in finding_ids(report)


def test_clarification_answers_cli_writes_output(tmp_path: Path) -> None:
    output = tmp_path / "idea_to_spec_clarification_answers.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--requests",
            str(REQUESTS_FIXTURE),
            "--answers",
            str(ANSWERS_READY_FIXTURE),
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
    assert report["artifact_kind"] == "idea_to_spec_clarification_answers"
    assert report["readiness"]["ready"] is True
    assert "answers_ready_for_rerun" in result.stdout
    dumped = json.dumps(report)
    assert "private prompt trace" not in dumped
