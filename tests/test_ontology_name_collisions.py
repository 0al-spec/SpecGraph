"""Check that composition reports new cross-package name collisions."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ontology_name_collisions.py"
GRAPH = ROOT / "specs/models/review/ontology-overview/generated/ontology.graph.json"


def check(tmp_path: Path, base: dict, head: dict) -> subprocess.CompletedProcess[str]:
    before, after = tmp_path / "base.json", tmp_path / "head.json"
    before.write_text(json.dumps(base), encoding="utf-8")
    after.write_text(json.dumps(head), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(TOOL), "--base-graph", str(before), "--head-graph", str(after)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def graph() -> dict:
    def declaration(fqid: str, package: str, section: str) -> dict:
        return {
            "fqid": fqid,
            "source": {
                "id": package,
                "version": "0.3.0",
                "pointer": f"/spec/{section}/{fqid.split(':')[1]}",
            },
        }

    return {
        "schemaVersion": "ontology.diagram-projection/v1",
        "view": "full",
        "classes": [
            declaration("sgcore:Intent", "org.0al.specgraph.core", "classes"),
            declaration("sgcore:Proposal", "org.0al.specgraph.core", "classes"),
            declaration("sgproposal:Proposal", "org.0al.specgraph.intent-proposal", "classes"),
        ],
        "relations": [
            declaration("pubverify:verifiesPublishedBundle", "org.0al.publication", "relations")
        ],
        "protocols": [],
        "policies": [],
        "stateMachines": [],
    }


def test_existing_collisions_are_reported_without_blocking(tmp_path: Path, graph: dict):
    result = check(tmp_path, graph, graph)
    assert result.returncode == 0
    assert "Existing collisions (unresolved): 1" in result.stdout
    assert "New collisions: 0" in result.stdout
    assert "sgcore:Proposal" in result.stdout
    assert "sgproposal:Proposal" in result.stdout
    assert "org.0al.specgraph.core@0.3.0 /spec/classes/Proposal" in result.stdout


def test_new_class_collision_blocks_with_both_sources(tmp_path: Path, graph: dict):
    head = copy.deepcopy(graph)
    original = next(item for item in head["classes"] if item["fqid"] == "sgcore:Intent")
    extra = copy.deepcopy(original)
    extra["fqid"] = "example:Intent"
    extra["source"]["id"] = "example.package"
    head["classes"].append(extra)
    result = check(tmp_path, graph, head)
    assert result.returncode == 1
    assert "New collisions: 1" in result.stdout
    assert "sgcore:Intent" in result.stdout and "example:Intent" in result.stdout
    assert "example.package@0.3.0 /spec/classes/Intent" in result.stdout


def test_third_definition_of_existing_name_is_not_hidden(tmp_path: Path, graph: dict):
    head = copy.deepcopy(graph)
    extra = copy.deepcopy(
        next(item for item in head["classes"] if item["fqid"] == "sgcore:Proposal")
    )
    extra["fqid"] = "example:Proposal"
    extra["source"]["id"] = "example.package"
    head["classes"].append(extra)
    result = check(tmp_path, graph, head)
    assert result.returncode == 1
    assert "Existing collisions (unresolved): 1" in result.stdout
    assert "New collisions: 2" in result.stdout


def test_resolving_a_collision_or_bumping_version_does_not_create_one(tmp_path: Path, graph: dict):
    head = copy.deepcopy(graph)
    head["classes"] = [item for item in head["classes"] if item["fqid"] != "sgproposal:Proposal"]
    for item in head["classes"] + head["relations"]:
        if item["source"]["id"] == "org.0al.specgraph.core":
            item["source"]["version"] = "0.4.0"
    result = check(tmp_path, graph, head)
    assert result.returncode == 0
    assert "Resolved collisions: 1" in result.stdout
    assert "New collisions: 0" in result.stdout


def test_missing_graph_section_fails_closed(tmp_path: Path, graph: dict):
    head = copy.deepcopy(graph)
    del head["relations"]
    result = check(tmp_path, graph, head)
    assert result.returncode == 2
    assert "graph section relations must be a list" in result.stderr


def test_new_relation_collision_blocks(tmp_path: Path, graph: dict):
    head = copy.deepcopy(graph)
    original = next(
        item for item in head["relations"] if item["fqid"] == "pubverify:verifiesPublishedBundle"
    )
    extra = copy.deepcopy(original)
    extra["fqid"] = "example:verifiesPublishedBundle"
    extra["source"]["id"] = "example.package"
    head["relations"].append(extra)
    result = check(tmp_path, graph, head)
    assert result.returncode == 1
    assert "relations verifiesPublishedBundle" in result.stdout
    assert "New collisions: 1" in result.stdout


def test_current_published_graph_can_be_compared(tmp_path: Path):
    graph = json.loads(GRAPH.read_bytes())
    result = check(tmp_path, graph, graph)
    assert result.returncode == 0
    assert "New collisions: 0" in result.stdout
