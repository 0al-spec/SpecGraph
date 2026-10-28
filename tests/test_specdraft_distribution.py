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


def test_verify_history_walks_past_display_limit_and_detects_missing_ancestor(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "sketch"
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request())))
    assert main(["notes", "update_notes", "--workspace", str(root)]) == 0
    first = json.loads(capsys.readouterr().out)["revision"]
    first_dir = root / "revisions" / first
    hc = (first_dir / "notes.hc").read_bytes()
    hcs = (first_dir / "notes.hcs").read_bytes()
    metadata = json.loads((first_dir / "metadata.json").read_text())
    parent = first
    for index in range(1, 102):
        revision = f"{index:032x}"
        directory = root / "revisions" / revision
        directory.mkdir()
        (directory / "notes.hc").write_bytes(hc)
        (directory / "notes.hcs").write_bytes(hcs)
        (directory / "metadata.json").write_text(
            json.dumps({**metadata, "revision": revision, "parent_revision": parent})
        )
        parent = revision
    (root / "CURRENT").write_text(parent + "\n")
    args = ["notes", "verify_history", "--workspace", str(root)]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["revision_count"] == 102 and result["status"] == "complete"
    (first_dir / "notes.hc").unlink()
    assert main(["notes", "read_notes", "--workspace", str(root), "--history-limit", "100"]) == 0
    capsys.readouterr()
    assert main(args) == 2
    assert "Cannot read snapshot" in json.loads(capsys.readouterr().err)["error"]


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


def test_cli_installs_named_skill_to_existing_project(tmp_path, capsys):
    project = tmp_path / "consumer project"
    project.mkdir()
    name = "specgraph-project-ontology"
    destination = project / ".codex" / "skills" / name
    args = ["skill", "install", "--name", name, "--project", str(project)]
    assert main(args) == 0
    installed = json.loads(capsys.readouterr().out)
    assert installed["status"] == "installed"
    assert installed["skill"] == name
    assert installed["destination"] == str(destination)
    assert (destination / "SKILL.md").read_bytes() == skill_contents(name)["SKILL.md"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "already_installed"
    (destination / "SKILL.md").write_text("user-maintained instructions")
    assert main(args) == 2
    assert "not overwritten" in json.loads(capsys.readouterr().err)["error"]
    assert (destination / "SKILL.md").read_text() == "user-maintained instructions"


def test_ontology_skill_matches_repository_workflow():
    root = Path(__file__).resolve().parents[1]
    repository_skill = root / ".codex/skills/specgraph-project-ontology/SKILL.md"
    assert skill_contents("specgraph-project-ontology")["SKILL.md"] == repository_skill.read_bytes()


def test_cli_project_destination_defaults_to_conversation_skill(tmp_path, capsys):
    assert main(["skill", "install", "--project", str(tmp_path)]) == 0
    installed = json.loads(capsys.readouterr().out)
    assert installed["skill"] == "specgraph-conversation-notes"
    assert Path(installed["destination"]) == (
        tmp_path / ".codex" / "skills" / "specgraph-conversation-notes"
    )


def test_cli_rejects_nonexistent_project_and_symlinked_skill_directory(tmp_path, capsys):
    missing = tmp_path / "missing"
    assert main(["skill", "install", "--project", str(missing)]) == 2
    assert "existing directory" in json.loads(capsys.readouterr().err)["error"]
    assert not missing.exists()
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / ".codex").symlink_to(outside, target_is_directory=True)
    assert main(["skill", "install", "--project", str(project)]) == 2
    assert "symlinks" in json.loads(capsys.readouterr().err)["error"]
    assert list(outside.iterdir()) == []


def test_cli_rejects_symlinked_project_skills_and_destination(tmp_path, capsys):
    project = tmp_path / "project"
    (project / ".codex").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    skills = project / ".codex" / "skills"
    skills.symlink_to(outside, target_is_directory=True)
    args = ["skill", "install", "--name", "specgraph-project-ontology", "--project", str(project)]
    assert main(args) == 2
    assert "symlinks" in json.loads(capsys.readouterr().err)["error"]
    assert list(outside.iterdir()) == []
    skills.unlink()
    skills.mkdir()
    (skills / "specgraph-project-ontology").symlink_to(outside, target_is_directory=True)
    assert main(args) == 2
    assert "symlink" in json.loads(capsys.readouterr().err)["error"]
    assert list(outside.iterdir()) == []


def test_cli_rejects_unknown_skill_without_creating_destination(tmp_path, capsys):
    destination = tmp_path / "target"
    with pytest.raises(SystemExit) as stopped:
        main(["skill", "install", "--name", "../unknown", "--destination", str(destination)])
    assert stopped.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
    assert not destination.exists()


def test_cli_rejects_multiple_skill_destinations(tmp_path, capsys):
    with pytest.raises(SystemExit) as stopped:
        main(["skill", "install", "--project", str(tmp_path), "--destination", str(tmp_path / "x")])
    assert stopped.value.code == 2
    assert "not allowed" in capsys.readouterr().err
    assert not (tmp_path / "x").exists()


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as stopped:
        main(["--version"])
    assert stopped.value.code == 0
    assert capsys.readouterr().out.strip() == f"specgraph {__version__}"
