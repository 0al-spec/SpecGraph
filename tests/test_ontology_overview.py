"""An authored hierarchy stays readable while mappings retain exact identities."""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ontology_overview.export as exporter  # noqa: E402
from ontology_overview.model import OverviewError, render, selected_role, sha  # noqa: E402
from ontology_overview_cli import main  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = Path("docs/reviews/0232_project_ontology_context/hypercode-overview")
REF = "ontology://example/1.0.0/classes/Check"


def node(name, identity, **properties):
    return {
        "type": "Check",
        "id": identity,
        "properties": {
            key: {"value": value}
            for key, value in {"overview_name": name, "ontology_ref": REF, **properties}.items()
        },
        "children": [],
    }


@pytest.fixture
def selection():
    root = node("Verification", "case", ontology_source="package.yaml")
    root["children"] = [node("Member", "member"), node("Dependencies", "closure")]
    return {"version": "hypercode.ir/v2", "context": {}, "nodes": [root]}


@pytest.fixture
def bindings_workspace(tmp_path, monkeypatch):
    (tmp_path / "package.yaml").write_text("captured source\n")
    # If a binding checker imports this module, the test fails before its assertions.
    (tmp_path / "policy.py").write_text(
        "raise AssertionError('must never import bound modules')\n"
        "def other():\n    return 'outside'\n"
        "def decide(value):\n    return value is not None  # selected anchor\n"
    )
    calls = []

    def capture(source, compiler, **kwargs):
        calls.append(kwargs["captured_inputs"].source)
        return SimpleNamespace(
            source_sha256=sha(kwargs["captured_inputs"].source),
            ir_sha256="b" * 64,
            ir_bytes=json.dumps(
                {
                    "classes": [{"uri": REF}],
                    "protocols": [],
                    "relations": [{"uri": "ontology://example/1.0.0/relations/includes"}],
                }
            ).encode(),
        )

    monkeypatch.setattr(exporter, "capture_ontology_snapshot", capture)
    return tmp_path, calls


def test_order_and_two_occurrences_of_one_type_survive(selection):
    root = selected_role(selection)
    roles = list(root.walk())
    bindings = {role.identity: dict(role.properties) for _, role in roles}
    original = copy.deepcopy(bindings)
    hc, hcs = render(root, bindings)
    assert hc == b"Verification\n  Member\n  Dependencies\n"
    assert b"#" not in hc and b"ontology://" not in hc
    assert hcs.count(REF.encode()) == 3
    assert b'role_id: "member"' in hcs and b'role_id: "closure"' in hcs
    assert b'source_type: "Check"' in hcs
    assert bindings == original
    assert render(root, bindings) == (hc, hcs)


def test_display_rename_preserves_stable_identity(selection):
    before = selected_role(selection)
    selection["nodes"][0]["children"][0]["properties"]["overview_name"]["value"] = "Package"
    after = selected_role(selection)
    assert before.children[0].identity == after.children[0].identity == "member"
    assert before.children[0].properties == after.children[0].properties
    assert after.children[0].name == "Package"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda ir: ir.update(version="hypercode.ir/v1"), "IR v2"),
        (lambda ir: ir.update(context={"mode": "other"}), "empty Hypercode context"),
        (lambda ir: ir.update(nodes=[]), "exactly one"),
        (lambda ir: ir["nodes"].append(copy.deepcopy(ir["nodes"][0])), "exactly one"),
        (lambda ir: ir["nodes"][0]["children"][0].update(id="case"), "distinct identity"),
        (
            lambda ir: ir["nodes"][0]["children"][0]["properties"].update(
                role_id={"value": "wrong"}
            ),
            "disagrees",
        ),
        (
            lambda ir: ir["nodes"][0]["children"][1]["properties"].update(
                overview_name={"value": "Member"}
            ),
            "duplicate sibling",
        ),
        (
            lambda ir: ir["nodes"][0]["properties"].update(overview_name={"value": "Bad > Child"}),
            "simple HC name",
        ),
        (
            lambda ir: ir["nodes"][0]["properties"].update(overview_name={"value": "Bad\nChild"}),
            "single-line",
        ),
        (lambda ir: ir["nodes"][0]["properties"].pop("ontology_ref"), "missing ontology_ref"),
    ],
)
def test_invalid_selected_compositions(selection, change, message):
    change(selection)
    with pytest.raises(OverviewError, match=message):
        selected_role(selection)


def test_distinct_parent_scopes_allow_repeated_display_names(selection):
    children = selection["nodes"][0]["children"]
    children[0]["children"] = [node("Result", "left-result")]
    children[1]["children"] = [node("Result", "right-result")]
    assert len(tuple(selected_role(selection).walk())) == 5


def test_bindings_capture_one_package_and_never_import_production(selection, bindings_workspace):
    workspace, calls = bindings_workspace
    selection["nodes"][0]["children"][0]["properties"].update(
        {
            k: {"value": v}
            for k, v in {
                "production_path": "policy.py",
                "production_symbol": "decide",
                "production_anchor": "selected anchor",
            }.items()
        }
    )
    result = exporter.checked_bindings(
        workspace, selected_role(selection), Path("compiler"), "a" * 64
    )
    assert calls == [b"captured source\n"]
    assert result["member"]["production_line"] == "5"
    assert result["member"]["production_sha256"] == sha((workspace / "policy.py").read_bytes())
    assert all(p["ontology_source"] == "package.yaml" for p in result.values())
    assert all(p["ontology_compiler_sha256"] == "a" * 64 for p in result.values())


@pytest.mark.parametrize(
    ("properties", "message"),
    [
        ({"ontology_ref": "ontology://example/1.0.0/classes/Typo"}, "unknown ontology_ref"),
        ({"ontology_ref": "ontology://example/2.0.0/classes/Check"}, "unknown ontology_ref"),
        ({"ontology_ref": "ontology://example/1.0.0/relations/includes"}, "unknown ontology_ref"),
        ({"composition_ref": "ontology://example/1.0.0/relations/Typo"}, "unknown composition_ref"),
        ({"ontology_sha256": "0" * 64}, "source hash mismatch"),
        ({"ontology_source": "../outside.yaml"}, "workspace-relative"),
        ({"ontology_source": "/outside.yaml"}, "workspace-relative"),
        ({"production_path": "policy.py"}, "requires path, symbol and anchor"),
        (
            {
                "production_path": "policy.py",
                "production_symbol": "missing",
                "production_anchor": "x",
            },
            "function missing or ambiguous",
        ),
        (
            {
                "production_path": "policy.py",
                "production_symbol": "decide",
                "production_anchor": "outside",
            },
            "once inside",
        ),
        (
            {
                "production_path": "policy.py",
                "production_symbol": "decide",
                "production_anchor": "selected anchor",
                "production_sha256": "0" * 64,
            },
            "source hash mismatch",
        ),
        ({"scenario_sha256": "0" * 64}, "requires scenario_source"),
    ],
)
def test_unusable_bindings_are_not_exportable(selection, bindings_workspace, properties, message):
    workspace, _ = bindings_workspace
    selection["nodes"][0]["children"][0]["properties"].update(
        {k: {"value": v} for k, v in properties.items()}
    )
    with pytest.raises(OverviewError, match=message):
        exporter.checked_bindings(workspace, selected_role(selection), Path("compiler"), "a" * 64)


def test_workspace_symlink_cannot_escape(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = tmp_path / "outside"
    target.write_text("outside")
    (workspace / "link").symlink_to(target)
    with pytest.raises(OverviewError, match="outside workspace"):
        exporter.workspace_file(workspace, "link")


def test_existing_output_is_rejected_without_touching_it(tmp_path):
    output = tmp_path / "saved"
    output.mkdir()
    original = output / "context.hc"
    original.write_bytes(b"precious\n")
    with pytest.raises(OverviewError, match="new directory"):
        exporter.export_overview(
            tmp_path, Path("none"), Path("none"), Path("none"), Path("none"), output
        )
    assert original.read_bytes() == b"precious\n"


def test_failed_generated_cascade_creates_no_destination(
    selection, bindings_workspace, monkeypatch
):
    workspace, _ = bindings_workspace
    (workspace / "selection.hc").write_bytes(b"original HC\n")
    (workspace / "selection.hcs").write_bytes(b"original HCS\n")
    executable = workspace / "tool"
    executable.write_bytes(b"not executed")
    executable.chmod(0o700)
    calls = []

    def resolve(*args):
        calls.append(args)
        if len(calls) == 2:
            raise OverviewError("generated cascade rejected")
        return selection

    monkeypatch.setattr(exporter, "run_hypercode", resolve)
    output = workspace / "export"
    with pytest.raises(OverviewError, match="generated cascade rejected"):
        exporter.export_overview(
            workspace, Path("selection.hc"), Path("selection.hcs"), executable, executable, output
        )
    assert not output.exists()
    assert (workspace / "selection.hc").read_bytes() == b"original HC\n"
    assert (workspace / "selection.hcs").read_bytes() == b"original HCS\n"


def test_cli_missing_tool_is_unavailable_without_writing(tmp_path, capsys):
    (tmp_path / "selection.hc").write_text("Source")
    (tmp_path / "selection.hcs").write_text("Source:")
    code = main(
        [
            "--workspace-root",
            str(tmp_path),
            "--hc",
            "selection.hc",
            "--hcs",
            "selection.hcs",
            "--hypercode",
            str(tmp_path / "missing"),
            "--ontologyc",
            str(tmp_path / "missing"),
            "--output-dir",
            str(tmp_path / "export"),
        ]
    )
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["status"] == "unavailable"
    assert not (tmp_path / "export").exists()


def test_imports_are_rejected_before_a_reference_tool_can_open_them(tmp_path, monkeypatch):
    (tmp_path / "selection.hc").write_text("Source")
    (tmp_path / "selection.hcs").write_text('@import "/untracked/outside.hcs"\n')

    def unexpected(*args):
        pytest.fail("Hypercode must not open an untracked imported sheet")

    monkeypatch.setattr(exporter, "run_hypercode", unexpected)
    output = tmp_path / "export"
    with pytest.raises(OverviewError, match="single-sheet"):
        exporter.export_overview(
            tmp_path,
            Path("selection.hc"),
            Path("selection.hcs"),
            Path("none"),
            Path("none"),
            output,
        )
    assert not output.exists()


def test_malformed_production_is_a_structured_cli_rejection(
    selection, bindings_workspace, monkeypatch, capsys
):
    workspace, _ = bindings_workspace
    (workspace / "policy.py").write_text("def broken(\n")
    selection["nodes"][0]["properties"].update(
        {
            k: {"value": v}
            for k, v in {
                "production_path": "policy.py",
                "production_symbol": "broken",
                "production_anchor": "def",
            }.items()
        }
    )
    (workspace / "selection.hc").write_text("Source")
    (workspace / "selection.hcs").write_text("Source:")
    executable = workspace / "tool"
    executable.write_bytes(b"not executed")
    executable.chmod(0o700)
    monkeypatch.setattr(exporter, "run_hypercode", lambda *args: selection)
    code = main(
        [
            "--workspace-root",
            str(workspace),
            "--hc",
            "selection.hc",
            "--hcs",
            "selection.hcs",
            "--hypercode",
            str(executable),
            "--ontologyc",
            str(executable),
            "--output-dir",
            str(workspace / "export"),
        ]
    )
    assert code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["status"] == "invalid"
    assert "Python syntax" in json.loads(captured.err)["error"]
    assert not (workspace / "export").exists()


@pytest.mark.skipif(
    not (os.environ.get("HYPERCODE_BIN") and os.environ.get("ONTOLOGYC_BIN")),
    reason="Optional real Hypercode / ontologyc compatibility check",
)
def test_reference_tools_export_the_approved_example(tmp_path):
    outputs = [tmp_path / "first", tmp_path / "second"]
    before = [(ROOT / EXAMPLE / name).read_bytes() for name in ("selection.hc", "selection.hcs")]
    reports = [
        exporter.export_overview(
            ROOT,
            EXAMPLE / "selection.hc",
            EXAMPLE / "selection.hcs",
            Path(os.environ["HYPERCODE_BIN"]),
            Path(os.environ["ONTOLOGYC_BIN"]),
            output,
        )
        for output in outputs
    ]
    assert reports[0] == reports[1]
    assert reports[0]["roles"] == 3 and reports[0]["status"] == "exported"
    assert reports[0]["semantic_approval"] == "not_established"
    assert (outputs[0] / "context.hc").read_bytes() == (ROOT / EXAMPLE / "context.hc").read_bytes()
    for name in ("context.hc", "context.hcs"):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
    assert before == [
        (ROOT / EXAMPLE / name).read_bytes() for name in ("selection.hc", "selection.hcs")
    ]


@pytest.mark.skipif(
    not (os.environ.get("HYPERCODE_BIN") and os.environ.get("ONTOLOGYC_BIN")),
    reason="Optional real Hypercode / ontologyc negative controls",
)
@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("/classes/CheckResult", "/classes/CheckReslut", "unknown ontology_ref"),
        (
            "512920428c4907fa6cdb938937797c50fd81e964c8d60e0d5290e688a6e10870",
            "0" * 64,
            "source hash mismatch",
        ),
        ("saved ontology IR differs from compiler output", "_strict_object", "once inside"),
        ('overview_name: "Member"', 'overview_name: "Dependencies"', "duplicate sibling"),
    ],
)
def test_reference_tools_reject_bad_mappings_before_publication(tmp_path, old, new, message):
    # Isolated workspace: no mutations of the real source, sketch or prototype.
    files = [
        EXAMPLE / "selection.hc",
        EXAMPLE / "selection.hcs",
        Path("specs/models/SG-SPEC-0072/domain-ontology-package.yaml"),
        Path("specs/models/SG-SPEC-0072/unsupported-closure.ts"),
        Path("tools/project_ontology_context/capture.py"),
        Path("tools/ontology_snapshot.py"),
    ]
    for relative in files:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    hcs = tmp_path / EXAMPLE / "selection.hcs"
    hcs.write_text(hcs.read_text().replace(old, new))
    output = tmp_path / "export"
    with pytest.raises(OverviewError, match=message):
        exporter.export_overview(
            tmp_path,
            EXAMPLE / "selection.hc",
            EXAMPLE / "selection.hcs",
            Path(os.environ["HYPERCODE_BIN"]),
            Path(os.environ["ONTOLOGYC_BIN"]),
            output,
        )
    assert not output.exists()
