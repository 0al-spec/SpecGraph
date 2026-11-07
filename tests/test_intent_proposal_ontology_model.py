"""Source and SDK controls for the draft SG-SPEC-0053 action interpretation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "specs/models/SG-SPEC-0053/intent-to-proposal"
CORE = ROOT / "ontology/packages/specgraph-core/domain-ontology-package.yaml"


def _document(path):
    return yaml.safe_load(path.read_bytes())


def _check_core_endpoints(candidate, core):
    """Check this pilot's selected import and relation endpoints against its source."""
    selected = core["metadata"]
    assert {k: selected[k] for k in ("id", "namespace", "version")} in candidate["spec"]["imports"]
    rels = candidate["spec"]["relations"]
    for reference in (
        rels["interpretsIntentForProposal"]["object"],
        rels["proposalOperationalizesIntent"]["range"],
    ):
        namespace, name = reference.split(":", 1)
        assert namespace == selected["namespace"]
        assert name in core["spec"]["classes"]
        assert name == "Intent"


def test_model_tracks_the_selected_spec_and_existing_intent():
    spec = _document(ROOT / "specs/nodes/SG-SPEC-0053.yaml")
    model = _document(MODEL / "domain-ontology-package.yaml")
    assert spec["id"] == "SG-SPEC-0053"
    assert (
        "operationalizes one or more intents"
        in spec["specification"]["kind_roles"]["proposal"]["role"]
    )
    assert model["metadata"]["approvalStatus"] == "draft"
    _check_core_endpoints(model, _document(CORE))


def test_unknown_imported_intent_is_not_accepted_by_the_pilot_check():
    model = _document(MODEL / "domain-ontology-package.yaml")
    model["spec"]["relations"]["interpretsIntentForProposal"]["object"] = "sgcore:MissingIntent"
    with pytest.raises(AssertionError):
        _check_core_endpoints(model, _document(CORE))


@pytest.fixture(scope="module")
def compiler():
    if not (value := os.environ.get("ONTOLOGYC_BINARY_PATH")):
        pytest.skip("set ONTOLOGYC_BINARY_PATH to check the real compiler")
    return Path(value).resolve(strict=True)


def test_compiler_accepts_model_and_rejects_wrong_local_reference(compiler, tmp_path):
    source = MODEL / "domain-ontology-package.yaml"
    subprocess.run([compiler, "check", source], check=True, capture_output=True, timeout=60)
    broken = _document(source)
    broken["spec"]["classes"]["InterpretIntentForProposal"]["fields"]["candidateProposal"][
        "target"
    ] = "MissingProposal"
    candidate = tmp_path / "broken.yaml"
    candidate.write_text(yaml.safe_dump(broken), encoding="utf-8")
    result = subprocess.run(
        [compiler, "check", candidate, "--format", "json"], capture_output=True, timeout=60
    )
    assert result.returncode == 1
    assert any(d["code"] == "class.field.target.unresolved" for d in json.loads(result.stdout))


def test_full_projection_reuses_exact_core_source(tmp_path):
    if not (value := os.environ.get("ONTOLOGYVIZ_BINARY_PATH")):
        pytest.skip("set ONTOLOGYVIZ_BINARY_PATH to check the released graph export")
    subprocess.run(
        [
            value,
            MODEL / "domain-ontology-package.yaml",
            "--view",
            "full",
            "--import",
            CORE,
            "--format",
            "json",
            "--out",
            tmp_path,
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    graph = json.loads((tmp_path / "ontology.graph.json").read_bytes())
    classes = {c["fqid"]: c for c in graph["classes"]}
    relations = {r["fqid"]: r for r in graph["relations"]}
    imported = classes["sgcore:Intent"]
    assert imported["source"]["id"] == "org.0al.specgraph.core"
    assert imported["source"]["pointer"] == "/spec/classes/Intent"
    assert (
        imported["source"]["sourceByteDigest"]
        == "sha256:" + hashlib.sha256(CORE.read_bytes()).hexdigest()
    )
    action = classes["sgproposal:InterpretIntentForProposal"]
    assert action["kind"] == "Action"
    assert action["fields"][0]["target"] == "sgproposal:Proposal"
    relationship = relations["sgproposal:interpretsIntentForProposal"]
    assert (relationship["domain"], relationship["action"], relationship["range"]) == (
        "sgproposal:ProposalAuthor",
        "sgproposal:InterpretIntentForProposal",
        "sgcore:Intent",
    )


def test_generated_sdk_example(compiler, tmp_path):
    if not (value := os.environ.get("TYPESCRIPT_TSC_PATH")):
        pytest.skip("set TYPESCRIPT_TSC_PATH to exercise the generated SDK")
    tsc = Path(value).resolve(strict=True)
    node_modules = tsc.parent.parent.parent
    if not (node_modules / "zod/package.json").is_file():
        pytest.fail("the selected TypeScript toolchain must also contain zod@4")
    (tmp_path / "node_modules").symlink_to(node_modules, target_is_directory=True)
    subprocess.run(
        [
            compiler,
            "compile",
            MODEL / "domain-ontology-package.yaml",
            "--target",
            "typescript",
            "--out",
            tmp_path / "generated",
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    shutil.copyfile(MODEL / "sdk-example.ts", tmp_path / "sdk-example.ts")
    subprocess.run(
        [
            "node",
            tsc,
            "--strict",
            "--target",
            "ES2022",
            "--module",
            "Node16",
            "--esModuleInterop",
            "--skipLibCheck",
            "--outDir",
            "js",
            "sdk-example.ts",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        timeout=60,
    )
    output = subprocess.check_output(
        ["node", "js/sdk-example.js"], cwd=tmp_path, text=True, timeout=60
    )
    assert output.strip() == "intent-proposal SDK example: PASS"
