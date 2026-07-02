from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "project_local_ontology_decision_effect_report.py"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "project_local_ontology_decision_effect_report_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def review_lane() -> dict[str, object]:
    return {
        "artifact_kind": "project_local_ontology_review_lane",
        "schema_version": 1,
        "contract_ref": "specgraph.product-ontology.project-local-review-lane.v0.1",
        "context": {
            "workspace_id": "cash-flow-control",
            "candidate_id": "cash-flow-control",
            "repair_session_id": "repair-session.cash-flow-control",
            "workflow_lane": "product_idea_to_spec",
        },
        "terms": [
            {
                "term": "Recurring Payment",
                "term_key": "recurringpayment",
                "status": "unreviewed",
            }
        ],
        "summary": {"term_count": 1},
        "authority_boundary": {
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
        },
    }


def import_preview(
    *, include_missing: bool = False, include_deferred: bool = False
) -> dict[str, object]:
    accepted = [
        {
            "id": "specspace-project-local-ontology-import.recurringpayment.keep",
            "source_decision_id": "decision.recurringpayment",
            "source_artifact": "runs/project_local_ontology_review_decisions.json",
            "decision_type": "propose_project_local_term",
            "review_action": "keep_project_local",
            "status": "accepted_for_project_local_preview",
            "term": "Recurring Payment",
            "term_key": "recurringpayment",
            "target_ref": "candidate-spec.cash-flow.gaps.ontology-gap.recurring-payment",
            "gap_refs": [
                {
                    "gap_id": "ontology-gap.recurring-payment",
                    "target_ref": "candidate-spec.cash-flow.gaps.ontology-gap.recurring-payment",
                }
            ],
            "writes_ontology_package": False,
            "accepts_ontology_terms": False,
            "canonical_mutations_allowed": False,
        }
    ]
    non_resolving = []
    missing = []
    if include_deferred:
        accepted = []
        non_resolving.append(
            {
                **import_preview()["import_preview"]["accepted_decisions"][0],
                "review_action": "defer",
                "decision_type": "defer_requires_owner",
                "status": "deferred_requires_owner",
            }
        )
    if include_missing:
        accepted = []
        missing.append(
            {
                "term": "Recurring Payment",
                "term_key": "recurringpayment",
                "reason": "required_project_local_ontology_decision_missing",
            }
        )
    return {
        "artifact_kind": "specspace_project_local_ontology_decision_import_preview",
        "schema_version": 1,
        "contract_ref": "specgraph.product-ontology.specspace-decision-import.v0.1",
        "context": {
            "workspace_id": "cash-flow-control",
            "candidate_id": "cash-flow-control",
            "repair_session_id": "repair-session.cash-flow-control",
            "workflow_lane": "product_idea_to_spec",
        },
        "import_preview": {
            "accepted_decisions": accepted,
            "non_resolving_decisions": non_resolving,
            "invalid_decisions": [],
            "missing_decisions": missing,
        },
        "summary": {
            "accepted_decision_count": len(accepted),
            "non_resolving_decision_count": len(non_resolving),
            "missing_decision_count": len(missing),
            "invalid_decision_count": 0,
        },
        "readiness": {
            "ready": bool(accepted) and not non_resolving and not missing,
            "review_state": "project_local_ontology_decision_import_ready",
        },
        "source_artifacts": {
            "project_local_ontology_review_lane": {
                "source_ref": "runs/project_local_ontology_review_lane.json",
                "status": "present",
            }
        },
        "authority_boundary": {
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
        },
    }


def build_report(**kwargs: object) -> dict[str, object]:
    module = load_module()
    return module.build_project_local_ontology_decision_effect_report(
        review_lane=kwargs.get("lane", review_lane()),
        import_preview=kwargs.get("preview", import_preview()),
        review_lane_path=ROOT / "runs" / "project_local_ontology_review_lane.json",
        import_preview_path=(
            ROOT / "runs" / "specspace_project_local_ontology_decision_import_preview.json"
        ),
    )


def test_project_local_decision_effect_counts_maturity_evidence() -> None:
    report = build_report()

    assert report["artifact_kind"] == "project_local_ontology_decision_effect_report"
    assert report["readiness"]["ready"] is True
    assert report["summary"]["accepted_decision_count"] == 1
    assert report["summary"]["keep_project_local_count"] == 1
    assert report["summary"]["missing_decision_count"] == 0
    assert report["summary"]["ready_for_maturity"] is True
    assert report["decision_effects"][0]["maturity_effect"] == "resolves_project_local_review"
    assert report["decision_effects"][0]["writes_ontology_package"] is False
    assert report["decision_effects"][0]["accepts_ontology_terms"] is False


def test_project_local_decision_effect_blocks_missing_decisions() -> None:
    report = build_report(preview=import_preview(include_missing=True))

    assert report["readiness"]["ready"] is False
    assert report["summary"]["missing_decision_count"] == 1
    assert report["summary"]["blocking_decision_count"] == 1
    assert any(
        finding["finding_id"].startswith("project_local_ontology_decision_missing")
        for finding in report["findings"]
    )


def test_project_local_decision_effect_records_deferred_as_non_resolving() -> None:
    report = build_report(preview=import_preview(include_deferred=True))

    assert report["readiness"]["ready"] is False
    assert report["summary"]["deferred_count"] == 1
    assert report["summary"]["non_resolving_decision_count"] == 1
    assert report["summary"]["blocking_decision_count"] == 0


def test_project_local_decision_effect_honors_blocked_import_preview() -> None:
    preview = import_preview()
    preview["readiness"] = {
        "ready": False,
        "review_state": "project_local_ontology_decision_import_review_required",
        "blocked_by": ["project_local_decision_invalid_recurringpayment"],
    }

    report = build_report(preview=preview)

    assert report["readiness"]["ready"] is False
    assert "project_local_ontology_import_preview_not_ready" in set(
        report["readiness"]["blocked_by"]
    )


def test_project_local_decision_effect_blocks_stale_import_preview_lane_source() -> None:
    preview = import_preview()
    preview["source_artifacts"]["project_local_ontology_review_lane"]["source_ref"] = (
        "runs/old_project_local_ontology_review_lane.json"
    )

    report = build_report(preview=preview)

    assert report["readiness"]["ready"] is False
    assert "project_local_ontology_import_preview_lane_source_stale" in set(
        report["readiness"]["blocked_by"]
    )
