"""Safety and provenance boundaries for the external compiler smoke."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ontology_release_smoke as smoke  # noqa: E402


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_refuses_nonempty_work_dir_without_touching_content(tmp_path):
    work = tmp_path / "existing"
    work.mkdir()
    valuable = work / "receipt.json"
    valuable.write_text("keep this")
    with pytest.raises(ValueError, match="new or empty"):
        smoke.prepare_work_dir(work)
    assert valuable.read_text() == "keep this"


def test_refuses_symlink_work_dir(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "link"
    link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        smoke.prepare_work_dir(link)
    assert list(actual.iterdir()) == []


def test_authority_observations_do_not_invent_or_change_status():
    package = {"metadata": {"approvalStatus": "approved"}}
    fixture = {"governance": {"lifecycle_state": "review_pending"}}
    observed = smoke.observe_authority(package, fixture)
    assert observed == {
        "package_approval_status": "approved",
        "fixture_authority_class": None,
        "fixture_lifecycle_state": "review_pending",
    }
    assert package == {"metadata": {"approvalStatus": "approved"}}
    assert fixture == {"governance": {"lifecycle_state": "review_pending"}}


def test_checks_release_revision_and_rejects_tracked_changes(tmp_path, monkeypatch):
    repo = tmp_path / "ontology"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "package").write_text("release")
    git(repo, "add", "package")
    git(
        repo,
        "-c",
        "user.name=Smoke Test",
        "-c",
        "user.email=smoke@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "fixture",
    )
    revision = git(repo, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="ontology source must be at"):
        smoke.check_ontology_source(repo)
    monkeypatch.setattr(smoke, "ONTOLOGY_REVISION", revision)
    assert smoke.check_ontology_source(repo) == revision
    (repo / "package").write_text("changed")
    with pytest.raises(ValueError, match="tracked changes"):
        smoke.check_ontology_source(repo)


def test_wrong_release_does_not_create_work_dir(tmp_path):
    repo = tmp_path / "ontology"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "package").write_text("other")
    git(repo, "add", "package")
    git(
        repo,
        "-c",
        "user.name=Smoke Test",
        "-c",
        "user.email=smoke@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "fixture",
    )
    work = tmp_path / "output"
    with pytest.raises(ValueError, match="ontology source must be at"):
        smoke.smoke(Path(sys.executable), repo, work)
    assert not work.exists()
