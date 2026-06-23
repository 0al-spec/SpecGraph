from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "candidate_approval_decision.py"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def ready_promotion_gate() -> dict[str, object]:
    return {
        "artifact_kind": "idea_to_spec_promotion_gate",
        "canonical_mutations_allowed": False,
        "contract_ref": "specgraph.idea-to-spec.promotion-gate.v0.1",
        "proposal_id": "0154",
        "promotion_request": {
            "path_argument": "--path",
            "paths": ["runs/materialized_candidate_specs/tdl-0001.yaml"],
            "platform_artifact_kind": "platform_graph_repository_promotion_request",
        },
        "readiness": {"ready": True, "review_state": "ready_for_platform_promotion_request"},
        "schema_version": 1,
        "summary": {"promotion_path_count": 1},
        "tracked_artifacts_written": False,
    }


def ready_active_candidate(
    *, promotion_gate_ref: str = "runs/idea_to_spec_promotion_gate.json"
) -> dict[str, object]:
    return {
        "artifact_kind": "active_idea_to_spec_candidate",
        "canonical_mutations_allowed": False,
        "contract_ref": "specgraph.idea-to-spec.active-candidate-source.v0.1",
        "candidate": {
            "authority_profile": "workspace_owner_controlled",
            "candidate_id": "team-decision-log",
            "display_name": "Team Decision Log",
            "governance_profile": "product_workspace",
            "public_route": "/team-decision-log",
            "target_repository_role": "product_spec_workspace",
            "workflow_lane": "product_idea_to_spec",
        },
        "proposal_id": "0155",
        "readiness": {"ready": True, "review_state": "active_candidate_ready"},
        "schema_version": 1,
        "source_artifacts": {
            "candidate_graph": {
                "artifact_kind": "candidate_spec_graph",
                "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
                "readiness": {"ready": True},
                "sha256": "candidate-graph-digest",
                "source_ref": "runs/candidate_spec_graph.json",
            },
            "promotion_gate": {
                "artifact_kind": "idea_to_spec_promotion_gate",
                "contract_ref": "specgraph.idea-to-spec.promotion-gate.v0.1",
                "readiness": {"ready": True},
                "sha256": "promotion-gate-digest",
                "source_ref": promotion_gate_ref,
            },
        },
        "source_mode": "active_candidate",
        "summary": {"candidate_id": "team-decision-log", "promotion_path_count": 1},
        "tracked_artifacts_written": False,
    }


def write_ready_inputs(tmp_path: Path) -> tuple[Path, Path]:
    active_path = tmp_path / "runs" / "active_idea_to_spec_candidate.json"
    gate_path = tmp_path / "runs" / "idea_to_spec_promotion_gate.json"
    write_json(active_path, ready_active_candidate(promotion_gate_ref=str(gate_path)))
    write_json(gate_path, ready_promotion_gate())
    return active_path, gate_path


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def test_candidate_approval_decision_approves_ready_handoff(tmp_path: Path) -> None:
    module = load_module(TOOL_PATH, "candidate_approval_decision_ready")
    active_path, gate_path = write_ready_inputs(tmp_path)

    report = module.build_candidate_approval_decision(
        active_candidate=json.loads(active_path.read_text(encoding="utf-8")),
        promotion_gate=json.loads(gate_path.read_text(encoding="utf-8")),
        active_candidate_path=active_path,
        promotion_gate_path=gate_path,
        requested_state="approved",
        operator_ref="local_operator:egor",
        reason="Candidate is ready for promotion request creation.",
    )

    assert report["artifact_kind"] == "candidate_approval_decision"
    assert report["proposal_id"] == "0157"
    assert report["contract_ref"] == "specgraph.idea-to-spec.candidate-approval-decision.v0.1"
    assert report["canonical_mutations_allowed"] is False
    assert report["ontology_writes_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["decision"]["requested_state"] == "approved"
    assert report["decision"]["state"] == "approved"
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "promotion_request_approved"
    assert report["promotion_request"]["paths"] == [
        "runs/materialized_candidate_specs/tdl-0001.yaml"
    ]
    assert report["authority_boundary"]["agent_may_approve"] is False
    assert report["authority_boundary"]["may_create_branch_or_commit"] is False
    assert report["authority_boundary"]["may_publish_read_model"] is False
    assert report["findings"] == []
    assert {ref["source_ref"] for ref in report["evidence_refs"] if isinstance(ref, dict)} >= {
        str(active_path),
        str(gate_path),
        "runs/candidate_spec_graph.json",
    }


def test_candidate_approval_decision_downgrades_unready_approval(
    tmp_path: Path,
) -> None:
    module = load_module(TOOL_PATH, "candidate_approval_decision_unready")
    active_path, gate_path = write_ready_inputs(tmp_path)
    gate = ready_promotion_gate()
    gate["readiness"] = {"ready": False, "review_state": "idea_to_spec_promotion_blocked"}
    gate["promotion_request"] = {"paths": []}
    write_json(gate_path, gate)

    report = module.build_candidate_approval_decision(
        active_candidate=json.loads(active_path.read_text(encoding="utf-8")),
        promotion_gate=json.loads(gate_path.read_text(encoding="utf-8")),
        active_candidate_path=active_path,
        promotion_gate_path=gate_path,
        requested_state="approved",
        operator_ref="local_operator:egor",
        reason="Approve the candidate.",
    )

    assert report["decision"]["requested_state"] == "approved"
    assert report["decision"]["state"] == "needs_context"
    assert report["readiness"]["ready"] is False
    assert report["promotion_request"]["paths"] == []
    assert "promotion_gate_not_ready" in finding_ids(report)
    assert "promotion_gate_paths_missing" in finding_ids(report)
    assert "approval_requested_for_unready_handoff" in finding_ids(report)


def test_candidate_approval_decision_records_explicit_rejection(
    tmp_path: Path,
) -> None:
    module = load_module(TOOL_PATH, "candidate_approval_decision_rejected")
    active_path, gate_path = write_ready_inputs(tmp_path)

    report = module.build_candidate_approval_decision(
        active_candidate=json.loads(active_path.read_text(encoding="utf-8")),
        promotion_gate=json.loads(gate_path.read_text(encoding="utf-8")),
        active_candidate_path=active_path,
        promotion_gate_path=gate_path,
        requested_state="rejected",
        operator_ref="local_operator:egor",
        reason="Scope still needs owner review.",
    )

    assert report["decision"]["state"] == "rejected"
    assert report["readiness"]["ready"] is False
    assert report["readiness"]["review_state"] == "candidate_promotion_rejected"
    assert report["readiness"]["blocked_by"] == ["decision_rejected"]
    assert report["promotion_request"]["paths"] == []


def test_candidate_approval_decision_rejects_private_operator_text(
    tmp_path: Path,
) -> None:
    module = load_module(TOOL_PATH, "candidate_approval_decision_private_text")
    active_path, gate_path = write_ready_inputs(tmp_path)

    report = module.build_candidate_approval_decision(
        active_candidate=json.loads(active_path.read_text(encoding="utf-8")),
        promotion_gate=json.loads(gate_path.read_text(encoding="utf-8")),
        active_candidate_path=active_path,
        promotion_gate_path=gate_path,
        requested_state="approved",
        operator_ref="local_operator:egor",
        reason="See /Users/egor/private-notes.md",
    )

    assert report["decision"]["state"] == "needs_context"
    assert report["readiness"]["ready"] is False
    assert "reason_contains_private_marker" in finding_ids(report)


def test_candidate_approval_decision_cli_strict_fails_without_approval(
    tmp_path: Path,
) -> None:
    active_path, gate_path = write_ready_inputs(tmp_path)
    output = tmp_path / "candidate_approval_decision.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--active-candidate",
            str(active_path),
            "--promotion-gate",
            str(gate_path),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["decision"]["state"] == "needs_context"
    assert report["readiness"]["ready"] is False
    assert report["readiness"]["blocked_by"] == ["decision_needs_context"]
