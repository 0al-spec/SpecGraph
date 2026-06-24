from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "user_idea_intake_session.py"
SOURCE_TOOL_PATH = ROOT / "tools" / "user_idea_intake_source.py"
INTAKE_TOOL_PATH = ROOT / "tools" / "idea_event_storming_intake.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "user_idea_intake_session"
READY_FIXTURE = FIXTURE_DIR / "raw_idea_ready.json"
NEEDS_CLARIFICATION_FIXTURE = FIXTURE_DIR / "raw_idea_needs_clarification.json"
PREPARED_SOURCE_FIXTURE = ROOT / "tests" / "fixtures" / "user_idea_intake" / "source_ready.json"


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


def test_user_idea_intake_session_writes_ready_source_contract(tmp_path: Path) -> None:
    module = load_module(TOOL_PATH, "user_idea_intake_session_ready")
    source_output = tmp_path / "user_idea_intake_source.json"

    session, source = module.build_user_idea_intake_session(
        load_json(READY_FIXTURE),
        source_path=READY_FIXTURE,
        source_output_path=source_output,
    )

    assert session["artifact_kind"] == "user_idea_intake_session"
    assert session["contract_ref"] == "specgraph.idea-to-spec.user-idea-intake-session.v0.1"
    assert session["readiness"]["ready"] is True
    assert session["readiness"]["review_state"] == "ready_for_event_storming_intake"
    assert session["summary"]["source_written"] is True
    assert session["source_output"]["written"] is True
    assert session["source_output"]["digest"]
    assert session["intent"]["raw_text_published"] is False
    assert source is not None
    assert source["artifact_kind"] == "user_idea_intake_source"
    assert source["contract_ref"] == "specgraph.idea-to-spec.user-idea-intake-source.v0.1"
    assert source["workspace"]["candidate_id"] == "support-triage-log"
    assert source["active_frame_hints"]["ontology_refs"] == ["ontology://specgraph-core"]
    assert source["active_frame_hints"]["ontology_layer_refs"] == ["objective", "mechanics"]
    assert source["active_frame_hints"]["model_applicability_refs"] == [
        "model-applicability://specgraph-core/product-spec-mvp"
    ]
    assert source["source_session"]["proposal_id"] == "0162"
    assert source["intent"]["text"] == ""
    assert source["intent"]["summary"]
    assert load_json(READY_FIXTURE)["idea"]["text"] not in json.dumps(source)
    assert "raw_prompt" not in json.dumps(source)
    assert "private prompt trace" not in json.dumps(source)


def test_user_idea_intake_session_redacts_raw_text_trace_fields(tmp_path: Path) -> None:
    module = load_module(TOOL_PATH, "user_idea_intake_session_redaction")
    payload = copy.deepcopy(load_json(READY_FIXTURE))
    payload["event_storming_hints"]["actors"][0]["raw_text"] = "SECRET-RAW-TEXT-TRACE"
    payload["event_storming_hints"]["actors"][0]["raw_debug"] = "SECRET-RAW-DEBUG"
    payload["event_storming_hints"]["actors"][0]["operator_note"] = "SECRET-OPERATOR-NOTE"
    payload["event_storming_hints"]["actors"][0]["operator_notes"] = ["SECRET-OPERATOR-NOTES"]
    payload["event_storming_hints"]["actors"][0]["private_note"] = "SECRET-NOTE"

    session, source = module.build_user_idea_intake_session(
        payload,
        source_path=READY_FIXTURE,
        source_output_path=tmp_path / "user_idea_intake_source.json",
    )

    assert session["readiness"]["ready"] is True
    assert source is not None
    dumped = json.dumps(source)
    assert "raw_text" not in dumped
    assert "raw_debug" not in dumped
    assert "operator_note" not in dumped
    assert "operator_notes" not in dumped
    assert "private_note" not in dumped
    assert "SECRET-RAW-TEXT-TRACE" not in dumped
    assert "SECRET-RAW-DEBUG" not in dumped
    assert "SECRET-OPERATOR-NOTE" not in dumped
    assert "SECRET-OPERATOR-NOTES" not in dumped
    assert "SECRET-NOTE" not in dumped


def test_user_idea_intake_session_needs_clarification_without_context() -> None:
    module = load_module(TOOL_PATH, "user_idea_intake_session_clarification")

    session, source = module.build_user_idea_intake_session(
        load_json(NEEDS_CLARIFICATION_FIXTURE),
        source_path=NEEDS_CLARIFICATION_FIXTURE,
    )

    assert source is None
    assert session["readiness"]["ready"] is False
    assert session["readiness"]["review_state"] == "needs_clarification"
    assert session["clarification_questions"]
    assert "question.active-frame.ontology_refs" in {
        question["id"] for question in session["clarification_questions"]
    }
    assert "question.event-storming.actors" in {
        question["id"] for question in session["clarification_questions"]
    }
    assert "user_idea_session_domain_refs_missing" in {
        finding["finding_id"] for finding in session["findings"]
    }
    assert session["source_output"]["written"] is False
    assert session["source_output"]["digest"] is None


def test_user_idea_intake_session_source_feeds_existing_intake_chain(tmp_path: Path) -> None:
    session_module = load_module(TOOL_PATH, "user_idea_intake_session_chain")
    source_module = load_module(SOURCE_TOOL_PATH, "user_idea_intake_source_from_session")
    intake_module = load_module(INTAKE_TOOL_PATH, "idea_event_storming_from_session_source")
    session, source = session_module.build_user_idea_intake_session(
        load_json(READY_FIXTURE),
        source_path=READY_FIXTURE,
        source_output_path=tmp_path / "user_idea_intake_source.json",
    )

    assert session["readiness"]["ready"] is True
    assert source is not None
    seed = source_module.build_user_idea_event_storming_seed(
        source,
        source_path=READY_FIXTURE,
    )
    intake = intake_module.build_idea_event_storming_intake(
        seed,
        source_path=READY_FIXTURE,
    )

    assert seed["artifact_kind"] == "idea_event_storming_seed"
    assert seed["source_intake"]["summary"]["status"] == "ready_for_event_storming_intake"
    assert intake["artifact_kind"] == "idea_event_storming_intake"
    assert intake["candidate_graph_readiness"]["ready"] is True
    assert intake["source_intake"]["workspace"]["candidate_id"] == "support-triage-log"


def test_user_idea_intake_session_cli_writes_session_and_source(tmp_path: Path) -> None:
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(READY_FIXTURE),
            "--session-output",
            str(session_output),
            "--source-output",
            str(source_output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    session = load_json(session_output)
    source = load_json(source_output)
    assert session["readiness"]["ready"] is True
    assert source["artifact_kind"] == "user_idea_intake_source"
    assert "source_written" in result.stdout


def test_user_idea_intake_session_strict_cli_rejects_missing_context(
    tmp_path: Path,
) -> None:
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(NEEDS_CLARIFICATION_FIXTURE),
            "--session-output",
            str(session_output),
            "--source-output",
            str(source_output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert session_output.exists()
    assert not source_output.exists()
    session = load_json(session_output)
    assert session["readiness"]["review_state"] == "needs_clarification"


def test_user_idea_intake_session_removes_stale_source_when_not_ready(
    tmp_path: Path,
) -> None:
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"

    ready_result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(READY_FIXTURE),
            "--session-output",
            str(session_output),
            "--source-output",
            str(source_output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert ready_result.returncode == 0
    assert source_output.exists()

    not_ready_result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(NEEDS_CLARIFICATION_FIXTURE),
            "--session-output",
            str(session_output),
            "--source-output",
            str(source_output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert not_ready_result.returncode == 0
    assert not source_output.exists()
    session = load_json(session_output)
    assert session["readiness"]["review_state"] == "needs_clarification"
    assert session["source_output"]["written"] is False


def test_generic_idea_intake_session_target_is_strict_and_removes_stale_source(
    tmp_path: Path,
) -> None:
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"
    seed_output = tmp_path / "idea_event_storming_seed.json"
    intake_output = tmp_path / "idea_event_storming_intake.json"
    write_json(source_output, {"artifact_kind": "stale_source"})

    result = subprocess.run(
        [
            "make",
            "generic-idea-intake-session",
            f"PYTHON={sys.executable}",
            f"USER_IDEA_INTAKE_SESSION_INPUT={NEEDS_CLARIFICATION_FIXTURE}",
            f"USER_IDEA_INTAKE_SESSION_OUTPUT={session_output}",
            f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={source_output}",
            f"USER_IDEA_EVENT_STORMING_SEED_OUTPUT={seed_output}",
            f"IDEA_EVENT_STORMING_INTAKE_OUTPUT={intake_output}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert session_output.exists()
    assert not source_output.exists()
    assert not seed_output.exists()
    assert not intake_output.exists()


def test_user_idea_intake_session_cli_idea_text_uses_cli_source_ref(tmp_path: Path) -> None:
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--idea-text",
            "A lightweight product for reviewing team decisions.",
            "--session-output",
            str(session_output),
            "--source-output",
            str(source_output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert session_output.exists()
    assert not source_output.exists()
    session = load_json(session_output)
    assert session["source_ref"] == "cli:idea-text"
    assert session["readiness"]["review_state"] == "needs_clarification"


def test_prepared_source_without_constraints_remains_compatible(tmp_path: Path) -> None:
    prepared = copy.deepcopy(load_json(PREPARED_SOURCE_FIXTURE))
    prepared["event_storming_hints"].pop("constraints", None)
    prepared_source = tmp_path / "prepared_source_without_constraints.json"
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"
    write_json(prepared_source, prepared)

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(prepared_source),
            "--session-output",
            str(session_output),
            "--source-output",
            str(source_output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    session = load_json(session_output)
    source = load_json(source_output)
    assert session["readiness"]["ready"] is True
    assert source["event_storming_hints"]["constraints"] == []

    source_module = load_module(SOURCE_TOOL_PATH, "user_idea_intake_source_constraints")
    seed = source_module.build_user_idea_event_storming_seed(
        source,
        source_path=source_output,
    )
    assert seed["event_storming"]["constraints"][0]["id"] == (
        "constraint.pre-canonical-review-boundary"
    )


def test_prepared_source_requires_supported_contract(tmp_path: Path) -> None:
    prepared = copy.deepcopy(load_json(PREPARED_SOURCE_FIXTURE))
    prepared["schema_version"] = 999
    prepared_source = tmp_path / "prepared_source_bad_schema.json"
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"
    write_json(prepared_source, prepared)

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(prepared_source),
            "--session-output",
            str(session_output),
            "--source-output",
            str(source_output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert session_output.exists()
    assert not source_output.exists()
    session = load_json(session_output)
    assert session["readiness"]["ready"] is False
    assert "user_idea_prepared_source_contract_invalid" in {
        finding["finding_id"] for finding in session["findings"]
    }


def test_user_idea_intake_session_rejects_unlabeled_event_storming_entries(
    tmp_path: Path,
) -> None:
    payload = copy.deepcopy(load_json(READY_FIXTURE))
    payload["event_storming_hints"]["actors"] = [{}]
    raw_input = tmp_path / "raw_idea_invalid_entries.json"
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"
    write_json(raw_input, payload)

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(raw_input),
            "--session-output",
            str(session_output),
            "--source-output",
            str(source_output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert session_output.exists()
    assert not source_output.exists()
    session = load_json(session_output)
    finding_ids = {finding["finding_id"] for finding in session["findings"]}
    assert "user_idea_session_event_storming_entry_invalid" in finding_ids
    assert "user_idea_session_actors_entries_invalid" in finding_ids


def test_user_idea_intake_session_make_target_writes_custom_outputs(tmp_path: Path) -> None:
    session_output = tmp_path / "user_idea_intake_session.json"
    source_output = tmp_path / "user_idea_intake_source.json"

    result = subprocess.run(
        [
            "make",
            "user-idea-intake-session",
            f"PYTHON={sys.executable}",
            f"USER_IDEA_INTAKE_SESSION_INPUT={READY_FIXTURE}",
            f"USER_IDEA_INTAKE_SESSION_OUTPUT={session_output}",
            f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={source_output}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    session = load_json(session_output)
    source = load_json(source_output)
    assert session["readiness"]["ready"] is True
    assert source["workspace"]["candidate_id"] == "support-triage-log"
