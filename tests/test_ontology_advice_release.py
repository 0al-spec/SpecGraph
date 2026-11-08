"""Exercise commit-time advice with the project's selected Ontology release."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "specs/models/SG-SPEC-0053/intent-to-proposal/domain-ontology-package.yaml"
CORE = Path("ontology/packages/specgraph-core/versions/0.3.0/domain-ontology-package.yaml")


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
