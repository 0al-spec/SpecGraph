from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "candidate_overview.py"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location("candidate_overview_under_test", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def authority_boundary(**overrides: bool) -> dict[str, bool]:
    boundary = {
        "may_execute_prompt_agent": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_accept_ontology_terms": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
    }
    boundary.update(overrides)
    return boundary


def intake() -> dict[str, object]:
    return {
        "artifact_kind": "idea_event_storming_intake",
        "contract_ref": "specgraph.idea-to-spec.event-storming-intake.v0.1",
        "schema_version": 1,
        "source_intake": {
            "workspace": {
                "candidate_id": "cash-flow-control",
                "display_name": "Cash Flow Control",
                "public_route": "/cash-flow-control",
            }
        },
        "root_intent": {
            "summary": "Track recurring payments and prevent overspending before bills clear.",
            "raw_intent_text": "private local raw idea from /Users/egor/tmp/raw.txt",
        },
        "event_storming": {
            "actors": [{"id": "actor.user", "name": "Budget Owner", "role": "primary"}],
            "commands": [
                {
                    "id": "command.record-payment",
                    "name": "Record Payment",
                    "actor_refs": ["actor.user"],
                    "produces_event_refs": ["event.payment-recorded"],
                }
            ],
            "domain_events": [
                {
                    "id": "event.payment-recorded",
                    "name": "Payment Recorded",
                    "actor_refs": ["actor.user"],
                }
            ],
            "policies": [],
            "constraints": [],
        },
        "summary": {"status": "ready_for_candidate_graph"},
        "authority_boundary": authority_boundary(),
    }


def candidate_graph(
    *,
    repaired: bool = False,
    write_capable: bool = False,
    top_level_write_capable: bool = False,
    candidate_id: str = "cash-flow-control",
) -> dict[str, object]:
    return {
        "artifact_kind": "candidate_spec_graph",
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "schema_version": 1,
        "source_intake": {
            "workspace": {
                "candidate_id": candidate_id,
                "display_name": "Cash Flow Control",
            }
        },
        "canonical_mutations_allowed": top_level_write_capable,
        "tracked_artifacts_written": False,
        "nodes": [
            {
                "id": "candidate-spec.product-boundary",
                "kind": "product_spec_boundary",
                "title": "Cash Flow Product Boundary",
                "description": "Track recurring payments and prevent overspending.",
                "source_event_refs": ["actor.user", "command.record-payment"],
                "requirements": [{"id": "req.boundary"}],
                "acceptance_criteria": [{"id": "ac.boundary"}],
                "gaps": (
                    [] if repaired else [{"id": "ontology-gap.payment", "kind": "ontology_gap"}]
                ),
            },
            {
                "id": "candidate-spec.record-payment",
                "kind": "command_spec",
                "title": "Record Payment",
                "source_event_refs": ["command.record-payment", "event.payment-recorded"],
                "requirements": [{"id": "req.record-payment"}],
                "acceptance_criteria": [{"id": "ac.record-payment"}],
                "gaps": [],
            },
        ],
        "edges": [
            {
                "id": "edge.actor-user.record-payment",
                "relation": "actor_triggers_command",
                "from": "candidate-spec.product-boundary",
                "to": "candidate-spec.record-payment",
                "source_event_refs": ["actor.user", "command.record-payment"],
            },
            {
                "id": "edge.record-payment.payment-recorded",
                "relation": "command_emits_event",
                "from": "candidate-spec.record-payment",
                "to": "candidate-spec.record-payment",
                "source_event_refs": ["command.record-payment", "event.payment-recorded"],
            },
        ],
        "summary": {
            "status": "ready_for_pre_sib",
            "node_count": 2,
            "edge_count": 2,
            "gap_count": 0 if repaired else 1,
        },
        "authority_boundary": authority_boundary(
            may_mutate_canonical_specs=write_capable,
        ),
    }


def maturity() -> dict[str, object]:
    return {
        "artifact_kind": "idea_maturity_metrics_report",
        "contract_ref": "specgraph.idea-to-spec.maturity-metrics-report.v0.1",
        "schema_version": 1,
        "status": "ready",
        "candidate": {"candidate_id": "cash-flow-control"},
        "summary": {
            "lifecycle_state": "approval_ready",
            "candidate_approval_state": "ready",
            "platform_promotion_state": "not_reached",
            "remaining_blocker_count": 0,
            "ontology_gap_unresolved_count": 0,
            "candidate_gap_unresolved_count": 0,
            "project_local_ontology_review_status": "ready",
        },
        "readiness_explainers": [],
        "authority_boundary": authority_boundary(),
    }


def repaired_repair_session() -> dict[str, object]:
    return {
        "artifact_kind": "idea_to_spec_repair_session_journal",
        "contract_ref": "specgraph.idea-to-spec.repair-session-journal.v0.1",
        "schema_version": 1,
        "summary": {
            "status": "repair_session_journal_ready",
            "accepted_answer_count": 4,
            "ready_for_candidate_approval": True,
            "ready_for_platform_promotion": False,
            "resolved_ontology_gap_count": 3,
            "unresolved_ontology_gap_count": 0,
            "resolved_candidate_gap_count": 1,
            "unresolved_candidate_gap_count": 0,
        },
        "authority_boundary": authority_boundary(),
    }


def project_local_lane() -> dict[str, object]:
    return {
        "artifact_kind": "project_local_ontology_review_lane",
        "contract_ref": "specgraph.product-ontology.project-local-review-lane.v0.1",
        "schema_version": 1,
        "terms": [
            {
                "term": "Recurring Payment",
                "term_key": "recurringpayment",
                "status": "kept_project_local",
            }
        ],
        "summary": {
            "status": "project_local_ontology_review_ready",
            "term_count": 1,
            "reviewed_term_count": 1,
            "unreviewed_term_count": 0,
        },
        "authority_boundary": authority_boundary(),
    }


def project_local_effect() -> dict[str, object]:
    return {
        "artifact_kind": "project_local_ontology_decision_effect_report",
        "contract_ref": "specgraph.product-ontology.project-local-decision-effect.v0.1",
        "schema_version": 1,
        "summary": {
            "status": "project_local_ontology_decision_effect_ready",
            "accepted_decision_count": 1,
            "blocking_decision_count": 0,
        },
        "decision_effects": [
            {
                "term": "Recurring Payment",
                "term_key": "recurringpayment",
                "status": "accepted_for_project_local_preview",
                "review_action": "keep_project_local",
                "maturity_effect": "resolves_project_local_review",
                "evidence_refs": [
                    "runs/project_local_ontology_review_decisions.json",
                    "candidate-spec.product-boundary.gaps.ontology-gap.payment",
                ],
                "writes_ontology_package": False,
                "accepts_ontology_terms": False,
            }
        ],
        "source_artifacts": {
            "project_local_ontology_review_lane": {
                "artifact_kind": "project_local_ontology_review_lane",
                "status": "present",
                "summary": {
                    "status": "project_local_ontology_review_ready",
                    "term_count": 1,
                    "reviewed_term_count": 1,
                    "unreviewed_term_count": 0,
                },
            }
        },
        "authority_boundary": authority_boundary(),
    }


def build_overview(**overrides: object) -> dict[str, object]:
    module = load_module()
    return module.build_candidate_overview(
        intake=overrides.get("intake", intake()),
        candidate_graph=overrides.get("candidate_graph", candidate_graph()),
        repaired_candidate_graph=overrides.get(
            "repaired_candidate_graph", candidate_graph(repaired=True)
        ),
        repaired_repair_session=overrides.get("repaired_repair_session", repaired_repair_session()),
        maturity=overrides.get("maturity", maturity()),
        project_local_ontology_lane=overrides.get(
            "project_local_ontology_lane", project_local_lane()
        ),
        project_local_ontology_effect=overrides.get(
            "project_local_ontology_effect", project_local_effect()
        ),
        source_artifacts=overrides.get(
            "source_artifacts",
            {
                "intake": {
                    "status": "present",
                    "artifact_kind": "idea_event_storming_intake",
                },
                "candidate_graph": {
                    "status": "present",
                    "artifact_kind": "candidate_spec_graph",
                },
            },
        ),
    )


def test_candidate_overview_builds_public_safe_narrative() -> None:
    overview = build_overview()

    assert overview["artifact_kind"] == "candidate_overview"
    assert overview["readiness"]["ready"] is True
    assert overview["summary"]["candidate_id"] == "cash-flow-control"
    assert overview["summary"]["graph_source"] == "repaired_candidate_graph"
    assert overview["sections"]["topology"]["workflow_edge_count"] == 2
    assert overview["sections"]["repair"]["ready_for_candidate_approval"] is True
    assert overview["sections"]["project_local_ontology"]["accepted_decision_count"] == 1
    assert (
        overview["sections"]["project_local_ontology"]["terms"][0]["effective_status"]
        == "reviewed_by_project_local_decision"
    )
    serialized = json.dumps(overview)
    assert "raw_intent_text" not in serialized
    assert "/Users/egor" not in serialized


def test_candidate_overview_uses_project_local_effect_as_effective_review_status() -> None:
    lane = project_local_lane()
    lane["summary"]["status"] = "project_local_ontology_review_required"
    lane["summary"]["reviewed_term_count"] = 1
    lane["summary"]["unreviewed_term_count"] = 3
    effect = project_local_effect()
    effect["source_artifacts"]["project_local_ontology_review_lane"]["summary"] = lane["summary"]

    overview = build_overview(
        project_local_ontology_lane=lane,
        project_local_ontology_effect=effect,
    )

    ontology = overview["sections"]["project_local_ontology"]
    assert ontology["lane_status"] == "project_local_ontology_review_required"
    assert ontology["effect_status"] == "project_local_ontology_decision_effect_ready"
    assert ontology["effect_matches_lane"] is True
    assert ontology["review_status"] == "project_local_ontology_decision_effect_ready"
    assert (
        overview["summary"]["project_local_ontology_review_status"]
        == "project_local_ontology_decision_effect_ready"
    )


def test_candidate_overview_ignores_stale_project_local_effect() -> None:
    lane = project_local_lane()
    lane["summary"]["status"] = "project_local_ontology_review_required"
    lane["summary"]["reviewed_term_count"] = 0
    lane["summary"]["unreviewed_term_count"] = 1
    lane["terms"][0]["status"] = "unreviewed"

    overview = build_overview(project_local_ontology_lane=lane)

    ontology = overview["sections"]["project_local_ontology"]
    assert ontology["lane_status"] == "project_local_ontology_review_required"
    assert ontology["raw_effect_status"] == "project_local_ontology_decision_effect_ready"
    assert ontology["effect_status"] == "missing"
    assert ontology["effect_matches_lane"] is False
    assert ontology["review_status"] == "project_local_ontology_review_required"
    assert ontology["terms"][0]["effective_status"] == "unreviewed"


def test_candidate_overview_does_not_mark_deferred_effect_as_reviewed() -> None:
    lane = project_local_lane()
    lane["summary"]["status"] = "project_local_ontology_review_required"
    lane["summary"]["reviewed_term_count"] = 0
    lane["summary"]["unreviewed_term_count"] = 1
    lane["terms"][0]["status"] = "unreviewed"
    effect = project_local_effect()
    effect["summary"]["status"] = "project_local_ontology_decision_effect_review_required"
    effect["summary"]["accepted_decision_count"] = 0
    effect["summary"]["blocking_decision_count"] = 0
    effect["decision_effects"][0]["status"] = "non_resolving"
    effect["decision_effects"][0]["review_action"] = "defer"
    effect["decision_effects"][0]["maturity_effect"] = "requires_owner_follow_up"
    effect["source_artifacts"]["project_local_ontology_review_lane"]["summary"] = lane["summary"]

    overview = build_overview(
        project_local_ontology_lane=lane,
        project_local_ontology_effect=effect,
    )

    ontology = overview["sections"]["project_local_ontology"]
    assert ontology["effect_status"] == "project_local_ontology_decision_effect_review_required"
    assert ontology["effect_matches_lane"] is True
    assert ontology["terms"][0]["effective_status"] == "unreviewed"
    assert ontology["terms"][0]["review_effect"]["review_action"] == "defer"


def test_candidate_overview_uses_standard_graph_when_repaired_graph_missing() -> None:
    overview = build_overview(repaired_candidate_graph={})

    assert overview["summary"]["graph_source"] == "candidate_graph"
    assert overview["sections"]["candidate_nodes"]["items"][0]["ontology_gap_count"] == 1


def test_candidate_overview_blocks_source_authority_expansion() -> None:
    overview = build_overview(candidate_graph=candidate_graph(write_capable=True))

    assert overview["readiness"]["ready"] is False
    assert any(
        finding["finding_id"] == "candidate_overview_source_authority_expansion"
        for finding in overview["findings"]
    )


def test_candidate_overview_blocks_top_level_source_authority_expansion() -> None:
    overview = build_overview(candidate_graph=candidate_graph(top_level_write_capable=True))

    assert overview["readiness"]["ready"] is False
    assert any(
        finding["finding_id"] == "candidate_overview_source_authority_expansion"
        and "candidate_graph.canonical_mutations_allowed" in finding["evidence"]["fields"]
        for finding in overview["findings"]
    )


def test_candidate_overview_blocks_wrong_required_source_artifact_kind() -> None:
    overview = build_overview(
        source_artifacts={
            "intake": {
                "status": "present",
                "artifact_kind": "idea_event_storming_intake",
            },
            "candidate_graph": {
                "status": "present",
                "artifact_kind": "idea_maturity_metrics_report",
            },
        }
    )

    assert overview["readiness"]["ready"] is False
    assert any(
        finding["finding_id"] == "candidate_overview_source_wrong_artifact_kind"
        and finding["evidence"]["artifact_key"] == "candidate_graph"
        for finding in overview["findings"]
    )


def test_candidate_overview_requires_repaired_graph_candidate_provenance() -> None:
    repaired_graph = candidate_graph(repaired=True)
    repaired_graph.pop("source_intake")

    overview = build_overview(repaired_candidate_graph=repaired_graph)

    assert overview["readiness"]["ready"] is False
    assert overview["summary"]["graph_source"] == "candidate_graph"
    assert any(
        finding["finding_id"] == "candidate_overview_repaired_graph_provenance_missing"
        for finding in overview["findings"]
    )


def test_candidate_overview_rejects_stale_repaired_graph_candidate() -> None:
    overview = build_overview(
        repaired_candidate_graph=candidate_graph(
            repaired=True,
            candidate_id="stale-candidate",
        )
    )

    assert overview["readiness"]["ready"] is False
    assert overview["summary"]["graph_source"] == "candidate_graph"
    assert any(
        finding["finding_id"] == "candidate_overview_repaired_graph_candidate_mismatch"
        for finding in overview["findings"]
    )


def test_candidate_overview_does_not_let_handoff_override_selected_session() -> None:
    repair_session = repaired_repair_session()
    repair_session["summary"]["ready_for_candidate_approval"] = False
    handoff = {
        "artifact_kind": "repaired_candidate_promotion_handoff_report",
        "summary": {"ready_for_candidate_approval": True},
        "authority_boundary": authority_boundary(),
    }

    overview = build_overview(
        repaired_repair_session=repair_session,
        repaired_handoff=handoff,
    )

    assert overview["sections"]["repair"]["ready_for_candidate_approval"] is False
    assert overview["next_action"]["action_id"] == "continue_repair_loop"


def test_candidate_overview_sanitizes_final_candidate_narrative_fields() -> None:
    unsafe_intake = intake()
    workspace = unsafe_intake["source_intake"]["workspace"]
    assert isinstance(workspace, dict)
    workspace["display_name"] = "Bearer secret product"
    workspace["public_route"] = "/Users/egor/private-product"
    unsafe_intake["root_intent"]["summary"] = "Use token=secret in /Users/egor/raw.txt"

    overview = build_overview(intake=unsafe_intake)
    serialized = json.dumps(overview)

    assert "Bearer secret product" not in serialized
    assert "/Users/egor" not in serialized
    assert "token=secret" not in serialized
    assert overview["candidate"]["display_name"] == "[redacted-private-text]"
    assert overview["narrative"]["product_intent"] == "[redacted-private-text]"


def test_candidate_overview_cli_writes_output(tmp_path: Path) -> None:
    paths = {
        "intake": tmp_path / "idea_event_storming_intake.json",
        "candidate": tmp_path / "candidate_spec_graph.json",
        "maturity": tmp_path / "idea_maturity_metrics_report.json",
        "repair": tmp_path / "repaired_idea_to_spec_repair_session.json",
        "lane": tmp_path / "project_local_ontology_review_lane.json",
        "effect": tmp_path / "project_local_ontology_decision_effect_report.json",
        "output": tmp_path / "candidate_overview.json",
    }
    write_json(paths["intake"], intake())
    write_json(paths["candidate"], candidate_graph(repaired=True))
    write_json(paths["maturity"], maturity())
    write_json(paths["repair"], repaired_repair_session())
    write_json(paths["lane"], project_local_lane())
    write_json(paths["effect"], project_local_effect())

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--intake",
            str(paths["intake"]),
            "--candidate-graph",
            str(paths["candidate"]),
            "--repaired-candidate-graph",
            str(tmp_path / "missing_repaired_graph.json"),
            "--repaired-repair-session",
            str(paths["repair"]),
            "--idea-maturity",
            str(paths["maturity"]),
            "--project-local-ontology-lane",
            str(paths["lane"]),
            "--project-local-ontology-effect",
            str(paths["effect"]),
            "--output",
            str(paths["output"]),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert payload["summary"]["status"] == "candidate_overview_ready"


def test_candidate_overview_strict_cli_rejects_wrong_candidate_graph_kind(
    tmp_path: Path,
) -> None:
    intake_path = tmp_path / "idea_event_storming_intake.json"
    candidate_path = tmp_path / "candidate_spec_graph.json"
    output_path = tmp_path / "candidate_overview.json"
    write_json(intake_path, intake())
    write_json(candidate_path, maturity())

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--intake",
            str(intake_path),
            "--candidate-graph",
            str(candidate_path),
            "--repaired-candidate-graph",
            str(tmp_path / "missing_repaired_graph.json"),
            "--repair-session",
            str(tmp_path / "missing_repair_session.json"),
            "--repaired-repair-session",
            str(tmp_path / "missing_repaired_repair_session.json"),
            "--idea-maturity",
            str(tmp_path / "missing_maturity.json"),
            "--project-local-ontology-lane",
            str(tmp_path / "missing_lane.json"),
            "--project-local-ontology-effect",
            str(tmp_path / "missing_effect.json"),
            "--repaired-handoff",
            str(tmp_path / "missing_handoff.json"),
            "--output",
            str(output_path),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["readiness"]["ready"] is False
    assert any(
        finding["finding_id"] == "candidate_overview_source_wrong_artifact_kind"
        for finding in payload["findings"]
    )
