from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "specauthor_invocation_artifact_contract.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "specauthor_invocation_artifact_contract"
READY_FIXTURE = FIXTURE_DIR / "invocation_ready.json"
REVIEW_REQUIRED_FIXTURE = FIXTURE_DIR / "invocation_review_required.json"


def load_contract_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "specauthor_invocation_artifact_contract_under_test",
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


def test_specauthor_invocation_artifact_contract_allows_ready_invocation() -> None:
    module = load_contract_module()

    report = module.build_specauthor_invocation_artifact_contract_report(
        load_fixture(READY_FIXTURE),
        artifact_path=READY_FIXTURE,
    )

    assert report["artifact_kind"] == "specauthor_invocation_artifact_contract_report"
    assert report["proposal_id"] == "0145"
    assert report["ok"] is True
    assert report["review_state"] == "ready_for_operator_review"
    assert report["invocation_ready"] is True
    assert report["operator_decision_required"] is True
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["findings"] == []
    assert report["active_frame_summary"]["ontology_layer_refs"] == ["meta"]
    assert report["active_frame_summary"]["model_applicability_refs"] == [
        "org.0al.specgraph.core@0.1.0#modelApplicability"
    ]
    assert report["model_applicability_summary"]["assumption_ref_count"] == 2
    assert report["model_applicability_summary"]["invalidation_trigger_ref_count"] == 2


def test_specauthor_invocation_artifact_contract_rejects_incomplete_chain() -> None:
    module = load_contract_module()

    report = module.build_specauthor_invocation_artifact_contract_report(
        load_fixture(REVIEW_REQUIRED_FIXTURE),
        artifact_path=REVIEW_REQUIRED_FIXTURE,
    )

    ids = finding_ids(report)
    assert report["ok"] is False
    assert report["review_state"] == "review_required"
    assert report["invocation_ready"] is False
    assert "authority_expansion" in ids
    assert "invocation_incomplete" in ids
    assert "active_frame_incomplete" in ids
    assert "model_applicability_incomplete" in ids
    assert "model_applicability_domain_mismatch" in ids
    assert "generated_artifact_contract_failed" in ids
    assert "write_gate_not_clear" in ids
    assert "operator_approval_missing_reviewer" in ids
    assert "operator_decision_authority_expansion" in ids


def test_specauthor_invocation_artifact_contract_rejects_missing_applicability() -> None:
    module = load_contract_module()
    artifact = load_fixture(READY_FIXTURE)
    del artifact["model_applicability"]
    artifact["active_frame"]["model_applicability_refs"] = []

    report = module.build_specauthor_invocation_artifact_contract_report(
        artifact,
        artifact_path=READY_FIXTURE,
    )

    ids = finding_ids(report)
    assert report["ok"] is False
    assert "active_frame_incomplete" in ids
    assert "model_applicability_missing" in ids


def test_specauthor_invocation_artifact_contract_strict_cli_exits_nonzero(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "specauthor-invocation-artifact-contract-report.json"

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
    assert report["ok"] is False
    assert "write_gate_not_clear" in finding_ids(report)
