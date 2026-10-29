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


def test_report_uses_one_ir_read_and_marks_unverified(monkeypatch) -> None:
    module = load_validation_module()
    calls = []
    original = module.load_json

    def read_once(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(module, "load_json", read_once)
    report = module.build_validation_report()
    assert len(calls) == 1
    assert report["ontology_verification"] == {"status": "not_verified"}


def test_checked_snapshot_is_consumed_without_reopening_ir(monkeypatch) -> None:
    module = load_validation_module()
    from ontology_snapshot import OntologySnapshot

    raw = module.DEFAULT_IR_PATH.read_bytes()
    snapshot = OntologySnapshot(
        b"source", raw, "sourcehash", "sha256:source", "irhash", "compilerhash"
    )

    def fail_read(_path):
        raise AssertionError("consumer reopened the IR")

    monkeypatch.setattr(module, "load_json", fail_read)
    report = module.build_validation_report(snapshot=snapshot)
    assert report["ontology_verification"] == {
        "status": "compiler_checked",
        "source_sha256": "sourcehash",
        "ir_sha256": "irhash",
        "compiler_sha256": "compilerhash",
        "compiler_provenance": "not_verified",
    }
    assert report["summary"]["spec_count"] > 0


def test_checked_cli_fails_if_compiler_missing(tmp_path) -> None:
    import subprocess

    for tool in ("spec_ontology_binding_index.py", "spec_ontology_validation_report.py"):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / tool), "--ontologyc", str(tmp_path / "missing")],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 2
        assert "ontologyc" in result.stderr
        assert not result.stdout
