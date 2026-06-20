from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "legacy_spec_ontology_backfill_plan.py"


def load_backfill_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "legacy_spec_ontology_backfill_plan_under_test",
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


def validation_report() -> dict[str, object]:
    return {
        "artifact_kind": "spec_ontology_validation_report",
        "output_artifact": "runs/spec_ontology_validation_report.json",
        "entries": [
            {
                "spec_id": "SG-SPEC-0001",
                "path": "specs/nodes/SG-SPEC-0001.yaml",
                "validation_status": "report_only_clean",
                "checks": [],
                "findings": [],
            },
            {
                "spec_id": "SG-SPEC-0002",
                "path": "specs/nodes/SG-SPEC-0002.yaml",
                "validation_status": "report_only_findings",
                "checks": [],
                "findings": [
                    {
                        "finding_id": "SG-SPEC-0002.gap.IntentAtom",
                        "severity": "warning",
                        "classification": "unknown_legacy_term",
                        "term": "IntentAtom",
                        "gap_ref": "ontology-gap-sg-spec-0002-intentatom",
                        "suggested_action": "review_ontology_gap",
                    },
                    {
                        "finding_id": "SG-SPEC-0002.gap.ContextFrame",
                        "severity": "warning",
                        "classification": "unknown_legacy_term",
                        "term": "ContextFrame",
                        "gap_ref": "ontology-gap-sg-spec-0002-contextframe",
                        "suggested_action": "review_ontology_gap",
                    },
                ],
            },
            {
                "spec_id": "SG-SPEC-0003",
                "path": "specs/nodes/SG-SPEC-0003.yaml",
                "validation_status": "report_only_findings",
                "checks": [],
                "findings": [
                    {
                        "finding_id": "SG-SPEC-0003.unknown-relation.sgcore:ownedBy",
                        "severity": "warning",
                        "classification": "unknown_relation",
                        "relation_ref": "sgcore:ownedBy",
                        "suggested_action": "emit_ontology_gap",
                    }
                ],
            },
            {
                "spec_id": "SG-SPEC-0004",
                "path": "specs/nodes/SG-SPEC-0004.yaml",
                "validation_status": "report_only_findings",
                "checks": [],
                "findings": [
                    {
                        "finding_id": f"SG-SPEC-0004.gap.Term{index}",
                        "severity": "warning",
                        "classification": "unknown_legacy_term",
                        "term": f"Term{index}",
                        "gap_ref": f"ontology-gap-sg-spec-0004-term{index}",
                        "suggested_action": "review_ontology_gap",
                    }
                    for index in range(1, 5)
                ],
            },
        ],
    }


def gap_review_workflow() -> dict[str, object]:
    return {
        "artifact_kind": "ontology_gap_review_workflow",
        "output_artifact": "runs/ontology_gap_review_workflow.json",
        "gap_groups": [
            {
                "group_id": "ontology-gap-review-legacy-term-intentatom",
                "gap_kind": "legacy_term",
                "proposed_term": "IntentAtom",
                "proposed_relation": None,
                "recommended_owner_action": "review_legacy_term_for_package_draft",
                "recommended_route": "ontology_owner_review",
                "source_specs": [
                    {
                        "spec_id": "SG-SPEC-0002",
                        "path": "specs/nodes/SG-SPEC-0002.yaml",
                        "finding_id": "SG-SPEC-0002.gap.IntentAtom",
                        "classification": "unknown_legacy_term",
                    }
                ],
                "source_findings": [
                    {
                        "finding_id": "SG-SPEC-0002.gap.IntentAtom",
                        "classification": "unknown_legacy_term",
                        "severity": "warning",
                    }
                ],
                "source_gap_refs": [
                    {
                        "gap_ref": "ontology-gap-sg-spec-0002-intentatom",
                        "source_artifact": "spec_ontology_validation_report",
                    }
                ],
            }
        ],
    }


def reviews_by_spec(report: dict[str, object]) -> dict[str, dict[str, object]]:
    reviews = report["spec_reviews"]
    assert isinstance(reviews, list)
    return {str(review["spec_id"]): review for review in reviews if isinstance(review, dict)}


def test_legacy_spec_backfill_plan_classifies_review_lanes_and_batches() -> None:
    module = load_backfill_module()

    report = module.build_legacy_spec_ontology_backfill_plan(
        validation_report=validation_report(),
        gap_review_workflow=gap_review_workflow(),
        max_findings_per_small_pr_spec=2,
        max_specs_per_batch=2,
        max_findings_per_batch=4,
    )

    module.require_legacy_spec_ontology_backfill_plan(report)
    assert report["artifact_kind"] == "legacy_spec_ontology_backfill_plan"
    assert report["proposal_id"] == "0140"
    assert report["canonical_mutations_allowed"] is False
    assert report["summary"]["spec_count"] == 4
    assert report["summary"]["clean_spec_count"] == 1
    assert report["summary"]["warning_only_spec_count"] == 3
    assert report["summary"]["small_pr_candidate_spec_count"] == 1
    assert report["summary"]["new_term_decision_spec_count"] == 2
    assert report["summary"]["large_new_term_decision_spec_count"] == 1
    assert report["summary"]["relation_review_spec_count"] == 1

    by_spec = reviews_by_spec(report)
    assert by_spec["SG-SPEC-0001"]["backfill_category"] == "clean_existing_bindings"
    assert by_spec["SG-SPEC-0002"]["backfill_category"] == "ready_for_small_pr_batch"
    assert by_spec["SG-SPEC-0002"]["matched_gap_group_count"] == 1
    assert by_spec["SG-SPEC-0003"]["backfill_category"] == "relation_review_required"
    assert by_spec["SG-SPEC-0004"]["backfill_category"] == "new_term_decision_required"
    assert by_spec["SG-SPEC-0004"]["unknown_term_count"] == 4

    batches = report["small_pr_batches"]
    assert len(batches) == 1
    assert batches[0]["specs"][0]["spec_id"] == "SG-SPEC-0002"
    assert batches[0]["canonical_mutations_allowed"] is False
    assert batches[0]["mutates_canonical_specs"] is False


def test_legacy_spec_backfill_plan_caps_single_candidate_by_batch_findings() -> None:
    module = load_backfill_module()

    report = module.build_legacy_spec_ontology_backfill_plan(
        validation_report=validation_report(),
        gap_review_workflow=gap_review_workflow(),
        max_findings_per_small_pr_spec=5,
        max_specs_per_batch=5,
        max_findings_per_batch=3,
    )

    by_spec = reviews_by_spec(report)
    assert by_spec["SG-SPEC-0004"]["finding_count"] == 4
    assert by_spec["SG-SPEC-0004"]["backfill_category"] == "new_term_decision_required"
    assert report["planning_thresholds"]["effective_max_findings_per_small_pr_spec"] == 3
    assert all(batch["finding_count"] <= 3 for batch in report["small_pr_batches"])


def test_legacy_spec_backfill_plan_is_clear_without_findings() -> None:
    module = load_backfill_module()

    report = module.build_legacy_spec_ontology_backfill_plan(
        validation_report={
            "artifact_kind": "spec_ontology_validation_report",
            "entries": [
                {
                    "spec_id": "SG-SPEC-0001",
                    "path": "specs/nodes/SG-SPEC-0001.yaml",
                    "validation_status": "report_only_clean",
                    "findings": [],
                }
            ],
        },
        gap_review_workflow={"artifact_kind": "ontology_gap_review_workflow", "gap_groups": []},
    )

    assert report["status"] == "clear"
    assert report["summary"]["next_gap"] == "none"
    assert report["small_pr_batches"] == []


def test_legacy_spec_backfill_plan_cli_writes_report(tmp_path: Path) -> None:
    validation_path = tmp_path / "validation.json"
    gap_path = tmp_path / "gap-review.json"
    output_path = tmp_path / "backfill-plan.json"
    validation_path.write_text(json.dumps(validation_report()), encoding="utf-8")
    gap_path.write_text(json.dumps(gap_review_workflow()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--validation-report",
            str(validation_path),
            "--gap-review-workflow",
            str(gap_path),
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
    assert report["artifact_kind"] == "legacy_spec_ontology_backfill_plan"
    assert report["summary"]["small_pr_batch_count"] == 1
