"""Exercise commit-time advice with the project's selected Ontology release."""

from __future__ import annotations

import os
import subprocess
import sys
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


def test_index_aware_hook_selects_both_versions_and_keeps_real_diagnostics(compiler, tmp_path):
    repo = tmp_path / "repository"
    repo.mkdir()
    template = tmp_path / "empty-template"
    template.mkdir()
    env = os.environ | {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Ontology test",
        "GIT_AUTHOR_EMAIL": "ontology-test@example.invalid",
        "GIT_COMMITTER_NAME": "Ontology test",
        "GIT_COMMITTER_EMAIL": "ontology-test@example.invalid",
    }

    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)

    def advise():
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/ontology_advice_staged.py"),
                "--compiler",
                str(compiler),
            ],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    git("init", "-q", f"--template={template}")
    for relative in (CORE, NEXT_CORE):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    git("add", str(CORE), str(NEXT_CORE))
    git("commit", "-qm", "Add indexed imports")
    old_model = Path("old/domain-ontology-package.yaml")
    new_model = Path("new model $(ignored)/domain-ontology-package.yaml")
    for relative, source in ((old_model, MODEL), (new_model, NEXT_MODEL)):
        target = repo / relative
        target.parent.mkdir(parents=True)
        target.write_bytes(source.read_bytes())
    git("add", str(old_model), str(new_model))

    # The working copies are not authoritative; the index still contains both valid sources.
    (repo / CORE).write_text("unstaged: invalid\n", encoding="utf-8")
    (repo / NEXT_CORE).write_text("unstaged: invalid\n", encoding="utf-8")
    assert "[ontology advice]" not in advise().stderr

    source = NEXT_MODEL.read_text(encoding="utf-8")
    (repo / new_model).write_text(
        source.replace("target: sgcore:Proposal", "target: sgcore:MissingProposal"),
        encoding="utf-8",
    )
    git("add", str(new_model))
    invalid = advise()
    assert "class.field.target.unresolved" in invalid.stderr
    assert "sgcore:MissingProposal" in invalid.stderr

    # A missing version does not stop the old model being checked with its available version.
    git("rm", "--cached", str(NEXT_CORE))
    missing = advise()
    assert "org.0al.specgraph.core@0.4.0 is unavailable in the active index" in missing.stderr
    assert 'old/domain-ontology-package.yaml" could not be checked' not in missing.stderr


def test_index_aware_hook_reports_conflicting_sources_and_preserves_alternate_index(
    compiler, tmp_path
):
    repo = tmp_path / "repository"
    repo.mkdir()
    template = tmp_path / "empty-template"
    template.mkdir()
    env = os.environ | {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}

    def git(*args, git_env=env):
        return subprocess.run(
            ["git", *args], cwd=repo, env=git_env, check=True, capture_output=True
        )

    git("init", "-q", f"--template={template}")
    alternate = env | {"GIT_INDEX_FILE": str(tmp_path / "alternate-index")}
    for relative in (CORE, NEXT_CORE):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
        git("add", str(relative), git_env=alternate)
    duplicate = repo / "other/domain-ontology-package.yaml"
    duplicate.parent.mkdir()
    duplicate.write_bytes((ROOT / NEXT_CORE).read_bytes())
    git("add", str(duplicate.relative_to(repo)), git_env=alternate)
    model = repo / "model/domain-ontology-package.yaml"
    model.parent.mkdir()
    model.write_bytes(NEXT_MODEL.read_bytes())
    git("add", str(model.relative_to(repo)), git_env=alternate)

    command = [
        sys.executable,
        str(ROOT / "tools/ontology_advice_staged.py"),
        "--compiler",
        str(compiler),
    ]
    identical = subprocess.run(
        command, cwd=repo, env=alternate, capture_output=True, text=True, check=True
    )
    assert "[ontology advice]" not in identical.stderr
    duplicate.write_bytes((ROOT / NEXT_CORE).read_bytes() + b"\n# different bytes\n")
    git("add", str(duplicate.relative_to(repo)), git_env=alternate)
    result = subprocess.run(
        command,
        cwd=repo,
        env=alternate,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "org.0al.specgraph.core@0.4.0 is ambiguous" in result.stderr
    assert git("ls-files").stdout == b""


def test_installed_hook_checks_actual_git_commit(compiler, tmp_path):
    repo = tmp_path / "repository"
    repo.mkdir()
    template = tmp_path / "empty-template"
    template.mkdir()
    env = os.environ | {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Ontology test",
        "GIT_AUTHOR_EMAIL": "ontology-test@example.invalid",
        "GIT_COMMITTER_NAME": "Ontology test",
        "GIT_COMMITTER_EMAIL": "ontology-test@example.invalid",
    }

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
        )

    git("init", "-q", f"--template={template}")
    core = repo / CORE
    core.parent.mkdir(parents=True)
    core.write_bytes((ROOT / CORE).read_bytes())
    git("add", str(CORE))
    git("commit", "-qm", "Add core")
    hooks_available = subprocess.run(["git", "hook", "-h"], cwd=repo, env=env, capture_output=True)
    if b"git hook list" not in hooks_available.stdout + hooks_available.stderr:
        pytest.skip("configured Git hooks require Git 2.54 or compatible support")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/ontology_advice_staged.py"),
            "--compiler",
            str(compiler),
            "--install",
        ],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    model = repo / "domain-ontology-package.yaml"
    model.write_text(
        MODEL.read_text(encoding="utf-8").replace(
            "target: sgcore:Proposal", "target: sgcore:MissingProposal"
        ),
        encoding="utf-8",
    )
    git("add", model.name)
    result = git("commit", "-m", "Save draft with a deliberate invalid reference")
    assert "[ontology advice]" in result.stderr
    assert "class.field.target.unresolved" in result.stderr
    assert "sgcore:MissingProposal" in result.stderr
