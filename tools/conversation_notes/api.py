"""The two agent tools. JSON parsing is confined to this boundary."""

import uuid
from dataclasses import asdict
from pathlib import Path

from conversation_notes.codec import REVISION, citation, fields, identifier, text
from conversation_notes.model import (
    AddNote,
    Change,
    ConnectNotes,
    MoveNote,
    Note,
    Notebook,
    NotesError,
    RecordApproval,
    ReviseNote,
    Update,
)
from conversation_notes.store import NotesStore


def record(value) -> dict:
    payload = asdict(value)
    if "sources" in payload:
        payload["sources"] = list(payload["sources"])
    return payload


def optional_parent(value: object) -> str | None:
    return None if value is None else identifier(value)


def parse_change(value: object) -> Change:
    if not isinstance(value, dict):
        raise NotesError("Each change must be an object")
    op = value.get("op")
    if op == "add":
        fields(value, {"op", "id", "label", "detail", "parent_id"}, {"op", "label"})
        return AddNote(
            Note(
                identifier(value.get("id", "n" + uuid.uuid4().hex)),
                text(value["label"]),
                text(value.get("detail", ""), empty=True),
                optional_parent(value.get("parent_id")),
            )
        )
    if op == "revise":
        fields(value, {"op", "id", "label", "detail"}, {"op", "id"})
        return ReviseNote(
            identifier(value["id"]),
            text(value["label"]) if "label" in value else None,
            text(value["detail"], empty=True) if "detail" in value else None,
        )
    if op == "move":
        fields(value, {"op", "id", "parent_id"}, {"op", "id", "parent_id"})
        return MoveNote(identifier(value["id"]), optional_parent(value["parent_id"]))
    if op == "link":
        fields(
            value,
            {"op", "source_id", "target_id", "label"},
            {"op", "source_id", "target_id", "label"},
        )
        return ConnectNotes(
            identifier(value["source_id"]), identifier(value["target_id"]), text(value["label"])
        )
    if op == "approve":
        fields(value, {"op"}, {"op"})
        return RecordApproval()
    raise NotesError(f"Unknown operation: {op}")


def parse_update(payload: object) -> Update:
    data = fields(
        payload,
        {"expected_revision", "source", "changes"},
        {"expected_revision", "source", "changes"},
    )
    revision = data["expected_revision"]
    if revision is not None and (not isinstance(revision, str) or not REVISION.fullmatch(revision)):
        raise NotesError("expected_revision must be null or a revision returned by read_notes")
    changes = data["changes"]
    if not isinstance(changes, list) or not 1 <= len(changes) <= 100:
        raise NotesError("changes must contain 1 to 100 operations")
    return Update(revision, citation(data["source"]), tuple(parse_change(c) for c in changes))


def sibling_positions(book: Notebook) -> dict[str, int]:
    counts: dict[str | None, int] = {}
    positions = {}
    for node in book.nodes:
        positions[node.id] = counts.get(node.parent_id, 0)
        counts[node.parent_id] = positions[node.id] + 1
    return positions


def differences(before: Notebook, after: Notebook) -> dict:
    old = {n.id: n for n in before.nodes}
    old_positions, new_positions = sibling_positions(before), sibling_positions(after)
    added, updated = [], []
    for node in after.branch():
        if node.id not in old:
            added.append(
                {
                    "id": node.id,
                    "label": node.label,
                    "detail": node.detail,
                    "parent_id": node.parent_id,
                }
            )
            continue
        previous = old[node.id]
        changed = {
            key: {"before": getattr(previous, key), "after": getattr(node, key)}
            for key in ("label", "detail", "parent_id")
            if getattr(previous, key) != getattr(node, key)
        }
        if old_positions[node.id] != new_positions[node.id]:
            changed["sibling_index"] = {
                "before": old_positions[node.id],
                "after": new_positions[node.id],
            }
        sources_added = len(node.sources) - len(previous.sources)
        if changed or sources_added:
            updated.append({"id": node.id, "fields": changed, "sources_added": sources_added})
    return {
        "added": added,
        "updated": updated,
        "links_changed": [record(link) for link in after.links if link not in before.links],
        "reviews_added": [
            asdict(review) for review in after.reviews if review not in before.reviews
        ],
    }


def read_notes(root: Path, *, node_id: str | None = None, history_limit: int = 0) -> dict:
    if type(history_limit) is not int or not 0 <= history_limit <= 100:
        raise NotesError("history_limit must be an integer from 0 to 100")
    store = NotesStore(root)
    revision, book = store.read()
    nodes = book.branch(identifier(node_id) if node_id is not None else None)
    ids = {n.id for n in nodes}
    return {
        "artifact_kind": "conversation_notes",
        "schema_version": 1,
        "revision": revision,
        "canonical": False,
        "nodes": [record(n) for n in nodes],
        "links": [
            record(link) for link in book.links if link.source_id in ids or link.target_id in ids
        ],
        "reviews": [asdict(review) for review in book.reviews],
        "omitted_nodes": len(book.nodes) - len(nodes),
        "history": store.history(revision, history_limit),
        "snapshot_path": str(root / "revisions" / revision) if revision else None,
    }


def update_notes(root: Path, payload: object) -> dict:
    request = parse_update(payload)
    revision, before, after = NotesStore(root).update(request)
    return {
        "artifact_kind": "conversation_notes_update",
        "schema_version": 1,
        "canonical": False,
        "revision": revision,
        "previous_revision": request.expected_revision,
        "diff": differences(before, after),
        "snapshot_path": str(root / "revisions" / revision),
    }
