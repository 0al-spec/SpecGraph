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
ADAPTER_REPORT = (
    ROOT / "tests" / "fixtures" / "ontology_import" / "examcalc" / "ontologyc-adapter-report.yaml"
)


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


def load_adapter_report_payload() -> dict[str, object]:
    payload = yaml.safe_load(ADAPTER_REPORT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def write_temp_policy(tmp_path: Path, payload: dict[str, object] | None = None) -> Path:
    policy = payload or json.loads((ROOT / "tools" / "ontology_import_policy.json").read_text())
    policy_path = tmp_path / "ontology_import_policy.json"
    policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True), encoding="utf-8")
    return policy_path


def write_temp_semantic_control_policy(
    tmp_path: Path, payload: dict[str, object] | None = None
) -> Path:
    policy = payload or json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    policy_dir = tmp_path / "tools"
    policy_dir.mkdir(parents=True, exist_ok=True)
    policy_path = policy_dir / "ontology_semantic_control_policy.json"
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


def write_temp_adapter_report(tmp_path: Path, payload: dict[str, object]) -> Path:
    fixture_dir = tmp_path / "tests" / "fixtures" / "ontology_import" / "examcalc"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    source_dir = ROOT / "tests" / "fixtures" / "ontology_import" / "examcalc"
    for relative in (
        "ontologyc/concept-refs.yaml",
        "ontologyc/ontology.lock.yaml",
        "ontologyc/ontology-gaps.yaml",
    ):
        target = fixture_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((source_dir / relative).read_text(encoding="utf-8"), encoding="utf-8")
    report_path = fixture_dir / "ontologyc-adapter-report.yaml"
    report_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return report_path


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
    contract = policy["ontologyc_adapter_report_contract"]
    assert contract["accepted_tool"] == "ontologyc"
    assert contract["accepted_command"] == "validate-specgraph"
    assert contract["digest_validation"] == ("package.digest_must_match_normalized_ir_sourceDigest")
    assert contract["ontology_lock_output_authority"] == "non_canonical_report_artifact"
    assert "canonical_spec_mutation" in contract["forbidden_effects"]


def test_ontology_semantic_control_policy_defines_review_only_contract() -> None:
    policy = json.loads((ROOT / "tools" / "ontology_semantic_control_policy.json").read_text())

    assert policy["artifact_kind"] == "ontology_semantic_control_policy"
    assert policy["proposal_id"] == "0103"
    assert policy["policy_basis"] == "docs/proposals/0100_ontology_grounded_semantic_control.md"
    assert policy["derived_output_contract"]["canonical_mutations_allowed"] is False
    assert policy["derived_output_contract"]["tracked_artifacts_written"] is False
    assert policy["repository_layout"]["semantic_lint_smoke"] == (
        "runs/ontology_semantic_lint_smoke.json"
    )
    assert policy["repository_layout"]["semantic_context_pack"] == (
        "runs/ontology_semantic_context_pack.json"
    )
    context_contract = policy["semantic_context_pack_contract"]
    assert context_contract["artifact_kind"] == "ontology_semantic_context_pack"
    assert context_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0104",
    }
    assert context_contract["consumer_boundary"]["for_prompt_agent_input"] is True
    assert context_contract["consumer_boundary"]["for_specspace_review_surface"] is True
    assert context_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert context_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    contract = policy["semantic_lint_contract"]
    assert contract["smoke_artifact_kind"] == "ontology_semantic_lint_smoke"
    assert {
        "accepted_term",
        "accepted_alias",
        "unknown_term",
        "deprecated_term",
        "relation_conflict",
    }.issubset(set(contract["term_classifications"]))
    boundary = policy["authority_boundary"]
    assert boundary["smoke_report_is_authority"] is False
    assert boundary["ontology_delta_candidate_is_authority"] is False
    assert boundary["prompt_agent_execution_allowed"] is False
    assert boundary["automatic_canonical_node_update"] is False


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


def test_ontology_semantic_lint_smoke_classifies_terms() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(
        FIXTURE,
        adapter_report_path=ADAPTER_REPORT,
    )

    smoke = surfaces["semantic_lint_smoke"]
    assert smoke["artifact_kind"] == "ontology_semantic_lint_smoke"
    assert smoke["proposal_id"] == "0103"
    assert smoke["canonical_mutations_allowed"] is False
    assert smoke["tracked_artifacts_written"] is False
    assert smoke["source_surfaces"] == {
        "ontology_binding_preview": "runs/ontology_binding_preview.json",
        "ontology_governance_evidence_index": "runs/ontology_governance_evidence_index.json",
        "ontology_import_gap_index": "runs/ontology_import_gap_index.json",
        "ontology_package_index": "runs/ontology_package_index.json",
    }
    assert smoke["summary"] == {
        "status": "blocked_relation_conflict",
        "term_count": 5,
        "classification_counts": {
            "accepted_alias": 1,
            "accepted_term": 1,
            "deprecated_term": 1,
            "relation_conflict": 1,
            "unknown_term": 1,
        },
        "review_required_count": 1,
        "blocking_count": 2,
        "next_gap": "review_ontology_relation_conflict",
    }

    by_term = {entry["term"]: entry for entry in smoke["term_results"]}
    assert by_term["Exam"]["classification"] == "accepted_term"
    assert by_term["Exam"]["status"] == "grounded"
    assert by_term["Exam"]["concept_ref"]["source_ref"] == "examcalc:Exam"

    assert by_term["requires policy"]["classification"] == "accepted_alias"
    assert by_term["requires policy"]["status"] == "grounded_with_aliases"
    assert by_term["requires policy"]["alias_of"] == "examcalc:requires_policy"
    assert by_term["requires policy"]["suggested_action"] == "prefer_accepted_term"

    assert by_term["CASFunction"]["classification"] == "unknown_term"
    assert by_term["CASFunction"]["status"] == "review_required_unknown_terms"
    assert by_term["CASFunction"]["gap"]["gap_id"] == "ontology-gap-examcalc-casfunction"
    assert by_term["CASFunction"]["suggested_action"] == "emit_ontology_gap"

    assert by_term["ExamPolicy"]["classification"] == "deprecated_term"
    assert by_term["ExamPolicy"]["status"] == "blocked_deprecated_terms"
    assert by_term["ExamPolicy"]["replacement_ref"] == "examcalc:ExamPolicyProfile"
    assert by_term["ExamPolicy"]["suggested_action"] == "replace_with_accepted_term"

    assert by_term["allows policy"]["classification"] == "relation_conflict"
    assert by_term["allows policy"]["status"] == "blocked_relation_conflict"
    assert by_term["allows policy"]["accepted_relation_ref"] == "examcalc:requires_policy"
    assert by_term["allows policy"]["suggested_action"] == "use_accepted_relation"

    boundary = smoke["authority_boundary"]
    assert boundary["lint_report_is_authority"] is False
    assert boundary["canonical_mutations_allowed"] is False


def test_ontology_semantic_context_pack_builds_agent_context() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    context_pack = surfaces["semantic_context_pack"]
    assert context_pack["artifact_kind"] == "ontology_semantic_context_pack"
    assert context_pack["proposal_id"] == "0104"
    assert context_pack["target_scope"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0104",
    }
    assert context_pack["canonical_mutations_allowed"] is False
    assert context_pack["tracked_artifacts_written"] is False
    assert context_pack["source_surfaces"] == {
        "ontology_binding_preview": "runs/ontology_binding_preview.json",
        "ontology_governance_evidence_index": "runs/ontology_governance_evidence_index.json",
        "ontology_import_gap_index": "runs/ontology_import_gap_index.json",
        "ontology_package_index": "runs/ontology_package_index.json",
    }
    assert context_pack["summary"] == {
        "status": "ready_with_gaps",
        "package_count": 1,
        "accepted_term_count": 1,
        "accepted_relation_count": 1,
        "alias_count": 1,
        "deprecated_term_count": 1,
        "relation_conflict_count": 1,
        "unresolved_gap_count": 1,
        "governance_evidence_count": 1,
        "next_gap": "build_ontology_semantic_lint_report",
    }

    package = context_pack["packages"][0]
    assert package["package_ref"] == "edu.university.examcalc@0.1.0"
    assert package["digest"] == (
        "sha256:7cdf061c1c845e0d0d801c7d935b6d4b765db1317ec595910da2cb910eca9e2f"
    )

    accepted_terms = {entry["source_ref"]: entry for entry in context_pack["accepted_terms"]}
    accepted_relations = {
        entry["source_ref"]: entry for entry in context_pack["accepted_relations"]
    }
    assert accepted_terms["examcalc:Exam"]["preferred_term"] == "Exam"
    assert accepted_terms["examcalc:Exam"]["kind"] == "class"
    assert accepted_relations["examcalc:requires_policy"]["preferred_term"] == ("requires_policy")
    assert accepted_relations["examcalc:requires_policy"]["kind"] == "relation"

    aliases = {entry["term"]: entry for entry in context_pack["aliases"]}
    assert aliases["requires policy"]["status"] == "grounded"
    assert aliases["requires policy"]["concept_ref"] == "examcalc:requires_policy"
    assert aliases["requires policy"]["concept"]["kind"] == "relation"

    deprecated = {entry["term"]: entry for entry in context_pack["deprecated_terms"]}
    assert deprecated["ExamPolicy"]["replacement_ref"] == "examcalc:ExamPolicyProfile"
    assert deprecated["ExamPolicy"]["replacement_status"] == "unresolved_replacement_ref"

    conflicts = {entry["term"]: entry for entry in context_pack["relation_conflicts"]}
    assert conflicts["allows policy"]["status"] == "grounded"
    assert conflicts["allows policy"]["accepted_relation_ref"] == "examcalc:requires_policy"

    assert context_pack["unresolved_gaps"][0]["missing_concept"]["ref"] == ("examcalc:CASFunction")
    assert context_pack["governance_evidence"][0]["decision_ref"].startswith(
        "ontology-governance://edu.university.examcalc/0.1.0/"
    )
    assert context_pack["consumer_boundary"]["for_prompt_agent_input"] is True
    assert context_pack["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert context_pack["authority_boundary"]["context_pack_is_authority"] is False


def test_ontology_semantic_context_pack_rejects_non_relation_conflict_embedding(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["semantic_controls"]["relation_conflicts"][0]["accepted_relation_ref"] = (
        "examcalc:Exam"
    )
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    surfaces = module.build_ontology_import_surfaces(
        fixture_path,
        policy_path=policy_path,
        semantic_policy_path=semantic_policy_path,
    )

    conflict = surfaces["semantic_context_pack"]["relation_conflicts"][0]
    assert conflict["accepted_relation_ref"] == "examcalc:Exam"
    assert conflict["status"] == "unresolved_relation_ref"
    assert "accepted_relation" not in conflict


def test_ontology_semantic_default_policy_follows_root_override(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path)

    surfaces = module.build_ontology_import_surfaces(
        fixture_path,
        policy_path=policy_path,
    )

    assert surfaces["semantic_context_pack"]["source_policy"] == (
        "tools/ontology_semantic_control_policy.json"
    )
    assert semantic_policy_path.exists()


def test_ontology_semantic_write_uses_surface_output_artifact(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["repository_layout"]["semantic_context_pack"] = (
        "runs/custom_semantic_context_pack.json"
    )
    semantic_policy["repository_layout"]["semantic_lint_smoke"] = (
        "runs/custom_semantic_lint_smoke.json"
    )
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    surfaces = module.build_ontology_import_surfaces(
        fixture_path,
        policy_path=policy_path,
        semantic_policy_path=semantic_policy_path,
    )
    written = module.write_ontology_import_surfaces(
        surfaces,
        policy_path=policy_path,
        out_dir=tmp_path,
    )

    written_paths = {path.relative_to(tmp_path).as_posix() for path in written}
    assert "runs/custom_semantic_context_pack.json" in written_paths
    assert "runs/custom_semantic_lint_smoke.json" in written_paths
    assert not (tmp_path / "runs" / "ontology_semantic_context_pack.json").exists()
    assert not (tmp_path / "runs" / "ontology_semantic_lint_smoke.json").exists()


def test_ontology_semantic_context_pack_rejects_malformed_governance_evidence() -> None:
    module = load_ontology_imports_module()
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    governance = dict(surfaces["governance_evidence_index"])
    governance["evidence"] = ["not-an-object"]
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    import_policy = json.loads((ROOT / "tools" / "ontology_import_policy.json").read_text())

    with pytest.raises(ValueError, match=r"ontology_governance_evidence_index\.evidence\[0\]"):
        module.build_ontology_semantic_context_pack(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            import_policy=import_policy,
            package_index=surfaces["package_index"],
            gap_index=surfaces["gap_index"],
            governance_evidence_index=governance,
            binding_preview=surfaces["binding_preview"],
        )


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


def test_ontologyc_adapter_report_smoke_validates_report_contract() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(
        FIXTURE,
        adapter_report_path=ADAPTER_REPORT,
    )

    smoke = surfaces["adapter_report_smoke"]
    assert smoke["artifact_kind"] == "ontologyc_adapter_report_smoke"
    assert smoke["canonical_mutations_allowed"] is False
    assert smoke["tracked_artifacts_written"] is False
    assert smoke["accepted_report_kind"] == "ontologyc_adapter_report"
    assert smoke["adapter_command"] == "validate-specgraph"
    assert smoke["source_authority"] == {
        "package_id": "edu.university.examcalc",
        "namespace": "examcalc",
        "version": "0.1.0",
        "source_uri": "git+https://github.com/0al-spec/Ontology.git",
        "source_ref": "main",
        "digest": ("sha256:7cdf061c1c845e0d0d801c7d935b6d4b765db1317ec595910da2cb910eca9e2f"),
        "digest_validation": "package.digest_must_match_normalized_ir_sourceDigest",
    }
    assert smoke["summary"] == {
        "status": "passed",
        "resolved_ref_count": 2,
        "gap_count": 1,
        "next_gap": "review_ontology_import_gap",
    }
    assert {check["check_id"] for check in smoke["checks"]} == {
        "adapter_report_shape_valid",
        "adapter_report_source_version_digest_match",
        "adapter_report_outputs_resolve",
        "adapter_report_counts_match_outputs",
        "adapter_report_authority_boundary_preserved",
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
        "runs/ontologyc_adapter_report_smoke.json": "ontologyc_adapter_report_smoke",
        "runs/ontology_semantic_context_pack.json": "ontology_semantic_context_pack",
        "runs/ontology_semantic_lint_smoke.json": "ontology_semantic_lint_smoke",
    }
    for relative_path, artifact_kind in expected.items():
        payload = json.loads((ROOT / relative_path).read_text())
        assert payload["artifact_kind"] == artifact_kind
        expected_proposal_id = {
            "ontology_semantic_context_pack": "0104",
            "ontology_semantic_lint_smoke": "0103",
        }.get(artifact_kind, "0060")
        assert payload["proposal_id"] == expected_proposal_id
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


def test_ontologyc_adapter_report_rejects_digest_mismatch(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    report = load_adapter_report_payload()
    assert isinstance(report["package"], dict)
    report["package"]["digest"] = (
        "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    )
    report_path = write_temp_adapter_report(tmp_path, report)

    with pytest.raises(ValueError, match="digest"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontologyc_adapter_report_rejects_bool_schema_version(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    report = load_adapter_report_payload()
    report["schema_version"] = True
    report_path = write_temp_adapter_report(tmp_path, report)

    with pytest.raises(ValueError, match="schema_version must be an integer"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontologyc_adapter_report_enforces_required_input_refs(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy = json.loads((ROOT / "tools" / "ontology_import_policy.json").read_text())
    contract = policy["ontologyc_adapter_report_contract"]
    assert isinstance(contract, dict)
    assert isinstance(contract["required_input_refs"], list)
    contract["required_input_refs"].append("source_manifest_ref")
    policy_path = write_temp_policy(tmp_path, policy)
    report_path = write_temp_adapter_report(tmp_path, load_adapter_report_payload())

    with pytest.raises(ValueError, match="source_manifest_ref"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontologyc_adapter_report_rejects_bad_authority_field_prefix(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy = json.loads((ROOT / "tools" / "ontology_import_policy.json").read_text())
    contract = policy["ontologyc_adapter_report_contract"]
    assert isinstance(contract, dict)
    contract["authority_fields"] = ["report.package_id"]
    policy_path = write_temp_policy(tmp_path, policy)
    report_path = write_temp_adapter_report(tmp_path, load_adapter_report_payload())

    with pytest.raises(ValueError, match=r"package\.<field>"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontologyc_adapter_report_rejects_authority_expansion(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    report = load_adapter_report_payload()
    assert isinstance(report["authority_boundary"], dict)
    report["authority_boundary"]["automatic_canonical_node_update"] = True
    report_path = write_temp_adapter_report(tmp_path, report)

    with pytest.raises(ValueError, match="automatic_canonical_node_update"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontologyc_adapter_report_rejects_wrong_digest_authority(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    report = load_adapter_report_payload()
    assert isinstance(report["authority_boundary"], dict)
    report["authority_boundary"]["digest_authority"] = "ontology_lock_digest"
    report_path = write_temp_adapter_report(tmp_path, report)

    with pytest.raises(ValueError, match="digest_authority"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontology_semantic_control_policy_rejects_authority_expansion(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["authority_boundary"]["lint_report_is_authority"] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="lint_report_is_authority"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_semantic_control_policy_rejects_output_authority_expansion(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["derived_output_contract"]["writes_canonical_specs"] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="writes_canonical_specs"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_semantic_control_policy_rejects_non_run_output_roots(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["derived_output_contract"]["allowed_output_roots"] = ["specs/"]
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="allowed_output_roots"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontologyc_adapter_report_rejects_lock_digest_mismatch(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    report_path = write_temp_adapter_report(tmp_path, load_adapter_report_payload())
    lock_path = report_path.parent / "ontologyc" / "ontology.lock.yaml"
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    lock["spec"]["resolved"][0]["digest"] = (
        "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    )
    lock_path.write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="digest"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontologyc_adapter_report_requires_fixture_source_ref(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture = load_fixture_payload()
    assert isinstance(fixture["package"], dict)
    del fixture["package"]["source_ref"]
    fixture_path = write_temp_fixture(tmp_path, fixture)
    policy_path = write_temp_policy(tmp_path)
    report_path = write_temp_adapter_report(tmp_path, load_adapter_report_payload())

    with pytest.raises(ValueError, match=r"fixture\.package\.source_ref"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontologyc_adapter_report_rejects_corrupt_concept_ref_payload(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    report_path = write_temp_adapter_report(tmp_path, load_adapter_report_payload())
    refs_path = report_path.parent / "ontologyc" / "concept-refs.yaml"
    refs = yaml.safe_load(refs_path.read_text(encoding="utf-8"))
    refs["spec"]["refs"][0]["concept"] = "WrongConcept"
    refs_path.write_text(yaml.safe_dump(refs, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="concept_refs_output examcalc:Exam.concept"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontologyc_adapter_report_rejects_duplicate_concept_ref_alias(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    report_path = write_temp_adapter_report(tmp_path, load_adapter_report_payload())
    refs_path = report_path.parent / "ontologyc" / "concept-refs.yaml"
    refs = yaml.safe_load(refs_path.read_text(encoding="utf-8"))
    duplicate = dict(refs["spec"]["refs"][0])
    refs["spec"]["refs"].append(duplicate)
    refs_path.write_text(yaml.safe_dump(refs, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="concept_refs_output.*duplicates"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_ontologyc_adapter_report_uses_gap_output_context(tmp_path: Path) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    report_path = write_temp_adapter_report(tmp_path, load_adapter_report_payload())
    gaps_path = report_path.parent / "ontologyc" / "ontology-gaps.yaml"
    gaps = yaml.safe_load(gaps_path.read_text(encoding="utf-8"))
    gaps["spec"]["gaps"] = "not-a-list"
    gaps_path.write_text(yaml.safe_dump(gaps, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match=r"ontology_gaps_output\.spec\.gaps"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            adapter_report_path=report_path,
        )


def test_cli_custom_fixture_does_not_require_default_adapter_report(tmp_path: Path) -> None:
    fixture = load_fixture_payload()
    fixture["proposal_id"] = "custom-0060"
    fixture_path = write_temp_fixture(tmp_path, fixture)

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "ontology_imports.py"),
            "--fixture",
            str(fixture_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    surfaces = json.loads(completed.stdout)

    assert "adapter_report_smoke" not in surfaces
    assert "semantic_context_pack" not in surfaces
    assert "semantic_lint_smoke" not in surfaces
    assert surfaces["package_index"]["proposal_id"] == "custom-0060"


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
        "tools/ontology_imports.py",
        "def build_ontologyc_adapter_report_smoke(",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_import_fixture_resolves_known_refs_and_gaps(",
    ) in validation_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontologyc_adapter_report_smoke_validates_report_contract(",
    ) in validation_markers
    assert ("Makefile", "ontology-imports:") in observation_markers


def test_proposal_0104_runtime_registry_tracks_context_pack() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0104"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert (
        "tools/ontology_semantic_control_policy.json",
        "semantic_context_pack_contract",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def build_ontology_semantic_context_pack(",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_semantic_context_pack_builds_agent_context(",
    ) in validation_markers
    assert (
        "tools/README.md",
        "runs/ontology_semantic_context_pack.json",
    ) in observation_markers
