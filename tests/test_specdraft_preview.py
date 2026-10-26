"""0228 / SDPV-01..06: policy, real saved notes, fixed read-only HTTP boundary."""

# ruff: noqa: E402

import hashlib
import json
import sys
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest
from specification_core import TraceRecorder

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from conversation_notes.api import update_notes
from specdraft_preview.context import DisplayFacts, DisplayState
from specdraft_preview.display_state import display_state
from specdraft_preview.server import create_server
from specdraft_preview.snapshot import NotesPreview


def save_note(root, revision=None, *, label="A thought", op="add"):
    return update_notes(
        root,
        {
            "expected_revision": revision,
            "source": {"speaker": "human", "ref": "fixture:preview", "quote": "Fixture quotation."},
            "changes": [{"op": op, "id": "idea", "label": label}],
        },
    )["revision"]


def hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (DisplayFacts(False, True, True), DisplayState.CURRENT),
        (DisplayFacts(False, True, False), DisplayState.EMPTY),
        (DisplayFacts(True, True, True), DisplayState.STALE),
        (DisplayFacts(True, True, False), DisplayState.STALE),
        (DisplayFacts(True, False, False), DisplayState.UNAVAILABLE),
    ],
)
def test_display_policy(facts, expected):
    recorder = TraceRecorder()
    assert display_state(facts, recorder=recorder) == expected
    assert recorder.events[0].name == "specdraft_preview.display_state"


def test_notes_readonly_update_stale_and_recovery(tmp_path):
    """SDPV-01/02/03/04/05: the actual note store, no copied JSON fixture."""
    preview = NotesPreview(tmp_path)
    assert preview.observe()["display_state"] == "empty"
    revision = save_note(tmp_path, label="<script>fixture()</script>")
    before = hashes(tmp_path)
    first = preview.observe()
    assert first["display_state"] == "current"
    assert first["snapshot"]["revision"] == revision
    assert first["snapshot"]["nodes"][0]["label"] == "<script>fixture()</script>"
    assert first["snapshot"]["nodes"][0]["sources"][0]["quote"] == "Fixture quotation."
    assert hashes(tmp_path) == before
    current = tmp_path / "CURRENT"
    current.write_text("broken")
    stale = preview.observe()
    assert stale["display_state"] == "stale"
    assert stale["snapshot"] == first["snapshot"]
    assert stale["warning"]
    assert NotesPreview(tmp_path).observe()["display_state"] == "unavailable"
    current.write_text(revision)
    revision2 = save_note(tmp_path, revision, label="Renamed", op="revise")
    recovered = preview.observe()
    assert recovered["display_state"] == "current" and recovered["warning"] is None
    assert recovered["snapshot"]["revision"] == revision2
    assert recovered["snapshot"]["nodes"][0]["id"] == "idea"
    assert recovered["snapshot"]["nodes"][0]["label"] == "Renamed"


def test_missing_head_after_saved_revision_is_stale(tmp_path):
    revision = save_note(tmp_path)
    preview = NotesPreview(tmp_path)
    first = preview.observe()
    (tmp_path / "CURRENT").unlink()
    stale = preview.observe()
    assert stale["display_state"] == "stale" and stale["snapshot"] == first["snapshot"]
    (tmp_path / "CURRENT").write_text(revision)
    assert preview.observe()["display_state"] == "current"


def test_constructor_does_not_read_or_create_workspace(tmp_path):
    root = tmp_path / "absent"
    preview = NotesPreview(root)
    assert not root.exists()
    unavailable = preview.observe()
    assert unavailable["display_state"] == "unavailable"
    assert unavailable["snapshot"] is None
    assert not root.exists()


@pytest.fixture()
def running_preview(tmp_path):
    save_note(tmp_path)
    server = create_server(tmp_path)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()
    try:
        yield tmp_path, server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request(server, method, path, headers=None):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_http_observes_live_store_without_mutation_or_history(running_preview):
    """SDPV-02/04/06: real HTTP + actual tool writes; history stays out of the API."""
    root, server = running_preview
    before = hashes(root)
    status, headers, raw = request(server, "GET", "/api/notes")
    payload = json.loads(raw)
    assert status == 200 and headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "history" not in payload["snapshot"] and "reviews" not in payload["snapshot"]
    assert not payload["canonical"] and not payload["snapshot"]["canonical"]
    assert hashes(root) == before
    revision = save_note(root, payload["snapshot"]["revision"], label="Visible update", op="revise")
    updated = json.loads(request(server, "GET", "/api/notes")[2])
    assert updated["snapshot"]["revision"] == revision
    assert updated["snapshot"]["nodes"][0]["label"] == "Visible update"
    assert server.server_address[0] == "127.0.0.1"


@pytest.mark.parametrize("path", ["/", "/app.js", "/style.css", "/icon.svg"])
def test_local_assets_and_head(running_preview, path):
    _, server = running_preview
    status, headers, body = request(server, "GET", path)
    assert status == 200 and body
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert request(server, "HEAD", path)[2] == b""


@pytest.mark.parametrize(
    ("method", "path", "headers", "status"),
    [
        ("POST", "/api/notes", {}, 405),
        ("GET", "/api/notes?workspace=/", {}, 400),
        ("GET", "/CURRENT", {}, 404),
        ("GET", "/../../pyproject.toml", {}, 404),
        ("GET", "/api/notes", {"Host": "rebinding.invalid"}, 403),
        ("GET", "/history", {}, 404),
    ],
)
def test_fixed_http_boundary(running_preview, method, path, headers, status):
    root, server = running_preview
    before = hashes(root)
    assert request(server, method, path, headers)[0] == status
    assert hashes(root) == before
