from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_executable(path: Path, marker: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$0 $*\" > {marker}\nexit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)


def copy_make_context(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "tools").mkdir(parents=True)
    (repo / "Makefile").write_text((ROOT / "Makefile").read_text(encoding="utf-8"))
    (repo / "tools" / "check_python_version.py").write_text("", encoding="utf-8")
    return repo


def test_makefile_prefers_local_venv_python_by_default(tmp_path: Path) -> None:
    repo = copy_make_context(tmp_path)
    marker = tmp_path / "selected_python.txt"
    write_executable(repo / ".venv" / "bin" / "python", marker)

    result = subprocess.run(
        ["make", "check-python"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    selected = marker.read_text(encoding="utf-8")
    assert ".venv/bin/python tools/check_python_version.py" in selected


def test_makefile_python_override_wins_over_local_venv(tmp_path: Path) -> None:
    repo = copy_make_context(tmp_path)
    local_marker = tmp_path / "local_python.txt"
    override_marker = tmp_path / "override_python.txt"
    write_executable(repo / ".venv" / "bin" / "python", local_marker)
    override_python = tmp_path / "custom-python"
    write_executable(override_python, override_marker)

    result = subprocess.run(
        ["make", "check-python", f"PYTHON={override_python}"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": os.environ.get("PATH", "")},
    )

    assert result.returncode == 0, result.stderr
    assert not local_marker.exists()
    selected = override_marker.read_text(encoding="utf-8")
    assert f"{override_python} tools/check_python_version.py" in selected
