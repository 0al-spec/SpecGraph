"""The target check shares captured bytes and never activates a gate."""

import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import project_ontology_supervisor_check as check  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def workspace(tmp_path):
    specs = tmp_path / "specs" / "nodes"
    specs.mkdir(parents=True)
    target = specs / "SG-SPEC-0001.yaml"
    target.write_text(
        "id: SG-SPEC-0001\nkind: spec\nspecification:\n  terminology:\n    Mystery: {}\n"
    )
    compiler = tmp_path / "compiler"
    compiler.write_text(
        "#!/usr/bin/env python3\n"
        "import hashlib,json,pathlib,sys\n"
        "source=pathlib.Path(sys.argv[2]).read_bytes()\n"
        "data=json.loads(source)\n"
        "if sys.argv[1] == 'compile':\n"
        " out=pathlib.Path(sys.argv[sys.argv.index('--out')+1]); out.mkdir()\n"
        " ir={**data['metadata'], 'imports':data['spec'].get('imports', []), "
        "'classes':[{'id':'Spec','fqid':'ex:Spec'}], 'relations':[], "
        "'sourceDigest':'sha256:'+hashlib.sha256(source).hexdigest()}\n"
        " (out/'ontology.normalized.json').write_text(json.dumps(ir,sort_keys=True))\n"
    )
    compiler.chmod(0o700)

    def selection(imports=None):
        data = {
            "metadata": {"id": "demo", "namespace": "ex", "version": "1.0.0"},
            "spec": {"imports": imports or []},
        }
        source = json.dumps(data, sort_keys=True).encode()
        ir = json.dumps(
            {
                **data["metadata"],
                "imports": imports or [],
                "classes": [{"id": "Spec", "fqid": "ex:Spec"}],
                "relations": [],
                "sourceDigest": "sha256:" + sha(source),
            },
            sort_keys=True,
        ).encode()
        (tmp_path / "source.yaml").write_bytes(source)
        (tmp_path / "ir.json").write_bytes(ir)
        payload = {
            "artifact_kind": "specgraph_project_ontology_selection",
            "schema_version": 1,
            "packages": [
                {
                    "id": "demo",
                    "namespace": "ex",
                    "version": "1.0.0",
                    "source": "source.yaml",
                    "source_sha256": sha(source),
                    "ir": "ir.json",
                    "ir_sha256": sha(ir),
                }
            ],
            "profiles": ["ontologyc-structural-v1"],
            "composition": {"dependency_rule": "explicit", "name_resolution_rule": "qualified"},
        }
        (tmp_path / "selection.yaml").write_text(yaml.safe_dump(payload))

    selection()

    def run(**kwargs):
        return check.build_target_context_check(
            tmp_path,
            project_id="project",
            target_spec_id="SG-SPEC-0001",
            selection_path=Path("selection.yaml"),
            ontologyc=compiler,
            **kwargs,
        )

    return tmp_path, target, compiler, selection, run


def test_checked_single_target_and_previous_freshness(workspace):
    root, _, _, _, run = workspace
    result = run()
    assert result["outcome"] == "checked"
    assert result["context"]["outcome"] == "verified"
    assert result["inventory"]["prose"] == "unassessed"
    assert result["canonical_mutations_allowed"] is False
    assert result["target"]["sha256"] == result["bundle"]["inputs"]["specs"][0]["sha256"]
    assert result["inventory"]["inputs"] == result["bundle"]["inputs"]
    (root / "previous.json").write_text(json.dumps(result))
    # Other specs never enter this target-only check.
    (root / "specs/nodes/SG-SPEC-0002.yaml").write_text("id: SG-SPEC-0002\n")
    assert (
        run(previous_report_path=Path("previous.json"))["previous_freshness"]["outcome"] == "fresh"
    )


def test_unavailable_closure_keeps_local_advisory(workspace):
    _, _, _, selection, run = workspace
    selection([{"id": "foundation", "namespace": "f", "version": "1.0.0"}])
    result = run()
    assert result["outcome"] == result["context"]["outcome"] == "unavailable"
    assert result["bundle"]["outcome"] == result["inventory"]["outcome"] == "analyzed"
    assert result["context"]["semantic_approval"] == "not_established"


def test_changed_target_after_capture_cannot_mix_documents(workspace, monkeypatch):
    root, target, _, _, run = workspace
    old = target.read_bytes()
    original = check.build_context_reports

    def mutate(*args, **kwargs):
        target.write_text(
            "id: SG-SPEC-0001\nkind: spec\nspecification:\n  terminology:\n    NewTerm: {}\n"
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(check, "build_context_reports", mutate)
    result = run()
    assert result["target"]["sha256"] == sha(old)
    assert result["inventory"]["inputs"]["specs"][0]["sha256"] == sha(old)
    assert result["bundle"]["inputs"]["specs"][0]["sha256"] == sha(old)
    assert target.read_bytes() != old
    assert root.is_dir()


def test_previous_changed_foreign_missing_and_target_failure(workspace):
    root, target, compiler, _, run = workspace
    previous = run()
    (root / "previous.json").write_text(json.dumps(previous))
    target.write_text(
        "id: SG-SPEC-0001\nkind: spec\nspecification:\n  terminology:\n    Changed: {}\n"
    )
    assert (
        run(previous_report_path=Path("previous.json"))["previous_freshness"]["outcome"] == "stale"
    )
    previous["target_spec_id"] = "SG-SPEC-0002"
    (root / "previous.json").write_text(json.dumps(previous))
    assert (
        run(previous_report_path=Path("previous.json"))["previous_freshness"]["outcome"] == "stale"
    )
    assert (
        run(previous_report_path=Path("absent"))["previous_freshness"]["outcome"] == "unavailable"
    )
    target.write_text("id: SG-SPEC-9999\n")
    assert run()["outcome"] == "invalid"
    target.unlink()
    result = run()
    assert result["outcome"] == "invalid" and result["context"] is None
    assert compiler.is_file()


def test_no_compiler_or_selection_does_not_replace_with_old_success(workspace):
    root, _, compiler, _, run = workspace
    old = run()
    (root / "previous.json").write_text(json.dumps(old))
    result = check.build_target_context_check(
        root,
        project_id="project",
        target_spec_id="SG-SPEC-0001",
        selection_path=None,
        ontologyc=compiler,
        previous_report_path=Path("previous.json"),
    )
    assert result["outcome"] == "unavailable"
    assert result["previous_freshness"]["outcome"] == "unavailable"
    assert result["input_binding"] is None
    result = check.build_target_context_check(
        root,
        project_id="project",
        target_spec_id="SG-SPEC-0001",
        selection_path=Path("selection.yaml"),
        ontologyc=None,
    )
    assert result["outcome"] == "unavailable"
    assert result["bundle"]["outcome"] == "unavailable"


def test_previous_source_changed_foreign_and_malformed(workspace):
    root, _, _, selection, run = workspace
    old = run()
    (root / "previous.json").write_text(json.dumps(old))
    selection([{"id": "foundation", "namespace": "f", "version": "1.0.0"}])
    assert (
        run(previous_report_path=Path("previous.json"))["previous_freshness"]["outcome"] == "stale"
    )
    selection()
    old["bundle"]["binding_index"]["project_context"]["project_id"] = "foreign"
    old["bundle"]["validation_report"]["project_context"]["project_id"] = "foreign"
    (root / "previous.json").write_text(json.dumps(old))
    assert (
        run(previous_report_path=Path("previous.json"))["previous_freshness"]["outcome"]
        == "invalid"
    )
    (root / "previous.json").write_text("{broken")
    assert (
        run(previous_report_path=Path("previous.json"))["previous_freshness"]["outcome"]
        == "invalid"
    )


def test_invalid_component_precedes_unavailable_and_unknown_is_unavailable(workspace, monkeypatch):
    _, _, _, _, run = workspace
    monkeypatch.setattr(
        check,
        "build_context_reports",
        lambda *a, **k: {"outcome": "invalid", "diagnostics": ["bad bundle"]},
    )
    monkeypatch.setattr(
        check,
        "build_term_inventory",
        lambda *a, **k: {"outcome": "unavailable", "diagnostics": ["missing inventory"]},
    )
    assert run()["outcome"] == "invalid"
    monkeypatch.setattr(
        check, "build_context_reports", lambda *a, **k: {"outcome": "unexpected", "diagnostics": []}
    )
    assert run()["outcome"] == "unavailable"


def test_previous_bundle_freshness_never_certifies_inventory(workspace):
    root, _, _, _, run = workspace
    old = run()
    old["inventory"]["entries"] = [{"invented": "tampered"}]
    (root / "previous.json").write_text(json.dumps(old))
    current = run(previous_report_path=Path("previous.json"))
    assert current["previous_freshness"]["outcome"] == "fresh"
    assert current["previous_freshness"]["scope"] == "binding_validation_bundle"
    assert current["previous_freshness"]["inventory_freshness"] == "not_assessed"
    assert current["inventory_freshness"] == "not_assessed"
