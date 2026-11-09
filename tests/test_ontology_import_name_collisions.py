"""Detect duplicate names throughout locally available import closures."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ontology_import_name_collisions.py"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def package(root: Path, name: str, *, imports=(), classes=(), relations=(), version="1") -> None:
    path = root / "specs/models" / f"{name}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "kind": "DomainOntologyPackage",
                "metadata": {"id": name, "version": version, "namespace": name},
                "spec": {
                    "imports": [{"id": item, "version": v} for item, v in imports],
                    "classes": {item: {} for item in classes},
                    "relations": {item: {} for item in relations},
                },
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.org")
    git(tmp_path, "config", "user.name", "Test")
    package(tmp_path, "core", classes=("Intent", "Proposal"))
    package(tmp_path, "unrelated", classes=("Intent",))
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def check(root: Path) -> subprocess.CompletedProcess[str]:
    git(root, "add", ".")
    return subprocess.run(
        [sys.executable, str(TOOL), "--root", str(root), "--base-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_checker_runs_without_specification_core(repo: Path):
    command = (
        "import runpy, sys; "
        "sys.modules['specification_core'] = None; "
        "sys.path.insert(0, sys.argv[1]); "
        "sys.argv = [sys.argv[2], '--root', sys.argv[3], '--base-ref', 'HEAD']; "
        "runpy.run_path(sys.argv[0], run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-c", command, str(TOOL.parent), str(TOOL), str(repo)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def add_foundation(root: Path) -> None:
    for name in ("exports.json", "exports-0.2.0.json"):
        path = Path("tools/project_ontology_context/pinned_foundation") / name
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, root / path)
    git(root, "add", ".")
    git(root, "commit", "-qm", "pinned foundation")


def test_imported_duplicate_outside_overview_blocks(repo: Path):
    package(repo, "new-model", imports=(("core", "1"),), classes=("Intent",))
    result = check(repo)
    assert result.returncode == 1
    assert "New import-closure collisions: 1" in result.stdout
    assert "core@1 /spec/classes/Intent" in result.stdout
    assert "new-model@1 /spec/classes/Intent" in result.stdout
    assert "specs/models/core.yaml" in result.stdout
    assert "specs/models/new-model.yaml" in result.stdout


def test_unrelated_packages_may_use_same_name(repo: Path):
    result = check(repo)
    assert result.returncode == 0
    assert "New import-closure collisions: 0" in result.stdout


def test_package_in_another_directory_is_discovered(repo: Path):
    package(repo, "other", imports=(("core", "1"),), classes=("Intent",))
    destination = repo / "new-area/other.yaml"
    destination.parent.mkdir()
    (repo / "specs/models/other.yaml").rename(destination)
    result = check(repo)
    assert result.returncode == 1
    assert "new-area/other.yaml" in result.stdout


def test_escaped_yaml_kind_is_still_discovered(repo: Path):
    package(repo, "escaped", imports=(("core", "1"),), classes=("Intent",))
    path = repo / "specs/models/escaped.yaml"
    path.write_text(
        path.read_text().replace("DomainOntologyPackage", r"DomainOntologyPack\u0061ge"),
        encoding="utf-8",
    )
    result = check(repo)
    assert result.returncode == 1
    assert "escaped@1 /spec/classes/Intent" in result.stdout


def test_transitive_import_and_same_kind_are_checked(repo: Path):
    package(repo, "middle", imports=(("core", "1"),))
    package(repo, "leaf", imports=(("middle", "1"),), classes=("Proposal",))
    result = check(repo)
    assert result.returncode == 1
    assert "core@1 /spec/classes/Proposal" in result.stdout
    assert "leaf@1 /spec/classes/Proposal" in result.stdout


def test_sibling_imports_are_checked_in_the_importing_package(repo: Path):
    package(repo, "model", imports=(("core", "1"), ("unrelated", "1")))
    result = check(repo)
    assert result.returncode == 1
    assert "core@1 /spec/classes/Intent" in result.stdout
    assert "unrelated@1 /spec/classes/Intent" in result.stdout


def test_same_name_in_different_declaration_kinds_does_not_collide(repo: Path):
    package(repo, "model", imports=(("core", "1"),), relations=("Intent",))
    assert check(repo).returncode == 0


def test_unavailable_import_is_reported_and_project_import_fails_closed(repo: Path):
    package(repo, "model", imports=(("external", "1"),))
    result = check(repo)
    assert result.returncode == 0
    assert "external@1" in result.stdout and "not checked" in result.stdout
    package(repo, "model", imports=(("org.0al.specgraph.missing", "1"),))
    result = check(repo)
    assert result.returncode == 2
    assert "org.0al.specgraph.missing@1" in result.stderr


def test_known_package_with_wrong_version_fails_closed(repo: Path):
    package(repo, "model", imports=(("core", "2"),))
    result = check(repo)
    assert result.returncode == 2
    assert "core@2" in result.stderr


@pytest.mark.parametrize(
    ("identity", "version", "name"),
    [("ontology.foundation", "0.2.0", "Action"), ("specgraph.foundation", "0.1.0", "Invariant")],
)
def test_pinned_foundation_exports_are_checked(repo: Path, identity: str, version: str, name: str):
    add_foundation(repo)
    package(repo, "model", imports=((identity, version),), classes=(name,))
    result = check(repo)
    assert result.returncode == 1
    assert f"ontology.foundation@{version} /classes/{name}" in result.stdout
    assert "tools/project_ontology_context/pinned_foundation/exports" in result.stdout


def test_foundation_aliases_are_one_source(repo: Path):
    add_foundation(repo)
    package(
        repo, "model", imports=(("ontology.foundation", "0.1.0"), ("specgraph.foundation", "0.1.0"))
    )
    assert check(repo).returncode == 0


def test_altered_foundation_catalog_fails_closed(repo: Path):
    add_foundation(repo)
    path = repo / "tools/project_ontology_context/pinned_foundation/exports.json"
    path.write_text(path.read_text() + "\n", encoding="utf-8")
    result = check(repo)
    assert result.returncode == 2
    assert "pinned foundation digest does not match" in result.stderr


def test_conflicting_versions_in_one_closure_fail_closed(repo: Path):
    second = repo / "ontology/core-v2.yaml"
    second.parent.mkdir(parents=True, exist_ok=True)
    content = json.loads((repo / "specs/models/core.yaml").read_text())
    content["metadata"]["version"] = "2"
    second.write_text(json.dumps(content), encoding="utf-8")
    package(repo, "model", imports=(("core", "1"), ("core", "2")))
    result = check(repo)
    assert result.returncode == 2
    assert "conflicting versions of core" in result.stderr


def test_duplicate_package_identity_fails_closed(repo: Path):
    path = repo / "ontology/duplicate.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((repo / "specs/models/core.yaml").read_text(), encoding="utf-8")
    result = check(repo)
    assert result.returncode == 2
    assert "ambiguous package core@1" in result.stderr


def test_duplicate_yaml_keys_cannot_hide_a_declaration(repo: Path):
    path = repo / "specs/models/core.yaml"
    path.write_text(
        "kind: DomainOntologyPackage\nmetadata: {id: core, version: '1', namespace: core}\n"
        "spec:\n  classes:\n    Intent: {}\n    Intent: {}\n",
        encoding="utf-8",
    )
    result = check(repo)
    assert result.returncode == 2
    assert "duplicate YAML key 'Intent'" in result.stderr


def test_unsafe_yaml_tags_are_rejected(repo: Path):
    path = repo / "specs/models/core.yaml"
    path.write_text(
        "kind: DomainOntologyPackage\nmetadata: !!python/object/apply:os.system ['false']\n",
        encoding="utf-8",
    )
    result = check(repo)
    assert result.returncode == 2
    assert "could not determine a constructor" in result.stderr


def test_preexisting_collision_is_reported_without_creating_a_new_one(repo: Path):
    package(repo, "model", imports=(("core", "1"),), classes=("Intent",))
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "existing collision")
    result = check(repo)
    assert result.returncode == 0
    assert "Existing import-closure collisions (unresolved): 1" in result.stdout
    assert "New import-closure collisions: 0" in result.stdout
