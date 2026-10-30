"""The CLI captures only explicitly selected workspace context."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

CLI = Path(__file__).resolve().parents[1] / "tools" / "project_ontology_context_cli.py"


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def context(tmp_path):
    workspace = tmp_path / "product"
    workspace.mkdir()
    source = json.dumps(
        {
            "metadata": {"id": "demo", "namespace": "demo", "version": "1.0.0"},
            "spec": {"imports": []},
        },
        sort_keys=True,
    ).encode()
    ir = json.dumps(
        {
            "id": "demo",
            "namespace": "demo",
            "version": "1.0.0",
            "imports": [],
            "sourceDigest": "sha256:" + digest(source),
        },
        sort_keys=True,
    ).encode()
    (workspace / "source.yaml").write_bytes(source)
    (workspace / "ir.json").write_bytes(ir)
    selection = {
        "artifact_kind": "specgraph_project_ontology_selection",
        "schema_version": 1,
        "packages": [
            {
                "id": "demo",
                "namespace": "demo",
                "version": "1.0.0",
                "source": "source.yaml",
                "source_sha256": digest(source),
                "ir": "ir.json",
                "ir_sha256": digest(ir),
            }
        ],
        "profiles": ["ontologyc-structural-v1"],
        "composition": {"dependency_rule": "explicit", "name_resolution_rule": "qualified"},
    }
    (workspace / "selection.yaml").write_text(yaml.safe_dump(selection))
    compiler = tmp_path / "ontologyc"
    compiler.write_text("""#!/usr/bin/env python3
import hashlib, json, pathlib, sys
source = pathlib.Path(sys.argv[2]).read_bytes()
if sys.argv[1] == "compile":
    data = json.loads(source)
    out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
    out.mkdir()
    ir = {**data["metadata"], "imports": data["spec"]["imports"],
          "sourceDigest": "sha256:" + hashlib.sha256(source).hexdigest()}
    (out / "ontology.normalized.json").write_text(json.dumps(ir, sort_keys=True))
""")
    compiler.chmod(0o700)
    return workspace, compiler


def call(workspace, *args):
    return subprocess.run(
        [sys.executable, str(CLI), "--workspace-root", str(workspace), *map(str, args)],
        cwd=workspace,
        capture_output=True,
        text=True,
    )


def test_external_workspace_config_default_and_atomic_report(context):
    workspace, compiler = context
    (workspace / "specgraph.project.yaml").write_text(
        yaml.safe_dump(
            {
                "artifact_kind": "specgraph_project_config",
                "schema_version": 1,
                "project_id": "demo",
                "ontology_context": {"selection": "selection.yaml"},
            }
        )
    )
    result = call(
        workspace,
        "--ontologyc",
        compiler,
        "--compiler-sha256",
        digest(compiler.read_bytes()),
        "--output",
        "report.json",
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout)["outcome"] == "verified"
    assert json.loads((workspace / "report.json").read_text()) == json.loads(result.stdout)
    assert result.stderr == ""


@pytest.mark.parametrize("version", [None, 99, True])
def test_unknown_project_config_schema_does_not_supply_defaults(context, version):
    workspace, _ = context
    (workspace / "specgraph.project.yaml").write_text(
        yaml.safe_dump(
            {
                "artifact_kind": "specgraph_project_config",
                "schema_version": version,
                "project_id": "demo",
                "ontology_context": {"selection": "selection.yaml"},
            }
        )
    )
    result = call(workspace, "--output", "report.json")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "invalid specgraph.project.yaml" in result.stderr
    assert not (workspace / "report.json").exists()


def test_missing_selection_or_compiler_and_wrong_pin(context):
    workspace, compiler = context
    missing = call(workspace, "--project-id", "demo")
    assert missing.returncode == 1 and json.loads(missing.stdout)["outcome"] == "unavailable"
    no_compiler = call(workspace, "--project-id", "demo", "--selection", "selection.yaml")
    assert no_compiler.returncode == 1
    wrong = call(
        workspace,
        "--project-id",
        "demo",
        "--selection",
        "selection.yaml",
        "--ontologyc",
        compiler,
        "--compiler-sha256",
        "0" * 64,
    )
    assert wrong.returncode == 2 and json.loads(wrong.stdout)["outcome"] == "invalid"


def test_output_and_selection_cannot_escape_workspace(context):
    workspace, compiler = context
    for args in (("--selection", "../selection.yaml"), ("--output", "../report.json")):
        result = call(workspace, "--project-id", "demo", "--ontologyc", compiler, *args)
        assert result.returncode == 2 and not result.stdout
        assert "outside workspace" in json.loads(result.stderr)["error"]
    assert not (workspace.parent / "report.json").exists()


def test_report_cannot_replace_inputs_or_unrelated_files(context):
    workspace, compiler = context
    original = (workspace / "source.yaml").read_bytes()
    for name in ("source.yaml", "selection.yaml", "ir.json"):
        result = call(
            workspace,
            "--project-id",
            "demo",
            "--selection",
            "selection.yaml",
            "--ontologyc",
            compiler,
            "--output",
            name,
        )
        assert result.returncode == 2 and not result.stdout
    assert (workspace / "source.yaml").read_bytes() == original
    unrelated = workspace / "notes.json"
    unrelated.write_text("{}")
    result = call(workspace, "--project-id", "demo", "--output", unrelated)
    assert result.returncode == 2 and unrelated.read_text() == "{}"
