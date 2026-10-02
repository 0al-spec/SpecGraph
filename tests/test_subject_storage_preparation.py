"""Protect review provenance and exact membership without canonical writes."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from spec_yaml import load_yaml_text  # noqa: E402
from subject_read_model import RevisionSelection  # noqa: E402
from subject_read_model_io import (  # noqa: E402
    SubjectDocumentError,
    parse_subject_index,
    parse_subject_ref,
)


@pytest.fixture()
def preparation() -> tuple[dict, list[dict], dict, dict]:
    manifest = load_yaml_text(
        (ROOT / "docs/reviews/0221_subject_storage/manifest.yaml").read_text()
    )
    candidates = [load_yaml_text((ROOT / path).read_text()) for path in manifest["candidate_paths"]]
    mapping = json.loads((ROOT / manifest["mapping_packet"]).read_text())
    contract = load_yaml_text((ROOT / manifest["storage_contract"]).read_text())
    return manifest, candidates, mapping, contract


def test_preparation_has_no_adoption_or_materialization_provenance(preparation) -> None:
    manifest, candidates, _, contract = preparation
    assert contract["gate_state"] == "review_pending"
    assert contract["refines"] == ["SG-SPEC-0068"]
    assert contract["specification"]["adoption_boundary"]["schema_approval_record"] is None
    assert set(manifest["decisions"].values()) == {None}
    assert manifest["canonical_mutations_allowed"] is False
    for document in [manifest, *candidates]:
        assert document["gate_state"] == "review_pending"
        assert document["canonical_adoption"] is False
        assert document["canonical_readiness"] == "not_evaluated"
        assert document["ready_for_materialization"] is False
    for candidate in candidates:
        assert candidate["source_lane"] == "SpecDraft"
        assert candidate["adoption_fields_pending"]
        record = candidate["proposed_record"]
        assert "canonical_presence" not in record
        if record["artifact_kind"] == "subject_workspace_declaration":
            assert record["provenance"] is None
        else:
            assert record["revisions"][0]["provenance"] is None
            assert record["current_disposition"] is None
            assert record["retained_disposition_transitions"] == []


def test_candidate_shapes_and_current_projections_match_the_pending_contract(preparation) -> None:
    _, candidates, _, contract = preparation
    shapes = contract["specification"]["document_shapes"]
    shapes_by_kind = {
        shapes[name]["artifact_kind"]: shapes[name]
        for name in ("workspace_declaration", "requirement_node", "criterion_record")
    }
    workspace = next(
        c["proposed_record"]["workspace_identity"]
        for c in candidates
        if c["proposed_record"]["artifact_kind"] == "subject_workspace_declaration"
    )
    local_ids = []
    for candidate in candidates:
        record = candidate["proposed_record"]
        assert set(record) == set(shapes_by_kind[record["artifact_kind"]]["required_fields"])
        assert type(record["schema_version"]) is int and record["schema_version"] == 1
        if "subject" not in record:
            continue
        reference = parse_subject_ref(record["subject"])
        assert reference.local_subject_id == record["id"]
        assert reference.workspace_identity == workspace
        local_ids.append(reference.local_subject_id)
        assert record["current_revision"] == 1
        revision = record["revisions"][0]
        assert set(revision) == set(shapes["revision"]["required_fields"])
        assert type(revision["number"]) is int and revision["number"] == 1
        assert revision["predecessor"] is None
        assert revision["containment"] == candidate["proposed_path"]
        for name, value in revision["node_fields"].items():
            assert record[name] == value
    assert len(local_ids) == len(set(local_ids)) == 6


def test_exact_membership_is_the_reviewed_three_plus_one_partition(preparation) -> None:
    _, candidates, mapping, _ = preparation
    records = {
        c["proposed_record"]["id"]: c["proposed_record"]
        for c in candidates
        if "subject" in c["proposed_record"]
    }
    assert len(records) == 6
    claimed = []
    for requirement in mapping["proposed_requirements"]:
        record = records[requirement["candidate_node"]["id"]]
        assert record["subject"] == requirement["proposed_subject"]["subject"]
        revision = record["revisions"][0]
        assert revision["statement"] == requirement["candidate_node"]["statement"]
        assert (
            revision["acceptance_criteria_refs"]
            == requirement["proposed_revision"]["acceptance_criteria_refs"]
        )
        for value in revision["acceptance_criteria_refs"]:
            selection = RevisionSelection(
                parse_subject_ref(value["subject"]), value["mode"], value["revision"]
            )
            assert selection.mode == "exact"
            criterion = records[selection.subject.local_subject_id]
            assert criterion["subject"] == value["subject"]
            assert criterion["revisions"][0]["number"] == selection.revision
            assert criterion["revisions"][0]["acceptance_criteria_refs"] == []
            claimed.append(selection.subject.local_subject_id)
    assert len(claimed) == len(set(claimed)) == 4
    assert sorted(claimed) == sorted(
        m["source"]["subject"]["local_subject_id"] for m in mapping["criterion_mappings"]
    )


def test_source_statements_and_pending_namespace_mapping_are_retained(preparation) -> None:
    manifest, candidates, mapping, _ = preparation
    digest = hashlib.sha256((ROOT / manifest["mapping_packet"]).read_bytes()).hexdigest()
    assert manifest["mapping_packet_sha256"] == digest
    for path, expected in manifest["validation_snapshot"]["checked_file_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    source_mappings = {
        m["source"]["subject"]["local_subject_id"]: m for m in mapping["criterion_mappings"]
    }
    for candidate in candidates:
        assert candidate["preparation_provenance"]["mapping_packet_sha256"] == digest
        record = candidate["proposed_record"]
        if record["artifact_kind"] != "acceptance_criterion_record":
            continue
        source = source_mappings[record["id"]]
        assert candidate["source_mapping"] == source
        assert record["subject"] == source["proposed_destination"]["subject"]
        assert parse_subject_ref(record["subject"]) != parse_subject_ref(
            source["source"]["subject"]
        )
        assert source["same_identity_predecessor"] is None
        assert source["review"]["outcome"] == "pending"
        statement = record["revisions"][0]["statement"]
        assert statement == source["statement"]
        assert hashlib.sha256(statement.encode()).hexdigest() == source["source_statement_sha256"]


def test_snapshot_parser_rejects_candidate_envelopes(preparation) -> None:
    _, candidates, _, _ = preparation
    for candidate in candidates:
        with pytest.raises(SubjectDocumentError):
            parse_subject_index(candidate)
        with pytest.raises(
            SubjectDocumentError, match="artifact_kind must be subject_read_snapshot"
        ):
            parse_subject_index(
                {"schema_version": 1, "artifact_kind": candidate["artifact_kind"], "workspaces": []}
            )
