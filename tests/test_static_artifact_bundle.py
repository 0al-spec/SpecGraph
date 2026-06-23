from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def bundle_module() -> object:
    module_path = Path(__file__).resolve().parents[1] / "tools" / "build_static_artifact_bundle.py"
    spec = importlib.util.spec_from_file_location("test_static_artifact_bundle_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_repo(root: Path) -> Path:
    specs_dir = root / "specs" / "nodes"
    runs_dir = root / "runs"
    specs_dir.mkdir(parents=True)
    runs_dir.mkdir(parents=True)
    (specs_dir / "SG-SPEC-0001.yaml").write_text(
        "\n".join(
            [
                "id: SG-SPEC-0001",
                "title: Root",
                "kind: spec",
                "status: linked",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    artifacts = {
        "graph_dashboard.json": {"artifact_kind": "graph_dashboard"},
        "graph_backlog_projection.json": {"artifact_kind": "graph_backlog_projection"},
        "graph_next_moves.json": {"artifact_kind": "graph_next_moves"},
        "implementation_work_index.json": {"artifact_kind": "implementation_work_index"},
        "spec_activity_feed.json": {"artifact_kind": "spec_activity_feed"},
        "supervisor_executor_adapter_index.json": {
            "artifact_kind": "supervisor_executor_adapter_index",
            "summary": {"agent_passport_cli_status": "available"},
        },
        "agent_surface_index.json": {"artifact_kind": "agent_surface_index"},
        "known_agent_passport_index.json": {"artifact_kind": "known_agent_passport_index"},
        "agent_passport_verification_report.json": {
            "artifact_kind": "agent_passport_verification_report",
            "summary": {
                "entry_count": 5,
                "valid_count": 5,
                "tool_unavailable_count": 0,
                "agent_passport_cli_status": "available",
            },
        },
        "agent_verification_gap_index.json": {
            "artifact_kind": "agent_verification_gap_index",
            "summary": {
                "verification_tool_unavailable_count": 0,
                "verification_not_attempted_count": 0,
                "agent_passport_cli_status": "available",
            },
        },
        "agent_runtime_enforcement_evidence_index.json": {
            "artifact_kind": "agent_runtime_enforcement_evidence_index"
        },
        "external_consumer_evidence_index.json": {
            "artifact_kind": "external_consumer_evidence_index",
            "entry_count": 5,
            "accepted_count": 5,
        },
        "ontology_semantic_review_surface.json": {
            "artifact_kind": "ontology_semantic_review_surface"
        },
        "ontology_review_dashboard.json": {"artifact_kind": "ontology_review_dashboard"},
        "ontology_decision_import_preview.json": {
            "artifact_kind": "ontology_decision_import_preview"
        },
        "ontology_package_index.json": {
            "artifact_kind": "ontology_package_index",
            "packages": [],
        },
        "ontology_gap_review_workflow.json": {
            "artifact_kind": "ontology_gap_review_workflow",
        },
        "legacy_spec_ontology_backfill_plan.json": {
            "artifact_kind": "legacy_spec_ontology_backfill_plan",
        },
        "ontology_owner_decision_import_v2.json": {
            "artifact_kind": "ontology_owner_decision_import_v2",
        },
        "spec_ontology_binding_index.json": {
            "artifact_kind": "spec_ontology_binding_index",
        },
        "spec_ontology_validation_report.json": {
            "artifact_kind": "spec_ontology_validation_report",
        },
        "specauthor_invocation_artifact.json": {
            "artifact_kind": "specauthor_invocation_artifact",
        },
        "specauthor_invocation_artifact_contract_report.json": {
            "artifact_kind": "specauthor_invocation_artifact_contract_report",
        },
        "specauthor_authoring_flow_report.json": {
            "artifact_kind": "specauthor_authoring_flow_report",
        },
        "candidate_spec_materialization_report.json": {
            "artifact_kind": "candidate_spec_materialization_report",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "readiness": {"ready": True},
        },
        "idea_to_spec_promotion_gate.json": {
            "artifact_kind": "idea_to_spec_promotion_gate",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "readiness": {"ready": True},
        },
    }
    for name, payload in artifacts.items():
        write_json(runs_dir / name, payload)
    write_json(
        runs_dir / "agent_runtime_enforcement_evidence" / "supervisor-executor-adapter-smoke.json",
        {"artifact_kind": "agent_runtime_enforcement_evidence"},
    )
    write_json(
        runs_dir
        / "agent_runtime_enforcement_evidence"
        / "supervisor-executor-adapter-redacted-local-summary.json",
        {"artifact_kind": "agent_runtime_enforcement_evidence"},
    )
    return root


def write_ready_active_candidate_source(repo: Path) -> None:
    write_json(
        repo / "runs" / "active_idea_to_spec_candidate.json",
        {
            "artifact_kind": "active_idea_to_spec_candidate",
            "candidate": {
                "candidate_id": "team-decision-log",
                "display_name": "Team Decision Log",
                "governance_profile": "product_workspace",
                "public_route": "/team-decision-log",
                "target_repository_role": "product_spec_workspace",
                "workflow_lane": "product_idea_to_spec",
            },
            "contract_ref": "specgraph.idea-to-spec.active-candidate-source.v0.1",
            "readiness": {"ready": True, "review_state": "active_candidate_ready"},
            "schema_version": 1,
            "source_mode": "active_candidate",
            "summary": {
                "candidate_id": "team-decision-log",
                "promotion_path_count": 2,
                "status": "active_candidate_ready",
            },
        },
    )


def write_candidate_approval_decision(repo: Path, bundle_module: object) -> None:
    write_json(
        repo / "runs" / "candidate_approval_decision.json",
        {
            "artifact_kind": "candidate_approval_decision",
            "canonical_mutations_allowed": False,
            "contract_ref": "specgraph.idea-to-spec.candidate-approval-decision.v0.1",
            "decision": {"requested_state": "approved", "state": "approved"},
            "readiness": {"ready": True, "review_state": "promotion_request_approved"},
            "schema_version": 1,
            "source_artifacts": {
                "active_candidate": {
                    "sha256": bundle_module.file_sha256(
                        repo / "runs" / "active_idea_to_spec_candidate.json"
                    ),
                    "source_ref": "runs/active_idea_to_spec_candidate.json",
                },
                "promotion_gate": {
                    "sha256": bundle_module.file_sha256(
                        repo / "runs" / "idea_to_spec_promotion_gate.json"
                    ),
                    "source_ref": "runs/idea_to_spec_promotion_gate.json",
                },
            },
            "tracked_artifacts_written": False,
        },
    )


def test_build_public_bundle_copies_specs_and_runs_with_manifest(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "raw_run.json",
        {"worktree_path": "/Users/egor/Development/GitHub/0AL/SpecGraph/.worktrees/x"},
    )
    write_json(
        repo / "runs" / "custom_public_surface.json",
        {"artifact_kind": "custom_public_surface"},
    )
    write_json(
        repo / "runs" / "ontology_future_surface.json",
        {"artifact_kind": "ontology_future_surface"},
    )
    write_json(
        repo / "runs" / "ontology_term_binding_gate_report.json",
        {"artifact_kind": "ontology_term_binding_gate_report", "term": "ExamPolicy"},
    )
    write_json(
        repo / "runs" / "local_operator_executor_readiness.json",
        {"artifact_kind": "local_operator_executor_readiness", "local_only": True},
    )
    write_json(
        repo / "runs" / "local_operator_future_probe.json",
        {"artifact_kind": "local_operator_future_probe", "local_only": True},
    )
    write_json(
        repo / "runs" / "local_operator_executor_smoke.json",
        {"artifact_kind": "local_operator_executor_smoke", "local_only": True},
    )
    write_json(
        repo / "runs" / "local_operator_executor_task_smoke.json",
        {"artifact_kind": "local_operator_executor_task_smoke", "local_only": True},
    )
    write_json(
        repo / "runs" / "local_operator_executor_report_contract.json",
        {"artifact_kind": "local_operator_executor_report_contract", "local_only": True},
    )
    write_json(
        repo / "runs" / "local_operator_executor_report.json",
        {"artifact_kind": "local_operator_executor_report", "local_only": True},
    )
    write_json(
        repo / "runs" / "local_operator_executor_report_review_packet.json",
        {
            "artifact_kind": "local_operator_executor_report_review_packet",
            "local_only": True,
        },
    )
    write_json(
        repo / "runs" / "local_operator_executor_analysis_report_review_outcome.json",
        {
            "artifact_kind": "local_operator_executor_analysis_report_review_outcome",
            "local_only": True,
        },
    )
    write_json(
        repo / "runs" / "local_operator_executor_analysis_report_followup_packet.json",
        {
            "artifact_kind": "local_operator_executor_analysis_report_followup_packet",
            "local_only": True,
        },
    )
    write_json(
        repo / "runs" / "local_operator_executor_analysis_report_followup_decision.json",
        {
            "artifact_kind": "local_operator_executor_analysis_report_followup_decision",
            "local_only": True,
        },
    )
    write_json(
        repo / "runs" / "local_operator_executor_proposal_draft_request.json",
        {
            "artifact_kind": "local_operator_executor_proposal_draft_request",
            "local_only": True,
        },
    )
    write_json(
        repo / "runs" / "local_operator_executor_proposal_draft_candidate.json",
        {
            "artifact_kind": "executor_report_proposal_draft_candidate",
            "local_only": True,
        },
    )
    write_json(
        repo / "runs" / "local_operator_executor_followup_proposal_draft_candidate.json",
        {
            "artifact_kind": "executor_followup_proposal_draft_candidate",
            "local_only": True,
        },
    )
    write_json(
        repo / "runs" / "local_operator_executor_proposal_promotion_packet.json",
        {
            "artifact_kind": "proposal_draft_candidate_promotion_packet",
            "local_only": True,
        },
    )
    write_json(
        repo / "runs" / "local_operator_executor_proposal_materialization_report.json",
        {
            "artifact_kind": "proposal_source_draft_materialization_report",
            "local_only": True,
        },
    )
    write_json(
        repo / "runs" / "local_operator_executor_public_proposal_materialization_report.json",
        {
            "artifact_kind": "public_proposal_doc_materialization_report",
            "local_only": True,
        },
    )
    (repo / "runs" / ".DS_Store").write_text("junk", encoding="utf-8")
    (repo / "runs" / ".gitkeep").write_text("", encoding="utf-8")

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
    )

    assert (result.output_dir / "specs" / "nodes" / "SG-SPEC-0001.yaml").is_file()
    assert (result.output_dir / "runs" / "graph_dashboard.json").is_file()
    assert (result.output_dir / "runs" / "custom_public_surface.json").is_file()
    assert (result.output_dir / "runs" / "ontology_future_surface.json").is_file()
    assert not (result.output_dir / "runs" / "ontology_term_binding_gate_report.json").exists()
    assert not (result.output_dir / "runs" / "local_operator_executor_readiness.json").exists()
    assert not (result.output_dir / "runs" / "local_operator_future_probe.json").exists()
    assert not (result.output_dir / "runs" / "local_operator_executor_smoke.json").exists()
    assert not (result.output_dir / "runs" / "local_operator_executor_task_smoke.json").exists()
    assert not (
        result.output_dir / "runs" / "local_operator_executor_report_contract.json"
    ).exists()
    assert not (result.output_dir / "runs" / "local_operator_executor_report.json").exists()
    assert not (
        result.output_dir / "runs" / "local_operator_executor_report_review_packet.json"
    ).exists()
    assert not (
        result.output_dir / "runs" / "local_operator_executor_analysis_report_review_outcome.json"
    ).exists()
    assert not (
        result.output_dir / "runs" / "local_operator_executor_analysis_report_followup_packet.json"
    ).exists()
    assert not (
        result.output_dir
        / "runs"
        / "local_operator_executor_analysis_report_followup_decision.json"
    ).exists()
    assert not (
        result.output_dir / "runs" / "local_operator_executor_proposal_draft_request.json"
    ).exists()
    assert not (
        result.output_dir / "runs" / "local_operator_executor_proposal_draft_candidate.json"
    ).exists()
    assert not (
        result.output_dir
        / "runs"
        / "local_operator_executor_followup_proposal_draft_candidate.json"
    ).exists()
    assert not (
        result.output_dir / "runs" / "local_operator_executor_proposal_promotion_packet.json"
    ).exists()
    assert not (
        result.output_dir / "runs" / "local_operator_executor_proposal_materialization_report.json"
    ).exists()
    assert not (
        result.output_dir
        / "runs"
        / "local_operator_executor_public_proposal_materialization_report.json"
    ).exists()
    assert not (result.output_dir / "runs" / ".DS_Store").exists()
    assert not (result.output_dir / "runs" / ".gitkeep").exists()
    assert "$LOCAL_PATH" in (result.output_dir / "runs" / "raw_run.json").read_text(
        encoding="utf-8"
    )
    assert "/Users/egor" not in (result.output_dir / "runs" / "raw_run.json").read_text(
        encoding="utf-8"
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifact_kind"] == "specgraph_static_artifact_manifest"
    assert manifest["published_roots"] == ["specs", "runs"]
    assert manifest["required_surfaces"]["implementation_work_index.json"] is True
    assert manifest["required_surfaces"]["agent_runtime_enforcement_evidence_index.json"] is True
    assert manifest["required_surfaces"]["external_consumer_evidence_index.json"] is True
    assert manifest["required_surfaces"]["ontology_semantic_review_surface.json"] is True
    assert manifest["required_surfaces"]["ontology_review_dashboard.json"] is True
    assert manifest["required_surfaces"]["ontology_decision_import_preview.json"] is True
    assert manifest["required_surfaces"]["ontology_package_index.json"] is True
    assert manifest["required_surfaces"]["specauthor_invocation_artifact.json"] is True
    assert (
        manifest["required_surfaces"]["specauthor_invocation_artifact_contract_report.json"] is True
    )
    assert manifest["required_surfaces"]["specauthor_authoring_flow_report.json"] is True
    assert manifest["required_surfaces"]["candidate_spec_materialization_report.json"] is True
    assert manifest["required_surfaces"]["idea_to_spec_promotion_gate.json"] is True
    assert (
        manifest["platform_handoff_surfaces"]["candidate_spec_materialization_report.json"]["path"]
        == "runs/candidate_spec_materialization_report.json"
    )
    assert (
        manifest["platform_handoff_surfaces"]["idea_to_spec_promotion_gate.json"]["present"] is True
    )
    assert (
        manifest["required_surfaces"][
            "agent_runtime_enforcement_evidence/supervisor-executor-adapter-smoke.json"
        ]
        is True
    )
    assert (
        manifest["required_surfaces"][
            "agent_runtime_enforcement_evidence/"
            "supervisor-executor-adapter-redacted-local-summary.json"
        ]
        is True
    )
    assert any(
        file_info["path"] == "runs/implementation_work_index.json"
        for file_info in manifest["files"]
    )
    assert any(
        file_info["path"] == "runs/custom_public_surface.json" for file_info in manifest["files"]
    )
    assert any(
        file_info["path"] == "runs/ontology_future_surface.json" for file_info in manifest["files"]
    )
    assert any(
        file_info["path"] == "runs/specauthor_invocation_artifact.json"
        for file_info in manifest["files"]
    )
    assert any(
        file_info["path"] == "runs/specauthor_invocation_artifact_contract_report.json"
        for file_info in manifest["files"]
    )
    assert any(
        file_info["path"] == "runs/specauthor_authoring_flow_report.json"
        for file_info in manifest["files"]
    )
    assert any(
        file_info["path"] == "runs/candidate_spec_materialization_report.json"
        for file_info in manifest["files"]
    )
    assert any(
        file_info["path"] == "runs/idea_to_spec_promotion_gate.json"
        for file_info in manifest["files"]
    )
    assert manifest["safety_gate"]["status"] == "passed"
    assert manifest["safety_gate"]["redacted_local_path_occurrences"] == 1
    assert "artifact_manifest.json" in result.checksums_path.read_text(encoding="utf-8")
    assert "runs/implementation_work_index.json" in result.checksums_path.read_text(
        encoding="utf-8"
    )
    assert "runs/custom_public_surface.json" in result.checksums_path.read_text(encoding="utf-8")
    assert "runs/ontology_future_surface.json" in result.checksums_path.read_text(encoding="utf-8")
    assert "runs/ontology_term_binding_gate_report.json" not in result.checksums_path.read_text(
        encoding="utf-8"
    )
    assert "runs/local_operator_executor_readiness.json" not in result.checksums_path.read_text(
        encoding="utf-8"
    )
    assert "runs/local_operator_future_probe.json" not in result.checksums_path.read_text(
        encoding="utf-8"
    )
    assert "runs/local_operator_executor_smoke.json" not in result.checksums_path.read_text(
        encoding="utf-8"
    )
    assert "runs/local_operator_executor_task_smoke.json" not in result.checksums_path.read_text(
        encoding="utf-8"
    )
    assert (
        "runs/local_operator_executor_report_contract.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert "runs/local_operator_executor_report.json" not in result.checksums_path.read_text(
        encoding="utf-8"
    )
    assert (
        "runs/local_operator_executor_report_review_packet.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert (
        "runs/local_operator_executor_analysis_report_review_outcome.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert (
        "runs/local_operator_executor_analysis_report_followup_packet.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert (
        "runs/local_operator_executor_analysis_report_followup_decision.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert (
        "runs/local_operator_executor_proposal_draft_request.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert (
        "runs/local_operator_executor_proposal_draft_candidate.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert (
        "runs/local_operator_executor_followup_proposal_draft_candidate.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert (
        "runs/local_operator_executor_proposal_promotion_packet.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert (
        "runs/local_operator_executor_proposal_materialization_report.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )
    assert (
        "runs/local_operator_executor_public_proposal_materialization_report.json"
        not in result.checksums_path.read_text(encoding="utf-8")
    )


def test_build_public_bundle_skips_symlinked_artifacts(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("do-not-publish", encoding="utf-8")
    (repo / "runs" / "linked-secret.txt").symlink_to(outside)

    linked_dir_target = tmp_path / "linked-dir-target"
    linked_dir_target.mkdir()
    (linked_dir_target / "nested.json").write_text('{"secret": true}', encoding="utf-8")
    (repo / "runs" / "linked-dir").symlink_to(linked_dir_target, target_is_directory=True)

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
    )

    assert not (result.output_dir / "runs" / "linked-secret.txt").exists()
    assert not (result.output_dir / "runs" / "linked-dir" / "nested.json").exists()
    assert "do-not-publish" not in result.checksums_path.read_text(encoding="utf-8")


def test_build_public_bundle_redacts_linux_absolute_paths(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "linux_paths.json",
        {
            "runner_path": "/home/runner/work/SpecGraph/SpecGraph/runs/x.json",
            "workspace_path": "/github/workspace/runs/y.json",
            "tmp_path": "/tmp/specgraph/z.json",
        },
    )

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
    )

    published = (result.output_dir / "runs" / "linux_paths.json").read_text(encoding="utf-8")
    assert "/home/runner" not in published
    assert "/github/workspace" not in published
    assert "/tmp/specgraph" not in published
    assert published.count("$LOCAL_PATH") == 3


def test_build_public_bundle_rejects_malformed_runs_json(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / "broken.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(bundle_module.PublishBundleError, match="malformed JSON artifact"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_rejects_secret_like_content(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(repo / "runs" / "secret.json", {"api_key": "sk-test"})

    with pytest.raises(bundle_module.PublishBundleError, match="secret-like content"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )

    assert not (repo / "dist" / "specgraph-public").exists()


def test_build_public_bundle_rejects_demo_ontology_fixture_content(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "ontology_review_dashboard.json",
        {"artifact_kind": "ontology_review_dashboard", "term": "ExamPolicy"},
    )

    with pytest.raises(bundle_module.PublishBundleError, match="demo ontology fixture content"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )

    assert not (repo / "dist" / "specgraph-public").exists()


def test_build_public_bundle_rejects_stale_demo_ontology_support_artifact(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "ontology_delta_candidate_review_packet.json",
        {
            "artifact_kind": "ontology_delta_candidate_review_packet",
            "gap_id": "ontology-gap-examcalc",
        },
    )

    with pytest.raises(bundle_module.PublishBundleError, match="demo ontology fixture content"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_publishes_ontology_tombstones(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "ontology_package_index.json",
        {
            "artifact_kind": "retired_public_ontology_artifact",
            "source_mode": "public_tombstone",
            "summary": {"status": "retired_local_only_artifact"},
        },
    )

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
    )

    assert result.manifest["safety_gate"]["status"] == "passed"
    tombstone = result.output_dir / "runs" / "ontology_package_index.json"
    assert tombstone.is_file()
    assert "ExamPolicy" not in tombstone.read_text(encoding="utf-8")
    assert (result.output_dir / "runs" / "ontology_review_dashboard.json").is_file()


def test_build_public_bundle_publishes_ontology_materialized_ir(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    ir_path = repo / "ontology" / "packages" / "specgraph-core" / "generated"
    write_json(
        ir_path / "ontology.normalized.json",
        {
            "artifact_kind": "ontology_normalized_ir",
            "id": "org.0al.specgraph.core",
            "classes": [{"id": "SpecGraph"}],
            "relations": [],
        },
    )
    write_json(
        repo / "runs" / "ontology_package_index.json",
        {
            "artifact_kind": "ontology_package_index",
            "packages": [
                {
                    "package_id": "org.0al.specgraph.core",
                    "materialized_ir": (
                        "ontology/packages/specgraph-core/generated/ontology.normalized.json"
                    ),
                }
            ],
        },
    )

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
    )

    published_ir = (
        result.output_dir
        / "ontology"
        / "packages"
        / "specgraph-core"
        / "generated"
        / "ontology.normalized.json"
    )
    assert published_ir.is_file()
    assert json.loads(published_ir.read_text(encoding="utf-8"))["id"] == "org.0al.specgraph.core"
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert "ontology" in manifest["published_roots"]
    assert any(
        file_info["path"] == "ontology/packages/specgraph-core/generated/ontology.normalized.json"
        for file_info in manifest["files"]
    )
    assert (
        "ontology/packages/specgraph-core/generated/ontology.normalized.json"
        in result.checksums_path.read_text(encoding="utf-8")
    )


def test_build_public_bundle_rejects_unsafe_ontology_materialized_ir(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "ontology_package_index.json",
        {
            "artifact_kind": "ontology_package_index",
            "packages": [{"package_id": "org.0al.specgraph.core", "materialized_ir": "../x.json"}],
        },
    )

    with pytest.raises(bundle_module.PublishBundleError, match="unsafe .*materialized_ir"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_rejects_missing_ontology_materialized_ir(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "ontology_package_index.json",
        {
            "artifact_kind": "ontology_package_index",
            "packages": [
                {
                    "package_id": "org.0al.specgraph.core",
                    "materialized_ir": (
                        "ontology/packages/specgraph-core/generated/ontology.normalized.json"
                    ),
                }
            ],
        },
    )

    with pytest.raises(bundle_module.PublishBundleError, match="missing ontology materialized IR"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_rejects_malformed_pre_copied_ontology_materialized_ir(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    ir_path = repo / "specs" / "ontology.normalized.json"
    ir_path.write_text("{not-json", encoding="utf-8")
    write_json(
        repo / "runs" / "ontology_package_index.json",
        {
            "artifact_kind": "ontology_package_index",
            "packages": [
                {
                    "package_id": "org.0al.specgraph.core",
                    "materialized_ir": "specs/ontology.normalized.json",
                }
            ],
        },
    )

    with pytest.raises(bundle_module.PublishBundleError, match="malformed JSON artifact"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_rejects_local_only_ontology_materialized_ir(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "local_operator_executor_report.json",
        {"artifact_kind": "local_operator_executor_report", "local_only": True},
    )
    write_json(
        repo / "runs" / "ontology_package_index.json",
        {
            "artifact_kind": "ontology_package_index",
            "packages": [
                {
                    "package_id": "org.0al.specgraph.core",
                    "materialized_ir": "runs/local_operator_executor_report.json",
                }
            ],
        },
    )

    with pytest.raises(
        bundle_module.PublishBundleError,
        match="local-only ontology materialized IR",
    ):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_requires_core_viewer_surfaces(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / "graph_next_moves.json").unlink()

    with pytest.raises(bundle_module.PublishBundleError, match="missing required run surfaces"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_requires_implementation_work_surface(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / "implementation_work_index.json").unlink()

    with pytest.raises(bundle_module.PublishBundleError, match="implementation_work_index"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_requires_agent_runtime_surface(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / "agent_runtime_enforcement_evidence_index.json").unlink()

    with pytest.raises(
        bundle_module.PublishBundleError,
        match="agent_runtime_enforcement_evidence_index",
    ):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_requires_external_consumer_evidence_surface(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / "external_consumer_evidence_index.json").unlink()

    with pytest.raises(
        bundle_module.PublishBundleError,
        match="external_consumer_evidence_index",
    ):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


@pytest.mark.parametrize(
    "surface_name",
    [
        "ontology_semantic_review_surface.json",
        "ontology_review_dashboard.json",
        "ontology_decision_import_preview.json",
    ],
)
def test_build_public_bundle_requires_ontology_review_surfaces(
    tmp_path: Path,
    bundle_module: object,
    surface_name: str,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / surface_name).unlink()

    with pytest.raises(
        bundle_module.PublishBundleError,
        match=surface_name,
    ):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_requires_ontology_package_index(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / "ontology_package_index.json").unlink()

    with pytest.raises(bundle_module.PublishBundleError, match="ontology_package_index"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_requires_agent_passport_cli_available(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "agent_passport_verification_report.json",
        {
            "artifact_kind": "agent_passport_verification_report",
            "summary": {
                "entry_count": 5,
                "valid_count": 0,
                "tool_unavailable_count": 5,
                "agent_passport_cli_status": "missing",
            },
        },
    )

    with pytest.raises(
        bundle_module.PublishBundleError,
        match="agent_passport_verification_report.json.summary.agent_passport_cli_status",
    ):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_requires_all_agent_passports_valid(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "agent_passport_verification_report.json",
        {
            "artifact_kind": "agent_passport_verification_report",
            "summary": {
                "entry_count": 5,
                "valid_count": 4,
                "tool_unavailable_count": 0,
                "agent_passport_cli_status": "available",
            },
        },
    )

    with pytest.raises(bundle_module.PublishBundleError, match="all report-only passport"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_can_opt_out_of_verified_agent_passports_for_local_drafts(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "agent_passport_verification_report.json",
        {
            "artifact_kind": "agent_passport_verification_report",
            "summary": {
                "entry_count": 5,
                "valid_count": 0,
                "tool_unavailable_count": 5,
                "agent_passport_cli_status": "missing",
            },
        },
    )

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
        require_verified_agent_passports=False,
    )

    assert result.manifest["safety_gate"]["status"] == "passed"


def test_refresh_publish_surfaces_builds_viewer_implementation_and_agent_surfaces(
    tmp_path: Path,
    bundle_module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_run_make_target(repo_root: Path, target: str) -> None:
        assert repo_root == tmp_path
        calls.append(target)

    monkeypatch.setattr(bundle_module, "run_make_target", fake_run_make_target)

    bundle_module.refresh_publish_surfaces(tmp_path)

    assert calls == [
        "viewer-surfaces",
        "implementation-delta",
        "implementation-work",
        "executor-adapters",
        "agent-passports",
        "agent-runtime-evidence",
        "viewer-surfaces",
        "external-handoffs",
        "external-consumer-evidence",
        "ontology-imports",
        "spec-ontology-bindings",
        "spec-ontology-validation",
        "ontology-gap-review",
        "legacy-spec-ontology-backfill-plan",
        "ontology-imports-public",
        "ontology-owner-decision-import-v2",
        "specauthor-authoring-flow",
        "product-workspace-active-candidate",
    ]
    materialization = json.loads(
        (tmp_path / "runs" / "candidate_spec_materialization_report.json").read_text(
            encoding="utf-8"
        )
    )
    promotion_gate = json.loads(
        (tmp_path / "runs" / "idea_to_spec_promotion_gate.json").read_text(encoding="utf-8")
    )
    assert materialization["source_mode"] == "public_placeholder"
    assert materialization["placeholder_reason"] == "no_active_candidate"
    assert materialization["promotion_request"]["paths"] == []
    assert materialization["summary"]["materialized_file_count"] == 0
    assert promotion_gate["source_mode"] == "public_placeholder"
    assert promotion_gate["placeholder_reason"] == "no_active_candidate"
    assert promotion_gate["promotion_request"]["paths"] == []
    assert promotion_gate["summary"]["promotion_path_count"] == 0


def test_refresh_publish_surfaces_preserves_ready_active_candidate_handoff(
    tmp_path: Path,
    bundle_module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = make_repo(tmp_path)
    write_ready_active_candidate_source(repo)
    materialization_path = repo / "runs" / "candidate_spec_materialization_report.json"
    materialization = json.loads(materialization_path.read_text(encoding="utf-8"))
    materialization["summary"] = {}
    materialization["summary"]["status"] = "real_active_candidate"
    write_json(materialization_path, materialization)
    calls: list[str] = []

    def fake_run_make_target(repo_root: Path, target: str) -> None:
        assert repo_root == repo
        calls.append(target)

    monkeypatch.setattr(bundle_module, "run_make_target", fake_run_make_target)

    bundle_module.refresh_publish_surfaces(repo)

    materialization = json.loads(materialization_path.read_text(encoding="utf-8"))
    assert calls[-1] == "specauthor-authoring-flow"
    assert "product-workspace-active-candidate" not in calls
    assert materialization["summary"]["status"] == "real_active_candidate"
    assert "placeholder_reason" not in materialization


def test_refresh_publish_surfaces_rebuilds_ready_candidate_when_requested(
    tmp_path: Path,
    bundle_module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = make_repo(tmp_path)
    write_ready_active_candidate_source(repo)
    calls: list[str] = []

    def fake_run_make_target(repo_root: Path, target: str) -> None:
        assert repo_root == repo
        calls.append(target)

    monkeypatch.setattr(bundle_module, "run_make_target", fake_run_make_target)
    monkeypatch.setenv("PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH", "force")

    bundle_module.refresh_publish_surfaces(repo)

    assert calls[-1] == "product-workspace-active-candidate"


def test_refresh_publish_surfaces_builds_product_workspace_active_candidate_before_fallback(
    tmp_path: Path,
    bundle_module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = make_repo(tmp_path)
    calls: list[str] = []

    def fake_run_make_target(repo_root: Path, target: str) -> None:
        assert repo_root == repo
        calls.append(target)
        if target == "product-workspace-active-candidate":
            write_ready_active_candidate_source(repo)

    monkeypatch.setattr(bundle_module, "run_make_target", fake_run_make_target)

    bundle_module.refresh_publish_surfaces(repo)

    active_source = json.loads(
        (repo / "runs" / "active_idea_to_spec_candidate.json").read_text(encoding="utf-8")
    )
    materialization = json.loads(
        (repo / "runs" / "candidate_spec_materialization_report.json").read_text(encoding="utf-8")
    )
    promotion_gate = json.loads(
        (repo / "runs" / "idea_to_spec_promotion_gate.json").read_text(encoding="utf-8")
    )
    assert calls[-1] == "product-workspace-active-candidate"
    assert active_source["source_mode"] == "active_candidate"
    assert active_source["readiness"]["ready"] is True
    assert "placeholder_reason" not in materialization
    assert "placeholder_reason" not in promotion_gate


def test_build_public_bundle_publishes_ready_active_candidate_source(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_ready_active_candidate_source(repo)

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
        require_verified_agent_passports=False,
    )

    active_source = result.output_dir / "runs" / "active_idea_to_spec_candidate.json"
    assert active_source.is_file()
    assert (
        result.manifest["platform_handoff_surfaces"]["active_idea_to_spec_candidate.json"][
            "present"
        ]
        is True
    )


def test_build_public_bundle_skips_unready_active_candidate_source(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_ready_active_candidate_source(repo)
    active_source_path = repo / "runs" / "active_idea_to_spec_candidate.json"
    active_source = json.loads(active_source_path.read_text(encoding="utf-8"))
    active_source["readiness"]["ready"] = False
    write_json(active_source_path, active_source)

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
        require_verified_agent_passports=False,
    )

    assert not (result.output_dir / "runs" / "active_idea_to_spec_candidate.json").exists()
    assert (
        result.manifest["platform_handoff_surfaces"]["active_idea_to_spec_candidate.json"][
            "present"
        ]
        is False
    )


def test_build_public_bundle_publishes_current_candidate_approval_decision(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_ready_active_candidate_source(repo)
    write_candidate_approval_decision(repo, bundle_module)

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
        require_verified_agent_passports=False,
    )

    assert (result.output_dir / "runs" / "candidate_approval_decision.json").is_file()


def test_build_public_bundle_skips_candidate_approval_without_publishable_active_candidate(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_ready_active_candidate_source(repo)
    write_candidate_approval_decision(repo, bundle_module)
    active_source_path = repo / "runs" / "active_idea_to_spec_candidate.json"
    active_source = json.loads(active_source_path.read_text(encoding="utf-8"))
    active_source["readiness"]["ready"] = False
    write_json(active_source_path, active_source)

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
        require_verified_agent_passports=False,
    )

    assert not (result.output_dir / "runs" / "candidate_approval_decision.json").exists()


def test_build_public_bundle_skips_candidate_approval_with_stale_digest(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_ready_active_candidate_source(repo)
    write_candidate_approval_decision(repo, bundle_module)
    promotion_gate_path = repo / "runs" / "idea_to_spec_promotion_gate.json"
    promotion_gate = json.loads(promotion_gate_path.read_text(encoding="utf-8"))
    promotion_gate["summary"] = {"status": "regenerated_after_approval"}
    write_json(promotion_gate_path, promotion_gate)

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
        require_verified_agent_passports=False,
    )

    assert not (result.output_dir / "runs" / "candidate_approval_decision.json").exists()


def test_main_prints_compact_summary(
    tmp_path: Path,
    bundle_module: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = make_repo(tmp_path / "repo")

    exit_code = bundle_module.main(
        [
            "--repo-root",
            str(repo),
            "--output-dir",
            str(repo / "dist" / "specgraph-public"),
        ]
    )

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["file_count"] >= 6
    assert summary["safety_gate"]["status"] == "passed"
