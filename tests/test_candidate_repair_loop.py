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
CLEAN_CANDIDATE = (
    ROOT / "tests" / "fixtures" / "pre_sib_coherence" / "candidate_spec_graph_ready.json"
)


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


def test_candidate_repair_loop_downgrades_strength_marker() -> None:
    module = load_module()
    candidate_graph = load_json(CANDIDATE_REPAIRABLE)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    product = next(node for node in nodes if node["id"] == "candidate-spec.calculator-product")
    claim = product["claims"][0]
    claim["type"] = "claim"
    claim["strength"] = "strong"

    report = module.build_candidate_repair_loop_report(
        candidate_graph=candidate_graph,
        pre_sib_report=load_json(PRE_SIB_REPAIR_REQUIRED),
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        pre_sib_report_path=PRE_SIB_REPAIR_REQUIRED,
    )

    preview = report["revised_candidate_graph_preview"]
    preview_product = next(
        node for node in preview["nodes"] if node["id"] == "candidate-spec.calculator-product"
    )
    assert preview_product["claims"][0]["type"] == "hypothesis"
    assert preview_product["claims"][0]["strength"] == "hypothesis"


def test_candidate_repair_loop_projects_metric_delta() -> None:
    report = build_repair_report()
    delta = report["metric_delta_projection"]["delta"]

    assert delta["edge_count"] == 1
    assert delta["acceptance_criteria_count"] == 1
    assert delta["orphan_node_count"] == -2
    assert delta["unsupported_strong_claim_count"] == -1


def test_candidate_repair_loop_allows_clean_noop_repair_loop() -> None:
    module = load_module()
    candidate_graph = load_json(CLEAN_CANDIDATE)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    for node in nodes:
        if isinstance(node, dict):
            node["gaps"] = []
    pre_sib_report = {
        "artifact_kind": "pre_sib_coherence_report",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.pre-sib-coherence-report.v0.1",
        "source_ref": candidate_graph["source_ref"],
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_candidate_graph": {
            "artifact_kind": "candidate_spec_graph",
            "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
            "source_ref": candidate_graph["source_ref"],
        },
        "readiness": {
            "ready": True,
            "review_state": "ready_for_repair_loop",
            "blocked_by": [],
        },
        "findings": [],
        "warnings": [],
    }

    report = module.build_candidate_repair_loop_report(
        candidate_graph=candidate_graph,
        pre_sib_report=pre_sib_report,
        candidate_graph_path=CLEAN_CANDIDATE,
        pre_sib_report_path=ROOT / "runs" / "pre_sib_coherence_report.json",
    )

    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "repair_preview_ready"
    assert report["repair_actions"] == []
    assert report["summary"]["applied_action_count"] == 0
    assert report["summary"]["context_required_count"] == 0
    assert report["summary"]["no_op_repair_loop"] is True
    assert report["revised_candidate_graph_preview"]["repair_preview"]["no_op_repair_loop"] is True


def test_candidate_repair_loop_rejects_mismatched_pre_sib_report() -> None:
    module = load_module()
    pre_sib_report = load_json(PRE_SIB_REPAIR_REQUIRED)
    pre_sib_report["source_candidate_graph"]["source_ref"] = "operator://other-candidate"

    report = module.build_candidate_repair_loop_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        pre_sib_report=pre_sib_report,
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        pre_sib_report_path=PRE_SIB_REPAIR_REQUIRED,
    )

    assert report["readiness"]["ready"] is False
    assert "pre_sib_candidate_graph_mismatch" in finding_ids(report)
    assert report["repair_actions"] == []


def test_candidate_repair_loop_preserves_unhandled_pre_sib_blockers() -> None:
    module = load_module()
    pre_sib_report = load_json(PRE_SIB_REPAIR_REQUIRED)
    pre_sib_report["readiness"]["blocked_by"].append("candidate_graph_not_ready")
    pre_sib_report["findings"].append(
        {
            "finding_id": "candidate_graph_not_ready",
            "severity": "review_required",
            "message": "Candidate graph is not ready for repair.",
            "source": "pre_sib_coherence_report",
            "evidence": {},
        }
    )

    report = module.build_candidate_repair_loop_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        pre_sib_report=pre_sib_report,
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        pre_sib_report_path=PRE_SIB_REPAIR_REQUIRED,
    )

    assert report["readiness"]["ready"] is False
    assert "candidate_graph_not_ready" in finding_ids(report)
    assert report["summary"]["applied_action_count"] == 3


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


def test_candidate_repair_loop_preview_ref_uses_output_path(tmp_path: Path) -> None:
    output = tmp_path / "custom-repair-report.json"

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
    assert (
        report["revised_candidate_graph_preview"]["source_ref"]
        == f"{output.as_posix()}#revised_candidate_graph_preview"
    )


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
