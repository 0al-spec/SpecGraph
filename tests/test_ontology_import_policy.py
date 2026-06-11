from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

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


def load_fixture_payload() -> dict[str, object]:
    payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def write_temp_policy(tmp_path: Path, payload: dict[str, object] | None = None) -> Path:
    policy = payload or json.loads((ROOT / "tools" / "ontology_import_policy.json").read_text())
    policy_path = tmp_path / "ontology_import_policy.json"
    policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True), encoding="utf-8")
    return policy_path


def write_temp_fixture(tmp_path: Path, payload: dict[str, object]) -> Path:
    fixture_dir = tmp_path / "tests" / "fixtures" / "ontology_import" / "examcalc"
    fixture_dir.mkdir(parents=True)
    source_ir = (
        ROOT / "tests" / "fixtures" / "ontology_import" / "examcalc" / "ontology.normalized.json"
    )
    (fixture_dir / "ontology.normalized.json").write_text(
        source_ir.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    fixture_path = fixture_dir / "import-fixture.yaml"
    fixture_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return fixture_path


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
    assert package_index["tracked_artifacts_written"] is False

    preview = surfaces["binding_preview"]
    resolved_refs = {entry["source_ref"]: entry for entry in preview["resolved_refs"]}
    assert sorted(resolved_refs) == ["examcalc:Exam", "examcalc:requires_policy"]
    assert resolved_refs["examcalc:Exam"]["kind"] == "class"
    assert resolved_refs["examcalc:requires_policy"]["kind"] == "relation"
    assert preview["unresolved_refs"] == ["examcalc:CASFunction"]
    assert preview["canonical_mutations_allowed"] is False
    assert preview["tracked_artifacts_written"] is False

    gap_index = surfaces["gap_index"]
    assert gap_index["artifact_kind"] == "ontology_import_gap_index"
    assert gap_index["canonical_mutations_allowed"] is False
    assert gap_index["tracked_artifacts_written"] is False
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
    assert governance["tracked_artifacts_written"] is False
    evidence = governance["evidence"][0]
    assert evidence["decision_ref"].startswith(
        "ontology-governance://edu.university.examcalc/0.1.0/"
    )
    assert evidence["repeatability_report_ref"].startswith(
        "Ontology:SPECS/ontology/golden-intents/"
    )
    assert evidence["trusted_registry_gate_ref"] == (
        "Ontology:SPECS/ontology/governance-protocol.md#trusted-registry-publication"
    )
    assert governance["summary"] == {
        "evidence_count": 1,
        "next_gap": "none",
    }

    prompt = surfaces["prompt_invocation_index"]
    assert prompt["artifact_kind"] == "ontology_prompt_invocation_index"
    assert prompt["canonical_mutations_allowed"] is False
    assert prompt["tracked_artifacts_written"] is False
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
        assert payload["tracked_artifacts_written"] is False


def test_ontology_import_fixture_validation_rejects_missing_subject(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture = load_fixture_payload()
    assert isinstance(fixture["binding"], dict)
    del fixture["binding"]["subject"]

    fixture_path = write_temp_fixture(tmp_path, fixture)
    policy_path = write_temp_policy(tmp_path)

    with pytest.raises(ValueError, match=r"fixture\.binding\.subject must be an object"):
        module.build_ontology_import_surfaces(fixture_path, policy_path=policy_path)


def test_ontology_import_fixture_validation_rejects_malformed_refs(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture = load_fixture_payload()
    assert isinstance(fixture["binding"], dict)
    fixture["binding"]["refs"] = ["examcalc"]

    fixture_path = write_temp_fixture(tmp_path, fixture)
    policy_path = write_temp_policy(tmp_path)

    with pytest.raises(ValueError, match="<namespace>:<symbol>"):
        module.build_ontology_import_surfaces(fixture_path, policy_path=policy_path)


def test_ontology_import_rejects_materialized_ir_outside_fixture_dir(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture = load_fixture_payload()
    assert isinstance(fixture["package"], dict)
    fixture["package"]["materialized_ir"] = "../ontology.normalized.json"

    fixture_path = write_temp_fixture(tmp_path, fixture)
    policy_path = write_temp_policy(tmp_path)

    with pytest.raises(ValueError, match="fixture directory"):
        module.build_ontology_import_surfaces(fixture_path, policy_path=policy_path)


def test_ontology_import_rejects_ir_metadata_mismatch(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    ir_path = fixture_path.parent / "ontology.normalized.json"
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    ir["sourceDigest"] = "sha256:mismatch"
    ir_path.write_text(json.dumps(ir, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="sourceDigest"):
        module.build_ontology_import_surfaces(fixture_path, policy_path=policy_path)


def test_ontology_import_missing_governance_emits_evidence_gap(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture = load_fixture_payload()
    assert isinstance(fixture["package"], dict)
    del fixture["package"]["governance"]
    fixture_path = write_temp_fixture(tmp_path, fixture)
    policy_path = write_temp_policy(tmp_path)

    surfaces = module.build_ontology_import_surfaces(fixture_path, policy_path=policy_path)

    governance = surfaces["governance_evidence_index"]
    assert governance["evidence"] == []
    assert governance["summary"] == {
        "evidence_count": 0,
        "next_gap": "attach_ontology_governance_evidence",
    }


def test_ontology_import_write_rejects_outputs_outside_allowed_roots(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    policy = json.loads((ROOT / "tools" / "ontology_import_policy.json").read_text())
    policy["repository_layout"]["package_index"] = "specs/nodes/ontology_package_index.json"
    policy_path = write_temp_policy(tmp_path, policy)

    with pytest.raises(ValueError, match="outside allowed output roots"):
        module.write_ontology_import_surfaces(
            surfaces,
            policy_path=policy_path,
            out_dir=tmp_path,
        )


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
