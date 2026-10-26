"""Opt-in append-only physical Intent/derived_from extension to subject storage.

Existing Requirement/criterion identities and snapshot exchanges stay unchanged.
Git source commits version the graph; version 1 only admits immutable origins.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from spec_yaml import dump_canonical_yaml
from subject_intent_derivation_spec import INTENT_DERIVATION_SPEC
from subject_intent_graph_append_spec import INTENT_GRAPH_APPEND_SPEC
from subject_intent_graph_context import IntentDerivationContext, IntentGraphAppendContext
from subject_read_model import (
    NodeProvenance,
    RevisionSelection,
    SubjectIndex,
    require_text,
    require_tuple,
)
from subject_read_model_io import (
    SubjectDocumentError,
    _list,
    _object,
    _selection,
    parse_node_fields,
    provenance_payload,
)

INTENT_GRAPH_PATH = "specs/intent_graph.yaml"


def _identifier(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise SubjectDocumentError("Intent graph IDs must use the shared ASCII convention")


@dataclass(frozen=True)
class CanonicalIntent:
    id: str
    title: str
    status: str
    authority_class: str
    source_ref: str
    provenance: NodeProvenance
    statement: str
    adoption_provenance: str
    revision: int = 1

    def __post_init__(self) -> None:
        _identifier(self.id)
        if type(self.revision) is not int or self.revision != 1:
            raise SubjectDocumentError("Intent extension v1 supports revision-1 origins only")
        for field in ("title", "status", "source_ref", "statement", "adoption_provenance"):
            require_text(getattr(self, field), field)
        if not isinstance(self.provenance, NodeProvenance) or (
            self.authority_class,
            self.source_ref,
        ) != (self.provenance.authority_class, self.provenance.source_ref):
            raise SubjectDocumentError("Intent metadata disagrees with its source provenance")

    def payload(self) -> dict:
        return {**asdict(self), "kind": "intent", "provenance": provenance_payload(self.provenance)}


@dataclass(frozen=True)
class IntentDerivation:
    id: str
    source: RevisionSelection
    target_intent_id: str
    target_revision: int
    adoption_provenance: str

    def __post_init__(self) -> None:
        _identifier(self.id)
        _identifier(self.target_intent_id)
        require_text(self.adoption_provenance, "relation adoption provenance")
        if not isinstance(self.source, RevisionSelection):
            raise SubjectDocumentError("derived_from requires a typed revision selection")
        if type(self.target_revision) is not int or self.target_revision != 1:
            raise SubjectDocumentError("Intent target must pin revision 1")

    def payload(self) -> dict:
        result = {**asdict(self), "kind": "derived_from"}
        result["source"]["subject"]["subject_class"] = self.source.subject.subject_class.value
        return result


@dataclass(frozen=True)
class CanonicalIntentGraph:
    workspace_identity: str
    intents: tuple[CanonicalIntent, ...] = ()
    derived_from: tuple[IntentDerivation, ...] = ()

    def __post_init__(self) -> None:
        require_text(self.workspace_identity, "Intent graph workspace")
        require_tuple(self.intents, "intents")
        require_tuple(self.derived_from, "derived_from")
        if any(not isinstance(i, CanonicalIntent) for i in self.intents) or any(
            not isinstance(e, IntentDerivation) for e in self.derived_from
        ):
            raise SubjectDocumentError("Intent graph requires typed origins and relations")
        keys = [item.id.lower() for item in (*self.intents, *self.derived_from)]
        if len(keys) != len(set(keys)):
            raise SubjectDocumentError("portable namespace collision in Intent graph")

    def payload(self) -> dict:
        return {
            "schema_version": 1,
            "artifact_kind": "subject_intent_graph",
            "workspace_identity": self.workspace_identity,
            "intents": [item.payload() for item in self.intents],
            "derived_from": [item.payload() for item in self.derived_from],
        }

    def validate_subjects(self, index: SubjectIndex) -> None:
        snapshot = index.snapshots[0]
        if snapshot.workspace_identity != self.workspace_identity:
            raise SubjectDocumentError("Intent graph belongs to another workspace")
        occupied = {r.reference.local_subject_id.lower() for r in snapshot.subjects}
        if occupied.intersection(i.id.lower() for i in (*self.intents, *self.derived_from)):
            raise SubjectDocumentError("portable namespace collision with stored subjects")
        roots = {(i.id, i.revision) for i in self.intents}
        for edge in self.derived_from:
            if not INTENT_DERIVATION_SPEC.is_satisfied_by(
                IntentDerivationContext(
                    edge.source.subject.subject_class.value,
                    edge.source.mode,
                    edge.source.subject.workspace_identity,
                    self.workspace_identity,
                    index.lookup_exact(edge.source.subject, edge.source.revision).status
                    == "resolved"
                    if edge.source.mode == "exact"
                    else False,
                    (edge.target_intent_id, edge.target_revision) in roots,
                )
            ):
                raise SubjectDocumentError(
                    "derived_from needs an existing exact Requirement and Intent in this workspace"
                )

    def additions(self, before: CanonicalIntentGraph | None) -> tuple:
        previous = before or CanonicalIntentGraph(self.workspace_identity)
        old = {
            item.id: dump_canonical_yaml(item.payload())
            for item in (*previous.intents, *previous.derived_from)
        }
        new = {
            item.id: dump_canonical_yaml(item.payload())
            for item in (*self.intents, *self.derived_from)
        }
        if not INTENT_GRAPH_APPEND_SPEC.is_satisfied_by(
            IntentGraphAppendContext(
                previous.workspace_identity,
                self.workspace_identity,
                tuple(old.items()),
                tuple(new.items()),
            )
        ):
            raise SubjectDocumentError(
                "Intent graph append must add origins and retain all existing records unchanged"
            )
        return tuple(item for item in (*self.intents, *self.derived_from) if item.id not in old)

    def paths_from(self, selection: RevisionSelection) -> tuple[tuple[str, str], ...]:
        """Explicit edges for this exact revision; membership supplies no implicit path."""
        return tuple((e.id, e.target_intent_id) for e in self.derived_from if e.source == selection)


def parse_intent_graph(value: object) -> CanonicalIntentGraph:
    data = _object(
        value, {"schema_version", "artifact_kind", "workspace_identity", "intents", "derived_from"}
    )
    if (
        type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or data["artifact_kind"] != "subject_intent_graph"
    ):
        raise SubjectDocumentError("unsupported Intent graph kind/version")
    intents = []
    for item in _list(data["intents"]):
        node = _object(
            item,
            {
                "id",
                "kind",
                "revision",
                "title",
                "status",
                "authority_class",
                "source_ref",
                "provenance",
                "statement",
                "adoption_provenance",
            },
        )
        if node["kind"] != "intent":
            raise SubjectDocumentError("Intent root kind must be intent")
        fields = parse_node_fields(
            {k: node[k] for k in ("title", "status", "authority_class", "source_ref", "provenance")}
        )
        intents.append(
            CanonicalIntent(
                node["id"],
                fields.title,
                fields.status,
                fields.authority_class,
                fields.source_ref,
                fields.provenance,
                node["statement"],
                node["adoption_provenance"],
                node["revision"],
            )
        )
    edges = []
    for item in _list(data["derived_from"]):
        edge = _object(
            item,
            {"id", "kind", "source", "target_intent_id", "target_revision", "adoption_provenance"},
        )
        if edge["kind"] != "derived_from":
            raise SubjectDocumentError("Intent extension only stores derived_from relations")
        edges.append(
            IntentDerivation(
                edge["id"],
                _selection(edge["source"]),
                edge["target_intent_id"],
                edge["target_revision"],
                edge["adoption_provenance"],
            )
        )
    return CanonicalIntentGraph(data["workspace_identity"], tuple(intents), tuple(edges))
