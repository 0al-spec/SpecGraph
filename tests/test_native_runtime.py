"""Safety and path boundaries of the native runtime installer."""

import importlib.util
import io
import json
import shutil
import subprocess
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


@pytest.mark.parametrize(
    ("operation", "tool"),
    [
        ("next-move", "product_workspace_next_moves.py"),
        ("lint", "spec_yaml_lint.py"),
        ("ontology-context", "project_ontology_context_cli.py"),
        ("ontology-doctor", "ontology_doctor.py"),
        ("ontology-overview", "ontology_overview_cli.py"),
    ],
)
def test_advisory_route_uses_selected_workspace(tmp_path, monkeypatch, operation, tool):
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
    assert runtime.run(root, workspace, operation, ["--help"]) == 1
    command, options = calls[-1]
    assert command[1].endswith(f"tools/{tool}")
    assert command[2:4] == ["--workspace-root", str(workspace)]
    assert options["cwd"] == workspace and "PYTHONPATH" not in options["env"]
    for supplied in (["--workspace-root", "/elsewhere"], ["--workspace-root=/elsewhere"]):
        with pytest.raises(ValueError, match="selected by --workspace"):
            runtime.run(root, workspace, operation, supplied)
    assert runtime.run(root, workspace, "init", ["--project-id", "demo"]) == 1
    assert calls[-1][0][1].endswith("tools/supervisor.py")


@pytest.fixture
def lint_runtime(tmp_path):
    installation = tmp_path / "runtime"
    installation.mkdir()
    source = Path(__file__).resolve().parents[1]
    (installation / "source").symlink_to(source, target_is_directory=True)
    (installation / "venv").symlink_to(Path(sys.prefix), target_is_directory=True)
    (installation / "runtime.json").write_text(
        json.dumps(
            {
                "artifact_kind": "specgraph_native_runtime",
                "status": "installed",
                "schema_version": 1,
                "source_commit": "a" * 40,
            }
        )
    )
    workspace = tmp_path / "project with spaces"
    (workspace / "specs/nodes").mkdir(parents=True)
    (workspace / "docs/drafts").mkdir(parents=True)
    command = [
        sys.executable,
        str(source / "tools" / "native_runtime.py"),
        "run",
        "--installation",
        str(installation),
        "--workspace",
        str(workspace),
        "lint",
        "--",
    ]
    return workspace, command


def test_native_lint_reports_executed_checks_for_each_workspace_file(lint_runtime):
    workspace, command = lint_runtime
    node = workspace / "specs/nodes/PRODUCT-SPEC-0001.yaml"
    source = (
        "id: PRODUCT-SPEC-0001\n"
        "kind: spec\n"
        "created_at: '2026-11-16T06:00:00Z'\n"
        "updated_at: '2026-11-16T06:00:00Z'\n"
        "acceptance:\n"
        "- One criterion.\n"
    )
    node.write_text(source)
    draft = workspace / "docs/drafts/PRODUCT-SPEC-0002.yaml"
    node_arg, draft_arg = (str(path.relative_to(workspace)) for path in (node, draft))

    passed = subprocess.run(
        [*command, node_arg], cwd=workspace.parent, capture_output=True, text=True
    )
    assert passed.returncode == 0, passed.stderr
    report = json.loads(passed.stdout)
    assert report["artifact_kind"] == "specgraph_yaml_lint"
    assert report["schema_version"] == 1
    assert report["status"] == "passed"
    checks = [
        "yaml_mapping_and_unique_keys",
        "evidence_claim_declarations",
        "spec_timestamps",
        "acceptance_shape",
        "acceptance_evidence_shape",
        "canonical_format",
    ]
    assert report["files"] == [{"path": node_arg, "checks_run": checks, "issues": []}]

    draft.write_text("id: one\nid: two\n")
    failed = subprocess.run(
        [*command, node_arg, draft_arg], cwd=workspace.parent, capture_output=True, text=True
    )
    assert failed.returncode == 1, failed.stderr
    report = json.loads(failed.stdout)
    assert report["status"] == "failed"
    assert report["files"] == [
        {"path": node_arg, "checks_run": checks, "issues": []},
        {
            "path": draft_arg,
            "checks_run": ["yaml_mapping_and_unique_keys"],
            "issues": ["duplicate key: 'id'"],
        },
    ]

    draft_source = source.replace("0001", "0002").replace(
        "updated_at: '2026-11-16T06:00:00Z'\n", ""
    )
    draft_source = "# Noncanonical formatting\n" + draft_source
    draft.write_text(draft_source)
    failed = subprocess.run([*command, draft_arg], capture_output=True, text=True)
    assert failed.returncode == 1
    result = json.loads(failed.stdout)["files"][0]
    assert result["checks_run"] == checks
    assert result["issues"] == [
        "updated_at must be a non-empty ISO 8601 timestamp string",
        "file is not canonically formatted",
    ]
    assert draft.read_text() == draft_source
    assert node.read_text() == source
    assert not (workspace / "runs").exists()


def test_native_lint_refuses_unselected_and_escaping_paths(lint_runtime):
    workspace, command = lint_runtime
    external = workspace.parent / "outside.yaml"
    external.write_text("private: value\n")
    (workspace / "specs/nodes/link.yaml").symlink_to(external)
    (workspace / "docs/drafts/linked").symlink_to(workspace.parent, target_is_directory=True)
    for arguments in (
        [],
        [str(external)],
        ["docs/drafts/../../outside.yaml"],
        ["specs/nodes/link.yaml"],
        ["docs/drafts/linked/outside.yaml"],
        ["--workspace-r", str(workspace.parent)],
    ):
        result = subprocess.run([*command, *arguments], capture_output=True, text=True)
        assert result.returncode == 2 and not result.stdout
        assert "error:" in result.stderr


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
    interpreter_root = Path(sys.prefix)
    assert (interpreter_root / "bin" / "python").is_file()
    (root / "venv").symlink_to(interpreter_root, target_is_directory=True)
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


@pytest.fixture
def overview_runtime(tmp_path):
    """Copy only the required engine modules; product commands cannot use the checkout."""
    installation = tmp_path / "runtime with spaces"
    tools = installation / "source/tools"
    tools.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / "tools"
    for name in (
        "native_runtime.py",
        "native_runtime_context.py",
        "native_runtime_ready_spec.py",
        "ontology_overview_cli.py",
        "ontology_snapshot.py",
    ):
        shutil.copyfile(source / name, tools / name)
    shutil.copytree(
        source / "ontology_overview",
        tools / "ontology_overview",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (installation / "venv").symlink_to(Path(sys.prefix), target_is_directory=True)
    (installation / "runtime.json").write_text(
        json.dumps(
            {
                "artifact_kind": "specgraph_native_runtime",
                "status": "installed",
                "schema_version": 1,
                "source_commit": "a" * 40,
            }
        )
    )
    workspace, caller = tmp_path / "product with spaces", tmp_path / "caller"
    workspace.mkdir()
    caller.mkdir()
    (workspace / "selection.hc").write_text("Selected\n")
    (workspace / "selection.hcs").write_text("Selected:\n")
    # A wrong cwd must not accidentally find usable inputs.
    for directory in (installation, caller):
        (directory / "selection.hc").write_bytes(b"\xff")
    command = [
        sys.executable,
        str(tools / "native_runtime.py"),
        "run",
        "--installation",
        str(installation),
        "--workspace",
        str(workspace),
        "ontology-overview",
        "--",
    ]
    arguments = [
        "--hc",
        "selection.hc",
        "--hcs",
        "selection.hcs",
        "--hypercode",
        str(tmp_path / "missing-hypercode"),
        "--ontologyc",
        str(tmp_path / "missing-ontologyc"),
        "--output-dir",
        "review-output",
    ]
    return installation, workspace, caller, command, arguments


def test_native_overview_forwards_help_and_unavailable_status(overview_runtime):
    installation, workspace, caller, command, arguments = overview_runtime
    help_result = subprocess.run([*command, "--help"], cwd=caller, capture_output=True, text=True)
    assert help_result.returncode == 0
    assert "--hc" in help_result.stdout and "--output-dir" in help_result.stdout
    result = subprocess.run([*command, *arguments], cwd=caller, capture_output=True, text=True)
    assert result.returncode == 1 and not result.stdout
    assert json.loads(result.stderr)["status"] == "unavailable"
    assert not (workspace / "review-output").exists()
    assert not (caller / "review-output").exists()
    assert not (installation / "review-output").exists()


@pytest.mark.parametrize(
    "option", ["--workspace-root", "--workspace-root=", "--workspace-r", "--workspace-r="]
)
def test_native_overview_cannot_forward_a_foreign_workspace(overview_runtime, option):
    installation, workspace, caller, command, arguments = overview_runtime
    override = [option + str(caller)] if option.endswith("=") else [option, str(caller)]
    result = subprocess.run(
        [*command, *arguments, *override], cwd=caller, capture_output=True, text=True
    )
    assert result.returncode == 2 and not result.stdout
    if option.startswith("--workspace-root"):
        assert "selected by --workspace" in json.loads(result.stderr)["error"]
    else:
        assert "unrecognized arguments" in result.stderr
    for directory in (installation, workspace, caller):
        assert not (directory / "review-output").exists()


def test_native_overview_preserves_an_existing_output(overview_runtime):
    _, workspace, caller, command, arguments = overview_runtime
    output = workspace / "review-output"
    output.mkdir()
    marker = output / "context.hc"
    marker.write_bytes(b"Existing\n")
    result = subprocess.run([*command, *arguments], cwd=caller, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["status"] == "invalid"
    assert marker.read_bytes() == b"Existing\n"
