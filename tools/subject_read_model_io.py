#!/usr/bin/env python3
"""Explicit snapshot boundary and CLI for the first RFC 0221 read-model slice.

The snapshot is an exchange/fixture format, not a canonical storage schema.
No repository discovery, identity allocation, migration, or writes occur here.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

from yaml import YAMLError

from spec_yaml import load_yaml_text
from subject_read_model import (
    CurrentSubjectDisposition,
    DispositionTransition,
    LookupResult,
    RelationEndpoint,
    RelationSource,
    RevisionSelection,
    SubjectClass,
    SubjectIndex,
    SubjectRecord,
    SubjectRef,
    SubjectRelation,
    SubjectRevision,
    WorkspaceSnapshot,
)


class SubjectDocumentError(ValueError):
    """The supplied snapshot cannot be interpreted without guessing."""


def _object(value: object, required: set[str], optional: set[str] | None = None) -> Mapping:
    if not isinstance(value, Mapping):
        raise SubjectDocumentError("expected a mapping")
    if set(value) - required - (optional or set()):
        raise SubjectDocumentError(
            f"unknown fields: {sorted(map(str, set(value) - required - (optional or set())))}"
        )
    if required - set(value):
        raise SubjectDocumentError(f"missing fields: {sorted(required - set(value))}")
    return value


def _list(value: object) -> list:
    if not isinstance(value, list):
        raise SubjectDocumentError("expected a list")
    return value


def parse_subject_ref(value: object) -> SubjectRef:
    data = _object(value, {"workspace_identity", "subject_class", "local_subject_id"})
    return SubjectRef(
        data["workspace_identity"], SubjectClass(data["subject_class"]), data["local_subject_id"]
    )


def _selection(value: object) -> RevisionSelection:
    data = _object(value, {"subject", "mode"}, {"revision"})
    return RevisionSelection(parse_subject_ref(data["subject"]), data["mode"], data.get("revision"))


def _revision(value: object) -> SubjectRevision:
    data = _object(
        value,
        {
            "number",
            "predecessor",
            "statement",
            "containment",
            "provenance",
            "acceptance_criteria_refs",
        },
    )
    return SubjectRevision(
        number=data["number"],
        predecessor=data["predecessor"],
        statement=data["statement"],
        containment=data["containment"],
        provenance=data["provenance"],
        acceptance_criteria_refs=tuple(
            _selection(v) for v in _list(data["acceptance_criteria_refs"])
        ),
    )


def _record(value: object) -> SubjectRecord:
    data = _object(
        value,
        {
            "reference",
            "current_revision",
            "revisions",
            "current_disposition",
            "canonical_presence",
            "retained_disposition_transitions",
        },
    )
    disposition = _object(
        data["current_disposition"], {"state", "basis_ref", "observation_provenance"}
    )
    return SubjectRecord(
        reference=parse_subject_ref(data["reference"]),
        current_revision=data["current_revision"],
        revisions=tuple(_revision(v) for v in _list(data["revisions"])),
        current_disposition=CurrentSubjectDisposition(**disposition),
        canonical_presence=data["canonical_presence"],
        retained_disposition_transitions=tuple(
            DispositionTransition(**_object(v, {"event_ref", "transition", "provenance"}))
            for v in _list(data["retained_disposition_transitions"])
        ),
    )


def _relation(value: object, source: RelationSource) -> SubjectRelation:
    data = _object(value, {"relation_id", "kind", "endpoints", "provenance"})
    endpoints = []
    for value in _list(data["endpoints"]):
        endpoint = _object(value, {"role", "selection"})
        endpoints.append(RelationEndpoint(endpoint["role"], _selection(endpoint["selection"])))
    return SubjectRelation(
        data["relation_id"],
        data["kind"],
        tuple(endpoints),
        data["provenance"],
        source,
    )


def parse_subject_index(value: object) -> SubjectIndex:
    """Decode explicit identified snapshots; never import candidate IDs as canonical."""
    try:
        data = _object(value, {"schema_version", "artifact_kind", "workspaces"})
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise SubjectDocumentError("schema_version must be integer 1")
        if data["artifact_kind"] != "subject_read_snapshot":
            raise SubjectDocumentError("artifact_kind must be subject_read_snapshot")
        workspaces = []
        for value in _list(data["workspaces"]):
            workspace = _object(
                value, {"workspace_identity", "dataset_identity", "subjects", "relations"}
            )
            workspaces.append(
                WorkspaceSnapshot(
                    workspace["workspace_identity"],
                    workspace["dataset_identity"],
                    tuple(_record(v) for v in _list(workspace["subjects"])),
                    tuple(
                        _relation(
                            v,
                            RelationSource(
                                workspace["workspace_identity"], workspace["dataset_identity"]
                            ),
                        )
                        for v in _list(workspace["relations"])
                    ),
                )
            )
        return SubjectIndex(tuple(workspaces))
    except (ValueError, TypeError) as exc:
        raise SubjectDocumentError(str(exc)) from exc


def load_subject_index(path: Path) -> SubjectIndex:
    """Read one explicit YAML/JSON snapshot, rejecting duplicate mapping keys."""
    try:
        return parse_subject_index(load_yaml_text(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, UnicodeError, YAMLError) as exc:
        raise SubjectDocumentError(f"{path}: {exc}") from exc


def lookup_payload(result: LookupResult) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "artifact_kind": "subject_lookup_result",
        "status": result.status,
        "requested": asdict(result.requested),
        "canonical_mutations_allowed": False,
    }
    if result.record is not None and result.selected_revision is not None:
        payload["resolved"] = {
            "reference": asdict(result.record.reference),
            "revision": asdict(result.selected_revision),
            "current_revision": result.record.current_revision,
            "retained_containment_history": [
                {"revision": r.number, "containment": r.containment, "provenance": r.provenance}
                for r in sorted(result.record.revisions, key=lambda r: r.number)
            ],
            "current_subject_disposition": asdict(result.record.current_disposition),
            "retained_disposition_transitions": [
                asdict(event) for event in result.record.retained_disposition_transitions
            ],
            "canonical_presence": result.record.canonical_presence,
            "acceptance_criteria_refs": [
                asdict(ref) for ref in result.selected_revision.acceptance_criteria_refs
            ],
            "authored_relations": [asdict(relation) for relation in result.relations],
            "relation_resolution": {
                "status": "incomplete" if result.relation_conflicts else "complete",
                "scope": "supplied_snapshots",
                "conflicts": [asdict(conflict) for conflict in result.relation_conflicts],
            },
        }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--workspace-identity", required=True)
    parser.add_argument("--subject-class", choices=[c.value for c in SubjectClass], required=True)
    parser.add_argument("--subject-id", required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--revision", type=int)
    selection.add_argument("--current", action="store_true")
    args = parser.parse_args(argv)
    try:
        index = load_subject_index(args.snapshot)
        ref = SubjectRef(args.workspace_identity, SubjectClass(args.subject_class), args.subject_id)
        result = (
            index.lookup_current(ref) if args.current else index.lookup_exact(ref, args.revision)
        )
    except (ValueError, TypeError) as exc:
        print(
            json.dumps(
                {
                    "artifact_kind": "subject_lookup_result",
                    "schema_version": 1,
                    "status": "invalid_input",
                    "diagnostic": str(exc),
                    "canonical_mutations_allowed": False,
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(lookup_payload(result), indent=2, sort_keys=True))
    return 0 if result.status == "resolved" and not result.relation_conflicts else 1


if __name__ == "__main__":
    sys.exit(main())
