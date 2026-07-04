from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_architecture_metrics_module():
    module_path = ROOT / "tools" / "architecture_metrics.py"
    spec = importlib.util.spec_from_file_location("_architecture_metrics_under_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_architecture_metrics_reports_gate_findings_and_code_shape(tmp_path: Path) -> None:
    module = _load_architecture_metrics_module()
    package = tmp_path / "src" / "specgraph" / "supervisor"
    package.mkdir(parents=True)
    (package / "run.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from typing import Any",
                "",
                "class RunManager:",
                "    @staticmethod",
                "    def build(payload: dict[str, Any], a, b, c, d, e, f):",
                "        if isinstance(payload, dict):",
                "            return payload",
                "        return {}",
                "",
                "    def set_state(self, state: str) -> None:",
                "        self.state = state",
                "",
            ]
        ),
        encoding="utf-8",
    )
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "supervisor.py").write_text(
        "def legacy(a, b, c, d, e, f):\n    return isinstance(a, dict)\n",
        encoding="utf-8",
    )

    report = module.report(tmp_path)
    package_metrics = report["scopes"]["new_supervisor_package"]
    legacy_metrics = report["scopes"]["legacy_supervisor"]

    assert report["artifact_kind"] == "architecture_style_metrics"
    assert report["architecture_gate"]["findings_total"] == 4
    assert report["architecture_gate"]["findings_by_code"] == {
        "ARCH001": 1,
        "ARCH002": 1,
        "ARCH003": 1,
        "ARCH004": 1,
    }
    assert package_metrics["procedural_class_suffix_count"] == 1
    assert package_metrics["procedural_class_suffixes_by_suffix"] == {"Manager": 1}
    assert package_metrics["staticmethod_count"] == 1
    assert package_metrics["setter_function_count"] == 1
    assert package_metrics["dict_any_signature_count"] == 1
    assert package_metrics["isinstance_call_count"] == 1
    assert package_metrics["functions_over_5_parameters"] == 1
    assert legacy_metrics["top_level_function_count"] == 1
    assert legacy_metrics["isinstance_call_count"] == 1


def test_architecture_metrics_reports_empty_scope(tmp_path: Path) -> None:
    module = _load_architecture_metrics_module()

    report = module.report(tmp_path)

    assert report["architecture_gate"]["status"] == "pass"
    assert report["architecture_gate"]["findings_total"] == 0
    assert report["scopes"]["new_supervisor_package"]["file_count"] == 0
    assert report["scopes"]["legacy_supervisor"]["file_count"] == 0


def test_architecture_metrics_keeps_json_shape_when_package_file_has_syntax_error(
    tmp_path: Path,
) -> None:
    module = _load_architecture_metrics_module()
    package = tmp_path / "src" / "specgraph" / "supervisor"
    package.mkdir(parents=True)
    (package / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    report = module.report(tmp_path)
    package_metrics = report["scopes"]["new_supervisor_package"]

    assert report["architecture_gate"]["status"] == "fail"
    assert report["architecture_gate"]["findings_total"] == 1
    assert report["architecture_gate"]["findings_by_code"] == {"ARCH000": 1}
    assert package_metrics["file_count"] == 1
    assert package_metrics["syntax_error_count"] == 1
