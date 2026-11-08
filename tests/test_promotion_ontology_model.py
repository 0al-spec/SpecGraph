"""Source, compiler and SDK checks for the draft SG-SPEC-0051 model."""

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
MODEL = ROOT / "specs/models/SG-SPEC-0051/proposal-promotion"
CORE = ROOT / "ontology/packages/specgraph-core/versions/0.3.0/domain-ontology-package.yaml"


def _document(path):
    return yaml.safe_load(path.read_bytes())


def _check_imported_proposal(candidate, core):
    selected = core["metadata"]
    assert {key: selected[key] for key in ("id", "namespace", "version")} in candidate["spec"][
        "imports"
    ]
    for reference in (
        candidate["spec"]["relations"]["promotesProposalToDraft"]["object"],
        candidate["spec"]["relations"]["proposalMotivatesSpecDraft"]["domain"],
    ):
        namespace, name = reference.split(":", 1)
        assert namespace == selected["namespace"]
        assert name == "Proposal" and name in core["spec"]["classes"]


def test_model_tracks_the_selected_spec_and_reuses_proposal():
    spec = _document(ROOT / "specs/nodes/SG-SPEC-0051.yaml")["specification"]
    model = _document(MODEL / "domain-ontology-package.yaml")
    rules = spec["promotion_rules"]
    assert {"proposal -> spec_draft", "spec_draft -> canonical_artifact"} <= set(
        rules["allowed_transitions"]
    )
    assert "intent_draft -> spec_draft" in rules["allowed_transitions"]
    assert {"proposal -> canonical_artifact", "intent_draft -> canonical_artifact"} <= set(
        rules["forbidden_transitions"]
    )
    assert rules["proposal_to_spec_draft_review"]["gate_types_allowed"] == ["review"]
    assert set(rules["spec_draft_to_canonical"]["gate_types_allowed"]) == {
        "review",
        "confirmation",
    }
    fields = model["spec"]["classes"]["TransitionRecord"]["fields"]
    required = spec["promotion_records"]["transition_record_required"]["mandatory_record_fields"]
    assert set(fields) == set(required)
    assert all(fields[name]["required"] is True for name in required)
    assert "Proposal" not in model["spec"]["classes"]
    assert model["metadata"]["approvalStatus"] == "draft"
    _check_imported_proposal(model, _document(CORE))


def test_unknown_imported_proposal_is_not_accepted_by_the_pilot_check():
    model = _document(MODEL / "domain-ontology-package.yaml")
    model["spec"]["relations"]["promotesProposalToDraft"]["object"] = "sgcore:Missing"
    with pytest.raises(AssertionError):
        _check_imported_proposal(model, _document(CORE))


@pytest.fixture(scope="module")
def compiler():
    if not (value := os.environ.get("ONTOLOGYC_BINARY_PATH")):
        pytest.skip("set ONTOLOGYC_BINARY_PATH to check the released compiler")
    return Path(value).resolve(strict=True)


def test_compiler_accepts_model_and_rejects_unknown_local_reference(compiler, tmp_path):
    source = MODEL / "domain-ontology-package.yaml"
    subprocess.run([compiler, "check", source], check=True, capture_output=True, timeout=60)
    broken = _document(source)
    broken["spec"]["classes"]["MaterializeSpecDraft"]["fields"]["ingressRecord"]["target"] = (
        "MissingRecord"
    )
    candidate = tmp_path / "broken.yaml"
    candidate.write_text(yaml.safe_dump(broken), encoding="utf-8")
    result = subprocess.run(
        [compiler, "check", candidate, "--format", "json"], capture_output=True, timeout=60
    )
    assert result.returncode == 1
    assert any(
        item["code"] == "class.field.target.unresolved" for item in json.loads(result.stdout)
    )


def test_full_projection_reuses_the_core_proposal(tmp_path):
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
    proposals = [item for item in graph["classes"] if item["fqid"] == "sgcore:Proposal"]
    assert len(proposals) == 1
    assert proposals[0]["source"]["id"] == "org.0al.specgraph.core"
    assert proposals[0]["source"]["pointer"] == "/spec/classes/Proposal"
    assert (
        proposals[0]["source"]["sourceByteDigest"]
        == "sha256:" + hashlib.sha256(CORE.read_bytes()).hexdigest()
    )
    classes = {item["fqid"]: item for item in graph["classes"]}
    relations = {item["fqid"]: item for item in graph["relations"]}
    for name, expected in (
        ("promotesProposalToDraft", ("PromoteProposalToSpecDraft", "sgcore:Proposal")),
        ("materializesSpecDraft", ("MaterializeSpecDraft", "sgpromotion:SpecDraft")),
    ):
        relation = relations[f"sgpromotion:{name}"]
        assert (relation["domain"], relation["action"], relation["range"]) == (
            "sgpromotion:PromotionActor",
            f"sgpromotion:{expected[0]}",
            expected[1],
        )
    fields = classes["sgpromotion:MaterializeSpecDraft"]["fields"]
    assert {item["id"]: item["target"] for item in fields} == {
        "ingressRecord": "sgpromotion:TransitionRecord",
        "target": "sgpromotion:CanonicalTarget",
        "transitionRecord": "sgpromotion:TransitionRecord",
    }


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
    assert output.strip() == "promotion SDK example: PASS"
