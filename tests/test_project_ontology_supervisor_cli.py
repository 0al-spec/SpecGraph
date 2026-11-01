"""Supervisor entry point for explicit ontology checks in product workspaces."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SUPERVISOR = Path(__file__).resolve().parents[1] / "tools" / "supervisor.py"


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "product"
    specs = root / "specs" / "nodes"
    specs.mkdir(parents=True)
    (specs / "SG-SPEC-0001.yaml").write_text("id: SG-SPEC-0001\nkind: spec\n")
    return root


def call(workspace, *args):
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, str(SUPERVISOR), *args],
        cwd=workspace,
        text=True,
        capture_output=True,
        env=environment,
    )


def test_external_workspace_missing_selection_persists_unavailable(workspace):
    target = workspace / "specs/nodes/SG-SPEC-0001.yaml"
    before = target.read_bytes()
    result = call(
        workspace,
        "--build-project-ontology-context-check",
        "--target-spec",
        "SG-SPEC-0001",
        "--ontology-context-project-id",
        "demo",
    )
    assert result.returncode == 1, result.stderr
    summary = json.loads(result.stdout)
    assert summary["outcome"] == "unavailable"
    assert summary["context_outcome"] == "unavailable"
    output = workspace / summary["report_path"]
    report = json.loads(output.read_text())
    assert report["outcome"] == "unavailable" and report["target_spec_id"] == "SG-SPEC-0001"
    assert target.read_bytes() == before
    full = call(
        workspace,
        "--build-project-ontology-context-check",
        "--target-spec",
        "SG-SPEC-0001",
        "--ontology-context-project-id",
        "demo",
        "--output-mode",
        "full",
        "--ontology-context-previous-report",
        summary["report_path"],
    )
    assert full.returncode == 1
    assert json.loads(full.stdout)["previous_freshness"] is not None


@pytest.mark.parametrize("target_id", ["SG-SPEC-0001", "GITVIEW-SPEC-0001", "ACME-UI-SPEC-12345"])
def test_product_spec_namespace_reaches_context_check_without_source_mutation(workspace, target_id):
    target = workspace / "specs/nodes" / f"{target_id}.yaml"
    target.write_text(f"id: {target_id}\nkind: spec\n")
    policy = workspace / ".specgraph/spec-id-policy.json"
    policy.parent.mkdir()
    policy.write_text(
        json.dumps({"schema_version": 1, "prefix": target_id.rsplit("-", 1)[0], "aliases": {}})
    )
    before = target.read_bytes(), policy.read_bytes()
    result = call(
        workspace,
        "--build-project-ontology-context-check",
        "--target-spec",
        target_id,
        "--ontology-context-project-id",
        "demo",
        "--output-mode",
        "full",
    )
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["outcome"] == "unavailable"
    assert report["target"]["id"] == target_id
    assert report["target"]["path"] == f"specs/nodes/{target_id}.yaml"
    saved = workspace / "runs/project_ontology_context" / f"{target_id}.json"
    assert json.loads(saved.read_text()) == report
    assert (target.read_bytes(), policy.read_bytes()) == before
    assert report["canonical_mutations_allowed"] is False


@pytest.mark.parametrize(
    "arguments",
    [
        ("--build-project-ontology-context-check", "--ontology-context-project-id", "demo"),
        ("--build-project-ontology-context-check", "--target-spec", "SG-SPEC-0001"),
        (
            "--build-project-ontology-context-check",
            "--target-spec",
            "../../other",
            "--ontology-context-project-id",
            "demo",
        ),
        ("--ontology-context-project-id", "demo"),
        (
            "--build-project-ontology-context-check",
            "--target-spec",
            "SG-SPEC-0001",
            "--ontology-context-project-id",
            "demo",
            "--auto-approve",
        ),
        (
            "--build-project-ontology-context-check",
            "--target-spec",
            "SG-SPEC-0001",
            "--ontology-context-project-id",
            "demo",
            "--loop",
        ),
        (
            "--build-project-ontology-context-check",
            "--target-spec",
            "SG-SPEC-0001",
            "--ontology-context-project-id",
            "demo",
            "--resolve-gate",
            "SG-SPEC-0001",
        ),
        (
            "--build-project-ontology-context-check",
            "--target-spec",
            "SG-SPEC-0001",
            "--ontology-context-project-id",
            "demo",
            "--workspace-r",
            "/tmp",
        ),
        (
            "--build-project-ontology-context-check",
            "--target-spec",
            "SG-SPEC-0001",
            "--ontology-context-project-id",
            "demo",
            "--ontology-context-selection",
            "../escape",
        ),
    ],
)
def test_input_errors_have_no_report(workspace, arguments):
    result = call(workspace, *arguments)
    assert result.returncode == 2, result.stderr
    assert not result.stdout and not (workspace / "runs").exists()


@pytest.mark.parametrize(
    "target_id",
    [
        "../GITVIEW-SPEC-0001",
        "GITVIEW-SPEC-0001/child",
        "GITVIEW-SPEC-0001\n",
        "GITVIEW-SPEC-０００１",
        "gitview-SPEC-0001",
    ],
)
def test_product_namespace_cannot_bypass_cli_path_validation(workspace, target_id):
    result = call(
        workspace,
        "--build-project-ontology-context-check",
        "--target-spec",
        target_id,
        "--ontology-context-project-id",
        "demo",
    )
    assert result.returncode == 2 and not result.stdout
    assert not (workspace / "runs").exists()


def test_product_target_does_not_follow_alias_or_rewrite_mismatched_yaml(workspace):
    target = workspace / "specs/nodes/GITVIEW-SPEC-0001.yaml"
    target.write_text("id: SG-SPEC-0001\nkind: spec\n")
    policy = workspace / ".specgraph/spec-id-policy.json"
    policy.parent.mkdir()
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "prefix": "GITVIEW-SPEC",
                "aliases": {"SG-SPEC-0001": "GITVIEW-SPEC-0001"},
            }
        )
    )
    before = target.read_bytes()
    result = call(
        workspace,
        "--build-project-ontology-context-check",
        "--target-spec",
        "GITVIEW-SPEC-0001",
        "--ontology-context-project-id",
        "demo",
        "--output-mode",
        "full",
    )
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["outcome"] == "invalid"
    assert report["target"] is None
    assert "target YAML id does not match" in report["diagnostics"][0]
    assert target.read_bytes() == before


def test_output_symlink_and_unrelated_artifact_are_rejected(workspace, tmp_path):
    directory = workspace / "runs/project_ontology_context"
    directory.mkdir(parents=True)
    output = directory / "SG-SPEC-0001.json"
    external = tmp_path / "external.json"
    external.write_text("untouched")
    args = (
        "--build-project-ontology-context-check",
        "--target-spec",
        "SG-SPEC-0001",
        "--ontology-context-project-id",
        "demo",
    )
    output.symlink_to(external)
    result = call(workspace, *args)
    assert result.returncode == 2 and external.read_text() == "untouched"
    output.unlink()
    output.write_text('{"artifact_kind":"unrelated"}')
    result = call(workspace, *args)
    assert result.returncode == 2 and json.loads(output.read_text())["artifact_kind"] == "unrelated"


def test_file_import_restores_sys_path(workspace, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("supervisor_for_context_cli", SUPERVISOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", workspace)
    before = list(sys.path)
    code = module.main(target_spec="SG-SPEC-0001", ontology_context_request={"project_id": "demo"})
    assert code == 1 and json.loads(capsys.readouterr().out)["outcome"] == "unavailable"
    assert sys.path == before


@pytest.mark.parametrize("target_id", ["SG-SPEC-0001", "GITVIEW-SPEC-0001"])
def test_checked_then_changed_target_reports_previous_stale(tmp_path, target_id):
    fixture_path = SUPERVISOR.parent.parent / "tests/test_project_ontology_supervisor_check.py"
    spec = importlib.util.spec_from_file_location("ontology_check_test_fixture", fixture_path)
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    try:
        spec.loader.exec_module(module)
        root, target, compiler, _, _ = module.workspace.__wrapped__(tmp_path)
    finally:
        sys.path[:] = old_path
    renamed = target.with_name(target_id + ".yaml")
    renamed.write_bytes(target.read_bytes().replace(b"SG-SPEC-0001", target_id.encode()))
    target = renamed
    args = (
        "--build-project-ontology-context-check",
        "--target-spec",
        target_id,
        "--ontology-context-project-id",
        "project",
        "--ontology-context-selection",
        "selection.yaml",
        "--ontologyc",
        str(compiler),
    )
    first = call(root, *args)
    assert first.returncode == 0, first.stderr + first.stdout
    first_summary = json.loads(first.stdout)
    assert first_summary["outcome"] == "checked"
    assert first_summary["target_spec_id"] == target_id
    previous = first_summary["report_path"]
    target.write_text(
        f"id: {target_id}\nkind: spec\nspecification:\n  terminology:\n    Changed: {{}}\n"
    )
    second = call(root, *args, "--ontology-context-previous-report", previous)
    assert second.returncode == 0, second.stderr + second.stdout
    summary = json.loads(second.stdout)
    assert summary["outcome"] == "checked"
    assert summary["previous_freshness"]["outcome"] == "stale"


def test_legacy_abbreviation_remains_enabled_without_context_mode(workspace):
    result = call(workspace, "--build-project", "--output-m", "summary")
    assert result.returncode in {0, 1}, result.stderr
    assert "ambiguous option" not in result.stderr
    report = json.loads(result.stdout)
    assert report["artifact_kind"] == "project_environment"
    assert not (workspace / "runs/project_ontology_context").exists()
    help_result = call(workspace, "--help")
    assert "--build-project-ontology-context-check --help" in " ".join(help_result.stdout.split())


@pytest.mark.parametrize(
    "args",
    [
        (
            "--build-project-ontology-context-c",
            "--target-spec",
            "SG-SPEC-0001",
            "--ontology-context-project-id",
            "demo",
        ),
        (
            "--build-project-ontology-context-check",
            "--target-spec",
            "SG-SPEC-0001",
            "--ontology-context-project-id",
            "demo",
            "--output-m",
            "summary",
        ),
    ],
)
def test_context_mode_rejects_abbreviations(workspace, args):
    result = call(workspace, *args)
    assert result.returncode == 2 and not result.stdout
    assert not (workspace / "runs").exists()


@pytest.mark.parametrize("selected_input", ["selection", "source", "ir", "compiler"])
def test_output_does_not_replace_selected_inputs(workspace, selected_input):
    directory = workspace / "runs/project_ontology_context"
    directory.mkdir(parents=True)
    output = directory / "SG-SPEC-0001.json"
    original = json.dumps(
        {
            "artifact_kind": "project_ontology_target_check",
            "schema_version": 1,
            "target_spec_id": "SG-SPEC-0001",
            "project_id": "demo",
        }
    ).encode()
    output.write_bytes(original)
    relative = output.relative_to(workspace).as_posix()
    member = {
        "id": "demo",
        "namespace": "ex",
        "version": "1.0.0",
        "source": "source.yaml",
        "ir": "ir.json",
        "source_sha256": "a" * 64,
        "ir_sha256": "b" * 64,
    }
    if selected_input in {"source", "ir"}:
        member[selected_input] = relative
    selection = {
        "artifact_kind": "specgraph_project_ontology_selection",
        "schema_version": 1,
        "packages": [member],
        "profiles": ["ontologyc-structural-v1"],
        "composition": {"dependency_rule": "explicit", "name_resolution_rule": "qualified"},
    }
    (workspace / "selection.yaml").write_text(yaml.safe_dump(selection))
    args = [
        "--build-project-ontology-context-check",
        "--target-spec",
        "SG-SPEC-0001",
        "--ontology-context-project-id",
        "demo",
        "--ontology-context-selection",
        relative if selected_input == "selection" else "selection.yaml",
    ]
    if selected_input == "compiler":
        args += ["--ontologyc", str(output)]
    result = call(workspace, *args)
    assert result.returncode == 2 and not result.stdout
    assert "collides" in result.stderr and output.read_bytes() == original


def test_malformed_selection_does_not_replace_existing_report(workspace):
    directory = workspace / "runs/project_ontology_context"
    directory.mkdir(parents=True)
    output = directory / "SG-SPEC-0001.json"
    original = json.dumps(
        {
            "artifact_kind": "project_ontology_target_check",
            "schema_version": 1,
            "target_spec_id": "SG-SPEC-0001",
            "project_id": "demo",
        }
    ).encode()
    output.write_bytes(original)
    (workspace / "selection.yaml").write_text("packages: [unterminated")
    result = call(
        workspace,
        "--build-project-ontology-context-check",
        "--target-spec",
        "SG-SPEC-0001",
        "--ontology-context-project-id",
        "demo",
        "--ontology-context-selection",
        "selection.yaml",
    )
    assert result.returncode == 2 and not result.stdout
    assert output.read_bytes() == original
