from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_validation_module() -> object:
    module_path = ROOT / "tools" / "spec_ontology_validation_report.py"
    spec = importlib.util.spec_from_file_location(
        "spec_ontology_validation_report_under_test", module_path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(module_path.parent))
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(module_path.parent))
    return module


def test_spec_ontology_validation_report_is_report_only_for_legacy_specs() -> None:
    module = load_validation_module()

    report = module.build_validation_report()

    assert report["artifact_kind"] == "spec_ontology_validation_report"
    assert report["proposal_id"] == "0135"
    assert report["status"] == "report_only"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["validation_modes"] == {
        "legacy_specs": "report_only",
        "generated_artifacts": "review_required",
        "hard_gate_enabled": False,
    }
    assert report["summary"]["spec_count"] == len(
        sorted((ROOT / "specs" / "nodes").glob("SG-SPEC-*.yaml"))
    )
    assert report["summary"]["finding_count"] > 0
    assert report["summary"]["passed_check_count"] > 0


def test_spec_ontology_validation_report_checks_root_spec_contracts() -> None:
    module = load_validation_module()

    report = module.build_validation_report()
    entries = {entry["spec_id"]: entry for entry in report["entries"]}
    root_entry = entries["SG-SPEC-0001"]

    assert root_entry["validation_status"] == "report_only_findings"
    check_ids = {check["check_id"] for check in root_entry["checks"]}
    assert "required_binding.sgcore_spec" in check_ids
    assert "relation_contract.sgcore:hasAcceptanceCriterion" in check_ids
    assert "relation_contract.sgcore:evidenceSupportsCriterion" in check_ids
    classifications = {finding["classification"] for finding in root_entry["findings"]}
    assert "unknown_legacy_term" in classifications
    assert {finding["severity"] for finding in root_entry["findings"]} == {"warning"}


def test_spec_ontology_validation_report_write_target_is_runs_only() -> None:
    module = load_validation_module()

    assert module.relative_path(module.DEFAULT_OUTPUT_PATH) == (
        "runs/spec_ontology_validation_report.json"
    )
