"""Actual approval remains distinct from preparation and subject materialization."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = "docs/reviews/0221_subject_storage_decision.json"
sys.path.insert(0, str(ROOT / "tools"))

from spec_yaml import load_yaml_text  # noqa: E402


@pytest.fixture()
def decision() -> dict:
    return json.loads((ROOT / DECISION_PATH).read_text())


def test_human_decision_binds_exact_reviewed_packet(decision) -> None:
    packet_bytes = (ROOT / decision["packet_path"]).read_bytes()
    packet = load_yaml_text(packet_bytes.decode())
    encoded = json.dumps(
        packet["approval_scope"], sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    assert decision["packet_sha256"] == hashlib.sha256(packet_bytes).hexdigest()
    assert decision["approval_scope_sha256"] == hashlib.sha256(encoded).hexdigest()
    review = decision["review"]
    assert review["approval_scope_sha256"] == decision["approval_scope_sha256"]
    assert review["reviewed_head"] == "6c88190d379b787661a47b07cf1279c25f0d585e"
    assert review["reviewed_pull_request"] == "https://github.com/0al-spec/SpecGraph/pull/752"
    assert review["reviewed_commit"] == packet["approval_scope"]["reviewed_commit"]
    assert review["provenance"]["source_quote"] == "Одобряю пакет PR #752"
    assert review["provenance"]["source"] == "current_codex_conversation"
    assert review["provenance"]["github_review_submitted"] is False
    assert review["outcome"] == "approve"
    assert review["reviewer_authority"] == "human_project_author"
    assert review["recorded_at"] >= review["decision_timestamp"]
    assert "user-message timestamp is unavailable" in review["decision_timestamp_basis"]
    assert "no additional human rationale" in review["rationale"]
    assert set(decision["decisions"]) == set(packet["decision_templates"])
    assert all(
        item == {"review_ref": DECISION_PATH + "#/review", "outcome": "approve"}
        for item in decision["decisions"].values()
    )


def test_each_exact_mapping_has_genuine_decision_attribution(decision) -> None:
    packet = load_yaml_text((ROOT / decision["packet_path"]).read_text())
    mappings = packet["approval_scope"]["criterion_mappings"]
    assert len(decision["mapping_decisions"]) == len(mappings) == 4
    for item, proposed in zip(decision["mapping_decisions"], mappings, strict=True):
        assert item["source"] == proposed["source"]
        assert item["destination"] == proposed["proposed_destination"]
        assert item["requirement_id"] == proposed["proposed_requirement_id"]
        assert item["source_statement_sha256"] == proposed["source_statement_sha256"]
        assert item["review"] == decision["review"]
        assert item["source"]["subject"] != item["destination"]["subject"]
        assert proposed["review"]["outcome"] == "pending"


def test_gate_resolution_is_attributed_without_materialization(decision) -> None:
    node = load_yaml_text((ROOT / "specs/nodes/SG-SPEC-0069.yaml").read_text())
    boundary = node["specification"]["adoption_boundary"]
    assert boundary["state"] == "human_approved"
    assert node["status"] == "specified" and node["gate_state"] == "none"
    assert node["last_gate_decision"] == "approve"
    assert DECISION_PATH in node["last_gate_note"]
    assert node["authority_class"] == node["provenance"]["authority_class"] == "authored"
    assert node["provenance"]["actor_id"] == "human:project-author"
    assert node["source_ref"] == node["provenance"]["source_ref"] == DECISION_PATH
    approved = boundary["schema_approval_record"]
    assert approved["reviewed_head"] == decision["review"]["reviewed_head"]
    assert approved["approval_scope_sha256"] == decision["approval_scope_sha256"]
    assert boundary["canonical_materialization_authorization"] is None
    assert decision["canonical_subject_adoption"] is False
    assert decision["workspace_and_id_plan"] == "approved_but_unallocated"
    assert decision["ready_for_materialization"] is False
    assert decision["canonical_readiness"] == "not_evaluated"
    for name in (
        "source_migration_authorized",
        "evidence_transfer_authorized",
        "platform_promotion_authorized",
        "trusted_runtime_receipts_created",
    ):
        assert decision[name] is False


def test_historical_reviewed_bytes_remain_verifiable(decision) -> None:
    packet = load_yaml_text((ROOT / decision["packet_path"]).read_text())
    manifest = load_yaml_text(
        (ROOT / "docs/reviews/0221_subject_storage/manifest.yaml").read_text()
    )
    for source, snapshot in decision["reviewed_snapshot_files"].items():
        expected = packet["approval_scope"]["reviewed_file_sha256"].get(
            source, manifest["validation_snapshot"]["checked_file_sha256"].get(source)
        )
        assert expected is not None
        assert hashlib.sha256((ROOT / snapshot).read_bytes()).hexdigest() == expected
    historical = load_yaml_text(
        (ROOT / decision["reviewed_snapshot_files"]["specs/nodes/SG-SPEC-0069.yaml"]).read_text()
    )
    assert historical["gate_state"] == "review_pending"
    assert historical["specification"]["adoption_boundary"]["schema_approval_record"] is None
    current = load_yaml_text((ROOT / "specs/nodes/SG-SPEC-0069.yaml").read_text())
    for field in ("storage_layout", "document_shapes", "revision_storage", "write_contract"):
        assert current["specification"][field] == historical["specification"][field]


def test_historical_candidates_and_evidence_do_not_become_approved(decision) -> None:
    manifest = load_yaml_text(
        (ROOT / "docs/reviews/0221_subject_storage/manifest.yaml").read_text()
    )
    assert set(manifest["decisions"].values()) == {None}
    for path in manifest["candidate_paths"]:
        candidate = load_yaml_text((ROOT / path).read_text())
        assert candidate["canonical_adoption"] is False
        assert candidate["ready_for_materialization"] is False
        assert candidate["gate_state"] == "review_pending"
    evidence = json.loads(
        (ROOT / "docs/reviews/0221_subject_storage_approval_evidence.json").read_text()
    )
    assert evidence["human_approval"] == "not_recorded"
    assert evidence["gate_state"] == "review_pending"
    assert decision["schema_adoption"] == "human_approved"
