"""Scoped reports distinguish requested domain analysis from unavailable meta rules."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import spec_ontology_context_reports as reports  # noqa: E402
from ontology_snapshot import OntologySnapshot  # noqa: E402
from project_ontology_check_scopes import ScopeFacts, normalize_requested_scopes  # noqa: E402
from project_ontology_context import CheckResult, ContextResult  # noqa: E402
from project_ontology_scope_outcome_spec import REQUESTED_SCOPES_ANALYZED_SPEC  # noqa: E402
from spec_ontology_binding_index import build_binding_index  # noqa: E402
from spec_ontology_validation_report import build_validation_report  # noqa: E402

DOMAIN = "domain_vocabulary"
META = "specification_metamodel"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _ir(namespace="sgcore"):
    return {
        "id": "test-package",
        "namespace": namespace,
        "version": "1.0.0",
        "classes": [
            {"id": name, "fqid": f"{namespace}:{name}"}
            for name in ("Spec", "Node", "AcceptanceCriterion", "Evidence")
        ],
        "relations": [
            {
                "id": name,
                "fqid": f"{namespace}:{name}",
                "domain": f"{namespace}:{domain}",
                "range": f"{namespace}:{range_}",
            }
            for name, domain, range_ in (
                ("hasAcceptanceCriterion", "Spec", "AcceptanceCriterion"),
                ("evidenceSupportsCriterion", "Evidence", "AcceptanceCriterion"),
            )
        ],
    }


def _snapshot(ir):
    source = b"controlled ontology source"
    raw = json.dumps(ir).encode()
    return OntologySnapshot(source, raw, _sha(source), "sha256:source", _sha(raw), "a" * 64)


@pytest.fixture
def workspace(tmp_path):
    specs = tmp_path / "specs" / "nodes"
    specs.mkdir(parents=True)

    def analyze(document, *, namespace="gitview", **kwargs):
        ir = _ir(namespace)
        member = (ir["id"], namespace, ir["version"])
        context = ContextResult(
            "gitview",
            str(tmp_path),
            "selection.yaml",
            "verified",
            "sha256:" + "b" * 64,
            (_snapshot(ir),),
            (member,),
            (CheckResult("member_capture", "verified", "captured", member[0]),),
            (member,),
            ("ontologyc-structural-v1",),
            (),
        )
        documents = (("specs/nodes/GITVIEW-SPEC-0001.yaml", json.dumps(document).encode()),)
        return reports.build_context_reports(
            context, workspace_root=tmp_path, specs_root=specs, documents=documents, **kwargs
        )

    return analyze


def _structural_document():
    return {
        "id": "GITVIEW-SPEC-0001",
        "kind": "spec",
        "acceptance": ["A criterion"],
        "acceptance_evidence": [{"criterion": "A criterion", "evidence": "An observation"}],
    }


@pytest.mark.parametrize("namespace", ["gitview", "sgcore"])
def test_default_domain_analysis_does_not_infer_any_structural_binding(workspace, namespace):
    bundle = workspace(_structural_document(), namespace=namespace)
    assert bundle["outcome"] == "analyzed"
    assert bundle["schema_version"] == 2
    assert bundle["requested_scopes"] == [DOMAIN]
    assert bundle["semantic_approval"] == "not_established"
    assert bundle["full_spec_conformance"] == "not_assessed"
    index, validation = bundle["binding_index"], bundle["validation_report"]
    assert index["entries"][0]["accepted_bindings"] == []
    assert index["entries"][0]["relation_candidates"] == []
    assert index["entries"][0]["gaps"] == []
    assert validation["entries"][0]["checks"] == []
    assert validation["entries"][0]["findings"] == []
    for child in (index, validation):
        assert child["schema_version"] == 2
        assert child["check_scope"] == DOMAIN
    meta = bundle["assessments"][META]
    assert meta["outcome"] == "not_requested"
    assert meta["summary"] is meta["project_context"] is None


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("namespace", ["gitview", "sgcore"])
def test_explicit_sgcore_reference_is_analyzed_as_authored_domain_input(
    workspace, nested, namespace
):
    document = _structural_document()
    refs = {"ontology_refs": ["sgcore:Spec"]}
    document.update({"specification": refs} if nested else refs)
    bundle = workspace(document, namespace=namespace)
    assert bundle["outcome"] == "analyzed"
    entry = bundle["binding_index"]["entries"][0]
    findings = bundle["validation_report"]["entries"][0]["findings"]
    source = ("specification." if nested else "") + "ontology_refs[0]"
    assert not any(f["classification"] == "missing_required_binding" for f in findings)
    if namespace == "sgcore":
        [binding] = entry["accepted_bindings"]
        assert binding["ontology_ref"] == "sgcore:Spec"
        assert binding["source"] == source
        assert binding["candidate_origins"]
        assert entry["gaps"] == findings == []
    else:
        assert entry["accepted_bindings"] == []
        [gap] = entry["gaps"]
        [finding] = findings
        assert gap["term"] == finding["term"] == "sgcore:Spec"
        assert gap["source"] == finding["source"] == source
        assert gap["resolution"] == "unknown"


def test_explicit_spec_terminology_remains_a_candidate_without_meta_inference(workspace):
    document = _structural_document()
    document["specification"] = {"terminology": {"Spec": {}}}
    bundle = workspace(document, namespace="sgcore")
    [binding] = bundle["binding_index"]["entries"][0]["accepted_bindings"]
    assert binding["term"] == "Spec"
    assert binding["ontology_ref"] == "sgcore:Spec"
    assert binding["source"] == "specification.terminology"
    assert bundle["assessments"][META]["outcome"] == "not_requested"


@pytest.mark.parametrize("include_spec", [False, True])
def test_legacy_no_context_reports_keep_structural_rules(include_spec):
    ir = _ir()
    if not include_spec:
        ir["classes"] = [row for row in ir["classes"] if row["id"] != "Spec"]
    index = build_binding_index(
        ir=ir, documents=(("specs/nodes/SG-SPEC-0001.yaml", _structural_document()),)
    )
    validation = build_validation_report(snapshot=_snapshot(ir), binding_index=index)
    entry = index["entries"][0]
    refs = {binding["ontology_ref"] for binding in entry["accepted_bindings"]}
    assert {"sgcore:Node", "sgcore:AcceptanceCriterion", "sgcore:Evidence"} <= refs
    assert ("sgcore:Spec" in refs) is include_spec
    checks = {check["check_id"] for check in validation["entries"][0]["checks"]}
    findings = validation["entries"][0]["findings"]
    if include_spec:
        assert "required_binding.sgcore_spec" in checks
        assert "relation_contract.sgcore:hasAcceptanceCriterion" in checks
        assert "relation_contract.sgcore:evidenceSupportsCriterion" in checks
    else:
        assert any(f["classification"] == "missing_required_binding" for f in findings)
    assert index["schema_version"] == validation["schema_version"] == 1
    assert "check_scope" not in index and "check_scope" not in validation


def test_requested_unavailable_meta_retains_completed_domain_findings(workspace):
    document = _structural_document()
    document["ontology_refs"] = ["foreign:Unknown"]
    bundle = workspace(document, requested_scopes=(META, DOMAIN))
    assert bundle["requested_scopes"] == [DOMAIN, META]
    assert bundle["outcome"] == "unavailable"
    assert bundle["assessments"][DOMAIN]["outcome"] == "analyzed"
    assert bundle["assessments"][DOMAIN]["summary"] is not None
    meta = bundle["assessments"][META]
    assert meta["outcome"] == "unavailable"
    assert meta["summary"] is meta["project_context"] is None
    assert any("applicability" in detail.lower() for detail in meta["diagnostics"])
    [finding] = bundle["validation_report"]["entries"][0]["findings"]
    assert finding["term"] == "foreign:Unknown"


@pytest.mark.parametrize("requested", [(), (META,)])
def test_unrequested_domain_never_runs_analysis(workspace, monkeypatch, requested):
    def forbidden(*args, **kwargs):
        pytest.fail("an unrequested domain analysis must not run")

    for name in ("capture_vocabulary", "build_binding_index", "build_validation_report"):
        monkeypatch.setattr(reports, name, forbidden)
    bundle = workspace(_structural_document(), requested_scopes=requested)
    assert bundle["outcome"] == "unavailable"
    domain = bundle["assessments"][DOMAIN]
    assert domain["outcome"] == "not_requested"
    assert domain["summary"] is domain["project_context"] is None
    assert bundle["inputs"] is bundle["binding_index"] is bundle["validation_report"] is None


@pytest.mark.parametrize("requested", [None, DOMAIN, [DOMAIN, DOMAIN], ["unknown"], [1]])
def test_malformed_scope_requests_are_invalid_before_analysis(workspace, monkeypatch, requested):
    monkeypatch.setattr(
        reports,
        "capture_vocabulary",
        lambda *a, **k: pytest.fail("invalid request must not analyze"),
    )
    with pytest.raises(ValueError):
        normalize_requested_scopes(requested)
    bundle = workspace(_structural_document(), requested_scopes=requested)
    assert bundle["outcome"] == "invalid"
    assert bundle["diagnostics"]
    assert bundle["binding_index"] is bundle["validation_report"] is None


def test_invalid_domain_precedes_unavailable_requested_meta(workspace):
    document = _structural_document()
    document["ontology_refs"] = "not a reference list"
    bundle = workspace(document, requested_scopes=(DOMAIN, META))
    assert bundle["outcome"] == "invalid"
    assert bundle["assessments"][DOMAIN]["outcome"] == "invalid"
    assert bundle["assessments"][META]["outcome"] == "unavailable"
    assert bundle["assessments"][META]["diagnostics"]


@pytest.mark.parametrize(
    ("requested", "outcomes", "expected"),
    [
        ((), (), False),
        ((DOMAIN,), ("analyzed",), True),
        ((DOMAIN, META), ("analyzed", "analyzed"), True),
        ((DOMAIN, META), ("analyzed", "unavailable"), False),
        ((DOMAIN,), ("not_requested",), False),
        ((DOMAIN,), ("invalid",), False),
        ((DOMAIN,), (), False),
        ((DOMAIN,), ("analyzed", "analyzed"), False),
    ],
)
def test_scope_completion_requires_nonempty_complete_analysis(requested, outcomes, expected):
    assert (
        REQUESTED_SCOPES_ANALYZED_SPEC.is_satisfied_by(ScopeFacts(requested, outcomes)) is expected
    )


def test_scope_normalization_has_stable_order_without_adding_requests():
    assert normalize_requested_scopes([META, DOMAIN]) == (DOMAIN, META)
    assert normalize_requested_scopes([META]) == (META,)
    assert normalize_requested_scopes([]) == ()
