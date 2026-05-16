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

    assert "deploy_connection_check:" in workflow
    connection_check_block = workflow.split("  deploy_connection_check:", 1)[1]

    assert "if: github.event_name == 'pull_request'" in connection_check_block
    assert (
        "github.event.pull_request.head.repo.full_name == github.repository"
        in connection_check_block
    )
    assert "name: FTP" in connection_check_block
    assert "secrets.SFTP_PASSWORD" in connection_check_block
    assert "tools/static_artifact_deploy_plan.py" in connection_check_block
    assert "Check FTP/SFTP connection without upload" in connection_check_block
    assert 'cls -1 "$SFTP_REMOTE_ROOT"' in connection_check_block
    assert "mirror -R" not in connection_check_block
