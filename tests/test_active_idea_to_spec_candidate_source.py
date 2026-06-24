from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "active_idea_to_spec_candidate_source.py"


@pytest.fixture()
def module() -> object:
    spec = importlib.util.spec_from_file_location("active_candidate_source_under_test", TOOL_PATH)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_ready_artifacts(
    root: Path,
    *,
    candidate_id: str = "team-decision-log",
    include_source_intake: bool = True,
    project: str = "TeamDecisionLog",
    domain_ref: str = "domain.team_decision_log",
) -> dict[str, str]:
    runs = root / "runs"
    artifacts = {
        "intake": "runs/idea_event_storming_intake.json",
        "candidate_graph": "runs/candidate_spec_graph.json",
        "pre_sib": "runs/pre_sib_coherence_report.json",
        "repair_loop": "runs/candidate_repair_loop_report.json",
        "materialization": "runs/candidate_spec_materialization_report.json",
        "promotion_gate": "runs/idea_to_spec_promotion_gate.json",
    }
    write_json(
        runs / "idea_event_storming_intake.json",
        {
            "artifact_kind": "idea_event_storming_intake",
            "canonical_mutations_allowed": False,
            "contract_ref": "specgraph.idea-to-spec.event-storming-intake.v0.1",
            "candidate_graph_readiness": {"ready": True, "review_state": "ready"},
            "schema_version": 1,
            **(
                {
                    "source_intake": {
                        "workspace": {
                            "candidate_id": candidate_id,
                            "display_name": "".join(
                                part[:1].upper() + part[1:] for part in candidate_id.split("-")
                            ),
                            "public_route": f"/{candidate_id}",
                        }
                    },
                }
                if include_source_intake
                else {}
            ),
            "source_ref": f"product://{candidate_id}/root-intent",
            "tracked_artifacts_written": False,
        },
    )
    write_json(
        runs / "candidate_spec_graph.json",
        {
            "active_frame": {
                "context_refs": ["context.idea_to_spec"],
                "domain_refs": [domain_ref],
                "ontology_refs": ["ontology://specgraph-core"],
                "project": project,
            },
            "artifact_kind": "candidate_spec_graph",
            "canonical_mutations_allowed": False,
            "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
            "pre_sib_readiness": {"ready": True, "review_state": "ready"},
            "schema_version": 1,
            "source_intake": {"source_ref": f"product://{candidate_id}/root-intent"},
            "source_ref": f"product://{candidate_id}/candidate-spec-graph-seed",
            "tracked_artifacts_written": False,
        },
    )
    write_json(
        runs / "pre_sib_coherence_report.json",
        {
            "artifact_kind": "pre_sib_coherence_report",
            "canonical_mutations_allowed": False,
            "contract_ref": "specgraph.idea-to-spec.pre-sib-coherence-report.v0.1",
            "readiness": {"ready": False, "review_state": "pre_sib_review_required"},
            "schema_version": 1,
            "tracked_artifacts_written": False,
        },
    )
    write_json(
        runs / "candidate_repair_loop_report.json",
        {
            "artifact_kind": "candidate_repair_loop_report",
            "canonical_mutations_allowed": False,
            "contract_ref": "specgraph.idea-to-spec.candidate-repair-loop.v0.1",
            "readiness": {"ready": True, "review_state": "repair_preview_ready"},
            "schema_version": 1,
            "tracked_artifacts_written": False,
        },
    )
    write_json(
        runs / "candidate_spec_materialization_report.json",
        {
            "artifact_kind": "candidate_spec_materialization_report",
            "canonical_mutations_allowed": False,
            "contract_ref": "specgraph.idea-to-spec.candidate-spec-materialization.v0.1",
            "materialization_source": "repair_loop_preview",
            "readiness": {"ready": True, "review_state": "materialized_candidate_review_ready"},
            "schema_version": 1,
            "summary": {"materialized_file_count": 3},
            "tracked_artifacts_written": False,
        },
    )
    write_json(
        runs / "idea_to_spec_promotion_gate.json",
        {
            "artifact_kind": "idea_to_spec_promotion_gate",
            "canonical_mutations_allowed": False,
            "contract_ref": "specgraph.idea-to-spec.promotion-gate.v0.1",
            "readiness": {"ready": True, "review_state": "ready_for_platform_promotion_request"},
            "schema_version": 1,
            "summary": {"promotion_path_count": 3},
            "tracked_artifacts_written": False,
        },
    )
    return artifacts


def ready_config(
    artifacts: dict[str, str],
    *,
    candidate_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    candidate = {
        "authority_profile": "workspace_owner_controlled",
        "candidate_id": "team-decision-log",
        "display_name": "Team Decision Log",
        "governance_profile": "product_workspace",
        "public_route": "/team-decision-log",
        "source_mode": "active_candidate",
        "target_repository_role": "product_spec_workspace",
        "workflow_lane": "product_idea_to_spec",
    }
    if candidate_overrides:
        candidate.update(candidate_overrides)
    return {
        "artifact_kind": "active_idea_to_spec_candidate_source_config",
        "artifacts": artifacts,
        "candidate": candidate,
        "contract_ref": "specgraph.idea-to-spec.active-candidate-source-config.v0.1",
        "schema_version": 1,
    }


def test_active_candidate_source_builds_ready_report(
    tmp_path: Path,
    module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    artifacts = write_ready_artifacts(tmp_path)

    report = module.build_active_idea_to_spec_candidate_source(ready_config(artifacts))

    assert report["artifact_kind"] == "active_idea_to_spec_candidate"
    assert report["source_mode"] == "active_candidate"
    assert report["readiness"]["ready"] is True
    assert report["candidate"]["target_repository_role"] == "product_spec_workspace"
    assert report["summary"]["promotion_path_count"] == 3
    assert "pre_sib_findings_repaired_by_preview" in {
        warning["finding_id"] for warning in report["warnings"]
    }
    assert report["source_artifacts"]["promotion_gate"]["sha256"]


def test_active_candidate_source_accepts_different_product_candidate_from_config(
    tmp_path: Path,
    module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    artifacts = write_ready_artifacts(
        tmp_path,
        candidate_id="support-triage-log",
        project="SupportTriageLog",
        domain_ref="domain.support_triage_log",
    )
    config = ready_config(
        artifacts,
        candidate_overrides={
            "candidate_id": "support-triage-log",
            "display_name": "Support Triage Log",
            "public_route": "/support-triage-log",
        },
    )

    report = module.build_active_idea_to_spec_candidate_source(config)

    assert report["readiness"]["ready"] is True
    assert report["candidate"]["candidate_id"] == "support-triage-log"
    assert report["candidate"]["display_name"] == "Support Triage Log"
    assert report["candidate"]["public_route"] == "/support-triage-log"
    assert report["summary"]["candidate_id"] == "support-triage-log"


def test_active_candidate_source_derives_candidate_metadata_from_intake(
    tmp_path: Path,
    module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    artifacts = write_ready_artifacts(
        tmp_path,
        candidate_id="support-triage-log",
        project="SupportTriageLog",
        domain_ref="domain.support_triage_log",
    )
    config = ready_config(artifacts)
    config.pop("candidate")

    report = module.build_active_idea_to_spec_candidate_source(config)

    assert report["readiness"]["ready"] is True
    assert report["source_mode"] == "active_candidate"
    assert {finding["finding_id"] for finding in report["findings"]}.isdisjoint(
        {
            "candidate_source_mode_unsupported",
            "candidate_workflow_lane_unsupported",
            "candidate_governance_profile_unsupported",
            "candidate_target_repository_role_unsupported",
            "candidate_authority_profile_unsupported",
        }
    )
    assert report["candidate"]["candidate_id"] == "support-triage-log"
    assert report["candidate"]["display_name"] == "SupportTriageLog"
    assert report["candidate"]["public_route"] == "/support-triage-log"
    assert report["candidate"]["governance_profile"] == "product_workspace"
    assert report["candidate"]["target_repository_role"] == "product_spec_workspace"
    assert report["candidate"]["authority_profile"] == "workspace_owner_controlled"
    assert report["summary"]["candidate_id"] == "support-triage-log"


def test_active_candidate_source_derives_candidate_metadata_from_legacy_intake_source_ref(
    tmp_path: Path,
    module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    artifacts = write_ready_artifacts(
        tmp_path,
        candidate_id="support-triage-log",
        include_source_intake=False,
        project="SupportTriageLog",
        domain_ref="domain.support_triage_log",
    )
    config = ready_config(artifacts)
    config.pop("candidate")

    report = module.build_active_idea_to_spec_candidate_source(config)

    assert report["readiness"]["ready"] is True
    assert report["candidate"]["candidate_id"] == "support-triage-log"
    assert report["candidate"]["display_name"] == "Support Triage Log"
    assert report["candidate"]["public_route"] == "/support-triage-log"
    assert report["candidate"]["target_repository_role"] == "product_spec_workspace"


def test_active_candidate_source_rejects_stale_artifacts_for_different_product(
    tmp_path: Path,
    module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    artifacts = write_ready_artifacts(tmp_path)
    config = ready_config(
        artifacts,
        candidate_overrides={
            "candidate_id": "support-triage-log",
            "display_name": "Support Triage Log",
            "public_route": "/support-triage-log",
        },
    )

    report = module.build_active_idea_to_spec_candidate_source(config)

    assert report["readiness"]["ready"] is False
    finding_ids = {finding["finding_id"] for finding in report["findings"]}
    assert "active_candidate_project_mismatch" in finding_ids
    assert "active_candidate_domain_mismatch" in finding_ids
    assert "active_candidate_source_ref_mismatch" in finding_ids


def test_active_candidate_source_rejects_unnormalized_candidate_metadata(
    tmp_path: Path,
    module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    artifacts = write_ready_artifacts(tmp_path)
    config = ready_config(
        artifacts,
        candidate_overrides={
            "candidate_id": " team-decision-log ",
            "display_name": " Team Decision Log ",
            "public_route": " /team-decision-log ",
        },
    )

    report = module.build_active_idea_to_spec_candidate_source(config)

    assert report["readiness"]["ready"] is False
    assert report["candidate"]["candidate_id"] == "team-decision-log"
    assert report["candidate"]["display_name"] == "Team Decision Log"
    assert report["candidate"]["public_route"] == "/team-decision-log"
    finding_ids = {finding["finding_id"] for finding in report["findings"]}
    assert "candidate_candidate_id_not_normalized" in finding_ids
    assert "candidate_display_name_not_normalized" in finding_ids
    assert "candidate_public_route_not_normalized" in finding_ids


@pytest.mark.parametrize(
    "public_route",
    ["/../admin", "/foo/../bar", "/./admin", "/%2e%2e/admin", "/foo/%2E/bar"],
)
def test_active_candidate_source_rejects_unsafe_public_route_segments(
    tmp_path: Path,
    module: object,
    monkeypatch: pytest.MonkeyPatch,
    public_route: str,
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    artifacts = write_ready_artifacts(tmp_path)
    config = ready_config(artifacts, candidate_overrides={"public_route": public_route})

    report = module.build_active_idea_to_spec_candidate_source(config)

    assert report["readiness"]["ready"] is False
    assert "candidate_public_route_unsafe_segment" in {
        finding["finding_id"] for finding in report["findings"]
    }


def test_active_candidate_source_rejects_public_placeholder(
    tmp_path: Path,
    module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    artifacts = write_ready_artifacts(tmp_path)
    materialization_path = tmp_path / "runs" / "candidate_spec_materialization_report.json"
    materialization = json.loads(materialization_path.read_text(encoding="utf-8"))
    materialization["source_mode"] = "public_placeholder"
    materialization["placeholder_reason"] = "no_active_candidate"
    write_json(materialization_path, materialization)

    report = module.build_active_idea_to_spec_candidate_source(ready_config(artifacts))

    assert report["readiness"]["ready"] is False
    assert "materialization_is_public_placeholder" in {
        finding["finding_id"] for finding in report["findings"]
    }


def test_active_candidate_source_rejects_bootstrap_repository_role(
    tmp_path: Path,
    module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    artifacts = write_ready_artifacts(tmp_path)
    config = ready_config(artifacts)
    config["candidate"]["target_repository_role"] = "specgraph_bootstrap"

    report = module.build_active_idea_to_spec_candidate_source(config)

    assert report["readiness"]["ready"] is False
    assert "candidate_target_repository_role_unsupported" in {
        finding["finding_id"] for finding in report["findings"]
    }
