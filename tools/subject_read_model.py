"""Immutable, read-only subject lookup over explicitly supplied snapshots (SG-SPEC-0068)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SubjectClass(str, Enum):
    REQUIREMENT = "Requirement"
    CRITERION = "criterion"


def require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be non-empty text without surrounding whitespace")


def require_revision(value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError("revision must be a positive integer")


def require_tuple(value: object, label: str) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{label} must be an immutable tuple")


@dataclass(frozen=True)
class SubjectRef:
    workspace_identity: str
    subject_class: SubjectClass
    local_subject_id: str

    def __post_init__(self) -> None:
        require_text(self.workspace_identity, "workspace_identity")
        require_text(self.local_subject_id, "local_subject_id")
        if not isinstance(self.subject_class, SubjectClass):
            raise ValueError("subject_class must be Requirement or criterion")

    @property
    def identity(self) -> tuple[str, str]:
        return self.workspace_identity, self.local_subject_id


@dataclass(frozen=True)
class RevisionSelection:
    subject: SubjectRef
    mode: str
    revision: int | None = None

    def __post_init__(self) -> None:
        if self.mode == "exact":
            require_revision(self.revision)
        elif self.mode != "current" or self.revision is not None:
            raise ValueError("selection must be exact with revision, or current without revision")


@dataclass(frozen=True)
class SubjectRevision:
    number: int
    predecessor: int | None
    statement: str
    containment: str
    provenance: str
    acceptance_criteria_refs: tuple[RevisionSelection, ...] = ()

    def __post_init__(self) -> None:
        require_revision(self.number)
        if self.number == 1:
            if self.predecessor is not None:
                raise ValueError("revision 1 must have no same-identity predecessor")
        else:
            require_revision(self.predecessor)
            if self.predecessor != self.number - 1:
                raise ValueError("revision must name its immediate same-identity predecessor")
        for label in ("statement", "containment", "provenance"):
            require_text(getattr(self, label), label)
        require_tuple(self.acceptance_criteria_refs, "acceptance_criteria_refs")
        if any(
            r.subject.subject_class != SubjectClass.CRITERION or r.mode != "exact"
            for r in self.acceptance_criteria_refs
        ):
            raise ValueError("acceptance_criteria_refs must pin exact criterion revisions")
        if len({r.subject.identity for r in self.acceptance_criteria_refs}) != len(
            self.acceptance_criteria_refs
        ):
            raise ValueError("duplicate acceptance criterion reference")
        object.__setattr__(
            self,
            "acceptance_criteria_refs",
            tuple(sorted(self.acceptance_criteria_refs, key=lambda r: r.subject.identity)),
        )


@dataclass(frozen=True)
class CurrentSubjectDisposition:
    state: str
    basis_ref: str
    observation_provenance: str

    def __post_init__(self) -> None:
        if self.state not in {"active", "retired"}:
            raise ValueError("current disposition must be active or retired")
        require_text(self.basis_ref, "disposition event or origin reference")
        require_text(self.observation_provenance, "disposition observation provenance")


@dataclass(frozen=True)
class DispositionTransition:
    event_ref: str
    transition: str
    provenance: str

    def __post_init__(self) -> None:
        require_text(self.event_ref, "disposition event_ref")
        require_text(self.provenance, "disposition transition provenance")
        if self.transition not in {"activation", "withdrawal"}:
            raise ValueError("disposition transition must be activation or withdrawal")

    @property
    def resulting_state(self) -> str:
        return {"activation": "active", "withdrawal": "retired"}[self.transition]


@dataclass(frozen=True)
class RelationEndpoint:
    role: str
    selection: RevisionSelection


@dataclass(frozen=True)
class RelationSource:
    workspace_identity: str
    dataset_identity: str

    def __post_init__(self) -> None:
        require_text(self.workspace_identity, "relation source workspace_identity")
        require_text(self.dataset_identity, "relation source dataset_identity")


@dataclass(frozen=True)
class SubjectRelation:
    relation_id: str
    kind: str
    endpoints: tuple[RelationEndpoint, ...]
    provenance: str
    source: RelationSource

    def __post_init__(self) -> None:
        if not isinstance(self.source, RelationSource):
            raise ValueError("relation source must be a RelationSource")
        require_tuple(self.endpoints, "endpoints")
        require_text(self.relation_id, "relation_id")
        require_text(self.provenance, "relation provenance")
        roles = {
            "decomposes_into": ("source", "result"),
            "composed_from": ("result", "contributor"),
        }
        if self.kind not in roles:
            raise ValueError("relation kind must be decomposes_into or composed_from")
        one, many = roles[self.kind]
        if (
            sum(e.role == one for e in self.endpoints) != 1
            or sum(e.role == many for e in self.endpoints) < 2
            or any(e.role not in {one, many} for e in self.endpoints)
        ):
            raise ValueError(f"{self.kind} needs one {one} and at least two {many} endpoints")
        refs = [e.selection.subject for e in self.endpoints]
        if len({r.subject_class for r in refs}) != 1:
            raise ValueError("relation endpoints must have the same subject class")
        if len({r.identity for r in refs}) != len(refs):
            raise ValueError("relation endpoints must have distinct subject identities")
        object.__setattr__(
            self,
            "endpoints",
            tuple(sorted(self.endpoints, key=lambda e: (e.role, e.selection.subject.identity))),
        )


@dataclass(frozen=True)
class SubjectRecord:
    reference: SubjectRef
    current_revision: int
    revisions: tuple[SubjectRevision, ...]
    current_disposition: CurrentSubjectDisposition
    canonical_presence: str | None
    retained_disposition_transitions: tuple[DispositionTransition, ...] = ()

    def __post_init__(self) -> None:
        require_tuple(self.revisions, "revisions")
        require_tuple(self.retained_disposition_transitions, "retained_disposition_transitions")
        events = self.retained_disposition_transitions
        if len({event.event_ref for event in events}) != len(events):
            raise ValueError("duplicate disposition event_ref")
        if any(
            event.event_ref == self.current_disposition.basis_ref
            and event.resulting_state != self.current_disposition.state
            for event in events
        ):
            raise ValueError("current disposition contradicts its retained basis event")
        # Canonical presentation order is not event chronology or current-state selection.
        object.__setattr__(
            self,
            "retained_disposition_transitions",
            tuple(sorted(events, key=lambda event: event.event_ref)),
        )
        require_revision(self.current_revision)
        numbers = [r.number for r in self.revisions]
        if len(numbers) != len(set(numbers)):
            raise ValueError("conflicting_revision_successor: duplicate revision number")
        object.__setattr__(self, "revisions", tuple(sorted(self.revisions, key=lambda r: r.number)))
        if self.current_revision not in numbers or any(n > self.current_revision for n in numbers):
            raise ValueError(
                "current_revision must identify the latest explicitly retained revision"
            )
        if self.reference.subject_class == SubjectClass.REQUIREMENT:
            if self.canonical_presence not in {"active", "historical_lineage_only"}:
                raise ValueError("Requirement must state canonical presence")
        elif self.canonical_presence is not None or any(
            r.acceptance_criteria_refs for r in self.revisions
        ):
            raise ValueError(
                "criterion cannot declare canonical presence or own acceptance criteria"
            )


@dataclass(frozen=True)
class WorkspaceSnapshot:
    """One declared source snapshot. Equal dataset identities declare replicas, not trust."""

    workspace_identity: str
    dataset_identity: str
    subjects: tuple[SubjectRecord, ...]
    relations: tuple[SubjectRelation, ...] = ()

    def __post_init__(self) -> None:
        require_text(self.workspace_identity, "workspace_identity")
        require_text(self.dataset_identity, "dataset_identity")
        require_tuple(self.subjects, "subjects")
        require_tuple(self.relations, "relations")
        identities = [r.reference.identity for r in self.subjects]
        if any(r.reference.workspace_identity != self.workspace_identity for r in self.subjects):
            raise ValueError("subject reference must belong to its declared workspace")
        if len(identities) != len(set(identities)):
            raise ValueError(
                "duplicate_subject_identity: local IDs cannot be shared across classes"
            )
        if len({r.relation_id for r in self.relations}) != len(self.relations):
            raise ValueError("duplicate relation ID")
        source = RelationSource(self.workspace_identity, self.dataset_identity)
        if any(r.source != source for r in self.relations):
            raise ValueError("relation source must match its containing workspace and dataset")


@dataclass(frozen=True)
class RelationSourceConflict:
    workspace_identity: str
    dataset_identities: tuple[str, ...]
    reason: str = "ambiguous_workspace_identity"

    def __post_init__(self) -> None:
        require_text(self.workspace_identity, "conflicting workspace_identity")
        require_tuple(self.dataset_identities, "conflicting dataset_identities")
        for identity in self.dataset_identities:
            require_text(identity, "conflicting dataset_identity")


@dataclass(frozen=True)
class LookupResult:
    status: str
    requested: RevisionSelection
    record: SubjectRecord | None = None
    selected_revision: SubjectRevision | None = None
    relations: tuple[SubjectRelation, ...] = ()
    relation_conflicts: tuple[RelationSourceConflict, ...] = ()

    def __post_init__(self) -> None:
        require_tuple(self.relations, "relations")
        require_tuple(self.relation_conflicts, "relation_conflicts")


@dataclass(frozen=True)
class SubjectIndex:
    snapshots: tuple[WorkspaceSnapshot, ...]

    def __post_init__(self) -> None:
        require_tuple(self.snapshots, "snapshots")
        errors = self.reference_errors()
        if errors:
            raise ValueError("unresolved snapshot references: " + "; ".join(errors))

    def lookup_exact(self, reference: SubjectRef, revision: int) -> LookupResult:
        return self._lookup(RevisionSelection(reference, "exact", revision))

    def lookup_current(self, reference: SubjectRef) -> LookupResult:
        return self._lookup(RevisionSelection(reference, "current"))

    def _workspace(self, identity: str) -> tuple[str, WorkspaceSnapshot | None]:
        matches = [s for s in self.snapshots if s.workspace_identity == identity]
        if not matches:
            return "unknown_workspace_identity", None
        datasets = {s.dataset_identity for s in matches}
        if any(
            s.dataset_identity in datasets and s.workspace_identity != identity
            for s in self.snapshots
        ):
            return "ambiguous_workspace_identity", None
        if len(datasets) != 1:
            return "ambiguous_workspace_identity", None
        first = matches[0]
        # Ordering is not identity; only identical declared replicas can be coalesced.
        if any(
            set(s.subjects) != set(first.subjects) or set(s.relations) != set(first.relations)
            for s in matches[1:]
        ):
            return "ambiguous_workspace_identity", None
        return "resolved", first

    def _lookup(self, request: RevisionSelection) -> LookupResult:
        status, workspace = self._workspace(request.subject.workspace_identity)
        if workspace is None:
            return LookupResult(status, request)
        record = next(
            (r for r in workspace.subjects if r.reference.identity == request.subject.identity),
            None,
        )
        if record is None:
            return LookupResult("unknown_subject_id", request)
        if record.reference.subject_class != request.subject.subject_class:
            return LookupResult("subject_class_mismatch", request)
        number = record.current_revision if request.mode == "current" else request.revision
        revision = next((r for r in record.revisions if r.number == number), None)
        if revision is None:
            return LookupResult("unavailable_revision", request)
        relations, conflicts = self._relations(request.subject)
        return LookupResult("resolved", request, record, revision, relations, conflicts)

    def _relations(
        self, reference: SubjectRef
    ) -> tuple[tuple[SubjectRelation, ...], tuple[RelationSourceConflict, ...]]:
        relations: list[SubjectRelation] = []
        conflicts: list[RelationSourceConflict] = []

        def mentions(relation: SubjectRelation) -> bool:
            return any(
                e.selection.subject.identity == reference.identity for e in relation.endpoints
            )

        for identity in sorted({s.workspace_identity for s in self.snapshots}):
            _, source = self._workspace(identity)
            if source is None:
                candidates = [s for s in self.snapshots if s.workspace_identity == identity]
                if any(mentions(r) for s in candidates for r in s.relations):
                    conflicts.append(
                        RelationSourceConflict(
                            identity, tuple(sorted({s.dataset_identity for s in candidates}))
                        )
                    )
                continue
            relations.extend(
                r for r in sorted(source.relations, key=lambda r: r.relation_id) if mentions(r)
            )
        return tuple(relations), tuple(conflicts)

    def reference_errors(self) -> tuple[str, ...]:
        """Check supplied endpoints; never infer or manufacture missing records."""
        errors: list[str] = []
        for snapshot in self.snapshots:
            if self._workspace(snapshot.workspace_identity)[1] is None:
                continue  # Preserve the explicit ambiguous workspace lookup result.
            selections = [
                ref
                for subject in snapshot.subjects
                for revision in subject.revisions
                for ref in revision.acceptance_criteria_refs
            ]
            selections += [e.selection for r in snapshot.relations for e in r.endpoints]
            for selection in selections:
                result = self._lookup(selection)
                if result.status != "resolved":
                    errors.append(f"{selection.subject.identity}: {result.status}")
        return tuple(sorted(set(errors)))
