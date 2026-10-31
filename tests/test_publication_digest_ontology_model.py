"""Shared source, SDK and endpoint checks for the publication digest examples."""

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

CASES = {
    "PB-PAYLOAD": ("case.json", "manifestEntry", "payload:ManifestEntry"),
    "PB-MANIFEST": ("manifest-case.json", "localManifest", "payload:LocalManifest"),
}


@pytest.mark.parametrize("criterion_id", CASES)
def test_binding_identifies_the_canonical_criterion_and_test(criterion_id):
    filename, _, _ = CASES[criterion_id]
    source = json.loads((MODEL / filename).read_bytes())["source"]
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
        == criterion_id
    )
    assert source["statement"] == atom["statement"]
    assert source["test"] in atom["verifiable_by"]
    bindings = json.loads(
        (ROOT / "tools/feature_passports/static-publication-bindings.json").read_bytes()
    )
    assert [b["test"] for b in bindings["obligations"] if b["criterion_id"] == atom["id"]] == [
        source["test"]
    ]


@pytest.fixture(scope="module")
def compiler():
    path = os.environ.get("ONTOLOGYC_BINARY_PATH")
    if not path:
        pytest.skip("Set ONTOLOGYC_BINARY_PATH for the released compiler controls")
    return path


def test_compiler_rejects_an_unknown_comparison_target(compiler, tmp_path):
    model = yaml.safe_load((MODEL / "domain-ontology-package.yaml").read_bytes())
    model["spec"]["relations"]["comparedAgainst"]["range"]["oneOf"][1] = "LocalManifestTypo"
    broken = tmp_path / "broken.yaml"
    broken.write_text(yaml.safe_dump(model), encoding="utf-8")
    check = subprocess.run([compiler, "check", broken, "--format", "json"], capture_output=True)
    assert check.returncode == 1
    assert any(
        d["code"] == "relation.range.unresolved"
        and "LocalManifestTypo" in d["message"]
        and d["path"].startswith("spec.relations.comparedAgainst.range")
        for d in json.loads(check.stdout)
    )


@pytest.fixture(scope="module")
def compiled_models(compiler, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("publication-sdk")
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
    for name in ("model.ts", *(filename for filename, _, _ in CASES.values())):
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
    graphs = json.loads(
        subprocess.check_output(
            ["node", "-p", 'JSON.stringify(require("./js/model.js").models)'], cwd=tmp_path
        )
    )
    packages = [
        json.loads((tmp_path / "generated" / n / "ontology.normalized.json").read_bytes())
        for n in ("core", "payload")
    ]
    classes = {c["fqid"]: c for pkg in packages for c in pkg["classes"]}
    relations = {r["fqid"]: r for pkg in packages for r in pkg["relations"]}
    return graphs, classes, relations


@pytest.mark.parametrize("criterion_id", CASES)
def test_compiled_model_and_endpoints(compiled_models, criterion_id):
    graphs, classes, relations = compiled_models
    graph = graphs[criterion_id]
    filename, reference_field, reference_type = CASES[criterion_id]
    case = json.loads((MODEL / filename).read_bytes())
    source = case["source"]
    entry = case[reference_field]["path"]
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert len(nodes) == len(graph["nodes"])
    assert nodes[entry]["path"] == entry
    assert nodes[entry]["expectedSHA256"] == case[reference_field]["expectedSHA256"]
    # Both alternatives are valid in the ontology. The criterion chooses the source.
    assert nodes[entry]["$type"] == reference_type
    edges = {(e["relation"], e["from"], e["to"]) for e in graph["edges"]}
    expected = {
        ("sgcore:requirementValidatedByCriterion", source["requirement"], source["criterion"]),
        ("sgcore:testValidatesRequirement", source["test"], source["requirement"]),
    }
    for key, observation in case["observations"].items():
        assert nodes[key]["$type"] == "payload:FetchedFileObservation"
        assert nodes[key]["observedSHA256"] == observation["observedSHA256"]
        expected.add(("payload:comparedAgainst", key, entry))
        expected.add(("sgcore:evidenceSupportsCriterion", key, source["criterion"]))
    assert edges == expected and len(graph["edges"]) == len(edges)

    # Compiling an imported namespace alone does not establish its symbol membership.
    comparison = relations["payload:comparedAgainst"]
    assert comparison["cardinality"] == {"min": 1, "max": 1}
    assert set(comparison["range"]["oneOf"]) == {"payload:ManifestEntry", "payload:LocalManifest"}
    for rel, first, last in edges:
        for node, slot in ((first, "domain"), (last, "range")):
            actual = nodes[node]["$type"]
            accepted = relations[rel][slot]
            choices = accepted["oneOf"] if isinstance(accepted, dict) else [accepted]
            assert all(choice in classes for choice in choices)
            assert actual in choices or classes[actual]["extends"] in choices
