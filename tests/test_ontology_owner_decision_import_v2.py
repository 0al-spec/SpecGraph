from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "ontology_owner_decision_import_v2.py"


def load_import_v2_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "ontology_owner_decision_import_v2_under_test",
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


def decision_import_preview(decision_state: str = "accepted") -> dict[str, object]:
    preview_state = {
        "accepted": "ready_for_operator_review",
        "rejected": "rejected_by_owner",
        "needs_clarification": "needs_clarification",
    }[decision_state]
    return {
        "artifact_kind": "ontology_decision_import_preview",
        "output_artifact": "runs/ontology_decision_import_preview.json",
        "decision_import_previews": [
            {
                "preview_id": "ontology-decision-import-preview-claim-calibration",
                "decision_id": "owner-decision-claim-calibration",
                "candidate_id": "candidate-claim-calibration",
                "intake_id": "intake-claim-calibration",
                "decision_state": decision_state,
                "preview_state": preview_state,
                "ontology_decision_ref": "ontology-decisions/claim-calibration",
                "decided_by": "ontology-owner@example.invalid",
                "decided_at": "2026-06-20T00:00:00Z",
                "reason": "Owner reviewed the proposed term.",
                "accepted_ontology_delta": decision_state == "accepted",
                "matched_closed_loop_evidence_id": (
                    "ontology-closed-loop-evidence-claim-calibration"
                ),
                "import_recommended": decision_state == "accepted",
            }
        ],
        "ignored_owner_decisions": [],
    }


def closed_loop_evidence() -> dict[str, object]:
    return {
        "artifact_kind": "ontology_closed_loop_evidence",
        "output_artifact": "runs/ontology_closed_loop_evidence.json",
        "evidence_entries": [
            {
                "evidence_id": "ontology-closed-loop-evidence-claim-calibration",
                "candidate_id": "candidate-claim-calibration",
                "intake_id": "intake-claim-calibration",
                "term": "ClaimCalibration",
                "source_intake_state": "awaiting_ontology_owner_review",
                "evidence_state": "pending_ontology_owner_decision",
                "required_human_action": "collect_ontology_owner_delta_decisions",
                "blocking_item_ids": ["SG-SPEC-0126.gap.ClaimCalibration"],
            }
        ],
    }


def gap_review_workflow() -> dict[str, object]:
    return {
        "artifact_kind": "ontology_gap_review_workflow",
        "output_artifact": "runs/ontology_gap_review_workflow.json",
        "gap_groups": [
            {
                "group_id": "ontology-gap-review-legacy-term-claimcalibration",
                "gap_kind": "legacy_term",
                "proposed_term": "ClaimCalibration",
                "proposed_relation": None,
                "missing_ref": "ontology-gap-sg-spec-0126-claimcalibration",
                "review_state": "needs_owner_review",
                "recommended_owner_action": "review_legacy_term_for_package_draft",
                "recommended_route": "ontology_owner_review",
                "source_specs": [
                    {
                        "spec_id": "SG-SPEC-0126",
                        "path": "specs/nodes/SG-SPEC-0126.yaml",
                        "finding_id": "SG-SPEC-0126.gap.ClaimCalibration",
                        "classification": "unknown_legacy_term",
                    }
                ],
                "affected_generated_artifacts": [
                    {
                        "source_ref": "memory://specauthor-claim-calibration",
                        "artifact_kind": "generated_spec_artifact",
                        "target_artifact_kind": "Proposal",
                        "target_artifact_title": "Claim Calibration Contract",
                        "gap_status": "requires_owner_review",
                    }
                ],
                "source_gap_refs": [
                    {
                        "gap_ref": "ontology-gap-sg-spec-0126-claimcalibration",
                        "source_artifact": "spec_ontology_validation_report",
                    }
                ],
                "source_findings": [
                    {
                        "finding_id": "SG-SPEC-0126.gap.ClaimCalibration",
                        "classification": "unknown_legacy_term",
                        "severity": "warning",
                        "suggested_action": "review_ontology_gap",
                    }
                ],
            }
        ],
    }


def validation_report() -> dict[str, object]:
    return {
        "artifact_kind": "spec_ontology_validation_report",
        "output_artifact": "runs/spec_ontology_validation_report.json",
        "entries": [
            {
                "spec_id": "SG-SPEC-0126",
                "path": "specs/nodes/SG-SPEC-0126.yaml",
                "findings": [
                    {
                        "finding_id": "SG-SPEC-0126.gap.ClaimCalibration",
                        "classification": "unknown_legacy_term",
                        "severity": "warning",
                        "term": "ClaimCalibration",
                        "gap_ref": "ontology-gap-sg-spec-0126-claimcalibration",
                        "suggested_action": "review_ontology_gap",
                    }
                ],
            }
        ],
    }


def write_gate_report() -> dict[str, object]:
    return {
        "artifact_kind": "specauthor_ontology_write_gate_report",
        "output_artifact": "runs/specauthor_ontology_write_gate_report.json",
        "source_artifact": {
            "source_ref": "memory://specauthor-claim-calibration",
            "artifact_kind": "generated_spec_artifact",
        },
        "findings": [
            {
                "finding_id": "term_binding_review_required",
                "severity": "review_required",
                "message": "Generated artifact includes terms that need ontology owner review.",
                "source_ref": "memory://specauthor-claim-calibration",
            }
        ],
    }


def test_owner_decision_import_v2_links_accepted_decision_to_gap_and_compliance() -> None:
    module = load_import_v2_module()

    report = module.build_owner_decision_import_v2(
        decision_import_preview=decision_import_preview("accepted"),
        closed_loop_evidence=closed_loop_evidence(),
        gap_review_workflow=gap_review_workflow(),
        validation_report=validation_report(),
        write_gate_reports=[write_gate_report()],
    )

    module.require_owner_decision_import_v2(report)
    assert report["artifact_kind"] == "ontology_owner_decision_import_v2"
    assert report["proposal_id"] == "0139"
    assert report["status"] == "ready_for_operator_ack"
    assert report["canonical_mutations_allowed"] is False
    assert report["summary"]["matched_gap_group_count"] == 1
    assert report["summary"]["importable_count"] == 1

    review = report["decision_import_reviews"][0]
    assert review["decision_state"] == "accepted"
    assert "decided_by" not in review
    assert "reason" not in review
    assert review["matched_closed_loop_evidence"]["term"] == "ClaimCalibration"
    assert review["matched_gap_groups"][0]["group_id"] == (
        "ontology-gap-review-legacy-term-claimcalibration"
    )
    assert review["affected_review_items"]["source_specs"][0]["spec_id"] == "SG-SPEC-0126"
    assert review["compliance_findings"][0]["finding_id"] == "SG-SPEC-0126.gap.ClaimCalibration"
    assert review["write_gate_findings"][0]["finding_id"] == "term_binding_review_required"
    assert review["after_semantic_status"]["status"] == "owner_accepted_pending_operator_import"
    assert review["after_semantic_status"]["writes_ontology_package"] is False
    assert review["after_semantic_status"]["mutates_canonical_specs"] is False


def test_owner_decision_import_v2_skips_write_gate_findings_without_generated_refs() -> None:
    module = load_import_v2_module()
    gap_workflow = gap_review_workflow()
    group = gap_workflow["gap_groups"][0]
    group["affected_generated_artifacts"] = []

    report = module.build_owner_decision_import_v2(
        decision_import_preview=decision_import_preview("accepted"),
        closed_loop_evidence=closed_loop_evidence(),
        gap_review_workflow=gap_workflow,
        validation_report=validation_report(),
        write_gate_reports=[write_gate_report()],
    )

    review = report["decision_import_reviews"][0]
    assert review["affected_review_items"]["affected_generated_artifacts"] == []
    assert review["write_gate_findings"] == []
    assert report["summary"]["write_gate_finding_count"] == 0


def test_owner_decision_import_v2_surfaces_ignored_owner_decisions_as_unmatched_reviews() -> None:
    module = load_import_v2_module()
    preview = decision_import_preview("accepted")
    ignored = preview["decision_import_previews"][0]
    preview["decision_import_previews"] = []
    preview["ignored_owner_decisions"] = [
        {
            **ignored,
            "reason": "missing_closed_loop_evidence",
        }
    ]

    report = module.build_owner_decision_import_v2(
        decision_import_preview=preview,
        closed_loop_evidence={},
        gap_review_workflow={"artifact_kind": "ontology_gap_review_workflow", "gap_groups": []},
        validation_report={"artifact_kind": "spec_ontology_validation_report", "entries": []},
    )

    assert report["status"] == "unmatched_decisions"
    assert report["summary"]["review_count"] == 1
    assert report["summary"]["unmatched_decision_count"] == 1
    review = report["decision_import_reviews"][0]
    assert review["decision_state"] == "accepted"
    assert review["preview_state"] == "unmatched_decision"
    assert "decided_by" not in review
    assert "reason" not in review
    assert review["after_semantic_status"]["status"] == "owner_decision_without_matching_evidence"
    assert review["required_operator_action"] == "review_unmatched_owner_decision"


def test_owner_decision_import_v2_keeps_rejection_ack_only() -> None:
    module = load_import_v2_module()

    report = module.build_owner_decision_import_v2(
        decision_import_preview=decision_import_preview("rejected"),
        closed_loop_evidence=closed_loop_evidence(),
        gap_review_workflow=gap_review_workflow(),
        validation_report=validation_report(),
    )

    review = report["decision_import_reviews"][0]
    assert report["status"] == "owner_rejections_ready_for_ack"
    assert report["summary"]["importable_count"] == 0
    assert review["after_semantic_status"]["status"] == "owner_rejected_no_import"
    assert review["required_operator_action"] == "inspect_and_acknowledge_owner_rejection"
    assert report["authority_boundary"]["may_import_owner_decision"] is False


def test_owner_decision_import_v2_handles_public_tombstone_no_decisions() -> None:
    module = load_import_v2_module()

    report = module.build_owner_decision_import_v2(
        decision_import_preview={
            "artifact_kind": "retired_public_ontology_artifact",
            "summary": {"status": "retired_local_only_artifact"},
        },
        closed_loop_evidence={},
        gap_review_workflow={"artifact_kind": "ontology_gap_review_workflow", "gap_groups": []},
        validation_report={"artifact_kind": "spec_ontology_validation_report", "entries": []},
    )

    assert report["status"] == "no_decisions"
    assert report["summary"]["review_count"] == 0
    assert report["summary"]["next_gap"] == "collect_ontology_owner_decisions"
    assert report["decision_import_reviews"] == []


def test_owner_decision_import_v2_cli_writes_report(tmp_path: Path) -> None:
    decision_path = tmp_path / "decision-preview.json"
    evidence_path = tmp_path / "closed-loop.json"
    gap_path = tmp_path / "gap-review.json"
    validation_path = tmp_path / "validation.json"
    output_path = tmp_path / "owner-decision-import-v2.json"
    decision_path.write_text(json.dumps(decision_import_preview()), encoding="utf-8")
    evidence_path.write_text(json.dumps(closed_loop_evidence()), encoding="utf-8")
    gap_path.write_text(json.dumps(gap_review_workflow()), encoding="utf-8")
    validation_path.write_text(json.dumps(validation_report()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--decision-import-preview",
            str(decision_path),
            "--closed-loop-evidence",
            str(evidence_path),
            "--gap-review-workflow",
            str(gap_path),
            "--validation-report",
            str(validation_path),
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
    assert report["artifact_kind"] == "ontology_owner_decision_import_v2"
    assert report["summary"]["matched_gap_group_count"] == 1


def test_owner_decision_import_v2_cli_reuses_default_gap_review_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_import_v2_module()
    decision_path = tmp_path / "decision-preview.json"
    evidence_path = tmp_path / "closed-loop.json"
    gap_path = tmp_path / "ontology-gap-review-workflow.json"
    validation_path = tmp_path / "validation.json"
    output_path = tmp_path / "owner-decision-import-v2.json"
    decision_path.write_text(json.dumps(decision_import_preview()), encoding="utf-8")
    evidence_path.write_text(json.dumps(closed_loop_evidence()), encoding="utf-8")
    gap_path.write_text(json.dumps(gap_review_workflow()), encoding="utf-8")
    validation_path.write_text(json.dumps(validation_report()), encoding="utf-8")
    monkeypatch.setattr(module, "DEFAULT_GAP_REVIEW_PATH", gap_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ontology_owner_decision_import_v2.py",
            "--decision-import-preview",
            str(decision_path),
            "--closed-loop-evidence",
            str(evidence_path),
            "--validation-report",
            str(validation_path),
            "--output",
            str(output_path),
            "--write",
        ],
    )

    assert module.main() == 0

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["artifact_kind"] == "ontology_owner_decision_import_v2"
    assert report["summary"]["matched_gap_group_count"] == 1
    assert report["source_artifacts"]["ontology_gap_review_workflow"] == (
        "runs/ontology_gap_review_workflow.json"
    )
