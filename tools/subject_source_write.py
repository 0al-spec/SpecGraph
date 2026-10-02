#!/usr/bin/env python3
"""Prepare or explicitly publish one authorized SG-SPEC-0069 origin/revision batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path

from yaml import YAMLError

from spec_yaml import dump_canonical_yaml, load_yaml_text
from subject_canonical_source import (
    DECLARATION,
    CanonicalTopologySelection,
    _storage_path,
    _version,
    parse_topology_selection,
    read_canonical_source,
)
from subject_read_model import SubjectRecord, SubjectRef, require_text, require_tuple
from subject_read_model_io import SubjectDocumentError, _list, _object, parse_subject_ref
from subject_source_git import SubjectSourceCommit, SubjectSourceConflict, selected_source_commit


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _require_digest(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise SubjectDocumentError("source digest must be a complete lowercase SHA256")


@dataclass(frozen=True)
class SubjectSourceChange:
    operation: str
    subject: SubjectRef
    path: str
    document_yaml: str
    expected_prior_sha256: str | None

    def __post_init__(self) -> None:
        if self.operation not in {"origin", "content_revision"}:
            raise SubjectDocumentError(
                "unsupported operation; only origin/content_revision are allowed"
            )
        if not isinstance(self.subject, SubjectRef):
            raise SubjectDocumentError("change requires a typed subject")
        _storage_path(self.path, self.subject)
        require_text(self.document_yaml.rstrip("\n"), "proposed record YAML")
        if self.operation == "origin":
            if self.expected_prior_sha256 is not None:
                raise SubjectDocumentError("origins require a no-existing-subject precondition")
        else:
            _require_digest(self.expected_prior_sha256)


@dataclass(frozen=True)
class SubjectSourceWriteRequest:
    source_ref: str
    expected_commit: str
    recorded_at: str
    topology: CanonicalTopologySelection
    expected_source_file_sha256: tuple[tuple[str, str], ...]
    changes: tuple[SubjectSourceChange, ...]
    workspace_declaration_yaml: str | None = None

    def __post_init__(self) -> None:
        require_text(self.source_ref, "source_ref")
        require_text(self.recorded_at, "recorded_at")
        if datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00")).tzinfo is None:
            raise SubjectDocumentError("publication recorded_at requires a timezone")
        if not isinstance(self.topology, CanonicalTopologySelection):
            raise SubjectDocumentError("write request requires a typed topology")
        require_tuple(self.changes, "changes")
        require_tuple(self.expected_source_file_sha256, "expected_source_file_sha256")
        if not self.changes or any(not isinstance(c, SubjectSourceChange) for c in self.changes):
            raise SubjectDocumentError("write request requires typed subject changes")
        if len({c.subject for c in self.changes}) != len(self.changes) or len(
            {c.path for c in self.changes}
        ) != len(self.changes):
            raise SubjectDocumentError("duplicate subject/path in write request")
        for entry in self.expected_source_file_sha256:
            require_tuple(entry, "expected source digest entry")
            path, digest = entry
            require_text(path, "expected source path")
            _require_digest(digest)
        if len(dict(self.expected_source_file_sha256)) != len(self.expected_source_file_sha256):
            raise SubjectDocumentError("duplicate expected source path")

    def digest(self) -> str:
        """Version-1 digest: canonical JSON of the immutable parsed request."""
        return _sha256(
            json.dumps(
                asdict(self),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )


@dataclass(frozen=True)
class SubjectWriteAuthorization:
    request_sha256: str
    decision_ref: str
    reviewer: str
    reviewer_authority: str
    recorded_at: str
    transition_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_digest(self.request_sha256)
        for field in ("decision_ref", "reviewer", "recorded_at"):
            require_text(getattr(self, field), field)
        if self.reviewer_authority != "human_project_author":
            raise SubjectDocumentError(
                "publication requires explicit human_project_author authorization"
            )
        if datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00")).tzinfo is None:
            raise SubjectDocumentError("authorization recorded_at requires a timezone")
        require_tuple(self.transition_refs, "authorized transition refs")
        if not self.transition_refs or len(set(self.transition_refs)) != len(self.transition_refs):
            raise SubjectDocumentError("authorization requires unique transition references")
        for reference in self.transition_refs:
            require_text(reference, "authorized transition reference")


def parse_write_request(value: object) -> SubjectSourceWriteRequest:
    data = _object(
        value,
        {
            "schema_version",
            "artifact_kind",
            "source_ref",
            "expected_commit",
            "recorded_at",
            "topology_selection",
            "expected_source_file_sha256",
            "changes",
        },
        {"workspace_declaration"},
    )
    _version(data, "subject_source_write_request")
    digests = data["expected_source_file_sha256"]
    if not isinstance(digests, dict):
        raise SubjectDocumentError("expected source digests must be a path/SHA256 mapping")
    changes = []
    for value in _list(data["changes"]):
        item = _object(value, {"operation", "path", "expected_prior_sha256", "proposed_record"})
        document = item["proposed_record"]
        if not isinstance(document, dict):
            raise SubjectDocumentError("proposed_record must be a mapping")
        changes.append(
            SubjectSourceChange(
                item["operation"],
                parse_subject_ref(document["subject"]),
                item["path"],
                dump_canonical_yaml(document),
                item["expected_prior_sha256"],
            )
        )
    return SubjectSourceWriteRequest(
        data["source_ref"],
        data["expected_commit"],
        data["recorded_at"],
        parse_topology_selection(data["topology_selection"]),
        tuple(sorted(digests.items())),
        tuple(changes),
        dump_canonical_yaml(data["workspace_declaration"])
        if "workspace_declaration" in data
        else None,
    )


def parse_write_authorization(value: object) -> SubjectWriteAuthorization:
    data = _object(
        value,
        {
            "schema_version",
            "artifact_kind",
            "request_sha256",
            "decision_ref",
            "reviewer",
            "reviewer_authority",
            "recorded_at",
            "transition_refs",
        },
    )
    _version(data, "subject_source_write_authorization")
    return SubjectWriteAuthorization(
        data["request_sha256"],
        data["decision_ref"],
        data["reviewer"],
        data["reviewer_authority"],
        data["recorded_at"],
        tuple(_list(data["transition_refs"])),
    )


def _records(read) -> dict[SubjectRef, SubjectRecord]:
    return {record.reference: record for record in read.index.snapshots[0].subjects}


def _check_transition(
    change: SubjectSourceChange, before: SubjectRecord | None, after: SubjectRecord
):
    if change.operation == "origin":
        if before is not None:
            raise SubjectSourceConflict("origin subject already exists")
        if (
            len(after.revisions) != 1
            or len(after.disposition_history) != 1
            or (after.disposition_history[0].transition != "activation")
        ):
            raise SubjectDocumentError("origin requires revision 1 and one activation event")
    else:
        if before is None:
            raise SubjectDocumentError("content revision requires an existing subject")
        if (
            after.revisions[:-1] != before.revisions
            or after.current_revision != before.current_revision + 1
        ):
            raise SubjectDocumentError(
                "content revision must append exactly one revision; history is immutable"
            )
        if after.revisions[-1].containment != before.revisions[-1].containment:
            raise SubjectDocumentError("containment_move is unsupported by the first writer")
        if after.current_disposition != before.current_disposition or (
            after.disposition_history != before.disposition_history
        ):
            raise SubjectDocumentError("disposition changes are unsupported by the first writer")


def write_subject_source(
    repository: Path,
    request: SubjectSourceWriteRequest,
    *,
    authorization: SubjectWriteAuthorization | None = None,
    preview: bool = False,
) -> dict:
    """Validate the full candidate, verify its immutable commit, then optionally publish one ref."""
    if not isinstance(request, SubjectSourceWriteRequest):
        raise SubjectDocumentError("a typed write request is required")
    if not preview and not isinstance(authorization, SubjectWriteAuthorization):
        raise SubjectDocumentError("publication requires an explicit typed authorization")
    if authorization is not None and authorization.request_sha256 != request.digest():
        raise SubjectDocumentError("authorization does not bind this exact write request")
    commit_id = selected_source_commit(repository, request.source_ref)
    if commit_id != request.expected_commit:
        raise SubjectSourceConflict("expected source commit no longer matches the selected ref")
    source = SubjectSourceCommit(repository, commit_id)
    blobs = source.blobs()
    digests = {blob.path: _sha256(blob.content) for blob in blobs}
    if digests != dict(request.expected_source_file_sha256):
        raise SubjectSourceConflict(
            "expected prior source digests do not match the complete source"
        )
    origins = {change.subject for change in request.changes if change.operation == "origin"}
    existing_subjects = {
        parse_subject_ref(load_yaml_text(blob.content.decode("utf-8"))["subject"])
        for blob in blobs
        if blob.path != DECLARATION
    }
    before_topology = replace(
        request.topology,
        requirements=tuple(
            item
            for item in request.topology.requirements
            if item.subject not in origins or item.subject in existing_subjects
        ),
    )
    with source.export() as candidate_root:
        declaration = candidate_root / DECLARATION
        if declaration.exists():
            if request.workspace_declaration_yaml is not None:
                raise SubjectDocumentError("workspace declaration is immutable after allocation")
            before = _records(read_canonical_source(candidate_root, before_topology))
        else:
            if blobs or request.workspace_declaration_yaml is None or before_topology.requirements:
                raise SubjectDocumentError(
                    "bootstrap requires an absent source and explicit declaration"
                )
            before = {}
            declaration.write_text(request.workspace_declaration_yaml, encoding="utf-8")
        files = {}
        if request.workspace_declaration_yaml is not None:
            files[DECLARATION] = request.workspace_declaration_yaml.encode("utf-8")
        for change in request.changes:
            if change.subject.workspace_identity != request.topology.workspace_identity:
                raise SubjectDocumentError("write subject belongs to another workspace")
            target = candidate_root / change.path
            if change.operation == "origin" and (target.exists() or change.subject in before):
                raise SubjectSourceConflict("origin requires no existing subject or target file")
            if (
                change.operation == "content_revision"
                and digests.get(change.path) != change.expected_prior_sha256
            ):
                raise SubjectSourceConflict(
                    "content revision expected prior source digest does not match"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            content = change.document_yaml.encode("utf-8")
            target.write_bytes(content)
            files[change.path] = content
        candidate_read = read_canonical_source(candidate_root, request.topology)
        after = _records(candidate_read)
        if set(after) != set(before) | origins:
            raise SubjectDocumentError("candidate must retain all existing subject identities")
        transitions = set()
        if request.workspace_declaration_yaml is not None:
            transitions.add(candidate_read.declaration_provenance)
        for change in request.changes:
            record = after[change.subject]
            _check_transition(change, before.get(change.subject), record)
            transitions.add(record.revisions[-1].provenance)
            if change.operation == "origin":
                transitions.add(record.disposition_history[0].provenance)
        if authorization is not None and transitions != set(authorization.transition_refs):
            raise SubjectDocumentError(
                "authorization must cover exactly the authored transition references"
            )
        proposed_commit = source.candidate_commit(files, request.recorded_at, request.digest())
        source.check_candidate_scope(proposed_commit, set(files))
        # Validate the actual Git objects being published, not just the staging files.
        with SubjectSourceCommit(repository, proposed_commit).export() as committed_root:
            committed = read_canonical_source(committed_root, request.topology)
            if committed.index != candidate_read.index or (
                committed.source_file_sha256 != candidate_read.source_file_sha256
            ):
                raise SubjectDocumentError(
                    "prepared Git source disagrees with the validated candidate"
                )
        payload = {
            "schema_version": 1,
            "artifact_kind": "subject_source_write_result",
            "status": "prepared" if preview else "published",
            "publication_backend": "git_commit_compare_and_swap_v1",
            "source_ref": request.source_ref,
            "prior_commit": commit_id,
            "candidate_commit": proposed_commit,
            "request_sha256": request.digest(),
            "source_file_sha256": dict(committed.source_file_sha256),
            "workspace_identity": request.topology.workspace_identity,
            "dataset_identity": request.topology.dataset_identity,
            "candidate_validation": "passed",
            "source_ref_updated": not preview,
            "authorization_ref": authorization.decision_ref if authorization else None,
            "authorization_verification": "operator_supplied_not_attested"
            if authorization
            else "not_supplied",
            "canonical_readiness": "not_evaluated",
            "ready_for_materialization": False,
            "trusted_runtime_receipt": False,
        }
    # Cleanup completes before the authoritative mutation; no fallible I/O follows CAS.
    if not preview:
        source.publish(request.source_ref, proposed_commit)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preview", action="store_true")
    mode.add_argument("--authorization", type=Path)
    args = parser.parse_args(argv)
    try:
        request = parse_write_request(load_yaml_text(args.request.read_text(encoding="utf-8")))
        authorization = (
            parse_write_authorization(
                load_yaml_text(args.authorization.read_text(encoding="utf-8"))
            )
            if args.authorization
            else None
        )
        payload = write_subject_source(
            args.repository_root, request, authorization=authorization, preview=args.preview
        )
        code = 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, YAMLError) as exc:
        conflict = isinstance(exc, SubjectSourceConflict)
        payload = {
            "schema_version": 1,
            "artifact_kind": "subject_source_write_result",
            "status": "source_conflict" if conflict else "invalid_input",
            "diagnostic": str(exc),
            "source_ref_updated": False,
        }
        code = 3 if conflict else 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
