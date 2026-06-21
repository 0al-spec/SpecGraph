from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "idea_to_spec_promotion_gate.py"
REPAIR_TOOL_PATH = ROOT / "tools" / "candidate_repair_loop.py"
MATERIALIZATION_TOOL_PATH = ROOT / "tools" / "candidate_spec_materialization.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "candidate_repair_loop"
CANDIDATE_REPAIRABLE = FIXTURE_DIR / "candidate_graph_repairable.json"
PRE_SIB_REPAIR_REQUIRED = FIXTURE_DIR / "pre_sib_repair_required.json"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_repair_report(*, context_resolved: bool) -> dict[str, object]:
    module = load_module(REPAIR_TOOL_PATH, "candidate_repair_loop_for_promotion_gate")
    report = module.build_candidate_repair_loop_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        pre_sib_report=load_json(PRE_SIB_REPAIR_REQUIRED),
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        pre_sib_report_path=PRE_SIB_REPAIR_REQUIRED,
    )
    if context_resolved:
        report["repair_actions"] = [
            action
            for action in report["repair_actions"]
            if action.get("status") != "requires_context"
        ]
        report["summary"]["context_required_count"] = 0
        report["readiness"]["context_required_count"] = 0
        report["warnings"] = [
            warning
            for warning in report["warnings"]
            if warning.get("finding_id") != "repair_context_required"
        ]
    return report


def build_materialization_report(
    repair_report: dict[str, object],
    tmp_path: Path,
) -> dict[str, object]:
    module = load_module(
        MATERIALIZATION_TOOL_PATH,
        "candidate_spec_materialization_for_promotion_gate",
    )
    report = module.build_candidate_spec_materialization_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        repair_loop=repair_report,
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        repair_loop_path=tmp_path / "candidate_repair_loop_report.json",
        output_dir=tmp_path / "materialized",
    )
    paths: list[str] = []
    for item in report["materialized_files"]:
        filename = Path(item["path"]).name
        path = f"runs/materialized_candidate_specs/{filename}"
        item["path"] = path
        item["promotion_path"] = path
        paths.append(path)
    report["promotion_request"]["paths"] = paths
    return report


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def warning_ids(report: dict[str, object]) -> set[str]:
    warnings = report["warnings"]
    assert isinstance(warnings, list)
    return {warning["finding_id"] for warning in warnings if isinstance(warning, dict)}


def test_promotion_gate_allows_resolved_repair_preview(tmp_path: Path) -> None:
    module = load_module(TOOL_PATH, "idea_to_spec_promotion_gate_under_test")
    repair = build_repair_report(context_resolved=True)
    materialization = build_materialization_report(repair, tmp_path)

    report = module.build_idea_to_spec_promotion_gate(
        pre_sib=load_json(PRE_SIB_REPAIR_REQUIRED),
        repair_loop=repair,
        materialization=materialization,
        pre_sib_path=PRE_SIB_REPAIR_REQUIRED,
        repair_loop_path=tmp_path / "candidate_repair_loop_report.json",
        materialization_path=tmp_path / "candidate_spec_materialization_report.json",
    )

    assert report["artifact_kind"] == "idea_to_spec_promotion_gate"
    assert report["proposal_id"] == "0154"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "ready_for_platform_promotion_request"
    assert report["summary"]["promotion_path_count"] == 2
    assert report["authority_boundary"]["may_open_pull_request"] is False
    assert "pre_sib_findings_repaired_by_preview" in warning_ids(report)
    assert report["promotion_request"]["paths"] == [
        item["promotion_path"] for item in materialization["materialized_files"]
    ]


def test_promotion_gate_blocks_unresolved_context(tmp_path: Path) -> None:
    module = load_module(TOOL_PATH, "idea_to_spec_promotion_gate_context_test")
    repair = build_repair_report(context_resolved=False)
    materialization = build_materialization_report(repair, tmp_path)

    report = module.build_idea_to_spec_promotion_gate(
        pre_sib=load_json(PRE_SIB_REPAIR_REQUIRED),
        repair_loop=repair,
        materialization=materialization,
    )

    assert report["readiness"]["ready"] is False
    assert "repair_context_required" in finding_ids(report)
    assert report["promotion_request"]["paths"] == []


def test_promotion_gate_blocks_unsafe_promotion_path(tmp_path: Path) -> None:
    module = load_module(TOOL_PATH, "idea_to_spec_promotion_gate_path_test")
    repair = build_repair_report(context_resolved=True)
    materialization = build_materialization_report(repair, tmp_path)
    materialization["promotion_request"]["paths"][0] = "../outside.yaml"

    report = module.build_idea_to_spec_promotion_gate(
        pre_sib=load_json(PRE_SIB_REPAIR_REQUIRED),
        repair_loop=repair,
        materialization=materialization,
    )

    assert report["readiness"]["ready"] is False
    assert "promotion_path_not_allowed" in finding_ids(report)


def test_promotion_gate_cli_strict_exits_nonzero_for_unresolved_context(
    tmp_path: Path,
) -> None:
    repair = build_repair_report(context_resolved=False)
    materialization = build_materialization_report(repair, tmp_path)
    repair_path = tmp_path / "candidate_repair_loop_report.json"
    materialization_path = tmp_path / "candidate_spec_materialization_report.json"
    output = tmp_path / "idea_to_spec_promotion_gate.json"
    repair_path.write_text(json.dumps(repair), encoding="utf-8")
    materialization_path.write_text(json.dumps(materialization), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--pre-sib",
            str(PRE_SIB_REPAIR_REQUIRED),
            "--repair-loop",
            str(repair_path),
            "--materialization",
            str(materialization_path),
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
    assert "repair_context_required" in finding_ids(report)
