from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def spec_yaml_module() -> object:
    module_path = Path(__file__).resolve().parents[1] / "tools" / "spec_yaml.py"
    spec = importlib.util.spec_from_file_location("test_spec_yaml_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_format_file_rewrites_to_canonical_yaml(
    tmp_path: Path,
    spec_yaml_module: object,
) -> None:
    target = tmp_path / "spec.yaml"
    target.write_text(
        '{"id":"SG-SPEC-0099","status":"outlined","acceptance":["x"]}', encoding="utf-8"
    )

    changed = spec_yaml_module.format_file(target)

    assert changed is True
    rendered = target.read_text(encoding="utf-8")
    assert rendered.startswith("id: SG-SPEC-0099\n")
    assert "{\n" not in rendered
    assert rendered.endswith("\n")


def test_lint_file_reports_noncanonical_format(
    tmp_path: Path,
    spec_yaml_module: object,
) -> None:
    target = tmp_path / "spec.yaml"
    target.write_text(
        '{"id":"SG-SPEC-0099","status":"outlined","acceptance":["x"]}', encoding="utf-8"
    )

    issues = spec_yaml_module.lint_file(target)

    assert len(issues) == 1
    assert "not canonically formatted" in issues[0].message


def test_lint_file_rejects_duplicate_keys(
    tmp_path: Path,
    spec_yaml_module: object,
) -> None:
    target = tmp_path / "spec.yaml"
    target.write_text(
        "id: SG-SPEC-0099\nstatus: outlined\nstatus: specified\nacceptance:\n  - x\n",
        encoding="utf-8",
    )

    issues = spec_yaml_module.lint_file(target)

    assert len(issues) == 1
    assert "duplicate key" in issues[0].message


def test_lint_file_rejects_mapping_acceptance_item(
    tmp_path: Path,
    spec_yaml_module: object,
) -> None:
    target = tmp_path / "spec.yaml"
    target.write_text(
        "id: SG-SPEC-0099\n"
        "status: outlined\n"
        "acceptance:\n"
        "- Defines seeds: Foo, Bar\n"
        "acceptance_evidence:\n"
        "- criterion: Defines seeds for Foo, Bar\n"
        "  evidence: covered\n",
        encoding="utf-8",
    )

    issues = spec_yaml_module.lint_file(target)

    assert any("acceptance[1] must be a string" in issue.message for issue in issues)


def test_lint_file_passes_for_canonical_yaml(
    tmp_path: Path,
    spec_yaml_module: object,
) -> None:
    target = tmp_path / "spec.yaml"
    target.write_text(
        "id: SG-SPEC-0099\nstatus: outlined\nacceptance:\n- x\n",
        encoding="utf-8",
    )

    issues = spec_yaml_module.lint_file(target)

    assert issues == []
