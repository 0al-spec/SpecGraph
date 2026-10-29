"""Project selection verifies bounded structural evidence without granting authority."""

import hashlib
import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from project_ontology_context import capture_project_context  # noqa: E402


def sha(value):
    return hashlib.sha256(value).hexdigest()


@pytest.fixture
def workspace(tmp_path):
    compiler = tmp_path / "compiler"
    compiler.write_text(
        "#!/usr/bin/env python3\n"
        "import hashlib,json,pathlib,sys\n"
        "source=pathlib.Path(sys.argv[2]).read_bytes()\n"
        "data=json.loads(source)\n"
        "if sys.argv[1] == 'compile':\n"
        " out=pathlib.Path(sys.argv[sys.argv.index('--out')+1]); out.mkdir()\n"
        " ir={**data['metadata'], 'imports':data['spec'].get('imports', []), "
        "'sourceDigest':'sha256:'+hashlib.sha256(source).hexdigest()}\n"
        " (out/'ontology.normalized.json').write_text(json.dumps(ir, sort_keys=True))\n"
    )
    compiler.chmod(0o700)

    def package(name="example", namespace="ex", imports=None):
        data = {
            "metadata": {"id": name, "namespace": namespace, "version": "1.0.0"},
            "spec": {"imports": imports or []},
        }
        source = json.dumps(data, sort_keys=True).encode()
        ir = json.dumps(
            {**data["metadata"], "imports": imports or [], "sourceDigest": "sha256:" + sha(source)},
            sort_keys=True,
        ).encode()
        (tmp_path / f"{name}.yaml").write_bytes(source)
        (tmp_path / f"{name}.json").write_bytes(ir)
        return {
            "id": name,
            "namespace": namespace,
            "version": "1.0.0",
            "source": f"{name}.yaml",
            "source_sha256": sha(source),
            "ir": f"{name}.json",
            "ir_sha256": sha(ir),
        }

    def selection(members, profiles=None):
        obj = {
            "artifact_kind": "specgraph_project_ontology_selection",
            "schema_version": 1,
            "packages": members,
            "profiles": ["ontologyc-structural-v1"] if profiles is None else profiles,
            "composition": {"dependency_rule": "explicit", "name_resolution_rule": "qualified"},
        }
        (tmp_path / "selection.yaml").write_text(yaml.safe_dump(obj))

    def capture(**kwargs):
        return capture_project_context(
            tmp_path,
            project_id="project",
            selection_path=Path("selection.yaml"),
            ontologyc=compiler,
            **kwargs,
        )

    return tmp_path, compiler, package, selection, capture


def test_snapshot_identity_and_mutable_files(workspace):
    root, compiler, package, selection, capture = workspace
    member = package()
    selection([member])
    a = capture(compiler_sha256=sha(compiler.read_bytes()))
    b = capture()
    assert a.outcome == "verified" and a.revision == b.revision
    assert a.report()["semantic_approval"] == "not_established"
    assert a.report()["members"] == [{"id": "example", "namespace": "ex", "version": "1.0.0"}]
    source_bytes, ir_bytes = a.snapshots[0].source_bytes, a.snapshots[0].ir_bytes
    (root / "example.yaml").write_text("changed")
    (root / "example.json").write_text("changed")
    assert a.snapshots[0].source_bytes == source_bytes and a.snapshots[0].ir_bytes == ir_bytes
    with pytest.raises(FrozenInstanceError):
        a.outcome = "verified"
    assert capture().outcome == "invalid"


def test_identity_changes_for_content_compiler_and_profiles(workspace):
    root, compiler, package, selection, capture = workspace
    member = package()
    selection([member])
    initial = capture().revision
    compiler.write_text(compiler.read_text() + "\n# second compiler\n")
    assert capture().revision != initial
    other = package(imports=[{"id": "foundation", "namespace": "f", "version": "1.0.0"}])
    selection([other])
    changed = capture()
    assert changed.revision != initial and changed.outcome == "unavailable"
    selection([member], profiles=["unknown"])
    assert capture().outcome == "invalid"  # package files have changed as well
    selection([other], profiles=["unknown"])
    assert capture().outcome == "unavailable"
    selection([other], profiles=[])
    assert capture().outcome == "unavailable"


def test_duplicate_invalid_takes_precedence_over_missing_compiler(workspace):
    root, _, package, selection, _ = workspace
    member = package()
    selection([member, member])
    result = capture_project_context(
        root, project_id="p", selection_path=Path("selection.yaml"), ontologyc=None
    )
    assert result.outcome == "invalid" and result.revision is None
    assert {c.outcome for c in result.checks} >= {"invalid", "unavailable"}


def test_selection_identity_pin_and_compiler_pin_mismatches(workspace):
    _, compiler, package, selection, capture = workspace
    member = package()
    selection([{**member, "id": "wrong"}])
    assert capture().outcome == "invalid"
    selection([member])
    assert capture(compiler_sha256="0" * 64).outcome == "invalid"
    assert capture(compiler_sha256=sha(compiler.read_bytes())).outcome == "verified"


def test_composition_unavailable_and_path_boundary(workspace):
    root, compiler, package, selection, capture = workspace
    one, two = package(), package("other", "other")
    selection([two, one])
    result = capture()
    assert result.outcome == "unavailable" and result.revision
    assert [x[0] for x in result.members] == ["example", "other"]
    selection([one, two])
    assert capture().revision == result.revision
    selection([{**one, "source": "../escape"}])
    assert capture().outcome == "invalid"
    missing = capture_project_context(root, project_id="p", selection_path=None, ontologyc=compiler)
    assert missing.outcome == "unavailable" and missing.revision is None


def test_duplicate_yaml_key_rejected(workspace):
    root, _, package, selection, capture = workspace
    selection([package()])
    with (root / "selection.yaml").open("a") as stream:
        stream.write("schema_version: 1\n")
    assert capture().outcome == "invalid"


def test_compiler_changes_between_package_captures(workspace, monkeypatch):
    from project_ontology_context import capture as module

    _, compiler, package, selection, capture = workspace
    selection([package(), package("other", "other")])
    original = module.capture_ontology_snapshot
    calls = 0

    def replaced(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == 1:
            compiler.write_text(compiler.read_text() + "\n# changed\n")
        return result

    monkeypatch.setattr(module, "capture_ontology_snapshot", replaced)
    result = capture()
    assert result.outcome == "invalid" and result.revision is None
    assert any("changed between member" in check.detail for check in result.checks)


def test_snapshot_failure_classification_is_independent_of_message(workspace, monkeypatch):
    from ontology_snapshot import OntologySnapshotError
    from project_ontology_context import capture as module

    _, _, package, selection, capture = workspace
    selection([package()])

    def fail(*args, **kwargs):
        raise OntologySnapshotError(
            "message says invalid but outcome is unavailable", outcome="unavailable"
        )

    monkeypatch.setattr(module, "capture_ontology_snapshot", fail)
    assert capture().outcome == "unavailable"

    def fail_invalid(*args, **kwargs):
        raise OntologySnapshotError("unavailable text", outcome="invalid")

    monkeypatch.setattr(module, "capture_ontology_snapshot", fail_invalid)
    assert capture().outcome == "invalid"


def test_context_pin_prevents_compiler_execution(workspace):
    root, compiler, package, selection, capture = workspace
    selection([package()])
    marker = root / "compiler-executed"
    contents = compiler.read_text()
    compiler.write_text(
        contents.replace(
            "import hashlib,json,pathlib,sys\n",
            f"import hashlib,json,pathlib,sys\npathlib.Path({str(marker)!r}).touch()\n",
        )
    )
    result = capture(compiler_sha256="0" * 64)
    assert result.outcome == "invalid"
    assert not marker.exists()
