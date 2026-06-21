from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "pre_sib_coherence_report.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "pre_sib_coherence"
READY_FIXTURE = FIXTURE_DIR / "candidate_spec_graph_ready.json"
REVIEW_REQUIRED_FIXTURE = FIXTURE_DIR / "candidate_spec_graph_review_required.json"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "pre_sib_coherence_report_under_test",
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


def warning_ids(report: dict[str, object]) -> set[str]:
    warnings = report["warnings"]
    assert isinstance(warnings, list)
    return {warning["finding_id"] for warning in warnings if isinstance(warning, dict)}


def test_pre_sib_coherence_report_builds_ready_report() -> None:
    module = load_module()

    report = module.build_pre_sib_coherence_report(
        load_json(READY_FIXTURE),
        candidate_graph_path=READY_FIXTURE,
    )

    assert report["artifact_kind"] == "pre_sib_coherence_report"
    assert report["proposal_id"] == "0151"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "ready_for_repair_loop"
    assert report["metrics"]["node_count"] == 2
    assert report["metrics"]["edge_count"] == 1
    assert report["metrics"]["orphan_node_count"] == 0
    assert report["metrics"]["acceptance_criteria_coverage_ratio"] == 1.0
    assert report["metrics"]["ontology_coverage_ratio"] == 1.0
    assert report["summary"]["warning_count"] == 1
    assert "pre_sib_unresolved_gaps" in warning_ids(report)


def test_pre_sib_coherence_report_blocks_unready_candidate_graph() -> None:
    module = load_module()

    report = module.build_pre_sib_coherence_report(
        load_json(REVIEW_REQUIRED_FIXTURE),
        candidate_graph_path=REVIEW_REQUIRED_FIXTURE,
    )

    ids = finding_ids(report)
    assert report["readiness"]["ready"] is False
    assert "candidate_graph_not_ready" in ids
    assert "pre_sib_nodes_missing" in ids


def test_pre_sib_coherence_report_detects_orphan_and_ontology_gaps() -> None:
    module = load_module()
    candidate = load_json(READY_FIXTURE)
    candidate["edges"] = []
    nodes = candidate["nodes"]
    assert isinstance(nodes, list)
    nodes[0]["ontology_refs"] = []

    report = module.build_pre_sib_coherence_report(
        candidate,
        candidate_graph_path=READY_FIXTURE,
    )

    ids = finding_ids(report)
    assert report["readiness"]["ready"] is False
    assert "pre_sib_orphan_nodes" in ids
    assert "pre_sib_ontology_coverage_gap" in ids


def test_pre_sib_coherence_report_warns_on_unsupported_strong_claim() -> None:
    module = load_module()
    candidate = load_json(READY_FIXTURE)
    nodes = candidate["nodes"]
    assert isinstance(nodes, list)
    claims = nodes[0]["claims"]
    assert isinstance(claims, list)
    claims[0]["calibration"]["R"] = "R2"
    claims[0]["evidence_refs"] = []

    report = module.build_pre_sib_coherence_report(
        candidate,
        candidate_graph_path=READY_FIXTURE,
    )

    assert report["readiness"]["ready"] is True
    assert "pre_sib_unsupported_strong_claims" in warning_ids(report)


def test_pre_sib_coherence_report_cli_writes_output(tmp_path: Path) -> None:
    output = tmp_path / "pre_sib_coherence_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--candidate-graph",
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
    report = load_json(output)
    assert report["artifact_kind"] == "pre_sib_coherence_report"
    assert report["readiness"]["ready"] is True


def test_pre_sib_coherence_report_strict_cli_exits_nonzero(tmp_path: Path) -> None:
    output = tmp_path / "pre_sib_coherence_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--candidate-graph",
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
    report = load_json(output)
    assert report["readiness"]["ready"] is False
