from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "idea_event_storming_intake.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "idea_event_storming_intake"
READY_FIXTURE = FIXTURE_DIR / "idea_ready.json"
REVIEW_REQUIRED_FIXTURE = FIXTURE_DIR / "idea_review_required.json"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "idea_event_storming_intake_under_test",
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


def test_idea_event_storming_intake_builds_ready_artifact() -> None:
    module = load_module()

    intake = module.build_idea_event_storming_intake(
        load_json(READY_FIXTURE),
        source_path=READY_FIXTURE,
    )

    assert intake["artifact_kind"] == "idea_event_storming_intake"
    assert intake["proposal_id"] == "0149"
    assert intake["canonical_mutations_allowed"] is False
    assert intake["tracked_artifacts_written"] is False
    assert intake["candidate_graph_readiness"]["ready"] is True
    assert intake["candidate_graph_readiness"]["review_state"] == "ready_for_candidate_graph"
    assert intake["summary"]["actor_count"] == 1
    assert intake["summary"]["domain_event_count"] == 3
    assert intake["summary"]["command_count"] == 2
    assert intake["summary"]["constraint_count"] == 1
    assert intake["summary"]["vocabulary_question_count"] == 1
    assert intake["privacy_boundary"]["raw_intent_text_published"] is False
    assert intake["root_intent"]["raw_text_published"] is False
    assert intake["root_intent"]["summary"].startswith("Build a calculator app")
    assert intake["findings"] == []


def test_idea_event_storming_intake_requires_frame_and_core_categories() -> None:
    module = load_module()

    intake = module.build_idea_event_storming_intake(
        load_json(REVIEW_REQUIRED_FIXTURE),
        source_path=REVIEW_REQUIRED_FIXTURE,
    )

    ids = finding_ids(intake)
    assert intake["candidate_graph_readiness"]["ready"] is False
    assert intake["candidate_graph_readiness"]["review_state"] == "context_completion_required"
    assert "active_frame_incomplete" in ids
    assert "event_storming_category_missing" in ids
    assert intake["summary"]["finding_count"] >= 5
    assert intake["summary"]["warning_count"] == 1
    assert intake["context_completion_questions"]


def test_idea_event_storming_intake_rejects_unknown_relationship_refs() -> None:
    module = load_module()
    seed = load_json(READY_FIXTURE)
    event_storming = seed["event_storming"]
    assert isinstance(event_storming, dict)
    commands = event_storming["commands"]
    assert isinstance(commands, list)
    commands[0]["produces_event_refs"] = ["event.missing"]

    intake = module.build_idea_event_storming_intake(seed, source_path=READY_FIXTURE)

    ids = finding_ids(intake)
    assert intake["candidate_graph_readiness"]["ready"] is False
    assert "event_storming_unknown_ref" in ids
    assert intake["findings"][0]["evidence"]["unknown_refs"] == ["event.missing"]


def test_idea_event_storming_intake_filters_raw_entry_trace_fields() -> None:
    module = load_module()
    seed = load_json(READY_FIXTURE)
    event_storming = seed["event_storming"]
    assert isinstance(event_storming, dict)
    actors = event_storming["actors"]
    assert isinstance(actors, list)
    actors[0]["raw_prompt"] = "secret prompt"
    actors[0]["raw_model_output"] = "secret model output"
    actors[0]["raw_intent_text"] = "secret intent"

    intake = module.build_idea_event_storming_intake(seed, source_path=READY_FIXTURE)

    actor = intake["event_storming"]["actors"][0]
    assert "raw_prompt" not in actor
    assert "raw_model_output" not in actor
    assert "raw_intent_text" not in actor
    assert "secret prompt" not in json.dumps(intake)
    assert intake["privacy_boundary"]["raw_prompt_published"] is False
    assert intake["privacy_boundary"]["raw_model_output_published"] is False


def test_idea_event_storming_intake_rejects_duplicate_entry_ids() -> None:
    module = load_module()
    seed = load_json(READY_FIXTURE)
    event_storming = seed["event_storming"]
    assert isinstance(event_storming, dict)
    actors = event_storming["actors"]
    assert isinstance(actors, list)
    actors.append({"id": "actor.user", "name": "Duplicate Calculator User"})

    intake = module.build_idea_event_storming_intake(seed, source_path=READY_FIXTURE)

    ids = finding_ids(intake)
    assert intake["candidate_graph_readiness"]["ready"] is False
    assert "event_storming_duplicate_id" in ids


def test_idea_event_storming_intake_validates_seed_contract_metadata() -> None:
    module = load_module()
    seed = load_json(READY_FIXTURE)
    seed["artifact_kind"] = "candidate_spec_graph"
    seed.pop("contract_ref", None)

    intake = module.build_idea_event_storming_intake(seed, source_path=READY_FIXTURE)

    ids = finding_ids(intake)
    assert intake["candidate_graph_readiness"]["ready"] is False
    assert "idea_event_storming_seed_contract_invalid" in ids


def test_idea_event_storming_intake_rejects_malformed_relationship_lists() -> None:
    module = load_module()
    seed = load_json(READY_FIXTURE)
    event_storming = seed["event_storming"]
    assert isinstance(event_storming, dict)
    commands = event_storming["commands"]
    assert isinstance(commands, list)
    commands[0]["actor_refs"] = "actor.user"

    intake = module.build_idea_event_storming_intake(seed, source_path=READY_FIXTURE)

    ids = finding_ids(intake)
    assert intake["candidate_graph_readiness"]["ready"] is False
    assert "event_storming_list_field_malformed" in ids
    assert intake["findings"][0]["evidence"]["field"] == "actor_refs"


def test_idea_event_storming_intake_normalizes_string_entries_and_aliases() -> None:
    module = load_module()
    seed = load_json(READY_FIXTURE)
    seed["event_storming"] = {
        "actors": ["Admin User"],
        "events": ["Workspace Created"],
        "commands": [
            {
                "name": "Create Workspace",
                "actor_refs": ["actors.admin-user"],
                "produces_event_refs": ["domain_events.workspace-created"],
            }
        ],
        "constraints": ["No canonical write during intake"],
    }

    intake = module.build_idea_event_storming_intake(seed, source_path=READY_FIXTURE)

    assert intake["candidate_graph_readiness"]["ready"] is True
    assert intake["event_storming"]["actors"][0]["id"] == "actors.admin-user"
    domain_event_id = intake["event_storming"]["domain_events"][0]["id"]
    assert domain_event_id == "domain_events.workspace-created"


def test_idea_event_storming_intake_preserves_singleton_optional_context() -> None:
    module = load_module()
    seed = load_json(READY_FIXTURE)
    event_storming = seed["event_storming"]
    assert isinstance(event_storming, dict)
    event_storming["policies"] = {
        "id": "policy.review_before_write",
        "name": "Review Before Write",
    }
    event_storming["risks"] = {
        "id": "risk.term_drift",
        "statement": "Terms may drift before the ontology frame is confirmed.",
    }
    event_storming["assumptions"] = [
        "The user accepts a review-only candidate graph before canonical write."
    ]

    intake = module.build_idea_event_storming_intake(seed, source_path=READY_FIXTURE)

    assert intake["candidate_graph_readiness"]["ready"] is True
    assert intake["event_storming"]["policies"][0]["id"] == "policy.review_before_write"
    assert intake["event_storming"]["risks"][0]["id"] == "risk.term_drift"
    assert intake["event_storming"]["assumptions"][0]["id"].startswith("assumptions.")
    assert intake["summary"]["risk_count"] == 1
    assert intake["summary"]["assumption_count"] == 1


def test_idea_event_storming_intake_cli_writes_output(tmp_path: Path) -> None:
    output = tmp_path / "idea_event_storming_intake.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(READY_FIXTURE),
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
    intake = load_json(output)
    assert intake["artifact_kind"] == "idea_event_storming_intake"
    assert intake["candidate_graph_readiness"]["ready"] is True


def test_idea_event_storming_intake_strict_cli_exits_nonzero(tmp_path: Path) -> None:
    output = tmp_path / "idea_event_storming_intake.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(REVIEW_REQUIRED_FIXTURE),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    intake = load_json(output)
    assert intake["candidate_graph_readiness"]["ready"] is False
