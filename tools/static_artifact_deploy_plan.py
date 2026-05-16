#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path


class DeployPlanError(ValueError):
    pass


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _require(name: str, value: str) -> str:
    if not value:
        raise DeployPlanError(f"missing required deploy setting: {name}")
    return value


def _contains_private_key(value: str) -> bool:
    return bool(re.search(r"BEGIN .*PRIVATE KEY", value))


def _bool_secret(name: str, value: str) -> bool:
    if value in {"", "false"}:
        return False
    if value == "true":
        return True
    raise DeployPlanError(f"{name} must be unset, 'false', or 'true'")


def validate_bundle_dir(bundle_dir: Path) -> None:
    required_paths = [
        bundle_dir / "artifact_manifest.json",
        bundle_dir / "checksums.sha256",
        bundle_dir / "specs",
        bundle_dir / "runs",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise DeployPlanError(f"deploy bundle is incomplete: missing {', '.join(missing)}")


def build_deploy_plan(env: Mapping[str, str], bundle_dir: Path) -> dict[str, object]:
    validate_bundle_dir(bundle_dir)

    host = _clean(env.get("SFTP_HOST"))
    if not host:
        return {
            "configured": False,
            "status": "skipped",
            "reason": "SFTP_HOST is not configured",
        }

    user = _require("SFTP_USER", _clean(env.get("SFTP_USER")))
    remote_root = _require("SFTP_REMOTE_ROOT", _clean(env.get("SFTP_REMOTE_ROOT")))
    port = _clean(env.get("SFTP_PORT")) or "22"
    password = _clean(env.get("SFTP_PASSWORD"))
    private_key = _clean(env.get("SFTP_PRIVATE_KEY"))
    known_hosts = _clean(env.get("SFTP_KNOWN_HOSTS"))
    allow_unverified_ftps_cert = _bool_secret(
        "FTPS_ALLOW_UNVERIFIED_CERT",
        _clean(env.get("FTPS_ALLOW_UNVERIFIED_CERT")),
    )

    if port == "21":
        _require("SFTP_PASSWORD", password)
        return {
            "configured": True,
            "status": "ready",
            "transport": "ftps",
            "host": host,
            "port": port,
            "user": user,
            "remote_root": remote_root,
            "auth_kind": "password",
            "tls": "required",
            "certificate_verification": (
                "disabled_by_explicit_opt_in" if allow_unverified_ftps_cert else "enabled"
            ),
            "accepted_risk": (
                "ftps_certificate_identity_not_verified" if allow_unverified_ftps_cert else None
            ),
            "known_hosts_required": False,
            "network_upload": "not_performed_by_validator",
        }

    _require("SFTP_KNOWN_HOSTS", known_hosts)
    if _contains_private_key(private_key):
        auth_kind = "private_key"
        auth_source = "SFTP_PRIVATE_KEY"
    elif password:
        auth_kind = "password"
        auth_source = "SFTP_PASSWORD"
    elif private_key:
        auth_kind = "password"
        auth_source = "SFTP_PRIVATE_KEY_COMPAT_PASSWORD"
    else:
        raise DeployPlanError("missing required deploy setting: SFTP_PASSWORD or SFTP_PRIVATE_KEY")

    return {
        "configured": True,
        "status": "ready",
        "transport": "sftp",
        "host": host,
        "port": port,
        "user": user,
        "remote_root": remote_root,
        "auth_kind": auth_kind,
        "auth_source": auth_source,
        "known_hosts_required": True,
        "network_upload": "not_performed_by_validator",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate static artifact deploy settings.")
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=Path("dist/specgraph-public"),
        help="Built static artifact bundle directory.",
    )
    args = parser.parse_args(argv)

    try:
        plan = build_deploy_plan(os.environ, args.bundle_dir)
    except DeployPlanError as exc:
        print(f"deploy plan error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
