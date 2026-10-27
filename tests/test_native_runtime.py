"""Safety and path boundaries of the native runtime installer."""

import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "native_runtime", Path(__file__).resolve().parents[1] / "tools" / "native_runtime.py"
)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


def test_existing_installation_is_not_overwritten(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "data"
    marker.write_text("keep")
    with pytest.raises(ValueError, match="already exists"):
        runtime.install("unused", "a" * 40, destination)
    assert marker.read_text() == "keep"


def test_archive_rejects_traversal_before_extracting(tmp_path):
    archive = tmp_path / "bad.tar"
    with tarfile.open(archive, "w") as bundle:
        entry = tarfile.TarInfo("../escaped")
        entry.size = 1
        bundle.addfile(entry, io.BytesIO(b"x"))
    destination = tmp_path / "snapshot"
    destination.mkdir()
    with pytest.raises(ValueError, match="Unsupported archive"):
        runtime.extract_snapshot(archive, destination)
    assert not (tmp_path / "escaped").exists()


def test_incomplete_installation_is_not_usable(tmp_path):
    root = tmp_path / "runtime"
    root.mkdir()
    (root / "runtime.json").write_text(json.dumps({"status": "installing"}))
    with pytest.raises(ValueError, match="not ready"):
        runtime.run(root, tmp_path / "workspace", "supervisor", ["--dry-run"])


def test_non_full_sha_rejected_without_creating_destination(tmp_path):
    target = tmp_path / "runtime"
    with pytest.raises(ValueError, match="full lowercase"):
        runtime.install("unused", "deadbeef", target)
    assert not target.exists()
