"""The first metamodel slice only recognizes an explicit document class."""

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from ontology_snapshot import OntologySnapshot  # noqa: E402
from project_ontology_context.model import CheckResult, ContextResult  # noqa: E402
from spec_ontology_metamodel_check import (  # noqa: E402
    PACKAGE,
    PROFILE,
    SOURCE_SHA256,
    assess_metamodel,
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def inputs(tmp_path):
    source = (ROOT / "ontology/packages/specgraph-core/domain-ontology-package.yaml").read_bytes()
    ir = (ROOT / "ontology/packages/specgraph-core/generated/ontology.normalized.json").read_bytes()
    assert sha(source) == SOURCE_SHA256
    snapshot = OntologySnapshot(source, ir, sha(source), "sha256:" + sha(source), sha(ir), "a" * 64)
    context = ContextResult(
        "gitview",
        str(tmp_path),
        "selection.yaml",
        "verified",
        "sha256:" + "b" * 64,
        (snapshot,),
        (PACKAGE,),
        (CheckResult("member_capture", "verified", "ok", PACKAGE[0]),),
        (PACKAGE,),
        ("specgraph-foundation-catalog-v1",),
        (),
    )
    return {
        "context": context,
        "document": (
            b"id: GITVIEW-SPEC-0001\nkind: spec\nstatus: idea\ndraft_status: pre_canonical\n"
        ),
        "document_path": "specs/nodes/GITVIEW-SPEC-0001.yaml",
        "target_id": "GITVIEW-SPEC-0001",
        "decision": {"profile": PROFILE, "outcome": "approved"},
        "mapping": {"profile": PROFILE, "document_kind": "spec", "ontology_class": "sgcore:Spec"},
    }


def test_explicit_spec_class_is_not_graph_or_lifecycle_acceptance(inputs):
    result = assess_metamodel(**inputs)
    assert result["outcome"] == "analyzed"
    summary = result["summary"]
    assert summary["class_check"]["ontology_ref"] == "sgcore:Spec"
    assert summary["class_check"]["source"] == "/kind"
    assert summary["node_membership"] == summary["lifecycle"] == "not_assessed"
    assert summary["semantic_approval"] == "not_established"
    assert summary["canonical_mutations_allowed"] is False
    assert summary["decision_provenance"] == "caller_attributed_not_attested"


@pytest.mark.parametrize("field", ["decision", "mapping", "context"])
def test_missing_explicit_input_cannot_produce_analysis(inputs, field):
    inputs[field] = None
    assert assess_metamodel(**inputs)["outcome"] == "unavailable"


def test_pending_disposition_is_unavailable(inputs):
    inputs["decision"]["outcome"] = "pending"
    assert assess_metamodel(**inputs)["outcome"] == "unavailable"


@pytest.mark.parametrize(
    "document",
    [
        b"id: GITVIEW-SPEC-0001\nkind: idea\n",
        b"id: GITVIEW-SPEC-0002\nkind: spec\n",
        b"id: GITVIEW-SPEC-0001\nid: GITVIEW-SPEC-0001\nkind: spec\n",
    ],
)
def test_malformed_or_conflicting_document_is_invalid_even_when_decision_missing(inputs, document):
    inputs.update(document=document, decision=None)
    assert assess_metamodel(**inputs)["outcome"] == "invalid"


def test_wrong_mapping_and_non_normal_path_are_invalid(inputs):
    inputs["mapping"]["ontology_class"] = "sgcore:Node"
    assert assess_metamodel(**inputs)["outcome"] == "invalid"
    inputs["mapping"]["ontology_class"] = "sgcore:Spec"
    inputs["document_path"] = "../spec.yaml"
    assert assess_metamodel(**inputs)["outcome"] == "invalid"


def test_wrong_source_pin_is_invalid_before_unavailable_decision(inputs):
    context = inputs["context"]
    bad = replace(context.snapshots[0], source_sha256="0" * 64)
    inputs.update(context=replace(context, snapshots=(bad,)), decision=None)
    assert assess_metamodel(**inputs)["outcome"] == "invalid"


def test_missing_spec_class_is_invalid(inputs):
    context = inputs["context"]
    old = context.snapshots[0]
    ir = json.loads(old.ir_bytes)
    ir["classes"] = [entry for entry in ir["classes"] if entry["fqid"] != "sgcore:Spec"]
    new_ir = json.dumps(ir).encode()
    inputs["context"] = replace(
        context, snapshots=(replace(old, ir_bytes=new_ir, ir_sha256=sha(new_ir)),)
    )
    assert assess_metamodel(**inputs)["outcome"] == "invalid"
