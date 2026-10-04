"""Reject stale review scopes, missing inputs and unearned materialization claims."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import validate_materialization_packet as review  # noqa: E402


@pytest.fixture()
def snapshot(tmp_path, monkeypatch):
    packet = json.loads((ROOT / review.PACKET).read_text())
    for relative in [review.PACKET, *packet["inputs"]["review_tree_file_sha256"]]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    original = review._contract_blob
    # Mutate only copied review inputs; historical blobs remain in the real Git repository.
    monkeypatch.setattr(
        review, "_contract_blob", lambda root, commit, path: original(ROOT, commit, path)
    )
    return tmp_path, packet


def save(root, packet, *, recompute=True):
    if recompute:
        packet["approval_scope_sha256"] = review.packet_digest(packet)
    (root / review.PACKET).write_text(json.dumps(packet, ensure_ascii=False))


def test_repository_pending_packet_is_consistent_not_authorized(capsys):
    assert review.validate(ROOT) == []
    assert review.main(["--root", str(ROOT)]) == 0
    assert "publication not authorized" in capsys.readouterr().out


def test_changed_scope_without_digest_update_fails(snapshot):
    root, packet = snapshot
    packet["subjects"][0]["statement"] += " modified"
    save(root, packet, recompute=False)
    assert "packet digest mismatch" in review.validate(root)[0]


@pytest.mark.parametrize(
    "kind", ["workspace", "criterion", "proposal", "prior_decision", "manifest"]
)
def test_changed_input_bytes_fail_even_with_unchanged_packet(snapshot, kind):
    root, packet = snapshot
    paths = {
        "workspace": packet["workspace"]["proposed_declaration"].split("#")[0],
        "criterion": packet["subjects"][2]["candidate_file"],
        "proposal": packet["subjects"][0]["source_proposal_ref"],
        "prior_decision": review.DECISION,
        "manifest": review.MANIFEST,
    }
    path = root / paths[kind]
    path.write_bytes(path.read_bytes() + b"\n")
    assert "input digest mismatch" in review.validate(root)[0]


def test_workspace_input_cannot_be_omitted(snapshot):
    root, packet = snapshot
    del packet["inputs"]["review_tree_file_sha256"][
        packet["workspace"]["proposed_declaration"].split("#")[0]
    ]
    save(root, packet)
    assert "input digest inventory" in review.validate(root)[0]


def test_rehashed_workspace_candidate_cannot_claim_adoption(snapshot):
    import hashlib

    from spec_yaml import dump_canonical_yaml, load_yaml_text

    root, packet = snapshot
    relative = packet["workspace"]["proposed_declaration"].split("#")[0]
    path = root / relative
    candidate = load_yaml_text(path.read_text())
    candidate["canonical_adoption"] = True
    path.write_text(dump_canonical_yaml(candidate))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    packet["workspace"]["candidate_sha256"] = digest
    packet["inputs"]["review_tree_file_sha256"][relative] = digest
    save(root, packet)
    assert "candidate envelopes must remain pending" in review.validate(root)[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "wrong_source",
        "wrong_target",
        "wrong_ingress",
        "wrong_revision",
        "approved",
    ],
)
def test_recomputed_digest_does_not_hide_invalid_transition_inventory(snapshot, mutation):
    root, packet = snapshot
    records = packet["transition_records"]
    if mutation == "missing":
        records.pop()
    elif mutation == "duplicate":
        records[-1] = records[0]
    elif mutation == "wrong_source":
        records[0]["source_ref"] = "docs/proposals/unrelated.md"
    elif mutation == "wrong_target":
        records[1]["target_ref"] = records[3]["target_ref"]
    elif mutation == "wrong_ingress":
        records[1]["ingress_record_ref"] = review.PACKET + "#/transition_records/2"
    elif mutation == "wrong_revision":
        records[1]["target_revision_selection"]["revision"] = 2
    else:
        records[0]["outcome"] = "approved"
    save(root, packet)
    assert review.validate(root)


@pytest.mark.parametrize(
    "mutation",
    [
        "lineage",
        "blocker",
        "lifecycle",
        "topology",
        "activation",
        "authorization",
        "readiness",
        "publication_gate",
    ],
)
def test_recomputed_digest_cannot_erase_unresolved_governance(snapshot, mutation):
    root, packet = snapshot
    if mutation == "lineage":
        del packet["transition_records"][0]["intent_lineage_ref"]
    elif mutation == "blocker":
        packet["review_blocker_codes"].remove("intent_lineage_unresolved")
    elif mutation == "lifecycle":
        packet["decision_lifecycle"]["decision_storage"] = "in_place"
    elif mutation == "topology":
        del packet["writer_request"]["topology_selection"]
    elif mutation == "activation":
        packet["provenance_binding_review"]["subject_bindings"][0]["activation_decision_ref"] = (
            "guessed"
        )
    elif mutation == "authorization":
        packet["publication_authorization"] = {"reviewer_authority": "human_project_author"}
    elif mutation == "readiness":
        packet["ready_for_materialization"] = True
    else:
        packet["governed_publication_gate"]["may_publish"] = True
    save(root, packet)
    assert review.validate(root)


def test_missing_historical_contract_fails_without_current_file_fallback(snapshot, monkeypatch):
    root, _ = snapshot

    def missing(*args):
        raise review.PacketError("contract snapshot unavailable")

    monkeypatch.setattr(review, "_contract_blob", missing)
    assert "contract snapshot unavailable" in review.validate(root)[0]


def test_changed_contract_digest_fails(snapshot):
    root, packet = snapshot
    packet["inputs"]["contract_snapshot"]["file_sha256"][review.CONTRACTS[0]] = "0" * 64
    save(root, packet)
    assert "contract snapshot digest mismatch" in review.validate(root)[0]


def test_wrong_requirement_membership_fails(snapshot):
    root, packet = snapshot
    packet["subjects"][0]["requirement_membership"].append("ac.approval-boundary")
    save(root, packet)
    assert "Requirement membership mismatch" in review.validate(root)[0]


@pytest.mark.parametrize("content", ['{"subjects": []', "[]", '{"subjects": [], "subjects": []}'])
def test_malformed_packet_returns_failure_without_traceback(snapshot, content, capsys):
    root, _ = snapshot
    (root / review.PACKET).write_text(content)
    assert review.main(["--root", str(root)]) == 1
    assert "invalid materialization packet" in capsys.readouterr().err


def test_duplicate_subject_cannot_replace_missing_approved_identity(snapshot):
    root, packet = snapshot
    packet["subjects"][-1] = packet["subjects"][0]
    save(root, packet)
    assert review.validate(root)


def test_candidate_path_cannot_escape_selected_root(snapshot):
    root, packet = snapshot
    packet["subjects"][0]["candidate_file"] = "../outside.yaml"
    save(root, packet)
    assert review.validate(root)


def test_exact_scope_digest_is_present_in_both_docs_and_sync_contract():
    packet = json.loads((ROOT / review.PACKET).read_text())
    digest = packet["approval_scope_sha256"]
    for path in (
        "docs/reviews/0221_canonical_materialization_packet.md",
        "Sources/SpecGraph/Documentation.docc/ProposalsAndRuntime.md",
    ):
        text = (ROOT / path).read_text()
        section = text[text.index("RFC 0221 canonical materialization review packet") :]
        assert digest in section
    contract = json.loads((ROOT / "tools/docc_sync_contract.json").read_text())
    group = next(
        g
        for g in contract["groups"]
        if g["id"] == "rfc0221-canonical-materialization-review-packet"
    )
    assert digest in group["required_terms"]
