"""Source identities, declaration deltas, and selection errors."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/ontology_ref_diff.py"


@pytest.fixture
def pair(tmp_path):
    names = "draft/PRODUCT-SPEC-0001.yaml", "nodes/PRODUCT-SPEC-0001.yaml"
    before, after = (tmp_path / name for name in names)
    before.parent.mkdir()
    after.parent.mkdir()
    before.write_text("""id: PRODUCT-SPEC-0001
ontology_refs:
  - demo:Retained
  - demo:Removed
specification:
  terminology:
    'Слово': description
  ontology_refs:
    - demo:Retained
""")
    after.write_text("""id: PRODUCT-SPEC-0001
specification:
  terminology:
    'Слово': updated description
  ontology_refs:
    - demo:Added
    - demo:Retained
""")
    return tmp_path, names


def run_diff(workspace, *args):
    return subprocess.run(
        [sys.executable, str(TOOL), "--workspace-root", str(workspace), *args],
        cwd=workspace.parent,
        capture_output=True,
        text=True,
    )


def test_diff_preserves_input_identity_and_declaration_locations(pair):
    workspace, names = pair
    captured = [(workspace / name).read_bytes() for name in names]
    result = run_diff(workspace, *names, "--explain-removal", "demo:Removed", "Handled elsewhere.")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["artifact_kind"] == "specgraph_ontology_ref_diff"
    assert report["schema_version"] == 1
    for side, name, raw in zip(("before", "after"), names, captured, strict=True):
        assert report["inputs"][side] == {
            "path": name,
            "spec_id": "PRODUCT-SPEC-0001",
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    assert [item["term"] for item in report["retained"]] == ["demo:Retained", "Слово"]
    retained = report["retained"][0]
    assert [item["field_path"] for item in retained["before"]] == [
        "ontology_refs[0]",
        "specification.ontology_refs[0]",
    ]
    assert retained["after"][0]["field_path"] == "specification.ontology_refs[1]"
    assert report["retained"][1]["before"][0]["field_path"] == 'specification.terminology["Слово"]'
    assert [item["term"] for item in report["added"]] == ["demo:Added"]
    assert len(report["removed"]) == 1
    removed = report["removed"][0]
    assert removed["term"] == "demo:Removed"
    assert removed["removal_explanation"] == "Handled elsewhere."
    assert removed["before"][0]["location"]["start"]["line"] == 4
    assert [(workspace / name).read_bytes() for name in names] == captured


def test_diff_reports_disappearance_when_successor_declares_nothing(pair):
    workspace, names = pair
    (workspace / names[1]).write_text(
        "id: PRODUCT-SPEC-0001\nsummary: demo:Retained is discussed.\n"
    )
    result = run_diff(workspace, *names)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert not report["retained"] and not report["added"]
    assert [item["term"] for item in report["removed"]] == [
        "demo:Removed",
        "demo:Retained",
        "Слово",
    ]
    assert all(item["removal_explanation"] is None for item in report["removed"])


def test_diff_refuses_ambiguous_or_external_inputs(pair):
    workspace, names = pair
    (workspace / "link.yaml").symlink_to(workspace / names[0])
    for arguments in (
        ("link.yaml", names[1]),
        (str(workspace / names[0]), names[1]),
        (f"nodes/../{names[0]}", names[1]),
        (*names, "--explain-removal", "demo:Retained", "Wrong term."),
        (*names, "--explain-removal", "demo:Removed", " "),
    ):
        result = run_diff(workspace, *arguments)
        assert result.returncode == 2 and not result.stdout
    (workspace / names[1]).write_text("ontology_refs: &r []\nother: *r\n")
    result = run_diff(workspace, *names)
    assert result.returncode == 2 and not result.stdout
    assert "YAML aliases" in result.stderr
