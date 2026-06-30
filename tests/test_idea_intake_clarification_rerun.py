from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INTERVIEW_TOOL = ROOT / "tools" / "user_idea_intake_interview.py"
REQUESTS_TOOL = ROOT / "tools" / "idea_to_spec_clarification_requests.py"
RERUN_TOOL = ROOT / "tools" / "idea_intake_clarification_rerun.py"
ANSWERS_READY = ROOT / "tests" / "fixtures" / "idea_intake_clarification" / "answers_ready.json"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supported_python() -> str:
    candidates = [
        sys.executable,
        str(ROOT / ".venv" / "bin" / "python"),
        *(shutil.which(name) or "" for name in ("python3.13", "python3.12", "python3.11")),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if candidate_path.is_absolute() and not candidate_path.exists():
            continue
        result = subprocess.run(
            [candidate, "tools/check_python_version.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return candidate
    pytest.skip("No Python >=3.10 interpreter available for Makefile integration test")


def build_incomplete_intake(tmp_path: Path) -> tuple[Path, Path]:
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
    assert not source.exists()
    return raw_input, session


def build_intake_requests(tmp_path: Path, session: Path) -> Path:
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
    assert load_json(requests)["summary"]["blocking_request_count"] == 9
    return requests


def test_idea_intake_clarification_rerun_materializes_clarified_session(
    tmp_path: Path,
) -> None:
    raw_input, session = build_incomplete_intake(tmp_path)
    requests = build_intake_requests(tmp_path, session)
    validated_answers = tmp_path / "idea_intake_clarification_answers.json"
    rerun_input = tmp_path / "idea_intake_answer_rerun_input.json"
    clarified_raw = tmp_path / "local_operator_clarified_user_idea_raw_input.json"
    clarified_session = tmp_path / "clarified_user_idea_intake_session.json"
    clarified_source = tmp_path / "clarified_user_idea_intake_source.json"
    report = tmp_path / "idea_intake_clarification_rerun_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(RERUN_TOOL),
            "--raw-input",
            str(raw_input),
            "--clarification-requests",
            str(requests),
            "--answers",
            str(ANSWERS_READY),
            "--validated-answers-output",
            str(validated_answers),
            "--rerun-input-output",
            str(rerun_input),
            "--clarified-raw-output",
            str(clarified_raw),
            "--clarified-session-output",
            str(clarified_session),
            "--clarified-source-output",
            str(clarified_source),
            "--report-output",
            str(report),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    rerun = load_json(rerun_input)
    session_payload = load_json(clarified_session)
    source = load_json(clarified_source)
    rerun_report = load_json(report)
    assert rerun["artifact_kind"] == "idea_intake_answer_rerun_input"
    assert rerun["readiness"]["ready"] is True
    assert len(rerun["accepted_answer_targets"]) == 9
    assert session_payload["readiness"]["review_state"] == "ready_for_event_storming_intake"
    assert source["workspace"]["candidate_id"] == "team-decision-log"
    assert source["event_storming_hints"]["domain_events"][0]["name"] == "Decision Recorded"
    assert rerun_report["summary"]["ready_for_candidate_source"] is True
    dumped = json.dumps(rerun_report)
    assert "I want a small tool for team decisions" not in dumped
    assert "/Users/" not in dumped


def test_idea_intake_clarification_rerun_strict_blocks_incomplete_answers(
    tmp_path: Path,
) -> None:
    raw_input, session = build_incomplete_intake(tmp_path)
    requests = build_intake_requests(tmp_path, session)
    incomplete_answers = tmp_path / "answers_incomplete.json"
    answer_payload = load_json(ANSWERS_READY)
    answer_payload["answers"] = answer_payload["answers"][:-1]
    write_json(incomplete_answers, answer_payload)

    result = subprocess.run(
        [
            sys.executable,
            str(RERUN_TOOL),
            "--raw-input",
            str(raw_input),
            "--clarification-requests",
            str(requests),
            "--answers",
            str(incomplete_answers),
            "--validated-answers-output",
            str(tmp_path / "answers_report.json"),
            "--rerun-input-output",
            str(tmp_path / "rerun_input.json"),
            "--clarified-raw-output",
            str(tmp_path / "clarified_raw.json"),
            "--clarified-session-output",
            str(tmp_path / "clarified_session.json"),
            "--clarified-source-output",
            str(tmp_path / "clarified_source.json"),
            "--report-output",
            str(tmp_path / "rerun_report.json"),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    report = load_json(tmp_path / "rerun_report.json")
    assert report["readiness"]["ready"] is False
    assert "idea_intake_clarification_rerun_session_not_ready" in report["readiness"]["blocked_by"]
    assert not (tmp_path / "clarified_source.json").exists()


def test_real_idea_intake_make_targets_build_ready_candidate_source(
    tmp_path: Path,
) -> None:
    python = supported_python()
    raw_input = tmp_path / "local_operator_user_idea_raw_input.json"
    session = tmp_path / "user_idea_intake_session.json"
    source = tmp_path / "user_idea_intake_source.json"
    report = tmp_path / "user_idea_intake_interview_report.json"
    requests = tmp_path / "idea_intake_clarification_requests.json"
    answers = tmp_path / "idea_intake_clarification_answers.json"
    rerun_input = tmp_path / "idea_intake_answer_rerun_input.json"
    clarified_raw = tmp_path / "local_operator_clarified_user_idea_raw_input.json"
    clarified_session = tmp_path / "clarified_user_idea_intake_session.json"
    clarified_source = tmp_path / "clarified_user_idea_intake_source.json"
    rerun_report = tmp_path / "idea_intake_clarification_rerun_report.json"
    bridge_report = tmp_path / "intake_session_candidate_source_report.json"

    result = subprocess.run(
        [
            "make",
            "real-idea-intake-clarification-rerun",
            f"PYTHON={python}",
            "SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT=I want a small tool for team decisions.",
            "USER_IDEA_INTAKE_INTERVIEW_IDEA_SUMMARY=Track team decisions.",
            "USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID=team-decision-log",
            "USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME=Team Decision Log",
            "USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE=/team-decision-log",
            f"USER_IDEA_RAW_INPUT_OUTPUT={raw_input}",
            f"USER_IDEA_INTAKE_SESSION_OUTPUT={session}",
            f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={source}",
            f"USER_IDEA_INTAKE_INTERVIEW_REPORT_OUTPUT={report}",
            f"IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT={requests}",
            f"IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT={ANSWERS_READY}",
            f"IDEA_INTAKE_CLARIFICATION_ANSWERS_OUTPUT={answers}",
            f"IDEA_INTAKE_ANSWER_RERUN_INPUT_OUTPUT={rerun_input}",
            f"CLARIFIED_USER_IDEA_RAW_INPUT_OUTPUT={clarified_raw}",
            f"CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT={clarified_session}",
            f"CLARIFIED_USER_IDEA_INTAKE_SOURCE_OUTPUT={clarified_source}",
            f"IDEA_INTAKE_CLARIFICATION_RERUN_REPORT_OUTPUT={rerun_report}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert load_json(rerun_report)["summary"]["ready_for_candidate_source"] is True

    bridge_result = subprocess.run(
        [
            "make",
            "real-idea-intake-ready-candidate-source",
            f"PYTHON={python}",
            f"USER_IDEA_INTAKE_SESSION_OUTPUT={session}",
            f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={source}",
            f"CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT={clarified_session}",
            f"INTAKE_SESSION_CANDIDATE_SOURCE_REPORT_OUTPUT={bridge_report}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert bridge_result.returncode == 0, bridge_result.stderr
    bridge = load_json(bridge_report)
    emitted_source = load_json(source)
    assert bridge["summary"]["status"] == "candidate_source_ready"
    assert bridge["source_refs"]["intake_session"].endswith(
        "clarified_user_idea_intake_session.json"
    )
    assert emitted_source["workspace"]["candidate_id"] == "team-decision-log"
