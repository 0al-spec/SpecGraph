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
    CriterionNodeFields,
    CurrentSubjectDisposition,
    DispositionTransition,
    LookupResult,
    NodeProvenance,
    RelationEndpoint,
    RelationSource,
    RequirementNodeFields,
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


def _require_string_trace_keys(value: object) -> None:
    """Reject YAML keys that JSON would rewrite, including in nested trace data."""
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise SubjectDocumentError("trace_context mappings must use string keys")
        for item in value.values():
            _require_string_trace_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _require_string_trace_keys(item)


def parse_subject_ref(value: object) -> SubjectRef:
    data = _object(value, {"workspace_identity", "subject_class", "local_subject_id"})
    return SubjectRef(
        data["workspace_identity"], SubjectClass(data["subject_class"]), data["local_subject_id"]
    )


def _selection(value: object) -> RevisionSelection:
    data = _object(value, {"subject", "mode"}, {"revision"})
    return RevisionSelection(parse_subject_ref(data["subject"]), data["mode"], data.get("revision"))


def parse_subject_revision(value: object) -> SubjectRevision:
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
        {"node_fields", "revision_scope"},
    )
    if ("node_fields" in data) != ("revision_scope" in data):
        raise SubjectDocumentError("node_fields and revision_scope must be supplied together")
    return SubjectRevision(
        number=data["number"],
        predecessor=data["predecessor"],
        statement=data["statement"],
        containment=data["containment"],
        provenance=data["provenance"],
        acceptance_criteria_refs=tuple(
            _selection(v) for v in _list(data["acceptance_criteria_refs"])
        ),
        node_fields=parse_node_fields(data["node_fields"]) if "node_fields" in data else None,
        revision_scope=data.get("revision_scope"),
    )


def parse_node_fields(value: object) -> RequirementNodeFields | CriterionNodeFields:
    """Decode complete retained metadata; a title-only record denotes a criterion."""
    if isinstance(value, Mapping) and set(value) == {"title"}:
        return CriterionNodeFields(**value)
    data = _object(value, {"title", "status", "authority_class", "source_ref", "provenance"})
    provenance = dict(
        _object(
            data["provenance"],
            {"actor_id", "authority_class", "recorded_at"},
            {"source_ref", "source_system", "source_confidence", "notes", "trace_context"},
        )
    )
    provenance["present_optional_fields"] = tuple(
        sorted(set(provenance) - {"actor_id", "authority_class", "recorded_at"})
    )
    if "trace_context" in provenance:
        _require_string_trace_keys(provenance["trace_context"])
        provenance["trace_context_json"] = json.dumps(
            provenance.pop("trace_context"), sort_keys=True, ensure_ascii=False, allow_nan=False
        )
    return RequirementNodeFields(
        data["title"],
        data["status"],
        data["authority_class"],
        data["source_ref"],
        NodeProvenance(**provenance),
    )


def revision_payload(revision: SubjectRevision) -> dict:
    """Keep legacy exchange output stable; export source metadata without losing trace shape."""
    result = asdict(revision)
    if revision.node_fields is None:
        result.pop("node_fields")
        result.pop("revision_scope")
    elif isinstance(revision.node_fields, RequirementNodeFields):
        provenance = result["node_fields"]["provenance"]
        trace = provenance.pop("trace_context_json")
        supplied = provenance.pop("present_optional_fields") or ()
        for key in list(provenance):
            if provenance[key] is None and key not in supplied:
                provenance.pop(key)
        if trace is not None:
            provenance["trace_context"] = json.loads(trace)
    return result


def snapshot_payload(index: SubjectIndex) -> dict:
    """Export an explicit exchange snapshot, preserving its declared dataset bindings."""
    workspaces = []
    for workspace in index.snapshots:
        subjects = []
        for subject in workspace.subjects:
            record = asdict(subject)
            record["revisions"] = [revision_payload(r) for r in subject.revisions]
            record["retained_disposition_transitions"] = [
                asdict(event) for event in subject.disposition_history
            ]
            if subject.retained_disposition_order is None:
                record.pop("retained_disposition_order")
            subjects.append(record)
        relations = []
        for relation in workspace.relations:
            value = asdict(relation)
            value.pop("source")
            relations.append(value)
        workspaces.append(
            {
                "workspace_identity": workspace.workspace_identity,
                "dataset_identity": workspace.dataset_identity,
                "subjects": subjects,
                "relations": relations,
            }
        )
    # JSON's array shape is part of this boundary; core collections remain tuples.
    return json.loads(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_kind": "subject_read_snapshot",
                "workspaces": workspaces,
            }
        )
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
        {"retained_disposition_order"},
    )
    disposition = _object(
        data["current_disposition"], {"state", "basis_ref", "observation_provenance"}
    )
    return SubjectRecord(
        reference=parse_subject_ref(data["reference"]),
        current_revision=data["current_revision"],
        revisions=tuple(parse_subject_revision(v) for v in _list(data["revisions"])),
        current_disposition=CurrentSubjectDisposition(**disposition),
        canonical_presence=data["canonical_presence"],
        retained_disposition_transitions=tuple(
            DispositionTransition(**_object(v, {"event_ref", "transition", "provenance"}))
            for v in _list(data["retained_disposition_transitions"])
        ),
        retained_disposition_order=(
            tuple(_list(data["retained_disposition_order"]))
            if "retained_disposition_order" in data
            else None
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
            "revision": revision_payload(result.selected_revision),
            "current_revision": result.record.current_revision,
            "retained_containment_history": [
                {"revision": r.number, "containment": r.containment, "provenance": r.provenance}
                for r in sorted(result.record.revisions, key=lambda r: r.number)
            ],
            "current_subject_disposition": asdict(result.record.current_disposition),
            "retained_disposition_transitions": [
                asdict(event) for event in result.record.disposition_history
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
