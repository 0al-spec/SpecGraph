from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "candidate_repair_loop.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "candidate_repair_loop"
CANDIDATE_REPAIRABLE = FIXTURE_DIR / "candidate_graph_repairable.json"
PRE_SIB_REPAIR_REQUIRED = FIXTURE_DIR / "pre_sib_repair_required.json"
PRE_SIB_WRONG_CONTRACT = FIXTURE_DIR / "pre_sib_wrong_contract.json"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "candidate_repair_loop_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def action_kinds(report: dict[str, object]) -> set[str]:
    actions = report["repair_actions"]
    assert isinstance(actions, list)
    return {action["kind"] for action in actions if isinstance(action, dict)}


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def build_repair_report() -> dict[str, object]:
    module = load_module()
    return module.build_candidate_repair_loop_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        pre_sib_report=load_json(PRE_SIB_REPAIR_REQUIRED),
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        pre_sib_report_path=PRE_SIB_REPAIR_REQUIRED,
    )


def test_candidate_repair_loop_builds_repair_preview() -> None:
    report = build_repair_report()

    assert report["artifact_kind"] == "candidate_repair_loop_report"
    assert report["proposal_id"] == "0152"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "repair_preview_ready"
    assert report["summary"]["applied_action_count"] == 3
    assert report["summary"]["context_required_count"] == 2
    assert action_kinds(report) == {
        "add_candidate_edge",
        "add_acceptance_criterion",
        "add_ontology_gap",
        "downgrade_claim",
        "request_context_for_gaps",
    }


def test_candidate_repair_loop_preview_applies_safe_repairs() -> None:
    report = build_repair_report()
    preview = report["revised_candidate_graph_preview"]
    assert isinstance(preview, dict)
    assert preview["canonical_mutations_allowed"] is False
    assert preview["tracked_artifacts_written"] is False
    assert preview["repair_preview"]["applied_action_count"] == 3

    edges = preview["edges"]
    assert isinstance(edges, list)
    assert len(edges) == 1
    assert edges[0]["relation"] == "decomposes_to"

    nodes = preview["nodes"]
    assert isinstance(nodes, list)
    numeric = next(node for node in nodes if node["id"] == "candidate-spec.numeric-input")
    assert numeric["acceptance_criteria"][0]["repair_generated"] is True
    assert numeric["requirements"][0]["acceptance_criteria_refs"] == ["ac.repair.req-input-digits"]

    product = next(node for node in nodes if node["id"] == "candidate-spec.calculator-product")
    assert product["claims"][0]["type"] == "hypothesis"
    assert product["claims"][0]["repair_generated_type_change"] is True


def test_candidate_repair_loop_projects_metric_delta() -> None:
    report = build_repair_report()
    delta = report["metric_delta_projection"]["delta"]

    assert delta["edge_count"] == 1
    assert delta["acceptance_criteria_count"] == 1
    assert delta["orphan_node_count"] == -2


def test_candidate_repair_loop_rejects_wrong_pre_sib_contract() -> None:
    module = load_module()

    report = module.build_candidate_repair_loop_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        pre_sib_report=load_json(PRE_SIB_WRONG_CONTRACT),
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        pre_sib_report_path=PRE_SIB_WRONG_CONTRACT,
    )

    assert report["readiness"]["ready"] is False
    assert "pre_sib_contract_ref_unsupported" in finding_ids(report)
    assert report["repair_actions"] == []


def test_candidate_repair_loop_cli_writes_output(tmp_path: Path) -> None:
    output = tmp_path / "candidate_repair_loop_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--candidate-graph",
            str(CANDIDATE_REPAIRABLE),
            "--pre-sib-report",
            str(PRE_SIB_REPAIR_REQUIRED),
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
    assert report["artifact_kind"] == "candidate_repair_loop_report"
    assert report["readiness"]["ready"] is True


def test_candidate_repair_loop_strict_cli_exits_nonzero(tmp_path: Path) -> None:
    output = tmp_path / "candidate_repair_loop_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--candidate-graph",
            str(CANDIDATE_REPAIRABLE),
            "--pre-sib-report",
            str(PRE_SIB_WRONG_CONTRACT),
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
