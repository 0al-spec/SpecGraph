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
CORE = ROOT / "ontology/packages/specgraph-core/versions/0.4.0/domain-ontology-package.yaml"
INTENT = (
    ROOT
    / "specs/models/SG-SPEC-0053/intent-to-proposal"
    / "versions/0.5.0-draft.1/domain-ontology-package.yaml"
)
PROMOTION = (
    ROOT
    / "specs/models/SG-SPEC-0051/proposal-promotion"
    / "versions/0.4.0-draft.1/domain-ontology-package.yaml"
)
PUBLICATION = ROOT / "specs/models/SG-SPEC-0071/verification-action/domain-ontology-package.yaml"
SECTIONS = ("classes", "relations", "protocols", "policies", "stateMachines")
FOUNDATION = ROOT / "tools/project_ontology_context/pinned_foundation"
FOUNDATION_MODELS = {
    "0.1.0": "7999a4ce110535c8093f177493532420a04ab7db9ff86492db802580531d7e48",
    "0.2.0": "2f43dbd772c8356de107e3ea48cd548405023edb6a641702ddbec52c4942033b",
}


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
    assert {(REVIEW / path).resolve() for path in profile["foundationModels"]} == {
        FOUNDATION / f"model-{version}.json" for version in FOUNDATION_MODELS
    }
    for version, expected in FOUNDATION_MODELS.items():
        actual = hashlib.sha256((FOUNDATION / f"model-{version}.json").read_bytes()).hexdigest()
        assert actual == expected

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


def test_migrated_draft_packages_only_change_identity_and_core_pin():
    for old_path, new_path in (
        (
            ROOT / "specs/models/SG-SPEC-0053/intent-to-proposal/domain-ontology-package.yaml",
            INTENT,
        ),
        (
            ROOT / "specs/models/SG-SPEC-0051/proposal-promotion/domain-ontology-package.yaml",
            PROMOTION,
        ),
    ):
        old = _document(old_path)
        new = _document(new_path)
        for key in ("id", "namespace", "publisher", "approvalStatus"):
            assert new["metadata"][key] == old["metadata"][key]
        assert new["metadata"]["version"] != old["metadata"]["version"]
        assert new["metadata"]["source"] == new_path.relative_to(ROOT).as_posix()
        new_imports = new["spec"].pop("imports")
        old_imports = old["spec"].pop("imports")
        assert new["spec"] == old["spec"]
        assert [
            {**item, "version": "0.4.0"} if item["id"] == "org.0al.specgraph.core" else item
            for item in old_imports
        ] == new_imports


def test_review_projection_selects_the_graph_specific_invariant():
    graph = json.loads((REVIEW / "generated/ontology.graph.json").read_bytes())
    classes = {item["fqid"]: item for item in graph["classes"]}
    assert "sgcore:Invariant" not in classes
    assert classes["sgcore:GraphInvariant"]["extends"] == "sg:Invariant"
    assert classes["sgcore:GraphInvariant"]["kind"] == "Invariant"
    relations = {item["fqid"]: item for item in graph["relations"]}
    assert relations["sgcore:invariantGovernsSpecGraph"]["domain"] == "sgcore:GraphInvariant"


@pytest.mark.parametrize("package", [INTENT, PROMOTION])
def test_migrated_packages_check_and_compile_against_exact_new_core(package, tmp_path):
    if not (compiler := os.environ.get("ONTOLOGYC_BINARY_PATH")):
        pytest.skip("set ONTOLOGYC_BINARY_PATH to check the released compiler")
    subprocess.run(
        [compiler, "check", package, "--import", CORE],
        check=True,
        capture_output=True,
        timeout=60,
    )
    subprocess.run(
        [
            compiler,
            "compile",
            package,
            "--import",
            CORE,
            "--target",
            "typescript",
            "--out",
            tmp_path,
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    ir = json.loads((tmp_path / "ontology.normalized.json").read_bytes())
    assert {
        "id": "org.0al.specgraph.core",
        "namespace": "sgcore",
        "version": "0.4.0",
    } in ir["imports"]


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
    catalogs = {
        (item["id"], item["version"], item["alias"]): item
        for item in combined["foundationCatalogs"]
    }
    assert set(catalogs) == {
        ("ontology.foundation", "0.2.0", "ont"),
        ("specgraph.foundation", "0.1.0", "sg"),
    }
    for (_, version, _), item in catalogs.items():
        assert item["catalogByteDigest"] == "sha256:" + FOUNDATION_MODELS[version]
        assert item["catalog"]["classes"]["DomainEntity"]["declaration"]

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
