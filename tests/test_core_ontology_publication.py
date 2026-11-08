"""Published core additions keep legacy authority and source provenance explicit."""

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
PACKAGE = ROOT / "ontology/packages/specgraph-core"
OLD = PACKAGE / "domain-ontology-package.yaml"
NEW = PACKAGE / "versions/0.3.0/domain-ontology-package.yaml"
IR = PACKAGE / "versions/0.3.0/generated/ontology.normalized.json"
GRAPH = PACKAGE / "versions/0.3.0/generated/ontology.graph.json"
COMPATIBILITY = PACKAGE / "versions/0.3.0/compatibility/from-0.1.0.yaml"
sys.path.insert(0, str(ROOT / "tools"))
from project_ontology_context import foundation  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_publication_is_additive_and_keeps_old_authority_pinned():
    old = yaml.safe_load(OLD.read_bytes())
    new = yaml.safe_load(NEW.read_bytes())
    assert (old["metadata"]["version"], new["metadata"]["version"]) == ("0.1.0", "0.3.0")
    assert old["metadata"]["approvalStatus"] == new["metadata"]["approvalStatus"] == "draft"
    compatibility = yaml.safe_load(COMPATIBILITY.read_bytes())
    assert compatibility["metadata"] == {
        "from": "org.0al.specgraph.core@0.1.0",
        "to": "org.0al.specgraph.core@0.3.0",
    }
    assert compatibility["result"]["compatible"] is True
    assert compatibility["result"]["requiredSpecGraphActions"] == ["updateLockfile"]
    assert digest(OLD) == "5bfa2ff40b6174def589546ab2fea2501e1f256c4f1446f36c45c7f3fffcd929"
    old_spec, new_spec = old["spec"], new["spec"]
    for section in ("classes", "relations", "protocols", "policies", "stateMachines"):
        for name, declaration in old_spec[section].items():
            assert new_spec[section][name] == declaration
    assert set(new_spec["classes"]) - set(old_spec["classes"]) == {
        "IntentFragment",
        "IntentDraft",
        "Hypothesis",
        "Proposal",
    }
    expected = {
        "fragmentContributesToDraft": ("IntentFragment", "IntentDraft"),
        "hypothesisInformsIntentDraft": ("Hypothesis", "IntentDraft"),
        "hypothesisInformsProposal": ("Hypothesis", "Proposal"),
        "intentDraftSourceForIntent": ("IntentDraft", "Intent"),
        "intentDraftMotivatesProposal": ("IntentDraft", "Proposal"),
        "intentMotivatesProposal": ("Intent", "Proposal"),
    }
    assert set(new_spec["relations"]) - set(old_spec["relations"]) == set(expected)
    for name, (domain, target) in expected.items():
        relation = new_spec["relations"][name]
        assert (relation["domain"], relation["range"]) == (domain, target)
        assert relation["cardinality"]["min"] == 0
    assert "pre-canonical" in new_spec["classes"]["IntentDraft"]["description"]
    assert (
        "not itself grant approval"
        in new_spec["relations"]["intentDraftSourceForIntent"]["description"]
    )


def test_new_core_resolves_its_pinned_foundation_without_alias_equivalence():
    source = yaml.safe_load(NEW.read_bytes())
    checks, imports = foundation.check_import(source["spec"], source["metadata"], 1)
    assert not [row for row in checks if row.outcome in {"invalid", "unavailable"}]
    assert imports == (foundation.LEGACY_PIN,)


def test_published_graph_and_ir_have_matching_version_and_source_digest():
    ir = json.loads(IR.read_bytes())
    graph = json.loads(GRAPH.read_bytes())
    identity = ("org.0al.specgraph.core", "sgcore", "0.3.0")
    for artifact in (ir, graph):
        assert (artifact["id"], artifact["namespace"], artifact["version"]) == identity
    sha = "sha256:" + digest(NEW)
    assert ir["sourceDigest"] == sha
    assert graph["schemaVersion"] == "ontology.diagram-projection/v1"
    assert any(
        source["id"] == identity[0]
        and source["version"] == identity[2]
        and source["sourceByteDigest"] == sha
        for source in graph["sources"]
    )
    assert {c["fqid"] for c in graph["classes"]} >= {
        "sgcore:IntentFragment",
        "sgcore:IntentDraft",
        "sgcore:Hypothesis",
        "sgcore:Proposal",
    }
    assert {r["fqid"] for r in graph["relations"]} >= {
        "sgcore:fragmentContributesToDraft",
        "sgcore:intentDraftSourceForIntent",
        "sgcore:intentMotivatesProposal",
    }


def test_released_compiler_reproduces_both_public_artifacts(tmp_path):
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
        [visualizer, NEW, "--view", "full", "--format", "json", "--out", tmp_path / "graph"],
        check=True,
        capture_output=True,
        timeout=60,
    )
    assert (tmp_path / "sdk/ontology.normalized.json").read_bytes() == IR.read_bytes()
    assert (tmp_path / "graph/ontology.graph.json").read_bytes() == GRAPH.read_bytes()
    compatibility = tmp_path / "compatibility.yaml"
    subprocess.run(
        [compiler, "diff", "--from", OLD, "--to", NEW, "--out", compatibility],
        check=True,
        capture_output=True,
        timeout=60,
    )
    assert compatibility.read_text().rstrip() == COMPATIBILITY.read_text().rstrip()
