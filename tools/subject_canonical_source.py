#!/usr/bin/env python3
"""Read SG-SPEC-0069 storage from an explicit root and caller-selected topology.

No identity allocation, source writes, evidence transfer or readiness evaluation.
Topology selection is an I/O exchange, not another canonical storage format.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import UUID

from yaml import YAMLError

from spec_yaml import dump_canonical_yaml, load_yaml_text
from subject_read_model import (
    CriterionNodeFields,
    CurrentSubjectDisposition,
    DispositionTransition,
    RequirementNodeFields,
    SubjectClass,
    SubjectIndex,
    SubjectRecord,
    SubjectRef,
    WorkspaceSnapshot,
    require_text,
    require_tuple,
)
from subject_read_model_io import (
    SubjectDocumentError,
    _list,
    _object,
    lookup_payload,
    parse_node_fields,
    parse_subject_ref,
    parse_subject_revision,
    snapshot_payload,
)

DECLARATION = "specs/workspace_identity.yaml"
DIRECTORIES = {SubjectClass.REQUIREMENT: "requirements", SubjectClass.CRITERION: "criteria"}


@dataclass(frozen=True)
class CanonicalRequirementPresence:
    subject: SubjectRef
    canonical_presence: str

    def __post_init__(self) -> None:
        if not isinstance(self.subject, SubjectRef):
            raise ValueError("topology presence requires a typed SubjectRef")
        if self.subject.subject_class != SubjectClass.REQUIREMENT:
            raise ValueError("topology presence must refer to a Requirement")
        if self.canonical_presence not in {"active", "historical_lineage_only"}:
            raise ValueError("invalid topology canonical_presence")


@dataclass(frozen=True)
class CanonicalTopologySelection:
    workspace_identity: str
    dataset_identity: str
    topology_ref: str
    governance_evidence_ref: str
    requirements: tuple[CanonicalRequirementPresence, ...]

    def __post_init__(self) -> None:
        for field in (
            "workspace_identity",
            "dataset_identity",
            "topology_ref",
            "governance_evidence_ref",
        ):
            require_text(getattr(self, field), field)
        require_tuple(self.requirements, "selected topology requirements")
        if any(not isinstance(item, CanonicalRequirementPresence) for item in self.requirements):
            raise ValueError("selected topology needs typed Requirement presence values")
        if any(
            item.subject.workspace_identity != self.workspace_identity for item in self.requirements
        ):
            raise ValueError("topology Requirement belongs to another workspace")
        identities = [item.subject.identity for item in self.requirements]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate topology Requirement identity")


@dataclass(frozen=True)
class CanonicalSourceRead:
    index: SubjectIndex
    declaration_provenance: str
    topology: CanonicalTopologySelection
    source_file_sha256: tuple[tuple[str, str], ...]
    source_root: Path

    def __post_init__(self) -> None:
        if not isinstance(self.index, SubjectIndex) or not isinstance(
            self.topology, CanonicalTopologySelection
        ):
            raise ValueError("source read requires a typed index and topology selection")
        require_text(self.declaration_provenance, "declaration provenance")
        if not isinstance(self.source_root, Path):
            raise ValueError("selected source root must be a Path")
        require_tuple(self.source_file_sha256, "source_file_sha256")
        for entry in self.source_file_sha256:
            require_tuple(entry, "source digest entry")
            if len(entry) != 2 or not re.fullmatch(r"[0-9a-f]{64}", entry[1]):
                raise ValueError("source digest entry needs a path and SHA256")
            require_text(entry[0], "source digest path")
        if len({path for path, _ in self.source_file_sha256}) != len(self.source_file_sha256):
            raise ValueError("duplicate source digest path")

    def audit_payload(self) -> dict:
        return {
            "schema_version": 1,
            "artifact_kind": "subject_canonical_source_read",
            "validation_status": "passed",
            "selected_source_root": str(self.source_root),
            "source_binding": {
                "workspace_identity": self.topology.workspace_identity,
                "dataset_identity": self.topology.dataset_identity,
                "workspace_declaration_provenance": self.declaration_provenance,
                "topology_ref": self.topology.topology_ref,
                "governance_evidence_ref": self.topology.governance_evidence_ref,
                "governance_evidence_verification": "caller_selected_not_attested",
            },
            "source_file_sha256": dict(self.source_file_sha256),
            "snapshot": snapshot_payload(self.index),
            "relation_scope": "stored_subject_records_only; external_relations_not_loaded",
            "canonical_mutations_allowed": False,
            "canonical_readiness": "not_evaluated",
            "ready_for_materialization": False,
        }


def parse_topology_selection(value: object) -> CanonicalTopologySelection:
    data = _object(
        value,
        {
            "schema_version",
            "artifact_kind",
            "workspace_identity",
            "dataset_identity",
            "topology_ref",
            "governance_evidence_ref",
            "requirements",
        },
    )
    _version(data, "subject_canonical_topology_selection")
    requirements = []
    for value in _list(data["requirements"]):
        entry = _object(value, {"subject", "canonical_presence"})
        requirements.append(
            CanonicalRequirementPresence(
                parse_subject_ref(entry["subject"]),
                entry["canonical_presence"],
            )
        )
    return CanonicalTopologySelection(
        data["workspace_identity"],
        data["dataset_identity"],
        data["topology_ref"],
        data["governance_evidence_ref"],
        tuple(requirements),
    )


def _version(data: dict, artifact_kind: str) -> None:
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise SubjectDocumentError("schema_version must be integer 1")
    if data["artifact_kind"] != artifact_kind:
        raise SubjectDocumentError(f"artifact_kind must be {artifact_kind}")


def _storage_path(value: str, reference: SubjectRef) -> str:
    require_text(value, "containment")
    path = PurePosixPath(value)
    expected = ("specs", DIRECTORIES[reference.subject_class])
    if str(path) != value or path.parts[:2] != expected or len(path.parts) < 3:
        raise SubjectDocumentError("containment must be a canonical source-relative path")
    if path.name != reference.local_subject_id + ".yaml":
        raise SubjectDocumentError("filename must preserve the exact local subject ID")
    if any(not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", part) for part in path.parts[2:-1]):
        raise SubjectDocumentError("grouping directories must use lowercase ASCII")
    return value


def _source_paths(root: Path) -> tuple[str, ...]:
    paths = [DECLARATION]
    specs = root / "specs"
    if specs.is_symlink() or not specs.is_dir():
        raise SubjectDocumentError("specs must be a real directory in the selected root")
    for directory in DIRECTORIES.values():
        pending = [specs / directory]
        while pending:
            current = pending.pop()
            if current.is_symlink():
                raise SubjectDocumentError("symlinks are forbidden in subject storage")
            if not current.exists():
                if current == specs / directory:
                    continue
                raise SubjectDocumentError("source tree changed during discovery")
            if current.is_dir():
                if current != specs / directory and not re.fullmatch(
                    r"[a-z0-9][a-z0-9._-]*", current.name
                ):
                    raise SubjectDocumentError("grouping directories must use lowercase ASCII")
                pending.extend(sorted(current.iterdir()))
            elif current.is_file() and current.suffix == ".yaml":
                paths.append(current.relative_to(root).as_posix())
            else:
                raise SubjectDocumentError("unsupported file in canonical subject storage")
    return tuple(sorted(paths))


def _record(document: dict, path: str, workspace: str, presence: dict) -> SubjectRecord:
    common = {
        "schema_version",
        "artifact_kind",
        "id",
        "title",
        "subject",
        "current_revision",
        "revisions",
        "current_disposition",
        "retained_disposition_transitions",
    }
    requirement = document.get("artifact_kind") == "requirement_node"
    metadata = (
        ("title", "status", "authority_class", "source_ref", "provenance")
        if requirement
        else ("title",)
    )
    data = _object(
        document,
        common
        | (
            {"kind", "status", "authority_class", "source_ref", "provenance"}
            if requirement
            else set()
        ),
    )
    _version(data, "requirement_node" if requirement else "acceptance_criterion_record")
    reference = parse_subject_ref(data["subject"])
    expected_class = SubjectClass.REQUIREMENT if requirement else SubjectClass.CRITERION
    if reference.subject_class != expected_class or reference.workspace_identity != workspace:
        raise SubjectDocumentError("subject class/workspace disagrees with its declared storage")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", reference.local_subject_id):
        raise SubjectDocumentError("local subject ID must use the approved ASCII convention")
    if data["id"] != reference.local_subject_id:
        raise SubjectDocumentError("id must equal subject.local_subject_id")
    _storage_path(path, reference)
    if requirement and data["kind"] != "requirement":
        raise SubjectDocumentError("Requirement node kind must be requirement")
    revisions = []
    for value in _list(data["revisions"]):
        _object(
            value,
            {
                "number",
                "predecessor",
                "node_fields",
                "statement",
                "containment",
                "provenance",
                "revision_scope",
                "acceptance_criteria_refs",
            },
        )
        revision = parse_subject_revision(value)
        expected_metadata = RequirementNodeFields if requirement else CriterionNodeFields
        if not isinstance(revision.node_fields, expected_metadata):
            raise SubjectDocumentError("retained node_fields disagree with subject class")
        _storage_path(revision.containment, reference)
        revisions.append(revision)
    numbers = sorted(revision.number for revision in revisions)
    if numbers != list(range(1, len(revisions) + 1)):
        raise SubjectDocumentError("canonical history must be a complete contiguous chain")
    if requirement:
        statuses = ("idea", "stub", "outlined", "specified", "linked", "reviewed", "frozen")
        ordered = sorted(revisions, key=lambda revision: revision.number)
        for previous, following in zip(ordered[:-1], ordered[1:], strict=True):
            before, after = previous.node_fields.status, following.node_fields.status
            if before == "frozen" or statuses.index(after) < statuses.index(before):
                raise SubjectDocumentError("frozen or regressed Requirement revision is forbidden")
    projection = parse_node_fields({field: data[field] for field in metadata})
    selected = next((r for r in revisions if r.number == data["current_revision"]), None)
    if selected is None or selected.node_fields != projection or selected.containment != path:
        raise SubjectDocumentError(
            "current node metadata/containment must match its retained revision"
        )
    events = tuple(
        DispositionTransition(**_object(value, {"event_ref", "transition", "provenance"}))
        for value in _list(data["retained_disposition_transitions"])
    )
    disposition = CurrentSubjectDisposition(
        **_object(
            data["current_disposition"],
            {"state", "basis_ref", "observation_provenance"},
        )
    )
    if (
        not events
        or events[-1].event_ref != disposition.basis_ref
        or events[-1].resulting_state != disposition.state
    ):
        raise SubjectDocumentError("current disposition must agree with the last authored event")
    if requirement and reference not in presence:
        raise SubjectDocumentError("Requirement has no selected governed topology presence")
    return SubjectRecord(
        reference,
        data["current_revision"],
        tuple(revisions),
        disposition,
        presence.get(reference) if requirement else None,
        events,
        tuple(event.event_ref for event in events),
    )


def read_canonical_source(root: Path, topology: CanonicalTopologySelection) -> CanonicalSourceRead:
    """Validate the complete declared tree without deriving identity or authority from paths."""
    try:
        if not isinstance(topology, CanonicalTopologySelection):
            raise SubjectDocumentError("an explicit typed topology selection is required")
        if root.is_symlink() or not root.is_dir():
            raise SubjectDocumentError("selected source root must be a real directory")
        root = root.resolve(strict=True)
        paths = _source_paths(root)
        documents, hashes = {}, []
        for path in paths:
            source = root / path
            if source.is_symlink() or not source.is_file():
                raise SubjectDocumentError("source record must be a real file")
            content = source.read_bytes()
            document = load_yaml_text(content.decode("utf-8"))
            if dump_canonical_yaml(document).encode() != content:
                raise SubjectDocumentError(f"{path}: noncanonical YAML formatting")
            documents[path] = document
            hashes.append((path, hashlib.sha256(content).hexdigest()))
        declaration = _object(
            documents[DECLARATION],
            {
                "schema_version",
                "artifact_kind",
                "workspace_identity",
                "provenance",
            },
        )
        _version(declaration, "subject_workspace_declaration")
        workspace = declaration["workspace_identity"]
        require_text(workspace, "workspace_identity")
        if not workspace.startswith("workspace:") or str(UUID(workspace[10:])) != workspace[10:]:
            raise SubjectDocumentError("workspace identity must use workspace:<lowercase UUID>")
        require_text(declaration["provenance"], "workspace declaration provenance")
        if workspace != topology.workspace_identity:
            raise SubjectDocumentError("topology selection disagrees with workspace declaration")
        presence = {item.subject: item.canonical_presence for item in topology.requirements}
        records = tuple(
            _record(documents[path], path, workspace, presence)
            for path in paths
            if path != DECLARATION
        )
        allocated = {}
        for record in records:
            key = record.reference.local_subject_id.lower()
            if key in allocated:
                raise SubjectDocumentError("portable namespace collision across subject records")
            allocated[key] = record.reference
        if set(presence) != {
            r.reference for r in records if r.reference.subject_class == SubjectClass.REQUIREMENT
        }:
            raise SubjectDocumentError(
                "topology selection must cover exactly the stored Requirements"
            )
        index = SubjectIndex((WorkspaceSnapshot(workspace, topology.dataset_identity, records),))
        # Detect ordinary concurrent changes; this is not an atomic filesystem snapshot/receipt.
        if paths != _source_paths(root) or any(
            (root / path).is_symlink()
            or hashlib.sha256((root / path).read_bytes()).hexdigest() != digest
            for path, digest in hashes
        ):
            raise SubjectDocumentError("source tree changed during read")
        return CanonicalSourceRead(index, declaration["provenance"], topology, tuple(hashes), root)
    except (OSError, ValueError, TypeError, UnicodeError, YAMLError) as exc:
        raise SubjectDocumentError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--topology-selection", type=Path, required=True)
    parser.add_argument("--subject-class", choices=[value.value for value in SubjectClass])
    parser.add_argument("--subject-id")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--revision", type=int)
    choice.add_argument("--current", action="store_true")
    args = parser.parse_args(argv)
    lookup_requested = any(
        (args.subject_class, args.subject_id, args.revision is not None, args.current)
    )
    if lookup_requested and not (
        args.subject_class and args.subject_id and (args.revision is not None or args.current)
    ):
        parser.error("lookup requires subject-class, subject-id and revision or current")
    try:
        topology = parse_topology_selection(
            load_yaml_text(args.topology_selection.read_text(encoding="utf-8"))
        )
        read = read_canonical_source(args.source_root, topology)
        payload = read.audit_payload()
        code = 0
        if lookup_requested:
            reference = SubjectRef(
                topology.workspace_identity, SubjectClass(args.subject_class), args.subject_id
            )
            result = (
                read.index.lookup_current(reference)
                if args.current
                else read.index.lookup_exact(reference, args.revision)
            )
            payload["lookup"] = lookup_payload(result)
            code = 0 if result.status == "resolved" else 1
    except (OSError, ValueError, TypeError, UnicodeError, YAMLError) as exc:
        payload = {
            "schema_version": 1,
            "artifact_kind": "subject_canonical_source_read",
            "status": "invalid_input",
            "diagnostic": str(exc),
            "canonical_mutations_allowed": False,
        }
        code = 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
