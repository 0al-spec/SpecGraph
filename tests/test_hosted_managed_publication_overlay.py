from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "hosted_managed_publication_overlay.py"
SPEC = importlib.util.spec_from_file_location(
    "hosted_managed_publication_overlay",
    TOOL_PATH,
)
assert SPEC is not None and SPEC.loader is not None
overlay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overlay)


def json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def public_authority() -> dict:
    return {
        "accepts_arbitrary_commands": False,
        "creates_git_commits": False,
        "merges_pull_requests": False,
        "mutates_canonical_specs": False,
        "opens_pull_requests": False,
        "publishes_read_models": False,
        "writes_ontology_packages": False,
        "accepts_ontology_terms": False,
    }


def review_object() -> dict:
    return {
        "schema_version": 1,
        "artifact_kind": overlay.REVIEW_OBJECT_KIND,
        "generated_at": "2026-07-18T12:00:00+00:00",
        "ok": True,
        "probe_only": True,
        "promotion_execution_report_ref": (
            "runs/product_candidate_promotion_execution_report.json"
        ),
        "promotion_execution_report_sha256": "a" * 64,
        "workspace_id": overlay.WORKSPACE_ID,
        "candidate_id": overlay.WORKSPACE_ID,
        "candidate_branch": "graph-candidate/hosted-operation-canary",
        "review_url": "https://github.com/0al-spec/SpecGraph/pull/690",
        "review_number": 690,
        "review_state_at_capture": "open",
        "review_head_sha": "b" * 40,
        "base_branch": "main",
        "workspace_binding": {
            "status": "ready",
            "workspace_id": overlay.WORKSPACE_ID,
            "binding_id": (f"product-workspace-binding://{overlay.WORKSPACE_ID}"),
        },
        "privacy_boundary": {
            "public_safe": True,
            "raw_idea_included": False,
            "local_paths_included": False,
        },
        "authority_boundary": public_authority(),
        "diagnostics": [],
        "summary": {
            "status": "review_object_ready",
            "error_count": 0,
            "next_action": "Run read-only review status inspection.",
        },
    }


def review_status() -> dict:
    return {
        "schema_version": 1,
        "artifact_kind": overlay.REVIEW_STATUS_KIND,
        "generated_at": "2026-07-18T12:05:00+00:00",
        "ok": True,
        "workflow_lane": "product_idea_to_spec",
        "workspace_id": overlay.WORKSPACE_ID,
        "candidate_id": overlay.WORKSPACE_ID,
        "candidate_branch": "graph-candidate/hosted-operation-canary",
        "promotion_execution_report_ref": (
            "runs/product_candidate_promotion_execution_report.json"
        ),
        "review_object_evidence_ref": overlay.REVIEW_OBJECT_REF,
        "review_probe_only": False,
        "review_state": "open",
        "review_decision": "",
        "pull_request": {
            "number": 690,
            "url": "https://github.com/0al-spec/SpecGraph/pull/690",
            "state": "OPEN",
            "isDraft": False,
            "headRefName": "graph-candidate/hosted-operation-canary",
            "baseRefName": "main",
            "headRefOid": "b" * 40,
            "reviewDecision": "",
            "mergedAt": None,
            "mergeCommit": None,
        },
        "graph_repository_review_status": {
            "artifact_kind": "platform_graph_repository_review_status_report",
            "ok": True,
            "review_state": "open",
            "review_url": "https://github.com/0al-spec/SpecGraph/pull/690",
            "summary": {
                "status": "waiting_for_review_merge",
                "review_merged": False,
            },
        },
        "authority_boundary": public_authority(),
        "privacy_boundary": {
            "public_safe": True,
            "raw_idea_included": False,
            "local_paths_included": False,
        },
        "diagnostics": [],
        "summary": {
            "status": "waiting_for_review_merge",
            "review_merged": False,
            "read_model_published": False,
            "error_count": 0,
        },
    }


def packet(report: dict, logical_ref: str) -> dict:
    return {
        "schema_version": 1,
        "artifact_kind": overlay.PACKET_ARTIFACT_KIND,
        "contract_ref": overlay.PACKET_CONTRACT_REF,
        "generated_at": "2026-07-18T12:10:00+00:00",
        "workspace_id": overlay.WORKSPACE_ID,
        "operation_id": overlay.OPERATION_ID,
        "logical_ref": logical_ref,
        "public_report_sha256": hashlib.sha256(json_bytes(report)).hexdigest(),
        "report": report,
        "source_provenance": {"source_sha256": "c" * 64},
        "publication_scope": {
            "workspace_bundle_only": True,
            "maximum_report_count": 1,
            "incremental_upload_required": True,
        },
        "privacy_boundary": {
            "public_safe": True,
            "raw_idea_included": False,
            "local_paths_included": False,
        },
        "authority_boundary": public_authority(),
        "summary": {
            "status": "publication_packet_ready",
            "report_count": 1,
        },
    }


def test_validate_review_object_and_status_packets() -> None:
    for report, logical_ref in (
        (review_object(), overlay.REVIEW_OBJECT_REF),
        (review_status(), overlay.REVIEW_STATUS_REF),
    ):
        selected_ref, selected_report = overlay.validate_packet(
            packet(report, logical_ref),
            workspace_id=overlay.WORKSPACE_ID,
        )
        assert selected_ref == logical_ref
        assert selected_report == report


def test_rejects_digest_drift_foreign_workspace_and_authority_expansion() -> None:
    payload = packet(review_status(), overlay.REVIEW_STATUS_REF)
    payload["public_report_sha256"] = "0" * 64
    with pytest.raises(overlay.OverlayError, match="digest"):
        overlay.validate_packet(payload, workspace_id=overlay.WORKSPACE_ID)

    payload = packet(review_status(), overlay.REVIEW_STATUS_REF)
    payload["workspace_id"] = "foreign"
    with pytest.raises(overlay.OverlayError, match="contract"):
        overlay.validate_packet(payload, workspace_id=overlay.WORKSPACE_ID)

    report = review_object()
    report["workspace_binding"]["workspace_id"] = "foreign"
    with pytest.raises(overlay.OverlayError, match="invalid"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_OBJECT_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )

    report = review_status()
    report["authority_boundary"]["may_merge_review"] = True
    with pytest.raises(overlay.OverlayError, match="authority"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_STATUS_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )

    report = review_status()
    report["authority_boundary"]["executes_managed_operations"] = True
    with pytest.raises(overlay.OverlayError, match="invalid"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_STATUS_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "/Users/operator/private",
        "/workspace/SpecGraph/runs/private.json",
        "/github/workspace/runs/private.json",
        "/opt/specgraph/private.json",
    ],
)
def test_rejects_private_fields_and_local_paths(unsafe_value: str) -> None:
    report = review_status()
    report["stdout"] = "ok"
    with pytest.raises(overlay.OverlayError, match="forbidden field"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_STATUS_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )

    report = review_status()
    report["summary"]["detail"] = unsafe_value
    with pytest.raises(overlay.OverlayError, match="local path"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_STATUS_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )

    report = review_status()
    report["summary"]["detail"] = "github_pat_" + "a" * 32
    with pytest.raises(overlay.OverlayError, match="secret-like"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_STATUS_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )


def test_rejects_foreign_branch_probe_status_missing_refs_and_state_drift() -> None:
    report = review_status()
    report["candidate_branch"] = "graph-candidate/foreign"
    report["pull_request"]["headRefName"] = "graph-candidate/foreign"
    with pytest.raises(overlay.OverlayError, match="identity"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_STATUS_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )

    for missing_ref in (
        "promotion_execution_report_ref",
        "review_object_evidence_ref",
    ):
        report = review_status()
        report.pop(missing_ref)
        with pytest.raises(overlay.OverlayError, match="invalid"):
            overlay.validate_packet(
                packet(report, overlay.REVIEW_STATUS_REF),
                workspace_id=overlay.WORKSPACE_ID,
            )

    report = review_status()
    report["review_probe_only"] = True
    with pytest.raises(overlay.OverlayError, match="invalid"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_STATUS_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )

    report = review_status()
    report["summary"]["status"] = "ready_for_read_model_publication"
    with pytest.raises(overlay.OverlayError, match="invalid"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_STATUS_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )


def test_accepts_probe_status_without_read_model_publication_authority() -> None:
    report = review_status()
    report["review_probe_only"] = True
    report["summary"]["status"] = "review_probe_completed"
    report["graph_repository_review_status"]["summary"]["status"] = "review_probe_completed"

    logical_ref, projected = overlay.validate_packet(
        packet(report, overlay.REVIEW_STATUS_REF),
        workspace_id=overlay.WORKSPACE_ID,
    )

    assert logical_ref == overlay.REVIEW_STATUS_REF
    assert projected["review_probe_only"] is True
    assert projected["review_state"] == "open"
    assert projected["summary"]["status"] == "review_probe_completed"
    assert projected["summary"]["review_merged"] is False


def test_probe_status_rejects_nested_publication_readiness() -> None:
    report = review_status()
    report["review_probe_only"] = True
    report["summary"]["status"] = "review_probe_completed"
    report["graph_repository_review_status"]["summary"]["status"] = (
        "ready_for_read_model_publication"
    )

    with pytest.raises(overlay.OverlayError, match="invalid"):
        overlay.validate_packet(
            packet(report, overlay.REVIEW_STATUS_REF),
            workspace_id=overlay.WORKSPACE_ID,
        )


def test_rejects_non_finite_json_and_workflow_refreshes_lifecycle() -> None:
    payload = packet(review_status(), overlay.REVIEW_STATUS_REF)
    payload["report"]["summary"]["depth"] = float("nan")
    with pytest.raises(overlay.OverlayError, match="non-strict JSON"):
        overlay.validate_packet(payload, workspace_id=overlay.WORKSPACE_ID)

    workflow = (ROOT / ".github" / "workflows" / "publish-static-artifacts.yml").read_text(
        encoding="utf-8"
    )
    assert "make hosted-managed-publication-lifecycle-refresh" in workflow
    assert "HOSTED_MANAGED_PUBLICATION_RUN_DIR=runs/hosted-operation-canary" in workflow


def test_apply_is_atomic_and_invalid_packet_preserves_existing_artifact() -> None:
    tracked_run_dir = ROOT / "runs" / overlay.WORKSPACE_ID
    destination = tracked_run_dir / Path(overlay.REVIEW_STATUS_REF).name
    original = destination.read_bytes() if destination.exists() else None
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet_path = Path(temp_dir) / "packet.json"
            packet_path.write_bytes(json_bytes(packet(review_status(), overlay.REVIEW_STATUS_REF)))
            result = overlay.apply_packet(
                packet_path=packet_path.resolve(),
                run_dir=tracked_run_dir.resolve(),
                workspace_id=overlay.WORKSPACE_ID,
            )
            assert result["summary"]["applied_report_count"] == 1
            applied = destination.read_bytes()

            invalid = packet(review_status(), overlay.REVIEW_STATUS_REF)
            invalid["public_report_sha256"] = "0" * 64
            packet_path.write_bytes(json_bytes(invalid))
            with pytest.raises(overlay.OverlayError, match="digest"):
                overlay.apply_packet(
                    packet_path=packet_path.resolve(),
                    run_dir=tracked_run_dir.resolve(),
                    workspace_id=overlay.WORKSPACE_ID,
                )
            assert destination.read_bytes() == applied
    finally:
        if original is None:
            destination.unlink(missing_ok=True)
        else:
            destination.write_bytes(original)
