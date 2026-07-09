from __future__ import annotations

import importlib.util
import json
import os
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


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


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
    assert load_json(requests)["summary"]["blocking_request_count"] == 10
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
    rerun_report = load_json(report)
    assert rerun["artifact_kind"] == "idea_intake_answer_rerun_input"
    assert rerun["readiness"]["ready"] is True
    assert len(rerun["accepted_answer_targets"]) == 10
    assert session_payload["readiness"]["review_state"] == "ready_for_event_storming_intake"
    assert not clarified_source.exists()
    assert rerun_report["summary"]["ready_for_candidate_source"] is True
    assert rerun_report["summary"]["source_written"] is False
    assert rerun_report["summary"]["source_materialization"] == (
        "intake_session_candidate_source_bridge_required"
    )
    assert rerun_report["output_refs"]["clarified_intake_source"] is None
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

    requests_result = subprocess.run(
        [
            "make",
            "real-idea-intake-clarification-requests",
            f"PYTHON={python}",
            "REAL_IDEA_INTAKE_REFRESH=1",
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
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert requests_result.returncode == 0, requests_result.stderr

    result = subprocess.run(
        [
            "make",
            "real-idea-intake-clarification-rerun",
            f"PYTHON={python}",
            f"USER_IDEA_RAW_INPUT_OUTPUT={raw_input}",
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
    assert not clarified_source.exists()

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


def test_real_idea_intake_clarification_requests_preserves_existing_session(
    tmp_path: Path,
) -> None:
    python = supported_python()
    raw_input, session = build_incomplete_intake(tmp_path)
    before = load_json(session)
    requests = tmp_path / "idea_intake_clarification_requests.json"

    result = subprocess.run(
        [
            "make",
            "real-idea-intake-clarification-requests",
            f"PYTHON={python}",
            "SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT=This text must not overwrite session.",
            "USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID=wrong-candidate",
            f"USER_IDEA_RAW_INPUT_OUTPUT={raw_input}",
            f"USER_IDEA_INTAKE_SESSION_OUTPUT={session}",
            f"IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT={requests}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    after = load_json(session)
    request_payload = load_json(requests)
    assert after == before
    assert after["workspace"]["candidate_id"] == "team-decision-log"
    assert request_payload["summary"]["blocking_request_count"] == 10


def test_real_idea_intake_active_candidate_target_builds_seed_first(
    tmp_path: Path,
) -> None:
    python = supported_python()
    run_rel = Path("runs") / f"test_real_idea_active_candidate_{tmp_path.name}"
    run_dir = ROOT / run_rel
    shutil.rmtree(run_dir, ignore_errors=True)
    try:
        raw_input = run_rel / "local_operator_user_idea_raw_input.json"
        session = run_rel / "user_idea_intake_session.json"
        source = run_rel / "user_idea_intake_source.json"
        report = run_rel / "user_idea_intake_interview_report.json"
        requests = run_rel / "idea_intake_clarification_requests.json"
        answers = run_rel / "idea_intake_clarification_answers.json"
        rerun_input = run_rel / "idea_intake_answer_rerun_input.json"
        clarified_raw = run_rel / "local_operator_clarified_user_idea_raw_input.json"
        clarified_session = run_rel / "clarified_user_idea_intake_session.json"
        clarified_source = run_rel / "clarified_user_idea_intake_source.json"
        rerun_report = run_rel / "idea_intake_clarification_rerun_report.json"
        bridge_report = run_rel / "intake_session_candidate_source_report.json"
        event_seed = run_rel / "idea_event_storming_seed.json"
        intake = run_rel / "idea_event_storming_intake.json"
        candidate_seed = run_rel / "candidate_spec_graph_seed.json"
        candidate_graph = run_rel / "candidate_spec_graph.json"
        pre_sib = run_rel / "pre_sib_coherence_report.json"
        repair_loop = run_rel / "candidate_repair_loop_report.json"
        downstream_requests = run_rel / "idea_to_spec_clarification_requests.json"
        materialized_dir = run_rel / "materialized_candidate"
        materialization = run_rel / "candidate_spec_materialization_report.json"
        promotion_gate = run_rel / "idea_to_spec_promotion_gate.json"
        active_candidate = run_rel / "active_idea_to_spec_candidate.json"

        for args in (
            [
                "real-idea-intake-clarification-requests",
                "REAL_IDEA_INTAKE_REFRESH=1",
                (
                    "SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT="
                    "I want a small tool for comparing product prices by weight."
                ),
                "USER_IDEA_INTAKE_INTERVIEW_IDEA_SUMMARY=Compare unit prices.",
                "USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID=store-unit-price-helper",
                "USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME=Store Unit Price Helper",
                "USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE=/store-unit-price-helper",
                f"USER_IDEA_RAW_INPUT_OUTPUT={raw_input}",
                f"USER_IDEA_INTAKE_SESSION_OUTPUT={session}",
                f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={source}",
                f"USER_IDEA_INTAKE_INTERVIEW_REPORT_OUTPUT={report}",
                f"IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT={requests}",
            ],
            [
                "real-idea-intake-clarification-rerun",
                f"USER_IDEA_RAW_INPUT_OUTPUT={raw_input}",
                f"IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT={requests}",
                f"IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT={ANSWERS_READY}",
                f"IDEA_INTAKE_CLARIFICATION_ANSWERS_OUTPUT={answers}",
                f"IDEA_INTAKE_ANSWER_RERUN_INPUT_OUTPUT={rerun_input}",
                f"CLARIFIED_USER_IDEA_RAW_INPUT_OUTPUT={clarified_raw}",
                f"CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT={clarified_session}",
                f"CLARIFIED_USER_IDEA_INTAKE_SOURCE_OUTPUT={clarified_source}",
                f"IDEA_INTAKE_CLARIFICATION_RERUN_REPORT_OUTPUT={rerun_report}",
            ],
        ):
            result = subprocess.run(
                ["make", *args, f"PYTHON={python}"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr

        result = subprocess.run(
            [
                "make",
                "real-idea-intake-active-candidate",
                f"PYTHON={python}",
                f"USER_IDEA_RAW_INPUT_OUTPUT={raw_input}",
                f"USER_IDEA_INTAKE_SESSION_OUTPUT={session}",
                f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={source}",
                f"CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT={clarified_session}",
                f"INTAKE_SESSION_CANDIDATE_SOURCE_REPORT_OUTPUT={bridge_report}",
                f"USER_IDEA_EVENT_STORMING_SEED_OUTPUT={event_seed}",
                f"IDEA_EVENT_STORMING_INTAKE_OUTPUT={intake}",
                f"PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT={candidate_seed}",
                f"CANDIDATE_SPEC_GRAPH_OUTPUT={candidate_graph}",
                f"PRE_SIB_COHERENCE_OUTPUT={pre_sib}",
                f"CANDIDATE_REPAIR_LOOP_OUTPUT={repair_loop}",
                f"IDEA_TO_SPEC_CLARIFICATION_OUTPUT={downstream_requests}",
                f"CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR={materialized_dir}",
                f"CANDIDATE_SPEC_MATERIALIZATION_OUTPUT={materialization}",
                f"IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT={promotion_gate}",
                f"ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT={active_candidate}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert load_json(ROOT / event_seed)["artifact_kind"] == "idea_event_storming_seed"
        assert load_json(ROOT / intake)["summary"]["status"] == "ready_for_candidate_graph"
        assert load_json(ROOT / candidate_graph)["summary"]["node_count"] > 0
        active = load_json(ROOT / active_candidate)
        assert active["summary"]["candidate_id"] == "store-unit-price-helper"
        assert "active_candidate_project_mismatch" not in json.dumps(active)
        assert "idea_event_storming_seed_contract_invalid" not in json.dumps(
            load_json(ROOT / intake)
        )
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_real_idea_smoke_target_writes_isolated_run_dir_summary(tmp_path: Path) -> None:
    python = supported_python()
    run_rel = Path(".pytest_cache") / "real_idea_smoke" / tmp_path.name
    run_dir = ROOT / run_rel
    shutil.rmtree(run_dir, ignore_errors=True)
    ready_fixture = ROOT / "tests/fixtures/user_idea_intake_session/raw_idea_ready.json"
    try:
        result = subprocess.run(
            [
                "make",
                "real-idea-smoke",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_rel}",
                f"USER_IDEA_INTAKE_INTERVIEW_INPUT={ready_fixture}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        summary = load_json(run_dir / "real_idea_smoke_summary.json")
        active = load_json(run_dir / "active_idea_to_spec_candidate.json")
        assert summary["artifact_kind"] == "real_idea_smoke_summary"
        assert summary["run_dir"] == run_rel.as_posix()
        assert summary["summary"]["candidate_id"] == "support-triage-log"
        assert summary["artifacts"]["active_candidate"]["present"] is True
        assert active["summary"]["candidate_id"] == "support-triage-log"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_real_idea_smoke_cleanup_covers_wrapper_output_args() -> None:
    module = load_module(ROOT / "tools" / "real_idea_smoke.py", "real_idea_smoke_under_test")
    run_dir_ref = "runs/coverage-smoke"
    args = module._smoke_make_args(run_dir_ref, python="python", interview_input="")
    output_refs = {
        value
        for value in (arg.split("=", 1)[1] for arg in args if "=" in arg)
        if value.startswith(f"{run_dir_ref}/")
    }
    managed_refs = {
        f"{run_dir_ref}/{name}"
        for _, name in [*module.SMOKE_OUTPUT_FILES, *module.SMOKE_OUTPUT_DIRS]
    }

    assert output_refs <= managed_refs


def test_real_idea_smoke_refreshes_existing_managed_outputs(tmp_path: Path) -> None:
    python = supported_python()
    run_rel = Path(".pytest_cache") / "real_idea_smoke_refresh" / tmp_path.name
    run_dir = ROOT / run_rel
    shutil.rmtree(run_dir, ignore_errors=True)
    ready_fixture = ROOT / "tests/fixtures/user_idea_intake_session/raw_idea_ready.json"
    second_fixture = run_dir / "second_raw_idea_ready.json"
    operator_answer_input = run_dir / "idea_to_spec_clarification_answers_input.json"
    stale_validated_answers = run_dir / "idea_to_spec_clarification_answers.json"
    stale_absent_decision = run_dir / "absent-post-approval" / "candidate_approval_decision.json"
    try:
        first = subprocess.run(
            [
                "make",
                "real-idea-smoke",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_rel}",
                f"USER_IDEA_INTAKE_INTERVIEW_INPUT={ready_fixture}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert first.returncode == 0, first.stderr
        assert (
            load_json(run_dir / "active_idea_to_spec_candidate.json")["summary"]["candidate_id"]
            == "support-triage-log"
        )
        write_json(operator_answer_input, {"artifact_kind": "operator_authored_answer_input"})
        write_json(stale_validated_answers, {"artifact_kind": "stale_validated_answers"})
        write_json(stale_absent_decision, {"artifact_kind": "stale_absent_decision"})

        second_payload = load_json(ready_fixture)
        second_payload["workspace"] = {
            "candidate_id": "cash-flow-refresh-smoke",
            "display_name": "Cash Flow Refresh Smoke",
            "public_route": "/cash-flow-refresh-smoke",
        }
        second_payload["idea"] = {
            "summary": "Build a cash-flow assistant that protects recurring payment reserves.",
            "text": (
                "The user records mandatory recurring payments and the system warns "
                "before overspend or overdraft risk."
            ),
        }
        second_payload["active_frame_hints"]["project"] = "CashFlowRefreshSmoke"
        second_payload["active_frame_hints"]["context_refs"] = [
            "context.idea_to_spec",
            "context.cash_flow_refresh_smoke",
        ]
        second_payload["active_frame_hints"]["domain_refs"] = ["domain.cash_flow_refresh_smoke"]
        write_json(second_fixture, second_payload)

        second = subprocess.run(
            [
                "make",
                "real-idea-smoke",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_rel}",
                f"USER_IDEA_INTAKE_INTERVIEW_INPUT={second_fixture}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert second.returncode == 0, second.stderr
        active = load_json(run_dir / "active_idea_to_spec_candidate.json")
        summary = load_json(run_dir / "real_idea_smoke_summary.json")
        assert active["summary"]["candidate_id"] == "cash-flow-refresh-smoke"
        assert summary["summary"]["candidate_id"] == "cash-flow-refresh-smoke"
        assert operator_answer_input.exists()
        assert not stale_validated_answers.exists()
        assert not stale_absent_decision.exists()
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_real_idea_smoke_normalizes_repo_local_absolute_run_dir(tmp_path: Path) -> None:
    python = supported_python()
    run_rel = Path(".pytest_cache") / "real_idea_smoke_abs" / tmp_path.name
    run_dir = ROOT / run_rel
    shutil.rmtree(run_dir, ignore_errors=True)
    ready_fixture = ROOT / "tests/fixtures/user_idea_intake_session/raw_idea_ready.json"
    try:
        result = subprocess.run(
            [
                "make",
                "real-idea-smoke",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_dir}",
                f"REAL_IDEA_SMOKE_SUMMARY_OUTPUT={run_dir / 'real_idea_smoke_summary.json'}",
                f"USER_IDEA_INTAKE_INTERVIEW_INPUT={ready_fixture}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        summary = load_json(run_dir / "real_idea_smoke_summary.json")
        assert summary["run_dir"] == run_rel.as_posix()
        assert summary["summary"]["candidate_id"] == "support-triage-log"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_real_idea_smoke_rejects_external_absolute_run_dir(tmp_path: Path) -> None:
    python = supported_python()
    ready_fixture = ROOT / "tests/fixtures/user_idea_intake_session/raw_idea_ready.json"
    result = subprocess.run(
        [
            "make",
            "real-idea-smoke",
            f"PYTHON={python}",
            f"REAL_IDEA_SMOKE_RUN_DIR={tmp_path}",
            f"REAL_IDEA_SMOKE_SUMMARY_OUTPUT={tmp_path / 'real_idea_smoke_summary.json'}",
            f"USER_IDEA_INTAKE_INTERVIEW_INPUT={ready_fixture}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "REAL_IDEA_SMOKE_RUN_DIR must stay inside the SpecGraph repository" in result.stderr


def test_real_idea_smoke_rejects_shared_runs_directory() -> None:
    python = supported_python()
    ready_fixture = ROOT / "tests/fixtures/user_idea_intake_session/raw_idea_ready.json"
    result = subprocess.run(
        [
            "make",
            "real-idea-smoke",
            f"PYTHON={python}",
            "REAL_IDEA_SMOKE_RUN_DIR=runs",
            f"USER_IDEA_INTAKE_INTERVIEW_INPUT={ready_fixture}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "REAL_IDEA_SMOKE_RUN_DIR=runs is reserved for shared SpecGraph runs" in result.stderr


def test_real_idea_smoke_clears_ambient_active_candidate_config(tmp_path: Path) -> None:
    python = supported_python()
    run_rel = Path(".pytest_cache") / "real_idea_smoke_config" / tmp_path.name
    run_dir = ROOT / run_rel
    shutil.rmtree(run_dir, ignore_errors=True)
    ready_fixture = ROOT / "tests/fixtures/user_idea_intake_session/raw_idea_ready.json"
    env = os.environ.copy()
    env["PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG"] = "tests/fixtures/missing-config.json"
    env["ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG"] = "tests/fixtures/missing-config.json"
    try:
        result = subprocess.run(
            [
                "make",
                "real-idea-smoke",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_rel}",
                f"USER_IDEA_INTAKE_INTERVIEW_INPUT={ready_fixture}",
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        active = load_json(run_dir / "active_idea_to_spec_candidate.json")
        assert active["summary"]["candidate_id"] == "support-triage-log"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_real_idea_smoke_writes_summary_for_blocked_intake(tmp_path: Path) -> None:
    python = supported_python()
    run_rel = Path(".pytest_cache") / "real_idea_smoke_blocked" / tmp_path.name
    run_dir = ROOT / run_rel
    shutil.rmtree(run_dir, ignore_errors=True)
    needs_clarification = (
        ROOT / "tests/fixtures/user_idea_intake_session/raw_idea_needs_clarification.json"
    )
    try:
        result = subprocess.run(
            [
                "make",
                "real-idea-smoke",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_rel}",
                f"USER_IDEA_INTAKE_INTERVIEW_INPUT={needs_clarification}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        summary = load_json(run_dir / "real_idea_smoke_summary.json")
        assert summary["artifact_kind"] == "real_idea_smoke_summary"
        assert summary["status"] == "incomplete"
        assert summary["artifacts"]["intake_session"]["present"] is True
        assert summary["artifacts"]["active_candidate"]["present"] is False
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_real_idea_smoke_continue_blocks_without_answers(tmp_path: Path) -> None:
    python = supported_python()
    run_rel = Path(".pytest_cache") / "real_idea_smoke_continue_blocked" / tmp_path.name
    run_dir = ROOT / run_rel
    idea_text = "I want a small tool for team decisions."
    shutil.rmtree(run_dir, ignore_errors=True)
    try:
        first = subprocess.run(
            [
                "make",
                "real-idea-smoke",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_rel}",
                f"SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT={idea_text}",
                "USER_IDEA_INTAKE_INTERVIEW_IDEA_SUMMARY=Track team decisions.",
                "USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID=team-decision-log",
                "USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME=Team Decision Log",
                "USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE=/team-decision-log",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert first.returncode != 0

        continued = subprocess.run(
            [
                "make",
                "real-idea-smoke-continue",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_rel}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert continued.returncode != 0
        report = load_json(run_dir / "real_idea_smoke_session_state_report.json")
        summary = load_json(run_dir / "real_idea_smoke_summary.json")
        assert report["status"] == "blocked"
        assert report["summary"]["continuation_path"] == "await_clarification_answers"
        assert "clarification_answers_input_missing" in report["blocked_by"]
        assert (run_dir / "idea_intake_clarification_requests.json").exists()
        assert summary["artifacts"]["intake_session"]["present"] is True
        assert summary["artifacts"]["active_candidate"]["present"] is False
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_real_idea_smoke_continue_applies_answers_without_refresh_flag(tmp_path: Path) -> None:
    python = supported_python()
    run_rel = Path(".pytest_cache") / "real_idea_smoke_continue_ready" / tmp_path.name
    run_dir = ROOT / run_rel
    idea_text = "I want a small tool for team decisions."
    shutil.rmtree(run_dir, ignore_errors=True)
    try:
        first = subprocess.run(
            [
                "make",
                "real-idea-smoke",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_rel}",
                f"SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT={idea_text}",
                "USER_IDEA_INTAKE_INTERVIEW_IDEA_SUMMARY=Track team decisions.",
                "USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID=team-decision-log",
                "USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME=Team Decision Log",
                "USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE=/team-decision-log",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert first.returncode != 0
        stale_active = run_dir / "active_idea_to_spec_candidate.json"
        write_json(stale_active, {"artifact_kind": "stale_active_candidate"})
        stale_clarified = load_json(run_dir / "user_idea_intake_session.json")
        stale_clarified["readiness"] = {
            "ready": False,
            "review_state": "needs_clarification",
            "blocked_by": ["stale_test_session"],
        }
        write_json(run_dir / "clarified_user_idea_intake_session.json", stale_clarified)
        env = os.environ.copy()
        env["REAL_IDEA_INTAKE_REFRESH"] = "1"
        env["SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT"] = (
            "This continuation must not overwrite the preserved session."
        )
        env["USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID"] = "wrong-continuation-candidate"

        continued = subprocess.run(
            [
                "make",
                "real-idea-smoke-continue",
                f"PYTHON={python}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_rel}",
                f"REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_INPUT={ANSWERS_READY}",
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        assert continued.returncode == 0, continued.stderr
        report = load_json(run_dir / "real_idea_smoke_session_state_report.json")
        summary = load_json(run_dir / "real_idea_smoke_summary.json")
        active = load_json(run_dir / "active_idea_to_spec_candidate.json")
        assert report["status"] == "ready"
        assert report["summary"]["continuation_path"] == "applied_clarification_answers"
        assert report["summary"]["answer_input_present"] is True
        assert (
            load_json(run_dir / "clarified_user_idea_intake_session.json")["readiness"][
                "review_state"
            ]
            == "ready_for_event_storming_intake"
        )
        assert active["artifact_kind"] == "active_idea_to_spec_candidate"
        assert active["summary"]["candidate_id"] == "team-decision-log"
        assert "active_candidate_project_mismatch" not in json.dumps(active)
        assert summary["artifacts"]["active_candidate"]["present"] is True
        assert summary["summary"]["candidate_id"] == "team-decision-log"
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_real_idea_smoke_summary_sanitizes_upstream_summaries(tmp_path: Path) -> None:
    python = supported_python()
    run_dir = tmp_path / "smoke"
    raw_text = "секретный сырой текст идеи"
    write_json(
        run_dir / "active_idea_to_spec_candidate.json",
        {
            "artifact_kind": "active_idea_to_spec_candidate",
            "summary": {
                "status": "active_candidate_ready",
                "candidate_id": "safe-candidate",
                "workspace_route": "/safe-candidate",
                "raw_idea_text": raw_text,
                "debug_payload": {"raw_idea_text": raw_text},
            },
            "readiness": {"ready": True},
        },
    )
    output = tmp_path / "real_idea_smoke_summary.json"

    result = subprocess.run(
        [
            python,
            "tools/real_idea_smoke_summary.py",
            "--run-dir",
            str(run_dir),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    summary = load_json(output)
    serialized = json.dumps(summary, ensure_ascii=False)
    assert summary["summary"]["candidate_id"] == "safe-candidate"
    assert summary["artifacts"]["active_candidate"]["summary"] == {
        "candidate_id": "safe-candidate",
        "status": "active_candidate_ready",
        "workspace_route": "/safe-candidate",
    }
    assert raw_text not in serialized


def test_product_workspace_active_candidate_rejects_direct_intake_source(
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

    setup = subprocess.run(
        [
            "make",
            "real-idea-intake-clarification-requests",
            f"PYTHON={python}",
            "REAL_IDEA_INTAKE_REFRESH=1",
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
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert setup.returncode == 0, setup.stderr
    rerun = subprocess.run(
        [
            "make",
            "real-idea-intake-clarification-rerun",
            f"PYTHON={python}",
            f"USER_IDEA_RAW_INPUT_OUTPUT={raw_input}",
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
    assert rerun.returncode == 0, rerun.stderr
    bridge = subprocess.run(
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
    assert bridge.returncode == 0, bridge.stderr

    result = subprocess.run(
        [
            "make",
            "product-workspace-active-candidate",
            f"PYTHON={python}",
            f"PRODUCT_WORKSPACE_INTAKE_SOURCE={source}",
            f"IDEA_EVENT_STORMING_INTAKE_OUTPUT={tmp_path / 'intake.json'}",
            f"PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT={tmp_path / 'seed.json'}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "PRODUCT_WORKSPACE_INTAKE_SOURCE points to user_idea_intake_source" in (result.stderr)


def test_product_workspace_active_candidate_reports_invalid_intake_json(
    tmp_path: Path,
) -> None:
    python = supported_python()
    invalid_source = tmp_path / "invalid_intake_source.json"
    invalid_source.write_text("{not-json\n", encoding="utf-8")

    result = subprocess.run(
        [
            "make",
            "product-workspace-active-candidate",
            f"PYTHON={python}",
            f"PRODUCT_WORKSPACE_INTAKE_SOURCE={invalid_source}",
            f"IDEA_EVENT_STORMING_INTAKE_OUTPUT={tmp_path / 'intake.json'}",
            f"PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT={tmp_path / 'seed.json'}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "PRODUCT_WORKSPACE_INTAKE_SOURCE is not valid JSON." in result.stderr
    assert "points to user_idea_intake_source" not in result.stderr


def test_real_idea_intake_clarification_rerun_requires_explicit_answers(
    tmp_path: Path,
) -> None:
    python = supported_python()
    result = subprocess.run(
        [
            "make",
            "real-idea-intake-clarification-rerun",
            f"PYTHON={python}",
            f"USER_IDEA_RAW_INPUT_OUTPUT={tmp_path / 'raw.json'}",
            f"IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT={tmp_path / 'requests.json'}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT=<json> is required" in result.stderr
