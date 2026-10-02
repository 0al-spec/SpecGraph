"""Keep a human review scope exact without creating approval or canonical subjects."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = "docs/reviews/0221_subject_storage_approval.yaml"
sys.path.insert(0, str(ROOT / "tools"))

from spec_yaml import load_yaml_text  # noqa: E402
from subject_read_model_io import SubjectDocumentError, parse_subject_index  # noqa: E402


@pytest.fixture()
def packet() -> dict:
    return load_yaml_text((ROOT / PACKET_PATH).read_text())


def test_approval_packet_preserves_the_pending_human_boundary(packet) -> None:
    assert packet["artifact_kind"] == "rfc0221_subject_storage_approval_packet"
    assert packet["schema_version"] == 1
    assert packet["created_at"] == packet["prepared_at"]
    assert packet["updated_at"] >= packet["created_at"]
    assert packet["authority"] == "agent_prepared_for_human_review"
    assert packet["source_lane"] == "SpecDraft"
    assert packet["gate_state"] == "review_pending"
    assert packet["canonical_adoption"] is False
    assert packet["canonical_mutations_allowed"] is False
    assert packet["canonical_readiness"] == "not_evaluated"
    assert packet["ready_for_materialization"] is False
    assert packet["preparation_authorization"]["source_quote"] == "Ок, готовь схему"
    node = load_yaml_text((ROOT / "specs/nodes/SG-SPEC-0069.yaml").read_text())
    assert node["gate_state"] == "review_pending"
    assert node["specification"]["adoption_boundary"]["schema_approval_record"] is None
    with pytest.raises(SubjectDocumentError):
        parse_subject_index(packet)


def test_review_scope_digest_binds_the_exact_content(packet) -> None:
    encoded = json.dumps(
        packet["approval_scope"], sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    assert packet["approval_scope_sha256"] == hashlib.sha256(encoded).hexdigest()
    doc = (ROOT / "docs/reviews/0221_subject_storage_approval.md").read_text()
    assert packet["approval_scope_sha256"] in doc
    assert packet["approval_scope"]["reviewed_commit"] in doc
    assert len(packet["approval_scope"]["reviewed_commit"]) == 40
    assert packet["suggested_human_reply"] in doc


def test_reviewed_file_digests_cover_schema_manifest_mapping_and_candidates(packet) -> None:
    manifest_path = "docs/reviews/0221_subject_storage/manifest.yaml"
    manifest = load_yaml_text((ROOT / manifest_path).read_text())
    pins = packet["approval_scope"]["reviewed_file_sha256"]
    assert set(pins) == {
        manifest_path,
        manifest["storage_contract"],
        manifest["mapping_packet"],
        *manifest["candidate_paths"],
    }
    for path, digest in pins.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_review_scope_retains_the_complete_selected_physical_schema(packet) -> None:
    selected = packet["approval_scope"]["physical_schema"]
    node = load_yaml_text((ROOT / selected["path"]).read_text())
    assert selected["spec_id"] == node["id"] == "SG-SPEC-0069"
    assert selected["schema_version"] == 1
    for name in ("storage_layout", "document_shapes", "revision_storage", "write_contract"):
        assert selected[name] == node["specification"][name]
    assert "SG-SPEC-0019" in selected["governing_specs"]
    assert "SG-SPEC-0024" in selected["governing_specs"]
    assert "revision_scope" in selected["document_shapes"]["revision"]["required_fields"]


def test_approval_mapping_retains_statements_exact_pins_and_distinct_identity(packet) -> None:
    scope = packet["approval_scope"]
    mapping = json.loads((ROOT / "docs/reviews/0221_requirement_mapping_review.json").read_text())
    assert scope["criterion_mappings"] == mapping["criterion_mappings"]
    requirements = {item["subject"]["local_subject_id"]: item for item in scope["requirements"]}
    assert len(requirements) == 2
    memberships = []
    for original in mapping["proposed_requirements"]:
        item = requirements[original["candidate_node"]["id"]]
        assert item["subject"] == original["proposed_subject"]["subject"]
        assert item["mode"] == "exact" and item["revision"] == 1
        assert item["statement"] == original["candidate_node"]["statement"]
        assert item["statement_sha256"] == hashlib.sha256(item["statement"].encode()).hexdigest()
        assert (
            item["acceptance_criteria_refs"]
            == original["proposed_revision"]["acceptance_criteria_refs"]
        )
        memberships.append(len(item["acceptance_criteria_refs"]))
    assert sorted(memberships) == [1, 3]
    destination_workspace = scope["workspace_and_id_plan"]["workspace_identity"]
    for item in scope["criterion_mappings"]:
        source, destination = item["source"], item["proposed_destination"]
        assert source["mode"] == destination["mode"] == "exact"
        assert source["revision"] == destination["revision"] == 1
        assert (
            source["subject"]["workspace_identity"] != destination["subject"]["workspace_identity"]
        )
        assert destination["subject"]["workspace_identity"] == destination_workspace
        assert item["same_identity_predecessor"] is None
        assert item["review"]["outcome"] == "pending"


def test_decision_templates_contain_no_fabricated_human_provenance(packet) -> None:
    assert set(packet["decision_templates"]) == {
        "physical_schema",
        "workspace_and_id_plan",
        "requirement_membership_and_mapping",
        "bounded_implementation_authorization",
    }
    required = {
        "reviewer",
        "reviewer_authority",
        "decision_timestamp",
        "outcome",
        "rationale",
        "provenance",
        "source_quote",
    }
    for decision in packet["decision_templates"].values():
        assert set(decision) == required
        assert set(decision.values()) == {None}
    assert len(packet["mapping_decision_templates"]) == 4
    for template, mapping in zip(
        packet["mapping_decision_templates"],
        packet["approval_scope"]["criterion_mappings"],
        strict=True,
    ):
        assert template["source"] == mapping["source"]
        assert template["destination"] == mapping["proposed_destination"]
        assert template["requirement_id"] == mapping["proposed_requirement_id"]
        assert set(template["review"]) == required
        assert set(template["review"].values()) == {None}


def test_validation_evidence_is_bound_to_the_packet_and_retains_review_gate(packet) -> None:
    evidence = json.loads(
        (ROOT / "docs/reviews/0221_subject_storage_approval_evidence.json").read_text()
    )
    assert evidence["approval_scope_sha256"] == packet["approval_scope_sha256"]
    assert (
        evidence["approval_packet_sha256"]
        == hashlib.sha256((ROOT / PACKET_PATH).read_bytes()).hexdigest()
    )
    assert evidence["gate_state"] == evidence["backlog_status"] == "review_pending"
    assert evidence["next_gap"] == "resolve_review_gate"
    assert not any(evidence["spec_checks"].values())
    assert evidence["graph_reconciliation"]["changed_spec_ids"] == []
    assert evidence["canonical_adoption"] is False
    assert evidence["canonical_mutations_allowed"] is False
    assert evidence["writer_conformance"] == "not_evaluated"
