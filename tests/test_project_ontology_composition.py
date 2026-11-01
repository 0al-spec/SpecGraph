"""Bounded package composition, with release packages and real CLI capture."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/motivation_composition"
sys.path.insert(0, str(ROOT / "tools"))
from project_ontology_context import capture_project_context, composition, foundation  # noqa: E402
from project_ontology_term_inventory import build_term_inventory  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def packages():
    result = []
    for name in ("project", "motivation-core", "events-core"):
        data = (FIXTURES / f"{name}.yaml").read_bytes()
        doc = yaml.safe_load(data)
        member = {**doc["metadata"], "source": f"{name}.yaml", "source_sha256": sha(data)}
        result.append(composition.declarations(member, doc))
    return tuple(result)


def assess(values, selected=None):
    return composition.check_packages(
        values,
        foundation.capture_vocabulary(),
        selected if selected is not None else tuple(p.identity for p in values),
    )


def test_release_packages_reuse_motive_with_a_complete_closure():
    values = packages()
    checks, imports = assess(values)
    assert all(c.outcome == "verified" for c in checks)
    [motive] = [
        c
        for c in checks
        if c.package == values[0].identity[0]
        and c.reference
        and c.reference.name == "motivcore:Motive"
    ]
    assert motive.reference.uri == "ontology://org.0al.motivation.core/0.1.0/classes/Motive"
    assert {i.id for i in imports} == {
        foundation.PIN.id,
        composition.MOTIVATION[0],
        composition.EVENTS[0],
    }
    origins = json.loads((FIXTURES / "origins.json").read_bytes())
    for name, origin in origins["packages"].items():
        assert sha((FIXTURES / f"{name}.yaml").read_bytes()) == origin["sha256"]


@pytest.mark.parametrize("name", ["motivcore:Typo", "Motive", "eventcore:Entity", "sg:Auditable"])
def test_unknown_unqualified_transitive_and_wrong_role_references_are_invalid(name):
    root, *dependencies = packages()
    root = replace(root, references=(("/spec/relations/hasMotive/range", name, "classes"),))
    checks, _ = assess((root, *dependencies))
    [failure] = [c for c in checks if c.outcome == "invalid"]
    assert failure.check == "name_resolution"
    assert failure.reference.pointer == "/spec/relations/hasMotive/range"
    assert failure.reference.name == name and failure.reference.uri is None


@pytest.mark.parametrize("change", ["missing", "version", "namespace", "duplicate", "cycle"])
def test_missing_conflicting_and_cyclic_imports_are_invalid(change):
    root, motivation, events = packages()
    if change == "missing":
        values = (root, motivation)
    elif change == "version":
        values = (root, motivation, replace(events, identity=(*events.identity[:2], "0.9.0")))
    elif change == "namespace":
        values = (
            root,
            replace(motivation, identity=(motivation.identity[0], "foreign", "0.1.0")),
            events,
        )
    elif change == "duplicate":
        values = (
            replace(root, imports=root.imports + (composition.MOTIVATION,)),
            motivation,
            events,
        )
    else:
        values = (root, motivation, replace(events, imports=events.imports + (root.identity,)))
    checks, _ = assess(values)
    assert any(c.check == "dependency_closure" and c.outcome == "invalid" for c in checks)


def test_missing_captured_dependency_is_unavailable_not_a_fictitious_unknown_name():
    root, motivation, events = packages()
    checks, _ = assess((root, events), tuple(p.identity for p in (root, motivation, events)))
    [reference] = [c for c in checks if c.reference and c.reference.name == "motivcore:Motive"]
    assert reference.outcome == "unavailable"
    assert not any(c.outcome == "invalid" for c in checks)


@pytest.fixture
def compiled_selection(tmp_path):
    binary = os.environ.get("ONTOLOGYC_BINARY_PATH")
    if not binary:
        pytest.skip("set ONTOLOGYC_BINARY_PATH for the release-compiler integration")
    compiler = Path(binary).resolve(strict=True)
    members = []
    for name in ("project", "motivation-core", "events-core"):
        source = (FIXTURES / f"{name}.yaml").read_bytes()
        path = tmp_path / f"{name}.yaml"
        path.write_bytes(source)
        output = tmp_path / name
        subprocess.run(
            [compiler, "compile", path, "--target", "typescript", "--out", output],
            check=True,
            capture_output=True,
            timeout=60,
        )
        ir = output / "ontology.normalized.json"
        meta = yaml.safe_load(source)["metadata"]
        members.append(
            {
                **{k: meta[k] for k in ("id", "namespace", "version")},
                "source": path.name,
                "source_sha256": sha(source),
                "ir": str(ir.relative_to(tmp_path)),
                "ir_sha256": sha(ir.read_bytes()),
            }
        )
    selection = {
        "artifact_kind": "specgraph_project_ontology_selection",
        "schema_version": 1,
        "packages": members,
        "profiles": [composition.PROFILE],
        "composition": {"dependency_rule": "explicit", "name_resolution_rule": "qualified"},
    }
    (tmp_path / "selection.yaml").write_text(yaml.safe_dump(selection))
    return tmp_path, compiler, selection


def capture(work, compiler):
    return capture_project_context(
        work,
        project_id="composition-pilot",
        selection_path=Path("selection.yaml"),
        ontologyc=compiler,
        compiler_sha256=sha(compiler.read_bytes()),
    )


def test_real_composition_cli_and_order_independent_revision(compiled_selection):
    work, compiler, selection = compiled_selection
    result = capture(work, compiler)
    assert result.outcome == "verified", result.report()
    proc = subprocess.run(
        [
            sys.executable,
            ROOT / "tools/project_ontology_context_cli.py",
            "--workspace-root",
            work,
            "--project-id",
            "composition-pilot",
            "--selection",
            "selection.yaml",
            "--ontologyc",
            compiler,
            "--compiler-sha256",
            sha(compiler.read_bytes()),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["context_revision"] == result.revision
    selection["packages"].reverse()
    (work / "selection.yaml").write_text(yaml.safe_dump(selection))
    assert capture(work, compiler).revision == result.revision
    assert result.report()["semantic_approval"] == "not_established"
    assert result.report()["canonical_mutations_allowed"] is False
    inventory = build_term_inventory(
        result, workspace_root=work, specs_root=work / "specs", documents=()
    )
    assert inventory["outcome"] == "unavailable" and inventory["grounded"] is False


@pytest.mark.parametrize(
    "edit",
    [
        "unknown",
        "source_hash",
        "ir_hash",
        "missing_ir",
        "missing_source",
        "missing_project",
        "missing_compiler",
    ],
)
def test_real_capture_failure_controls(compiled_selection, edit):
    work, compiler, selection = compiled_selection
    member = selection["packages"][0]
    if edit == "unknown":
        path = work / member["source"]
        path.write_bytes(path.read_bytes().replace(b"motivcore:Motive", b"motivcore:Typo"))
        member["source_sha256"] = sha(path.read_bytes())
    elif edit in ("source_hash", "ir_hash"):
        member[edit.replace("_hash", "_sha256")] = "0" * 64
    elif edit == "missing_ir":
        (work / member["ir"]).unlink()
    elif edit == "missing_source":
        (work / selection["packages"][1]["source"]).unlink()
    elif edit == "missing_project":
        (work / member["source"]).unlink()
    else:
        compiler = None
    (work / "selection.yaml").write_text(yaml.safe_dump(selection))
    result = capture_project_context(
        work,
        project_id="composition-pilot",
        selection_path=Path("selection.yaml"),
        ontologyc=compiler,
    )
    assert result.outcome == ("unavailable" if edit.startswith("missing") else "invalid"), (
        result.report()
    )
    if edit == "unknown":
        assert any(
            c.reference and c.reference.name == "motivcore:Typo" and c.outcome == "invalid"
            for c in result.checks
        )


def test_known_import_conflict_takes_priority_over_missing_compiler(compiled_selection):
    work, _, selection = compiled_selection
    selection["packages"].pop()
    (work / "selection.yaml").write_text(yaml.safe_dump(selection))
    result = capture_project_context(
        work, project_id="composition-pilot", selection_path=Path("selection.yaml"), ontologyc=None
    )
    assert result.outcome == "invalid"
    assert any(c.outcome == "unavailable" for c in result.checks)


def test_changed_dependency_changes_revision_without_mutating_prior_capture(compiled_selection):
    work, compiler, selection = compiled_selection
    before = capture(work, compiler)
    member = selection["packages"][1]
    source = work / member["source"]
    old_bytes = source.read_bytes()
    source.write_bytes(old_bytes + b"\n# A distinct explicitly selected source revision.\n")
    member["source_sha256"] = sha(source.read_bytes())
    output = (work / member["ir"]).parent
    subprocess.run(
        [compiler, "compile", source, "--target", "typescript", "--out", output],
        check=True,
        capture_output=True,
        timeout=60,
    )
    member["ir_sha256"] = sha((work / member["ir"]).read_bytes())
    (work / "selection.yaml").write_text(yaml.safe_dump(selection))
    after = capture(work, compiler)
    assert before.outcome == after.outcome == "verified"
    assert before.revision != after.revision
    [old] = [
        snapshot
        for identity, snapshot in zip(before.captured_members, before.snapshots, strict=True)
        if identity[0] == composition.MOTIVATION[0]
    ]
    assert old.source_bytes == old_bytes
    assert before.resolved_imports != after.resolved_imports


@pytest.mark.parametrize("corrupt", [False, True])
def test_unavailable_or_corrupt_foundation_catalog_cannot_verify_composition(
    compiled_selection, monkeypatch, corrupt
):
    work, compiler, _ = compiled_selection
    path = work / "catalog.json"
    if corrupt:
        path.write_text("{}")
    monkeypatch.setattr(foundation, "EXPORTS", path)
    result = capture(work, compiler)
    assert result.outcome == ("invalid" if corrupt else "unavailable")
    assert result.revision is None
    assert not result.resolved_imports


def test_arbitrary_package_graph_remains_unsupported():
    values = packages()
    other = replace(values[0], identity=("app.other", "other", "0.1.0"))
    checks, _ = assess((*values, other))
    assert any(c.outcome == "unavailable" for c in checks)
