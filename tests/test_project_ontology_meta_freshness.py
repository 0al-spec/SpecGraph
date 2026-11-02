"""Schema-3 freshness binds all explicit meta inputs without claiming attestation."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from project_ontology_check_scopes import SCOPED_ANALYSIS_PROFILE  # noqa: E402
from project_ontology_meta_freshness import (  # noqa: E402
    META_BUNDLE_PROFILE,
    assess_meta_freshness,
    bind_meta_bundle,
)
from spec_ontology_metamodel_check import PACKAGE, PROFILE, SOURCE_SHA256  # noqa: E402

DOMAIN = "domain_vocabulary"
META = "specification_metamodel"
H = "a" * 64


def _absent(scope):
    return {
        "check_scope": scope,
        "outcome": "not_requested",
        "diagnostics": [],
        "project_context": None,
        "analysis_profile": None,
        "summary": None,
    }


def _bundle(both=False):
    member = dict(zip(("id", "namespace", "version"), PACKAGE, strict=True))
    context = {
        "project_id": "gitview",
        "workspace": "/project",
        "context_revision": "sha256:" + H,
        "context_outcome": "verified",
        "scope": "single_member_local_symbols",
        "verified_closure": False,
        "analysis_profile": "specgraph-local-symbol-advisory-v3",
        "semantic_approval": "not_established",
        "binding_authority": "structural_advisory_only",
        "selected_member": member,
        "source_sha256": SOURCE_SHA256,
        "ir_sha256": H,
        "compiler_sha256": H,
        "compiler_provenance": "not_verified",
    }
    document = {
        "id": "GITVIEW-SPEC-0001",
        "path": "specs/nodes/GITVIEW-SPEC-0001.yaml",
        "sha256": H,
    }
    summary = {
        "document": document,
        "mapping_sha256": H,
        "decision_sha256": H,
        "decision_provenance": "caller_attributed_not_attested",
        "class_check": {
            "ontology_ref": "sgcore:Spec",
            "source": "/kind",
            "result": "matched",
            "origin": {
                "ontology_ref": "sgcore:Spec",
                "ontology_uri": f"ontology://{PACKAGE[0]}/{PACKAGE[2]}/classes/Spec",
                "package": member,
                "source_sha256": SOURCE_SHA256,
                "ir_sha256": H,
                "compiler_sha256": H,
                "verification": "compiler_checked",
            },
        },
        "node_membership": "not_assessed",
        "lifecycle": "not_assessed",
        "semantic_approval": "not_established",
        "canonical_mutations_allowed": False,
    }
    meta = {
        "check_scope": META,
        "outcome": "analyzed",
        "diagnostics": [],
        "project_context": context,
        "analysis_profile": PROFILE,
        "summary": summary,
    }
    bundle = {
        "schema_version": 3,
        "analysis_profile": META_BUNDLE_PROFILE,
        "requested_scopes": [META],
        "assessments": {DOMAIN: _absent(DOMAIN), META: meta},
        "outcome": "analyzed",
        "diagnostics": [],
        "inputs": None,
        "binding_index": None,
        "validation_report": None,
        "semantic_approval": "not_established",
        "full_spec_conformance": "not_assessed",
    }
    if both:
        domain_context = copy.deepcopy(context)
        domain_context["selected_member"] = {
            "id": "gitview",
            "namespace": "gitview",
            "version": "1.0.0",
        }
        domain_context["source_sha256"] = H
        inputs = {"specs_root": "specs/nodes", "specs": [{"path": document["path"], "sha256": H}]}
        child = {
            "schema_version": 2,
            "analysis_profile": SCOPED_ANALYSIS_PROFILE,
            "check_scope": DOMAIN,
            "entries": [],
            "summary": {},
            "project_context": domain_context,
            "inputs": inputs,
        }
        binding = {**child, "artifact_kind": "spec_ontology_binding_index"}
        validation = {**child, "artifact_kind": "spec_ontology_validation_report"}
        domain = {
            "check_scope": DOMAIN,
            "outcome": "analyzed",
            "diagnostics": [],
            "project_context": domain_context,
            "analysis_profile": SCOPED_ANALYSIS_PROFILE,
            "summary": {"binding_index": {}, "validation_report": {}},
        }
        bundle.update(
            requested_scopes=[DOMAIN, META],
            assessments={DOMAIN: domain, META: meta},
            inputs=inputs,
            binding_index=binding,
            validation_report=validation,
        )
    return bundle


@pytest.mark.parametrize("both", [False, True])
def test_complete_meta_bundles_bind_and_compare_without_attestation(both):
    bundle = _bundle(both)
    binding = bind_meta_bundle(bundle, producer_identity="producer-v2")
    result = assess_meta_freshness(
        bundle,
        input_binding=binding.report(),
        current_bundle=copy.deepcopy(bundle),
        producer_identity="producer-v2",
    )
    assert result.outcome == "fresh"
    assert result.report()["producer_provenance"] == "caller_attributed"
    assert result.report()["semantic_approval"] == "not_established"
    assert result.report()["tests_verified"] is False


@pytest.mark.parametrize("field", ["mapping_sha256", "decision_sha256"])
def test_new_current_mapping_or_disposition_is_stale(field):
    original = _bundle()
    binding = bind_meta_bundle(original, producer_identity="producer-v2")
    changed = copy.deepcopy(original)
    changed["assessments"][META]["summary"][field] = "b" * 64
    assert (
        assess_meta_freshness(
            original, input_binding=binding, current_bundle=changed, producer_identity="producer-v2"
        ).outcome
        == "stale"
    )


def test_new_document_context_or_producer_is_stale():
    original = _bundle()
    binding = bind_meta_bundle(original, producer_identity="producer-v2")
    changed = copy.deepcopy(original)
    changed["assessments"][META]["summary"]["document"]["sha256"] = "b" * 64
    assert (
        assess_meta_freshness(
            original, input_binding=binding, current_bundle=changed, producer_identity="producer-v2"
        ).outcome
        == "stale"
    )
    changed = copy.deepcopy(original)
    changed["assessments"][META]["project_context"]["context_revision"] = "sha256:" + "b" * 64
    assert (
        assess_meta_freshness(
            original, input_binding=binding, current_bundle=changed, producer_identity="producer-v2"
        ).outcome
        == "stale"
    )
    assert (
        assess_meta_freshness(
            original,
            input_binding=binding,
            current_bundle=original,
            producer_identity="producer-v3",
        ).outcome
        == "stale"
    )


def test_tampered_saved_or_binding_is_invalid_without_fallback():
    original = _bundle()
    binding = bind_meta_bundle(original, producer_identity="producer-v2").report()
    changed = copy.deepcopy(original)
    changed["assessments"][META]["summary"]["decision_sha256"] = "b" * 64
    assert (
        assess_meta_freshness(
            changed, input_binding=binding, current_bundle=original, producer_identity="producer-v2"
        ).outcome
        == "invalid"
    )
    binding["bundle_sha256"] = "b" * 64
    assert (
        assess_meta_freshness(
            original,
            input_binding=binding,
            current_bundle=original,
            producer_identity="producer-v2",
        ).outcome
        == "invalid"
    )


def test_tampered_binding_producer_is_invalid():
    bundle = _bundle()
    binding = bind_meta_bundle(bundle, producer_identity="producer-v2").report()
    binding["producer_identity"] = "fabricated"
    result = assess_meta_freshness(
        bundle, input_binding=binding, current_bundle=bundle, producer_identity="producer-v2"
    )
    assert result.outcome == "invalid"


def test_missing_partial_and_legacy_inputs_never_become_fresh():
    original = _bundle()
    binding = bind_meta_bundle(original, producer_identity="producer-v2")
    assert (
        assess_meta_freshness(
            original, input_binding=binding, current_bundle=None, producer_identity="producer-v2"
        ).outcome
        == "unavailable"
    )
    partial = copy.deepcopy(original)
    partial["assessments"][META]["summary"]["mapping_sha256"] = None
    assert (
        assess_meta_freshness(
            original, input_binding=binding, current_bundle=partial, producer_identity="producer-v2"
        ).outcome
        == "unavailable"
    )
    legacy = copy.deepcopy(original)
    legacy["schema_version"] = 2
    assert (
        assess_meta_freshness(
            original, input_binding=binding, current_bundle=legacy, producer_identity="producer-v2"
        ).outcome
        == "unavailable"
    )
    missing_slot = copy.deepcopy(original)
    del missing_slot["inputs"]
    assert (
        assess_meta_freshness(
            original,
            input_binding=binding,
            current_bundle=missing_slot,
            producer_identity="producer-v2",
        ).outcome
        == "unavailable"
    )


def test_scope_authority_and_cross_context_inconsistencies_fail_closed():
    original = _bundle(both=True)
    binding = bind_meta_bundle(original, producer_identity="producer-v2")
    for mutate in (
        lambda b: b["assessments"][META]["summary"].update(canonical_mutations_allowed=True),
        lambda b: b["assessments"][META]["summary"]["class_check"].update(
            ontology_ref="sgcore:Node"
        ),
        lambda b: b["assessments"][META]["summary"]["document"].update(
            path="../GITVIEW-SPEC-0001.yaml"
        ),
        lambda b: b["inputs"]["specs"][0].update(sha256="b" * 64),
        lambda b: b.update(binding_index=None),
    ):
        changed = copy.deepcopy(original)
        mutate(changed)
        assert assess_meta_freshness(
            original, input_binding=binding, current_bundle=changed, producer_identity="producer-v2"
        ).outcome in {"invalid", "unavailable"}
        with pytest.raises(ValueError):
            bind_meta_bundle(changed, producer_identity="producer-v2")
