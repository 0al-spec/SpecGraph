"""Safety and path boundaries of the native runtime installer."""

import importlib.util
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
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


def test_local_git_sources_use_caller_root_and_remote_syntax_stays_unchanged(tmp_path):
    assert runtime.resolve_git_source(".", tmp_path) == str(tmp_path.resolve())
    assert runtime.resolve_git_source("../repository with spaces", tmp_path) == str(
        (tmp_path / "../repository with spaces").resolve()
    )
    for source in (
        "https://github.com/0al-spec/SpecGraph.git",
        "ssh://git@example.com/repository",
        "git@example.com:owner/repository.git",
        "example.com:owner/repository.git",
        "file:///tmp/source.git",
    ):
        assert runtime.resolve_git_source(source, tmp_path) == source


def test_ready_spec_requires_a_complete_versioned_receipt():
    from native_runtime_context import RuntimeReadyFacts
    from native_runtime_ready_spec import RUNTIME_READY_SPEC

    ready = RuntimeReadyFacts("specgraph_native_runtime", "installed", 1, "a" * 40)
    assert RUNTIME_READY_SPEC.is_satisfied_by(ready)
    assert not RUNTIME_READY_SPEC.is_satisfied_by(
        RuntimeReadyFacts(ready.artifact_kind, ready.status, True, ready.source_commit)
    )
    assert not RUNTIME_READY_SPEC.is_satisfied_by(
        RuntimeReadyFacts(ready.artifact_kind, ready.status, 1, "incomplete")
    )
