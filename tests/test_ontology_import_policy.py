from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "ontology_import" / "examcalc" / "import-fixture.yaml"


def load_ontology_imports_module() -> object:
    module_path = ROOT / "tools" / "ontology_imports.py"
    spec = importlib.util.spec_from_file_location("ontology_imports_under_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ontology_import_policy_defines_read_only_contract() -> None:
    policy = json.loads((ROOT / "tools" / "ontology_import_policy.json").read_text())

    assert policy["artifact_kind"] == "ontology_import_policy"
    assert policy["proposal_id"] == "0060"
    assert policy["derived_output_contract"]["canonical_mutations_allowed"] is False
    assert policy["derived_output_contract"]["writes_canonical_specs"] is False
    assert policy["package_ref_contract"]["semantic_source"] == (
        "ontology_normalized_ir_or_registry_materialization"
    )
    assert "local_pseudo_concepts" in policy["package_ref_contract"]["forbidden_sources"]
    assert policy["concept_ref_contract"]["unresolved_ref_action"] == "emit_ontology_gap"


def test_ontology_import_fixture_resolves_known_refs_and_gaps() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    package_index = surfaces["package_index"]
    package = package_index["packages"][0]
    assert package["package_id"] == "edu.university.examcalc"
    assert package["namespace"] == "examcalc"
    assert package["version"] == "0.1.0"
    assert package["digest"] == (
        "sha256:7cdf061c1c845e0d0d801c7d935b6d4b765db1317ec595910da2cb910eca9e2f"
    )
    assert package["lock"]["package_ref"] == "edu.university.examcalc@0.1.0"
    assert package_index["canonical_mutations_allowed"] is False

    preview = surfaces["binding_preview"]
    resolved_refs = {entry["source_ref"]: entry for entry in preview["resolved_refs"]}
    assert sorted(resolved_refs) == ["examcalc:Exam", "examcalc:requires_policy"]
    assert resolved_refs["examcalc:Exam"]["kind"] == "class"
    assert resolved_refs["examcalc:requires_policy"]["kind"] == "relation"
    assert preview["unresolved_refs"] == ["examcalc:CASFunction"]
    assert preview["canonical_mutations_allowed"] is False

    gap_index = surfaces["gap_index"]
    assert gap_index["artifact_kind"] == "ontology_import_gap_index"
    assert gap_index["canonical_mutations_allowed"] is False
    assert gap_index["summary"] == {
        "gap_count": 1,
        "next_gap": "review_ontology_import_gap",
    }
    assert gap_index["gaps"][0]["missing_concept"] == {
        "ref": "examcalc:CASFunction",
        "namespace_hint": "examcalc",
        "concept_hint": "CASFunction",
    }
    assert gap_index["gaps"][0]["recommended_route"] == "ontology_package_draft"


def test_ontology_import_governance_and_prompt_surfaces_are_derived() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    governance = surfaces["governance_evidence_index"]
    assert governance["artifact_kind"] == "ontology_governance_evidence_index"
    assert governance["canonical_mutations_allowed"] is False
    assert governance["evidence"][0]["decision_ref"].startswith(
        "ontology-governance://edu.university.examcalc/0.1.0/"
    )
    assert governance["summary"]["next_gap"] == "none"

    prompt = surfaces["prompt_invocation_index"]
    assert prompt["artifact_kind"] == "ontology_prompt_invocation_index"
    assert prompt["canonical_mutations_allowed"] is False
    assert prompt["invocations"] == []
    assert prompt["summary"] == {
        "invocation_count": 0,
        "status": "not_invoked",
        "next_gap": "none",
    }


def test_make_ontology_imports_writes_declared_surfaces() -> None:
    subprocess.run(
        ["make", "ontology-imports", f"PYTHON={sys.executable}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )

    expected = {
        "runs/ontology_package_index.json": "ontology_package_index",
        "runs/ontology_import_gap_index.json": "ontology_import_gap_index",
        "runs/ontology_governance_evidence_index.json": "ontology_governance_evidence_index",
        "runs/ontology_binding_preview.json": "ontology_binding_preview",
        "runs/ontology_prompt_invocation_index.json": "ontology_prompt_invocation_index",
    }
    for relative_path, artifact_kind in expected.items():
        payload = json.loads((ROOT / relative_path).read_text())
        assert payload["artifact_kind"] == artifact_kind
        assert payload["proposal_id"] == "0060"
        assert payload["canonical_mutations_allowed"] is False


def test_proposal_0060_runtime_registry_tracks_slice() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0060"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert ("tools/ontology_imports.py", "def build_ontology_import_surfaces(") in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_import_fixture_resolves_known_refs_and_gaps(",
    ) in validation_markers
    assert ("Makefile", "ontology-imports:") in observation_markers
