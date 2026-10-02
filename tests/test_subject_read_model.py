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

from subject_read_model import RelationSource, SubjectClass, SubjectRef  # noqa: E402
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
        for revision in subject["revisions"]:
            for selection in revision["acceptance_criteria_refs"]:
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
        for revision in subject["revisions"]:
            for selection in revision["acceptance_criteria_refs"]:
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


@pytest.mark.parametrize("independent_dataset", [True, False])
def test_ambiguous_relation_source_reports_incomplete_enumeration(
    independent_dataset: bool,
) -> None:
    data = cross_workspace_snapshot()
    request = ref("AC-2", workspace="workspace-b")
    healthy = parse_subject_index(data).lookup_exact(request, 1)
    assert len(healthy.relations) == 1
    conflict = copy.deepcopy(data["workspaces"][0])
    if independent_dataset:
        conflict["dataset_identity"] = "independent-fork"
    else:
        conflict["relations"] = []
    data["workspaces"].append(conflict)
    result = parse_subject_index(data).lookup_exact(request, 1)
    assert result.status == "resolved"
    assert result.selected_revision == healthy.selected_revision
    assert result.relations == ()  # Disputed records are not promoted as true.
    projection = lookup_payload(result)["resolved"]["relation_resolution"]
    assert projection == {
        "status": "incomplete",
        "scope": "supplied_snapshots",
        "conflicts": [
            {
                "workspace_identity": "workspace-a",
                "dataset_identities": (
                    ("independent-fork", "source-a") if independent_dataset else ("source-a",)
                ),
                "reason": "ambiguous_workspace_identity",
            }
        ],
    }
    data["workspaces"].reverse()
    assert parse_subject_index(data).lookup_exact(request, 1) == result


def test_unrelated_workspace_conflict_does_not_imply_missing_relations() -> None:
    data = cross_workspace_snapshot()
    data["workspaces"][0]["relations"] = []
    conflict = copy.deepcopy(data["workspaces"][0])
    conflict["dataset_identity"] = "independent-fork"
    data["workspaces"].append(conflict)
    result = parse_subject_index(data).lookup_current(ref("AC-2", workspace="workspace-b"))
    assert result.status == "resolved"
    assert lookup_payload(result)["resolved"]["relation_resolution"] == {
        "status": "complete",
        "scope": "supplied_snapshots",
        "conflicts": [],
    }


def test_relation_source_scope_survives_identical_cross_workspace_records() -> None:
    data = cross_workspace_snapshot()
    data["workspaces"].append(
        {
            "workspace_identity": "workspace-c",
            "dataset_identity": "source-c",
            "subjects": [],
            "relations": copy.deepcopy(data["workspaces"][0]["relations"]),
        }
    )
    index = parse_subject_index(data)
    result = index.lookup_current(ref("AC-2", workspace="workspace-b"))
    payloads = lookup_payload(result)["resolved"]["authored_relations"]
    assert len(payloads) == 2
    assert [p["source"] for p in payloads] == [
        {"workspace_identity": "workspace-a", "dataset_identity": "source-a"},
        {"workspace_identity": "workspace-c", "dataset_identity": "source-c"},
    ]
    assert payloads[0] != payloads[1]
    assert {p["relation_id"] for p in payloads} == {"relation-1"}
    assert payloads[0]["endpoints"] == payloads[1]["endpoints"]
    workspace = index.snapshots[0]
    bad_relation = replace(workspace.relations[0], source=RelationSource("other", "source-a"))
    with pytest.raises(ValueError, match="relation source must match"):
        replace(workspace, relations=(bad_relation,))


def test_requirement_revision_preserves_acceptance_pins_across_criterion_move() -> None:
    data = snapshot()
    requirement = data["workspaces"][0]["subjects"][0]
    request = ref("REQ-1", kind="Requirement")
    before = parse_subject_index(data).lookup_exact(request, 1)
    new_revision = copy.deepcopy(requirement["revisions"][0])
    new_revision.update(number=2, predecessor=1, provenance="review:new-acceptance-link")
    new_revision["acceptance_criteria_refs"][0]["revision"] = 3
    requirement["revisions"].append(new_revision)
    requirement["current_revision"] = 2
    index = parse_subject_index(data)
    old = index.lookup_exact(request, 1)
    current = index.lookup_current(request)
    assert old.selected_revision == before.selected_revision
    assert old.selected_revision.acceptance_criteria_refs[0].revision == 1
    assert current.selected_revision.acceptance_criteria_refs[0].revision == 3
    assert lookup_payload(old)["resolved"]["acceptance_criteria_refs"][0]["revision"] == 1
    assert lookup_payload(current)["resolved"]["acceptance_criteria_refs"][0]["revision"] == 3
    assert index.lookup_exact(ref(), 1).selected_revision.containment == "spec-a"
    assert index.lookup_exact(ref(), 3).selected_revision.containment == "spec-b"


def test_acceptance_links_require_exact_criterion_pins_and_validate_retained_history() -> None:
    data = snapshot()
    requirement = data["workspaces"][0]["subjects"][0]
    selection = requirement["revisions"][0]["acceptance_criteria_refs"][0]
    selection.update(mode="current", revision=None)
    with pytest.raises(SubjectDocumentError, match="pin exact criterion"):
        parse_subject_index(data)
    selection.update(mode="exact", revision=2)
    with pytest.raises(SubjectDocumentError, match="unavailable_revision"):
        parse_subject_index(data)
    selection["revision"] = 1
    selection["subject"]["subject_class"] = "Requirement"
    with pytest.raises(SubjectDocumentError, match="pin exact criterion"):
        parse_subject_index(data)


def test_obsolete_record_level_acceptance_links_are_not_assigned_to_history() -> None:
    data = snapshot()
    requirement = data["workspaces"][0]["subjects"][0]
    requirement["acceptance_criteria_refs"] = requirement["revisions"][0].pop(
        "acceptance_criteria_refs"
    )
    with pytest.raises(SubjectDocumentError, match="unknown fields"):
        parse_subject_index(data)


def test_cli_incomplete_relations_exit_nonzero_with_resolved_content(
    tmp_path: Path, capsys
) -> None:
    data = cross_workspace_snapshot()
    conflict = copy.deepcopy(data["workspaces"][0])
    conflict["dataset_identity"] = "independent-fork"
    data["workspaces"].append(conflict)
    source = json.dumps(data)
    path = tmp_path / "conflict.json"
    path.write_text(source)
    code = main(
        [
            "--snapshot",
            str(path),
            "--workspace-identity",
            "workspace-b",
            "--subject-class",
            "criterion",
            "--subject-id",
            "AC-2",
            "--revision",
            "1",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["status"] == "resolved"
    assert payload["resolved"]["revision"]["number"] == 1
    assert payload["resolved"]["relation_resolution"]["status"] == "incomplete"
    assert path.read_text() == source


def test_replicas_coalesce_when_acceptance_reference_order_differs() -> None:
    data = related_snapshot()
    source = data["workspaces"][0]
    refs = source["subjects"][0]["revisions"][0]["acceptance_criteria_refs"]
    second = copy.deepcopy(refs[0])
    second["subject"]["local_subject_id"] = "AC-2"
    refs.append(second)
    replica = copy.deepcopy(source)
    replica["subjects"][0]["revisions"][0]["acceptance_criteria_refs"].reverse()
    data["workspaces"].append(replica)
    index = parse_subject_index(data)
    assert index.lookup_current(ref("REQ-1", kind="Requirement")).status == "resolved"
    revision = index.snapshots[0].subjects[0].revisions[0]
    assert (
        replace(
            revision, acceptance_criteria_refs=tuple(reversed(revision.acceptance_criteria_refs))
        )
        == revision
    )


def test_typed_replica_values_normalize_revision_and_endpoint_order() -> None:
    workspace = parse_subject_index(related_snapshot()).snapshots[0]
    criterion = workspace.subjects[1]
    assert replace(criterion, revisions=tuple(reversed(criterion.revisions))) == criterion
    relation_value = workspace.relations[0]
    assert (
        replace(relation_value, endpoints=tuple(reversed(relation_value.endpoints)))
        == relation_value
    )


def test_one_dataset_cannot_declare_multiple_workspace_identities() -> None:
    data = cross_workspace_snapshot()
    data["workspaces"][1]["dataset_identity"] = "source-a"
    index = parse_subject_index(data)
    assert index.lookup_current(ref()).status == "ambiguous_workspace_identity"
    assert index.lookup_current(ref("AC-2", workspace="workspace-b")).status == (
        "ambiguous_workspace_identity"
    )
    data["workspaces"].reverse()
    assert parse_subject_index(data).lookup_exact(ref(), 1).status == "ambiguous_workspace_identity"


def test_disposition_history_is_retained_without_inferring_current_or_as_of_state() -> None:
    data = snapshot()
    record = data["workspaces"][0]["subjects"][1]
    events = [
        {"event_ref": "z-activation", "transition": "activation", "provenance": "review:1"},
        {"event_ref": "a-withdrawal", "transition": "withdrawal", "provenance": "review:2"},
        {"event_ref": "m-reactivation", "transition": "activation", "provenance": "review:3"},
    ]
    record["retained_disposition_transitions"] = events
    record["current_disposition"] = {
        "state": "active",
        "basis_ref": "m-reactivation",
        "observation_provenance": "obs:3",
    }
    index = parse_subject_index(data)
    result = index.lookup_exact(ref(), 1)
    payload = lookup_payload(result)["resolved"]
    assert payload["current_subject_disposition"]["basis_ref"] == "m-reactivation"
    assert {e["event_ref"] for e in payload["retained_disposition_transitions"]} == {
        e["event_ref"] for e in events
    }
    replica = copy.deepcopy(data["workspaces"][0])
    replica["subjects"][1]["retained_disposition_transitions"].reverse()
    data["workspaces"].append(replica)
    assert parse_subject_index(data).lookup_exact(ref(), 1) == result
    with pytest.raises(FrozenInstanceError):
        result.record.retained_disposition_transitions[0].provenance = "changed"
    with pytest.raises(ValueError, match="immutable tuple"):
        replace(
            result.record,
            retained_disposition_transitions=list(result.record.retained_disposition_transitions),
        )


def test_disposition_history_rejects_duplicate_and_contradictory_basis_events() -> None:
    data = snapshot()
    record = data["workspaces"][0]["subjects"][1]
    event = {
        "event_ref": record["current_disposition"]["basis_ref"],
        "transition": "withdrawal",
        "provenance": "review:withdrawal",
    }
    record["retained_disposition_transitions"] = [event]
    with pytest.raises(SubjectDocumentError, match="contradicts its retained basis"):
        parse_subject_index(data)
    event["transition"] = "activation"
    record["retained_disposition_transitions"].append(copy.deepcopy(event))
    with pytest.raises(SubjectDocumentError, match="duplicate disposition event_ref"):
        parse_subject_index(data)
