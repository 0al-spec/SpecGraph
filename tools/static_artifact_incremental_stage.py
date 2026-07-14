#!/usr/bin/env python3
"""Stage changed static artifacts and verify the published HTTP surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from typing import Any


class IncrementalStageError(ValueError):
    pass


Fetcher = Callable[[str], bytes]


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def _safe_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise IncrementalStageError("manifest file path must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value != path.as_posix():
        raise IncrementalStageError(f"manifest file path is unsafe: {value!r}")
    return value


def _manifest_files(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise IncrementalStageError("artifact manifest must contain files[]")
    files: dict[str, dict[str, Any]] = {}
    for row in payload["files"]:
        if not isinstance(row, dict):
            raise IncrementalStageError("artifact manifest files[] entries must be objects")
        path = _safe_path(row.get("path"))
        digest = row.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise IncrementalStageError(f"manifest sha256 is invalid for {path}")
        if path in files:
            raise IncrementalStageError(f"artifact manifest contains duplicate path: {path}")
        files[path] = row
    return files


def _load_local_manifest(bundle_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = bundle_dir / "artifact_manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IncrementalStageError(f"cannot read local artifact manifest: {exc}") from exc
    files = _manifest_files(payload)
    for relative_path, row in files.items():
        source = bundle_dir / relative_path
        if not source.is_file():
            raise IncrementalStageError(f"local manifest path is missing: {relative_path}")
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != row["sha256"]:
            raise IncrementalStageError(f"local manifest digest mismatch: {relative_path}")
    if not (bundle_dir / "checksums.sha256").is_file():
        raise IncrementalStageError("local bundle is missing checksums.sha256")
    return payload, files


def _remote_files(url: str, fetcher: Fetcher) -> tuple[dict[str, dict[str, Any]], bool]:
    try:
        payload = json.loads(fetcher(url))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {}, False
        raise IncrementalStageError(f"remote manifest request failed: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise IncrementalStageError(f"remote manifest request failed: {exc}") from exc
    return _manifest_files(payload), True


def stage_changed_files(
    *,
    bundle_dir: Path,
    remote_manifest_url: str,
    staging_dir: Path,
    staging_prefix: str = "",
    fetcher: Fetcher = _fetch,
) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(remote_manifest_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise IncrementalStageError("remote manifest URL must use absolute HTTPS")
    prefix = _safe_path(staging_prefix) if staging_prefix else ""
    _, local_files = _load_local_manifest(bundle_dir)
    remote_files, remote_manifest_available = _remote_files(remote_manifest_url, fetcher)
    changed = sorted(
        path
        for path, row in local_files.items()
        if remote_files.get(path, {}).get("sha256") != row["sha256"]
    )
    removed = sorted(set(remote_files) - set(local_files))
    payload_bytes = 0
    for relative_path in changed:
        source = bundle_dir / relative_path
        destination = staging_dir / prefix / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            raise IncrementalStageError(f"staging path collision: {destination}")
        shutil.copyfile(source, destination)
        payload_bytes += source.stat().st_size
    return {
        "artifact_kind": "specgraph_static_artifact_incremental_stage_report",
        "schema_version": 1,
        "status": "ready",
        "bundle_dir": str(bundle_dir),
        "remote_manifest_url": remote_manifest_url,
        "staging_prefix": prefix,
        "remote_manifest_available": remote_manifest_available,
        "publication_required": bool(changed or removed or not remote_manifest_available),
        "summary": {
            "local_file_count": len(local_files),
            "remote_file_count": len(remote_files),
            "changed_file_count": len(changed),
            "unchanged_file_count": len(local_files) - len(changed),
            "removed_file_count": len(removed),
            "payload_bytes": payload_bytes,
        },
        "changed_paths": changed,
        "removed_paths": removed,
    }


def verify_remote_bundle(
    *,
    bundle_dir: Path,
    remote_base_url: str,
    fetcher: Fetcher = _fetch,
    workers: int = 12,
) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(remote_base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise IncrementalStageError("remote base URL must use absolute HTTPS")
    _, local_files = _load_local_manifest(bundle_dir)
    base_url = remote_base_url.rstrip("/")

    def verify(item: tuple[str, dict[str, Any]]) -> str:
        path, row = item
        try:
            body = fetcher(f"{base_url}/{path}")
        except Exception as exc:
            raise IncrementalStageError(
                f"remote artifact request failed for {path}: {exc}"
            ) from exc
        actual = hashlib.sha256(body).hexdigest()
        if actual != row["sha256"]:
            raise IncrementalStageError(f"remote artifact digest mismatch: {path}")
        return path

    with ThreadPoolExecutor(max_workers=workers) as pool:
        verified = list(pool.map(verify, local_files.items()))
    return {
        "artifact_kind": "specgraph_static_artifact_remote_verification_report",
        "schema_version": 1,
        "status": "verified",
        "remote_base_url": base_url,
        "summary": {"verified_file_count": len(verified), "failure_count": 0},
    }


def _write_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    stage = subparsers.add_parser("stage")
    stage.add_argument("--bundle-dir", type=Path, required=True)
    stage.add_argument("--remote-manifest-url", required=True)
    stage.add_argument("--staging-dir", type=Path, required=True)
    stage.add_argument("--staging-prefix", default="")
    stage.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--bundle-dir", type=Path, required=True)
    verify.add_argument("--remote-base-url", required=True)
    verify.add_argument("--attempts", type=int, default=3)
    verify.add_argument("--retry-delay-seconds", type=float, default=5.0)
    verify.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "stage":
            report = stage_changed_files(
                bundle_dir=args.bundle_dir.resolve(),
                remote_manifest_url=args.remote_manifest_url,
                staging_dir=args.staging_dir.resolve(),
                staging_prefix=args.staging_prefix,
            )
        else:
            if args.attempts < 1:
                raise IncrementalStageError("verification attempts must be positive")
            last_error: IncrementalStageError | None = None
            for attempt in range(1, args.attempts + 1):
                try:
                    report = verify_remote_bundle(
                        bundle_dir=args.bundle_dir.resolve(),
                        remote_base_url=args.remote_base_url,
                    )
                    report["attempt"] = attempt
                    break
                except IncrementalStageError as exc:
                    last_error = exc
                    if attempt < args.attempts:
                        time.sleep(args.retry_delay_seconds)
            else:
                raise last_error or IncrementalStageError("remote verification failed")
        _write_report(report, args.output.resolve())
    except IncrementalStageError as exc:
        print(f"incremental static artifact error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
