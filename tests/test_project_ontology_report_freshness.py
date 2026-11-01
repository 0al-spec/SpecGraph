"""Freshness remains scoped to explicit, captured report inputs."""

import copy
import hashlib
import json
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from ontology_snapshot import OntologySnapshot  # noqa: E402
from project_ontology_context import CheckResult, ContextResult  # noqa: E402
from project_ontology_report_freshness import (  # noqa: E402
    ReportInputBinding,
    assess_report_freshness,
    bind_report_bundle,
)
from spec_ontology_context_reports import build_context_reports  # noqa: E402


@pytest.fixture
def captured(tmp_path):
    specs = tmp_path / "specs" / "nodes"
    specs.mkdir(parents=True)
    spec = specs / "SG-SPEC-0001.yaml"
    spec.write_text(
        "id: SG-SPEC-0001\nkind: spec\nspecification:\n  terminology:\n    unknown_term: {}\n"
    )
    source = b"source"
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

    def digest(value):
        return hashlib.sha256(value).hexdigest()

    snap = OntologySnapshot(source, ir, digest(source), "sha256:source", digest(ir), "a" * 64)
    member = ("demo", "sgcore", "1.0.0")
    context = ContextResult(
        "project",
        str(tmp_path),
        "selection.yaml",
        "verified",
        "sha256:" + "b" * 64,
        (snap,),
        (member,),
        (CheckResult("member_capture", "verified", "captured", "demo"),),
        (member,),
        ("ontologyc-structural-v1",),
        (),
    )
    bundle = build_context_reports(context, workspace_root=tmp_path, specs_root=specs)
    input_binding = bind_report_bundle(bundle, producer_identity="producer-v1")

    def assess(
        bundle=bundle,
        input_binding=input_binding,
        context=context,
        producer="producer-v1",
        requested_scopes=("domain_vocabulary",),
    ):
        return assess_report_freshness(
            bundle,
            input_binding=input_binding,
            context=context,
            workspace_root=tmp_path,
            specs_root=specs,
            producer_identity=producer,
            requested_scopes=requested_scopes,
        )

    return spec, context, bundle, input_binding, assess


def test_fresh_result_with_serialized_input_binding_and_immutable_capture(captured):
    spec, _, bundle, input_binding, assess = captured
    result = assess(input_binding=input_binding.report())
    assert result.outcome == "fresh"
    assert result.report()["semantic_approval"] == "not_established"
    assert result.report()["tests_verified"] is False
    original = copy.deepcopy(bundle)
    spec.write_text("id: SG-SPEC-0001\nkind: changed\n")
    assert bundle == original
    assert assess().outcome == "stale"
    assert "spec_inputs changed" in assess().diagnostics
    with pytest.raises(FrozenInstanceError):
        input_binding.bundle_sha256 = "0" * 64


def test_changed_project_context_and_producer(captured):
    _, context, _, _, assess = captured
    assert assess(context=replace(context, project_id="foreign")).outcome == "stale"
    assert assess(context=replace(context, revision="sha256:" + "c" * 64)).outcome == "stale"
    assert assess(producer="producer-v2").outcome == "stale"
    assert assess(context=replace(context, revision=None)).outcome == "unavailable"


def test_binding_change_and_profile_change_are_stale(captured):
    _, _, bundle, _, assess = captured
    changed_binding = copy.deepcopy(bundle)
    changed_binding["binding_index"]["entries"][0]["gaps"] = []
    saved = bind_report_bundle(changed_binding, producer_identity="producer-v1")
    assert (
        "binding_payload changed" in assess(bundle=changed_binding, input_binding=saved).diagnostics
    )
    changed_profile = copy.deepcopy(bundle)
    for key in ("binding_index", "validation_report"):
        changed_profile[key]["project_context"]["analysis_profile"] = "other-profile"
    changed_profile["assessments"]["domain_vocabulary"]["project_context"] = copy.deepcopy(
        changed_profile["binding_index"]["project_context"]
    )
    saved = bind_report_bundle(changed_profile, producer_identity="producer-v1")
    assert (
        "analysis_profile changed"
        in assess(bundle=changed_profile, input_binding=saved).diagnostics
    )


def test_tamper_missing_and_incomplete_never_fallback(captured, monkeypatch):
    import project_ontology_report_freshness as freshness

    _, _, bundle, _, assess = captured
    tampered = copy.deepcopy(bundle)
    tampered["binding_index"]["entries"] = []
    assert assess(bundle=tampered).outcome == "invalid"
    monkeypatch.setattr(
        freshness, "build_context_reports", lambda *a, **k: pytest.fail("no fallback")
    )
    assert assess(input_binding=None).outcome == "unavailable"
    assert assess(producer=None).outcome == "unavailable"
    incomplete = copy.deepcopy(bundle)
    incomplete["validation_report"] = None
    assert assess(bundle=incomplete).outcome == "unavailable"


def test_missing_identity_and_inconsistent_metadata(captured):
    _, context, bundle, input_binding, assess = captured
    assert assess(context=replace(context, revision="unknown")).outcome == "unavailable"
    inconsistent = copy.deepcopy(bundle)
    inconsistent["validation_report"]["inputs"] = {"specs_root": "elsewhere", "specs": []}
    assert assess(bundle=inconsistent).outcome == "invalid"
    missing = copy.deepcopy(bundle)
    del missing["binding_index"]["project_context"]["analysis_profile"]
    assert assess(bundle=missing).outcome == "unavailable"
    assert input_binding.report()["producer_provenance"] == "caller_attributed"


def test_changed_captured_ir_identity_is_stale(captured):
    _, context, _, _, assess = captured
    original = context.snapshots[0]
    ir = json.loads(original.ir_bytes)
    ir["classes"].append({"id": "New", "fqid": "sgcore:New"})
    ir_bytes = json.dumps(ir).encode()
    snapshot = replace(original, ir_bytes=ir_bytes, ir_sha256=hashlib.sha256(ir_bytes).hexdigest())
    changed = replace(context, snapshots=(snapshot,))
    result = assess(context=changed)
    assert result.outcome == "stale" and "ir_sha256 changed" in result.diagnostics


def test_saved_single_member_v1_profile_is_stale(captured):
    _, _, bundle, _, assess = captured
    historical = copy.deepcopy(bundle)
    for name in ("binding_index", "validation_report"):
        historical[name]["project_context"]["analysis_profile"] = (
            "specgraph-local-symbol-advisory-v1"
        )
    historical["assessments"]["domain_vocabulary"]["project_context"] = copy.deepcopy(
        historical["binding_index"]["project_context"]
    )
    binding = bind_report_bundle(historical, producer_identity="producer-v1")
    result = assess(bundle=historical, input_binding=binding)
    assert result.outcome == "stale"
    assert "analysis_profile changed" in result.diagnostics


def test_fresh_comparisons_include_requested_and_assessed_scopes(captured):
    _, _, bundle, _, assess = captured
    result = assess()
    assert result.outcome == "fresh"
    assert bundle["schema_version"] == 2
    assert bundle["requested_scopes"] == ["domain_vocabulary"]
    assert bundle["assessments"]["specification_metamodel"]["outcome"] == "not_requested"
    comparisons = dict(result.comparisons)
    assert comparisons["requested_scopes"]
    assert comparisons["scope_assessments"]
    assert comparisons["bundle_analysis_profile"]


def test_changed_scope_assessment_cannot_stay_fresh_with_matching_domain_payloads(captured):
    _, _, bundle, _, assess = captured
    changed = copy.deepcopy(bundle)
    changed["assessments"]["specification_metamodel"]["diagnostics"] = [
        "No metamodel assessment was requested at capture time."
    ]
    binding = bind_report_bundle(changed, producer_identity="producer-v1")
    result = assess(bundle=changed, input_binding=binding)
    assert result.outcome == "stale"
    assert "scope_assessments changed" in result.diagnostics
    assert dict(result.comparisons)["binding_payload"]
    assert dict(result.comparisons)["validation_payload"]


@pytest.mark.parametrize(
    "requested",
    [(), ("specification_metamodel",), ("domain_vocabulary", "specification_metamodel")],
)
def test_unassessed_current_scopes_never_compare_fresh(captured, requested):
    *_, assess = captured
    assert assess(requested_scopes=requested).outcome == "unavailable"


@pytest.mark.parametrize("requested", [("unknown",), ("domain_vocabulary", "domain_vocabulary")])
def test_invalid_current_scope_request_stays_invalid(captured, requested):
    *_, assess = captured
    assert assess(requested_scopes=requested).outcome == "invalid"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b.__setitem__("requested_scopes", ["unknown"]),
        lambda b: b.__setitem__("requested_scopes", ["domain_vocabulary"] * 2),
        lambda b: b["assessments"].pop("specification_metamodel"),
        lambda b: b["assessments"]["domain_vocabulary"].__setitem__("check_scope", "wrong"),
        lambda b: b["assessments"]["specification_metamodel"].__setitem__("outcome", "analyzed"),
        lambda b: b["assessments"]["domain_vocabulary"].__setitem__("diagnostics", "clean"),
        lambda b: b["binding_index"].__setitem__("check_scope", "specification_metamodel"),
        lambda b: b["binding_index"].__setitem__("analysis_profile", "combined-legacy-profile"),
        lambda b: b["validation_report"].__setitem__("analysis_profile", "combined-legacy-profile"),
        lambda b: b["validation_report"].__setitem__("schema_version", 1),
        lambda b: b["assessments"]["domain_vocabulary"].__setitem__("summary", {}),
    ],
    ids=[
        "unknown-scope",
        "duplicate-scope",
        "missing-scope-status",
        "wrong-assessment-scope",
        "unexpected-meta-success",
        "malformed-diagnostics",
        "wrong-report-scope",
        "wrong-binding-profile",
        "wrong-validation-profile",
        "old-report-version",
        "inconsistent-summary",
    ],
)
def test_malformed_saved_scope_claims_are_invalid(captured, mutation):
    _, _, bundle, _, assess = captured
    malformed = copy.deepcopy(bundle)
    mutation(malformed)
    assert assess(bundle=malformed).outcome == "invalid"
    with pytest.raises(ValueError):
        bind_report_bundle(malformed, producer_identity="producer-v1")


def test_scope_manifest_tamper_is_invalid_before_current_scope_change(captured):
    _, _, bundle, _, assess = captured
    changed = copy.deepcopy(bundle)
    changed["requested_scopes"].append("specification_metamodel")
    changed["assessments"]["specification_metamodel"]["outcome"] = "unavailable"
    changed["assessments"]["specification_metamodel"]["diagnostics"] = ["not supported"]
    changed["outcome"] = "unavailable"
    assert (
        assess(bundle=changed, requested_scopes=("specification_metamodel",)).outcome == "invalid"
    )


def test_old_combined_bundle_cannot_become_fresh_by_rebinding(captured):
    _, _, bundle, _, assess = captured
    historical = copy.deepcopy(bundle)
    for key in ("schema_version", "analysis_profile", "requested_scopes", "assessments"):
        historical.pop(key)
    for report in (historical["binding_index"], historical["validation_report"]):
        report.pop("check_scope")
        report["schema_version"] = 1
        report["project_context"]["analysis_profile"] = "specgraph-local-symbol-advisory-v2"

    def digest(value):
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()

    rebound = ReportInputBinding(
        digest(historical), digest(historical["binding_index"]), "producer-v1"
    )
    assert assess(bundle=historical, input_binding=rebound).outcome == "unavailable"
    with pytest.raises(ValueError, match="scoped advisory bundle version"):
        bind_report_bundle(historical, producer_identity="producer-v1")


@pytest.mark.parametrize("missing", ["validation_report", "assessments"])
def test_incomplete_current_bundle_is_unavailable(captured, monkeypatch, missing):
    import project_ontology_report_freshness as freshness

    _, _, bundle, _, assess = captured
    incomplete = copy.deepcopy(bundle)
    incomplete.pop(missing)
    monkeypatch.setattr(freshness, "build_context_reports", lambda *args, **kwargs: incomplete)
    assert assess().outcome == "unavailable"
