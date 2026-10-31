"""Source and SDK checks for the single PB-PAYLOAD authoring example."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "specs/models/SG-SPEC-0071"
CORE = ROOT / "ontology/packages/specgraph-core"
sys.path.insert(0, str(ROOT / "tools"))
from local_ontology_pilot import pointer  # noqa: E402


def test_pb_payload_binding_identifies_the_canonical_criterion_and_test():
    source = json.loads((MODEL / "case.json").read_bytes())["source"]
    raw = (ROOT / "specs/nodes/SG-SPEC-0071.yaml").read_bytes()
    spec = yaml.safe_load(raw)
    assert source["sha256"] == hashlib.sha256(raw).hexdigest()
    assert source["spec"] == spec["id"] == "SG-SPEC-0071"
    assert source["requirement"] == spec["specification"]["requirement"]["id"]
    criterion = pointer(spec, source["criterionPointer"])
    atom = pointer(spec, source["atomPointer"])
    assert (
        source["criterion"]
        == criterion["id"]
        == criterion["intent_atom_id"]
        == atom["id"]
        == "PB-PAYLOAD"
    )
    assert source["statement"] == atom["statement"]
    assert source["test"] in atom["verifiable_by"]
    bindings = json.loads(
        (ROOT / "tools/feature_passports/static-publication-bindings.json").read_bytes()
    )
    assert [b["test"] for b in bindings["obligations"] if b["criterion_id"] == atom["id"]] == [
        source["test"]
    ]


@pytest.fixture
def compiler():
    path = os.environ.get("ONTOLOGYC_BINARY_PATH")
    if not path:
        pytest.skip("Set ONTOLOGYC_BINARY_PATH for the released compiler controls")
    return path


def test_pb_payload_compiler_rejects_an_unknown_comparison_target(compiler, tmp_path):
    model = yaml.safe_load((MODEL / "domain-ontology-package.yaml").read_bytes())
    model["spec"]["relations"]["comparedAgainst"]["range"] = "ManifestEntyr"
    broken = tmp_path / "broken.yaml"
    broken.write_text(yaml.safe_dump(model), encoding="utf-8")
    check = subprocess.run([compiler, "check", broken, "--format", "json"], capture_output=True)
    assert check.returncode == 1
    assert any(
        d["code"] == "relation.range.unresolved"
        and d["path"] == "spec.relations.comparedAgainst.range"
        for d in json.loads(check.stdout)
    )


def test_pb_payload_compiled_model_and_endpoints(compiler, tmp_path):
    tsc = os.environ.get("TYPESCRIPT_TSC_PATH")
    if not tsc:
        pytest.skip("Set TYPESCRIPT_TSC_PATH to run the SDK control")
    for name, folder in (("core", CORE), ("payload", MODEL)):
        subprocess.run(
            [
                compiler,
                "compile",
                folder / "domain-ontology-package.yaml",
                "--target",
                "typescript",
                "--out",
                tmp_path / "generated" / name,
            ],
            check=True,
        )
    for name in ("model.ts", "case.json"):
        shutil.copyfile(MODEL / name, tmp_path / name)
    subprocess.run(
        [
            "node",
            tsc,
            "--strict",
            "--target",
            "ES2022",
            "--module",
            "Node16",
            "--resolveJsonModule",
            "--outDir",
            "js",
            "model.ts",
        ],
        cwd=tmp_path,
        check=True,
    )
    graph = json.loads(
        subprocess.check_output(
            ["node", "-p", 'JSON.stringify(require("./js/model.js").model)'], cwd=tmp_path
        )
    )
    case = json.loads((MODEL / "case.json").read_bytes())
    source = case["source"]
    entry = case["manifestEntry"]["path"]
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert len(nodes) == len(graph["nodes"])
    assert nodes[entry]["path"] == entry
    assert nodes[entry]["expectedSHA256"] == case["manifestEntry"]["expectedSHA256"]
    edges = {(e["relation"], e["from"], e["to"]) for e in graph["edges"]}
    expected = {
        ("sgcore:requirementValidatedByCriterion", source["requirement"], source["criterion"]),
        ("sgcore:testValidatesRequirement", source["test"], source["requirement"]),
    }
    for key, observation in case["observations"].items():
        assert nodes[key]["observedSHA256"] == observation["observedSHA256"]
        expected.add(("payload:comparedAgainst", key, entry))
        expected.add(("sgcore:evidenceSupportsCriterion", key, source["criterion"]))
    assert edges == expected and len(graph["edges"]) == len(edges)

    # Compiling an imported namespace alone does not establish its symbol membership.
    packages = [
        json.loads((tmp_path / "generated" / n / "ontology.normalized.json").read_bytes())
        for n in ("core", "payload")
    ]
    classes = {c["fqid"]: c for pkg in packages for c in pkg["classes"]}
    relations = {r["fqid"]: r for pkg in packages for r in pkg["relations"]}
    assert relations["payload:comparedAgainst"]["cardinality"] == {"min": 1, "max": 1}
    for rel, first, last in edges:
        for node, slot in ((first, "domain"), (last, "range")):
            actual = nodes[node]["$type"]
            accepted = relations[rel][slot]
            assert accepted in classes
            assert actual == accepted or classes[actual]["extends"] == accepted
