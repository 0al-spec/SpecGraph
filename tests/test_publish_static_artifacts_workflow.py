from __future__ import annotations

from pathlib import Path


def _workflow_text(relative_path: str = "publish-static-artifacts.yml") -> str:
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / relative_path
    return workflow_path.read_text(encoding="utf-8")


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

    assert "lcd dist/specgraph-public" in workflow
    assert 'mirror -R --verbose . "$SFTP_REMOTE_ROOT"' in workflow
    assert 'mirror -R --delete --verbose dist/specgraph-public "$SFTP_REMOTE_ROOT"' not in workflow


def test_artifact_deploy_does_not_delete_webroot_content() -> None:
    workflow = _workflow_text()
    upload_bundle_block = workflow.split("      - name: Upload bundle", 1)[1].split(
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


def test_workflows_opt_into_node24_actions_runtime() -> None:
    workflow_dir = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    workflow_paths = sorted(workflow_dir.glob("*.yml"))

    assert workflow_paths
    for workflow_path in workflow_paths:
        workflow = workflow_path.read_text(encoding="utf-8")
        if "uses:" not in workflow:
            continue
        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true" in workflow, workflow_path.name
