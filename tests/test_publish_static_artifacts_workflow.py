from __future__ import annotations

from pathlib import Path


def test_ftps_deploy_requires_password_secret_without_private_key_fallback() -> None:
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "publish-static-artifacts.yml"
    )
    workflow = workflow_path.read_text(encoding="utf-8")

    ftp_block = workflow.split('if [ "$DEPLOY_PORT" = "21" ]; then', 1)[1].split(
        "\n          fi",
        1,
    )[0]

    assert 'test -n "$SFTP_PASSWORD"' in ftp_block
    assert 'lftp -u "$SFTP_USER,$SFTP_PASSWORD"' in ftp_block
    assert "DEPLOY_PASSWORD" not in ftp_block
    assert "SFTP_PRIVATE_KEY" not in ftp_block
