"""Concrete CN-CAPTURE preparation; all source mutations stay in disposable clones."""

# ruff: noqa: E402

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from spec_yaml import load_yaml_text
from subject_canonical_source import read_canonical_source
from subject_publication import (
    DecisionSnapshot,
    PublicationGovernanceError,
    SubjectPublicationEvidence,
    _packet,
    scope_digest,
)
from subject_read_model import RevisionSelection, SubjectClass, SubjectRef
from subject_read_model_io import SubjectDocumentError
from subject_source_git import SubjectSourceCommit, git_command, selected_source_commit
from subject_source_write import (
    SubjectWriteAuthorization,
    parse_write_authorization,
    parse_write_request,
    write_subject_source,
)

FOLDER = "docs/reviews/0045_cn_capture/materialization"
PACKET = FOLDER + "/packet.json"
REQUEST = FOLDER + "/writer-request.json"
LINEAGES = FOLDER + "/lineages.json"
DECISIONS_TEMPLATE = FOLDER + "/decisions.template.json"
DECISIONS = FOLDER + "/decisions.json"


def document(path, root=ROOT):
    return load_yaml_text((root / path).read_text())


def save(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def commit_paths(root, paths):
    git_command(root, "add", "--", *sorted(set(paths)))
    # The initial clone already contains these bytes once this package is committed.
    git_command(root, "commit", "--allow-empty", "-qm", "Synthetic CN-CAPTURE evidence fixture")
    return git_command(root, "rev-parse", "HEAD").stdout.decode().strip()


def binding(root, packet, head):
    return {
        "reviewed_head": head,
        "packet_path": PACKET,
        "packet_sha256": hashlib.sha256((root / PACKET).read_bytes()).hexdigest(),
        "approval_scope_sha256": packet["approval_scope_sha256"],
    }


@pytest.fixture()
def rehearsal(tmp_path):
    """Borrow immutable objects, keeping the clone's refs/index/objects independent."""
    root = tmp_path / "rehearsal"
    subprocess.run(
        ["git", "clone", "--shared", "--no-checkout", "--quiet", str(ROOT), str(root)],
        check=True,
        capture_output=True,
    )
    for key, value in (
        ("user.name", "CN-CAPTURE fixture"),
        ("user.email", "fixture@example.invalid"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", "/dev/null"),
    ):
        git_command(root, "config", key, value)
    git_command(root, "read-tree", "HEAD")
    packet = document(PACKET)
    for path in [PACKET, *packet["inputs"]["review_tree_file_sha256"]]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / path).read_bytes())
    head = commit_paths(root, [PACKET, *packet["inputs"]["review_tree_file_sha256"]])
    request = parse_write_request(document(REQUEST, root))
    git_command(root, "update-ref", request.source_ref, request.expected_commit)
    return root, packet, request, head


def test_complete_preparation_retains_meaning_exact_request_and_pending_decisions():
    packet = document(PACKET)
    request = parse_write_request(document(REQUEST))
    assert (
        scope_digest({k: v for k, v in packet.items() if k != "approval_scope_sha256"})
        == packet["approval_scope_sha256"]
    )
    for path, digest in packet["inputs"]["review_tree_file_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    assert request.digest() == packet["writer_request"]["request_sha256"]
    assert request.expected_source_file_sha256 == ()
    assert {change.subject.local_subject_id for change in request.changes} == {
        "req.cn.capture",
        "ac.cn.capture-without-kind",
    }
    for subject in packet["subjects"]:
        candidate = document(subject["candidate_file"])
        record = candidate["proposed_record"]
        original = document(candidate["source_prototype"])["proposed_record"]
        assert record["revisions"][0]["statement"] == original["revisions"][0]["statement"]
        assert (
            not candidate["canonical_adoption"] and not candidate["publication_decisions_recorded"]
        )
        assert record["current_disposition"]["state"] == "active"
        assert record["revisions"][0]["provenance"].startswith(DECISIONS + "#/effects/")
    graph = load_yaml_text(request.intent_graph_yaml)
    prior = document("docs/reviews/0045_cn_capture/adoption/intent-lineage.json")
    assert graph["intents"][0]["statement"] == prior["canonical_intent_candidates"][0]["statement"]
    assert (
        graph["derived_from"][0]["source"] == packet["subjects"][0]["canonical_revision_selection"]
    )
    templates = document(DECISIONS_TEMPLATE)["proposed_decisions"]
    assert len(templates["effects"]) == 8
    assert len(templates["transition_decisions"]) == 4
    assert all(e["review"] is None for e in templates["effects"])
    assert all(
        t["review"] is None and t["outcome"] is None for t in templates["transition_decisions"]
    )
    assert all(lineage["review"] is None for lineage in document(LINEAGES)["lineages"])
    assert not (ROOT / DECISIONS).exists()
    assert packet["canonical_readiness"] == "not_evaluated"
    with pytest.raises(SubjectDocumentError):
        parse_write_authorization(document(FOLDER + "/authorization.template.json"))


@pytest.mark.parametrize("changed_request", [False, True])
def test_packet_reader_uses_committed_inputs_and_rejects_a_changed_request(
    rehearsal, changed_request
):
    root, packet, _, head = rehearsal
    if changed_request:
        path = root / REQUEST
        path.write_text(path.read_text() + "\n")
        head = commit_paths(root, [REQUEST])
    selection = binding(root, packet, head)
    snapshot = DecisionSnapshot(root, head)
    if changed_request:
        with pytest.raises(PublicationGovernanceError, match="review input changed"):
            _packet(snapshot, selection)
    else:
        checked, _ = _packet(snapshot, selection)
        assert checked["gate_state"] == "review_pending"
        assert checked["canonical_mutations_allowed"] is False


def test_isolated_preview_reproduces_physical_commit_and_keeps_ref_index_head(rehearsal):
    root, _, request, _ = rehearsal
    head = git_command(root, "rev-parse", "HEAD").stdout
    index = (root / ".git/index").read_bytes()
    result = write_subject_source(root, request, preview=True)
    recorded = document(FOLDER + "/preview.json")
    assert result["candidate_commit"] == recorded["result"]["candidate_commit"]
    assert result["request_sha256"] == recorded["request_sha256"]
    assert result["source_file_sha256"] == recorded["result"]["source_file_sha256"]
    assert not result["source_ref_updated"]
    assert selected_source_commit(root, request.source_ref) == request.expected_commit
    assert git_command(root, "rev-parse", "HEAD").stdout == head
    assert (root / ".git/index").read_bytes() == index
    with SubjectSourceCommit(root, result["candidate_commit"]).export() as exported:
        source = read_canonical_source(exported, request.topology)
        edge = source.intent_graph.derived_from[0]
        assert source.intent_graph.paths_from(edge.source) == (
            ("edge.cn.capture.derived-from-intent", "intent.cn.capture"),
        )
        criterion = SubjectRef(
            request.topology.workspace_identity,
            SubjectClass.CRITERION,
            "ac.cn.capture-without-kind",
        )
        assert source.intent_graph.paths_from(RevisionSelection(criterion, "exact", 1)) == ()
    assert not (root / "specs/workspace_identity.yaml").exists()


@pytest.mark.parametrize("extract_proposed", [False, True])
def test_pending_templates_do_not_grant_publication_permission(rehearsal, extract_proposed):
    root, packet, request, head = rehearsal
    selected = DECISIONS_TEMPLATE
    if extract_proposed:
        save(root, DECISIONS, document(DECISIONS_TEMPLATE, root)["proposed_decisions"])
        head = commit_paths(root, [DECISIONS])
        selected = DECISIONS
    proposed = document(packet["authorization_template_path"], root)["proposed_authorization"]
    authorization = SubjectWriteAuthorization(
        request.digest(),
        proposed["decision_ref"],
        "human:fixture",
        "human_project_author",
        request.recorded_at,
        tuple(proposed["transition_refs"]),
    )
    evidence = SubjectPublicationEvidence(root, head, selected)
    before = git_command(root, "count-objects", "-v").stdout
    with pytest.raises(PublicationGovernanceError):
        write_subject_source(root, request, authorization=authorization, governance=evidence)
    assert selected_source_commit(root, request.source_ref) == request.expected_commit
    assert git_command(root, "count-objects", "-v").stdout == before


class FixtureApprovals:
    """Synthetic approvals in a private test clone, never attributed to the operator."""

    def __init__(self, root, timestamp):
        self.root = root
        self.timestamp = timestamp
        self.counter = 0
        self.paths = []

    def approve(self, record):
        self.counter += 1
        path = f"docs/fixture-human/review-{self.counter}.json"
        review = {
            "reviewer": "human:cn-capture-fixture",
            "reviewer_authority": "human_project_author",
            "decision_timestamp": self.timestamp,
            "outcome": "approved",
            "rationale": "Synthetic temporary-repository approval only.",
            "source_quote": "Fixture: approve exactly this action.",
            "source_ref": path,
            "scope_sha256": scope_digest({k: v for k, v in record.items() if k != "review"}),
        }
        record["review"] = review
        save(
            self.root,
            path,
            {"schema_version": 1, "artifact_kind": "subject_human_review_record", "review": review},
        )
        self.paths.append(path)


def test_synthetic_decisions_publish_the_same_payload_with_a_new_review_scope(rehearsal):
    root, original, request, _ = rehearsal
    packet = copy.deepcopy(original)
    author = FixtureApprovals(root, request.recorded_at)
    lineages = document(LINEAGES, root)
    for lineage in lineages["lineages"]:
        author.approve(lineage)
    save(root, LINEAGES, lineages)
    packet["inputs"]["review_tree_file_sha256"][LINEAGES] = hashlib.sha256(
        (root / LINEAGES).read_bytes()
    ).hexdigest()
    packet.pop("approval_scope_sha256")
    packet["approval_scope_sha256"] = scope_digest(packet)
    assert packet["approval_scope_sha256"] != original["approval_scope_sha256"]
    save(root, PACKET, packet)
    reviewed_head = commit_paths(root, [LINEAGES, PACKET, *author.paths])
    decisions = document(DECISIONS_TEMPLATE, root)["proposed_decisions"]
    decisions["packet_binding"] = binding(root, packet, reviewed_head)
    decisions["packet_approval"] = {"packet_binding": decisions["packet_binding"]}
    author.approve(decisions["packet_approval"])
    for transition in decisions["transition_decisions"]:
        transition.update(
            state="approved",
            outcome="approved",
            reviewer_or_decider="human:cn-capture-fixture",
            decision_timestamp=request.recorded_at,
            rationale="Synthetic temporary-repository approval only.",
        )
        author.approve(transition)
    for effect in decisions["effects"]:
        author.approve(effect)
    author.approve(decisions["publication"])
    save(root, DECISIONS, decisions)
    evidence_head = commit_paths(root, [DECISIONS, *author.paths])
    proposed = document(FOLDER + "/authorization.template.json", root)["proposed_authorization"]
    authorization = SubjectWriteAuthorization(
        request.digest(),
        proposed["decision_ref"],
        "human:cn-capture-fixture",
        "human_project_author",
        request.recorded_at,
        tuple(proposed["transition_refs"]),
    )
    result = write_subject_source(
        root,
        request,
        authorization=authorization,
        governance=SubjectPublicationEvidence(root, evidence_head, DECISIONS),
    )
    assert result["status"] == "published"
    assert (
        result["candidate_commit"]
        == document(FOLDER + "/preview.json")["result"]["candidate_commit"]
    )
    assert selected_source_commit(root, request.source_ref) == result["candidate_commit"]
    assert result["reviewer_identity_attested"] is False
