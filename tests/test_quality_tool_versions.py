from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def load_pre_commit() -> dict:
    return yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))


def load_python_ci() -> str:
    return (ROOT / ".github" / "workflows" / "python-ci.yml").read_text(encoding="utf-8")


def find_local_hook(config: dict, hook_id: str) -> dict:
    for repo in config.get("repos", []):
        if repo.get("repo") != "local":
            continue
        for hook in repo.get("hooks", []):
            if hook.get("id") == hook_id:
                return hook
    raise AssertionError(f"Hook {hook_id!r} not found")


def find_ruff_repo(config: dict) -> dict:
    for repo in config.get("repos", []):
        if repo.get("repo") == "https://github.com/astral-sh/ruff-pre-commit":
            return repo
    raise AssertionError("ruff-pre-commit repo not found")


def test_quality_tool_versions_are_pinned_and_aligned() -> None:
    pyproject = load_pyproject()
    pre_commit = load_pre_commit()
    python_ci = load_python_ci()

    dependencies = pyproject["project"]["dependencies"]
    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]

    assert "pyyaml==6.0.3" in dependencies
    assert "pytest==9.0.2" in dev_dependencies
    assert "ruff==0.15.9" in dev_dependencies

    python_quality = find_local_hook(pre_commit, "python-quality")
    assert python_quality["additional_dependencies"] == ["ruff==0.15.9", "pyyaml==6.0.3"]

    spec_yaml_format = find_local_hook(pre_commit, "spec-yaml-format")
    assert spec_yaml_format["additional_dependencies"] == ["pyyaml==6.0.3"]

    spec_yaml_lint = find_local_hook(pre_commit, "spec-yaml-lint")
    assert spec_yaml_lint["additional_dependencies"] == ["pyyaml==6.0.3"]

    ruff_repo = find_ruff_repo(pre_commit)
    assert ruff_repo["rev"] == "v0.15.9"

    assert "python -m pip install -e .[dev]" in python_ci
    assert "python tools/python_quality.py" in python_ci
