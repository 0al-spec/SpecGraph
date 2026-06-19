from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "specauthor_ontology_write_gate.py"
POLICY_PATH = ROOT / "tools" / "ontology_term_binding_policy.json"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "specauthor_ontology_write_gate"
READY_FIXTURE = FIXTURE_DIR / "generated_spec_ready.json"
REVIEW_REQUIRED_FIXTURE = FIXTURE_DIR / "generated_spec_review_required.json"


def load_gate_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "specauthor_ontology_write_gate_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def load_fixture(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def test_specauthor_write_gate_allows_framed_bound_and_calibrated_artifact() -> None:
    module = load_gate_module()
    report = module.build_specauthor_ontology_write_gate_report(
        load_fixture(READY_FIXTURE),
        term_policy=load_policy(),
        artifact_path=READY_FIXTURE,
    )

    assert report["artifact_kind"] == "specauthor_ontology_write_gate_report"
    assert report["proposal_id"] == "0136"
    assert report["ok"] is True
    assert report["review_state"] == "clear"
    assert report["write_decision"] == "allow_graph_write"
    assert report["would_reject_in_hard_gate"] is False
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["findings"] == []


def test_specauthor_write_gate_rejects_missing_frame_binding_and_low_r_decision() -> None:
    module = load_gate_module()
    report = module.build_specauthor_ontology_write_gate_report(
        load_fixture(REVIEW_REQUIRED_FIXTURE),
        term_policy=load_policy(),
        artifact_path=REVIEW_REQUIRED_FIXTURE,
    )

    assert report["ok"] is False
    assert report["review_state"] == "review_required"
    assert report["write_decision"] == "reject_graph_write"
    ids = finding_ids(report)
    assert "active_frame_incomplete" in ids
    assert "new_term_without_gap" in ids
    assert "low_reliability_claim_marked_decision" in ids


def test_specauthor_write_gate_blocks_context_completion_as_final_spec() -> None:
    module = load_gate_module()
    artifact = load_fixture(READY_FIXTURE)
    artifact["context_completion_request"] = {
        "kind": "ontology",
        "proposed_name": "MissingConcept",
        "status": "requires_human_confirmation",
        "canonical_mutations_allowed": False,
    }

    report = module.build_specauthor_ontology_write_gate_report(
        artifact,
        term_policy=load_policy(),
        artifact_path=READY_FIXTURE,
    )

    assert report["ok"] is False
    assert report["review_state"] == "context_completion_required"
    assert "context_completion_required" in finding_ids(report)


def test_specauthor_write_gate_strict_cli_exits_nonzero(tmp_path: Path) -> None:
    output_path = tmp_path / "specauthor-gate-report.json"

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
    assert report["would_reject_in_hard_gate"] is True
    assert "low_reliability_claim_marked_decision" in finding_ids(report)
