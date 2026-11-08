"""Guard the source-bound, non-canonical ontology review selection."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml
from tools.ontology_name_collisions import collisions

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "specs/models/review/ontology-overview"
PROFILE = REVIEW / "ontology.profile.json"
PACKAGE = REVIEW / "domain-ontology-package.yaml"
CORE = ROOT / "ontology/packages/specgraph-core/versions/0.3.0/domain-ontology-package.yaml"
INTENT = ROOT / "specs/models/SG-SPEC-0053/intent-to-proposal/domain-ontology-package.yaml"
PROMOTION = ROOT / "specs/models/SG-SPEC-0051/proposal-promotion/domain-ontology-package.yaml"
PUBLICATION = ROOT / "specs/models/SG-SPEC-0071/verification-action/domain-ontology-package.yaml"
SECTIONS = ("classes", "relations", "protocols", "policies", "stateMachines")


def _document(path: Path):
    return yaml.safe_load(path.read_bytes())


def test_profile_selects_the_four_real_packages_as_review_sources():
    profile = json.loads(PROFILE.read_bytes())
    assert profile["schemaVersion"] == 1
    assert profile["view"] == "full"
    assert (REVIEW / profile["package"]).resolve() == PACKAGE
    assert {(REVIEW / path).resolve() for path in profile["imports"]} == {
        CORE,
        INTENT,
        PROMOTION,
        PUBLICATION,
    }

    review = _document(PACKAGE)
    assert review["metadata"]["approvalStatus"] == "draft"
    assert set(review["spec"]["classes"]) == {"ReviewScope", "SelectedPackage"}
    assert set(review["spec"]["relations"]) == {"scopeIncludesPackage"}
    relation = review["spec"]["relations"]["scopeIncludesPackage"]
    assert (relation["domain"], relation["range"]) == ("ReviewScope", "SelectedPackage")
    imports = {item["id"]: item for item in review["spec"]["imports"]}
    for path in (CORE, INTENT, PROMOTION, PUBLICATION):
        metadata = _document(path)["metadata"]
        assert imports[metadata["id"]] == {
            key: metadata[key] for key in ("id", "namespace", "version")
        }
    for path in (INTENT, PROMOTION, PUBLICATION):
        assert _document(path)["metadata"]["approvalStatus"] == "draft"


def _export(viz: str, out: Path, *arguments: str | Path) -> dict:
    subprocess.run(
        [viz, *map(str, arguments), "--format", "json", "--out", str(out)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return json.loads((out / "ontology.graph.json").read_bytes())


def _records(graph: dict, section: str) -> dict[tuple[str, str], dict]:
    records = {}
    for record in graph[section]:
        key = (record["source"]["id"], record["source"]["pointer"])
        assert key not in records
        # The visualizer marks imported declarations and qualifies imported relation ids.
        normalized = {k: v for k, v in record.items() if k != "diagramOrigin"}
        if section == "relations":
            normalized["id"] = normalized["fqid"].split(":", 1)[1]
        records[key] = normalized
    return records


def test_real_projection_preserves_sources_and_existing_declarations(tmp_path):
    if not (viz := os.environ.get("ONTOLOGYVIZ_BINARY_PATH")):
        pytest.skip("set ONTOLOGYVIZ_BINARY_PATH to check the real graph export")

    combined = _export(viz, tmp_path / "combined", "--profile", PROFILE)
    repeated = _export(viz, tmp_path / "repeated", "--profile", PROFILE)
    assert combined == repeated
    assert (
        (tmp_path / "combined/ontology.graph.json").read_bytes()
        == (tmp_path / "repeated/ontology.graph.json").read_bytes()
        == (REVIEW / "generated/ontology.graph.json").read_bytes()
    )
    assert sum(bool(relation.get("action")) for relation in combined["relations"]) == 5
    assert not collisions(combined)

    sources = {source["id"]: source for source in combined["sources"]}
    expected_paths = (PACKAGE, CORE, INTENT, PROMOTION, PUBLICATION)
    assert len(sources) == len(expected_paths)
    for path in expected_paths:
        metadata = _document(path)["metadata"]
        source = sources[metadata["id"]]
        assert (source["namespace"], source["version"]) == (
            metadata["namespace"],
            metadata["version"],
        )
        expected_digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        assert source["sourceByteDigest"] == expected_digest

    intent = _export(viz, tmp_path / "intent", INTENT, "--view", "full", "--import", CORE)
    promotion = _export(
        viz,
        tmp_path / "promotion",
        PROMOTION,
        "--view",
        "full",
        "--import",
        CORE,
    )
    publication = _export(viz, tmp_path / "publication", PUBLICATION, "--view", "full")
    review_id = _document(PACKAGE)["metadata"]["id"]
    for section in SECTIONS:
        expected = {}
        for graph in (intent, promotion, publication):
            for key, record in _records(graph, section).items():
                if key in expected:
                    assert expected[key] == record
                expected[key] = record
        actual = {
            key: record
            for key, record in _records(combined, section).items()
            if key[0] != review_id
        }
        assert actual == expected

    relations = {record["fqid"]: record for record in combined["relations"]}
    assert (
        relations["sgcore:intentMotivatesProposal"]["domain"],
        relations["sgcore:intentMotivatesProposal"]["range"],
    ) == ("sgcore:Intent", "sgcore:Proposal")
    assert relations["sgpromotion:promotesProposalToDraft"]["range"] == "sgcore:Proposal"
    assert (
        relations["pubverify:verifiesPublishedBundle"]["action"]
        == "pubverify:VerifyPublishedBundle"
    )
