"""The graph-specific invariant is a subtype of the shared foundation concept."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "ontology/packages/specgraph-core/versions"
OLD = CORE / "0.3.0/domain-ontology-package.yaml"
NEW = CORE / "0.4.0/domain-ontology-package.yaml"
IR = CORE / "0.4.0/generated/ontology.normalized.json"
GRAPH = CORE / "0.4.0/generated/ontology.graph.json"
REPORT = CORE / "0.4.0/compatibility/from-0.3.0.yaml"
FOUNDATION = ROOT / "tools/project_ontology_context/pinned_foundation"
DEFECT = ROOT / "docs/reviews/0232_project_ontology_context/graph-invariant-typescript-defect.json"

sys.path.insert(0, str(ROOT / "tools"))
from ontology_foundation_pins import PIN  # noqa: E402
from ontology_import_name_collisions import (  # noqa: E402
    foundation_packages,
    import_collisions,
    parse_package,
)


def test_graph_invariant_is_scoped_subtype_and_other_declarations_stay_unchanged():
    old = yaml.safe_load(OLD.read_bytes())
    new = yaml.safe_load(NEW.read_bytes())
    assert old["metadata"]["version"] == "0.3.0"
    assert new["metadata"]["version"] == "0.4.0"
    assert new["metadata"]["approvalStatus"] == "draft"
    old_classes = dict(old["spec"]["classes"])
    old_invariant = old_classes.pop("Invariant")
    new_classes = dict(new["spec"]["classes"])
    graph_invariant = new_classes.pop("GraphInvariant")
    assert new_classes == old_classes
    assert graph_invariant == {**old_invariant, "extends": "sg:Invariant"}
    old_relations = dict(old["spec"]["relations"])
    old_governing = old_relations.pop("invariantGovernsSpecGraph")
    new_relations = dict(new["spec"]["relations"])
    new_governing = new_relations.pop("invariantGovernsSpecGraph")
    assert new_relations == old_relations
    assert new_governing == {**old_governing, "domain": "GraphInvariant"}
    for section in ("imports", "protocols", "policies", "stateMachines"):
        assert new["spec"][section] == old["spec"][section]


def test_new_import_closure_has_no_foundation_invariant_collision():
    candidate = parse_package(str(NEW.relative_to(ROOT)), NEW.read_bytes())
    assert candidate is not None
    catalogs = foundation_packages(
        "tools/project_ontology_context/pinned_foundation/exports.json",
        PIN,
        (FOUNDATION / "exports.json").read_bytes(),
        verify_digest=True,
    )
    packages = {item.identity: item for item in [candidate, *catalogs]}
    found, missing = import_collisions(packages)
    assert not found
    assert not missing


def test_compatibility_report_exposes_breaking_identity_change():
    report = yaml.safe_load(REPORT.read_bytes())
    assert report["metadata"] == {
        "from": "org.0al.specgraph.core@0.3.0",
        "to": "org.0al.specgraph.core@0.4.0",
    }
    assert report["result"] == {
        "compatible": False,
        "requiredSpecGraphActions": ["reviewBreakingOntologyChange"],
    }
    assert set(report["changes"]["breakingChanges"]) == {
        "remove class sgcore:Invariant",
        "change relation domain sgcore:invariantGovernsSpecGraph",
    }


def test_unfixed_typescript_projection_defect_is_linked_to_existing_proposal():
    defect = json.loads(DEFECT.read_bytes())
    assert defect["status"] == "observed_open"
    assert not defect["closure"]["merged_fix"]
    assert (ROOT / defect["candidate_ref"]) == NEW
    graph = defect["graph"]
    assert (ROOT / graph["user_intent_path"]).is_file()
    assert (ROOT / graph["operator_request_path"]).is_file()
    proposal = json.loads((ROOT / graph["proposal_node_path"]).read_bytes())
    assert proposal["proposal_handle"]["handle_value"] == graph["proposal_handle"]
    assert str(DEFECT.relative_to(ROOT)) in {
        link["reference_value"] for link in proposal["proposal_artifact_link"]
    }


def test_inheritance_validation_gap_has_reproducible_graph_lineage():
    observation_path = (
        ROOT
        / "docs/reviews/0232_project_ontology_context/inheritance-validation-gap-20261109"
        / "observation.json"
    )
    observation = json.loads(observation_path.read_bytes())
    fixture = ROOT / observation["fixture_ref"]
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == observation["fixture_sha256"]
    assert (ROOT / observation["source_ref"]).is_file()
    assert observation["closure"] == {"status": "open", "merged_fix": False}
    graph = observation["graph"]
    assert (ROOT / graph["user_intent_path"]).is_file()
    assert (ROOT / graph["operator_request_path"]).is_file()
    proposal = json.loads((ROOT / graph["proposal_node_path"]).read_bytes())
    reference = str(observation_path.relative_to(ROOT))
    assert reference in {link["reference_value"] for link in proposal["proposal_artifact_link"]}
    assert reference in {link["source_reference"] for link in proposal["proposal_lineage_link"]}


def test_published_candidate_artifacts_bind_to_the_exact_source():
    ir = json.loads(IR.read_bytes())
    graph = json.loads(GRAPH.read_bytes())
    expected_digest = "sha256:" + hashlib.sha256(NEW.read_bytes()).hexdigest()
    assert ir["version"] == graph["version"] == "0.4.0"
    assert ir["sourceDigest"] == expected_digest
    assert any(source["sourceByteDigest"] == expected_digest for source in graph["sources"])
    classes = {item["fqid"]: item for item in graph["classes"]}
    assert "sgcore:Invariant" not in classes
    assert classes["sgcore:GraphInvariant"]["extends"] == "sg:Invariant"
    assert classes["sgcore:GraphInvariant"]["kind"] == "Invariant"
    relations = {item["fqid"]: item for item in graph["relations"]}
    assert relations["sgcore:invariantGovernsSpecGraph"]["domain"] == "sgcore:GraphInvariant"
    assert [
        (item["id"], item["version"], item["alias"]) for item in graph["foundationCatalogs"]
    ] == [("specgraph.foundation", "0.1.0", "sg")]


def test_released_compiler_reproduces_graph_invariant_candidate(tmp_path):
    compiler = os.environ.get("ONTOLOGYC_BINARY_PATH")
    visualizer = os.environ.get("ONTOLOGYVIZ_BINARY_PATH")
    if not compiler or not visualizer:
        pytest.skip("set ONTOLOGYC_BINARY_PATH and ONTOLOGYVIZ_BINARY_PATH")
    subprocess.run([compiler, "check", NEW], check=True, capture_output=True, timeout=60)
    subprocess.run(
        [compiler, "compile", NEW, "--target", "typescript", "--out", tmp_path / "sdk"],
        check=True,
        capture_output=True,
        timeout=60,
    )
    subprocess.run(
        [
            visualizer,
            NEW,
            "--view",
            "full",
            "--format",
            "json",
            "--foundation-model",
            FOUNDATION / "model-0.1.0.json",
            "--out",
            tmp_path / "graph",
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    report = tmp_path / "compatibility.yaml"
    subprocess.run(
        [compiler, "diff", "--from", OLD, "--to", NEW, "--out", report],
        check=True,
        capture_output=True,
        timeout=60,
    )
    assert (tmp_path / "sdk/ontology.normalized.json").read_bytes() == IR.read_bytes()
    assert (tmp_path / "graph/ontology.graph.json").read_bytes() == GRAPH.read_bytes()
    assert report.read_text().rstrip() == REPORT.read_text().rstrip()
