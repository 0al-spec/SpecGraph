from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "real_idea_entry_request_import.py"
TEST_PYTHON = ROOT / ".venv" / "bin" / "python"


def load_module() -> object:
    tools_dir = str(ROOT / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    spec = importlib.util.spec_from_file_location("real_idea_entry_request_import", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def entry_state(
    *,
    idea_text: str = "A small app for tracking pantry prices.",
    idea_summary_hint: str | None = "Pantry price helper",
    workspace_id: str = "pantry-price-helper",
    workspace_display_name: str | None = "Pantry Price Helper",
    schema_version: int = 1,
    request_privacy: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "artifact_kind": "specspace_real_idea_entry_request_state",
        "schema_version": schema_version,
        "workspace_id": workspace_id,
        "summary": {"active_submitted_count": 1},
        "privacy_boundary": {
            "raw_idea_text_local_only": True,
            "raw_idea_text_public_safe": False,
            "public_safe": False,
        },
        "authority_boundary": {
            "may_execute_specgraph": False,
            "may_execute_platform": False,
            "may_mutate_candidate_source_artifacts": False,
            "may_mutate_canonical_specs": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
            "may_create_branch_or_commit": False,
            "may_open_pull_request": False,
            "may_publish_read_model": False,
        },
        "requests": [
            {
                "request_id": "entry-001",
                "workspace_id": workspace_id,
                "status": "submitted",
                "idea_text": idea_text,
                "idea_summary_hint": idea_summary_hint,
                "workspace_display_name": workspace_display_name,
                "public_route_hint": f"/{workspace_id}",
                "domain_hints": ["household shopping"],
                "constraints": ["local-only storage"],
                "privacy_boundary": request_privacy
                or {
                    "raw_idea_text_local_only": True,
                    "raw_idea_text_public_safe": False,
                },
                "authority_boundary": {
                    "may_execute_specgraph": False,
                    "may_mutate_candidate_source_artifacts": False,
                    "may_mutate_canonical_specs": False,
                    "may_write_ontology_package": False,
                    "may_accept_ontology_terms": False,
                },
            }
        ],
    }


def test_entry_request_preview_is_sanitized() -> None:
    tool = load_module()
    state = entry_state()
    preview = tool.build_preview(
        state=state,
        state_path=Path("runs/test/real_idea_entry_requests.json"),
        workspace_id="pantry-price-helper",
        request_id="entry-001",
    )

    assert preview["readiness"]["ready"] is True
    assert preview["selected_request"]["candidate_id"] == "pantry-price-helper"
    dumped = json.dumps(preview)
    assert "A small app for tracking pantry prices." not in dumped
    assert "Pantry price helper" not in dumped
    assert "idea_text_digest" in dumped
    assert "public_summary_digest" in dumped


def test_entry_request_preview_blocks_missing_public_summary() -> None:
    tool = load_module()
    preview = tool.build_preview(
        state=entry_state(idea_summary_hint=None),
        state_path=Path("runs/test/real_idea_entry_requests.json"),
        workspace_id="pantry-price-helper",
        request_id="entry-001",
    )

    assert preview["readiness"]["ready"] is False
    assert "real_idea_entry_public_summary_missing" in preview["readiness"]["blocked_by"]


def test_entry_request_preview_blocks_raw_public_summary() -> None:
    tool = load_module()
    preview = tool.build_preview(
        state=entry_state(
            idea_text="A local-only idea with customer-sensitive shopping details.",
            idea_summary_hint="A local-only idea with customer-sensitive shopping details.",
        ),
        state_path=Path("runs/test/real_idea_entry_requests.json"),
        workspace_id="pantry-price-helper",
        request_id="entry-001",
    )

    assert preview["readiness"]["ready"] is False
    assert "real_idea_entry_public_summary_matches_raw_text" in preview["readiness"]["blocked_by"]


def test_entry_request_preview_blocks_private_public_metadata() -> None:
    tool = load_module()
    preview = tool.build_preview(
        state=entry_state(idea_summary_hint="Read draft from /Users/egor/private.md"),
        state_path=Path("runs/test/real_idea_entry_requests.json"),
        workspace_id="pantry-price-helper",
        request_id="entry-001",
    )

    assert preview["readiness"]["ready"] is False
    assert "real_idea_entry_public_metadata_private_marker" in preview["readiness"]["blocked_by"]


def test_entry_request_preview_blocks_request_privacy_claim() -> None:
    tool = load_module()
    preview = tool.build_preview(
        state=entry_state(
            request_privacy={
                "raw_idea_text_local_only": True,
                "raw_idea_text_public_safe": True,
            }
        ),
        state_path=Path("runs/test/real_idea_entry_requests.json"),
        workspace_id="pantry-price-helper",
        request_id="entry-001",
    )

    assert preview["readiness"]["ready"] is False
    assert "real_idea_entry_request_privacy_claim_invalid" in preview["readiness"]["blocked_by"]


def test_entry_request_preview_blocks_invalid_schema_and_workspace() -> None:
    tool = load_module()
    preview = tool.build_preview(
        state=entry_state(
            schema_version=2,
            workspace_id="x",
            workspace_display_name=None,
        ),
        state_path=Path("runs/test/real_idea_entry_requests.json"),
        workspace_id="x",
        request_id="entry-001",
    )

    assert preview["readiness"]["ready"] is False
    assert "real_idea_entry_state_schema_version_unsupported" in preview["readiness"]["blocked_by"]
    assert "real_idea_entry_candidate_id_invalid" in preview["readiness"]["blocked_by"]


def test_entry_request_materialization_writes_local_raw_but_public_report_is_sanitized(
    tmp_path: Path,
) -> None:
    tool = load_module()
    state_path = tmp_path / "real_idea_entry_requests.json"
    state = entry_state()
    write_json(state_path, state)
    preview = tool.build_preview(
        state=state,
        state_path=state_path,
        workspace_id="pantry-price-helper",
        request_id="entry-001",
    )
    preview_path = tmp_path / "specspace_real_idea_entry_request_import_preview.json"
    write_json(preview_path, preview)
    run_dir = tmp_path / "run"

    report = tool.build_materialization(
        state=state,
        state_path=state_path,
        preview=preview,
        preview_path=preview_path,
        run_dir=run_dir,
        raw_output_path=run_dir / "local_operator_user_idea_raw_input.json",
        session_output_path=run_dir / "user_idea_intake_session.json",
        source_output_path=run_dir / "user_idea_intake_source.json",
        report_output_path=run_dir / "user_idea_intake_interview_report.json",
    )

    raw_input = load_json(run_dir / "local_operator_user_idea_raw_input.json")
    session = load_json(run_dir / "user_idea_intake_session.json")
    interview_report = load_json(run_dir / "user_idea_intake_interview_report.json")
    assert raw_input["idea"]["text"] == "A small app for tracking pantry prices."
    assert raw_input["local_only"] is True
    assert raw_input["raw_text_published"] is False
    assert raw_input["active_frame_hints"]["project"] == "PantryPriceHelper"
    assert session["active_frame_hints"]["project"] == "PantryPriceHelper"
    assert session["intent"]["raw_text_published"] is False
    assert report["privacy_boundary"]["raw_idea_text_published"] is False
    assert "A small app for tracking pantry prices." not in json.dumps(report)
    assert "A small app for tracking pantry prices." not in json.dumps(interview_report)


def test_entry_request_materialization_requires_local_operator_raw_output(
    tmp_path: Path,
) -> None:
    tool = load_module()
    state_path = tmp_path / "real_idea_entry_requests.json"
    state = entry_state()
    write_json(state_path, state)
    preview = tool.build_preview(
        state=state,
        state_path=state_path,
        workspace_id="pantry-price-helper",
        request_id="entry-001",
    )
    preview_path = tmp_path / "specspace_real_idea_entry_request_import_preview.json"
    write_json(preview_path, preview)
    run_dir = tmp_path / "run"

    with pytest.raises(SystemExit, match="local_operator_"):
        tool.build_materialization(
            state=state,
            state_path=state_path,
            preview=preview,
            preview_path=preview_path,
            run_dir=run_dir,
            raw_output_path=run_dir / "raw_input.json",
            session_output_path=run_dir / "user_idea_intake_session.json",
            source_output_path=run_dir / "user_idea_intake_source.json",
            report_output_path=run_dir / "user_idea_intake_interview_report.json",
        )


def test_entry_request_materialization_rejects_stale_preview(tmp_path: Path) -> None:
    tool = load_module()
    state_path = tmp_path / "real_idea_entry_requests.json"
    state = entry_state()
    preview = tool.build_preview(
        state=state,
        state_path=state_path,
        workspace_id="pantry-price-helper",
        request_id="entry-001",
    )
    changed_state = entry_state(idea_text="A changed local-only idea.")

    with pytest.raises(SystemExit, match="stale"):
        tool.build_materialization(
            state=changed_state,
            state_path=state_path,
            preview=preview,
            preview_path=tmp_path / "preview.json",
            run_dir=tmp_path / "run",
            raw_output_path=tmp_path / "run" / "local_operator_user_idea_raw_input.json",
            session_output_path=tmp_path / "run" / "user_idea_intake_session.json",
            source_output_path=tmp_path / "run" / "user_idea_intake_source.json",
            report_output_path=tmp_path / "run" / "user_idea_intake_interview_report.json",
        )


def test_entry_request_make_flow_builds_intake_artifacts() -> None:
    run_dir = ROOT / "runs" / "test_real_idea_entry_request_import"
    shutil.rmtree(run_dir, ignore_errors=True)
    try:
        state_path = run_dir / "real_idea_entry_requests.json"
        write_json(state_path, entry_state())
        result = subprocess.run(
            [
                "make",
                "real-idea-intake-from-entry-request",
                f"PYTHON={TEST_PYTHON if TEST_PYTHON.exists() else sys.executable}",
                f"REAL_IDEA_SMOKE_RUN_DIR={run_dir.relative_to(ROOT).as_posix()}",
                f"SPECSPACE_REAL_IDEA_ENTRY_REQUESTS={state_path.relative_to(ROOT).as_posix()}",
                "SPECSPACE_REAL_IDEA_ENTRY_WORKSPACE_ID=pantry-price-helper",
                "SPECSPACE_REAL_IDEA_ENTRY_REQUEST_ID=entry-001",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert (run_dir / "specspace_real_idea_entry_request_import_preview.json").exists()
        assert (run_dir / "real_idea_entry_request_intake_report.json").exists()
        assert (run_dir / "user_idea_intake_session.json").exists()
        assert (run_dir / "idea_intake_clarification_requests.json").exists()
        assert (run_dir / "real_idea_answer_template.json").exists()
        preview = load_json(run_dir / "specspace_real_idea_entry_request_import_preview.json")
        report = load_json(run_dir / "real_idea_entry_request_intake_report.json")
        assert "A small app for tracking pantry prices." not in json.dumps(preview)
        assert "A small app for tracking pantry prices." not in json.dumps(report)
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
