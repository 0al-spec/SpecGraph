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
    source_set = policy.get("semantic_lint_input_sources")
    if isinstance(source_set, dict):
        for raw_source in source_set.get("source_outputs", []):
            if not isinstance(raw_source, dict):
                continue
            raw_path = raw_source.get("path")
            if not isinstance(raw_path, str):
                continue
            source_path = ROOT / raw_path
            if not source_path.exists():
                continue
            target_path = tmp_path / raw_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
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
    assert policy["repository_layout"]["semantic_lint_input"] == (
        "runs/ontology_semantic_lint_input.json"
    )
    assert policy["repository_layout"]["semantic_lint_report"] == (
        "runs/ontology_semantic_lint_report.json"
    )
    assert policy["repository_layout"]["semantic_review_surface"] == (
        "runs/ontology_semantic_review_surface.json"
    )
    assert policy["repository_layout"]["supervisor_semantic_gate"] == (
        "runs/ontology_supervisor_semantic_gate.json"
    )
    assert policy["repository_layout"]["ontology_delta_draft_intake"] == (
        "runs/ontology_delta_draft_intake.json"
    )
    assert policy["repository_layout"]["ontology_closed_loop_evidence"] == (
        "runs/ontology_closed_loop_evidence.json"
    )
    assert policy["repository_layout"]["ontology_review_dashboard"] == (
        "runs/ontology_review_dashboard.json"
    )
    assert policy["repository_layout"]["ontology_owner_decision_report"] == (
        "runs/ontology_owner_decision_report.json"
    )
    assert policy["repository_layout"]["ontology_decision_import_preview"] == (
        "runs/ontology_decision_import_preview.json"
    )
    assert policy["repository_layout"]["ontology_delta_candidate_review_packet"] == (
        "runs/ontology_delta_candidate_review_packet.json"
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
    lint_input_contract = policy["semantic_lint_input_contract"]
    assert lint_input_contract["artifact_kind"] == "ontology_semantic_lint_input"
    assert lint_input_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0116",
    }
    assert {"proposal_markdown", "supervisor_run_summary"}.issubset(
        set(lint_input_contract["source_output_kinds"])
    )
    assert lint_input_contract["extraction_mode"] == "deterministic_declared_term_extraction"
    assert lint_input_contract["consumer_boundary"]["for_semantic_lint_report"] is True
    assert lint_input_contract["consumer_boundary"]["for_supervisor_gate_evidence"] is True
    assert lint_input_contract["consumer_boundary"]["may_parse_arbitrary_text"] is False
    assert lint_input_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert lint_input_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    lint_input_sources = policy["semantic_lint_input_sources"]
    assert lint_input_sources["artifact_kind"] == "ontology_semantic_lint_input_source_set"
    assert lint_input_sources["source_outputs"][0]["path"] == (
        "docs/proposals/0105_ontology_semantic_lint_report.md"
    )
    report_contract = policy["semantic_lint_report_contract"]
    assert report_contract["artifact_kind"] == "ontology_semantic_lint_report"
    assert report_contract["source_context_pack_artifact_kind"] == (
        "ontology_semantic_context_pack"
    )
    assert report_contract["source_lint_input_artifact_kind"] == ("ontology_semantic_lint_input")
    assert report_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0105",
    }
    assert report_contract["consumer_boundary"]["for_supervisor_gate_evidence"] is True
    assert report_contract["consumer_boundary"]["for_specspace_review_surface"] is True
    assert report_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert report_contract["consumer_boundary"]["may_write_ontology_delta"] is False
    delta_contract = policy["ontology_delta_candidate_review_packet_contract"]
    assert delta_contract["artifact_kind"] == "ontology_delta_candidate_review_packet"
    assert delta_contract["source_lint_report_artifact_kind"] == ("ontology_semantic_lint_report")
    assert delta_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0106",
    }
    assert {
        "approve_for_ontology_package_draft",
        "reject_candidate",
        "request_clarification",
    }.issubset(set(delta_contract["review_actions"]))
    assert delta_contract["consumer_boundary"]["for_supervisor_gate_evidence"] is True
    assert delta_contract["consumer_boundary"]["for_specspace_review_surface"] is True
    assert delta_contract["consumer_boundary"]["may_write_ontology_package"] is False
    assert delta_contract["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert delta_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    review_surface_contract = policy["semantic_review_surface_contract"]
    assert review_surface_contract["artifact_kind"] == "ontology_semantic_review_surface"
    assert review_surface_contract["source_context_pack_artifact_kind"] == (
        "ontology_semantic_context_pack"
    )
    assert review_surface_contract["source_lint_report_artifact_kind"] == (
        "ontology_semantic_lint_report"
    )
    assert review_surface_contract["source_delta_candidate_review_packet_artifact_kind"] == (
        "ontology_delta_candidate_review_packet"
    )
    assert review_surface_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0108",
    }
    assert {
        "blocking_findings",
        "review_required_findings",
        "ontology_delta_candidates",
    }.issubset(set(review_surface_contract["review_item_sources"]))
    assert {
        "replace_with_accepted_term",
        "use_accepted_relation",
        "emit_ontology_gap",
        "approve_for_ontology_package_draft",
        "reject_candidate",
        "request_clarification",
    }.issubset(set(review_surface_contract["review_actions"]))
    assert review_surface_contract["consumer_boundary"]["for_supervisor_gate_evidence"] is True
    assert review_surface_contract["consumer_boundary"]["for_specspace_review_surface"] is True
    assert review_surface_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert review_surface_contract["consumer_boundary"]["may_write_ontology_package"] is False
    assert review_surface_contract["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert review_surface_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert review_surface_contract["consumer_boundary"]["may_mark_candidate_accepted"] is False
    supervisor_gate_contract = policy["supervisor_semantic_gate_contract"]
    assert supervisor_gate_contract["artifact_kind"] == "ontology_supervisor_semantic_gate"
    assert supervisor_gate_contract["source_review_surface_artifact_kind"] == (
        "ontology_semantic_review_surface"
    )
    assert supervisor_gate_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0109",
    }
    assert {"clear", "review_pending", "blocked"}.issubset(
        set(supervisor_gate_contract["gate_states"])
    )
    assert "blocked" in supervisor_gate_contract["blocking_review_states"]
    assert {"needs_review", "needs_ontology_owner_review"}.issubset(
        set(supervisor_gate_contract["review_required_states"])
    )
    assert supervisor_gate_contract["consumer_boundary"]["for_supervisor_gate_evidence"] is True
    assert supervisor_gate_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert supervisor_gate_contract["consumer_boundary"]["may_write_ontology_package"] is False
    assert supervisor_gate_contract["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert supervisor_gate_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert supervisor_gate_contract["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert supervisor_gate_contract["typed_invocation_boundary"]["prompt_agent_executed"] is False
    assert (
        supervisor_gate_contract["typed_invocation_boundary"]["prompt_agent_execution_allowed"]
        is False
    )
    assert (
        supervisor_gate_contract["typed_invocation_boundary"]["supervisor_prompt_mutation_allowed"]
        is False
    )
    delta_draft_intake_contract = policy["ontology_delta_draft_intake_contract"]
    assert delta_draft_intake_contract["artifact_kind"] == "ontology_delta_draft_intake"
    assert delta_draft_intake_contract["source_supervisor_semantic_gate_artifact_kind"] == (
        "ontology_supervisor_semantic_gate"
    )
    assert (
        delta_draft_intake_contract["source_delta_candidate_review_packet_artifact_kind"]
        == "ontology_delta_candidate_review_packet"
    )
    assert delta_draft_intake_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0110",
    }
    assert {
        "blocked_by_semantic_gate",
        "awaiting_ontology_owner_review",
        "no_candidates",
    }.issubset(set(delta_draft_intake_contract["allowed_intake_states"]))
    assert {"blocked", "review_pending", "clear"}.issubset(
        set(delta_draft_intake_contract["required_gate_states"])
    )
    assert "blocked" in delta_draft_intake_contract["blocked_gate_states"]
    assert (
        "needs_ontology_owner_review"
        in delta_draft_intake_contract["review_required_candidate_states"]
    )
    assert (
        delta_draft_intake_contract["consumer_boundary"]["for_ontology_owner_draft_intake"] is True
    )
    assert delta_draft_intake_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert delta_draft_intake_contract["consumer_boundary"]["may_write_ontology_package"] is False
    assert delta_draft_intake_contract["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert delta_draft_intake_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert delta_draft_intake_contract["consumer_boundary"]["may_mark_candidate_accepted"] is False
    closed_loop_contract = policy["ontology_closed_loop_evidence_contract"]
    assert closed_loop_contract["artifact_kind"] == "ontology_closed_loop_evidence"
    assert closed_loop_contract["source_delta_draft_intake_artifact_kind"] == (
        "ontology_delta_draft_intake"
    )
    assert closed_loop_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0111",
    }
    assert {
        "blocked_by_semantic_gate",
        "pending_ontology_owner_decision",
        "no_candidates",
    }.issubset(set(closed_loop_contract["evidence_states"]))
    assert closed_loop_contract["closed_loop_source"] == (
        "ontology_delta_draft_intake.draft_requests"
    )
    assert closed_loop_contract["consumer_boundary"]["for_specgraph_evidence_review"] is True
    assert closed_loop_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert closed_loop_contract["consumer_boundary"]["may_write_ontology_package"] is False
    assert closed_loop_contract["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert closed_loop_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert closed_loop_contract["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert closed_loop_contract["consumer_boundary"]["may_close_semantic_gate"] is False
    dashboard_contract = policy["ontology_review_dashboard_contract"]
    assert dashboard_contract["artifact_kind"] == "ontology_review_dashboard"
    assert dashboard_contract["source_review_surface_artifact_kind"] == (
        "ontology_semantic_review_surface"
    )
    assert dashboard_contract["source_supervisor_semantic_gate_artifact_kind"] == (
        "ontology_supervisor_semantic_gate"
    )
    assert dashboard_contract["source_delta_draft_intake_artifact_kind"] == (
        "ontology_delta_draft_intake"
    )
    assert dashboard_contract["source_closed_loop_evidence_artifact_kind"] == (
        "ontology_closed_loop_evidence"
    )
    assert dashboard_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0113",
    }
    assert {
        "status_summary",
        "gate",
        "blocking_items",
        "review_required_items",
        "delta_candidates",
        "draft_requests",
        "closed_loop_entries",
        "review_actions",
        "source_artifacts",
        "authority_boundary",
    }.issubset(set(dashboard_contract["dashboard_sections"]))
    assert {
        "blocked_by_semantic_gate",
        "pending_ontology_owner_decision",
        "review_pending",
        "clear",
        "no_candidates",
    }.issubset(set(dashboard_contract["status_states"]))
    assert dashboard_contract["consumer_boundary"]["for_specgraph_review_dashboard"] is True
    assert dashboard_contract["consumer_boundary"]["for_specspace_review_dashboard"] is True
    assert dashboard_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert dashboard_contract["consumer_boundary"]["may_write_ontology_package"] is False
    assert dashboard_contract["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert dashboard_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert dashboard_contract["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert dashboard_contract["consumer_boundary"]["may_import_owner_decision"] is False
    assert dashboard_contract["consumer_boundary"]["may_close_semantic_gate"] is False
    owner_decision_contract = policy["ontology_owner_decision_report_contract"]
    assert owner_decision_contract["artifact_kind"] == "ontology_owner_decision_report"
    assert owner_decision_contract["source_closed_loop_evidence_artifact_kind"] == (
        "ontology_closed_loop_evidence"
    )
    assert owner_decision_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0114",
    }
    assert {
        "accepted",
        "rejected",
        "needs_clarification",
    }.issubset(set(owner_decision_contract["decision_states"]))
    assert {
        "decision_id",
        "candidate_id",
        "intake_id",
        "decision_state",
        "ontology_decision_ref",
        "accepted_ontology_delta",
        "imports_into_specgraph",
        "closes_semantic_gate",
        "mutates_canonical_specs",
    }.issubset(set(owner_decision_contract["required_decision_fields"]))
    assert (
        owner_decision_contract["consumer_boundary"]["for_specgraph_decision_import_preview"]
        is True
    )
    assert owner_decision_contract["consumer_boundary"]["for_specspace_review_dashboard"] is True
    assert owner_decision_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert owner_decision_contract["consumer_boundary"]["may_write_ontology_package"] is False
    assert owner_decision_contract["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert owner_decision_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert owner_decision_contract["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert owner_decision_contract["consumer_boundary"]["may_import_into_specgraph"] is False
    assert owner_decision_contract["consumer_boundary"]["may_close_semantic_gate"] is False
    decision_import_contract = policy["ontology_decision_import_preview_contract"]
    assert decision_import_contract["artifact_kind"] == "ontology_decision_import_preview"
    assert decision_import_contract["source_review_dashboard_artifact_kind"] == (
        "ontology_review_dashboard"
    )
    assert decision_import_contract["source_owner_decision_report_artifact_kind"] == (
        "ontology_owner_decision_report"
    )
    assert decision_import_contract["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0115",
    }
    assert {
        "blocked_by_semantic_gate",
        "ready_for_operator_review",
        "rejected_by_owner",
        "needs_clarification",
        "unmatched_decision",
        "no_decisions",
    }.issubset(set(decision_import_contract["preview_states"]))
    assert (
        decision_import_contract["consumer_boundary"]["for_specgraph_decision_import_preview"]
        is True
    )
    assert decision_import_contract["consumer_boundary"]["for_specspace_review_dashboard"] is True
    assert decision_import_contract["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert decision_import_contract["consumer_boundary"]["may_write_ontology_package"] is False
    assert decision_import_contract["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert decision_import_contract["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert decision_import_contract["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert decision_import_contract["consumer_boundary"]["may_apply_preview"] is False
    assert decision_import_contract["consumer_boundary"]["may_import_into_specgraph"] is False
    assert decision_import_contract["consumer_boundary"]["may_close_semantic_gate"] is False
    owner_decision_fixture = policy["owner_decision_fixture"]
    assert owner_decision_fixture["artifact_kind"] == "ontology_owner_decision_fixture"
    assert {decision["decision_state"] for decision in owner_decision_fixture["decisions"]} == {
        "accepted",
        "rejected",
    }
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
    assert boundary["semantic_lint_input_is_authority"] is False
    assert boundary["smoke_report_is_authority"] is False
    assert boundary["ontology_delta_candidate_is_authority"] is False
    assert boundary["semantic_review_surface_is_authority"] is False
    assert boundary["supervisor_semantic_gate_is_authority"] is False
    assert boundary["ontology_delta_draft_intake_is_authority"] is False
    assert boundary["ontology_closed_loop_evidence_is_authority"] is False
    assert boundary["ontology_review_dashboard_is_authority"] is False
    assert boundary["ontology_owner_decision_report_is_authority"] is False
    assert boundary["ontology_decision_import_preview_is_authority"] is False
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


def test_ontology_semantic_lint_input_extracts_terms_from_proposal_output() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    lint_input = surfaces["semantic_lint_input"]
    assert lint_input["artifact_kind"] == "ontology_semantic_lint_input"
    assert lint_input["proposal_id"] == "0116"
    assert lint_input["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0116",
    }
    assert lint_input["canonical_mutations_allowed"] is False
    assert lint_input["tracked_artifacts_written"] is False
    assert lint_input["output_artifact"] == "runs/ontology_semantic_lint_input.json"
    assert lint_input["summary"] == {
        "status": "ready",
        "source_output_count": 1,
        "detected_term_count": 5,
        "next_gap": "wire_supervisor_semantic_gate_into_targeted_runs",
    }

    source = lint_input["source_outputs"][0]
    assert source["source_id"] == "proposal-0105-semantic-lint-report"
    assert source["source_kind"] == "proposal_markdown"
    assert source["path"] == "docs/proposals/0105_ontology_semantic_lint_report.md"
    assert source["text_sha256"].startswith("sha256:")
    assert source["declared_term_count"] == 5

    source_text = (ROOT / source["path"]).read_text(encoding="utf-8")
    by_term = {entry["term"]: entry for entry in lint_input["detected_terms"]}
    assert sorted(by_term) == [
        "CASFunction",
        "Exam",
        "ExamPolicy",
        "allows policy",
        "requires policy",
    ]
    assert by_term["CASFunction"]["source_ref"] == "examcalc:CASFunction"
    assert by_term["Exam"]["source_ref"] == "examcalc:Exam"
    assert by_term["ExamPolicy"]["source_output_kind"] == "proposal_markdown"
    span = by_term["allows policy"]["source_span"]
    assert source_text[span["start_offset"] : span["end_offset"]] == "allows policy"
    assert span["line"] > 0
    assert span["column"] > 0
    assert lint_input["extraction_summary"] == {
        "mode": "deterministic_declared_term_extraction",
        "source_output_count": 1,
        "detected_term_count": 5,
        "term_source": "semantic_lint_input_sources.source_outputs[].terms",
        "arbitrary_text_parsed": False,
        "prompt_agent_executed": False,
    }
    assert lint_input["consumer_boundary"]["for_semantic_lint_report"] is True
    assert lint_input["consumer_boundary"]["may_parse_arbitrary_text"] is False
    assert lint_input["authority_boundary"]["semantic_lint_input_is_authority"] is False


def test_ontology_semantic_lint_report_builds_review_findings() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    report = surfaces["semantic_lint_report"]
    assert report["artifact_kind"] == "ontology_semantic_lint_report"
    assert report["proposal_id"] == "0105"
    assert report["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0105",
    }
    assert report["source_context_pack"] == "runs/ontology_semantic_context_pack.json"
    assert report["source_lint_input"] == "runs/ontology_semantic_lint_input.json"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["summary"] == {
        "status": "blocked_relation_conflict",
        "finding_count": 5,
        "classification_counts": {
            "accepted_alias": 1,
            "accepted_term": 1,
            "deprecated_term": 1,
            "relation_conflict": 1,
            "unknown_term": 1,
        },
        "review_required_count": 1,
        "blocking_count": 2,
        "candidate_delta_count": 1,
        "next_review_gap": "review_ontology_relation_conflict",
        "next_gap": "build_ontology_delta_candidate_review_packet",
    }

    by_term = {entry["term"]: entry for entry in report["findings"]}
    assert by_term["Exam"]["classification"] == "accepted_term"
    assert by_term["Exam"]["source_output_id"] == "proposal-0105-semantic-lint-report"
    assert by_term["Exam"]["source_path"] == (
        "docs/proposals/0105_ontology_semantic_lint_report.md"
    )
    assert by_term["requires policy"]["classification"] == "accepted_alias"
    assert by_term["CASFunction"]["classification"] == "unknown_term"
    assert by_term["CASFunction"]["gap"]["gap_id"] == "ontology-gap-examcalc-casfunction"
    assert by_term["ExamPolicy"]["classification"] == "deprecated_term"
    assert by_term["allows policy"]["classification"] == "relation_conflict"

    blocking_terms = {entry["term"] for entry in report["blocking_findings"]}
    assert blocking_terms == {"ExamPolicy", "allows policy"}
    review_terms = {entry["term"] for entry in report["review_required_findings"]}
    assert review_terms == {"CASFunction"}

    assert report["candidate_delta_terms"] == [
        {
            "term": "CASFunction",
            "source_ref": "examcalc:CASFunction",
            "missing_concept": {
                "ref": "examcalc:CASFunction",
                "namespace_hint": "examcalc",
                "concept_hint": "CASFunction",
            },
            "gap_id": "ontology-gap-examcalc-casfunction",
            "recommended_route": "ontology_package_draft",
            "suggested_action": "emit_ontology_gap",
        }
    ]
    action_counts = {
        entry["action"]: entry["term_count"] for entry in report["recommended_actions"]
    }
    assert action_counts["emit_ontology_gap"] == 1
    assert action_counts["replace_with_accepted_term"] == 1
    assert action_counts["use_accepted_relation"] == 1
    assert report["consumer_boundary"]["for_supervisor_gate_evidence"] is True
    assert report["consumer_boundary"]["may_write_ontology_delta"] is False
    assert report["authority_boundary"]["lint_report_is_authority"] is False


def test_ontology_delta_candidate_review_packet_builds_review_packet() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    packet = surfaces["ontology_delta_candidate_review_packet"]
    assert packet["artifact_kind"] == "ontology_delta_candidate_review_packet"
    assert packet["proposal_id"] == "0106"
    assert packet["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0106",
    }
    assert packet["source_lint_report"] == "runs/ontology_semantic_lint_report.json"
    assert packet["canonical_mutations_allowed"] is False
    assert packet["tracked_artifacts_written"] is False
    assert packet["summary"] == {
        "status": "review_required",
        "candidate_count": 1,
        "source_lint_status": "blocked_relation_conflict",
        "blocking_count": 2,
        "next_gap": "build_specspace_semantic_review_surface",
    }

    assert packet["candidates"] == [
        {
            "candidate_id": "ontology-delta-candidate-examcalc-casfunction",
            "term": "CASFunction",
            "source_ref": "examcalc:CASFunction",
            "missing_concept": {
                "ref": "examcalc:CASFunction",
                "namespace_hint": "examcalc",
                "concept_hint": "CASFunction",
            },
            "gap_id": "ontology-gap-examcalc-casfunction",
            "recommended_route": "ontology_package_draft",
            "source_lint_action": "emit_ontology_gap",
            "proposed_delta": {
                "operation": "draft_ontology_concept",
                "ref": "examcalc:CASFunction",
                "namespace": "examcalc",
                "symbol": "CASFunction",
                "source": "ontology_semantic_lint_report_candidate",
            },
            "review_state": "needs_ontology_owner_review",
            "writes_ontology_package": False,
            "mutates_canonical_specs": False,
        }
    ]
    actions = {entry["action"]: entry for entry in packet["review_actions"]}
    assert sorted(actions) == [
        "approve_for_ontology_package_draft",
        "reject_candidate",
        "request_clarification",
    ]
    assert actions["approve_for_ontology_package_draft"]["writes_ontology_package"] is False
    assert actions["approve_for_ontology_package_draft"]["mutates_canonical_specs"] is False
    assert packet["consumer_boundary"]["may_write_ontology_package"] is False
    assert packet["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert packet["authority_boundary"]["ontology_delta_candidate_is_authority"] is False


def test_ontology_semantic_review_surface_builds_specspace_surface() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    surface = surfaces["semantic_review_surface"]
    assert surface["artifact_kind"] == "ontology_semantic_review_surface"
    assert surface["proposal_id"] == "0108"
    assert surface["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0108",
    }
    assert surface["source_artifacts"] == {
        "semantic_context_pack": "runs/ontology_semantic_context_pack.json",
        "semantic_lint_report": "runs/ontology_semantic_lint_report.json",
        "ontology_delta_candidate_review_packet": (
            "runs/ontology_delta_candidate_review_packet.json"
        ),
    }
    assert surface["canonical_mutations_allowed"] is False
    assert surface["tracked_artifacts_written"] is False
    assert surface["grounding_summary"] == {
        "source_context_status": "ready_with_gaps",
        "source_lint_status": "blocked_relation_conflict",
        "source_delta_candidate_status": "review_required",
        "package_count": 1,
        "accepted_term_count": 1,
        "accepted_relation_count": 1,
        "alias_count": 1,
        "deprecated_term_count": 1,
        "relation_conflict_count": 1,
        "unresolved_gap_count": 1,
        "governance_evidence_count": 1,
    }
    assert surface["summary"] == {
        "status": "blocked_relation_conflict",
        "blocking_count": 2,
        "review_required_count": 1,
        "candidate_count": 1,
        "review_item_count": 4,
        "next_gap": "build_specspace_semantic_review_surface_consumer",
    }

    review_items = {entry["item_id"]: entry for entry in surface["review_items"]}
    assert sorted(review_items) == [
        "ontology-delta-candidate-examcalc-casfunction",
        "semantic-finding-allows-policy",
        "semantic-finding-casfunction",
        "semantic-finding-exampolicy",
    ]
    relation_conflict = review_items["semantic-finding-allows-policy"]
    assert relation_conflict["item_kind"] == "semantic_finding"
    assert relation_conflict["review_state"] == "blocked"
    assert relation_conflict["classification"] == "relation_conflict"
    assert relation_conflict["suggested_action"] == "use_accepted_relation"

    candidate = review_items["ontology-delta-candidate-examcalc-casfunction"]
    assert candidate["item_kind"] == "ontology_delta_candidate"
    assert candidate["review_state"] == "needs_ontology_owner_review"
    assert candidate["suggested_actions"] == [
        "approve_for_ontology_package_draft",
        "reject_candidate",
        "request_clarification",
    ]

    action_sources = {
        (entry["source"], entry["action"]): entry for entry in surface["review_actions"]
    }
    assert sorted(action_sources) == [
        (
            "ontology_delta_candidate_review_packet.review_actions",
            "approve_for_ontology_package_draft",
        ),
        ("ontology_delta_candidate_review_packet.review_actions", "reject_candidate"),
        ("ontology_delta_candidate_review_packet.review_actions", "request_clarification"),
        ("ontology_semantic_lint_report.recommended_actions", "emit_ontology_gap"),
        ("ontology_semantic_lint_report.recommended_actions", "replace_with_accepted_term"),
        ("ontology_semantic_lint_report.recommended_actions", "use_accepted_relation"),
    ]
    assert (
        action_sources[
            (
                "ontology_delta_candidate_review_packet.review_actions",
                "approve_for_ontology_package_draft",
            )
        ]["writes_ontology_package"]
        is False
    )
    assert surface["consumer_boundary"]["for_specspace_review_surface"] is True
    assert surface["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert surface["consumer_boundary"]["may_write_ontology_package"] is False
    assert surface["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert surface["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert surface["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert surface["authority_boundary"]["semantic_review_surface_is_authority"] is False


def test_ontology_supervisor_semantic_gate_builds_gate_evidence() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    gate = surfaces["supervisor_semantic_gate"]
    assert gate["artifact_kind"] == "ontology_supervisor_semantic_gate"
    assert gate["proposal_id"] == "0109"
    assert gate["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0109",
    }
    assert gate["source_artifacts"] == {
        "semantic_context_pack": "runs/ontology_semantic_context_pack.json",
        "semantic_lint_report": "runs/ontology_semantic_lint_report.json",
        "ontology_delta_candidate_review_packet": (
            "runs/ontology_delta_candidate_review_packet.json"
        ),
        "semantic_review_surface": "runs/ontology_semantic_review_surface.json",
    }
    assert gate["canonical_mutations_allowed"] is False
    assert gate["tracked_artifacts_written"] is False
    assert gate["typed_invocation_boundary"] == {
        "input_artifact": "runs/ontology_semantic_review_surface.json",
        "output_artifact": "runs/ontology_supervisor_semantic_gate.json",
        "prompt_agent_executed": False,
        "prompt_agent_execution_allowed": False,
        "supervisor_prompt_mutation_allowed": False,
    }
    assert gate["gate"] == {
        "gate_state": "blocked",
        "outcome": "semantic_gate_blocked",
        "required_human_action": "resolve_blocking_ontology_semantic_findings",
        "blocking_item_ids": [
            "semantic-finding-exampolicy",
            "semantic-finding-allows-policy",
        ],
        "review_required_item_ids": [
            "semantic-finding-casfunction",
            "ontology-delta-candidate-examcalc-casfunction",
        ],
        "candidate_item_ids": ["ontology-delta-candidate-examcalc-casfunction"],
    }
    assert gate["summary"] == {
        "status": "blocked",
        "source_status": "blocked_relation_conflict",
        "blocking_count": 2,
        "review_required_count": 1,
        "candidate_count": 1,
        "review_item_count": 4,
        "next_gap": "wire_supervisor_semantic_gate_into_targeted_runs",
    }
    assert gate["evidence_refs"]["source_artifacts"]["semantic_review_surface"] == (
        "runs/ontology_semantic_review_surface.json"
    )
    assert gate["evidence_refs"]["blocking_item_ids"] == [
        "semantic-finding-exampolicy",
        "semantic-finding-allows-policy",
    ]
    assert gate["failure_modes"] == [
        "missing_or_invalid_semantic_review_surface",
        "blocking_semantic_findings",
        "ontology_owner_review_required",
    ]
    assert gate["consumer_boundary"]["for_supervisor_gate_evidence"] is True
    assert gate["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert gate["consumer_boundary"]["may_write_ontology_package"] is False
    assert gate["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert gate["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert gate["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert gate["authority_boundary"]["supervisor_semantic_gate_is_authority"] is False


def test_ontology_delta_draft_intake_builds_review_only_intake() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    intake = surfaces["ontology_delta_draft_intake"]
    assert intake["artifact_kind"] == "ontology_delta_draft_intake"
    assert intake["proposal_id"] == "0110"
    assert intake["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0110",
    }
    assert intake["source_artifacts"] == {
        "semantic_context_pack": "runs/ontology_semantic_context_pack.json",
        "semantic_lint_report": "runs/ontology_semantic_lint_report.json",
        "ontology_delta_candidate_review_packet": (
            "runs/ontology_delta_candidate_review_packet.json"
        ),
        "semantic_review_surface": "runs/ontology_semantic_review_surface.json",
        "supervisor_semantic_gate": "runs/ontology_supervisor_semantic_gate.json",
    }
    assert intake["canonical_mutations_allowed"] is False
    assert intake["tracked_artifacts_written"] is False
    assert intake["summary"] == {
        "status": "blocked_by_semantic_gate",
        "gate_state": "blocked",
        "candidate_count": 1,
        "draft_request_count": 1,
        "required_human_action": "resolve_blocking_ontology_semantic_findings",
        "next_gap": "collect_ontology_owner_delta_decisions",
    }

    request = intake["draft_requests"][0]
    assert request == {
        "intake_id": "ontology-delta-draft-intake-ontology-delta-candidate-examcalc-casfunction",
        "candidate_id": "ontology-delta-candidate-examcalc-casfunction",
        "term": "CASFunction",
        "review_state": "needs_ontology_owner_review",
        "intake_state": "blocked_by_semantic_gate",
        "required_human_action": "resolve_blocking_ontology_semantic_findings",
        "blocked_by_gate_state": "blocked",
        "blocking_item_ids": [
            "semantic-finding-exampolicy",
            "semantic-finding-allows-policy",
        ],
        "draft_delta": {
            "operation": "draft_ontology_concept",
            "ref": "examcalc:CASFunction",
            "namespace": "examcalc",
            "symbol": "CASFunction",
            "source": "ontology_semantic_lint_report_candidate",
        },
        "writes_ontology_package": False,
        "updates_ontology_lockfile": False,
        "mutates_canonical_specs": False,
        "marks_candidate_accepted": False,
    }
    assert intake["gate"]["gate_state"] == "blocked"
    assert intake["consumer_boundary"]["for_ontology_owner_draft_intake"] is True
    assert intake["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert intake["consumer_boundary"]["may_write_ontology_package"] is False
    assert intake["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert intake["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert intake["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert intake["authority_boundary"]["ontology_delta_draft_intake_is_authority"] is False


def test_ontology_closed_loop_evidence_builds_specgraph_evidence_surface() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    evidence = surfaces["ontology_closed_loop_evidence"]
    assert evidence["artifact_kind"] == "ontology_closed_loop_evidence"
    assert evidence["proposal_id"] == "0111"
    assert evidence["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0111",
    }
    assert evidence["source_artifacts"] == {
        "semantic_context_pack": "runs/ontology_semantic_context_pack.json",
        "semantic_lint_report": "runs/ontology_semantic_lint_report.json",
        "ontology_delta_candidate_review_packet": (
            "runs/ontology_delta_candidate_review_packet.json"
        ),
        "semantic_review_surface": "runs/ontology_semantic_review_surface.json",
        "supervisor_semantic_gate": "runs/ontology_supervisor_semantic_gate.json",
        "ontology_delta_draft_intake": "runs/ontology_delta_draft_intake.json",
    }
    assert evidence["canonical_mutations_allowed"] is False
    assert evidence["tracked_artifacts_written"] is False
    assert evidence["summary"] == {
        "status": "blocked_by_semantic_gate",
        "evidence_entry_count": 1,
        "pending_decision_count": 0,
        "blocked_entry_count": 1,
        "required_human_action": "resolve_blocking_ontology_semantic_findings",
        "next_gap": "wire_closed_loop_evidence_into_specgraph_review",
    }

    entry = evidence["evidence_entries"][0]
    assert entry == {
        "evidence_id": (
            "ontology-closed-loop-evidence-ontology-delta-candidate-examcalc-casfunction"
        ),
        "candidate_id": "ontology-delta-candidate-examcalc-casfunction",
        "intake_id": ("ontology-delta-draft-intake-ontology-delta-candidate-examcalc-casfunction"),
        "term": "CASFunction",
        "source_intake_state": "blocked_by_semantic_gate",
        "evidence_state": "blocked_by_semantic_gate",
        "specgraph_review_state": "blocked",
        "required_human_action": "resolve_blocking_ontology_semantic_findings",
        "ontology_decision_ref": "",
        "accepted_ontology_delta": False,
        "closes_semantic_gate": False,
        "mutates_canonical_specs": False,
        "blocking_item_ids": [
            "semantic-finding-exampolicy",
            "semantic-finding-allows-policy",
        ],
        "source_artifacts": evidence["source_artifacts"],
    }
    assert evidence["consumer_boundary"]["for_specgraph_evidence_review"] is True
    assert evidence["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert evidence["consumer_boundary"]["may_write_ontology_package"] is False
    assert evidence["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert evidence["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert evidence["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert evidence["consumer_boundary"]["may_close_semantic_gate"] is False
    assert evidence["authority_boundary"]["ontology_closed_loop_evidence_is_authority"] is False


def test_ontology_review_dashboard_builds_rich_review_projection() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    dashboard = surfaces["ontology_review_dashboard"]
    assert dashboard["artifact_kind"] == "ontology_review_dashboard"
    assert dashboard["proposal_id"] == "0113"
    assert dashboard["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0113",
    }
    assert dashboard["source_artifacts"] == {
        "semantic_context_pack": "runs/ontology_semantic_context_pack.json",
        "semantic_lint_report": "runs/ontology_semantic_lint_report.json",
        "ontology_delta_candidate_review_packet": (
            "runs/ontology_delta_candidate_review_packet.json"
        ),
        "semantic_review_surface": "runs/ontology_semantic_review_surface.json",
        "supervisor_semantic_gate": "runs/ontology_supervisor_semantic_gate.json",
        "ontology_delta_draft_intake": "runs/ontology_delta_draft_intake.json",
        "ontology_closed_loop_evidence": "runs/ontology_closed_loop_evidence.json",
    }
    assert dashboard["canonical_mutations_allowed"] is False
    assert dashboard["tracked_artifacts_written"] is False
    assert dashboard["status_summary"] == {
        "status": "blocked_by_semantic_gate",
        "gate_state": "blocked",
        "review_surface_status": "blocked_relation_conflict",
        "intake_status": "blocked_by_semantic_gate",
        "closed_loop_status": "blocked_by_semantic_gate",
        "blocking_count": 2,
        "review_required_count": 1,
        "candidate_count": 1,
        "draft_request_count": 1,
        "evidence_entry_count": 1,
        "pending_decision_count": 0,
        "blocked_entry_count": 1,
        "required_human_action": "resolve_blocking_ontology_semantic_findings",
        "next_gap": "build_specspace_rich_ontology_review_panel",
    }
    assert dashboard["gate"]["gate_state"] == "blocked"
    assert [item["item_id"] for item in dashboard["blocking_items"]] == [
        "semantic-finding-exampolicy",
        "semantic-finding-allows-policy",
    ]
    assert [item["item_id"] for item in dashboard["review_required_items"]] == [
        "semantic-finding-casfunction",
        "ontology-delta-candidate-examcalc-casfunction",
    ]
    assert [candidate["candidate_id"] for candidate in dashboard["delta_candidates"]] == [
        "ontology-delta-candidate-examcalc-casfunction"
    ]
    assert [request["intake_state"] for request in dashboard["draft_requests"]] == [
        "blocked_by_semantic_gate"
    ]
    assert [entry["evidence_state"] for entry in dashboard["closed_loop_entries"]] == [
        "blocked_by_semantic_gate"
    ]
    assert {action["action"] for action in dashboard["review_actions"]} == {
        "emit_ontology_gap",
        "replace_with_accepted_term",
        "use_accepted_relation",
        "approve_for_ontology_package_draft",
        "reject_candidate",
        "request_clarification",
    }
    assert dashboard["consumer_boundary"]["for_specgraph_review_dashboard"] is True
    assert dashboard["consumer_boundary"]["for_specspace_review_dashboard"] is True
    assert dashboard["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert dashboard["consumer_boundary"]["may_write_ontology_package"] is False
    assert dashboard["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert dashboard["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert dashboard["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert dashboard["consumer_boundary"]["may_import_owner_decision"] is False
    assert dashboard["consumer_boundary"]["may_close_semantic_gate"] is False
    assert dashboard["authority_boundary"]["ontology_review_dashboard_is_authority"] is False


def test_ontology_owner_decision_report_builds_read_only_decision_contract() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    report = surfaces["ontology_owner_decision_report"]
    assert report["artifact_kind"] == "ontology_owner_decision_report"
    assert report["proposal_id"] == "0114"
    assert report["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0114",
    }
    assert report["source_artifacts"]["ontology_closed_loop_evidence"] == (
        "runs/ontology_closed_loop_evidence.json"
    )
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["summary"] == {
        "status": "no_decisions",
        "decision_count": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "clarification_count": 0,
        "ignored_decision_count": 2,
        "next_gap": "build_ontology_decision_import_preview",
    }
    assert report["decisions"] == []
    ignored = {entry["decision_id"]: entry for entry in report["ignored_decisions"]}
    assert (
        ignored["ontology-owner-decision-accept-casfunction"]["reason"]
        == "closed_loop_evidence_not_pending_owner_decision"
    )
    assert (
        ignored["ontology-owner-decision-reject-legacyterm"]["reason"]
        == "missing_closed_loop_evidence"
    )
    assert report["consumer_boundary"]["for_specgraph_decision_import_preview"] is True
    assert report["consumer_boundary"]["for_specspace_review_dashboard"] is True
    assert report["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert report["consumer_boundary"]["may_write_ontology_package"] is False
    assert report["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert report["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert report["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert report["consumer_boundary"]["may_import_into_specgraph"] is False
    assert report["consumer_boundary"]["may_close_semantic_gate"] is False
    assert report["authority_boundary"]["ontology_owner_decision_report_is_authority"] is False


def test_ontology_decision_import_preview_builds_read_only_preview() -> None:
    module = load_ontology_imports_module()

    surfaces = module.build_ontology_import_surfaces(FIXTURE)

    preview = surfaces["ontology_decision_import_preview"]
    assert preview["artifact_kind"] == "ontology_decision_import_preview"
    assert preview["proposal_id"] == "0115"
    assert preview["target"] == {
        "target_kind": "proposal",
        "target_ref": "SG-RFC-0115",
    }
    assert preview["source_artifacts"]["ontology_review_dashboard"] == (
        "runs/ontology_review_dashboard.json"
    )
    assert preview["source_artifacts"]["ontology_owner_decision_report"] == (
        "runs/ontology_owner_decision_report.json"
    )
    assert preview["canonical_mutations_allowed"] is False
    assert preview["tracked_artifacts_written"] is False
    assert preview["summary"] == {
        "status": "no_decisions",
        "preview_count": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "clarification_count": 0,
        "importable_count": 0,
        "blocked_count": 0,
        "unmatched_count": 0,
        "ignored_decision_count": 2,
        "next_gap": "build_specspace_owner_decision_review_surface",
    }
    assert preview["decision_import_previews"] == []
    ignored = {entry["decision_id"]: entry for entry in preview["ignored_owner_decisions"]}
    assert (
        ignored["ontology-owner-decision-accept-casfunction"]["reason"]
        == "closed_loop_evidence_not_pending_owner_decision"
    )
    assert (
        ignored["ontology-owner-decision-reject-legacyterm"]["reason"]
        == "missing_closed_loop_evidence"
    )
    assert preview["consumer_boundary"]["for_specgraph_decision_import_preview"] is True
    assert preview["consumer_boundary"]["for_specspace_review_dashboard"] is True
    assert preview["consumer_boundary"]["may_execute_prompt_agent"] is False
    assert preview["consumer_boundary"]["may_write_ontology_package"] is False
    assert preview["consumer_boundary"]["may_update_ontology_lockfile"] is False
    assert preview["consumer_boundary"]["may_mutate_canonical_specs"] is False
    assert preview["consumer_boundary"]["may_mark_candidate_accepted"] is False
    assert preview["consumer_boundary"]["may_apply_preview"] is False
    assert preview["consumer_boundary"]["may_import_into_specgraph"] is False
    assert preview["consumer_boundary"]["may_close_semantic_gate"] is False
    assert preview["authority_boundary"]["ontology_decision_import_preview_is_authority"] is False


def test_ontology_review_dashboard_keeps_blocked_gate_above_no_candidates() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    review_surface = json.loads(json.dumps(surfaces["semantic_review_surface"]))
    supervisor_gate = json.loads(json.dumps(surfaces["supervisor_semantic_gate"]))
    draft_intake = json.loads(json.dumps(surfaces["ontology_delta_draft_intake"]))
    closed_loop_evidence = json.loads(json.dumps(surfaces["ontology_closed_loop_evidence"]))

    review_surface["delta_candidates"] = []
    review_surface["summary"]["candidate_count"] = 0
    draft_intake["draft_requests"] = []
    draft_intake["summary"]["status"] = "no_candidates"
    draft_intake["summary"]["candidate_count"] = 0
    draft_intake["summary"]["draft_request_count"] = 0
    draft_intake["summary"]["required_human_action"] = "none"
    closed_loop_evidence["evidence_entries"] = []
    closed_loop_evidence["summary"]["status"] = "no_candidates"
    closed_loop_evidence["summary"]["evidence_entry_count"] = 0
    closed_loop_evidence["summary"]["pending_decision_count"] = 0
    closed_loop_evidence["summary"]["blocked_entry_count"] = 0
    closed_loop_evidence["summary"]["required_human_action"] = "none"

    dashboard = module.build_ontology_review_dashboard(
        semantic_policy,
        semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
        review_surface=review_surface,
        supervisor_gate=supervisor_gate,
        draft_intake=draft_intake,
        closed_loop_evidence=closed_loop_evidence,
    )

    assert dashboard["status_summary"]["status"] == "blocked_by_semantic_gate"
    assert dashboard["status_summary"]["gate_state"] == "blocked"
    assert dashboard["status_summary"]["closed_loop_status"] == "no_candidates"
    assert dashboard["status_summary"]["required_human_action"] == (
        "resolve_blocking_ontology_semantic_findings"
    )


def test_ontology_review_dashboard_rejects_missing_gate_item_ids() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    supervisor_gate = json.loads(json.dumps(surfaces["supervisor_semantic_gate"]))
    supervisor_gate["gate"]["blocking_item_ids"].append("semantic-finding-missing")

    with pytest.raises(ValueError, match="blocking_item_ids"):
        module.build_ontology_review_dashboard(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            review_surface=surfaces["semantic_review_surface"],
            supervisor_gate=supervisor_gate,
            draft_intake=surfaces["ontology_delta_draft_intake"],
            closed_loop_evidence=surfaces["ontology_closed_loop_evidence"],
        )


def test_ontology_review_dashboard_uses_gate_action_for_review_pending_no_candidates() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    review_surface = json.loads(json.dumps(surfaces["semantic_review_surface"]))
    supervisor_gate = json.loads(json.dumps(surfaces["supervisor_semantic_gate"]))
    draft_intake = json.loads(json.dumps(surfaces["ontology_delta_draft_intake"]))
    closed_loop_evidence = json.loads(json.dumps(surfaces["ontology_closed_loop_evidence"]))

    review_surface["review_items"] = [
        item
        for item in review_surface["review_items"]
        if item["item_id"] == "semantic-finding-casfunction"
    ]
    review_surface["blocking_findings"] = []
    review_surface["delta_candidates"] = []
    review_surface["summary"]["blocking_count"] = 0
    review_surface["summary"]["review_required_count"] = 1
    review_surface["summary"]["candidate_count"] = 0
    supervisor_gate["gate"] = {
        "gate_state": "review_pending",
        "outcome": "semantic_review_pending",
        "required_human_action": "review_ontology_semantic_items",
        "blocking_item_ids": [],
        "review_required_item_ids": ["semantic-finding-casfunction"],
        "candidate_item_ids": [],
    }
    draft_intake["gate"] = json.loads(json.dumps(supervisor_gate["gate"]))
    draft_intake["draft_requests"] = []
    draft_intake["summary"]["status"] = "no_candidates"
    draft_intake["summary"]["gate_state"] = "review_pending"
    draft_intake["summary"]["candidate_count"] = 0
    draft_intake["summary"]["draft_request_count"] = 0
    draft_intake["summary"]["required_human_action"] = "none"
    closed_loop_evidence["evidence_entries"] = []
    closed_loop_evidence["summary"]["status"] = "no_candidates"
    closed_loop_evidence["summary"]["evidence_entry_count"] = 0
    closed_loop_evidence["summary"]["pending_decision_count"] = 0
    closed_loop_evidence["summary"]["blocked_entry_count"] = 0
    closed_loop_evidence["summary"]["required_human_action"] = "none"

    dashboard = module.build_ontology_review_dashboard(
        semantic_policy,
        semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
        review_surface=review_surface,
        supervisor_gate=supervisor_gate,
        draft_intake=draft_intake,
        closed_loop_evidence=closed_loop_evidence,
    )

    assert dashboard["status_summary"]["status"] == "review_pending"
    assert dashboard["status_summary"]["closed_loop_status"] == "no_candidates"
    assert dashboard["status_summary"]["required_human_action"] == (
        "review_ontology_semantic_items"
    )


def test_ontology_owner_decision_report_builds_matched_pending_decisions() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    closed_loop_evidence = json.loads(json.dumps(surfaces["ontology_closed_loop_evidence"]))
    cas_entry = closed_loop_evidence["evidence_entries"][0]
    cas_entry["evidence_state"] = "pending_ontology_owner_decision"
    cas_entry["source_intake_state"] = "awaiting_ontology_owner_review"
    cas_entry["required_human_action"] = "collect_ontology_owner_delta_decisions"
    legacy_entry = json.loads(json.dumps(cas_entry))
    legacy_entry["candidate_id"] = "ontology-delta-candidate-examcalc-legacyterm"
    legacy_entry["intake_id"] = (
        "ontology-delta-draft-intake-ontology-delta-candidate-examcalc-legacyterm"
    )
    legacy_entry["evidence_id"] = (
        "ontology-closed-loop-evidence-ontology-delta-candidate-examcalc-legacyterm"
    )
    legacy_entry["term"] = "LegacyTerm"
    closed_loop_evidence["evidence_entries"].append(legacy_entry)
    closed_loop_evidence["summary"]["status"] = "pending_ontology_owner_decision"
    closed_loop_evidence["summary"]["evidence_entry_count"] = 2
    closed_loop_evidence["summary"]["pending_decision_count"] = 2
    closed_loop_evidence["summary"]["blocked_entry_count"] = 0
    closed_loop_evidence["summary"]["required_human_action"] = (
        "collect_ontology_owner_delta_decisions"
    )

    report = module.build_ontology_owner_decision_report(
        semantic_policy,
        semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
        closed_loop_evidence=closed_loop_evidence,
    )

    assert report["summary"] == {
        "status": "decisions_available",
        "decision_count": 2,
        "accepted_count": 1,
        "rejected_count": 1,
        "clarification_count": 0,
        "ignored_decision_count": 0,
        "next_gap": "build_ontology_decision_import_preview",
    }
    assert report["ignored_decisions"] == []
    decisions = {entry["decision_id"]: entry for entry in report["decisions"]}
    accepted = decisions["ontology-owner-decision-accept-casfunction"]
    assert accepted["candidate_id"] == "ontology-delta-candidate-examcalc-casfunction"
    assert accepted["decision_state"] == "accepted"
    assert accepted["accepted_ontology_delta"] is True
    assert accepted["source_evidence_state"] == "pending_ontology_owner_decision"
    assert accepted["source_intake_state"] == "awaiting_ontology_owner_review"
    assert accepted["imports_into_specgraph"] is False
    assert accepted["closes_semantic_gate"] is False
    assert accepted["mutates_canonical_specs"] is False
    rejected = decisions["ontology-owner-decision-reject-legacyterm"]
    assert rejected["decision_state"] == "rejected"
    assert rejected["accepted_ontology_delta"] is False


def test_ontology_decision_import_preview_builds_pending_owner_decision_preview() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    closed_loop_evidence = json.loads(json.dumps(surfaces["ontology_closed_loop_evidence"]))
    cas_entry = closed_loop_evidence["evidence_entries"][0]
    cas_entry["evidence_state"] = "pending_ontology_owner_decision"
    cas_entry["source_intake_state"] = "awaiting_ontology_owner_review"
    cas_entry["required_human_action"] = "collect_ontology_owner_delta_decisions"
    legacy_entry = json.loads(json.dumps(cas_entry))
    legacy_entry["candidate_id"] = "ontology-delta-candidate-examcalc-legacyterm"
    legacy_entry["intake_id"] = (
        "ontology-delta-draft-intake-ontology-delta-candidate-examcalc-legacyterm"
    )
    legacy_entry["evidence_id"] = (
        "ontology-closed-loop-evidence-ontology-delta-candidate-examcalc-legacyterm"
    )
    legacy_entry["term"] = "LegacyTerm"
    closed_loop_evidence["evidence_entries"].append(legacy_entry)
    closed_loop_evidence["summary"]["status"] = "pending_ontology_owner_decision"
    closed_loop_evidence["summary"]["evidence_entry_count"] = 2
    closed_loop_evidence["summary"]["pending_decision_count"] = 2
    closed_loop_evidence["summary"]["blocked_entry_count"] = 0
    closed_loop_evidence["summary"]["required_human_action"] = (
        "collect_ontology_owner_delta_decisions"
    )
    owner_decision_report = module.build_ontology_owner_decision_report(
        semantic_policy,
        semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
        closed_loop_evidence=closed_loop_evidence,
    )
    dashboard = json.loads(json.dumps(surfaces["ontology_review_dashboard"]))
    dashboard["status_summary"]["status"] = "pending_ontology_owner_decision"
    dashboard["status_summary"]["gate_state"] = "review_pending"
    dashboard["status_summary"]["closed_loop_status"] = "pending_ontology_owner_decision"
    dashboard["status_summary"]["pending_decision_count"] = 2
    dashboard["status_summary"]["blocked_entry_count"] = 0
    dashboard["status_summary"]["evidence_entry_count"] = 2
    dashboard["status_summary"]["required_human_action"] = "collect_ontology_owner_delta_decisions"
    dashboard["closed_loop_entries"] = json.loads(
        json.dumps(closed_loop_evidence["evidence_entries"])
    )

    preview = module.build_ontology_decision_import_preview(
        semantic_policy,
        semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
        dashboard=dashboard,
        owner_decision_report=owner_decision_report,
    )

    assert preview["summary"] == {
        "status": "ready_for_operator_review",
        "preview_count": 2,
        "accepted_count": 1,
        "rejected_count": 1,
        "clarification_count": 0,
        "importable_count": 1,
        "blocked_count": 0,
        "unmatched_count": 0,
        "ignored_decision_count": 0,
        "next_gap": "build_specspace_owner_decision_review_surface",
    }
    previews = {entry["decision_id"]: entry for entry in preview["decision_import_previews"]}
    accepted = previews["ontology-owner-decision-accept-casfunction"]
    assert accepted["preview_state"] == "ready_for_operator_review"
    assert accepted["import_recommended"] is True
    assert accepted["imports_into_specgraph"] is False
    assert accepted["matched_evidence_state"] == "pending_ontology_owner_decision"
    rejected = previews["ontology-owner-decision-reject-legacyterm"]
    assert rejected["preview_state"] == "rejected_by_owner"
    assert rejected["import_recommended"] is False
    assert preview["ignored_owner_decisions"] == []


def test_ontology_semantic_review_surface_rejects_authority_expansion(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["semantic_review_surface_contract"]["consumer_boundary"][
        "may_mutate_canonical_specs"
    ] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="may_mutate_canonical_specs"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_supervisor_semantic_gate_rejects_policy_authority_expansion(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["supervisor_semantic_gate_contract"]["consumer_boundary"][
        "may_execute_prompt_agent"
    ] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="may_execute_prompt_agent"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_supervisor_semantic_gate_rejects_source_authority_expansion() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    review_surface = json.loads(json.dumps(surfaces["semantic_review_surface"]))
    review_surface["consumer_boundary"]["may_execute_prompt_agent"] = True

    with pytest.raises(ValueError, match="may_execute_prompt_agent"):
        module.build_ontology_supervisor_semantic_gate(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            review_surface=review_surface,
        )


def test_ontology_supervisor_semantic_gate_rejects_source_supervisor_authority() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    review_surface = json.loads(json.dumps(surfaces["semantic_review_surface"]))
    review_surface["authority_boundary"]["supervisor_semantic_gate_is_authority"] = True

    with pytest.raises(ValueError, match="supervisor_semantic_gate_is_authority"):
        module.build_ontology_supervisor_semantic_gate(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            review_surface=review_surface,
        )


def test_ontology_supervisor_semantic_gate_rejects_stale_blocking_summary() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    review_surface = json.loads(json.dumps(surfaces["semantic_review_surface"]))
    review_surface["summary"]["blocking_count"] = 1
    for item in review_surface["review_items"]:
        if item["review_state"] == "blocked":
            item["review_state"] = "needs_review"

    with pytest.raises(ValueError, match="blocking_count"):
        module.build_ontology_supervisor_semantic_gate(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            review_surface=review_surface,
        )


def test_ontology_delta_draft_intake_rejects_policy_authority_expansion(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["ontology_delta_draft_intake_contract"]["consumer_boundary"][
        "may_write_ontology_package"
    ] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="may_write_ontology_package"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_delta_draft_intake_rejects_source_gate_authority_expansion() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    supervisor_gate = json.loads(json.dumps(surfaces["supervisor_semantic_gate"]))
    supervisor_gate["consumer_boundary"]["may_mutate_canonical_specs"] = True

    with pytest.raises(ValueError, match="may_mutate_canonical_specs"):
        module.build_ontology_delta_draft_intake(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            review_packet=surfaces["ontology_delta_candidate_review_packet"],
            supervisor_gate=supervisor_gate,
        )


def test_ontology_closed_loop_evidence_rejects_policy_authority_expansion(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["ontology_closed_loop_evidence_contract"]["consumer_boundary"][
        "may_close_semantic_gate"
    ] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="may_close_semantic_gate"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_closed_loop_evidence_rejects_source_intake_authority_expansion() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    draft_intake = json.loads(json.dumps(surfaces["ontology_delta_draft_intake"]))
    draft_intake["consumer_boundary"]["may_write_ontology_package"] = True

    with pytest.raises(ValueError, match="may_write_ontology_package"):
        module.build_ontology_closed_loop_evidence(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            draft_intake=draft_intake,
        )


def test_ontology_closed_loop_evidence_rejects_source_request_authority_expansion() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    draft_intake = json.loads(json.dumps(surfaces["ontology_delta_draft_intake"]))
    draft_intake["draft_requests"][0]["writes_ontology_package"] = True

    with pytest.raises(ValueError, match=r"draft_requests\[0\]\.writes_ontology_package"):
        module.build_ontology_closed_loop_evidence(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            draft_intake=draft_intake,
        )


def test_ontology_closed_loop_evidence_rejects_unknown_source_intake_state() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    draft_intake = json.loads(json.dumps(surfaces["ontology_delta_draft_intake"]))
    draft_intake["draft_requests"][0]["intake_state"] = "awaiting-owner-review"

    with pytest.raises(ValueError, match=r"draft_requests\[0\]\.intake_state"):
        module.build_ontology_closed_loop_evidence(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            draft_intake=draft_intake,
        )


def test_ontology_review_dashboard_rejects_policy_authority_expansion(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["ontology_review_dashboard_contract"]["consumer_boundary"][
        "may_import_owner_decision"
    ] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="may_import_owner_decision"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_review_dashboard_rejects_source_decision_authority() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    closed_loop_evidence = json.loads(json.dumps(surfaces["ontology_closed_loop_evidence"]))
    closed_loop_evidence["evidence_entries"][0]["accepted_ontology_delta"] = True

    with pytest.raises(ValueError, match=r"evidence_entries\[0\]\.accepted_ontology_delta"):
        module.build_ontology_review_dashboard(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            review_surface=surfaces["semantic_review_surface"],
            supervisor_gate=surfaces["supervisor_semantic_gate"],
            draft_intake=surfaces["ontology_delta_draft_intake"],
            closed_loop_evidence=closed_loop_evidence,
        )


def test_ontology_owner_decision_report_rejects_policy_import_authority(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["ontology_owner_decision_report_contract"]["consumer_boundary"][
        "may_import_into_specgraph"
    ] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="may_import_into_specgraph"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_owner_decision_report_rejects_inconsistent_accepted_flag(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["owner_decision_fixture"]["decisions"][1]["accepted_ontology_delta"] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="accepted_ontology_delta"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_decision_import_preview_rejects_policy_apply_authority(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["ontology_decision_import_preview_contract"]["consumer_boundary"][
        "may_apply_preview"
    ] = True
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="may_apply_preview"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_decision_import_preview_rejects_source_import_authority() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    owner_decision_report = json.loads(json.dumps(surfaces["ontology_owner_decision_report"]))
    owner_decision_report["decisions"] = [
        {
            "decision_id": "ontology-owner-decision-accept-casfunction",
            "candidate_id": "ontology-delta-candidate-examcalc-casfunction",
            "intake_id": (
                "ontology-delta-draft-intake-ontology-delta-candidate-examcalc-casfunction"
            ),
            "decision_state": "accepted",
            "ontology_decision_ref": (
                "ontology-decision://edu.university.examcalc/0.1.0/casfunction/accepted"
            ),
            "decided_by": "ontology-owner",
            "decided_at": "2026-06-13T00:00:00Z",
            "accepted_ontology_delta": True,
            "source_evidence_id": (
                "ontology-closed-loop-evidence-ontology-delta-candidate-examcalc-casfunction"
            ),
            "source_evidence_state": "pending_ontology_owner_decision",
            "source_intake_state": "awaiting_ontology_owner_review",
            "imports_into_specgraph": False,
            "closes_semantic_gate": False,
            "mutates_canonical_specs": False,
        }
    ]
    owner_decision_report["decisions"][0]["imports_into_specgraph"] = True

    with pytest.raises(ValueError, match=r"decisions\[0\]\.imports_into_specgraph"):
        module.build_ontology_decision_import_preview(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            dashboard=surfaces["ontology_review_dashboard"],
            owner_decision_report=owner_decision_report,
        )


def test_ontology_decision_import_preview_rejects_source_artifact_mismatch() -> None:
    module = load_ontology_imports_module()
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    owner_decision_report = json.loads(json.dumps(surfaces["ontology_owner_decision_report"]))
    owner_decision_report["source_artifacts"]["ontology_closed_loop_evidence"] = (
        "runs/other_closed_loop_evidence.json"
    )

    with pytest.raises(ValueError, match="ontology_closed_loop_evidence"):
        module.build_ontology_decision_import_preview(
            semantic_policy,
            semantic_policy_path=ROOT / "tools" / "ontology_semantic_control_policy.json",
            dashboard=surfaces["ontology_review_dashboard"],
            owner_decision_report=owner_decision_report,
        )


def test_ontology_decision_import_preview_rejects_ready_non_accepted_decision() -> None:
    module = load_ontology_imports_module()
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    preview = json.loads(json.dumps(surfaces["ontology_decision_import_preview"]))
    preview["summary"]["status"] = "ready_for_operator_review"
    preview["summary"]["preview_count"] = 1
    preview["summary"]["rejected_count"] = 1
    preview["summary"]["importable_count"] = 1
    preview["decision_import_previews"] = [
        {
            "preview_id": "ontology-decision-import-preview-rejected-ready",
            "decision_id": "ontology-owner-decision-reject-legacyterm",
            "candidate_id": "ontology-delta-candidate-examcalc-legacyterm",
            "intake_id": (
                "ontology-delta-draft-intake-ontology-delta-candidate-examcalc-legacyterm"
            ),
            "decision_state": "rejected",
            "ontology_decision_ref": (
                "ontology-decision://edu.university.examcalc/0.1.0/legacyterm/rejected"
            ),
            "decided_by": "ontology-owner",
            "decided_at": "2026-06-13T00:00:00Z",
            "reason": "",
            "accepted_ontology_delta": False,
            "matched_closed_loop_evidence_id": (
                "ontology-closed-loop-evidence-ontology-delta-candidate-examcalc-legacyterm"
            ),
            "matched_source_intake_state": "awaiting_ontology_owner_review",
            "matched_evidence_state": "pending_ontology_owner_decision",
            "preview_state": "ready_for_operator_review",
            "required_human_action": "operator_review_ontology_owner_decision",
            "import_recommended": True,
            "imports_into_specgraph": False,
            "closes_semantic_gate": False,
            "mutates_canonical_specs": False,
            "writes_ontology_package": False,
            "updates_ontology_lockfile": False,
        }
    ]

    with pytest.raises(ValueError, match="accepted decision"):
        module.require_ontology_decision_import_preview(preview)


def test_ontology_decision_import_preview_rejects_ready_without_evidence_match() -> None:
    module = load_ontology_imports_module()
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    preview = json.loads(json.dumps(surfaces["ontology_decision_import_preview"]))
    preview["summary"]["status"] = "ready_for_operator_review"
    preview["summary"]["preview_count"] = 1
    preview["summary"]["accepted_count"] = 1
    preview["summary"]["importable_count"] = 1
    preview["decision_import_previews"] = [
        {
            "preview_id": "ontology-decision-import-preview-accepted-ready",
            "decision_id": "ontology-owner-decision-accept-casfunction",
            "candidate_id": "ontology-delta-candidate-examcalc-casfunction",
            "intake_id": (
                "ontology-delta-draft-intake-ontology-delta-candidate-examcalc-casfunction"
            ),
            "decision_state": "accepted",
            "ontology_decision_ref": (
                "ontology-decision://edu.university.examcalc/0.1.0/casfunction/accepted"
            ),
            "decided_by": "ontology-owner",
            "decided_at": "2026-06-13T00:00:00Z",
            "reason": "",
            "accepted_ontology_delta": True,
            "matched_closed_loop_evidence_id": "",
            "matched_source_intake_state": "awaiting_ontology_owner_review",
            "matched_evidence_state": "pending_ontology_owner_decision",
            "preview_state": "ready_for_operator_review",
            "required_human_action": "operator_review_ontology_owner_decision",
            "import_recommended": True,
            "imports_into_specgraph": False,
            "closes_semantic_gate": False,
            "mutates_canonical_specs": False,
            "writes_ontology_package": False,
            "updates_ontology_lockfile": False,
        }
    ]

    with pytest.raises(ValueError, match="matched_closed_loop_evidence_id"):
        module.require_ontology_decision_import_preview(preview)


def test_ontology_owner_decision_report_requires_decision_identity_fields() -> None:
    module = load_ontology_imports_module()
    surfaces = module.build_ontology_import_surfaces(FIXTURE)
    report = json.loads(json.dumps(surfaces["ontology_owner_decision_report"]))
    report["decisions"] = [
        {
            "decision_state": "accepted",
            "accepted_ontology_delta": True,
            "imports_into_specgraph": False,
            "closes_semantic_gate": False,
            "mutates_canonical_specs": False,
        }
    ]

    with pytest.raises(ValueError, match=r"decisions\[0\]\.decision_id"):
        module.require_ontology_owner_decision_report(report)


def test_ontology_delta_candidate_review_packet_uses_policy_review_action_order(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["ontology_delta_candidate_review_packet_contract"]["review_actions"] = [
        "request_clarification",
        "reject_candidate",
        "approve_for_ontology_package_draft",
    ]
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    surfaces = module.build_ontology_import_surfaces(
        fixture_path,
        policy_path=policy_path,
        semantic_policy_path=semantic_policy_path,
    )

    assert [
        action["action"]
        for action in surfaces["ontology_delta_candidate_review_packet"]["review_actions"]
    ] == [
        "request_clarification",
        "reject_candidate",
        "approve_for_ontology_package_draft",
    ]


def test_ontology_delta_candidate_review_packet_rejects_unsupported_review_action(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["ontology_delta_candidate_review_packet_contract"]["review_actions"].append(
        "auto_apply_candidate"
    )
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match="unsupported action"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


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
    semantic_policy["repository_layout"]["ontology_delta_candidate_review_packet"] = (
        "runs/custom_delta_candidate_review_packet.json"
    )
    semantic_policy["repository_layout"]["semantic_context_pack"] = (
        "runs/custom_semantic_context_pack.json"
    )
    semantic_policy["repository_layout"]["semantic_lint_input"] = (
        "runs/custom_semantic_lint_input.json"
    )
    semantic_policy["repository_layout"]["semantic_lint_report"] = (
        "runs/custom_semantic_lint_report.json"
    )
    semantic_policy["repository_layout"]["semantic_review_surface"] = (
        "runs/custom_semantic_review_surface.json"
    )
    semantic_policy["repository_layout"]["supervisor_semantic_gate"] = (
        "runs/custom_supervisor_semantic_gate.json"
    )
    semantic_policy["repository_layout"]["ontology_delta_draft_intake"] = (
        "runs/custom_delta_draft_intake.json"
    )
    semantic_policy["repository_layout"]["ontology_closed_loop_evidence"] = (
        "runs/custom_closed_loop_evidence.json"
    )
    semantic_policy["repository_layout"]["ontology_review_dashboard"] = (
        "runs/custom_ontology_review_dashboard.json"
    )
    semantic_policy["repository_layout"]["ontology_owner_decision_report"] = (
        "runs/custom_ontology_owner_decision_report.json"
    )
    semantic_policy["repository_layout"]["ontology_decision_import_preview"] = (
        "runs/custom_ontology_decision_import_preview.json"
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
    gate = surfaces["supervisor_semantic_gate"]
    assert gate["typed_invocation_boundary"]["input_artifact"] == (
        "runs/custom_semantic_review_surface.json"
    )
    assert gate["typed_invocation_boundary"]["output_artifact"] == (
        "runs/custom_supervisor_semantic_gate.json"
    )
    assert gate["source_artifacts"]["semantic_review_surface"] == (
        "runs/custom_semantic_review_surface.json"
    )
    assert gate["output_artifact"] == "runs/custom_supervisor_semantic_gate.json"
    written = module.write_ontology_import_surfaces(
        surfaces,
        policy_path=policy_path,
        out_dir=tmp_path,
    )

    written_paths = {path.relative_to(tmp_path).as_posix() for path in written}
    assert "runs/custom_delta_candidate_review_packet.json" in written_paths
    assert "runs/custom_semantic_context_pack.json" in written_paths
    assert "runs/custom_semantic_lint_input.json" in written_paths
    assert "runs/custom_semantic_lint_report.json" in written_paths
    assert "runs/custom_semantic_review_surface.json" in written_paths
    assert "runs/custom_supervisor_semantic_gate.json" in written_paths
    assert "runs/custom_delta_draft_intake.json" in written_paths
    assert "runs/custom_closed_loop_evidence.json" in written_paths
    assert "runs/custom_ontology_review_dashboard.json" in written_paths
    assert "runs/custom_ontology_owner_decision_report.json" in written_paths
    assert "runs/custom_ontology_decision_import_preview.json" in written_paths
    assert "runs/custom_semantic_lint_smoke.json" in written_paths
    assert not (tmp_path / "runs" / "ontology_delta_candidate_review_packet.json").exists()
    assert not (tmp_path / "runs" / "ontology_semantic_context_pack.json").exists()
    assert not (tmp_path / "runs" / "ontology_semantic_lint_input.json").exists()
    assert not (tmp_path / "runs" / "ontology_semantic_lint_report.json").exists()
    assert not (tmp_path / "runs" / "ontology_semantic_review_surface.json").exists()
    assert not (tmp_path / "runs" / "ontology_supervisor_semantic_gate.json").exists()
    assert not (tmp_path / "runs" / "ontology_delta_draft_intake.json").exists()
    assert not (tmp_path / "runs" / "ontology_closed_loop_evidence.json").exists()
    assert not (tmp_path / "runs" / "ontology_review_dashboard.json").exists()
    assert not (tmp_path / "runs" / "ontology_owner_decision_report.json").exists()
    assert not (tmp_path / "runs" / "ontology_decision_import_preview.json").exists()
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


def test_ontology_semantic_lint_report_rejects_non_string_source_ref(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["semantic_lint_input_sources"]["source_outputs"][0]["terms"][0][
        "source_ref"
    ] = 123
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    with pytest.raises(ValueError, match=r"terms\[0\]\.source_ref"):
        module.build_ontology_import_surfaces(
            fixture_path,
            policy_path=policy_path,
            semantic_policy_path=semantic_policy_path,
        )


def test_ontology_semantic_lint_report_treats_none_source_ref_as_absent(
    tmp_path: Path,
) -> None:
    module = load_ontology_imports_module()
    module.ROOT = tmp_path
    fixture_path = write_temp_fixture(tmp_path, load_fixture_payload())
    policy_path = write_temp_policy(tmp_path)
    semantic_policy = json.loads(
        (ROOT / "tools" / "ontology_semantic_control_policy.json").read_text()
    )
    semantic_policy["semantic_lint_input_sources"]["source_outputs"][0]["terms"][0][
        "source_ref"
    ] = None
    semantic_policy_path = write_temp_semantic_control_policy(tmp_path, semantic_policy)

    surfaces = module.build_ontology_import_surfaces(
        fixture_path,
        policy_path=policy_path,
        semantic_policy_path=semantic_policy_path,
    )

    finding = surfaces["semantic_lint_report"]["findings"][0]
    assert finding["term"] == "Exam"
    assert finding["source_ref"] is None
    assert finding["classification"] == "unknown_term"


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
        "runs/ontology_semantic_lint_input.json": "ontology_semantic_lint_input",
        "runs/ontology_semantic_lint_report.json": "ontology_semantic_lint_report",
        "runs/ontology_delta_candidate_review_packet.json": (
            "ontology_delta_candidate_review_packet"
        ),
        "runs/ontology_semantic_review_surface.json": "ontology_semantic_review_surface",
        "runs/ontology_supervisor_semantic_gate.json": "ontology_supervisor_semantic_gate",
        "runs/ontology_delta_draft_intake.json": "ontology_delta_draft_intake",
        "runs/ontology_closed_loop_evidence.json": "ontology_closed_loop_evidence",
        "runs/ontology_review_dashboard.json": "ontology_review_dashboard",
        "runs/ontology_owner_decision_report.json": "ontology_owner_decision_report",
        "runs/ontology_decision_import_preview.json": "ontology_decision_import_preview",
        "runs/ontology_semantic_lint_smoke.json": "ontology_semantic_lint_smoke",
    }
    for relative_path, artifact_kind in expected.items():
        payload = json.loads((ROOT / relative_path).read_text())
        assert payload["artifact_kind"] == artifact_kind
        expected_proposal_id = {
            "ontology_delta_candidate_review_packet": "0106",
            "ontology_semantic_context_pack": "0104",
            "ontology_semantic_lint_input": "0116",
            "ontology_semantic_lint_report": "0105",
            "ontology_semantic_review_surface": "0108",
            "ontology_supervisor_semantic_gate": "0109",
            "ontology_delta_draft_intake": "0110",
            "ontology_closed_loop_evidence": "0111",
            "ontology_review_dashboard": "0113",
            "ontology_owner_decision_report": "0114",
            "ontology_decision_import_preview": "0115",
            "ontology_semantic_lint_smoke": "0103",
        }.get(artifact_kind, "0060")
        assert payload["proposal_id"] == expected_proposal_id
        assert payload["canonical_mutations_allowed"] is False
        assert payload["tracked_artifacts_written"] is False


def test_supervisor_build_ontology_supervisor_semantic_gate_command() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "tools/supervisor.py",
            "--build-ontology-supervisor-semantic-gate",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["artifact_kind"] == "ontology_supervisor_semantic_gate_report"
    assert payload["summary"]["gate_state"] == "blocked"
    assert payload["summary"]["required_human_action"] == (
        "resolve_blocking_ontology_semantic_findings"
    )
    assert payload["summary"]["artifact_path"] == "runs/ontology_supervisor_semantic_gate.json"
    written_paths = set(payload["written_artifacts"]["paths"])
    assert "runs/ontology_semantic_review_surface.json" in written_paths
    assert "runs/ontology_supervisor_semantic_gate.json" in written_paths
    assert "runs/ontology_delta_draft_intake.json" in written_paths
    assert "runs/ontology_closed_loop_evidence.json" in written_paths


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
    assert "ontology_delta_candidate_review_packet" not in surfaces
    assert "semantic_context_pack" not in surfaces
    assert "semantic_lint_report" not in surfaces
    assert "semantic_review_surface" not in surfaces
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


def test_proposal_0105_runtime_registry_tracks_lint_report() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0105"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert (
        "tools/ontology_semantic_control_policy.json",
        "semantic_lint_report_contract",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def build_ontology_semantic_lint_report(",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_semantic_lint_report_builds_review_findings(",
    ) in validation_markers
    assert (
        "tools/README.md",
        "runs/ontology_semantic_lint_report.json",
    ) in observation_markers


def test_proposal_0116_runtime_registry_tracks_lint_input() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0116"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert (
        "tools/ontology_semantic_control_policy.json",
        "semantic_lint_input_contract",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def build_ontology_semantic_lint_input(",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_semantic_lint_input_extracts_terms_from_proposal_output(",
    ) in validation_markers
    assert (
        "tools/README.md",
        "runs/ontology_semantic_lint_input.json",
    ) in observation_markers


def test_proposal_0106_runtime_registry_tracks_delta_candidate_packet() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0106"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert (
        "tools/ontology_semantic_control_policy.json",
        "ontology_delta_candidate_review_packet_contract",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def build_ontology_delta_candidate_review_packet(",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_delta_candidate_review_packet_builds_review_packet(",
    ) in validation_markers
    assert (
        "tools/README.md",
        "runs/ontology_delta_candidate_review_packet.json",
    ) in observation_markers


def test_proposal_0108_runtime_registry_tracks_semantic_review_surface() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0108"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert (
        "tools/ontology_semantic_control_policy.json",
        "semantic_review_surface_contract",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def build_ontology_semantic_review_surface(",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_semantic_review_surface_builds_specspace_surface(",
    ) in validation_markers
    assert (
        "tools/README.md",
        "runs/ontology_semantic_review_surface.json",
    ) in observation_markers


def test_proposal_0109_runtime_registry_tracks_supervisor_semantic_gate() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0109"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert (
        "tools/ontology_semantic_control_policy.json",
        "supervisor_semantic_gate_contract",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def build_ontology_supervisor_semantic_gate(",
    ) in runtime_markers
    assert (
        "tools/supervisor.py",
        "--build-ontology-supervisor-semantic-gate",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_supervisor_semantic_gate_builds_gate_evidence(",
    ) in validation_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_supervisor_build_ontology_supervisor_semantic_gate_command(",
    ) in validation_markers
    assert (
        "tools/README.md",
        "runs/ontology_supervisor_semantic_gate.json",
    ) in observation_markers
    assert (
        "docs/supervisor_manual.md",
        "--build-ontology-supervisor-semantic-gate",
    ) in observation_markers


def test_proposal_0110_runtime_registry_tracks_delta_draft_intake() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0110"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert (
        "tools/ontology_semantic_control_policy.json",
        "ontology_delta_draft_intake_contract",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def build_ontology_delta_draft_intake(",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_delta_draft_intake_builds_review_only_intake(",
    ) in validation_markers
    assert (
        "tests/test_supervisor.py",
        "def test_supervisor_output_summary_includes_ontology_gate_report(",
    ) in validation_markers
    assert (
        "tools/README.md",
        "runs/ontology_delta_draft_intake.json",
    ) in observation_markers
    assert (
        "docs/supervisor_manual.md",
        "runs/ontology_delta_draft_intake.json",
    ) in observation_markers


def test_proposal_0111_runtime_registry_tracks_closed_loop_evidence() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0111"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert (
        "tools/ontology_semantic_control_policy.json",
        "ontology_closed_loop_evidence_contract",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def build_ontology_closed_loop_evidence(",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_closed_loop_evidence_builds_specgraph_evidence_surface(",
    ) in validation_markers
    assert (
        "tools/README.md",
        "runs/ontology_closed_loop_evidence.json",
    ) in observation_markers
    assert (
        "docs/supervisor_manual.md",
        "runs/ontology_closed_loop_evidence.json",
    ) in observation_markers


def test_proposal_0115_runtime_registry_tracks_decision_import_preview() -> None:
    registry = json.loads((ROOT / "tools" / "proposal_runtime_registry.json").read_text())
    entries = {entry["proposal_id"]: entry for entry in registry if isinstance(entry, dict)}
    proposal = entries["0115"]

    runtime_markers = {(item["path"], item["pattern"]) for item in proposal["runtime_markers"]}
    validation_markers = {
        (item["path"], item["pattern"]) for item in proposal["validation_markers"]
    }
    observation_markers = {
        (item["path"], item["pattern"]) for item in proposal["observation_markers"]
    }

    assert (
        "tools/ontology_semantic_control_policy.json",
        "ontology_decision_import_preview_contract",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def build_ontology_decision_import_preview(",
    ) in runtime_markers
    assert (
        "tools/ontology_imports.py",
        "def require_ontology_decision_import_preview(",
    ) in runtime_markers
    assert (
        "tests/test_ontology_import_policy.py",
        "def test_ontology_decision_import_preview_builds_read_only_preview(",
    ) in validation_markers
    assert (
        "tools/README.md",
        "runs/ontology_decision_import_preview.json",
    ) in observation_markers
    assert (
        "docs/supervisor_manual.md",
        "runs/ontology_decision_import_preview.json",
    ) in observation_markers
