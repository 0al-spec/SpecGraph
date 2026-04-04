from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def list_specs_module() -> object:
    module_path = Path(__file__).resolve().parents[1] / "tools" / "list_specs.py"
    spec = importlib.util.spec_from_file_location("test_list_specs_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def specs_fixture(
    tmp_path: Path,
    list_specs_module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    root = tmp_path
    specs_dir = root / "specs" / "nodes"
    runs_dir = root / "runs"
    specs_dir.mkdir(parents=True)
    runs_dir.mkdir(parents=True)

    (specs_dir / "A.yaml").write_text(
        json.dumps(
            {
                "id": "A",
                "title": "Ready node",
                "status": "outlined",
                "maturity": 0.1,
                "depends_on": [],
                "acceptance": ["x"],
                "gate_state": "none",
                "required_human_action": "-",
            }
        ),
        encoding="utf-8",
    )
    (specs_dir / "B.yaml").write_text(
        json.dumps(
            {
                "id": "B",
                "title": "Dependency blocked",
                "status": "outlined",
                "maturity": 0.2,
                "depends_on": ["C"],
                "acceptance": ["x"],
                "gate_state": "none",
                "required_human_action": "-",
            }
        ),
        encoding="utf-8",
    )
    (specs_dir / "C.yaml").write_text(
        json.dumps(
            {
                "id": "C",
                "title": "Review pending",
                "status": "specified",
                "maturity": 0.3,
                "depends_on": [],
                "acceptance": ["x"],
                "gate_state": "review_pending",
                "required_human_action": "resolve gate",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(list_specs_module.supervisor, "ROOT", root)
    monkeypatch.setattr(list_specs_module.supervisor, "SPECS_DIR", specs_dir)
    monkeypatch.setattr(list_specs_module.supervisor, "RUNS_DIR", runs_dir)

    return root


def test_ready_view_json(
    list_specs_module: object, specs_fixture: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = specs_fixture
    exit_code = list_specs_module.main(["--view", "ready", "--format", "json"])
    assert exit_code == 0

    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1
    assert rows[0]["ID"] == "A"
    assert rows[0]["Queue"] == "ready"


def test_blocked_view_table(
    list_specs_module: object, specs_fixture: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = specs_fixture
    exit_code = list_specs_module.main(["--view", "blocked"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert "B" in output
    assert "blocked" in output
    assert "C (specified)" in output


def test_review_pending_view_table(
    list_specs_module: object,
    specs_fixture: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = specs_fixture
    exit_code = list_specs_module.main(["--view", "review_pending"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert "C" in output
    assert "review_pending" in output
    assert "resolve gate" in output
