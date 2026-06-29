from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "product_workspace_repair_pack.py"
IMPORT_PREVIEW_TOOL_PATH = ROOT / "tools" / "specspace_repair_draft_import_preview.py"
PACK_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "product_workspace_repair_packs"
    / "team_decision_log_happy_path_repair_pack.json"
)


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pack() -> dict[str, object]:
    return load_json(PACK_PATH)


def _repair_session() -> dict[str, object]:
    return {
        "artifact_kind": "idea_to_spec_repair_session_journal",
        "schema_version": 1,
        "proposal_id": "0171",
        "contract_ref": "specgraph.idea-to-spec.repair-session-journal.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "session": {
            "session_id": "repair-session.team-decision-log",
            "candidate_id": "team-decision-log",
            "workspace_route": "/team-decision-log",
            "workflow_lane": "product_idea_to_spec",
            "governance_profile": "product_workspace",
            "target_repository_role": "product_spec_workspace",
        },
        "source_artifacts": {
            "clarification_requests": {
                "artifact_kind": "idea_to_spec_clarification_requests",
                "contract_ref": "specgraph.idea-to-spec.clarification-requests.v0.1",
                "source_ref": "runs/idea_to_spec_clarification_requests.json",
            }
        },
        "readiness_impact": {
            "ready_for_candidate_approval": False,
            "ready_for_platform_promotion": False,
            "unresolved_ontology_gap_count": 11,
            "resolved_ontology_gap_count": 0,
        },
        "readiness": {
            "ready": True,
            "review_state": "repair_session_journal_ready",
            "blocked_by": [],
        },
        "authority_boundary": {
            "may_execute_prompt_agent": False,
            "may_apply_answers_to_source_artifacts": False,
            "may_apply_decisions_to_source_artifacts": False,
            "may_mutate_candidate_source_artifacts": False,
            "may_mutate_canonical_specs": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
            "may_create_branch_or_commit": False,
        },
        "summary": {
            "status": "repair_session_journal_ready",
            "candidate_id": "team-decision-log",
            "unresolved_ontology_gap_count": 11,
        },
    }


def _target_ref_for_request(request_id: str) -> str:
    if request_id == "clarification.repair.repair-review-unresolved-gaps":
        return "candidate_graph.gaps"
    prefix = "clarification.candidate-gap."
    assert request_id.startswith(prefix)
    raw = request_id.removeprefix(prefix)
    node_prefix, gap = raw.split("-gaps-", 1)
    node_id = node_prefix.replace("candidate-spec-", "candidate-spec.")
    gap_id = gap.replace("ontology-gap-", "ontology-gap.").replace("gap-", "gap.")
    return f"{node_id}.gaps.{gap_id}"


def _clarification_requests(pack: dict[str, object]) -> dict[str, object]:
    requests: list[dict[str, object]] = []
    for raw in pack["drafts"]:
        record = raw if isinstance(raw, dict) else {}
        request_id = str(record["request_id"])
        action = str(record["allowed_action"])
        is_ontology = action in {
            "bind_existing_term",
            "alias",
            "propose_project_local_term",
            "reject",
        } and (
            "ontology-gap" in request_id
            or request_id == "clarification.repair.repair-review-unresolved-gaps"
        )
        requests.append(
            {
                "id": request_id,
                "kind": "ontology_gap" if is_ontology else "candidate_gap",
                "severity": (
                    "blocking"
                    if request_id == "clarification.repair.repair-review-unresolved-gaps"
                    else "review_required"
                ),
                "status": "open",
                "target_artifact": "runs/candidate_spec_graph.json",
                "target_ref": _target_ref_for_request(request_id),
                "question": f"Demo repair request for {request_id}",
                "suggested_actions": (
                    [
                        "bind_existing_term",
                        "alias",
                        "propose_project_local_term",
                        "reject",
                        "defer",
                    ]
                    if is_ontology
                    else ["answer_question", "provide_candidate_context", "reject", "defer"]
                ),
            }
        )
    return {
        "artifact_kind": "idea_to_spec_clarification_requests",
        "schema_version": 1,
        "proposal_id": "0163",
        "contract_ref": "specgraph.idea-to-spec.clarification-requests.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "clarification_requests": requests,
        "readiness": {
            "ready": False,
            "review_state": "clarification_required",
            "blocked_by": ["clarification.repair.repair-review-unresolved-gaps"],
        },
        "summary": {
            "status": "clarification_required",
            "request_count": len(requests),
            "blocking_request_count": 1,
        },
    }


def test_team_decision_log_repair_pack_materializes_specspace_owned_state() -> None:
    module = load_module(TOOL_PATH, "product_workspace_repair_pack_under_test")
    pack = _pack()
    draft_state, request_state = module.build_product_workspace_repair_pack_states(
        pack=pack,
        repair_session=_repair_session(),
        clarification_requests=_clarification_requests(pack),
        pack_path=PACK_PATH,
        repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
    )

    assert draft_state["artifact_kind"] == "specspace_idea_to_spec_repair_draft_state"
    assert draft_state["summary"]["draft_count"] == 15
    assert draft_state["authority_boundary"]["canonical_mutations_allowed"] is False
    assert all(draft["mutates_canonical_specs"] is False for draft in draft_state["drafts"])
    assert request_state["artifact_kind"] == "specspace_idea_to_spec_repair_rerun_request_state"
    assert request_state["requests"][0]["accepted_for_rerun_count"] == 15
    assert request_state["summary"]["accepted_for_rerun_count"] == 15
    assert request_state["requests"][0]["may_run_make_target"] is False


def test_team_decision_log_repair_pack_import_preview_is_ready() -> None:
    pack_module = load_module(TOOL_PATH, "product_workspace_repair_pack_ready_under_test")
    preview_module = load_module(
        IMPORT_PREVIEW_TOOL_PATH,
        "specspace_repair_draft_import_preview_for_pack_under_test",
    )
    pack = _pack()
    repair_session = _repair_session()
    requests = _clarification_requests(pack)
    draft_state, _ = pack_module.build_product_workspace_repair_pack_states(
        pack=pack,
        repair_session=repair_session,
        clarification_requests=requests,
        pack_path=PACK_PATH,
        repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
    )

    preview = preview_module.build_specspace_repair_draft_import_preview(
        draft_state=draft_state,
        repair_session=repair_session,
        clarification_requests=requests,
        draft_state_path=ROOT / "runs" / "idea_to_spec_repair_drafts.json",
        repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
        clarification_requests_path=ROOT / "runs" / "idea_to_spec_clarification_requests.json",
        workspace_id="team-decision-log",
    )

    assert preview["readiness"]["ready"] is True
    assert preview["summary"]["accepted_for_rerun_count"] == 15
    assert preview["summary"]["invalid_draft_count"] == 0
    assert preview["summary"]["deferred_count"] == 0


def test_repair_pack_request_state_counts_only_unique_resolving_drafts() -> None:
    module = load_module(TOOL_PATH, "product_workspace_repair_pack_count_under_test")
    pack = _pack()
    duplicate = deepcopy(pack["drafts"][0])
    deferred = deepcopy(pack["drafts"][1])
    deferred["allowed_action"] = "defer"
    pack["drafts"].extend([duplicate, deferred])

    _, request_state = module.build_product_workspace_repair_pack_states(
        pack=pack,
        repair_session=_repair_session(),
        clarification_requests=_clarification_requests(pack),
        pack_path=PACK_PATH,
        repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
    )

    assert request_state["requests"][0]["draft_count"] == 17
    assert request_state["requests"][0]["accepted_for_rerun_count"] == 15
    assert request_state["summary"]["accepted_for_rerun_count"] == 15


def test_repair_pack_rejects_stale_repair_session_identity() -> None:
    module = load_module(TOOL_PATH, "product_workspace_repair_pack_stale_under_test")
    pack = _pack()
    stale_session = deepcopy(_repair_session())
    stale_session["session"]["session_id"] = "repair-session.other-workspace"

    try:
        module.build_product_workspace_repair_pack_states(
            pack=pack,
            repair_session=stale_session,
            clarification_requests=_clarification_requests(pack),
            pack_path=PACK_PATH,
            repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
        )
    except ValueError as error:
        assert "repair_session_id must match" in str(error)
    else:
        raise AssertionError("stale repair session identity should fail")
