"""Target-level integration with independently captured ontology contexts.

The decision is loaded from the repository; context capture is stubbed and
therefore these tests do not claim a real compiler execution.
"""

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import project_ontology_supervisor_check as check  # noqa: E402
from ontology_snapshot import OntologySnapshot  # noqa: E402
from project_ontology_context.model import CheckResult, ContextResult  # noqa: E402
from spec_ontology_metamodel_check import PACKAGE, SOURCE_SHA256  # noqa: E402

DOMAIN = "domain_vocabulary"
META = "specification_metamodel"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def context(root, member, source, ir, revision):
    snapshot = OntologySnapshot(
        source, ir, digest(source), "sha256:" + digest(source), digest(ir), "a" * 64
    )
    return ContextResult(
        "gitview",
        str(root),
        "selection.yaml",
        "verified",
        "sha256:" + revision * 64,
        (snapshot,),
        (member,),
        (CheckResult("member_capture", "verified", "captured", member[0]),),
        (member,),
        ("ontologyc-structural-v1",),
        (),
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    directory = tmp_path / "specs" / "nodes"
    directory.mkdir(parents=True)
    target = directory / "GITVIEW-SPEC-0001.yaml"
    target.write_text("id: GITVIEW-SPEC-0001\nkind: spec\nstatus: idea\n")
    source = (ROOT / "ontology/packages/specgraph-core/domain-ontology-package.yaml").read_bytes()
    ir = (ROOT / "ontology/packages/specgraph-core/generated/ontology.normalized.json").read_bytes()
    assert digest(source) == SOURCE_SHA256
    meta = context(tmp_path, PACKAGE, source, ir, "b")
    member = ("gitview", "gitview", "1.0.0")
    domain_source = b"independent synthetic domain source"
    domain_ir = json.dumps(
        {
            "id": member[0],
            "namespace": member[1],
            "version": member[2],
            "classes": [{"id": "Project", "fqid": "gitview:Project"}],
            "relations": [],
        }
    ).encode()
    domain = context(tmp_path, member, domain_source, domain_ir, "c")
    contexts = {Path("domain.yaml"): domain, Path("meta.yaml"): meta}
    captured = []

    def capture(root, *, project_id, selection_path, ontologyc, compiler_sha256):
        captured.append(selection_path)
        return contexts[selection_path]

    monkeypatch.setattr(check, "capture_project_context", capture)

    def run(**overrides):
        kwargs = {
            "project_id": "gitview",
            "target_spec_id": "GITVIEW-SPEC-0001",
            "selection_path": Path("domain.yaml"),
            "metamodel_selection_path": Path("meta.yaml"),
            "ontologyc": None,
            "requested_scopes": (META,),
            "map_spec_artifact": True,
        }
        kwargs.update(overrides)
        return check.build_target_context_check(tmp_path, **kwargs)

    return tmp_path, target, contexts, captured, run


def test_meta_only_never_captures_domain(env):
    _, _, _, captured, run = env
    result = run()
    assert captured == [Path("meta.yaml")]
    assert result["outcome"] == "checked", result["diagnostics"]
    assert result["bundle"]["schema_version"] == 3
    assert result["assessments"][META]["outcome"] == "analyzed"
    assert result["assessments"][DOMAIN]["outcome"] == "not_requested"
    assert result["inventory"] is None
    assert result["input_binding"]["producer_provenance"] == "caller_attributed"


def test_both_scopes_capture_distinct_sources(env):
    _, _, _, captured, run = env
    result = run(requested_scopes=(DOMAIN, META))
    assert captured == [Path("domain.yaml"), Path("meta.yaml")]
    assert result["outcome"] == "checked", result["diagnostics"]
    assert all(result["assessments"][scope]["outcome"] == "analyzed" for scope in (DOMAIN, META))
    domain = result["assessments"][DOMAIN]["project_context"]["selected_member"]
    meta = result["assessments"][META]["project_context"]["selected_member"]
    assert domain["namespace"] == "gitview" and meta["namespace"] == "sgcore"


def test_missing_mapping_is_unavailable_and_domain_survives(env):
    _, _, _, _, run = env
    result = run(requested_scopes=(DOMAIN, META), map_spec_artifact=False)
    assert result["outcome"] == "unavailable"
    assert result["assessments"][DOMAIN]["outcome"] == "analyzed"
    assert result["assessments"][META]["outcome"] == "unavailable"
    assert result["bundle"]["binding_index"] is not None


def test_invalid_pin_precedes_missing_mapping(env):
    _, _, contexts, _, run = env
    context_ = contexts[Path("meta.yaml")]
    bad = replace(context_.snapshots[0], source_sha256="0" * 64)
    contexts[Path("meta.yaml")] = replace(context_, snapshots=(bad,))
    result = run(map_spec_artifact=False)
    assert result["outcome"] == "invalid"
    assert result["assessments"][META]["outcome"] == "invalid"


def test_previous_report_is_fresh_then_stale_on_document_change(env):
    root, target, _, _, run = env
    original = run()
    assert original["outcome"] == "checked", original["diagnostics"]
    (root / "previous.json").write_text(json.dumps(original))
    repeated = run(previous_report_path=Path("previous.json"))
    assert repeated["previous_freshness"]["outcome"] == "fresh"
    target.write_text(target.read_text() + "title: Changed\n")
    changed = run(previous_report_path=Path("previous.json"))
    assert changed["previous_freshness"]["outcome"] == "stale"


def test_previous_domain_only_schema2_never_fresh_for_meta(env):
    root, _, _, _, run = env
    original = run(requested_scopes=(DOMAIN,))
    assert original["outcome"] == "checked", original["diagnostics"]
    assert original["bundle"]["schema_version"] == 2
    (root / "previous.json").write_text(json.dumps(original))
    result = run(previous_report_path=Path("previous.json"))
    assert result["outcome"] == "checked", result["diagnostics"]
    assert result["previous_freshness"]["outcome"] != "fresh"
