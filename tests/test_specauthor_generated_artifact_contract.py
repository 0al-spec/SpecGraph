from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "specauthor_generated_artifact_contract.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "specauthor_generated_artifact_contract"
READY_FIXTURE = FIXTURE_DIR / "generated_spec_ready.json"
REVIEW_REQUIRED_FIXTURE = FIXTURE_DIR / "generated_spec_review_required.json"


def load_contract_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "specauthor_generated_artifact_contract_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_fixture(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def test_specauthor_generated_artifact_contract_allows_review_bound_artifact() -> None:
    module = load_contract_module()

    report = module.build_specauthor_generated_artifact_contract_report(
        load_fixture(READY_FIXTURE),
        artifact_path=READY_FIXTURE,
    )

    assert report["artifact_kind"] == "specauthor_generated_artifact_contract_report"
    assert report["proposal_id"] == "0137"
    assert report["ok"] is True
    assert report["review_state"] == "clear"
    assert report["write_gate_ready"] is True
    assert report["would_reject_in_contract"] is False
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["findings"] == []
    assert report["contract"]["downstream_write_gate"] == "specauthor-ontology-write-gate"
    assert report["summary"]["claim_count"] == 1
    assert report["summary"]["term_binding_count"] == 1


def test_specauthor_generated_artifact_contract_rejects_authority_expansion() -> None:
    module = load_contract_module()

    report = module.build_specauthor_generated_artifact_contract_report(
        load_fixture(REVIEW_REQUIRED_FIXTURE),
        artifact_path=REVIEW_REQUIRED_FIXTURE,
    )

    ids = finding_ids(report)
    assert report["ok"] is False
    assert report["review_state"] == "review_required"
    assert report["write_gate_ready"] is False
    assert "authority_expansion" in ids
    assert "materialization_intent_invalid" in ids
    assert "target_artifact_incomplete" in ids


def test_specauthor_generated_artifact_contract_rejects_nested_authority_expansion() -> None:
    module = load_contract_module()
    artifact = load_fixture(READY_FIXTURE)
    artifact["authority_boundary"] = {
        "may_execute_prompt_agent": True,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mutate_canonical_specs": True,
        "may_mark_candidate_accepted": False,
    }

    report = module.build_specauthor_generated_artifact_contract_report(
        artifact,
        artifact_path=READY_FIXTURE,
    )

    assert report["ok"] is False
    assert report["write_gate_ready"] is False
    assert "authority_expansion" in finding_ids(report)


def test_specauthor_generated_artifact_contract_rejects_target_artifact_conflict() -> None:
    module = load_contract_module()
    artifact = load_fixture(READY_FIXTURE)
    artifact["active_frame"]["target_artifact"] = "ADR"
    artifact["target_artifact"]["kind"] = "Proposal"

    report = module.build_specauthor_generated_artifact_contract_report(
        artifact,
        artifact_path=READY_FIXTURE,
    )

    assert report["ok"] is False
    assert report["write_gate_ready"] is False
    assert "target_artifact_identity_conflict" in finding_ids(report)


def test_specauthor_generated_artifact_contract_rejects_malformed_term_bindings() -> None:
    module = load_contract_module()
    artifact = load_fixture(READY_FIXTURE)
    artifact["term_bindings"] = [
        {
            "generated_term": "Spec",
            "binding_state": "bound_to_accepted_entity",
        },
        "sgcore:Node",
    ]

    report = module.build_specauthor_generated_artifact_contract_report(
        artifact,
        artifact_path=READY_FIXTURE,
    )

    assert report["ok"] is False
    assert report["write_gate_ready"] is False
    assert "term_binding_entries_invalid" in finding_ids(report)


def test_specauthor_generated_artifact_contract_rejects_missing_context_and_draft() -> None:
    module = load_contract_module()
    artifact = load_fixture(READY_FIXTURE)
    artifact["active_frame"]["ontology_refs"] = [""]
    artifact["active_frame"]["domain_refs"] = []
    artifact["draft"] = {"format": "markdown"}

    report = module.build_specauthor_generated_artifact_contract_report(
        artifact,
        artifact_path=READY_FIXTURE,
    )

    ids = finding_ids(report)
    assert report["ok"] is False
    assert "active_frame_incomplete" in ids
    assert "draft_incomplete" in ids


def test_specauthor_generated_artifact_contract_rejects_missing_producer_invocation() -> None:
    module = load_contract_module()
    artifact = load_fixture(READY_FIXTURE)
    artifact["producer"] = {
        "agent_id": "SpecAuthorAgent",
        "prompt_contract_ref": (
            "docs/proposals/0126_specauthor_claim_calibration_prompt_contract.md"
        ),
    }

    report = module.build_specauthor_generated_artifact_contract_report(
        artifact,
        artifact_path=READY_FIXTURE,
    )

    assert report["ok"] is False
    assert "producer_incomplete" in finding_ids(report)


def test_specauthor_generated_artifact_contract_strict_cli_exits_nonzero(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "specauthor-generated-artifact-contract-report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--artifact",
            str(REVIEW_REQUIRED_FIXTURE),
            "--output",
            str(output_path),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["would_reject_in_contract"] is True
    assert "materialization_intent_invalid" in finding_ids(report)
