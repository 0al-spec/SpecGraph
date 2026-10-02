"""SG-SPEC-0069 read-only source checks; all origins are temporary fixture data."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import subject_canonical_source as source_module  # noqa: E402
from spec_yaml import dump_canonical_yaml, load_yaml_text  # noqa: E402
from subject_canonical_source import (  # noqa: E402
    CanonicalRequirementPresence,
    CanonicalTopologySelection,
    main,
    parse_topology_selection,
    read_canonical_source,
)
from subject_read_model import SubjectClass, SubjectRef  # noqa: E402
from subject_read_model_io import (  # noqa: E402
    SubjectDocumentError,
    lookup_payload,
    parse_subject_index,
    snapshot_payload,
)

WORKSPACE = "workspace:11111111-1111-4111-8111-111111111111"
REQ_PATH = "specs/requirements/feature/req.readiness.yaml"
AC_PATH = "specs/criteria/feature/ac.ready.yaml"


def ref(local_id="req.readiness", subject_class=SubjectClass.REQUIREMENT) -> SubjectRef:
    return SubjectRef(WORKSPACE, subject_class, local_id)


def put(root: Path, path: str, document: dict) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dump_canonical_yaml(document))


def get(root: Path, path: str) -> dict:
    return load_yaml_text((root / path).read_text())


def topology_payload(topology) -> dict:
    return {
        "schema_version": 1,
        "artifact_kind": "subject_canonical_topology_selection",
        "workspace_identity": topology.workspace_identity,
        "dataset_identity": topology.dataset_identity,
        "topology_ref": topology.topology_ref,
        "governance_evidence_ref": topology.governance_evidence_ref,
        "requirements": [
            {
                "subject": {
                    "workspace_identity": item.subject.workspace_identity,
                    "subject_class": item.subject.subject_class.value,
                    "local_subject_id": item.subject.local_subject_id,
                },
                "canonical_presence": item.canonical_presence,
            }
            for item in topology.requirements
        ],
    }


@pytest.fixture()
def source(tmp_path):
    root = tmp_path / "selected"
    root.mkdir()
    put(
        root,
        "specs/workspace_identity.yaml",
        {
            "schema_version": 1,
            "artifact_kind": "subject_workspace_declaration",
            "workspace_identity": WORKSPACE,
            "provenance": "fixture:workspace-declaration",
        },
    )
    for local_id, subject_class, path in (
        ("req.readiness", "Requirement", REQ_PATH),
        ("ac.ready", "criterion", AC_PATH),
    ):
        revisions = []
        for number in (1, 2):
            fields = {"title": f"Fixture {local_id} revision {number}"}
            if subject_class == "Requirement":
                fields.update(
                    {
                        "status": "outlined" if number == 1 else "specified",
                        "authority_class": "imported" if number == 1 else "inferred",
                        "source_ref": f"fixture:revision-{number}",
                        "provenance": {
                            "actor_id": f"fixture:actor-{number}",
                            "authority_class": "imported" if number == 1 else "inferred",
                            "recorded_at": f"2026-10-02T16:0{number}:00Z",
                            "source_ref": f"fixture:revision-{number}",
                        },
                    }
                )
                if number == 2:
                    fields["provenance"].update(
                        {
                            "source_confidence": "high",
                            "source_system": "fixture",
                            "notes": "Fixture revision, not canonical adoption.",
                            "trace_context": {"steps": [{"values": [1, "α", True]}]},
                        }
                    )
            directory = "requirements" if subject_class == "Requirement" else "criteria"
            revisions.append(
                {
                    "number": number,
                    "predecessor": None if number == 1 else 1,
                    "node_fields": fields,
                    "statement": f"Fixture normative statement {number}",
                    "containment": path
                    if number == 2
                    else f"specs/{directory}/previous/{local_id}.yaml",
                    "provenance": f"fixture:materialization-or-revision-{number}",
                    "revision_scope": (
                        f"Fixture authored scope {number}: {local_id} and exact membership."
                    ),
                    "acceptance_criteria_refs": (
                        [
                            {
                                "subject": {
                                    "workspace_identity": WORKSPACE,
                                    "subject_class": "criterion",
                                    "local_subject_id": "ac.ready",
                                },
                                "mode": "exact",
                                "revision": number,
                            }
                        ]
                        if subject_class == "Requirement"
                        else []
                    ),
                }
            )
        events = [
            {
                "event_ref": "fixture:z-origin",
                "transition": "activation",
                "provenance": "fixture:materialization",
            }
        ]
        if subject_class == "Requirement":
            events.append(
                {
                    "event_ref": "fixture:a-withdrawal",
                    "transition": "withdrawal",
                    "provenance": "fixture:withdrawal-decision",
                }
            )
        document = {
            "schema_version": 1,
            "artifact_kind": "requirement_node"
            if subject_class == "Requirement"
            else "acceptance_criterion_record",
            "id": local_id,
            **copy.deepcopy(revisions[-1]["node_fields"]),
            "subject": {
                "workspace_identity": WORKSPACE,
                "subject_class": subject_class,
                "local_subject_id": local_id,
            },
            "current_revision": 2,
            "revisions": revisions,
            "current_disposition": {
                "state": "retired" if subject_class == "Requirement" else "active",
                "basis_ref": events[-1]["event_ref"],
                "observation_provenance": "fixture:observation",
            },
            "retained_disposition_transitions": events,
        }
        if subject_class == "Requirement":
            document["kind"] = "requirement"
        put(root, path, document)
    topology = CanonicalTopologySelection(
        WORKSPACE,
        "fixture:dataset",
        "fixture:topology",
        "fixture:governance-evidence",
        (CanonicalRequirementPresence(ref(), "active"),),
    )
    return root, topology


def test_historical_metadata_scope_and_exact_membership_survive_source_read(source) -> None:
    root, topology = source
    before = {
        p.relative_to(root): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*.yaml")
    }
    read = read_canonical_source(root, topology)
    old, current = read.index.lookup_exact(ref(), 1), read.index.lookup_current(ref())
    assert old.status == current.status == "resolved"
    assert old.selected_revision.node_fields.provenance.actor_id == "fixture:actor-1"
    assert current.selected_revision.node_fields.provenance.actor_id == "fixture:actor-2"
    assert old.selected_revision.node_fields.status == "outlined"
    assert current.selected_revision.node_fields.status == "specified"
    assert old.selected_revision.revision_scope.startswith("Fixture authored scope 1")
    assert old.selected_revision.acceptance_criteria_refs[0].revision == 1
    assert current.selected_revision.acceptance_criteria_refs[0].revision == 2
    assert old.record.current_disposition.state == "retired"
    assert old.record.canonical_presence == "active"
    assert old.selected_revision.containment == "specs/requirements/previous/req.readiness.yaml"
    payload = lookup_payload(old)["resolved"]
    assert [e["event_ref"] for e in payload["retained_disposition_transitions"]] == [
        "fixture:z-origin",
        "fixture:a-withdrawal",
    ]
    exported = read.audit_payload()
    assert exported["canonical_readiness"] == "not_evaluated"
    assert exported["ready_for_materialization"] is False
    assert exported["canonical_mutations_allowed"] is False
    assert (
        exported["source_binding"]["governance_evidence_verification"]
        == "caller_selected_not_attested"
    )
    assert len(exported["source_file_sha256"]) == 3
    assert before == {
        p.relative_to(root): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*.yaml")
    }


def test_source_snapshot_roundtrip_retains_dataset_order_and_nested_provenance(source) -> None:
    root, topology = source
    original = read_canonical_source(root, topology).index
    payload = snapshot_payload(original)
    assert parse_subject_index(payload) == original
    current = original.lookup_current(ref()).selected_revision
    nested = lookup_payload(original.lookup_current(ref()))["resolved"]["revision"]
    nested["node_fields"]["provenance"]["trace_context"]["steps"][0]["values"].append("mutated")
    assert "mutated" not in current.node_fields.provenance.trace_context_json
    with pytest.raises(FrozenInstanceError):
        current.revision_scope = "mutated"
    assert original.snapshots[0].dataset_identity == "fixture:dataset"
    assert parse_subject_index(payload).lookup_current(ref()).record.retained_disposition_order == (
        "fixture:z-origin",
        "fixture:a-withdrawal",
    )


def test_topology_presence_is_selected_independently_of_file_and_disposition(source) -> None:
    root, topology = source
    selected = replace(
        topology, requirements=(CanonicalRequirementPresence(ref(), "historical_lineage_only"),)
    )
    assert (
        read_canonical_source(root, selected).index.lookup_current(ref()).record.canonical_presence
        == "historical_lineage_only"
    )
    for bad in (
        None,
        replace(topology, requirements=()),
        replace(
            topology,
            workspace_identity="workspace:22222222-2222-4222-8222-222222222222",
            requirements=(),
        ),
    ):
        with pytest.raises(SubjectDocumentError):
            read_canonical_source(root, bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("kind", "criterion"),
        ("canonical_presence", "active"),
        ("unexpected", "value"),
        ("id", "another-id"),
        ("current_revision", True),
        ("current_revision", 1),
        ("title", "wrong projection"),
    ],
)
def test_invalid_current_record_fields_fail_closed(source, field, value) -> None:
    root, topology = source
    document = get(root, REQ_PATH)
    document[field] = value
    put(root, REQ_PATH, document)
    with pytest.raises(SubjectDocumentError):
        read_canonical_source(root, topology)


@pytest.mark.parametrize(
    "field,value",
    [
        ("number", True),
        ("predecessor", 0),
        ("revision_scope", None),
        ("revision_scope", " "),
        ("provenance", None),
        ("containment", "../../escape.yaml"),
        ("containment", "specs/requirements/../req.readiness.yaml"),
        ("containment", "specs/requirements/Upper/req.readiness.yaml"),
        ("unexpected", "value"),
    ],
)
def test_invalid_retained_revisions_fail_closed(source, field, value) -> None:
    root, topology = source
    document = get(root, REQ_PATH)
    document["revisions"][0][field] = value
    put(root, REQ_PATH, document)
    with pytest.raises(SubjectDocumentError):
        read_canonical_source(root, topology)


def test_incomplete_history_dangling_pins_and_duplicate_origins_are_rejected(source) -> None:
    root, topology = source
    original = get(root, AC_PATH)
    for revisions in ([original["revisions"][1]], [original["revisions"][0]] * 2):
        changed = copy.deepcopy(original)
        changed["revisions"] = revisions
        put(root, AC_PATH, changed)
        with pytest.raises(SubjectDocumentError):
            read_canonical_source(root, topology)
    put(root, AC_PATH, original)
    (root / AC_PATH).unlink()
    with pytest.raises(SubjectDocumentError, match="unknown_subject_id"):
        read_canonical_source(root, topology)


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor_id", ""),
        ("recorded_at", "2026-10-02"),
        ("recorded_at", None),
        ("authority_class", "unknown"),
        ("source_ref", None),
        ("source_confidence", None),
        ("source_confidence", "certain"),
        ("unknown", True),
    ],
)
def test_retained_node_provenance_is_validated_including_historical_envelopes(
    source, field, value
) -> None:
    root, topology = source
    document = get(root, REQ_PATH)
    document["revisions"][1]["node_fields"]["provenance"][field] = value
    document["provenance"][field] = value
    put(root, REQ_PATH, document)
    with pytest.raises(SubjectDocumentError):
        read_canonical_source(root, topology)


def test_old_provenance_cannot_disappear_behind_a_valid_current_projection(source) -> None:
    root, topology = source
    document = get(root, REQ_PATH)
    document["revisions"][0]["node_fields"]["provenance"]["actor_id"] = None
    put(root, REQ_PATH, document)
    with pytest.raises(SubjectDocumentError, match="actor_id"):
        read_canonical_source(root, topology)


@pytest.mark.parametrize("mode,revision", [("current", None), ("exact", True), ("exact", 3)])
def test_acceptance_membership_requires_resolvable_exact_pins(source, mode, revision) -> None:
    root, topology = source
    document = get(root, REQ_PATH)
    document["revisions"][0]["acceptance_criteria_refs"][0].update(mode=mode, revision=revision)
    put(root, REQ_PATH, document)
    with pytest.raises(SubjectDocumentError):
        read_canonical_source(root, topology)


def test_authored_disposition_order_and_current_projection_are_checked(source) -> None:
    root, topology = source
    original = get(root, REQ_PATH)
    for field, value in (
        (
            "retained_disposition_transitions",
            list(reversed(original["retained_disposition_transitions"])),
        ),
        ("retained_disposition_transitions", []),
        (
            "current_disposition",
            {
                "state": "active",
                "basis_ref": "fixture:z-origin",
                "observation_provenance": "fixture:obs",
            },
        ),
    ):
        document = copy.deepcopy(original)
        document[field] = value
        put(root, REQ_PATH, document)
        with pytest.raises(SubjectDocumentError, match="last authored event"):
            read_canonical_source(root, topology)


@pytest.mark.parametrize("subject_class", ["criterion", "Requirement"])
def test_portable_case_collisions_span_grouping_classes_and_retired_history(
    source, subject_class
) -> None:
    root, topology = source
    document = get(root, AC_PATH if subject_class == "criterion" else REQ_PATH)
    local_id = "REQ.READINESS"
    directory = "criteria" if subject_class == "criterion" else "requirements"
    path = f"specs/{directory}/other/{local_id}.yaml"
    document["id"] = document["subject"]["local_subject_id"] = local_id
    for revision in document["revisions"]:
        revision["containment"] = path
    put(root, path, document)
    if subject_class == "Requirement":
        topology = replace(
            topology,
            requirements=topology.requirements
            + (CanonicalRequirementPresence(ref(local_id), "active"),),
        )
    with pytest.raises(SubjectDocumentError, match="portable namespace collision"):
        read_canonical_source(root, topology)


@pytest.mark.parametrize(
    "target", ["specs/workspace_identity.yaml", AC_PATH, "specs/requirements/feature"]
)
def test_symlinked_records_and_directories_are_rejected(source, tmp_path, target) -> None:
    root, topology = source
    destination = tmp_path / "outside"
    path = root / target
    path.rename(destination)
    path.symlink_to(destination, target_is_directory=destination.is_dir())
    with pytest.raises(SubjectDocumentError):
        read_canonical_source(root, topology)


def test_duplicate_yaml_keys_missing_declaration_and_preparation_envelopes_are_rejected(
    source,
) -> None:
    root, topology = source
    declaration = root / "specs/workspace_identity.yaml"
    before = declaration.read_bytes()
    declaration.write_bytes(before + b"schema_version: 1\n")
    with pytest.raises(SubjectDocumentError, match="duplicate key"):
        read_canonical_source(root, topology)
    declaration.unlink()
    with pytest.raises(SubjectDocumentError):
        read_canonical_source(root, topology)
    declaration.write_bytes(before)
    candidate = load_yaml_text(
        (TOOLS.parent / "docs/reviews/0221_subject_storage/ac.clean-noop.yaml").read_text()
    )
    put(root, AC_PATH, candidate)
    with pytest.raises(SubjectDocumentError):
        read_canonical_source(root, topology)


def test_cli_codes_snapshot_and_source_identity_remain_explicit(source, tmp_path, capsys) -> None:
    root, topology = source
    selection = tmp_path / "topology.yaml"
    put(tmp_path, selection.name, topology_payload(topology))
    args = ["--source-root", str(root), "--topology-selection", str(selection)]
    assert parse_topology_selection(topology_payload(topology)) == topology
    assert main(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert parse_subject_index(payload["snapshot"]).lookup_current(ref()).status == "resolved"
    lookup = args + ["--subject-class", "Requirement", "--subject-id", "req.readiness"]
    assert main(lookup + ["--revision", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["lookup"]["resolved"]["revision"]["number"] == 1
    assert main(lookup + ["--revision", "3"]) == 1
    assert json.loads(capsys.readouterr().out)["lookup"]["status"] == "unavailable_revision"
    selection.write_text("schema_version: false\n")
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"


def test_legacy_snapshot_output_is_unchanged_and_extended_metadata_needs_a_pair() -> None:
    fixture = TOOLS.parent / "tests/fixtures/subject_read_model/snapshot.json"
    data = json.loads(fixture.read_text())
    index = parse_subject_index(data)
    payload = lookup_payload(
        index.lookup_current(SubjectRef("workspace-a", SubjectClass.CRITERION, "AC-1"))
    )
    assert "node_fields" not in payload["resolved"]["revision"]
    assert "revision_scope" not in payload["resolved"]["revision"]
    assert parse_subject_index(snapshot_payload(index)) == index
    data["workspaces"][0]["subjects"][0]["revisions"][0]["revision_scope"] = "half metadata"
    with pytest.raises(SubjectDocumentError, match="supplied together"):
        parse_subject_index(data)


def test_optional_provenance_nulls_and_nested_trace_are_retained_without_invention(source) -> None:
    root, topology = source
    document = get(root, REQ_PATH)
    document["provenance"]["notes"] = None
    document["revisions"][1]["node_fields"]["provenance"]["notes"] = None
    put(root, REQ_PATH, document)
    read = read_canonical_source(root, topology)
    payload = lookup_payload(read.index.lookup_current(ref()))["resolved"]["revision"]
    assert payload["node_fields"] == document["revisions"][1]["node_fields"]
    assert payload["node_fields"]["provenance"]["notes"] is None
    assert parse_subject_index(snapshot_payload(read.index)) == read.index
    old = lookup_payload(read.index.lookup_exact(ref(), 1))["resolved"]["revision"]
    assert "trace_context" not in old["node_fields"]["provenance"]


@pytest.mark.parametrize(
    "placement", ["current", "retained_current", "retained_history", "current_and_retained"]
)
@pytest.mark.parametrize(
    "trace_context",
    [
        {1: "value"},
        {True: "value"},
        {None: "value"},
        {1.5: "value"},
        {"nested": {1: "value"}},
        {"steps": [{1: "value"}]},
        {1: "numeric", "1": "string"},
    ],
)
def test_non_string_trace_keys_are_rejected_before_json_encoding(
    source, placement, trace_context
) -> None:
    root, topology = source
    document = get(root, REQ_PATH)
    if placement in {"current", "current_and_retained"}:
        provenance = document["provenance"]
    else:
        number = 1 if placement == "retained_current" else 0
        provenance = document["revisions"][number]["node_fields"]["provenance"]
    provenance["trace_context"] = trace_context
    if placement == "current_and_retained":
        document["revisions"][1]["node_fields"]["provenance"]["trace_context"] = trace_context
    put(root, REQ_PATH, document)
    with pytest.raises(SubjectDocumentError, match="trace_context.*string keys"):
        read_canonical_source(root, topology)


@pytest.mark.parametrize("change", ["content", "namespace"])
def test_source_changes_during_read_fail_closed(source, monkeypatch, change) -> None:
    root, topology = source
    original = source_module.parse_subject_revision
    changed = False

    def concurrent_change(value):
        nonlocal changed
        if not changed:
            changed = True
            if change == "content":
                path = root / "specs/workspace_identity.yaml"
                path.write_text(path.read_text() + "# concurrent update\n")
            else:
                put(root, "specs/criteria/new.yaml", {"schema_version": 1})
        return original(value)

    monkeypatch.setattr(source_module, "parse_subject_revision", concurrent_change)
    with pytest.raises(SubjectDocumentError, match="source tree changed during read"):
        read_canonical_source(root, topology)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("governance_evidence_ref", ""),
        ("dataset_identity", ""),
        ("unknown", "value"),
    ],
)
def test_topology_selection_is_strict_and_keeps_governance_binding(source, field, value) -> None:
    _, topology = source
    payload = topology_payload(topology)
    payload[field] = value
    with pytest.raises(ValueError):
        parse_topology_selection(payload)


def test_empty_invalid_grouping_and_untyped_source_metadata_are_rejected(source) -> None:
    root, topology = source
    (root / "specs/criteria/Upper").mkdir()
    with pytest.raises(SubjectDocumentError, match="lowercase ASCII"):
        read_canonical_source(root, topology)
    with pytest.raises(ValueError, match="immutable tuple"):
        replace(topology, requirements=list(topology.requirements))
    with pytest.raises(ValueError, match="typed Requirement"):
        replace(topology, requirements=({},))


@pytest.mark.parametrize("previous_status", ["frozen", "linked"])
def test_frozen_or_regressed_requirement_revision_is_rejected(source, previous_status) -> None:
    root, topology = source
    document = get(root, REQ_PATH)
    document["revisions"][0]["node_fields"]["status"] = previous_status
    put(root, REQ_PATH, document)
    with pytest.raises(SubjectDocumentError, match="frozen or regressed"):
        read_canonical_source(root, topology)
