from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "user_idea_intake_source.py"
INTAKE_TOOL_PATH = ROOT / "tools" / "idea_event_storming_intake.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "user_idea_intake"
READY_FIXTURE = FIXTURE_DIR / "source_ready.json"
REVIEW_REQUIRED_FIXTURE = FIXTURE_DIR / "source_review_required.json"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_user_idea_intake_source_builds_generic_event_storming_seed() -> None:
    module = load_module(TOOL_PATH, "user_idea_intake_source_ready")

    seed = module.build_user_idea_event_storming_seed(
        load_json(READY_FIXTURE),
        source_path=READY_FIXTURE,
    )

    assert seed["artifact_kind"] == "idea_event_storming_seed"
    assert seed["contract_ref"] == "specgraph.idea-to-spec.event-storming-seed.v0.1"
    assert seed["source_ref"] == "product://support-triage-log/root-intent"
    assert seed["active_frame"]["project"] == "SupportTriageLog"
    assert seed["active_frame"]["domain_refs"] == ["domain.support_triage_log"]
    assert "context.support_triage_log" in seed["active_frame"]["context_refs"]
    assert seed["event_storming"]["actors"][0]["id"] == "actor.support-agent"
    assert "raw_prompt" not in seed["event_storming"]["actors"][0]
    assert "private prompt trace" not in json.dumps(seed)
    source_intake = seed["source_intake"]
    assert source_intake["proposal_id"] == "0158"
    assert source_intake["summary"]["status"] == "ready_for_event_storming_intake"
    assert source_intake["authority_boundary"]["may_execute_prompt_agent"] is False


def test_user_idea_intake_source_preserves_broader_domain_and_adds_candidate_domain() -> None:
    module = load_module(TOOL_PATH, "user_idea_intake_source_candidate_domain")
    source = load_json(READY_FIXTURE)
    source["workspace"]["candidate_id"] = "apartment-renovation-assistant"
    source["workspace"]["display_name"] = "Apartment Renovation Assistant"
    source["active_frame_hints"] = {
        "project": "ApartmentRenovationAssistant",
        "domain_refs": ["domain.home_renovation_project_management"],
    }

    seed = module.build_user_idea_event_storming_seed(source, source_path=READY_FIXTURE)

    assert seed["active_frame"]["domain_refs"] == [
        "domain.home_renovation_project_management",
        "domain.apartment_renovation_assistant",
    ]


def test_user_idea_intake_source_feeds_existing_intake_contract() -> None:
    source_module = load_module(TOOL_PATH, "user_idea_intake_source_to_intake")
    intake_module = load_module(INTAKE_TOOL_PATH, "idea_event_storming_from_user_idea")
    seed = source_module.build_user_idea_event_storming_seed(
        load_json(READY_FIXTURE),
        source_path=READY_FIXTURE,
    )

    intake = intake_module.build_idea_event_storming_intake(
        seed,
        source_path=READY_FIXTURE,
    )

    assert intake["artifact_kind"] == "idea_event_storming_intake"
    assert intake["candidate_graph_readiness"]["ready"] is True
    assert intake["summary"]["actor_count"] == 2
    assert intake["summary"]["domain_event_count"] == 2
    assert intake["summary"]["command_count"] == 2
    assert intake["root_intent"]["raw_text_published"] is False


def test_user_idea_intake_source_review_required_flows_to_context_questions() -> None:
    source_module = load_module(TOOL_PATH, "user_idea_intake_source_review")
    intake_module = load_module(INTAKE_TOOL_PATH, "idea_event_storming_review")
    seed = source_module.build_user_idea_event_storming_seed(
        load_json(REVIEW_REQUIRED_FIXTURE),
        source_path=REVIEW_REQUIRED_FIXTURE,
    )

    intake = intake_module.build_idea_event_storming_intake(
        seed,
        source_path=REVIEW_REQUIRED_FIXTURE,
    )

    assert intake["candidate_graph_readiness"]["ready"] is False
    assert intake["candidate_graph_readiness"]["review_state"] == "context_completion_required"
    assert intake["context_completion_questions"]
    assert {finding["finding_id"] for finding in intake["findings"]} == {
        "event_storming_category_missing"
    }
    assert intake["summary"]["constraint_count"] == 1


def test_user_idea_intake_source_strict_cli_rejects_invalid_source(
    tmp_path: Path,
) -> None:
    source = load_json(READY_FIXTURE)
    source["contract_ref"] = "wrong"
    source_path = tmp_path / "source.json"
    output = tmp_path / "idea_event_storming_seed.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--input",
            str(source_path),
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
    seed = load_json(output)
    findings = seed["source_intake"]["findings"]
    assert findings[0]["finding_id"] == "user_idea_source_contract_invalid"


def test_user_idea_intake_source_findings_block_downstream_intake() -> None:
    source_module = load_module(TOOL_PATH, "user_idea_intake_source_invalid_downstream")
    intake_module = load_module(INTAKE_TOOL_PATH, "idea_event_storming_invalid_source")
    source = load_json(READY_FIXTURE)
    source["contract_ref"] = "wrong"
    seed = source_module.build_user_idea_event_storming_seed(
        source,
        source_path=READY_FIXTURE,
    )

    intake = intake_module.build_idea_event_storming_intake(
        seed,
        source_path=READY_FIXTURE,
    )

    assert intake["candidate_graph_readiness"]["ready"] is False
    assert intake["candidate_graph_readiness"]["review_state"] == "context_completion_required"
    assert "source_intake_review_required" in {
        finding["finding_id"] for finding in intake["findings"]
    }


def test_user_idea_intake_source_cli_writes_seed(tmp_path: Path) -> None:
    output = tmp_path / "idea_event_storming_seed.json"

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
    seed = load_json(output)
    assert seed["artifact_kind"] == "idea_event_storming_seed"
    assert seed["source_intake"]["workspace"]["candidate_id"] == "support-triage-log"
