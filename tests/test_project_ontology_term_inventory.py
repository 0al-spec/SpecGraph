"""Explicit term locations and bounded advisory resolution."""

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from ontology_snapshot import OntologySnapshot  # noqa: E402
from project_ontology_context import CheckResult, ContextResult  # noqa: E402
from project_ontology_term_inventory import build_term_inventory  # noqa: E402


def sha(value):
    return hashlib.sha256(value).hexdigest()


@pytest.fixture
def sample(tmp_path):
    specs = tmp_path / "specs" / "nodes"
    specs.mkdir(parents=True)
    spec = specs / "SG-SPEC-0001.yaml"
    spec.write_text("""id: SG-SPEC-0001
ontology_refs:
  - "demo:Spec"
  - 'demo:Missing'
specification:
  terminology:
    'Known term': definition
    Shared: definition
    Unknown: definition
  ontology_refs:
    - demo:Node
  prose: "This mentions Ghost but is not analyzed."
""")
    source = b"source"
    ir = json.dumps(
        {
            "id": "pkg",
            "namespace": "demo",
            "version": "1.0.0",
            "classes": [
                {"id": "Spec", "fqid": "demo:Spec", "aliases": ["Known term"]},
                {"id": "Node", "fqid": "demo:Node", "aliases": ["Shared"]},
                {"id": "Other", "fqid": "demo:Other", "aliases": ["Shared"]},
            ],
            "relations": [],
        }
    ).encode()
    snapshot = OntologySnapshot(source, ir, sha(source), "sha256:source", sha(ir), "a" * 64)
    member = ("pkg", "demo", "1.0.0")
    context = ContextResult(
        "project",
        str(tmp_path),
        "selection.yaml",
        "verified",
        "sha256:revision",
        (snapshot,),
        (member,),
        (CheckResult("member_capture", "verified", "ok", "pkg"),),
        (member,),
        ("ontologyc-structural-v1",),
        (),
    )
    return tmp_path, specs, spec, context


def inventory(sample, **kwargs):
    root, specs, _, context = sample
    return build_term_inventory(
        kwargs.pop("context", context),
        workspace_root=kwargs.pop("workspace_root", root),
        specs_root=kwargs.pop("specs_root", specs),
        **kwargs,
    )


def test_explicit_fields_positions_and_resolutions(sample):
    result = inventory(sample)
    assert result["outcome"] == "analyzed" and result["prose"] == "unassessed"
    assert result["grounded"] is False and result["full_spec_conformance"] == "not_assessed"
    entries = {entry["term"]: entry for entry in result["entries"]}
    assert set(entries) == {
        "demo:Spec",
        "demo:Missing",
        "Known term",
        "Shared",
        "Unknown",
        "demo:Node",
    }
    assert entries["demo:Spec"]["resolution"] == "structurally_resolved_candidate"
    assert entries["demo:Spec"]["location"]["start"] == {"line": 3, "column": 5, "offset": 36}
    assert entries["demo:Spec"]["location"]["end"]["column"] == 16
    assert entries["Known term"]["resolution"] == "spelling_candidate"
    assert entries["Known term"]["location"]["start"]["line"] == 7
    assert (
        entries["Shared"]["resolution"] == "ambiguous" and len(entries["Shared"]["candidates"]) == 2
    )
    assert entries["demo:Missing"]["classification"] == "missing_ontology_ref"
    assert entries["Unknown"]["classification"] == "legacy_unknown_term"
    assert all(
        entry["spec_id"] == "SG-SPEC-0001" and entry["path"] == "specs/nodes/SG-SPEC-0001.yaml"
        for entry in entries.values()
    )


def test_supplied_bytes_stable_and_zero_does_not_imply_grounding(sample):
    _, _, spec, context = sample
    raw = spec.read_bytes()
    spec.write_text("id: changed\n")
    result = inventory(
        sample,
        documents=(("specs/nodes/SG-SPEC-0001.yaml", raw),),
        context=replace(context, outcome="unavailable"),
    )
    assert result["entries"][0]["spec_id"] == "SG-SPEC-0001"
    assert result["inputs"]["specs"][0]["sha256"] == sha(raw)
    assert result["project_context"]["context_outcome"] == "unavailable"
    assert result["project_context"]["verified_closure"] is False
    empty = inventory(sample)
    assert empty["entries"] == [] and empty["grounded"] is False and empty["prose"] == "unassessed"


def test_context_and_path_boundaries(sample):
    root, specs, spec, context = sample
    assert inventory(sample, workspace_root=root.parent)["outcome"] == "invalid"
    assert inventory(sample, specs_root=root.parent)["outcome"] == "invalid"
    assert inventory(sample, context=replace(context, outcome="invalid"))["outcome"] == "invalid"
    assert (
        inventory(sample, context=replace(context, members=context.members * 2))["outcome"]
        == "unavailable"
    )
    assert inventory(sample, context=replace(context, snapshots=()))["outcome"] == "unavailable"
    for name in ("../escape.yaml", "/tmp/escape.yaml", "specs/nodes/../nodes/SG-SPEC-0001.yaml"):
        assert inventory(sample, documents=((name, b"id: x"),))["outcome"] == "invalid"
    outside = root.parent / "SG-SPEC-external.yaml"
    outside.write_text("id: outside")
    spec.unlink()
    spec.symlink_to(outside)
    assert inventory(sample)["outcome"] == "invalid"


def test_duplicate_identity_is_rejected(sample):
    _, specs, _, _ = sample
    (specs / "SG-SPEC-0002.yaml").write_text("id: SG-SPEC-0001\n")
    result = inventory(sample)
    assert result["outcome"] == "invalid" and "duplicate spec identity" in result["diagnostics"][0]


def test_capture_integrity_and_ambiguous_evidence(sample):
    _, _, _, context = sample
    assert inventory(sample, context=replace(context, checks=()))["outcome"] == "unavailable"
    assert (
        inventory(sample, context=replace(context, captured_members=(("wrong", "demo", "1.0.0"),)))[
            "outcome"
        ]
        == "invalid"
    )
    snapshot = replace(context.snapshots[0], ir_sha256="0" * 64)
    assert (
        inventory(sample, context=replace(context, snapshots=(snapshot,)))["outcome"] == "invalid"
    )


def test_field_path_identifies_terminology_key(sample):
    result = inventory(sample)
    entry = next(e for e in result["entries"] if e["term"] == "Known term")
    assert entry["field_path"] == 'specification.terminology["Known term"]'
    assert entry["source"] == "specification.terminology"


def test_unicode_alias_is_distinct_from_unrelated_term_and_casefolded(sample):
    _, _, spec, context = sample
    spec.write_text(
        "id: SG-SPEC-0001\nspecification:\n  terminology:\n"
        "    Требование: {}\n    ТРЕБОВАНИЕ: {}\n    Призрак: {}\n"
    )
    snapshot = context.snapshots[0]
    ir = json.loads(snapshot.ir_bytes)
    ir["classes"][0]["aliases"].append("Требование")
    raw = json.dumps(ir, ensure_ascii=False).encode()
    context = replace(context, snapshots=(replace(snapshot, ir_bytes=raw, ir_sha256=sha(raw)),))
    result = inventory(sample, context=context)
    assert result["outcome"] == "analyzed"
    entries = {entry["term"]: entry for entry in result["entries"]}
    for term in ("Требование", "ТРЕБОВАНИЕ"):
        assert entries[term]["resolution"] == "spelling_candidate"
        assert entries[term]["candidates"] == ["demo:Spec"]
        assert entries[term]["authority"] == "structural_advisory_only"
    assert entries["Призрак"]["resolution"] == "unknown"
    assert entries["Призрак"]["classification"] == "legacy_unknown_term"
    assert entries["Призрак"]["candidates"] == []
    assert result["project_context"]["semantic_approval"] == "not_established"


def test_captured_documents_survive_deleted_source(sample):
    _, _, spec, _ = sample
    original = spec.read_bytes()
    expected = inventory(sample)
    spec.unlink()
    result = inventory(sample, documents=(("specs/nodes/SG-SPEC-0001.yaml", original),))
    assert result["outcome"] == "analyzed"
    assert result["entries"] == expected["entries"]
    assert result["inputs"]["specs"][0]["sha256"] == sha(original)
    entry = next(item for item in result["entries"] if item["term"] == "demo:Spec")
    assert entry["location"]["start"] == {"line": 3, "column": 5, "offset": 36}
