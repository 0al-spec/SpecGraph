"""Bounded context reports use captured ontology and one read of each spec."""

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import spec_ontology_context_reports as reports  # noqa: E402
from ontology_snapshot import OntologySnapshot  # noqa: E402
from project_ontology_context import CheckResult, ContextResult  # noqa: E402
from project_ontology_term_inventory import build_term_inventory  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def captured(tmp_path):
    specs = tmp_path / "specs" / "nodes"
    specs.mkdir(parents=True)
    path = specs / "SG-SPEC-0001.yaml"
    path.write_text(
        "id: SG-SPEC-0001\nkind: spec\nspecification:\n  terminology:\n    unknown_term: {}\n"
    )
    source = b"captured source"
    ir = json.dumps(
        {
            "id": "demo",
            "namespace": "sgcore",
            "version": "1.0.0",
            "classes": [
                {"id": "Spec", "fqid": "sgcore:Spec"},
                {"id": "Node", "fqid": "sgcore:Node"},
            ],
            "relations": [],
        }
    ).encode()
    snapshot = OntologySnapshot(source, ir, sha(source), "sha256:source", sha(ir), "a" * 64)
    member = ("demo", "sgcore", "1.0.0")
    context = ContextResult(
        "project",
        str(tmp_path),
        "selection.yaml",
        "verified",
        "sha256:revision",
        (snapshot,),
        (member,),
        (CheckResult("member_capture", "verified", "captured", "demo"),),
        (member,),
        ("ontologyc-structural-v1",),
        (),
    )
    return tmp_path, specs, path, context


def test_same_captured_specs_and_ir_used_by_both_reports(captured, monkeypatch):
    root, specs, path, context = captured
    original = path.read_bytes()
    build = reports.build_binding_index

    def change_after_capture(**kwargs):
        path.write_text("id: CHANGED\nkind: other\n")
        return build(**kwargs)

    monkeypatch.setattr(reports, "build_binding_index", change_after_capture)
    result = reports.build_context_reports(context, workspace_root=root, specs_root=specs)
    assert result["outcome"] == "analyzed"
    index, validation = result["binding_index"], result["validation_report"]
    assert index["entries"][0]["spec_id"] == validation["entries"][0]["spec_id"] == "SG-SPEC-0001"
    assert index["entries"][0]["path"] == "specs/nodes/SG-SPEC-0001.yaml"
    assert result["inputs"]["specs"] == [
        {"path": "specs/nodes/SG-SPEC-0001.yaml", "sha256": sha(original)}
    ]
    assert any(g["classification"] == "legacy_unknown_term" for g in index["entries"][0]["gaps"])
    assert validation["project_context"] == index["project_context"]
    assert validation["project_context"]["binding_authority"] == "structural_advisory_only"
    assert validation["ontology_ir_ref"] is None


def test_unavailable_closure_can_only_run_verified_local_capture(captured):
    root, specs, _, context = captured
    unavailable = replace(context, outcome="unavailable")
    result = reports.build_context_reports(unavailable, workspace_root=root, specs_root=specs)
    assert result["outcome"] == "analyzed"
    metadata = result["validation_report"]["project_context"]
    assert metadata["context_outcome"] == "unavailable"
    assert metadata["scope"] == "single_member_local_symbols"
    assert (
        metadata["verified_closure"] is False and metadata["semantic_approval"] == "not_established"
    )
    missing_check = replace(unavailable, checks=())
    assert (
        reports.build_context_reports(missing_check, workspace_root=root, specs_root=specs)[
            "outcome"
        ]
        == "unavailable"
    )


def test_invalid_missing_mismatch_and_multiple_never_fallback(captured, monkeypatch):
    root, specs, _, context = captured
    monkeypatch.setattr(
        reports, "build_binding_index", lambda **kwargs: pytest.fail("must not analyze")
    )
    member = context.members[0]
    cases = [
        (replace(context, outcome="invalid"), "invalid"),
        (replace(context, snapshots=(), captured_members=()), "unavailable"),
        (replace(context, captured_members=(("other", member[1], member[2]),)), "invalid"),
        (replace(context, members=(member, ("other", "other", "1.0.0"))), "unavailable"),
        (
            replace(context, snapshots=(replace(context.snapshots[0], ir_sha256="0" * 64),)),
            "invalid",
        ),
    ]
    for selected, outcome in cases:
        result = reports.build_context_reports(selected, workspace_root=root, specs_root=specs)
        assert result["outcome"] == outcome and result["diagnostics"]
        assert result["binding_index"] is result["validation_report"] is None


def test_workspace_and_spec_containment(captured, tmp_path):
    root, specs, path, context = captured
    assert (
        reports.build_context_reports(context, workspace_root=root.parent, specs_root=specs)[
            "outcome"
        ]
        == "invalid"
    )
    assert (
        reports.build_context_reports(context, workspace_root=root, specs_root=root.parent)[
            "outcome"
        ]
        == "invalid"
    )
    path.unlink()
    path.symlink_to(root.parent / "outside.yaml")
    result = reports.build_context_reports(context, workspace_root=root, specs_root=specs)
    assert result["outcome"] == "invalid" and "escapes" in result["diagnostics"][0]


def test_duplicate_spec_id_is_invalid(captured):
    root, specs, _, context = captured
    (specs / "SG-SPEC-0002.yaml").write_text("id: SG-SPEC-0001\nkind: spec\n")
    result = reports.build_context_reports(context, workspace_root=root, specs_root=specs)
    assert result["outcome"] == "invalid"
    assert "duplicate spec identity" in result["diagnostics"][0]
    assert result["binding_index"] is None


def test_explicit_captured_document_survives_source_removal(captured):
    root, specs, path, context = captured
    raw = path.read_bytes()
    name = path.relative_to(root).as_posix()
    path.unlink()
    result = reports.build_context_reports(
        context, workspace_root=root, specs_root=specs, documents=((name, raw),)
    )
    assert result["outcome"] == "analyzed"
    assert result["inputs"]["specs"] == [{"path": name, "sha256": sha(raw)}]
    assert result["binding_index"]["entries"][0]["spec_id"] == "SG-SPEC-0001"
    assert result["validation_report"]["entries"][0]["spec_id"] == "SG-SPEC-0001"


def test_explicit_document_still_rejects_symlink_escape(captured, tmp_path):
    root, specs, path, context = captured
    raw = path.read_bytes()
    name = path.relative_to(root).as_posix()
    path.unlink()
    path.symlink_to(tmp_path.parent / "outside.yaml")
    result = reports.build_context_reports(
        context, workspace_root=root, specs_root=specs, documents=((name, raw),)
    )
    assert result["outcome"] == "invalid" and "escapes" in result["diagnostics"][0]


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("reference", ["sgcore:Spec", "motivcore:Motive", "foreign:Spec"])
def test_single_member_explicit_references_appear_in_all_advisory_views(
    captured, nested, reference
):
    root, specs, path, context = captured
    field = {"ontology_refs": [reference]}
    document = {"id": "SG-SPEC-0001", **({"specification": field} if nested else field)}
    documents = ((path.relative_to(root).as_posix(), json.dumps(document).encode()),)
    inventory = build_term_inventory(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    bundle = reports.build_context_reports(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    assert inventory["outcome"] == bundle["outcome"] == "analyzed"
    [term] = inventory["entries"]
    entry = bundle["binding_index"]["entries"][0]
    findings = bundle["validation_report"]["entries"][0]["findings"]
    if reference == "sgcore:Spec":
        [binding] = [b for b in entry["accepted_bindings"] if b["term"] == reference]
        assert binding["candidate_origins"] == term["candidate_origins"]
        assert not any(f.get("term") == reference for f in findings)
    else:
        [gap] = [g for g in entry["gaps"] if g["term"] == reference]
        assert gap["classification"] == "missing_ontology_ref"
        assert gap["resolution"] == term["resolution"] == "unknown"
        [finding] = [f for f in findings if f.get("term") == reference]
        assert finding["source"] == ("specification." if nested else "") + "ontology_refs[0]"
        assert finding["candidate_origins"] == []
    for result in (bundle["binding_index"], bundle["validation_report"]):
        assert result["ontology_verification"]["status"] == "compiler_checked"
        assert result["ontology_verification"]["ir_sha256"] == context.snapshots[0].ir_sha256
        assert result["project_context"]["analysis_profile"] == "specgraph-local-symbol-advisory-v3"
        assert result["project_context"]["verified_closure"] is False
        assert result["canonical_mutations_allowed"] is False


def test_single_member_alias_ambiguity_matches_inventory(captured):
    root, specs, path, context = captured
    snapshot = context.snapshots[0]
    ir = json.loads(snapshot.ir_bytes)
    for symbol in ir["classes"]:
        symbol["aliases"] = ["Общий термин"]
    raw = json.dumps(ir).encode()
    context = replace(context, snapshots=(replace(snapshot, ir_bytes=raw, ir_sha256=sha(raw)),))
    document = {"id": "SG-SPEC-0001", "specification": {"terminology": {"Общий термин": {}}}}
    documents = ((path.relative_to(root).as_posix(), json.dumps(document).encode()),)
    inventory = build_term_inventory(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    bundle = reports.build_context_reports(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    [term] = inventory["entries"]
    [gap] = bundle["binding_index"]["entries"][0]["gaps"]
    assert gap["resolution"] == term["resolution"] == "ambiguous"
    assert gap["candidates"] == term["candidates"] == ["sgcore:Node", "sgcore:Spec"]
    assert gap["candidate_origins"] == term["candidate_origins"]
    assert any(
        f["classification"] == "ambiguous_ontology_term"
        for f in bundle["validation_report"]["entries"][0]["findings"]
    )


@pytest.mark.parametrize("bad", ["sgcore:Spec", [7], [None]])
@pytest.mark.parametrize("nested", [False, True])
def test_single_member_malformed_reference_list_is_explicitly_invalid(captured, bad, nested):
    root, specs, path, context = captured
    field = {"ontology_refs": bad}
    document = {"id": "SG-SPEC-0001", **({"specification": field} if nested else field)}
    documents = ((path.relative_to(root).as_posix(), json.dumps(document).encode()),)
    inventory = build_term_inventory(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    bundle = reports.build_context_reports(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    assert inventory["outcome"] == bundle["outcome"] == "invalid"


def test_single_member_qualified_terminology_cannot_match_another_namespace(captured):
    root, specs, path, context = captured
    documents = (
        (
            path.relative_to(root).as_posix(),
            b"""id: SG-SPEC-0001
kind: spec
specification:
  terminology:
    sgcore:Spec: {}
    foreign:Spec: {}
    SGCORE:Spec: {}
    sgcore:spec: {}
""",
        ),
    )
    inventory = build_term_inventory(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    bundle = reports.build_context_reports(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    terms = {e["term"]: e for e in inventory["entries"]}
    entry = bundle["binding_index"]["entries"][0]
    assert any(
        b["term"] == "sgcore:Spec" and b["ontology_ref"] == "sgcore:Spec"
        for b in entry["accepted_bindings"]
    )
    for term in ("foreign:Spec", "SGCORE:Spec", "sgcore:spec"):
        assert terms[term]["resolution"] == "unknown"
        assert any(g["term"] == term and g["resolution"] == "unknown" for g in entry["gaps"])


def test_single_member_unique_alias_keeps_attributed_candidate(captured):
    root, specs, path, context = captured
    snapshot = context.snapshots[0]
    ir = json.loads(snapshot.ir_bytes)
    ir["classes"][0]["aliases"] = ["Known alias"]
    raw = json.dumps(ir).encode()
    context = replace(context, snapshots=(replace(snapshot, ir_bytes=raw, ir_sha256=sha(raw)),))
    documents = (
        (
            path.relative_to(root).as_posix(),
            b"""id: SG-SPEC-0001
specification:
  terminology:
    Known alias: {}
""",
        ),
    )
    inventory = build_term_inventory(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    bundle = reports.build_context_reports(
        context, workspace_root=root, specs_root=specs, documents=documents
    )
    [term] = inventory["entries"]
    [binding] = [
        candidate
        for candidate in bundle["binding_index"]["entries"][0]["accepted_bindings"]
        if candidate["term"] == "Known alias"
    ]
    assert term["resolution"] == "spelling_candidate"
    assert binding["ontology_ref"] == "sgcore:Spec"
    assert binding["candidate_origins"] == term["candidate_origins"]
