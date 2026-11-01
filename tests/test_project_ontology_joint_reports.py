"""A composed vocabulary retains every candidate and its captured package origin."""

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from ontology_snapshot import OntologySnapshot  # noqa: E402
from project_ontology_context import (  # noqa: E402
    CheckResult,
    ContextResult,
    composition,
    foundation,
)
from project_ontology_report_freshness import (  # noqa: E402
    assess_report_freshness,
    bind_report_bundle,
)
from project_ontology_term_inventory import build_term_inventory  # noqa: E402
from spec_ontology_context_reports import build_context_reports  # noqa: E402


def sha(value):
    return hashlib.sha256(value).hexdigest()


@pytest.fixture
def joint(tmp_path):
    specs = tmp_path / "specs/nodes"
    specs.mkdir(parents=True)
    members = (("app.gitview", "gitview", "0.1.0"), composition.MOTIVATION, composition.EVENTS)
    snapshots = []
    for member, names in zip(
        members, (("Project", "Motive"), ("Motive",), ("Event",)), strict=True
    ):
        source = member[0].encode()
        raw = json.dumps(
            {
                **dict(zip(("id", "namespace", "version"), member, strict=True)),
                "classes": [
                    {"id": name, "fqid": f"{member[1]}:{name}", "aliases": ["Shared", "Общее"]}
                    for name in names
                ],
                "relations": [],
            }
        ).encode()
        snapshots.append(
            OntologySnapshot(source, raw, sha(source), "sha256:source", sha(raw), "a" * 64)
        )
    context = ContextResult(
        "gitview",
        str(tmp_path),
        "context.yaml",
        "verified",
        "sha256:" + "b" * 64,
        tuple(snapshots),
        members,
        tuple(CheckResult("member_capture", "verified", "captured", m[0]) for m in members)
        + (CheckResult("dependency_closure", "verified", "pinned closure"),),
        members,
        (composition.PROFILE,),
        (),
        (foundation.PIN,),
    )
    raw = b"""id: GITVIEW-SPEC-0001
specification:
  terminology:
    Project: {}
    Motive: {}
    Shared: {}
    Unknown: {}
  ontology_refs:
    - motivcore:Motive
    - sg:ValueObject
    - missing:Motive
"""
    documents = (("specs/nodes/GITVIEW-SPEC-0001.yaml", raw),)
    return tmp_path, specs, context, documents


def analyze(joint, context=None, documents=None):
    root, specs, captured, docs = joint
    arguments = dict(
        workspace_root=root, specs_root=specs, documents=docs if documents is None else documents
    )
    current = captured if context is None else context
    return build_term_inventory(current, **arguments), build_context_reports(current, **arguments)


def test_joint_explicit_inventory_and_binding_share_resolution_and_origins(joint):
    inventory, bundle = analyze(joint)
    assert inventory["outcome"] == bundle["outcome"] == "analyzed"
    terms = {e["term"]: e for e in inventory["entries"]}
    assert terms["motivcore:Motive"]["resolution"] == "structurally_resolved_candidate"
    assert terms["motivcore:Motive"]["candidates"] == ["motivcore:Motive"]
    [origin] = terms["motivcore:Motive"]["candidate_origins"]
    assert origin["package"] == dict(
        zip(("id", "namespace", "version"), composition.MOTIVATION, strict=True)
    )
    assert origin["ontology_uri"] == "ontology://org.0al.motivation.core/0.1.0/classes/Motive"
    assert origin["ir_sha256"] == joint[2].snapshots[1].ir_sha256
    assert terms["sg:ValueObject"]["resolution"] == "structurally_resolved_candidate"
    assert (
        terms["sg:ValueObject"]["candidate_origins"][0]["verification"] == "pinned_export_catalog"
    )
    for name in ("Motive", "Shared"):
        assert terms[name]["resolution"] == "ambiguous"
    for name in ("Unknown", "missing:Motive"):
        assert terms[name]["resolution"] == "unknown"
    entry = bundle["binding_index"]["entries"][0]
    bindings = {e["term"]: e for e in entry["accepted_bindings"]}
    assert "Motive" not in bindings and "Shared" not in bindings
    assert bindings["motivcore:Motive"]["candidate_origins"] == [origin]
    assert bindings["Project"]["ontology_ref"] == "gitview:Project"
    gaps = {e["term"]: e for e in entry["gaps"]}
    assert gaps["Motive"]["resolution"] == "ambiguous"
    findings = bundle["validation_report"]["entries"][0]["findings"]
    assert any(
        f.get("term") == "Motive" and f["classification"] == "ambiguous_ontology_term"
        for f in findings
    )
    assert (
        inventory["project_context"]["members"]
        == bundle["binding_index"]["project_context"]["members"]
    )
    assert inventory["grounded"] is False
    assert inventory["prose"] == "unassessed"
    assert bundle["validation_report"]["canonical_mutations_allowed"] is False


def test_order_and_captured_bytes_are_stable_without_reopening_ir(joint, monkeypatch):
    expected = analyze(joint)
    context = joint[2]
    reordered = replace(
        context,
        members=context.members[::-1],
        captured_members=context.captured_members[::-1],
        snapshots=context.snapshots[::-1],
    )
    read_bytes = Path.read_bytes

    def only_catalog(path):
        assert path == foundation.EXPORTS, f"reopened an input: {path}"
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", only_catalog)
    assert analyze(joint, reordered) == expected


@pytest.mark.parametrize(
    "change, expected",
    [
        ("missing", "unavailable"),
        ("hash", "invalid"),
        ("identity", "invalid"),
        ("closure", "unavailable"),
        ("profile", "unavailable"),
        ("invalid", "invalid"),
    ],
)
def test_no_partial_or_foreign_composition_fallback(joint, change, expected):
    context = joint[2]
    if change == "missing":
        context = replace(
            context,
            snapshots=context.snapshots[:-1],
            captured_members=context.captured_members[:-1],
        )
    elif change == "hash":
        context = replace(
            context,
            snapshots=(replace(context.snapshots[0], ir_sha256="0" * 64), *context.snapshots[1:]),
        )
    elif change == "identity":
        context = replace(
            context, captured_members=(("other", "gitview", "0.1.0"), *context.captured_members[1:])
        )
    elif change == "closure":
        context = replace(context, outcome="unavailable")
    elif change == "profile":
        context = replace(context, profiles=("ontologyc-structural-v1",))
    else:
        context = replace(context, outcome="invalid")
    for report in analyze(joint, context):
        assert report["outcome"] == expected


def test_freshness_covers_all_captured_packages_and_report_payloads(joint):
    root, specs, context, documents = joint
    _, bundle = analyze(joint)
    binding = bind_report_bundle(bundle, producer_identity="test-producer")

    def assess(selected):
        return assess_report_freshness(
            bundle,
            input_binding=binding,
            context=selected,
            workspace_root=root,
            specs_root=specs,
            documents=documents,
            producer_identity="test-producer",
        )

    assert assess(context).outcome == "fresh"
    dependency = context.snapshots[1]
    changed = dependency.source_bytes + b" changed"
    modified = replace(
        context,
        snapshots=(
            context.snapshots[0],
            replace(dependency, source_bytes=changed, source_sha256=sha(changed)),
            context.snapshots[2],
        ),
    )
    # Even an attributed revision left unchanged cannot hide changed dependency bytes.
    assert assess(modified).outcome == "stale"


@pytest.mark.parametrize("corrupt", [False, True])
def test_missing_or_changed_foundation_does_not_yield_a_partial_vocabulary(
    joint, monkeypatch, corrupt
):
    path = joint[0] / "catalog.json"
    if corrupt:
        path.write_text("{}")
    monkeypatch.setattr(foundation, "EXPORTS", path)
    for report in analyze(joint):
        assert report["outcome"] == ("invalid" if corrupt else "unavailable")


def test_qualified_names_are_exact_and_unicode_aliases_remain_ambiguous(joint):
    documents = (
        (
            "specs/nodes/GITVIEW-SPEC-0001.yaml",
            """id: GITVIEW-SPEC-0001
specification:
  terminology:
    ОБЩЕЕ: {}
  ontology_refs:
    - motivcore:Motive
    - MOTIVCORE:Motive
    - motivcore:motive
""".encode(),
        ),
    )
    inventory, bundle = analyze(joint, documents=documents)
    terms = {entry["term"]: entry for entry in inventory["entries"]}
    assert terms["ОБЩЕЕ"]["resolution"] == "ambiguous"
    assert terms["motivcore:Motive"]["resolution"] == "structurally_resolved_candidate"
    assert terms["MOTIVCORE:Motive"]["resolution"] == "unknown"
    assert terms["motivcore:motive"]["resolution"] == "unknown"
    binding = bundle["binding_index"]["entries"][0]
    assert [b["term"] for b in binding["accepted_bindings"]] == ["motivcore:Motive"]
    assert {g["term"] for g in binding["gaps"]} >= {"ОБЩЕЕ", "MOTIVCORE:Motive", "motivcore:motive"}


def test_saved_composed_bundle_requires_every_member_hash(joint):
    _, bundle = analyze(joint)
    for result in (bundle["binding_index"], bundle["validation_report"]):
        result["project_context"]["members"][1].pop("ir_sha256", None)
    with pytest.raises(ValueError, match="snapshot hash"):
        bind_report_bundle(bundle, producer_identity="test-producer")
