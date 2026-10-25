"""Integrity of one pending adoption scope, without synthetic human approvals."""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml

from test_intent_atoms import git, make_repo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from subject_publication import (  # noqa: E402
    DecisionSnapshot,
    PublicationGovernanceError,
    _packet,
    scope_digest,
)
from subject_read_model_io import parse_subject_ref  # noqa: E402

PACKET = "docs/reviews/0045_cn_capture/adoption/packet.json"


def load_packet():
    return json.loads((ROOT / PACKET).read_text())


def test_capture_adoption_scope_binds_two_unchanged_pending_candidates():
    packet = load_packet()
    scope = {key: value for key, value in packet.items() if key != "approval_scope_sha256"}
    assert scope_digest(scope) == packet["approval_scope_sha256"]
    assert packet["gate_state"] == "review_pending"
    assert packet["canonical_mutations_allowed"] is False
    assert not packet["canonical_adoption"] and not packet["ready_for_materialization"]
    assert packet["writer_request"] is packet["publication_authorization"] is None
    inputs = packet["inputs"]["review_tree_file_sha256"]
    assert PACKET not in inputs
    for path, expected in inputs.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    for label in ("contract_snapshot", "publication_implementation_snapshot"):
        snapshot = packet["inputs"][label]
        for path, expected in snapshot["file_sha256"].items():
            raw = DecisionSnapshot(ROOT, snapshot["commit"]).read(path)
            assert hashlib.sha256(raw).hexdigest() == expected
    assert {s["local_subject_id"] for s in packet["subjects"]} == {
        "req.cn.capture",
        "ac.cn.capture-without-kind",
    }
    assert len(packet["subjects"]) == 2
    base = DecisionSnapshot(ROOT, packet["prepared_against_commit"])
    for subject in packet["subjects"]:
        path = subject["candidate_file"]
        assert (ROOT / path).read_bytes() == base.read(path)
        candidate = yaml.safe_load((ROOT / path).read_text())
        record = candidate["proposed_record"]
        assert subject["candidate_sha256"] == inputs[path]
        assert subject["source_draft_ref"] == path + "#/proposed_record"
        assert subject["canonical_target_ref"] == candidate["proposed_path"] + "#/subject"
        assert subject["canonical_revision_selection"] == {
            "subject": record["subject"],
            "mode": "exact",
            "revision": 1,
        }
        assert subject["statement"] == record["revisions"][0]["statement"]
        assert (
            subject["candidate_statement_sha256"]
            == hashlib.sha256(subject["statement"].encode()).hexdigest()
        )
        assert subject["title"] == record["title"]
        assert subject["source_proposal_sha256"] == inputs[subject["source_proposal_ref"]]
        assert subject["subject_class"] == parse_subject_ref(record["subject"]).subject_class.value
        assert candidate["gate_state"] == "review_pending"
        assert record["current_disposition"] is None
        assert record["revisions"][0]["provenance"] is None
    requirement, criterion = packet["subjects"]
    proposal = yaml.safe_load((ROOT / requirement["source_proposal_ref"]).read_text())
    assert requirement["statement"] == proposal["atoms"]["intents"][0]["statement"]
    assert requirement["statement_relation_to_source"] == (
        "verbatim_existing_CN_CAPTURE_proposal_obligation"
    )
    assert criterion["statement_relation_to_source"] == (
        "agent_formalized_acceptance_scenario_from_proposal_context_not_verbatim"
    )
    assert requirement["requirement_membership"] == [criterion["local_subject_id"]]
    assert criterion["requirement_membership"] == []
    candidate = yaml.safe_load((ROOT / requirement["candidate_file"]).read_text())
    assert candidate["proposed_record"]["revisions"][0]["acceptance_criteria_refs"] == [
        criterion["canonical_revision_selection"]
    ]


def test_capture_adoption_transitions_and_intent_remain_preparation():
    packet = load_packet()
    lineage_path, pointer = packet["intent_nodes_ref"].split("#")
    assert pointer == "/canonical_intent_candidates"
    lineage = json.loads((ROOT / lineage_path).read_text())
    excerpt = json.loads((ROOT / "docs/reviews/0045_cn_capture/source-note.json").read_text())
    human = lineage["human_intent_records"][0]
    draft = lineage["intent_drafts"][0]
    assert human["text"] == draft["statement"] == excerpt["note"]["sources"][0]["quote"]
    assert human["original_timestamp"] is None
    assert draft["provenance"]["source_ref"] == lineage_path + "#/human_intent_records/0"
    intent = lineage["canonical_intent_candidates"][0]
    assert intent["authority_class"] == "distilled" and not intent["canonical_adoption"]
    assert intent["canonical_storage_binding"] is None
    records = packet["transition_records"]
    assert len(records) == len({r["transition_record_id"] for r in records}) == 4
    assert len({r["transition_identifier"] for r in records}) == 4
    for index, subject in enumerate(packet["subjects"]):
        ingress, canonical = records[2 * index : 2 * index + 2]
        assert ingress["promotion_edge"] == "proposal -> spec_draft"
        assert ingress["source_ref"] == subject["source_proposal_ref"]
        assert ingress["target_ref"] == subject["source_draft_ref"]
        assert ingress["intent_lineage_ref"] == lineage_path + f"#/ingress_lineages/{index}"
        origin = lineage["ingress_lineages"][index]
        assert origin["source_proposal_ref"] == ingress["source_ref"]
        assert origin["source_proposal_sha256"] == subject["source_proposal_sha256"]
        assert origin["intent_ref"] == lineage_path + "#/intent_drafts/0"
        assert origin["review"] is None
        assert canonical["promotion_edge"] == "spec_draft -> canonical_artifact"
        assert canonical["ingress_transition_id"] == ingress["transition_record_id"]
        assert canonical["source_ref"] == subject["source_draft_ref"]
        assert canonical["target_ref"] == subject["canonical_target_ref"]
        assert canonical["target_revision_selection"] == subject["canonical_revision_selection"]
    for record in records:
        assert record["gate_type"] == "review" and record["state"] == "review_pending"
        for field in (
            "reviewer_or_decider",
            "decision_timestamp",
            "outcome",
            "rationale",
            "review",
        ):
            assert record[field] is None
    (edge,) = packet["proposed_canonical_edges"]
    assert (edge["kind"], edge["source"]["kind"], edge["target"]["kind"]) == (
        "derived_from",
        "requirement",
        "intent",
    )
    assert edge["source"]["node_id"] == "req.cn.capture"
    assert edge["target"]["node_id"] == intent["id"]
    assert not edge["canonical_adoption"] and edge["canonical_storage_binding"] is None
    assert not packet["canonical_traceability"]["canonical_topology_published"]
    evidence = json.loads(
        (ROOT / packet["evidence_boundary"]["retained_execution_ref"]).read_text()
    )
    for subject in packet["subjects"]:
        assert (
            evidence["input_candidate_sha256"][subject["candidate_file"]]
            == subject["candidate_sha256"]
        )
    assert len(evidence["test_cases"]) == 2
    assert evidence["evidence_transfer"] == "not_performed"
    assert evidence["admission"] == evidence["tests_verified"] == "not_evaluated"


@pytest.mark.parametrize("mutation", [None, "input", "scope"])
def test_existing_packet_reader_checks_capture_preparation_bytes(tmp_path, mutation):
    packet = copy.deepcopy(load_packet())
    documents = {
        path: (ROOT / path).read_text() for path in packet["inputs"]["review_tree_file_sha256"]
    }
    historical = packet["inputs"]["contract_snapshot"]
    for path in historical["file_sha256"]:
        documents[path] = DecisionSnapshot(ROOT, historical["commit"]).read(path).decode()
    repository = make_repo(tmp_path, documents)
    # Adapt only this isolated test repository's historical commit identity.
    historical["commit"] = git(repository, "rev-parse", "HEAD")
    packet["approval_scope_sha256"] = scope_digest(
        {k: v for k, v in packet.items() if k != "approval_scope_sha256"}
    )
    if mutation == "scope":
        packet["subjects"][0]["statement"] += " Unreviewed scope change."
    path = repository / PACKET
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(packet, ensure_ascii=False, indent=2) + "\n").encode()
    path.write_bytes(raw)
    if mutation == "input":
        source = repository / "docs/reviews/0045_cn_capture/source-note.json"
        source.write_text(source.read_text() + "\n")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "Pending packet fixture")
    head = git(repository, "rev-parse", "HEAD")
    binding = {
        "reviewed_head": head,
        "packet_path": PACKET,
        "packet_sha256": hashlib.sha256(raw).hexdigest(),
        "approval_scope_sha256": packet["approval_scope_sha256"],
    }
    snapshot = DecisionSnapshot(repository, head)
    if mutation:
        match = "review input changed" if mutation == "input" else "exact packet scope"
        with pytest.raises(PublicationGovernanceError, match=match):
            _packet(snapshot, binding)
    else:
        accepted, _ = _packet(snapshot, binding)
        assert accepted["gate_state"] == "review_pending"
        assert accepted["canonical_mutations_allowed"] is False
