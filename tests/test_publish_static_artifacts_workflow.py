from __future__ import annotations

from pathlib import Path


def _workflow_text() -> str:
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "publish-static-artifacts.yml"
    )
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


def test_publish_workflow_has_pr_deploy_connection_check_without_upload() -> None:
    workflow = _workflow_text()

    assert "pull_request_target:" in workflow
    assert "deploy_connection_check:" in workflow
    connection_check_block = workflow.split("  deploy_connection_check:", 1)[1]

    assert "if: github.event_name == 'pull_request_target'" in connection_check_block
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
    workflow = _workflow_text()

    assert "if: github.event_name != 'pull_request_target'" in workflow
    assert "if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'" in workflow
    assert "if: github.event_name == 'pull_request_target'" in workflow
