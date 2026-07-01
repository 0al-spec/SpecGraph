from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "specspace_real_idea_answer_handoff.py"
AUTHORING_TOOL = ROOT / "tools" / "real_idea_answer_authoring.py"
INTERVIEW_TOOL = ROOT / "tools" / "user_idea_intake_interview.py"
REQUESTS_TOOL = ROOT / "tools" / "idea_to_spec_clarification_requests.py"
INTAKE_ANSWERS = ROOT / "tests" / "fixtures" / "idea_intake_clarification" / "answers_ready.json"


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


def finding_ids(report: dict[str, object]) -> set[str]:
    return {finding["finding_id"] for finding in report["findings"] if isinstance(finding, dict)}


def prepare_run_dir(run_dir: Path, *, candidate_id: str = "team-decision-log") -> dict[str, Path]:
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    raw_input = run_dir / "local_operator_user_idea_raw_input.json"
    session = run_dir / "user_idea_intake_session.json"
    source = run_dir / "user_idea_intake_source.json"
    report = run_dir / "user_idea_intake_interview_report.json"
    interview = subprocess.run(
        [
            sys.executable,
            str(INTERVIEW_TOOL),
            "--idea-text",
            "I want a small tool for team decisions.",
            "--idea-summary",
            "Track team decisions.",
            "--candidate-id",
            candidate_id,
            "--display-name",
            "Team Decision Log",
            "--public-route",
            f"/{candidate_id}",
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
    assert interview.returncode == 0, interview.stderr
    requests = run_dir / "idea_intake_clarification_requests.json"
    request_result = subprocess.run(
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
    assert request_result.returncode == 0, request_result.stderr
    authoring = load_module(AUTHORING_TOOL, "real_idea_answer_authoring_for_handoff_test")
    template = authoring.build_template(
        clarification_requests=load_json(requests),
        requests_path=requests,
        stage="intake",
        run_dir=run_dir,
    )
    template_path = run_dir / "real_idea_answer_template.json"
    write_json(template_path, template)
    return {
        "run_dir": run_dir,
        "session": session,
        "requests": requests,
        "template": template_path,
    }


def specspace_state(
    paths: dict[str, Path], *, candidate_id: str = "team-decision-log"
) -> dict[str, object]:
    answers = load_json(INTAKE_ANSWERS)
    requests_ref = paths["requests"].resolve().relative_to(ROOT).as_posix()
    template_ref = paths["template"].resolve().relative_to(ROOT).as_posix()
    rows = []
    for index, answer in enumerate(answers["answers"]):
        row = {
            **answer,
            "answer_id": f"specspace-intake-answer::{candidate_id}::{answer['request_id']}",
            "workspace_id": candidate_id,
            "candidate_id": candidate_id,
            "request_kind": "intake_context_gap",
            "request_status": "open",
            "target_artifact": "user_idea_intake_session",
            "target_ref": f"active_frame.{index}",
            "operator_ref": "local_operator",
            "created_at": "2026-07-01T00:00:00Z",
            "updated_at": "2026-07-01T00:00:00Z",
            "source_artifact": requests_ref,
            "template_ref": template_ref,
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "applies_to_specgraph": False,
            "applies_to_candidate_source": False,
            "mutates_user_intent": False,
            "mutates_canonical_specs": False,
            "writes_ontology_package": False,
            "accepts_ontology_terms": False,
            "creates_branch_or_commit": False,
            "opens_pull_request": False,
        }
        rows.append(row)
    return {
        "artifact_kind": "specspace_idea_intake_clarification_answer_state",
        "schema_version": 1,
        "state_owner": "SpecSpace",
        "selected_workspace_id": candidate_id,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "intake_clarification_requests": requests_ref,
            "real_idea_answer_template": template_ref,
        },
        "answer_set": answers,
        "answers": rows,
        "summary": {
            "status": "intake_clarification_answers_recorded",
            "answer_count": len(rows),
            "accepted_answer_count": len(rows),
            "invalid_answer_count": 0,
            "workspace_count": 1,
        },
        "consumer_boundary": {
            "specspace_owned_state": True,
            "for_real_idea_intake_workflow": True,
            "may_execute_specgraph": False,
            "may_execute_prompt_agent": False,
            "may_apply_to_specgraph": False,
            "may_apply_answers": False,
            "may_mutate_candidate_source_artifacts": False,
            "may_mutate_canonical_specs": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
            "may_create_branch_or_commit": False,
            "may_open_pull_request": False,
            "may_execute_git_service_operation": False,
        },
        "authority_boundary": {
            "intake_answer_state_is_authority": False,
            "specgraph_artifact_authority": False,
            "ontology_authority": False,
            "git_service_authority": False,
            "canonical_mutations_allowed": False,
        },
    }


def test_specspace_real_idea_answer_import_preview_accepts_state() -> None:
    module = load_module(TOOL_PATH, "specspace_real_idea_answer_handoff_under_test")
    run_dir = ROOT / ".pytest_cache" / "specspace_real_idea_answer_handoff" / "happy"
    paths = prepare_run_dir(run_dir)
    state_path = run_dir / "idea_to_spec_intake_clarification_answers.json"
    write_json(state_path, specspace_state(paths))

    preview = module.build_import_preview(
        specspace_answer_state=load_json(state_path),
        state_path=state_path,
        template=load_json(paths["template"]),
        template_path=paths["template"],
        clarification_requests=load_json(paths["requests"]),
        requests_path=paths["requests"],
        intake_session=load_json(paths["session"]),
        intake_session_path=paths["session"],
        run_dir=run_dir,
        stage="intake",
    )

    assert preview["artifact_kind"] == "specspace_real_idea_answer_import_preview"
    assert preview["readiness"]["ready"] is True
    assert preview["summary"]["accepted_answer_count"] == 9
    dumped = json.dumps(preview)
    assert "I want a small tool for team decisions" not in dumped
    assert "/Users/" not in dumped


def test_specspace_real_idea_answer_handoff_materializes_continuation() -> None:
    module = load_module(TOOL_PATH, "specspace_real_idea_answer_handoff_materialize_test")
    run_dir = ROOT / ".pytest_cache" / "specspace_real_idea_answer_handoff" / "materialize"
    paths = prepare_run_dir(run_dir)
    state_path = run_dir / "idea_to_spec_intake_clarification_answers.json"
    write_json(state_path, specspace_state(paths))
    preview = module.build_import_preview(
        specspace_answer_state=load_json(state_path),
        state_path=state_path,
        template=load_json(paths["template"]),
        template_path=paths["template"],
        clarification_requests=load_json(paths["requests"]),
        requests_path=paths["requests"],
        intake_session=load_json(paths["session"]),
        intake_session_path=paths["session"],
        run_dir=run_dir,
        stage="intake",
    )
    preview_path = run_dir / "specspace_real_idea_answer_import_preview.json"
    write_json(preview_path, preview)

    report = module.build_continuation_report(
        import_preview=preview,
        import_preview_path=preview_path,
        clarification_requests=load_json(paths["requests"]),
        requests_path=paths["requests"],
        answer_set_output=run_dir / "real_idea_answer_set.json",
        validated_answers_output=run_dir / "idea_intake_clarification_answers.json",
        authoring_report_output=run_dir / "real_idea_answer_authoring_report.json",
        run_dir=run_dir,
        stage="intake",
    )

    assert report["readiness"]["ready"] is True
    assert (run_dir / "clarified_user_idea_intake_session.json").exists()
    assert (run_dir / "idea_intake_clarification_rerun_report.json").exists()
    assert report["summary"]["status"] == "real_idea_answer_continuation_ready"


def test_specspace_real_idea_answer_import_preview_blocks_cross_candidate_state() -> None:
    module = load_module(TOOL_PATH, "specspace_real_idea_answer_handoff_cross_candidate_test")
    run_dir = ROOT / ".pytest_cache" / "specspace_real_idea_answer_handoff" / "cross"
    paths = prepare_run_dir(run_dir)
    state_path = run_dir / "idea_to_spec_intake_clarification_answers.json"
    write_json(state_path, specspace_state(paths, candidate_id="other-product"))

    preview = module.build_import_preview(
        specspace_answer_state=load_json(state_path),
        state_path=state_path,
        template=load_json(paths["template"]),
        template_path=paths["template"],
        clarification_requests=load_json(paths["requests"]),
        requests_path=paths["requests"],
        intake_session=load_json(paths["session"]),
        intake_session_path=paths["session"],
        run_dir=run_dir,
        stage="intake",
    )

    assert preview["readiness"]["ready"] is False
    ids = finding_ids(preview)
    assert "specspace_answer_state_workspace_mismatch" in ids
    assert "specspace_answer_candidate_mismatch" in ids


def test_specspace_real_idea_answer_import_preview_blocks_template_mismatch() -> None:
    module = load_module(TOOL_PATH, "specspace_real_idea_answer_handoff_template_test")
    run_dir = ROOT / ".pytest_cache" / "specspace_real_idea_answer_handoff" / "template"
    paths = prepare_run_dir(run_dir)
    state = specspace_state(paths)
    state["source_artifacts"]["real_idea_answer_template"] = "runs/other/template.json"
    state_path = run_dir / "idea_to_spec_intake_clarification_answers.json"
    write_json(state_path, state)

    preview = module.build_import_preview(
        specspace_answer_state=load_json(state_path),
        state_path=state_path,
        template=load_json(paths["template"]),
        template_path=paths["template"],
        clarification_requests=load_json(paths["requests"]),
        requests_path=paths["requests"],
        intake_session=load_json(paths["session"]),
        intake_session_path=paths["session"],
        run_dir=run_dir,
        stage="intake",
    )

    assert preview["readiness"]["ready"] is False
    assert "specspace_answer_template_ref_mismatch" in finding_ids(preview)


def test_specspace_real_idea_answer_import_preview_blocks_authority_expansion() -> None:
    module = load_module(TOOL_PATH, "specspace_real_idea_answer_handoff_authority_test")
    run_dir = ROOT / ".pytest_cache" / "specspace_real_idea_answer_handoff" / "authority"
    paths = prepare_run_dir(run_dir)
    state = specspace_state(paths)
    state["consumer_boundary"]["may_execute_specgraph"] = True
    state["answer_set"]["answers"][0]["value"]["may_write_ontology_package"] = True
    state_path = run_dir / "idea_to_spec_intake_clarification_answers.json"
    write_json(state_path, state)

    preview = module.build_import_preview(
        specspace_answer_state=load_json(state_path),
        state_path=state_path,
        template=load_json(paths["template"]),
        template_path=paths["template"],
        clarification_requests=load_json(paths["requests"]),
        requests_path=paths["requests"],
        intake_session=load_json(paths["session"]),
        intake_session_path=paths["session"],
        run_dir=run_dir,
        stage="intake",
    )

    assert preview["readiness"]["ready"] is False
    ids = finding_ids(preview)
    assert "specspace_answer_state_authority_expanded" in ids
    assert "authority_field_expanded" in ids


def test_specspace_real_idea_answer_handoff_cli_strict_fails_when_not_ready() -> None:
    run_dir = ROOT / ".pytest_cache" / "specspace_real_idea_answer_handoff" / "cli-strict"
    paths = prepare_run_dir(run_dir)
    state = specspace_state(paths, candidate_id="other-product")
    state_path = run_dir / "idea_to_spec_intake_clarification_answers.json"
    write_json(state_path, state)

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "preview",
            "--run-dir",
            run_dir.resolve().relative_to(ROOT).as_posix(),
            "--specspace-answers",
            str(state_path),
            "--template",
            str(paths["template"]),
            "--requests",
            str(paths["requests"]),
            "--intake-session",
            str(paths["session"]),
            "--output",
            str(run_dir / "specspace_real_idea_answer_import_preview.json"),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "specspace_real_idea_answers_review_required" in result.stdout
