from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_authoring_module() -> object:
    module_path = ROOT / "tools" / "ontology_package_authoring.py"
    spec = importlib.util.spec_from_file_location(
        "ontology_package_authoring_under_test", module_path
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


def test_package_authoring_validate_reports_project_local_package() -> None:
    module = load_authoring_module()

    report = module.build_authoring_surface("validate")

    assert report["artifact_kind"] == "ontology_package_authoring_report"
    assert report["proposal_id"] == "0133"
    assert report["status"] == "passed"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["source_fixture"] == "ontology/packages/specgraph-core/import-fixture.yaml"
    assert report["package"]["authority_class"] == "project_local_draft"
    assert report["package"]["materialized_ir"] == (
        "ontology/packages/specgraph-core/generated/ontology.normalized.json"
    )
    assert report["authority_boundary"]["make_target"] == "ontology-package-validate"
    assert report["authority_boundary"]["writes_canonical_specs"] is False
    assert report["authority_boundary"]["updates_ontology_lockfile"] is False
    assert report["authority_boundary"]["accepts_terms"] is False
    assert report["authority_boundary"]["prompt_agent_execution_allowed"] is False


def test_package_authoring_preview_exposes_refs_and_compatibility() -> None:
    module = load_authoring_module()

    preview = module.build_authoring_surface("preview")

    assert preview["artifact_kind"] == "ontology_package_preview"
    assert preview["proposal_id"] == "0133"
    assert preview["package"]["package_id"] == "org.0al.specgraph.core"
    assert len(preview["resolved_refs"]) == 7
    assert preview["unresolved_refs"] == ["sgcore:ClaimCalibration"]
    assert preview["compatibility_summary"]["status"] == "compatible"
    assert preview["required_specgraph_actions"] == ["updateLockfile"]
    assert preview["compatibility_changes"]["added_classes"] == ["sgcore:ClaimCalibration"]
    assert preview["authority_boundary"]["make_target"] == "ontology-package-preview"
    assert preview["authority_boundary"]["specspace_mutations_allowed"] is False


def test_package_authoring_gap_preview_is_review_only() -> None:
    module = load_authoring_module()

    gaps = module.build_authoring_surface("gaps")

    assert gaps["artifact_kind"] == "ontology_package_gap_preview"
    assert gaps["proposal_id"] == "0133"
    assert gaps["status"] == "review_required"
    assert gaps["summary"] == {
        "gap_count": 1,
        "next_gap": "review_ontology_package_gaps",
    }
    assert gaps["gaps"][0]["gap_id"] == "ontology-gap-sgcore-claimcalibration"
    assert gaps["authority_boundary"]["make_target"] == "ontology-package-gaps"
    assert gaps["authority_boundary"]["canonical_mutations_allowed"] is False
