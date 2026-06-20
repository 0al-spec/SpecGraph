from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "ontology_gap_review_workflow.py"
GENERATED_ARTIFACT_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "ontology_term_binding"
    / "generated_artifact_review_required.json"
)


def load_gap_review_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "ontology_gap_review_workflow_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOL_PATH.parent))
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOL_PATH.parent))
    return module


def package_gap_preview() -> dict[str, object]:
    return {
        "artifact_kind": "ontology_package_gap_preview",
        "gaps": [
            {
                "gap_id": "ontology-gap-sgcore-claimcalibration",
                "missing_concept": {
                    "ref": "sgcore:ClaimCalibration",
                    "namespace_hint": "sgcore",
                    "concept_hint": "ClaimCalibration",
                },
                "recommended_route": "ontology_package_draft",
                "source_refs": [
                    "docs/proposals/0126_specauthor_claim_calibration_prompt_contract.md"
                ],
            }
        ],
    }


def validation_report() -> dict[str, object]:
    return {
        "artifact_kind": "spec_ontology_validation_report",
        "entries": [
            {
                "spec_id": "SG-SPEC-0001",
                "path": "specs/nodes/SG-SPEC-0001.yaml",
                "findings": [
                    {
                        "finding_id": "SG-SPEC-0001.gap.intent",
                        "severity": "warning",
                        "classification": "unknown_legacy_term",
                        "term": "Intent",
                        "source": "specification.terminology",
                        "gap_ref": "ontology-gap-sg-spec-0001-intent",
                        "suggested_action": "review_ontology_gap",
                    }
                ],
            },
            {
                "spec_id": "SG-SPEC-0002",
                "path": "specs/nodes/SG-SPEC-0002.yaml",
                "findings": [
                    {
                        "finding_id": "SG-SPEC-0002.unknown-relation.sgcore:ownedBy",
                        "severity": "warning",
                        "classification": "unknown_relation",
                        "relation_ref": "sgcore:ownedBy",
                        "suggested_action": "emit_ontology_gap",
                    }
                ],
            },
        ],
    }


def generated_artifact() -> dict[str, object]:
    return {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://specauthor-gap-candidate",
        "target_artifact": {
            "kind": "Proposal",
            "title": "Generated Gap Candidate",
        },
        "ontology_gaps": [
            {
                "gap_id": "ontology-gap-ownerdecisionreviewsurface",
                "proposed_term": "ClaimCalibration",
                "proposed_kind": "entity",
                "status": "requires_owner_review",
                "canonical_mutations_allowed": False,
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
            }
        ],
    }


def groups_by_term(report: dict[str, object]) -> dict[str, dict[str, object]]:
    groups = report["gap_groups"]
    assert isinstance(groups, list)
    return {
        str(group.get("proposed_term") or group.get("proposed_relation")): group
        for group in groups
        if isinstance(group, dict)
    }


def test_ontology_gap_review_workflow_groups_package_spec_and_generated_gaps() -> None:
    module = load_gap_review_module()

    report = module.build_gap_review_workflow(
        package_gap_preview=package_gap_preview(),
        validation_report=validation_report(),
        generated_artifacts=[(generated_artifact(), None)],
    )

    assert report["artifact_kind"] == "ontology_gap_review_workflow"
    assert report["proposal_id"] == "0138"
    assert report["status"] == "review_required"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["summary"]["gap_group_count"] == 3
    assert report["summary"]["source_spec_count"] == 2
    assert report["summary"]["affected_generated_artifact_count"] == 1

    by_term = groups_by_term(report)
    assert by_term["ClaimCalibration"]["recommended_owner_action"] == (
        "draft_project_local_ontology_package_update"
    )
    assert by_term["ClaimCalibration"]["affected_generated_artifacts"][0]["source_ref"] == (
        "memory://specauthor-gap-candidate"
    )
    assert by_term["Intent"]["source_specs"][0]["spec_id"] == "SG-SPEC-0001"
    assert by_term["sgcore:ownedBy"]["gap_kind"] == "relation"


def test_ontology_gap_review_workflow_is_clear_without_gaps() -> None:
    module = load_gap_review_module()

    report = module.build_gap_review_workflow(
        package_gap_preview={"artifact_kind": "ontology_package_gap_preview", "gaps": []},
        validation_report={"artifact_kind": "spec_ontology_validation_report", "entries": []},
        generated_artifacts=[],
    )

    assert report["status"] == "clear"
    assert report["review_state"] == "clear"
    assert report["summary"]["next_gap"] == "none"
    assert report["gap_groups"] == []


def test_ontology_gap_review_workflow_cli_writes_report(tmp_path: Path) -> None:
    output_path = tmp_path / "ontology-gap-review-workflow.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--generated-artifact",
            str(GENERATED_ARTIFACT_FIXTURE),
            "--output",
            str(output_path),
            "--write",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["artifact_kind"] == "ontology_gap_review_workflow"
    assert report["summary"]["gap_group_count"] > 0
    assert any(group["affected_generated_artifact_count"] == 1 for group in report["gap_groups"])
