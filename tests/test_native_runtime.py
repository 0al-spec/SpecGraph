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


def test_unsupported_python_fails_before_destination_creation(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(runtime.sys, "version_info", (3, 9, 6))
    target = tmp_path / "runtime"
    assert (
        runtime.main(
            ["install", "--source", ".", "--revision", "a" * 40, "--destination", str(target)]
        )
        == 2
    )
    error = json.loads(capsys.readouterr().err)["error"]
    assert "Python 3.10 or newer" in error
    assert "3.9.6" in error and runtime.sys.executable in error
    assert not target.exists()


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


def test_ontology_context_route_uses_selected_workspace(tmp_path, monkeypatch):
    root = tmp_path / "runtime"
    root.mkdir()
    (root / "runtime.json").write_text(
        json.dumps(
            {
                "artifact_kind": "specgraph_native_runtime",
                "status": "installed",
                "schema_version": 1,
                "source_commit": "a" * 40,
            }
        )
    )
    workspace = tmp_path / "product"
    workspace.mkdir()
    calls = []
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda command, **kwargs: (
            calls.append((command, kwargs)) or type("Result", (), {"returncode": 1})()
        ),
    )
    monkeypatch.setenv("PYTHONPATH", "untrusted")
    assert runtime.run(root, workspace, "ontology-context", ["--project-id", "demo"]) == 1
    command, options = calls[-1]
    assert command[1].endswith("tools/project_ontology_context_cli.py")
    assert command[2:4] == ["--workspace-root", str(workspace)]
    assert options["cwd"] == workspace and "PYTHONPATH" not in options["env"]
    for supplied in (["--workspace-root", "/elsewhere"], ["--workspace-root=/elsewhere"]):
        with pytest.raises(ValueError, match="selected by --workspace"):
            runtime.run(root, workspace, "ontology-context", supplied)
    assert runtime.run(root, workspace, "init", ["--project-id", "demo"]) == 1
    assert calls[-1][0][1].endswith("tools/supervisor.py")


def test_ontology_context_launcher_runs_in_external_workspace(tmp_path):
    import subprocess

    root = tmp_path / "runtime"
    root.mkdir()
    (root / "runtime.json").write_text(
        json.dumps(
            {
                "artifact_kind": "specgraph_native_runtime",
                "status": "installed",
                "schema_version": 1,
                "source_commit": "a" * 40,
            }
        )
    )
    source = Path(__file__).resolve().parents[1]
    (root / "source").symlink_to(source, target_is_directory=True)
    (root / "venv").symlink_to(source / ".venv", target_is_directory=True)
    workspace = tmp_path / "product"
    workspace.mkdir()
    process = subprocess.run(
        [
            sys.executable,
            str(source / "tools" / "native_runtime.py"),
            "run",
            "--installation",
            str(root),
            "--workspace",
            str(workspace),
            "ontology-context",
            "--project-id",
            "demo",
        ],
        capture_output=True,
        text=True,
    )
    assert process.returncode == 1, process.stderr
    assert json.loads(process.stdout)["outcome"] == "unavailable"
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    for target in (foreign, root):
        (target / "specgraph.project.yaml").write_text(
            "artifact_kind: specgraph_project_config\nproject_id: foreign\n"
        )
        for option in ("--workspace-r", f"--workspace-r={target}"):
            forwarded = [option, str(target)] if option == "--workspace-r" else [option]
            attack = subprocess.run(
                [
                    sys.executable,
                    str(source / "tools" / "native_runtime.py"),
                    "run",
                    "--installation",
                    str(root),
                    "--workspace",
                    str(workspace),
                    "ontology-context",
                    *forwarded,
                    "--output",
                    "report.json",
                ],
                capture_output=True,
                text=True,
            )
            assert attack.returncode == 2
            assert not attack.stdout and "unrecognized arguments" in attack.stderr
            assert not (target / "report.json").exists()
            assert not (workspace / "report.json").exists()
