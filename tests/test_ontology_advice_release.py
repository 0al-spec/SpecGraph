"""Exercise commit-time advice with the project's selected Ontology release."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "specs/models/SG-SPEC-0051/proposal-promotion/domain-ontology-package.yaml"


@pytest.fixture
def compiler():
    if not (value := os.environ.get("ONTOLOGYC_BINARY_PATH")):
        pytest.skip("set ONTOLOGYC_BINARY_PATH to exercise the selected release")
    return Path(value).resolve(strict=True)


def test_staged_action_package_is_quiet_but_invalid_reference_is_reported(compiler, tmp_path):
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

    def check(source):
        package.write_text(source, encoding="utf-8")
        subprocess.run(["git", "add", package.name], cwd=repo, check=True, env=env)
        return subprocess.run(
            [compiler, "advise-staged"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    valid = check(original)
    assert "[ontology advice]" not in valid.stderr
    assert original.count("target: CanonicalTarget") == 1
    invalid = check(original.replace("target: CanonicalTarget", "target: MissingCanonicalTarget"))
    assert "[ontology advice]" in invalid.stderr
    assert "class.field.target.unresolved" in invalid.stderr
