"""Read adapter and a per-sidecar last-good projection, never a second store."""

from pathlib import Path
from threading import Lock

from conversation_notes.api import read_notes
from conversation_notes.model import NotesError

from .context import DisplayFacts, SnapshotContinuityFacts
from .display_state import display_state
from .snapshot_continuity_spec import SNAPSHOT_CONTINUITY_SPEC


class NotesPreview:
    def __init__(self, workspace: Path, node_id: str | None = None):
        self.workspace = workspace
        self.node_id = node_id
        self._snapshot: dict | None = None
        self._lock = Lock()

    def observe(self) -> dict:
        with self._lock:
            failed = False
            try:
                if not self.workspace.is_dir():
                    raise NotesError("Selected notes workspace is unavailable")
                source = read_notes(self.workspace, node_id=self.node_id, history_limit=0)
                continuity = SnapshotContinuityFacts(
                    bool(self._snapshot and self._snapshot["revision"]), bool(source["revision"])
                )
                if not SNAPSHOT_CONTINUITY_SPEC.is_satisfied_by(continuity):
                    raise NotesError("Previously saved head is unavailable")
                self._snapshot = {
                    key: source[key]
                    for key in ("revision", "canonical", "nodes", "links", "omitted_nodes")
                }
            except (NotesError, OSError):
                failed = True
            snapshot = self._snapshot
            state = display_state(
                DisplayFacts(failed, snapshot is not None, bool(snapshot and snapshot["nodes"]))
            )
            return {
                "schema_version": 1,
                "artifact_kind": "specdraft_preview",
                "canonical": False,
                "sketch": self.workspace.name,
                "display_state": state.value,
                "warning": "Saved notes are temporarily unavailable." if failed else None,
                "snapshot": snapshot,
            }
