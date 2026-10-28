"""Local immutable snapshots with a single atomic CURRENT publication point."""

import fcntl
import hashlib
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from conversation_notes.codec import REVISION, decode, encode
from conversation_notes.model import Notebook, NotesError, Update


def digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def durable_write(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class NotesStore:
    def __init__(self, root: Path):
        self.root = root

    def current_revision(self) -> str | None:
        pointer = self.root / "CURRENT"
        if not pointer.exists():
            return None
        revision = pointer.read_text(encoding="utf-8").strip()
        if not REVISION.fullmatch(revision):
            raise NotesError("Invalid CURRENT revision")
        return revision

    def snapshot(self, revision: str) -> tuple[Notebook, dict]:
        if not isinstance(revision, str) or not REVISION.fullmatch(revision):
            raise NotesError("Invalid snapshot revision")
        directory = self.root / "revisions" / revision
        try:
            metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
            hc = (directory / "notes.hc").read_text(encoding="utf-8")
            hcs = (directory / "notes.hcs").read_text(encoding="utf-8")
            if metadata["schema_version"] != 1 or metadata["revision"] != revision:
                raise NotesError("Unsupported or inconsistent snapshot metadata")
            if metadata["content_hashes"] != {"notes.hc": digest(hc), "notes.hcs": digest(hcs)}:
                raise NotesError("Snapshot files changed outside update_notes")
            return decode(hc, hcs, metadata), metadata
        except (OSError, KeyError, TypeError, ValueError) as error:
            raise NotesError(f"Cannot read snapshot {revision}: {error}") from error

    def read(self) -> tuple[str | None, Notebook]:
        revision = self.current_revision()
        return (revision, self.snapshot(revision)[0]) if revision else (None, Notebook())

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / ".lock").open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def update(self, request: Update) -> tuple[str, Notebook, Notebook]:
        with self.locked():
            revision, before = self.read()
            if revision != request.expected_revision:
                raise NotesError(
                    f"Revision conflict: expected {request.expected_revision}, current {revision}; "
                    "read_notes again"
                )
            after = request.apply(before)
            # Match the stored preorder before deciding whether a revision changed.
            after = replace(after, nodes=after.branch())
            if after == before:
                raise NotesError("No changes to save")
            new_revision = uuid.uuid4().hex
            hc, hcs = encode(after)
            metadata = {
                "schema_version": 1,
                "revision": new_revision,
                "parent_revision": revision,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "source": asdict(request.source),
                "sources": {n.id: [asdict(s) for s in n.sources] for n in after.nodes},
                "links": [asdict(link) for link in after.links],
                "reviews": [asdict(review) for review in after.reviews],
                "content_hashes": {"notes.hc": digest(hc), "notes.hcs": digest(hcs)},
            }
            revisions = self.root / "revisions"
            revisions.mkdir(exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=".pending-", dir=revisions))
            durable_write(temporary / "notes.hc", hc)
            durable_write(temporary / "notes.hcs", hcs)
            durable_write(
                temporary / "metadata.json",
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            )
            sync_directory(temporary)
            os.replace(temporary, revisions / new_revision)
            sync_directory(revisions)
            self.publish(new_revision)
            return new_revision, before, after

    def publish(self, revision: str) -> None:
        pointer = self.root / f".CURRENT-{revision}"
        durable_write(pointer, revision + "\n")
        os.replace(pointer, self.root / "CURRENT")
        sync_directory(self.root)

    def history(self, revision: str | None, limit: int) -> list[dict]:
        entries = []
        seen = set()
        while revision is not None and len(entries) < limit:
            if revision in seen:
                raise NotesError("Snapshot history cycle")
            seen.add(revision)
            _, metadata = self.snapshot(revision)
            entries.append(
                {
                    key: metadata[key]
                    for key in ("revision", "parent_revision", "captured_at", "source")
                }
            )
            revision = metadata["parent_revision"]
        return entries

    def verify_history(self) -> dict:
        """Validate every published snapshot through the root, without a display limit."""
        current = self.current_revision()
        if current is None:
            raise NotesError("No published sketch revision to verify")
        revision = current
        seen = set()
        while revision is not None:
            if not isinstance(revision, str) or not REVISION.fullmatch(revision):
                raise NotesError("Invalid parent revision")
            if revision in seen:
                raise NotesError("Snapshot history cycle")
            seen.add(revision)
            _, metadata = self.snapshot(revision)
            if "parent_revision" not in metadata:
                raise NotesError(f"Missing parent_revision in snapshot {revision}")
            revision = metadata["parent_revision"]
        if self.current_revision() != current:
            raise NotesError("Current revision changed during history verification; retry")
        return {
            "artifact_kind": "conversation_notes_history_verification",
            "schema_version": 1,
            "revision": current,
            "revision_count": len(seen),
            "status": "complete",
            "canonical": False,
        }
