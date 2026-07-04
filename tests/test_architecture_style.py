from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_architecture_style_module():
    module_path = ROOT / "tools" / "validate_architecture_style.py"
    spec = importlib.util.spec_from_file_location(
        "_validate_architecture_style_under_test",
        module_path,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_architecture_style_accepts_domain_object_code(tmp_path: Path) -> None:
    module = _load_architecture_style_module()
    package = tmp_path / "src" / "specgraph" / "supervisor"
    package.mkdir(parents=True)
    (package / "policy.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "class Policy:",
                "    def __init__(self, path: object):",
                "        self._path = path",
                "",
                "    def value(self, dotted: str) -> object:",
                "        return dotted",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert module.validate(tmp_path) == []


def test_architecture_style_reports_supervisor_package_violations(tmp_path: Path) -> None:
    module = _load_architecture_style_module()
    package = tmp_path / "src" / "specgraph" / "supervisor"
    package.mkdir(parents=True)
    (package / "run.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from pathlib import Path",
                "from typing import Any",
                "",
                "import tools.supervisor",
                "",
                "PAYLOAD = Path('policy.json').read_text()",
                "",
                "class RunManager:",
                "    @staticmethod",
                "    def build(payload: dict[str, Any]) -> dict[str, Any]:",
                "        return payload",
                "",
                "    def set_state(self, state: str) -> None:",
                "        self.state = state",
                "",
            ]
        ),
        encoding="utf-8",
    )

    findings = module.validate(tmp_path)
    codes = {finding.code for finding in findings}

    assert codes == {"ARCH001", "ARCH002", "ARCH003", "ARCH004", "ARCH005", "ARCH006"}


def test_architecture_style_does_not_scan_legacy_supervisor_shim(tmp_path: Path) -> None:
    module = _load_architecture_style_module()
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "supervisor.py").write_text(
        "class LegacyManager:\n"
        "    @staticmethod\n"
        "    def build(payload):\n"
        "        return payload\n",
        encoding="utf-8",
    )

    assert module.validate(tmp_path) == []
