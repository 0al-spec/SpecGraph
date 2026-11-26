"""Viewer input selection and renderer invocation contract."""

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from tools import ontology_viewer

from specgraph.cli import main as installed_cli


@pytest.fixture
def projection(tmp_path):
    def write_yaml(name, package_id, *imports):
        path = tmp_path / name
        path.write_text(
            json.dumps(
                {
                    "metadata": {"id": package_id, "version": "1.0.0"},
                    "spec": {
                        "imports": [{"id": key, "version": version} for key, version in imports]
                    },
                }
            )
        )
        return path

    parent = write_yaml("parent.yaml", "example.parent", ("example.contracts", "1.0.0"))
    contracts = write_yaml("contracts.yaml", "example.contracts", ("ontology.foundation", "0.2.0"))
    root = write_yaml("package.yaml", "example.root", ("example.parent", "1.0.0"))
    for version in ("0.1.0", "0.2.0"):
        (tmp_path / f"{version}.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "ontology.foundation-model/v1",
                    "id": "ontology.foundation",
                    "version": version,
                }
            )
        )
    binary = tmp_path / "ontologyviz"
    binary.write_bytes(b"renderer bytes")
    options = [
        str(root),
        "--ontologyviz",
        str(binary),
        "--out",
        str(tmp_path / "output"),
        "--foundation-catalog",
        str(tmp_path / "0.1.0.json"),
        "--foundation-catalog",
        str(tmp_path / "0.2.0.json"),
        "--package-candidate",
        str(contracts),
        "--package-candidate",
        str(parent),
    ]
    return options


def test_first_call_includes_entire_dependency_chain(tmp_path, projection, monkeypatch, capsys):
    renderer = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(ontology_viewer.subprocess, "run", renderer)
    checksum = hashlib.sha256(b"renderer bytes").hexdigest()
    assert ontology_viewer.main([*projection, "--viz-sha256", checksum]) == 0
    renderer.assert_called_once_with(
        [
            str(tmp_path / "ontologyviz"),
            "--format",
            "json",
            "--out",
            str(tmp_path / "output"),
            "--import",
            str(tmp_path / "parent.yaml"),
            "--import",
            str(tmp_path / "contracts.yaml"),
            "--foundation-model",
            str(tmp_path / "0.2.0.json"),
            str(tmp_path / "package.yaml"),
        ],
        check=False,
    )
    assert checksum in capsys.readouterr().err


@pytest.mark.parametrize(
    ("change", "diagnostic"),
    [
        ("missing-yaml", "missing YAML package for example.contracts@1.0.0"),
        ("wrong-catalog", "missing foundation catalog for ontology.foundation@0.2.0"),
        ("duplicate-catalog", "Ambiguous input for ontology.foundation@0.2.0"),
        ("hash-mismatch", "SHA-256 mismatch"),
        ("hash-read", "cannot read SHA-256"),
    ],
)
def test_preflight_stops_before_renderer(
    tmp_path, projection, change, diagnostic, monkeypatch, capsys
):
    args = projection[:]
    if change == "missing-yaml":
        del args[-4:-2]
    elif change == "wrong-catalog":
        del args[7:9]
    elif change == "duplicate-catalog":
        duplicate = tmp_path / "duplicate.json"
        duplicate.write_bytes((tmp_path / "0.2.0.json").read_bytes())
        args += ["--foundation-catalog", str(duplicate)]
    elif change == "hash-mismatch":
        args += ["--viz-sha256", "0" * 64]
    else:
        (tmp_path / "ontologyviz").unlink()
    renderer = Mock()
    monkeypatch.setattr(ontology_viewer.subprocess, "run", renderer)
    assert ontology_viewer.main(args) == 2
    assert diagnostic in capsys.readouterr().err
    renderer.assert_not_called()


def test_legacy_import_uses_the_pinned_catalog(tmp_path):
    root = tmp_path / "package.yaml"
    root.write_text("""metadata: {id: example.root, version: 1.0.0}
spec:
  imports: [{id: specgraph.foundation, version: 0.1.0}]
""")
    catalog = tmp_path / "model.json"
    catalog.write_text(
        json.dumps(
            {
                "schemaVersion": "ontology.foundation-model/v1",
                "id": "ontology.foundation",
                "version": "0.1.0",
            }
        )
    )
    assert ontology_viewer.projection_inputs(root, [], [catalog]) == ([], [catalog])


def test_installed_cli_forwards_options(monkeypatch):
    tools = Path(__file__).resolve().parents[1] / "tools"
    monkeypatch.syspath_prepend(str(tools))
    cli = Mock(return_value=3)
    monkeypatch.setitem(sys.modules, "ontology_viewer", Mock(main=cli))
    assert installed_cli(["ontology-viewer", "package.yaml", "--out", "output"]) == 3
    cli.assert_called_once_with(["package.yaml", "--out", "output"])
