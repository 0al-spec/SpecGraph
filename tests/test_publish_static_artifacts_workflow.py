from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _workflow_text(relative_path: str = "publish-static-artifacts.yml") -> str:
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / relative_path
    return workflow_path.read_text(encoding="utf-8")


def _step_block(workflow: str, step_name: str) -> str:
    marker = f"      - name: {step_name}"
    block = workflow.split(marker, 1)[1]
    return block.split("\n      - name:", 1)[0]


def test_ftps_deploy_requires_password_secret_without_private_key_fallback() -> None:
    workflow = _workflow_text()

    ftp_block = workflow.split('if [ "$DEPLOY_PORT" = "21" ]; then', 1)[1].split(
        "\n          fi",
        1,
    )[0]

    assert 'test -n "$SFTP_PASSWORD"' in ftp_block
    assert 'lftp -u "$SFTP_USER,$SFTP_PASSWORD"' in ftp_block
    assert "DEPLOY_PASSWORD" not in ftp_block
    assert "SFTP_PRIVATE_KEY" not in ftp_block


def test_deploy_connection_check_workflow_uses_trusted_code_without_upload() -> None:
    workflow = _workflow_text("deploy-connection-check.yml")

    assert "pull_request_target:" in workflow
    assert "deploy_connection_check:" in workflow
    connection_check_block = workflow.split("  deploy_connection_check:", 1)[1]

    assert (
        "github.event.pull_request.head.repo.full_name == github.repository"
        in connection_check_block
    )
    assert "name: FTP" in connection_check_block
    assert "secrets.SFTP_PASSWORD" in connection_check_block
    assert "Checkout trusted deploy tooling" in connection_check_block
    assert "ref: ${{ github.event.pull_request.base.sha }}" in connection_check_block
    assert "actions/download-artifact" not in connection_check_block
    assert "secrets.FTPS_ALLOW_UNVERIFIED_CERT" in connection_check_block
    assert "tools/static_artifact_deploy_plan.py --skip-bundle-check" in connection_check_block
    assert "Check FTP/SFTP connection without upload" in connection_check_block
    assert "set ssl:verify-certificate false" in connection_check_block
    assert 'cls -1 "$SFTP_REMOTE_ROOT"' in connection_check_block
    assert "mirror -R" not in connection_check_block


def test_secret_bearing_jobs_do_not_run_on_pr_controlled_workflow() -> None:
    publish_workflow = _workflow_text()
    connection_workflow = _workflow_text("deploy-connection-check.yml")

    assert "pull_request_target:" not in publish_workflow
    assert "deploy_connection_check:" not in publish_workflow
    assert (
        "if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'"
        in publish_workflow
    )
    assert "pull_request_target:" in connection_workflow
    assert "ref: ${{ github.event.pull_request.base.sha }}" in connection_workflow


def test_deploy_upload_mirrors_bundle_contents_not_wrapper_directory() -> None:
    workflow = _workflow_text()

    assert 'lcd "$INCREMENTAL_STAGE_DIR"' in workflow
    assert workflow.count('mirror -R --parallel=4 --verbose . "$REMOTE_ROOT"') == 3
    assert 'mirror -R --delete --verbose dist/specgraph-public "$SFTP_REMOTE_ROOT"' not in workflow


def test_deploy_stages_workspace_payloads_and_finalizes_manifests_last() -> None:
    workflow = _workflow_text()
    stage_block = _step_block(workflow, "Stage changed artifact payloads")
    upload_block = _step_block(workflow, "Upload changed artifact payloads and metadata")
    verify_block = _step_block(workflow, "Verify published artifact digests")

    assert stage_block.count("tools/static_artifact_incremental_stage.py stage") == 3
    assert "--staging-prefix workspaces/team-decision-log" in stage_block
    assert "--staging-prefix workspaces/hosted-operation-canary" in stage_block
    assert upload_block.index("mirror -R --parallel=4 --verbose") < upload_block.index(
        "checksums.sha256"
    )
    assert upload_block.index("checksums.sha256") < upload_block.index("artifact_manifest.json")
    assert verify_block.count("tools/static_artifact_incremental_stage.py verify") == 3
    assert "$STATIC_ARTIFACT_PUBLIC_BASE_URL/workspaces/hosted-operation-canary" in (verify_block)
    assert "name: specgraph-incremental-deployment-reports" in workflow


def test_publish_workflow_builds_team_decision_log_workspace_bundle() -> None:
    workflow = _workflow_text()
    build_workspace_block = _step_block(
        workflow,
        "Build Team Decision Log product workspace bundle",
    )

    assert "make product-workspace-team-decision-log-happy-path-repair-pack" in (
        build_workspace_block
    )
    assert "tools/build_static_artifact_bundle.py" in build_workspace_block
    assert "--output-dir dist/specgraph-public/workspaces/team-decision-log" in (
        build_workspace_block
    )
    upload_block = _step_block(workflow, "Upload bundle as GitHub Actions artifact")
    assert "path: dist/specgraph-public" in upload_block


def test_publish_workflow_builds_hosted_operation_canary_workspace_bundle() -> None:
    workflow = _workflow_text()
    build_workspace_block = _step_block(
        workflow,
        "Build Hosted Operation Canary product workspace bundle",
    )

    assert "tools/build_static_artifact_bundle.py" in build_workspace_block
    assert "--workspace-bootstrap-run-dir runs/hosted-operation-canary" in (build_workspace_block)
    assert (
        "--output-dir dist/specgraph-public/workspaces/hosted-operation-canary"
        in build_workspace_block
    )
    assert workflow.index("Build Team Decision Log product workspace bundle") < (
        workflow.index("Build Hosted Operation Canary product workspace bundle")
    )
    assert workflow.index("Build Hosted Operation Canary product workspace bundle") < (
        workflow.index("Upload bundle as GitHub Actions artifact")
    )


def test_publish_workflow_applies_bounded_hosted_report_before_workspace_build() -> None:
    workflow = _workflow_text()
    overlay_block = _step_block(
        workflow,
        "Apply hosted managed public report overlay",
    )

    assert "hosted_managed_publication_packet_b64:" in workflow
    assert "inputs.hosted_managed_publication_packet_b64 != ''" in overlay_block
    assert "SPECGRAPH_EXTERNAL_CHECKOUT_ROOT: ${{ github.workspace }}/external" in overlay_block
    assert "base64 --decode" in overlay_block
    assert "tools/hosted_managed_publication_overlay.py" in overlay_block
    assert "--workspace-id hosted-operation-canary" in overlay_block
    assert "--run-dir runs/hosted-operation-canary" in overlay_block
    assert "current-public-review-status.json" in overlay_block
    assert (
        "https://specgraph.tech/workspaces/hosted-operation-canary/runs/"
        "hosted-operation-canary/product_candidate_promotion_review_status_report.json"
        in overlay_block
    )
    assert "--current-review-status" in overlay_block
    assert "--proto '=https'" in overlay_block
    assert workflow.index("Apply hosted managed public report overlay") < workflow.index(
        "Build Hosted Operation Canary product workspace bundle"
    )


def test_hosted_operation_canary_packet_is_self_contained_and_ready() -> None:
    run_dir = ROOT / "runs" / "hosted-operation-canary"
    decision = json.loads(
        (run_dir / "candidate_approval_decision.json").read_text(encoding="utf-8")
    )
    approved_paths = decision["promotion_request"]["paths"]

    assert len(approved_paths) == 59
    assert len(approved_paths) == len(set(approved_paths))
    assert all((ROOT / path).is_file() for path in approved_paths)
    assert "runs/hosted-operation-canary/graph_repository_execution_plan.json" in (approved_paths)
    assert "runs/hosted-operation-canary/idea_maturity_metrics_report.json" in (approved_paths)

    for source_key in ("active_candidate", "promotion_gate"):
        source = decision["source_artifacts"][source_key]
        source_path = ROOT / source["source_ref"]
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source["sha256"]

    maturity = json.loads(
        (run_dir / "idea_maturity_metrics_report.json").read_text(encoding="utf-8")
    )
    validation = json.loads(
        (run_dir / "idea_maturity_metrics_validation_report.json").read_text(encoding="utf-8")
    )
    assert maturity["status"] == "ready"
    assert maturity["summary"]["lifecycle_state"] == "promotion_requested"
    assert maturity["summary"]["remaining_blocker_count"] == 0
    assert maturity["summary"]["stale_ref_count"] == 0
    assert validation["summary"]["status"] == "ok"

    private_markers = ("/Users/", "/private/tmp/", "/home/")
    for path in approved_paths:
        content = (ROOT / path).read_text(encoding="utf-8")
        assert not any(marker in content for marker in private_markers)


def test_artifact_deploy_does_not_delete_webroot_content() -> None:
    workflow = _workflow_text()
    upload_bundle_block = workflow.split(
        "      - name: Upload changed artifact payloads and metadata", 1
    )[1].split(
        "      - name: Report skipped SFTP upload",
        1,
    )[0]

    assert "--delete" not in upload_bundle_block


def test_landing_page_deploys_as_separate_non_destructive_job() -> None:
    workflow = _workflow_text()
    landing_job = workflow.split("  deploy_landing:", 1)[1]

    assert "name: Deploy landing page to static host" in landing_job
    assert "needs: deploy" in landing_job
    assert "landing/**" in workflow
    assert "test -f landing/index.html" in landing_job
    assert "lcd landing" in landing_job
    assert (
        "mirror -R --verbose --exclude-glob .DS_Store --exclude-glob 'check/**' . "
        '"$SFTP_REMOTE_ROOT"'
    ) in landing_job
    assert "--delete" not in landing_job


def test_pages_technical_root_builds_docc_surface() -> None:
    workflow = _workflow_text("pages-technical-root.yml")

    assert "name: Deploy DocC Technical Surface" in workflow
    assert "pull_request:" in workflow
    assert "runs-on: macos-14" in workflow
    assert "generate-documentation" in workflow
    assert "--target SpecGraph" in workflow
    assert "--hosting-base-path SpecGraph" in workflow
    assert "cp docs/github-pages-root/index.html ./.docc-build/index.html" in workflow
    assert "Add mixed-case DocC compatibility redirect" in workflow
    assert "test -f ./.docc-build/documentation/specgraph/index.html" in workflow
    assert "test -f ./.docc-build/documentation/SpecGraph/index.html" in workflow
    assert "if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'" in workflow
    archive_step = _step_block(workflow, "Archive DocC artifact")
    assert "actions/upload-artifact@v7" in archive_step
    assert "include-hidden-files: true" in archive_step
    assert "path: ./.docc-build" in archive_step
    pages_upload_step = _step_block(workflow, "Upload Pages artifact")
    assert "actions/upload-pages-artifact@v5" in pages_upload_step
    assert "include-hidden-files: true" in pages_upload_step
    assert "path: ./.docc-build" in pages_upload_step
    assert "actions/deploy-pages@v5" in workflow


def test_github_pages_root_docs_card_points_to_docc_entrypoint() -> None:
    root_page = (
        Path(__file__).resolve().parents[1] / "docs" / "github-pages-root" / "index.html"
    ).read_text(encoding="utf-8")

    assert "https://0al-spec.github.io/SpecGraph/documentation/specgraph/" in root_page
    assert "https://github.com/0al-spec/SpecGraph/tree/main/docs" not in root_page


def test_workflows_opt_into_node24_actions_runtime() -> None:
    workflow_dir = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    workflow_paths = sorted(workflow_dir.glob("*.yml"))

    assert workflow_paths
    for workflow_path in workflow_paths:
        workflow = workflow_path.read_text(encoding="utf-8")
        if "uses:" not in workflow:
            continue
        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true" in workflow, workflow_path.name
