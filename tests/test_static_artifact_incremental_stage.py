from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "static_artifact_incremental_stage.py"
SPEC = importlib.util.spec_from_file_location("static_artifact_incremental_stage", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

IncrementalStageError = MODULE.IncrementalStageError
stage_changed_files = MODULE.stage_changed_files
verify_remote_bundle = MODULE.verify_remote_bundle


def _bundle(root: Path, files: dict[str, bytes]) -> Path:
    root.mkdir(parents=True)
    rows = []
    for relative_path, body in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        rows.append(
            {
                "path": relative_path,
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            }
        )
    (root / "artifact_manifest.json").write_text(json.dumps({"files": rows}), encoding="utf-8")
    (root / "checksums.sha256").write_text("checksums\n", encoding="utf-8")
    return root


def test_stage_copies_only_changed_payload_under_workspace_prefix(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path / "bundle", {"runs/a.json": b"same", "runs/b.json": b"new"})
    remote = {
        "files": [
            {"path": "runs/a.json", "sha256": hashlib.sha256(b"same").hexdigest()},
            {"path": "runs/b.json", "sha256": hashlib.sha256(b"old").hexdigest()},
            {"path": "runs/removed.json", "sha256": hashlib.sha256(b"gone").hexdigest()},
        ]
    }

    def fetch(url: str) -> bytes:
        if url.endswith("artifact_manifest.json"):
            return json.dumps(remote).encode()
        if url.endswith("runs/a.json"):
            return b"same"
        raise AssertionError(f"unexpected fetch: {url}")

    report = stage_changed_files(
        bundle_dir=bundle,
        remote_manifest_url="https://specgraph.tech/workspaces/example/artifact_manifest.json",
        staging_dir=tmp_path / "stage",
        staging_prefix="workspaces/example",
        fetcher=fetch,
    )

    assert report["summary"] == {
        "local_file_count": 2,
        "remote_file_count": 3,
        "changed_file_count": 1,
        "manifest_matched_but_stale_count": 0,
        "unchanged_file_count": 1,
        "removed_file_count": 1,
        "payload_bytes": 3,
    }
    assert report["changed_paths"] == ["runs/b.json"]
    assert report["removed_paths"] == ["runs/removed.json"]
    assert (tmp_path / "stage/workspaces/example/runs/b.json").read_bytes() == b"new"
    assert not (tmp_path / "stage/workspaces/example/runs/a.json").exists()


def test_stage_self_heals_manifest_matched_but_stale_remote_file(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path / "bundle", {"runs/a.json": b"expected"})
    remote = {
        "files": [
            {
                "path": "runs/a.json",
                "sha256": hashlib.sha256(b"expected").hexdigest(),
            }
        ]
    }

    report = stage_changed_files(
        bundle_dir=bundle,
        remote_manifest_url="https://specgraph.tech/artifact_manifest.json",
        staging_dir=tmp_path / "stage",
        fetcher=lambda url: (
            json.dumps(remote).encode() if url.endswith("artifact_manifest.json") else b"stale"
        ),
        workers=1,
    )

    assert report["changed_paths"] == ["runs/a.json"]
    assert report["summary"]["manifest_matched_but_stale_count"] == 1
    assert (tmp_path / "stage/runs/a.json").read_bytes() == b"expected"


def test_stage_rejects_unsafe_manifest_path(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "artifact_manifest.json").write_text(
        json.dumps({"files": [{"path": "../private", "sha256": "0" * 64}]}),
        encoding="utf-8",
    )
    (bundle / "checksums.sha256").write_text("checksums\n", encoding="utf-8")

    with pytest.raises(IncrementalStageError, match="unsafe"):
        stage_changed_files(
            bundle_dir=bundle,
            remote_manifest_url="https://specgraph.tech/artifact_manifest.json",
            staging_dir=tmp_path / "stage",
            fetcher=lambda _url: b'{"files": []}',
        )


def test_verify_remote_bundle_hashes_every_manifest_file(tmp_path: Path) -> None:
    files = {"specs/a.yaml": b"a", "runs/b.json": b"b"}
    bundle = _bundle(tmp_path / "bundle", files)

    remote_files = {
        **files,
        "artifact_manifest.json": (bundle / "artifact_manifest.json").read_bytes(),
        "checksums.sha256": (bundle / "checksums.sha256").read_bytes(),
    }
    report = verify_remote_bundle(
        bundle_dir=bundle,
        remote_base_url="https://specgraph.tech/workspaces/example",
        fetcher=lambda url: remote_files[url.split("/workspaces/example/", 1)[1]],
        workers=2,
    )

    assert report["status"] == "verified"
    assert report["summary"] == {
        "verified_file_count": 2,
        "verified_metadata_file_count": 2,
        "failure_count": 0,
    }


def test_verify_remote_bundle_fails_on_digest_drift(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path / "bundle", {"runs/a.json": b"expected"})

    def fetch(url: str) -> bytes:
        name = url.rsplit("/", 1)[1]
        if name in {"artifact_manifest.json", "checksums.sha256"}:
            return (bundle / name).read_bytes()
        return b"foreign"

    with pytest.raises(IncrementalStageError, match="digest mismatch"):
        verify_remote_bundle(
            bundle_dir=bundle,
            remote_base_url="https://specgraph.tech/workspaces/example",
            fetcher=fetch,
            workers=1,
        )


def test_verify_remote_bundle_fails_on_stale_published_manifest(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path / "bundle", {"runs/a.json": b"expected"})

    with pytest.raises(IncrementalStageError, match="metadata digest mismatch"):
        verify_remote_bundle(
            bundle_dir=bundle,
            remote_base_url="https://specgraph.tech/workspaces/example",
            fetcher=lambda _url: b"stale",
            workers=1,
        )
