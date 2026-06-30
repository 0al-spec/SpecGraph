from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_TOOL_PATH = ROOT / "tools" / "intake_session_candidate_source.py"
SESSION_TOOL_PATH = ROOT / "tools" / "user_idea_intake_session.py"
SOURCE_TOOL_PATH = ROOT / "tools" / "user_idea_intake_source.py"
INTAKE_TOOL_PATH = ROOT / "tools" / "idea_event_storming_intake.py"
READY_FIXTURE = ROOT / "tests" / "fixtures" / "user_idea_intake_session" / "raw_idea_ready.json"
NEEDS_CLARIFICATION_FIXTURE = (
    ROOT / "tests" / "fixtures" / "user_idea_intake_session" / "raw_idea_needs_clarification.json"
)


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


def ready_session(tmp_path: Path) -> dict[str, object]:
    session_module = load_module(SESSION_TOOL_PATH, "bridge_ready_session")
    session, source = session_module.build_user_idea_intake_session(
        load_json(READY_FIXTURE),
        source_path=READY_FIXTURE,
        source_output_path=tmp_path / "legacy_user_idea_intake_source.json",
    )
    assert source is not None
    return session


def test_intake_session_candidate_source_materializes_ready_source(
    tmp_path: Path,
) -> None:
    bridge = load_module(BRIDGE_TOOL_PATH, "intake_session_bridge_ready")
    source_module = load_module(SOURCE_TOOL_PATH, "bridge_user_idea_source")
    intake_module = load_module(INTAKE_TOOL_PATH, "bridge_event_storming_intake")
    session = ready_session(tmp_path)
    session_path = tmp_path / "user_idea_intake_session.json"
    output_path = tmp_path / "user_idea_intake_source.json"
    write_json(session_path, session)

    source, report = bridge.build_intake_session_candidate_source(
        session,
        session_path=session_path,
        output_path=output_path,
    )

    assert source is not None
    assert report["readiness"]["ready"] is True
    assert report["summary"]["status"] == "candidate_source_ready"
    assert source["artifact_kind"] == "user_idea_intake_source"
    assert source["workspace"]["candidate_id"] == "support-triage-log"
    assert source["source_session"]["bridge_proposal_id"] == "0185"
    assert re.fullmatch(
        r"external:[0-9a-f]{16}:user_idea_intake_session\.json",
        source["source_session"]["source_ref"],
    )
    assert source["intent"]["text"] == ""
    dumped = json.dumps(source)
    assert load_json(READY_FIXTURE)["idea"]["text"] not in dumped
    assert "raw_prompt" not in dumped
    assert "local_operator_user_idea_raw_input" not in dumped

    seed = source_module.build_user_idea_event_storming_seed(source, source_path=output_path)
    intake = intake_module.build_idea_event_storming_intake(seed, source_path=output_path)
    assert seed["artifact_kind"] == "idea_event_storming_seed"
    assert intake["candidate_graph_readiness"]["ready"] is True
    assert intake["source_intake"]["workspace"]["candidate_id"] == "support-triage-log"


def test_intake_session_candidate_source_cli_writes_report_and_source(
    tmp_path: Path,
) -> None:
    session_path = tmp_path / "user_idea_intake_session.json"
    output_path = tmp_path / "user_idea_intake_source.json"
    report_path = tmp_path / "intake_session_candidate_source_report.json"
    write_json(session_path, ready_session(tmp_path))

    result = subprocess.run(
        [
            sys.executable,
            str(BRIDGE_TOOL_PATH),
            "--intake-session",
            str(session_path),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert report_path.exists()
    source = load_json(output_path)
    report = load_json(report_path)
    assert source["artifact_kind"] == "user_idea_intake_source"
    assert report["summary"]["source_written"] is True
    assert "source_written" in result.stdout


def test_intake_session_candidate_source_rejects_not_ready_session(
    tmp_path: Path,
) -> None:
    session_module = load_module(SESSION_TOOL_PATH, "bridge_not_ready_session")
    session, source = session_module.build_user_idea_intake_session(
        load_json(NEEDS_CLARIFICATION_FIXTURE),
        source_path=NEEDS_CLARIFICATION_FIXTURE,
        source_output_path=tmp_path / "user_idea_intake_source.json",
    )
    assert source is None
    session_path = tmp_path / "user_idea_intake_session.json"
    output_path = tmp_path / "user_idea_intake_source.json"
    report_path = tmp_path / "intake_session_candidate_source_report.json"
    write_json(output_path, {"artifact_kind": "stale_source"})
    write_json(session_path, session)

    result = subprocess.run(
        [
            sys.executable,
            str(BRIDGE_TOOL_PATH),
            "--intake-session",
            str(session_path),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert load_json(output_path) == {"artifact_kind": "stale_source"}
    report = load_json(report_path)
    assert report["readiness"]["ready"] is False
    finding_ids = {finding["finding_id"] for finding in report["findings"]}
    assert "intake_session_candidate_source_session_not_ready" in finding_ids


def test_intake_session_candidate_source_external_refs_are_unique(
    tmp_path: Path,
) -> None:
    bridge = load_module(BRIDGE_TOOL_PATH, "intake_session_bridge_external_refs")
    session = ready_session(tmp_path)
    first_path = tmp_path / "a" / "user_idea_intake_session.json"
    second_path = tmp_path / "b" / "user_idea_intake_session.json"

    first_source, _ = bridge.build_intake_session_candidate_source(
        session,
        session_path=first_path,
        output_path=tmp_path / "first_user_idea_intake_source.json",
    )
    second_source, _ = bridge.build_intake_session_candidate_source(
        session,
        session_path=second_path,
        output_path=tmp_path / "second_user_idea_intake_source.json",
    )

    assert first_source is not None
    assert second_source is not None
    assert (
        first_source["source_session"]["source_ref"]
        != second_source["source_session"]["source_ref"]
    )


def test_intake_session_candidate_source_rejects_empty_event_storming_lists(
    tmp_path: Path,
) -> None:
    bridge = load_module(BRIDGE_TOOL_PATH, "intake_session_bridge_empty_events")
    session = ready_session(tmp_path)
    session["candidate_source_input"]["event_storming_hints"]["actors"] = []

    source, report = bridge.build_intake_session_candidate_source(
        session,
        session_path=tmp_path / "user_idea_intake_session.json",
        output_path=tmp_path / "user_idea_intake_source.json",
    )

    assert source is None
    finding_ids = {finding["finding_id"] for finding in report["findings"]}
    assert "intake_session_candidate_source_actors_missing" in finding_ids


def test_intake_session_candidate_source_blocks_authority_expansion(
    tmp_path: Path,
) -> None:
    bridge = load_module(BRIDGE_TOOL_PATH, "intake_session_bridge_authority")
    session = ready_session(tmp_path)
    session["candidate_source_input"]["may_mutate_candidate_source_artifacts"] = True

    source, report = bridge.build_intake_session_candidate_source(
        session,
        session_path=tmp_path / "user_idea_intake_session.json",
        output_path=tmp_path / "user_idea_intake_source.json",
    )

    assert source is None
    finding_ids = {finding["finding_id"] for finding in report["findings"]}
    assert "intake_session_candidate_source_authority_expanded" in finding_ids


def test_intake_session_candidate_source_blocks_unsafe_privacy_boundary(
    tmp_path: Path,
) -> None:
    bridge = load_module(BRIDGE_TOOL_PATH, "intake_session_bridge_privacy")
    session = ready_session(tmp_path)
    session["privacy_boundary"]["raw_idea_text_published_in_session"] = True

    source, report = bridge.build_intake_session_candidate_source(
        session,
        session_path=tmp_path / "user_idea_intake_session.json",
        output_path=tmp_path / "user_idea_intake_source.json",
    )

    assert source is None
    finding_ids = {finding["finding_id"] for finding in report["findings"]}
    assert "intake_session_candidate_source_privacy_unsafe" in finding_ids


def test_intake_session_candidate_source_blocks_raw_trace_payload(
    tmp_path: Path,
) -> None:
    bridge = load_module(BRIDGE_TOOL_PATH, "intake_session_bridge_raw_trace")
    session = ready_session(tmp_path)
    session["candidate_source_input"]["event_storming_hints"]["actors"][0]["raw_text"] = (
        "SECRET RAW IDEA"
    )

    source, report = bridge.build_intake_session_candidate_source(
        session,
        session_path=tmp_path / "user_idea_intake_session.json",
        output_path=tmp_path / "user_idea_intake_source.json",
    )

    assert source is None
    assert "SECRET RAW IDEA" not in json.dumps(report)
    finding_ids = {finding["finding_id"] for finding in report["findings"]}
    assert "intake_session_candidate_source_raw_trace_field" in finding_ids


def test_intake_session_candidate_source_session_digest_ignores_generated_at(
    tmp_path: Path,
) -> None:
    bridge = load_module(BRIDGE_TOOL_PATH, "intake_session_bridge_stable_digest")
    session = ready_session(tmp_path)
    first_source, _ = bridge.build_intake_session_candidate_source(
        session,
        session_path=tmp_path / "user_idea_intake_session.json",
        output_path=tmp_path / "user_idea_intake_source.json",
    )
    session["generated_at"] = "2099-01-01T00:00:00+00:00"
    second_source, _ = bridge.build_intake_session_candidate_source(
        session,
        session_path=tmp_path / "user_idea_intake_session.json",
        output_path=tmp_path / "user_idea_intake_source.json",
    )

    assert first_source is not None
    assert second_source is not None
    assert (
        first_source["source_session"]["session_digest"]
        == second_source["source_session"]["session_digest"]
    )


def test_intake_session_candidate_source_make_target_uses_custom_outputs(
    tmp_path: Path,
) -> None:
    session_path = tmp_path / "user_idea_intake_session.json"
    source_path = tmp_path / "user_idea_intake_source.json"
    report_path = tmp_path / "intake_session_candidate_source_report.json"
    write_json(session_path, ready_session(tmp_path))

    result = subprocess.run(
        [
            "make",
            "intake-session-candidate-source",
            f"PYTHON={sys.executable}",
            f"INTAKE_SESSION_CANDIDATE_SOURCE_INPUT={session_path}",
            f"INTAKE_SESSION_CANDIDATE_SOURCE_OUTPUT={source_path}",
            f"INTAKE_SESSION_CANDIDATE_SOURCE_REPORT_OUTPUT={report_path}",
            "INTAKE_SESSION_CANDIDATE_SOURCE_STRICT=1",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert load_json(source_path)["artifact_kind"] == "user_idea_intake_source"
    assert load_json(report_path)["summary"]["status"] == "candidate_source_ready"


def test_user_idea_intake_session_embeds_public_safe_candidate_source_input(
    tmp_path: Path,
) -> None:
    session = ready_session(tmp_path)

    embedded = session["candidate_source_input"]
    assert embedded["artifact_kind"] == "intake_session_candidate_source_input"
    assert embedded["contract_ref"] == (
        "specgraph.idea-to-spec.intake-session-candidate-source-input.v0.1"
    )
    assert embedded["workspace"]["candidate_id"] == "support-triage-log"
    assert embedded["intent"]["text"] == ""
    dumped = json.dumps(embedded)
    assert load_json(READY_FIXTURE)["idea"]["text"] not in dumped
    assert "private prompt trace" not in dumped
