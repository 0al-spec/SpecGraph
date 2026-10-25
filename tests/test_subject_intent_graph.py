"""Real temporary Git publication of Intent origins and exact derived_from links.

Human approvals below are synthetic fixture data, never production adoption.
"""

# ruff: noqa: E402

import copy
import hashlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import MappingProxyType

import pytest
from specification_core import TraceRecorder

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from spec_yaml import dump_canonical_yaml, load_yaml_text
from subject_canonical_source import read_canonical_source
from subject_intent_derivation_spec import INTENT_DERIVATION_SPEC
from subject_intent_graph import INTENT_GRAPH_PATH, parse_intent_graph
from subject_intent_graph_append_spec import INTENT_GRAPH_APPEND_SPEC
from subject_intent_graph_context import IntentDerivationContext, IntentGraphAppendContext
from subject_publication import PublicationGovernanceError, scope_digest
from subject_read_model import RevisionSelection, SubjectClass
from subject_read_model_io import SubjectDocumentError
from subject_source_git import (
    SubjectSourceCommit,
    SubjectSourceConflict,
    git_command,
    selected_source_commit,
)
from subject_source_write import main, parse_write_request, write_subject_source
from test_subject_canonical_source import WORKSPACE, put, ref, topology_payload
from test_subject_canonical_source import source as source
from test_subject_publication import DECISION, PACKET, commit, write_json
from test_subject_publication import governed as governed
from test_subject_source_write import RECORDED_AT, SOURCE_REF, request_payload, seed_repository


def graph_document(subject=None, revision=2, human_source="docs/intent_source.json"):
    subject = subject or ref()
    return {
        "schema_version": 1,
        "artifact_kind": "subject_intent_graph",
        "workspace_identity": WORKSPACE,
        "intents": [
            {
                "id": "intent.capture",
                "kind": "intent",
                "revision": 1,
                "title": "Retain the fixture intent",
                "status": "outlined",
                "authority_class": "distilled",
                "source_ref": human_source,
                "provenance": {
                    "actor_id": "agent:fixture",
                    "authority_class": "distilled",
                    "recorded_at": RECORDED_AT,
                    "source_ref": human_source,
                },
                "statement": "Fixture: retain a note before classification.",
                "adoption_provenance": "fixture:intent-origin",
            }
        ],
        "derived_from": [
            {
                "id": "edge.capture",
                "kind": "derived_from",
                "source": {
                    "subject": {**asdict(subject), "subject_class": subject.subject_class.value},
                    "mode": "exact",
                    "revision": revision,
                },
                "target_intent_id": "intent.capture",
                "target_revision": 1,
                "adoption_provenance": "fixture:edge-origin",
            }
        ],
    }


@pytest.fixture()
def graph_governed(governed):
    root, original, authorization, _, decisions, author = governed
    selection = original.changes[0]
    revision = load_yaml_text(selection.document_yaml)["current_revision"]
    document = graph_document(selection.subject, revision, "docs/graph_human.json")
    human = json.loads((root / "docs/intent_source.json").read_text())
    write_json(root, "docs/graph_human.json", {**human, "schema_version": 1})
    for item in (*document["intents"], *document["derived_from"]):
        item["adoption_provenance"] = DECISION + f"#/effects/{len(decisions['effects'])}"
        effect = {
            "effect": "intent_graph_origin",
            "workspace_identity": WORKSPACE,
            "record_id": item["id"],
            "record_kind": item["kind"],
            "record_sha256": scope_digest(item),
        }
        author.approve(effect)
        decisions["effects"].append(effect)
    request = replace(original, intent_graph_yaml=dump_canonical_yaml(document))
    candidate = "docs/intent_graph_candidate.json"
    write_json(root, candidate, {"proposed_record": document})
    packet = json.loads((root / PACKET).read_text())
    packet.pop("approval_scope_sha256")
    digest = hashlib.sha256((root / candidate).read_bytes()).hexdigest()
    packet["inputs"]["review_tree_file_sha256"][candidate] = digest
    packet["inputs"]["review_tree_file_sha256"]["docs/graph_human.json"] = hashlib.sha256(
        (root / "docs/graph_human.json").read_bytes()
    ).hexdigest()
    packet["intent_graph"] = {
        "candidate_file": candidate,
        "candidate_sha256": digest,
        "source_draft_ref": candidate + "#/proposed_record",
        "target_path": INTENT_GRAPH_PATH,
    }
    packet["approval_scope_sha256"] = scope_digest(packet)
    write_json(root, PACKET, packet)
    binding = {
        "packet_path": PACKET,
        "reviewed_head": commit(root),
        "packet_sha256": hashlib.sha256((root / PACKET).read_bytes()).hexdigest(),
        "approval_scope_sha256": packet["approval_scope_sha256"],
    }
    decisions["packet_binding"] = binding
    decisions["packet_approval"] = {"packet_binding": binding}
    author.approve(decisions["packet_approval"])
    references = set(authorization.transition_refs) | {
        i["adoption_provenance"] for i in (*document["intents"], *document["derived_from"])
    }
    decisions["publication"] = {
        "request_sha256": request.digest(),
        "transition_refs": sorted(references),
    }
    author.approve(decisions["publication"])
    evidence = author.save(decisions)
    authorization = replace(
        authorization, request_sha256=request.digest(), transition_refs=tuple(sorted(references))
    )
    return root, request, authorization, evidence, decisions, author


def test_graph_read_roundtrip_has_only_authored_revision_paths(source):
    root, topology = source
    document = graph_document()
    put(root, INTENT_GRAPH_PATH, document)
    selected = read_canonical_source(root, topology)
    graph = selected.intent_graph
    assert parse_intent_graph(graph.payload()) == graph
    assert INTENT_GRAPH_PATH in dict(selected.source_file_sha256)
    assert graph.paths_from(RevisionSelection(ref(), "exact", 2)) == (
        ("edge.capture", "intent.capture"),
    )
    assert graph.paths_from(RevisionSelection(ref(), "exact", 1)) == ()
    assert (
        graph.paths_from(RevisionSelection(ref("ac.ready", SubjectClass.CRITERION), "exact", 2))
        == ()
    )
    assert json.loads(json.dumps(selected.audit_payload()))["intent_graph"] == graph.payload()


@pytest.mark.parametrize(
    "case",
    [
        "missing_target",
        "missing_source_revision",
        "current_source",
        "criterion",
        "other_workspace",
        "wrong_kind",
        "portable_alias",
        "bool_revision",
        "unknown_field",
        "alias_path",
    ],
)
def test_graph_rejects_invalid_authored_endpoints_and_shapes(source, case):
    root, topology = source
    document = graph_document()
    edge, node = document["derived_from"][0], document["intents"][0]
    if case == "missing_target":
        edge["target_intent_id"] = "intent.absent"
    elif case == "missing_source_revision":
        edge["source"]["revision"] = 99
    elif case == "current_source":
        edge["source"].update(mode="current")
        edge["source"].pop("revision")
    elif case == "criterion":
        edge["source"]["subject"].update(subject_class="criterion", local_subject_id="ac.ready")
    elif case == "other_workspace":
        edge["source"]["subject"]["workspace_identity"] = (
            "workspace:22222222-2222-4222-8222-222222222222"
        )
    elif case == "wrong_kind":
        edge["kind"] = "relates_to"
    elif case == "portable_alias":
        node["id"] = "REQ.READINESS"
    elif case == "bool_revision":
        node["revision"] = True
    elif case == "unknown_field":
        document["canonical_presence"] = "active"
    put(root, INTENT_GRAPH_PATH, document)
    if case == "alias_path":
        (root / INTENT_GRAPH_PATH).rename(root / "specs/Intent_Graph.yaml")
    with pytest.raises((SubjectDocumentError, ValueError)):
        read_canonical_source(root, topology)


def test_append_preserves_origins_and_rejects_empty_or_changed_history():
    before = parse_intent_graph(graph_document())
    after = before.payload()
    new = copy.deepcopy(after["intents"][0])
    new["id"] = "intent.second"
    after["intents"].append(new)
    graph = parse_intent_graph(after)
    assert [i.id for i in graph.additions(before)] == ["intent.second"]
    for changed in (before.payload(), {**after, "intents": [new]}):
        with pytest.raises(SubjectDocumentError, match="retain all existing"):
            parse_intent_graph(changed).additions(before)
    after["intents"][0]["statement"] = "Changed after adoption."
    with pytest.raises(SubjectDocumentError, match="retain all existing"):
        parse_intent_graph(after).additions(before)
    assert not INTENT_GRAPH_APPEND_SPEC.is_satisfied_by(
        IntentGraphAppendContext("one", "two", (), (("id", "bytes"),))
    )


def test_v1_request_digest_and_parser_contract_stay_unchanged(governed):
    _, request, _, _, _, _ = governed
    legacy = asdict(request)
    assert legacy.pop("intent_graph_yaml") is None
    assert request.digest() == scope_digest(legacy)


def test_governed_graph_and_subjects_publish_in_one_commit(graph_governed):
    root, request, authorization, evidence, _, _ = graph_governed
    original_head = git_command(root, "rev-parse", "HEAD").stdout
    index_bytes = (root / ".git/index").read_bytes()
    result = write_subject_source(root, request, authorization=authorization, governance=evidence)
    assert result["status"] == "published"
    assert selected_source_commit(root, SOURCE_REF) == result["candidate_commit"]
    assert (
        git_command(root, "rev-parse", result["candidate_commit"] + "^").stdout.decode().strip()
        == request.expected_commit
    )
    assert git_command(root, "rev-parse", "HEAD").stdout == original_head
    assert (root / ".git/index").read_bytes() == index_bytes
    assert not (root / INTENT_GRAPH_PATH).exists()
    with SubjectSourceCommit(root, result["candidate_commit"]).export() as exported:
        source = read_canonical_source(exported, request.topology)
        graph = source.intent_graph
        assert graph.paths_from(graph.derived_from[0].source) == (
            ("edge.capture", "intent.capture"),
        )
        assert (
            source.index.lookup_exact(
                request.changes[0].subject, graph.derived_from[0].source.revision
            ).status
            == "resolved"
        )
        assert INTENT_GRAPH_PATH in result["source_file_sha256"]


def test_graph_preview_and_missing_permission_never_advance_ref(graph_governed):
    root, request, authorization, _, _, _ = graph_governed
    preview = write_subject_source(root, request, preview=True)
    assert preview["status"] == "prepared" and not preview["source_ref_updated"]
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit
    before_objects = git_command(root, "count-objects", "-v").stdout
    with pytest.raises(PublicationGovernanceError, match="publication evidence required"):
        write_subject_source(root, request, authorization=authorization)
    assert git_command(root, "count-objects", "-v").stdout == before_objects
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit


@pytest.mark.parametrize(
    "case",
    ["changed_record", "missing_origin_review", "wrong_origin_scope", "missing_origin_effect"],
)
def test_graph_permission_failures_do_not_publish(graph_governed, case):
    root, request, authorization, evidence, decisions, author = graph_governed
    if case == "changed_record":
        document = load_yaml_text(request.intent_graph_yaml)
        document["intents"][0]["statement"] += " Different unreviewed meaning."
        request = replace(request, intent_graph_yaml=dump_canonical_yaml(document))
        authorization = replace(authorization, request_sha256=request.digest())
    elif case == "missing_origin_review":
        decisions["effects"][-1]["review"] = None
        evidence = author.save(decisions)
    elif case == "wrong_origin_scope":
        decisions["effects"][-1]["record_sha256"] = "0" * 64
        author.approve(decisions["effects"][-1])
        evidence = author.save(decisions)
    else:
        decisions["effects"].pop()
        evidence = author.save(decisions)
    with pytest.raises(PublicationGovernanceError):
        write_subject_source(root, request, authorization=authorization, governance=evidence)
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit


def test_v2_cli_requires_explicit_graph_and_preserves_v1_field_rejection(
    graph_governed, tmp_path, capsys
):
    root, request, authorization, _, _, _ = graph_governed
    payload = {
        "schema_version": 2,
        "artifact_kind": "subject_source_write_request",
        "source_ref": request.source_ref,
        "expected_commit": request.expected_commit,
        "recorded_at": request.recorded_at,
        "topology_selection": topology_payload(request.topology),
        "expected_source_file_sha256": dict(request.expected_source_file_sha256),
        "changes": [
            {
                "operation": c.operation,
                "path": c.path,
                "expected_prior_sha256": c.expected_prior_sha256,
                "proposed_record": load_yaml_text(c.document_yaml),
            }
            for c in request.changes
        ],
        "intent_graph": load_yaml_text(request.intent_graph_yaml),
    }
    if request.workspace_declaration_yaml is not None:
        payload["workspace_declaration"] = load_yaml_text(request.workspace_declaration_yaml)
    assert parse_write_request(payload).digest() == request.digest()
    assert parse_write_request(MappingProxyType(payload)).digest() == request.digest()
    with pytest.raises(SubjectDocumentError, match="unknown fields"):
        parse_write_request({**payload, "schema_version": 1})
    missing = {k: v for k, v in payload.items() if k != "intent_graph"}
    with pytest.raises(SubjectDocumentError, match="requires a complete"):
        parse_write_request(missing)
    request_file, auth_file = tmp_path / "request.json", tmp_path / "auth.json"
    request_file.write_text(json.dumps(payload))
    auth_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_kind": "subject_source_write_authorization",
                **asdict(authorization),
            }
        )
    )
    assert (
        main(
            [
                "--repository-root",
                str(root),
                "--request",
                str(request_file),
                "--authorization",
                str(auth_file),
            ]
        )
        == 4
    )
    assert json.loads(capsys.readouterr().out)["source_ref_updated"] is False
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit


def test_graph_only_append_prepares_against_existing_requirements(source):
    root, topology = source
    commit_id = seed_repository(root)
    payload = request_payload((root, topology, commit_id), changes=[])
    payload.update(schema_version=2, intent_graph=graph_document())
    result = write_subject_source(root, parse_write_request(payload), preview=True)
    assert not result["source_ref_updated"]
    with SubjectSourceCommit(root, result["candidate_commit"]).export() as exported:
        assert read_canonical_source(exported, topology).intent_graph is not None


def test_graph_publication_loses_compare_and_swap_without_partial_write(
    graph_governed, monkeypatch
):
    root, request, authorization, evidence, _, _ = graph_governed
    publish = SubjectSourceCommit.publish

    def concurrent_successor(source, source_ref, candidate):
        git_command(
            root, "update-ref", source_ref, evidence.evidence_commit, request.expected_commit
        )
        publish(source, source_ref, candidate)

    monkeypatch.setattr(SubjectSourceCommit, "publish", concurrent_successor)
    with pytest.raises(SubjectSourceConflict):
        write_subject_source(root, request, authorization=authorization, governance=evidence)
    assert selected_source_commit(root, SOURCE_REF) == evidence.evidence_commit
    assert not (root / INTENT_GRAPH_PATH).exists()


@pytest.mark.parametrize("case", ["append", "unchanged", "changed", "removed", "omitted_digest"])
def test_existing_graph_is_preserved_on_a_later_append(graph_governed, case):
    root, request, authorization, evidence, _, _ = graph_governed
    published = write_subject_source(
        root, request, authorization=authorization, governance=evidence
    )
    document = load_yaml_text(request.intent_graph_yaml)
    if case != "unchanged":
        additional = copy.deepcopy(document["intents"][0])
        additional.update(id="intent.second", adoption_provenance="fixture:second-origin")
        document["intents"].append(additional)
    if case == "changed":
        document["intents"][0]["statement"] += " Rewritten."
    if case == "removed":
        document["derived_from"] = []
    digests = dict(published["source_file_sha256"])
    if case == "omitted_digest":
        digests.pop(INTENT_GRAPH_PATH)
    following = replace(
        request,
        expected_commit=published["candidate_commit"],
        expected_source_file_sha256=tuple(sorted(digests.items())),
        changes=(),
        workspace_declaration_yaml=None,
        intent_graph_yaml=dump_canonical_yaml(document),
    )
    if case == "append":
        preview = write_subject_source(root, following, preview=True)
        assert preview["status"] == "prepared" and not preview["source_ref_updated"]
    else:
        with pytest.raises((SubjectDocumentError, SubjectSourceConflict)):
            write_subject_source(root, following, preview=True)
    assert selected_source_commit(root, SOURCE_REF) == published["candidate_commit"]


@pytest.mark.parametrize("case", ["agent_source", "empty_quote", "unsupported_version"])
def test_graph_origin_needs_a_reviewed_original_human_source(graph_governed, case):
    root, request, authorization, _, decisions, author = graph_governed
    path = "docs/graph_human.json"
    human = json.loads((root / path).read_text())
    if case == "agent_source":
        human["actor_id"] = "agent:fixture"
    elif case == "empty_quote":
        human["text"] = ""
    else:
        human["schema_version"] = 2
    write_json(root, path, human)
    packet = json.loads((root / PACKET).read_text())
    packet["inputs"]["review_tree_file_sha256"][path] = hashlib.sha256(
        (root / path).read_bytes()
    ).hexdigest()
    packet.pop("approval_scope_sha256")
    packet["approval_scope_sha256"] = scope_digest(packet)
    write_json(root, PACKET, packet)
    binding = {
        "reviewed_head": commit(root),
        "packet_path": PACKET,
        "packet_sha256": hashlib.sha256((root / PACKET).read_bytes()).hexdigest(),
        "approval_scope_sha256": packet["approval_scope_sha256"],
    }
    decisions["packet_binding"] = binding
    decisions["packet_approval"] = {"packet_binding": binding}
    author.approve(decisions["packet_approval"])
    evidence = author.save(decisions)
    with pytest.raises(PublicationGovernanceError, match="original human source"):
        write_subject_source(root, request, authorization=authorization, governance=evidence)
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit


@pytest.mark.parametrize("case", ["symlink", "directory", "alias"])
def test_git_export_rejects_graph_aliases_and_directories(source, case):
    root, _ = source
    path = root / INTENT_GRAPH_PATH
    if case == "symlink":
        path.symlink_to(root / "specs/workspace_identity.yaml")
    elif case == "directory":
        path.mkdir()
        (path / "hidden.yaml").write_text("not a graph record")
    else:
        (root / "specs/Intent_Graph.yaml").write_text(dump_canonical_yaml(graph_document()))
    commit_id = seed_repository(root)
    with pytest.raises(SubjectDocumentError, match="real files|canonical case"):
        SubjectSourceCommit(root, commit_id).blobs()


def test_intent_graph_policies_retain_stable_trace_names():
    recorder = TraceRecorder()
    assert INTENT_DERIVATION_SPEC.is_satisfied_by(
        IntentDerivationContext("Requirement", "exact", WORKSPACE, WORKSPACE, True, True),
        recorder=recorder,
    )
    assert recorder.events[0].name == "subject_intent_graph.exact_requirement_to_intent"
    recorder = TraceRecorder()
    assert INTENT_GRAPH_APPEND_SPEC.is_satisfied_by(
        IntentGraphAppendContext(WORKSPACE, WORKSPACE, (), (("id", "record"),)), recorder=recorder
    )
    assert recorder.events[0].name == "subject_intent_graph.append_preserves_origins"
