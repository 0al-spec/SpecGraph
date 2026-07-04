from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "specspace_project_local_ontology_decision_import_preview.py"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "specspace_project_local_ontology_decision_import_preview_under_test",
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
        "proposal_id": "0197",
        "contract_ref": "specgraph.product-ontology.project-local-review-lane.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "readiness": {
            "ready": False,
            "review_state": "project_local_ontology_review_required",
            "blocked_by": ["project_local_ontology_terms_unreviewed"],
        },
        "context": {
            "workspace_id": "cash-flow-control",
            "candidate_id": "cash-flow-control",
            "repair_session_id": "repair-session.cash-flow-control",
            "workflow_lane": "product_idea_to_spec",
            "domain_refs": ["domain.cash_flow_control"],
            "context_refs": ["context.idea_to_spec"],
            "ontology_refs": ["ontology://specgraph-core"],
        },
        "review_decision_schema": {
            "supported_actions": [
                "keep_project_local",
                "bind_existing",
                "alias",
                "reject",
                "request_workspace_promotion",
                "defer",
            ],
            "authority": "operator_intent_only",
        },
        "terms": [
            {
                "id": "project-local-ontology-term.recurringpayment",
                "term": "Recurring Payment",
                "term_key": "recurringpayment",
                "status": "unreviewed",
                "suggested_actions": [
                    "keep_project_local",
                    "bind_existing",
                    "alias",
                    "reject",
                    "request_workspace_promotion",
                    "defer",
                ],
                "gap_refs": [
                    {
                        "gap_id": "ontology-gap.recurring-payment",
                        "node_id": "candidate-spec.cash-flow-boundary",
                        "target_ref": (
                            "candidate-spec.cash-flow-boundary.gaps.ontology-gap.recurring-payment"
                        ),
                    }
                ],
            }
        ],
        "authority_boundary": {
            "may_execute_prompt_agent": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
            "may_create_branch_or_commit": False,
        },
        "privacy_boundary": {
            "raw_idea_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
        },
        "summary": {
            "status": "project_local_ontology_review_required",
            "term_count": 1,
            "unreviewed_term_count": 1,
        },
    }


def decision_state(
    *,
    action: str = "keep_project_local",
    decision_value: dict[str, object] | None = None,
    authority_expanded: bool = False,
    lane_ref: str = "runs/project_local_ontology_review_lane.json",
) -> dict[str, object]:
    return {
        "artifact_kind": "specspace_project_local_ontology_review_decision_state",
        "schema_version": 1,
        "state_owner": "SpecSpace",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "consumer_boundary": {
            "specspace_owned_state": True,
            "may_apply_to_specgraph": False,
            "may_write_ontology_package": authority_expanded,
            "may_accept_ontology_terms": False,
        },
        "authority_boundary": {
            "specgraph_artifact_authority": False,
            "ontology_authority": False,
            "git_service_authority": False,
        },
        "decisions": [
            {
                "decision_id": (
                    "specspace-project-local-ontology-decision::cash-flow-control::recurringpayment"
                ),
                "workspace_id": "cash-flow-control",
                "candidate_id": "cash-flow-control",
                "repair_session_id": "repair-session.cash-flow-control",
                "project_local_ontology_review_lane_ref": lane_ref,
                "term": "Recurring Payment",
                "term_key": "recurringpayment",
                "review_action": action,
                "decision_value": decision_value
                if decision_value is not None
                else {
                    "term": "Recurring Payment",
                    "term_scope": "project_local",
                    "reason": "Product-local term for this bounded context.",
                },
                "canonical_mutations_allowed": False,
                "tracked_artifacts_written": False,
                "applies_to_specgraph": False,
                "writes_ontology_package": False,
                "accepts_ontology_terms": False,
                "creates_branch_or_commit": False,
            }
        ],
        "summary": {"decision_count": 1},
    }


def build_report(
    *,
    state: dict[str, object] | None = None,
    lane: dict[str, object] | None = None,
) -> dict[str, object]:
    module = load_module()
    return module.build_specspace_project_local_ontology_decision_import_preview(
        decision_state=decision_state() if state is None else state,
        review_lane=review_lane() if lane is None else lane,
        decision_state_path=ROOT / "runs" / "project_local_ontology_review_decisions.json",
        review_lane_path=ROOT / "runs" / "project_local_ontology_review_lane.json",
        workspace_id="cash-flow-control",
    )


def test_specspace_project_local_import_preview_accepts_project_local_decision() -> None:
    report = build_report()

    assert report["artifact_kind"] == "specspace_project_local_ontology_decision_import_preview"
    assert report["proposal_id"] == "0198"
    assert report["readiness"]["ready"] is True
    assert report["summary"]["accepted_decision_count"] == 1
    assert report["summary"]["missing_decision_count"] == 0
    candidate = report["decision_candidates"][0]
    assert candidate["decision_type"] == "propose_project_local_term"
    assert candidate["writes_ontology_package"] is False
    assert candidate["accepts_ontology_terms"] is False
    assert report["authority_boundary"]["may_apply_to_specgraph"] is False


def test_specspace_project_local_import_preview_accepts_isolated_lane_alias() -> None:
    module = load_module()
    report = module.build_specspace_project_local_ontology_decision_import_preview(
        decision_state=decision_state(lane_ref="runs/project_local_ontology_review_lane.json"),
        review_lane=review_lane(),
        decision_state_path=ROOT
        / "runs"
        / "ui-started-smoke"
        / "project_local_ontology_review_decisions.json",
        review_lane_path=ROOT
        / "runs"
        / "ui-started-smoke"
        / "project_local_ontology_review_lane.json",
        workspace_id="cash-flow-control",
    )

    assert report["readiness"]["ready"] is True
    assert report["summary"]["accepted_decision_count"] == 1
    assert report["summary"]["invalid_decision_count"] == 0


def test_specspace_project_local_import_preview_redacts_private_decision_value_text() -> None:
    report = build_report(
        state=decision_state(
            decision_value={
                "term": "Recurring Payment",
                "reason": "See /Users/operator/private-note.txt bearer secret-token",
            },
        )
    )

    candidate = report["decision_candidates"][0]
    accepted = report["import_preview"]["accepted_decisions"][0]
    assert candidate["decision_value"]["reason"] == "[redacted-private-text]"
    assert accepted["decision_value"]["reason"] == "[redacted-private-text]"
    assert "/Users/operator" not in json.dumps(report)
    assert "bearer secret-token" not in json.dumps(report)


def test_specspace_project_local_import_preview_redacts_private_non_resolving_text() -> None:
    report = build_report(
        state=decision_state(
            action="defer",
            decision_value={
                "term": "Recurring Payment",
                "reason": "Owner has the details.",
                "follow_up": "Ask operator with api_key=local-secret",
            },
        )
    )

    deferred = report["import_preview"]["non_resolving_decisions"][0]
    assert deferred["decision_value"]["follow_up"] == "[redacted-private-text]"
    assert "api_key=local-secret" not in json.dumps(report)


def test_specspace_project_local_import_preview_blocks_missing_decision() -> None:
    state = decision_state()
    state["decisions"] = []

    report = build_report(state=state)

    assert report["readiness"]["ready"] is False
    assert report["summary"]["missing_decision_count"] == 1
    assert "project_local_decision_missing_recurringpayment" in set(
        report["readiness"]["blocked_by"]
    )


def test_specspace_project_local_import_preview_blocks_authority_expansion() -> None:
    report = build_report(state=decision_state(authority_expanded=True))

    assert report["readiness"]["ready"] is False
    assert any(
        finding["finding_id"] == "project_local_decision_state_consumer_boundary_expanded"
        for finding in report["findings"]
    )


def test_specspace_project_local_import_preview_rejects_read_model_authority() -> None:
    state = decision_state()
    boundary = state["authority_boundary"]
    assert isinstance(boundary, dict)
    boundary["may_publish_read_model"] = True

    report = build_report(state=state)

    assert report["readiness"]["ready"] is False
    assert any(
        finding["finding_id"] == "project_local_decision_state_authority_boundary_expanded"
        for finding in report["findings"]
    )


def test_specspace_project_local_import_preview_requires_candidate_identity() -> None:
    state = decision_state()
    decision = state["decisions"][0]
    assert isinstance(decision, dict)
    decision.pop("candidate_id")

    report = build_report(state=state)

    assert report["readiness"]["ready"] is False
    assert report["summary"]["invalid_decision_count"] == 1
    assert report["summary"]["missing_decision_count"] == 0
    assert report["import_preview"]["invalid_decisions"][0]["reason"] == ("candidate_missing")


def test_specspace_project_local_import_preview_requires_lane_ref() -> None:
    state = decision_state()
    decision = state["decisions"][0]
    assert isinstance(decision, dict)
    decision.pop("project_local_ontology_review_lane_ref")

    report = build_report(state=state)

    assert report["readiness"]["ready"] is False
    assert report["summary"]["invalid_decision_count"] == 1
    assert report["summary"]["missing_decision_count"] == 0
    assert report["import_preview"]["invalid_decisions"][0]["reason"] == ("review_lane_ref_missing")


def test_specspace_project_local_import_preview_rejects_invalid_bind() -> None:
    report = build_report(
        state=decision_state(
            action="bind_existing",
            decision_value={"term": "Recurring Payment"},
        )
    )

    assert report["readiness"]["ready"] is False
    assert report["summary"]["invalid_decision_count"] == 1
    assert report["import_preview"]["invalid_decisions"][0]["reason"] == (
        "bind_existing_requires_ontology_ref"
    )
    assert report["summary"]["missing_decision_count"] == 0


def test_specspace_project_local_import_preview_rejects_term_mismatch() -> None:
    report = build_report(
        state=decision_state(
            decision_value={
                "term": "Customer Password",
                "reason": "Wrong term.",
            },
        )
    )

    assert report["readiness"]["ready"] is False
    assert report["summary"]["invalid_decision_count"] == 1
    assert report["summary"]["missing_decision_count"] == 0
    assert report["import_preview"]["invalid_decisions"][0]["reason"] == ("decision_term_mismatch")


def test_specspace_project_local_import_preview_rejects_duplicate_term_decisions() -> None:
    state = decision_state()
    duplicate = dict(state["decisions"][0])
    duplicate["decision_id"] = (
        "specspace-project-local-ontology-decision::cash-flow-control::recurringpayment::2"
    )
    state["decisions"].append(duplicate)

    report = build_report(state=state)

    assert report["readiness"]["ready"] is False
    assert report["summary"]["accepted_decision_count"] == 1
    assert report["summary"]["invalid_decision_count"] == 1
    assert report["import_preview"]["invalid_decisions"][0]["reason"] == (
        "duplicate_project_local_term_decision"
    )


def test_specspace_project_local_import_preview_keeps_defer_non_resolving() -> None:
    report = build_report(
        state=decision_state(
            action="defer",
            decision_value={
                "term": "Recurring Payment",
                "reason": "Needs owner review.",
            },
        )
    )

    assert report["readiness"]["ready"] is False
    assert report["summary"]["non_resolving_decision_count"] == 1
    assert "project_local_ontology_decisions_deferred" in set(report["readiness"]["blocked_by"])


def test_specspace_project_local_import_preview_cli_writes_output(tmp_path: Path) -> None:
    decisions_path = tmp_path / "project_local_ontology_review_decisions.json"
    lane_path = tmp_path / "project_local_ontology_review_lane.json"
    output = tmp_path / "specspace_project_local_ontology_decision_import_preview.json"
    decisions_path.write_text(
        json.dumps(decision_state(lane_ref="external:project_local_ontology_review_lane.json")),
        encoding="utf-8",
    )
    lane_path.write_text(json.dumps(review_lane()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--decisions",
            str(decisions_path),
            "--review-lane",
            str(lane_path),
            "--workspace-id",
            "cash-flow-control",
            "--output",
            str(output),
            "--strict",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["summary"]["status"] == "project_local_ontology_decision_import_ready"
