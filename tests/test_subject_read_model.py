from __future__ import annotations

import copy
import json
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from subject_read_model import SubjectClass, SubjectRef  # noqa: E402
from subject_read_model_io import (  # noqa: E402
    SubjectDocumentError,
    lookup_payload,
    main,
    parse_subject_index,
)

FIXTURE = Path(__file__).parent / "fixtures" / "subject_read_model" / "snapshot.json"


def snapshot() -> dict:
    return json.loads(FIXTURE.read_text())


def ref(
    local_id: str = "AC-1", workspace: str = "workspace-a", kind: str = "criterion"
) -> SubjectRef:
    return SubjectRef(workspace, SubjectClass(kind), local_id)


def test_exact_and_current_select_authored_revisions_and_containment() -> None:
    index = parse_subject_index(snapshot())
    old = index.lookup_exact(ref(), 1)
    current = index.lookup_current(ref())
    assert old.status == current.status == "resolved"
    assert old.selected_revision.statement == "Original criterion"
    assert old.selected_revision.containment == "spec-a"
    assert current.selected_revision.number == 3
    assert current.selected_revision.containment == "spec-b"
    assert index.lookup_exact(ref(), 2).status == "unavailable_revision"
    assert index.lookup_exact(ref(), 999).status == "unavailable_revision"
    assert "resolved" not in lookup_payload(index.lookup_exact(ref(), 2))


def test_disposition_is_current_while_exact_content_stays_historical() -> None:
    data = snapshot()
    active = parse_subject_index(data).lookup_exact(ref(), 1)
    data["workspaces"][0]["subjects"][1]["current_disposition"] = {
        "state": "retired",
        "basis_ref": "withdrawal-2",
        "observation_provenance": "review-2",
    }
    retired = parse_subject_index(data).lookup_exact(ref(), 1)
    assert active.selected_revision == retired.selected_revision
    assert active.record.current_disposition.state == "active"
    payload = lookup_payload(retired)["resolved"]
    assert payload["current_subject_disposition"]["state"] == "retired"
    assert payload["current_subject_disposition"]["basis_ref"] == "withdrawal-2"
    assert retired.status == "resolved"


def test_scope_class_and_missing_identity_are_explicit() -> None:
    data = snapshot()
    second = copy.deepcopy(data["workspaces"][0])
    second["workspace_identity"] = "workspace-b"
    second["dataset_identity"] = "independent-b"
    for subject in second["subjects"]:
        subject["reference"]["workspace_identity"] = "workspace-b"
        for selection in subject["acceptance_criteria_refs"]:
            selection["subject"]["workspace_identity"] = "workspace-b"
    data["workspaces"].append(second)
    index = parse_subject_index(data)
    assert index.lookup_current(ref(workspace="workspace-b")).status == "resolved"
    assert index.lookup_current(ref(workspace="missing")).status == "unknown_workspace_identity"
    assert index.lookup_current(ref("missing")).status == "unknown_subject_id"
    assert index.lookup_current(ref(kind="Requirement")).status == "subject_class_mismatch"


def test_workspace_collision_precedes_subject_selection_and_replica_conflicts_fail_closed() -> None:
    data = snapshot()
    replica = copy.deepcopy(data["workspaces"][0])
    replica["subjects"].reverse()
    data["workspaces"].append(replica)
    assert parse_subject_index(data).lookup_current(ref()).status == "resolved"
    replica["dataset_identity"] = "independent-fork"
    replica["subjects"] = []
    assert parse_subject_index(data).lookup_current(ref()).status == "ambiguous_workspace_identity"
    replica["dataset_identity"] = "source-a"
    assert parse_subject_index(data).lookup_current(ref()).status == "ambiguous_workspace_identity"


def test_duplicate_local_id_cannot_hide_in_another_subject_class() -> None:
    data = snapshot()
    duplicate = copy.deepcopy(data["workspaces"][0]["subjects"][0])
    duplicate["reference"]["local_subject_id"] = "AC-1"
    data["workspaces"][0]["subjects"].append(duplicate)
    with pytest.raises(SubjectDocumentError, match="duplicate_subject_identity"):
        parse_subject_index(data)


@pytest.mark.parametrize("number", [True, 0, -1, 1.5, "1", None])
def test_invalid_revisions_are_not_coerced(number: object) -> None:
    index = parse_subject_index(snapshot())
    with pytest.raises(ValueError, match="positive integer"):
        index.lookup_exact(ref(), number)
    data = snapshot()
    data["workspaces"][0]["subjects"][0]["current_revision"] = number
    with pytest.raises(SubjectDocumentError):
        parse_subject_index(data)


def test_revision_origin_and_immediate_predecessor_are_checked_without_inventing_history() -> None:
    data = snapshot()
    record = data["workspaces"][0]["subjects"][1]
    record["revisions"][0]["predecessor"] = 0
    with pytest.raises(SubjectDocumentError, match="revision 1"):
        parse_subject_index(data)
    record["revisions"][0]["predecessor"] = None
    record["revisions"][1]["predecessor"] = 1
    with pytest.raises(SubjectDocumentError, match="immediate"):
        parse_subject_index(data)
    record["revisions"][1]["predecessor"] = 2
    record["revisions"].append(copy.deepcopy(record["revisions"][1]))
    with pytest.raises(SubjectDocumentError, match="conflicting_revision_successor"):
        parse_subject_index(data)


def relation(kind: str = "decomposes_into") -> dict:
    roles = (
        ["source", "result", "result"]
        if kind == "decomposes_into"
        else ["result", "contributor", "contributor"]
    )
    return {
        "relation_id": "relation-1",
        "kind": kind,
        "provenance": "review:relation",
        "endpoints": [
            {
                "role": role,
                "selection": {
                    "subject": {
                        "workspace_identity": "workspace-a",
                        "subject_class": "criterion",
                        "local_subject_id": name,
                    },
                    "mode": "current",
                },
            }
            for role, name in zip(roles, ["AC-1", "AC-2", "AC-3"], strict=True)
        ],
    }


def related_snapshot() -> dict:
    data = snapshot()
    for name in ["AC-2", "AC-3"]:
        record = copy.deepcopy(data["workspaces"][0]["subjects"][1])
        record["reference"]["local_subject_id"] = name
        data["workspaces"][0]["subjects"].append(record)
    data["workspaces"][0]["relations"] = [relation()]
    return data


def test_relations_return_every_authored_endpoint_without_inferred_inverse() -> None:
    index = parse_subject_index(related_snapshot())
    assert index.reference_errors() == ()
    outgoing = index.lookup_current(ref()).relations
    incoming = index.lookup_current(ref("AC-2")).relations
    assert outgoing == incoming
    assert outgoing[0].kind == "decomposes_into"
    assert {e.selection.subject.local_subject_id for e in outgoing[0].endpoints} == {
        "AC-1",
        "AC-2",
        "AC-3",
    }
    assert {e.role for e in outgoing[0].endpoints} == {"source", "result"}


def test_cross_kind_and_unknown_relation_endpoints_are_diagnosed() -> None:
    data = related_snapshot()
    endpoint = data["workspaces"][0]["relations"][0]["endpoints"][0]
    endpoint["selection"]["subject"]["subject_class"] = "Requirement"
    with pytest.raises(SubjectDocumentError, match="same subject class"):
        parse_subject_index(data)
    endpoint["selection"]["subject"]["subject_class"] = "criterion"
    endpoint["selection"]["subject"]["local_subject_id"] = "missing"
    with pytest.raises(SubjectDocumentError, match="unknown_subject_id"):
        parse_subject_index(data)


def cross_workspace_snapshot() -> dict:
    data = related_snapshot()
    source = data["workspaces"][0]
    target = {
        "workspace_identity": "workspace-b",
        "dataset_identity": "source-b",
        "subjects": source["subjects"][2:],
        "relations": [],
    }
    source["subjects"] = source["subjects"][:2]
    for subject in target["subjects"]:
        subject["reference"]["workspace_identity"] = "workspace-b"
    for endpoint in source["relations"][0]["endpoints"][1:]:
        endpoint["selection"]["subject"]["workspace_identity"] = "workspace-b"
    data["workspaces"].append(target)
    return data


def test_incoming_cross_workspace_relations_preserve_authored_roles() -> None:
    index = parse_subject_index(cross_workspace_snapshot())
    outgoing = index.lookup_current(ref()).relations
    assert len(outgoing) == 1
    for name in ("AC-2", "AC-3"):
        incoming = index.lookup_current(ref(name, workspace="workspace-b")).relations
        assert incoming == outgoing
    assert outgoing[0].kind == "decomposes_into"
    assert {(e.role, e.selection.subject.workspace_identity) for e in outgoing[0].endpoints} == {
        ("source", "workspace-a"),
        ("result", "workspace-b"),
    }


def test_cross_workspace_relation_enumeration_coalesces_only_declared_replicas() -> None:
    data = cross_workspace_snapshot()
    source = data["workspaces"][0]
    other = copy.deepcopy(source)
    other["workspace_identity"] = "workspace-c"
    other["dataset_identity"] = "source-c"
    for subject in other["subjects"]:
        subject["reference"]["workspace_identity"] = "workspace-c"
        for selection in subject["acceptance_criteria_refs"]:
            selection["subject"]["workspace_identity"] = "workspace-c"
    other["relations"][0]["endpoints"][0]["selection"]["subject"]["workspace_identity"] = (
        "workspace-c"
    )
    data["workspaces"].extend([other, copy.deepcopy(source)])
    request = ref("AC-2", workspace="workspace-b")
    relations = parse_subject_index(data).lookup_current(request).relations
    assert len(relations) == 2
    assert {r.relation_id for r in relations} == {"relation-1"}
    data["workspaces"].reverse()
    assert parse_subject_index(data).lookup_current(request).relations == relations


def test_nested_data_detached_and_immutable() -> None:
    data = snapshot()
    before = copy.deepcopy(data)
    index = parse_subject_index(data)
    assert data == before
    data["workspaces"][0]["subjects"][1]["revisions"][0]["statement"] = "mutated"
    record = index.lookup_exact(ref(), 1).record
    assert record.revisions[0].statement == "Original criterion"
    with pytest.raises(FrozenInstanceError):
        record.revisions[0].statement = "mutated"


def test_cli_preserves_source_bytes_and_distinguishes_lookup_from_input_failure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "snapshot.json"
    path.write_bytes(FIXTURE.read_bytes())
    original = path.read_bytes()
    args = [
        sys.executable,
        str(TOOLS / "subject_read_model_io.py"),
        "--snapshot",
        str(path),
        "--workspace-identity",
        "workspace-a",
        "--subject-class",
        "criterion",
        "--subject-id",
        "AC-1",
    ]
    result = subprocess.run(args + ["--revision", "1"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["resolved"]["revision"]["number"] == 1
    absent = subprocess.run(args + ["--revision", "2"], capture_output=True, text=True)
    assert absent.returncode == 1
    assert json.loads(absent.stdout)["status"] == "unavailable_revision"
    assert path.read_bytes() == original
    assert subprocess.run(args, capture_output=True).returncode == 2


@pytest.mark.parametrize(
    "text", ["schema_version: 1\nschema_version: 2\n", "workspaces: [", "- list", "? [a, b]\n: c\n"]
)
def test_malformed_documents_return_diagnostic_json(tmp_path: Path, capsys, text: str) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(text)
    code = main(
        [
            "--snapshot",
            str(path),
            "--workspace-identity",
            "w",
            "--subject-class",
            "criterion",
            "--subject-id",
            "a",
            "--current",
        ]
    )
    assert code == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"


def test_unknown_fields_and_missing_identity_never_trigger_allocation() -> None:
    data = snapshot()
    data["workspaces"][0]["subjects"][1]["reference"].pop("local_subject_id")
    with pytest.raises(SubjectDocumentError, match="missing fields"):
        parse_subject_index(data)
    data = snapshot()
    data["workspaces"][0]["unexpected"] = "field"
    with pytest.raises(SubjectDocumentError, match="unknown fields"):
        parse_subject_index(data)


def test_public_constructors_reject_mutable_collections() -> None:
    index = parse_subject_index(snapshot())
    with pytest.raises(ValueError, match="immutable tuple"):
        replace(index, snapshots=list(index.snapshots))
    workspace = index.snapshots[0]
    with pytest.raises(ValueError, match="immutable tuple"):
        replace(workspace, subjects=list(workspace.subjects))
    with pytest.raises(ValueError, match="immutable tuple"):
        replace(workspace.subjects[0], revisions=list(workspace.subjects[0].revisions))


def test_exact_result_exposes_retained_containment_history_without_fabricating_gaps() -> None:
    result = parse_subject_index(snapshot()).lookup_exact(ref(), 1)
    payload = lookup_payload(result)["resolved"]
    assert payload["current_revision"] == 3
    assert payload["revision"]["containment"] == "spec-a"
    assert [(x["revision"], x["containment"]) for x in payload["retained_containment_history"]] == [
        (1, "spec-a"),
        (3, "spec-b"),
    ]
