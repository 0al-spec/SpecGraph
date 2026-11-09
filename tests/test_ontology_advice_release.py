"""Exercise commit-time advice with the project's selected Ontology release."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "specs/models/SG-SPEC-0053/intent-to-proposal/domain-ontology-package.yaml"
CORE = Path("ontology/packages/specgraph-core/versions/0.3.0/domain-ontology-package.yaml")
NEXT_CORE = Path("ontology/packages/specgraph-core/versions/0.4.0/domain-ontology-package.yaml")
NEXT_MODEL = (
    ROOT
    / "specs/models/SG-SPEC-0053/intent-to-proposal/versions/0.5.0-draft.1"
    / "domain-ontology-package.yaml"
)


@pytest.fixture
def compiler():
    if not (value := os.environ.get("ONTOLOGYC_BINARY_PATH")):
        pytest.skip("set ONTOLOGYC_BINARY_PATH to exercise the selected release")
    return Path(value).resolve(strict=True)


def test_staged_import_is_used_when_worktree_differs_and_invalid_reference_is_reported(
    compiler, tmp_path
):
    # A disposable index exercises the real advisory without affecting any user checkout.
    template = tmp_path / "empty-template"
    template.mkdir()
    repo = tmp_path / "repository"
    repo.mkdir()
    env = os.environ | {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    subprocess.run(
        ["git", "init", "-q", f"--template={template}", str(repo)],
        check=True,
        env=env,
        capture_output=True,
    )
    package = repo / "domain-ontology-package.yaml"
    original = MODEL.read_text(encoding="utf-8")
    core = repo / CORE
    core.parent.mkdir(parents=True)
    core.write_bytes((ROOT / CORE).read_bytes())
    subprocess.run(["git", "add", str(CORE)], cwd=repo, check=True, env=env)
    core.write_text("unstaged: not the package\n", encoding="utf-8")

    def check(source):
        package.write_text(source, encoding="utf-8")
        subprocess.run(["git", "add", package.name], cwd=repo, check=True, env=env)
        return subprocess.run(
            [compiler, "advise-staged", "--import", str(CORE)],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    valid = check(original)
    assert "[ontology advice]" not in valid.stderr
    assert original.count("target: sgcore:Proposal") == 1
    invalid = check(original.replace("target: sgcore:Proposal", "target: sgcore:MissingProposal"))
    assert "[ontology advice]" in invalid.stderr
    assert "class.field.target.unresolved" in invalid.stderr


def test_multiple_staged_models_need_their_matching_core_versions(compiler, tmp_path):
    """Passing both explicit imports supports both valid versions without hiding defects."""
    template = tmp_path / "empty-template"
    template.mkdir()
    repo = tmp_path / "repository"
    repo.mkdir()
    env = os.environ | {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Ontology test",
        "GIT_AUTHOR_EMAIL": "ontology-test@example.invalid",
        "GIT_COMMITTER_NAME": "Ontology test",
        "GIT_COMMITTER_EMAIL": "ontology-test@example.invalid",
    }

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)

    git("init", "-q", f"--template={template}")
    for relative in (CORE, NEXT_CORE):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    git("add", str(CORE), str(NEXT_CORE))
    git("commit", "-qm", "Add indexed import fixtures")

    old_model = Path("old/domain-ontology-package.yaml")
    new_model = Path("new/domain-ontology-package.yaml")
    for relative, source in ((old_model, MODEL), (new_model, NEXT_MODEL)):
        target = repo / relative
        target.parent.mkdir(parents=True)
        target.write_bytes(source.read_bytes())
    git("add", str(old_model), str(new_model))

    def advise(*imports):
        args = [str(compiler), "advise-staged"]
        for imported in imports:
            args.extend(("--import", str(imported)))
        return subprocess.run(args, cwd=repo, env=env, capture_output=True, text=True, check=True)

    wrong_import = advise(CORE)
    assert "class.field.target.unresolved" in wrong_import.stderr
    assert "new/domain-ontology-package.yaml" in wrong_import.stderr

    matching_imports = advise(CORE, NEXT_CORE)
    assert "[ontology advice]" not in matching_imports.stderr

    missing_import = advise(CORE, Path("missing/domain-ontology-package.yaml"))
    assert "could not be checked" in missing_import.stderr
    assert "old/domain-ontology-package.yaml" in missing_import.stderr
    assert "new/domain-ontology-package.yaml" in missing_import.stderr

    source = NEXT_MODEL.read_text(encoding="utf-8")
    assert source.count("target: sgcore:Proposal") == 1
    (repo / new_model).write_text(
        source.replace("target: sgcore:Proposal", "target: sgcore:MissingProposal"),
        encoding="utf-8",
    )
    git("add", str(new_model))
    invalid = advise(CORE, NEXT_CORE)
    assert "class.field.target.unresolved" in invalid.stderr
    assert "sgcore:MissingProposal" in invalid.stderr
