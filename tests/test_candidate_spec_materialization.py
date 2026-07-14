from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "candidate_spec_materialization.py"
REPAIR_TOOL_PATH = ROOT / "tools" / "candidate_repair_loop.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "candidate_repair_loop"
CANDIDATE_REPAIRABLE = FIXTURE_DIR / "candidate_graph_repairable.json"
PRE_SIB_REPAIR_REQUIRED = FIXTURE_DIR / "pre_sib_repair_required.json"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "candidate_spec_materialization_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_repair_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "candidate_repair_loop_for_materialization_test",
        REPAIR_TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_repair_report() -> dict[str, object]:
    module = load_repair_module()
    return module.build_candidate_repair_loop_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        pre_sib_report=load_json(PRE_SIB_REPAIR_REQUIRED),
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        pre_sib_report_path=PRE_SIB_REPAIR_REQUIRED,
    )


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def test_candidate_spec_materialization_writes_review_yaml(tmp_path: Path) -> None:
    module = load_module()
    output_dir = tmp_path / "materialized"

    report = module.build_candidate_spec_materialization_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        repair_loop=build_repair_report(),
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        repair_loop_path=tmp_path / "candidate_repair_loop_report.json",
        output_dir=output_dir,
    )

    assert report["artifact_kind"] == "candidate_spec_materialization_report"
    assert report["proposal_id"] == "0153"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "materialized_candidate_review_ready"
    assert report["materialization_source"] == "repair_loop_preview"
    assert report["summary"]["materialized_file_count"] == 2
    assert report["authority_boundary"]["may_create_branch_or_commit"] is False
    assert report["promotion_request"]["paths"] == [
        item["promotion_path"] for item in report["materialized_files"]
    ]

    first_file = report["materialized_files"][0]
    assert isinstance(first_file, dict)
    materialized_path = ROOT / first_file["path"]
    if not materialized_path.exists():
        materialized_path = output_dir / Path(first_file["path"]).name
    parsed = yaml.safe_load(materialized_path.read_text(encoding="utf-8"))
    assert parsed["id"].startswith("CANDIDATE-SOURCE-")
    assert report["candidate_scope"]["derivation"] == "source_ref_digest"
    assert parsed["kind"] == "spec"
    assert parsed["gate_state"] == "review_pending"
    assert parsed["specification"]["materialization_mode"] == "candidate_review_preview"
    assert parsed["specification"]["requirements"]


def test_candidate_spec_materialization_skips_review_only_workflow_edges(
    tmp_path: Path,
) -> None:
    module = load_module()
    candidate_graph = {
        "artifact_kind": "candidate_spec_graph",
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_ref": "product://workflow-review/root-intent",
        "nodes": [
            {
                "id": "candidate-spec.product-boundary",
                "display_alias": "Product boundary",
                "title": "Product Boundary",
                "kind": "product_spec_boundary",
                "description": "Boundary",
                "requirements": [{"id": "req.boundary", "statement": "Boundary"}],
                "acceptance_criteria": [],
            },
            {
                "id": "candidate-spec.record-decision",
                "display_alias": "Record a decision",
                "title": "Record Decision",
                "kind": "behavior_requirement",
                "description": "Record decision",
                "requirements": [{"id": "req.record", "statement": "Record decision"}],
                "acceptance_criteria": [],
            },
        ],
        "edges": [
            {
                "id": "edge.product-boundary.record-decision",
                "from": "candidate-spec.product-boundary",
                "to": "candidate-spec.record-decision",
                "relation": "decomposes_to",
            },
            {
                "id": "edge.command.record-decision.decision-recorded",
                "from": "candidate-spec.record-decision",
                "to": "candidate-spec.product-boundary",
                "relation": "command_emits_event",
                "review_only": True,
                "materialization_dependency": False,
            },
        ],
    }
    output_dir = tmp_path / "materialized"

    report = module.build_candidate_spec_materialization_report(
        candidate_graph=candidate_graph,
        output_dir=output_dir,
    )

    assert report["readiness"]["ready"] is True
    paths = {
        item["candidate_node_id"]: output_dir / Path(item["path"]).name
        for item in report["materialized_files"]
    }
    boundary = yaml.safe_load(paths["candidate-spec.product-boundary"].read_text(encoding="utf-8"))
    command = yaml.safe_load(paths["candidate-spec.record-decision"].read_text(encoding="utf-8"))

    assert boundary["depends_on"] == [command["id"]]
    assert command["depends_on"] == []
    assert boundary["title"] == "Product boundary"
    assert boundary["specification"]["candidate_display_alias"] == "Product boundary"
    assert boundary["specification"]["candidate_source_title"] == "Product Boundary"
    assert report["materialized_files"][0]["display_alias"] == "Product boundary"


def test_candidate_spec_materialization_namespaces_shared_node_ids_by_candidate(
    tmp_path: Path,
) -> None:
    module = load_module()
    base_graph = load_json(CANDIDATE_REPAIRABLE)
    base_graph["source_ref"] = "product://first-product/root-intent"
    other_graph = load_json(CANDIDATE_REPAIRABLE)
    other_graph["source_ref"] = "product://second-product/root-intent"

    first_report = module.build_candidate_spec_materialization_report(
        candidate_graph=base_graph,
        output_dir=tmp_path / "first",
    )
    second_report = module.build_candidate_spec_materialization_report(
        candidate_graph=other_graph,
        output_dir=tmp_path / "second",
    )

    first_paths = {Path(path).name for path in first_report["promotion_request"]["paths"]}
    second_paths = {Path(path).name for path in second_report["promotion_request"]["paths"]}
    first_ids = {item["materialized_id"] for item in first_report["materialized_files"]}
    second_ids = {item["materialized_id"] for item in second_report["materialized_files"]}

    assert first_report["candidate_scope"]["namespace"] == "first-product"
    assert second_report["candidate_scope"]["namespace"] == "second-product"
    assert first_paths.isdisjoint(second_paths)
    assert first_ids.isdisjoint(second_ids)
    assert all(identifier.startswith("CANDIDATE-FIRST-PRODUCT-") for identifier in first_ids)
    assert all(identifier.startswith("CANDIDATE-SECOND-PRODUCT-") for identifier in second_ids)


def test_candidate_spec_materialization_rejects_invalid_product_scope(
    tmp_path: Path,
) -> None:
    module = load_module()
    candidate_graph = load_json(CANDIDATE_REPAIRABLE)
    candidate_graph["source_ref"] = "product://Wrong_Candidate/root-intent"

    report = module.build_candidate_spec_materialization_report(
        candidate_graph=candidate_graph,
        output_dir=tmp_path / "materialized",
    )

    assert report["readiness"]["ready"] is False
    assert "candidate_materialization_product_scope_invalid" in finding_ids(report)
    assert report["candidate_scope"] is None
    assert report["materialized_files"] == []


def test_candidate_spec_materialization_rejects_authority_expansion(
    tmp_path: Path,
) -> None:
    module = load_module()
    candidate_graph = load_json(CANDIDATE_REPAIRABLE)
    candidate_graph["tracked_artifacts_written"] = True

    report = module.build_candidate_spec_materialization_report(
        candidate_graph=candidate_graph,
        output_dir=tmp_path / "materialized",
    )

    assert report["readiness"]["ready"] is False
    assert "candidate_graph_authority_expanded" in finding_ids(report)
    assert report["materialized_files"] == []
    assert report["local_files_written"] == []


def test_candidate_spec_materialization_rejects_unsafe_display_alias(
    tmp_path: Path,
) -> None:
    module = load_module()
    candidate_graph = {
        "artifact_kind": "candidate_spec_graph",
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "nodes": [
            {
                "id": "candidate-spec.private-node",
                "display_alias": "/Users/operator/private candidate",
                "title": "Private node",
                "kind": "product_spec_boundary",
                "description": "Boundary",
                "requirements": [{"id": "req.private", "statement": "Boundary"}],
                "acceptance_criteria": [],
            }
        ],
        "edges": [],
    }

    report = module.build_candidate_spec_materialization_report(
        candidate_graph=candidate_graph,
        output_dir=tmp_path / "materialized",
    )

    assert report["readiness"]["ready"] is False
    assert "candidate_node_display_alias_invalid" in finding_ids(report)
    assert report["materialized_files"] == []


def test_candidate_spec_materialization_rejects_unbounded_display_alias(
    tmp_path: Path,
) -> None:
    module = load_module()
    candidate_graph = {
        "artifact_kind": "candidate_spec_graph",
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "nodes": [
            {
                "id": "candidate-spec.long-alias",
                "display_alias": "A" * 65,
                "title": "Long alias node",
                "kind": "product_spec_boundary",
                "description": "Boundary",
                "requirements": [{"id": "req.long", "statement": "Boundary"}],
                "acceptance_criteria": [],
            }
        ],
        "edges": [],
    }

    report = module.build_candidate_spec_materialization_report(
        candidate_graph=candidate_graph,
        output_dir=tmp_path / "materialized",
    )

    assert report["readiness"]["ready"] is False
    assert "candidate_node_display_alias_invalid" in finding_ids(report)
    assert report["materialized_files"] == []


def test_candidate_spec_materialization_cli_writes_report_and_files(
    tmp_path: Path,
) -> None:
    repair_report = tmp_path / "candidate_repair_loop_report.json"
    repair_report.write_text(json.dumps(build_repair_report()), encoding="utf-8")
    output_dir = tmp_path / "materialized"
    output = tmp_path / "candidate_spec_materialization_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--candidate-graph",
            str(CANDIDATE_REPAIRABLE),
            "--repair-loop",
            str(repair_report),
            "--output-dir",
            str(output_dir),
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
    assert report["readiness"]["ready"] is True
    assert len(report["materialized_files"]) == 2
    assert len(list(output_dir.glob("*.yaml"))) == 2


def test_candidate_spec_materialization_strict_cli_exits_nonzero(
    tmp_path: Path,
) -> None:
    candidate_graph = load_json(CANDIDATE_REPAIRABLE)
    candidate_graph["artifact_kind"] = "wrong"
    candidate_path = tmp_path / "candidate_graph.json"
    candidate_path.write_text(json.dumps(candidate_graph), encoding="utf-8")
    output = tmp_path / "candidate_spec_materialization_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--candidate-graph",
            str(candidate_path),
            "--output-dir",
            str(tmp_path / "materialized"),
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
    assert "candidate_graph_wrong_artifact_kind" in finding_ids(report)
