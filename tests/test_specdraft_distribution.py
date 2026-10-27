"""Installed facade compatibility and self-contained skill resource contracts."""

# ruff: noqa: E402 -- the preserved source CLI modules live under tools.

import io
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from specgraph import __version__
from specgraph.cli import main
from specgraph.distribution import install_skill, skill_contents


def request(revision=None):
    return {
        "expected_revision": revision,
        "source": {
            "ref": "synthetic:distribution-test",
            "quote": "Keep this quotation",
            "speaker": "human",
        },
        "changes": [{"op": "add", "id": "goal", "label": "Goal", "parent_id": None}],
    }


def test_cli_reuses_notes_protocol(tmp_path, monkeypatch, capsys):
    root = str(tmp_path / "consumer" / "sketch")
    assert main(["notes", "read_notes", "--workspace", root]) == 0
    initial = json.loads(capsys.readouterr().out)
    assert initial["revision"] is None and initial["canonical"] is False
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request())))
    assert main(["notes", "update_notes", "--workspace", root]) == 0
    saved = json.loads(capsys.readouterr().out)
    assert saved["revision"] and saved["canonical"] is False
    assert main(["notes", "read_notes", "--workspace", root, "--history-limit", "2"]) == 0
    restored = json.loads(capsys.readouterr().out)
    assert restored["revision"] == saved["revision"]
    assert restored["nodes"][0]["sources"][0]["quote"] == "Keep this quotation"


def test_cli_rejects_stale_revision(tmp_path, monkeypatch, capsys):
    root = str(tmp_path / "sketch")
    for expected in (0, 2):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request())))
        assert main(["notes", "update_notes", "--workspace", root]) == expected
        output = capsys.readouterr()
    assert "Revision conflict" in json.loads(output.err)["error"]


def test_skill_is_self_contained_and_idempotent(tmp_path):
    destination = tmp_path / "consumer" / ".codex" / "skills" / "specgraph-conversation-notes"
    installed = install_skill(destination)
    assert installed["status"] == "installed" and installed["runtime_version"] == __version__
    assert install_skill(destination)["status"] == "already_installed"
    assert set(installed["files_sha256"]) == {"SKILL.md", "references/usage.md"}
    for name, expected in skill_contents().items():
        path = destination / name
        assert path.read_bytes() == expected
        for reference in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            linked = (path.parent / reference).resolve()
            assert linked.is_relative_to(destination.resolve()) and linked.is_file()


def test_skill_conflict_preserves_existing_content(tmp_path):
    destination = tmp_path / "skill"
    install_skill(destination)
    user_file = destination / "SKILL.md"
    user_file.write_text("user-maintained instructions")
    with pytest.raises(ValueError, match="not overwritten"):
        install_skill(destination)
    assert user_file.read_text() == "user-maintained instructions"


def test_skill_rejects_symlink_destination(tmp_path):
    destination = tmp_path / "skill"
    actual = tmp_path / "actual"
    actual.mkdir()
    destination.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        install_skill(destination)
    assert list(actual.iterdir()) == []


def test_cli_reports_skill_errors_as_json(tmp_path, capsys):
    destination = tmp_path / "file"
    destination.write_text("preserve me")
    assert main(["skill", "install", "--destination", str(destination)]) == 2
    assert "not overwritten" in json.loads(capsys.readouterr().err)["error"]
    assert destination.read_text() == "preserve me"


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as stopped:
        main(["--version"])
    assert stopped.value.code == 0
    assert capsys.readouterr().out.strip() == f"specgraph {__version__}"
