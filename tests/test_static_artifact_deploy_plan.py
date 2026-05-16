from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def deploy_plan_module() -> object:
    module_path = Path(__file__).resolve().parents[1] / "tools" / "static_artifact_deploy_plan.py"
    spec = importlib.util.spec_from_file_location(
        "test_static_artifact_deploy_plan_module", module_path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def bundle_dir(tmp_path: Path) -> Path:
    bundle = tmp_path / "dist" / "specgraph-public"
    (bundle / "specs").mkdir(parents=True)
    (bundle / "runs").mkdir()
    (bundle / "artifact_manifest.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (bundle / "checksums.sha256").write_text("abc  artifact_manifest.json\n", encoding="utf-8")
    return bundle


def test_ftps_plan_requires_password_secret(
    deploy_plan_module: object,
    bundle_dir: Path,
) -> None:
    env = {
        "SFTP_HOST": "example.invalid",
        "SFTP_PORT": "21",
        "SFTP_USER": "dry-run",
        "SFTP_PRIVATE_KEY": "legacy-password",
        "SFTP_REMOTE_ROOT": "/",
    }

    with pytest.raises(deploy_plan_module.DeployPlanError, match="SFTP_PASSWORD"):
        deploy_plan_module.build_deploy_plan(env, bundle_dir)


def test_ftps_plan_uses_password_and_requires_tls(
    deploy_plan_module: object,
    bundle_dir: Path,
) -> None:
    plan = deploy_plan_module.build_deploy_plan(
        {
            "SFTP_HOST": "example.invalid",
            "SFTP_PORT": "21",
            "SFTP_USER": "dry-run",
            "SFTP_PASSWORD": "password",
            "SFTP_PRIVATE_KEY": "",
            "SFTP_REMOTE_ROOT": "/",
        },
        bundle_dir,
    )

    assert plan["transport"] == "ftps"
    assert plan["auth_kind"] == "password"
    assert plan["tls"] == "required"
    assert plan["known_hosts_required"] is False


def test_sftp_plan_allows_private_key_auth(
    deploy_plan_module: object,
    bundle_dir: Path,
) -> None:
    plan = deploy_plan_module.build_deploy_plan(
        {
            "SFTP_HOST": "example.invalid",
            "SFTP_PORT": "22",
            "SFTP_USER": "dry-run",
            "SFTP_PRIVATE_KEY": "\n".join(
                [
                    "-----BEGIN OPENSSH PRIVATE KEY-----",
                    "key",
                    "-----END OPENSSH PRIVATE KEY-----",
                ]
            ),
            "SFTP_KNOWN_HOSTS": "example.invalid ssh-ed25519 AAAA",
            "SFTP_REMOTE_ROOT": "/",
        },
        bundle_dir,
    )

    assert plan["transport"] == "sftp"
    assert plan["auth_kind"] == "private_key"
    assert plan["auth_source"] == "SFTP_PRIVATE_KEY"


def test_sftp_plan_requires_known_hosts(
    deploy_plan_module: object,
    bundle_dir: Path,
) -> None:
    env = {
        "SFTP_HOST": "example.invalid",
        "SFTP_PORT": "22",
        "SFTP_USER": "dry-run",
        "SFTP_PASSWORD": "password",
        "SFTP_REMOTE_ROOT": "/",
    }

    with pytest.raises(deploy_plan_module.DeployPlanError, match="SFTP_KNOWN_HOSTS"):
        deploy_plan_module.build_deploy_plan(env, bundle_dir)


def test_deploy_plan_skips_when_host_is_not_configured(
    deploy_plan_module: object,
    bundle_dir: Path,
) -> None:
    plan = deploy_plan_module.build_deploy_plan({}, bundle_dir)

    assert plan == {
        "configured": False,
        "status": "skipped",
        "reason": "SFTP_HOST is not configured",
    }


def test_deploy_plan_requires_complete_bundle(
    deploy_plan_module: object,
    tmp_path: Path,
) -> None:
    with pytest.raises(deploy_plan_module.DeployPlanError, match="deploy bundle is incomplete"):
        deploy_plan_module.build_deploy_plan({}, tmp_path / "missing")
