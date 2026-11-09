"""Native ontology prerequisite diagnostics preserve context verification boundaries."""

import json
import os
import subprocess
import sys
from pathlib import Path

pytest_plugins = ("test_project_ontology_context",)

TOOL = Path(__file__).resolve().parents[1] / "tools/ontology_doctor.py"


def run(root, *args, path=""):
    env = dict(os.environ, PATH=path, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--workspace-root",
            str(root),
            "--project-id",
            "project",
            *args,
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_reports_missing_compiler_and_selection(tmp_path):
    result = run(tmp_path)
    report = json.loads(result.stdout)
    assert result.returncode == 1
    assert report["compiler"]["status"] == "unavailable"
    assert report["context"]["outcome"] == "unavailable"
    assert len(report["next_steps"]) == 2
    assert not list(tmp_path.iterdir())


def test_selected_package_and_exact_compiler_pin(workspace):
    root, compiler, package, selection, _ = workspace
    selection([package()])
    # The fixture uses /usr/bin/env python3 to emulate ontologyc.
    result = run(
        root, "--selection", "selection.yaml", "--ontologyc", str(compiler), path=os.environ["PATH"]
    )
    report = json.loads(result.stdout)
    assert result.returncode == 0, result.stderr
    assert report["context"]["outcome"] == "verified"
    assert report["compiler"]["version"] is None
    assert len(report["compiler"]["sha256"]) == 64
    assert report["semantic_approval"] == "not_established"
    assert report["next_steps"] == []
    result = run(
        root,
        "--selection",
        "selection.yaml",
        "--ontologyc",
        str(compiler),
        "--compiler-sha256",
        "0" * 64,
        path=os.environ["PATH"],
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["context"]["outcome"] == "invalid"


def test_compiler_discovery_and_explicit_override(tmp_path):
    compiler = tmp_path / "ontologyc"
    compiler.write_text("#!/bin/sh\necho ontologyc 1.2.3\n")
    compiler.chmod(0o700)
    found = json.loads(run(tmp_path, path=str(tmp_path)).stdout)
    assert found["compiler"]["path"] == str(compiler)
    assert found["compiler"]["version"] == "1.2.3"
    missing = json.loads(run(tmp_path, "--ontologyc", "missing", path=str(tmp_path)).stdout)
    assert missing["compiler"]["status"] == "unavailable"
    assert missing["compiler"]["path"] == str(tmp_path / "missing")


def test_wrong_pin_never_executes_compiler(tmp_path):
    marker = tmp_path / "executed"
    compiler = tmp_path / "ontologyc"
    compiler.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
    compiler.chmod(0o700)
    result = run(tmp_path, "--ontologyc", str(compiler), "--compiler-sha256", "0" * 64)
    assert result.returncode == 2
    assert json.loads(result.stdout)["compiler"]["status"] == "invalid"
    assert not marker.exists()


def test_native_runtime_route_in_real_external_workspace(tmp_path):
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
    (root / "venv").symlink_to(Path(sys.prefix), target_is_directory=True)
    project = tmp_path / "project"
    project.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(source / "tools/native_runtime.py"),
            "run",
            "--installation",
            str(root),
            "--workspace",
            str(project),
            "ontology-doctor",
            "--project-id",
            "demo",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["artifact_kind"] == "specgraph_ontology_doctor"
    assert report["context"]["project_id"] == "demo"
    assert report["context"]["outcome"] == "unavailable"
