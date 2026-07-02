from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "project_local_ontology_review_lane.py"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "project_local_ontology_review_lane_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def candidate_graph() -> dict[str, object]:
    return {
        "artifact_kind": "candidate_spec_graph",
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "schema_version": 1,
        "authority_boundary": {
            "may_execute_prompt_agent": False,
            "may_mutate_canonical_specs": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
        },
        "active_frame": {
            "domain_refs": ["domain.cash_flow_control"],
            "context_refs": ["context.idea_to_spec"],
            "ontology_refs": ["ontology://specgraph-core"],
        },
        "nodes": [
            {
                "id": "candidate-spec.product-boundary",
                "title": "Product Boundary",
                "gaps": [
                    {
                        "id": "ontology-gap.recurring-payment",
                        "kind": "ontology_gap",
                        "term": "Recurring Payment",
                        "source_ref": "event.recurring-payment-scheduled",
                        "source_kind": "domain_event",
                        "statement": (
                            "Confirm whether `Recurring Payment` should bind to an "
                            "existing ontology term or remain project-local."
                        ),
                        "suggested_action": "confirm_bind_or_promote_domain_term",
                    }
                ],
            }
        ],
        "summary": {"status": "ready_for_pre_sib"},
    }


def decisions_report(
    *,
    authority_expanded: bool = False,
    ready: bool = True,
) -> dict[str, object]:
    return {
        "artifact_kind": "product_ontology_gap_review_decisions",
        "contract_ref": "specgraph.product-ontology.gap-review-decisions.v0.1",
        "schema_version": 1,
        "readiness": {
            "ready": ready,
            "review_state": (
                "ontology_gap_decisions_ready"
                if ready
                else "ontology_gap_decisions_review_required"
            ),
            "blocked_by": [] if ready else ["unsupported_ontology_decision"],
        },
        "authority_boundary": {
            "may_execute_prompt_agent": False,
            "may_write_ontology_package": authority_expanded,
            "may_accept_ontology_terms": False,
            "may_apply_answers_to_source_artifacts": False,
        },
        "decisions": [
            {
                "id": "product-ontology-decision.recurring-payment.0",
                "decision_type": "propose_project_local_term",
                "status": "accepted_for_candidate_preview",
                "materialization_intent": "rerun_overlay_only",
                "request_id": (
                    "clarification.candidate-gap.candidate-spec-product-boundary-"
                    "gaps-ontology-gap-recurring-payment"
                ),
                "request_kind": "ontology_gap",
                "target_artifact": "runs/candidate_spec_graph.json",
                "target_ref": (
                    "candidate-spec.product-boundary.gaps.ontology-gap.recurring-payment"
                ),
                "source_answer_kind": "propose_project_local_term",
                "source_answer_status": "accepted_for_candidate",
                "term": "Recurring Payment",
                "term_scope": "project_local",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "accepts_ontology_term": False,
            }
        ],
        "summary": {"status": "ontology_gap_decisions_ready", "decision_count": 1},
    }


def rerun_preview() -> dict[str, object]:
    return {
        "artifact_kind": "idea_to_spec_rerun_preview",
        "contract_ref": "specgraph.idea-to-spec.rerun-preview.v0.1",
        "schema_version": 1,
        "authority_boundary": {
            "may_execute_prompt_agent": False,
            "may_apply_answers_to_source_artifacts": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
        },
        "rerun_preview": {
            "ontology_gap_preview": {
                "resolved_ontology_gaps": [
                    {
                        "gap_id": "ontology-gap.recurring-payment",
                        "node_id": "candidate-spec.product-boundary",
                        "term": "Recurring Payment",
                        "source_ref": "event.recurring-payment-scheduled",
                        "decision_id": "product-ontology-decision.recurring-payment.0",
                        "match_kind": "target_ref",
                        "confidence": "explicit_target",
                    }
                ],
                "unresolved_ontology_gaps": [],
            }
        },
        "summary": {
            "status": "rerun_preview_ready",
            "resolved_ontology_gap_count": 1,
            "unresolved_ontology_gap_count": 0,
        },
    }


def test_project_local_ontology_review_lane_blocks_unreviewed_terms() -> None:
    module = load_module()

    report = module.build_project_local_ontology_review_lane(candidate_graph=candidate_graph())

    assert report["artifact_kind"] == "project_local_ontology_review_lane"
    assert report["proposal_id"] == "0197"
    assert report["readiness"]["ready"] is False
    assert report["summary"]["unreviewed_term_count"] == 1
    assert report["terms"][0]["status"] == "unreviewed"
    assert report["terms"][0]["effect"]["next_action"] == "choose_project_local_ontology_decision"
    boundary = report["authority_boundary"]
    assert boundary["may_write_ontology_package"] is False
    assert boundary["may_accept_ontology_terms"] is False


def test_project_local_ontology_review_lane_marks_project_local_decision_ready() -> None:
    module = load_module()

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions_report(),
        rerun_preview=rerun_preview(),
    )

    assert report["readiness"]["ready"] is True
    assert report["summary"]["status_counts"] == {"kept_project_local": 1}
    term = report["terms"][0]
    assert term["status"] == "kept_project_local"
    assert term["decisions"][0]["decision_type"] == "propose_project_local_term"
    assert term["effect"]["candidate_readiness_effect"] == "preview_resolves_ontology_gap"
    assert (
        term["resolved_gap_refs"][0]["decision_id"]
        == "product-ontology-decision.recurring-payment.0"
    )


def test_project_local_ontology_review_lane_requires_ready_decisions() -> None:
    module = load_module()

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions_report(ready=False),
        rerun_preview=rerun_preview(),
    )

    assert report["readiness"]["ready"] is False
    assert "ontology_decisions_not_ready" in set(report["readiness"]["blocked_by"])
    assert report["terms"][0]["status"] == "unreviewed"


def test_project_local_ontology_review_lane_accepts_advertised_bind_action() -> None:
    module = load_module()
    decisions = decisions_report()
    decision = decisions["decisions"][0]
    assert isinstance(decision, dict)
    decision["decision_type"] = "bind_existing"
    decision["ontology_ref"] = "ontology://specgraph-core/classes/Requirement"

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions,
        rerun_preview=rerun_preview(),
    )

    assert report["readiness"]["ready"] is True
    assert report["terms"][0]["status"] == "bound_existing"


def test_project_local_ontology_review_lane_blocks_authority_expansion() -> None:
    module = load_module()

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions_report(authority_expanded=True),
        rerun_preview=rerun_preview(),
    )

    assert report["readiness"]["ready"] is False
    assert "ontology_decisions_authority_expanded" in set(report["readiness"]["blocked_by"])


def test_project_local_ontology_review_lane_blocks_answer_apply_authority() -> None:
    module = load_module()
    preview = rerun_preview()
    boundary = preview["authority_boundary"]
    assert isinstance(boundary, dict)
    boundary["may_apply_answers_to_source_artifacts"] = True

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions_report(),
        rerun_preview=preview,
    )

    assert report["readiness"]["ready"] is False
    assert "rerun_preview_authority_expanded" in set(report["readiness"]["blocked_by"])


def test_project_local_ontology_review_lane_does_not_apply_project_local_aggregate_to_all() -> None:
    module = load_module()
    graph = candidate_graph()
    node = graph["nodes"][0]
    assert isinstance(node, dict)
    gaps = node["gaps"]
    assert isinstance(gaps, list)
    gaps.append(
        {
            "id": "ontology-gap.savings-buffer",
            "kind": "ontology_gap",
            "term": "Savings Buffer",
            "source_ref": "event.savings-buffer-reviewed",
            "source_kind": "domain_event",
            "statement": "Confirm whether `Savings Buffer` remains project-local.",
        }
    )
    decisions = decisions_report()
    decision = decisions["decisions"][0]
    assert isinstance(decision, dict)
    decision["target_ref"] = "candidate_graph.gaps"

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=graph,
        decisions_report=decisions,
        rerun_preview=rerun_preview(),
    )

    assert report["readiness"]["ready"] is False
    statuses_by_term = {term["term"]: term["status"] for term in report["terms"]}
    assert statuses_by_term["Recurring Payment"] == "kept_project_local"
    assert statuses_by_term["Savings Buffer"] == "unreviewed"


def test_project_local_ontology_review_lane_rejects_stale_rerun_preview_source(
    tmp_path: Path,
) -> None:
    module = load_module()
    candidate_path = tmp_path / "candidate_spec_graph.json"
    preview = rerun_preview()
    preview["source_artifacts"] = {
        "candidate_graph": {
            "artifact_kind": "candidate_spec_graph",
            "source_ref": "runs/stale_candidate_spec_graph.json",
        }
    }

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions_report(),
        rerun_preview=preview,
        candidate_graph_path=candidate_path,
    )

    assert report["readiness"]["ready"] is False
    assert "rerun_preview_candidate_graph_source_mismatch" in set(report["readiness"]["blocked_by"])
    assert report["terms"][0]["effect"]["candidate_readiness_effect"] == (
        "decision_pending_rerun_preview"
    )


def test_project_local_ontology_review_lane_uses_actual_evidence_refs(
    tmp_path: Path,
) -> None:
    module = load_module()
    candidate_path = tmp_path / "custom_candidate_spec_graph.json"
    decisions_path = tmp_path / "custom_decisions.json"
    rerun_path = tmp_path / "custom_rerun_preview.json"

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions_report(),
        rerun_preview=rerun_preview(),
        candidate_graph_path=candidate_path,
        decisions_path=decisions_path,
        rerun_preview_path=rerun_path,
    )

    refs = set(report["terms"][0]["evidence_refs"])
    assert "external:custom_candidate_spec_graph.json" in refs
    assert "external:custom_decisions.json" in refs
    assert "external:custom_rerun_preview.json" in refs


def test_project_local_ontology_review_lane_allows_reject_aggregate_target() -> None:
    module = load_module()
    decisions = decisions_report()
    decision = decisions["decisions"][0]
    assert isinstance(decision, dict)
    decision["decision_type"] = "reject_non_domain_term"
    decision["target_ref"] = "candidate_graph.gaps"
    decision.pop("term", None)

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions,
    )

    assert report["readiness"]["ready"] is True
    assert report["terms"][0]["status"] == "rejected"


def test_project_local_ontology_review_lane_warns_on_conflicting_decisions() -> None:
    module = load_module()
    decisions = decisions_report()
    second = dict(decisions["decisions"][0])
    second["id"] = "product-ontology-decision.recurring-payment.1"
    second["decision_type"] = "reject"
    decisions["decisions"].append(second)

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions,
        rerun_preview=rerun_preview(),
    )

    warning_ids = {warning["finding_id"] for warning in report["warnings"]}
    assert "project_local_ontology_conflicting_decisions_recurringpayment" in warning_ids


def test_project_local_ontology_review_lane_redacts_private_text() -> None:
    module = load_module()
    decisions = decisions_report()
    decision = decisions["decisions"][0]
    assert isinstance(decision, dict)
    decision["reason"] = "operator note in /Users/example/private.txt"

    report = module.build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph(),
        decisions_report=decisions,
    )

    assert report["terms"][0]["decisions"][0]["reason"] == "[redacted-private-text]"


def test_project_local_ontology_review_lane_cli_writes_output(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate_spec_graph.json"
    decisions_path = tmp_path / "product_ontology_gap_review_decisions.json"
    rerun_path = tmp_path / "idea_to_spec_rerun_preview.json"
    output = tmp_path / "project_local_ontology_review_lane.json"
    candidate_path.write_text(json.dumps(candidate_graph()), encoding="utf-8")
    decisions_path.write_text(json.dumps(decisions_report()), encoding="utf-8")
    rerun_path.write_text(json.dumps(rerun_preview()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--candidate-graph",
            str(candidate_path),
            "--ontology-decisions",
            str(decisions_path),
            "--rerun-preview",
            str(rerun_path),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["summary"]["status"] == "project_local_ontology_review_ready"
