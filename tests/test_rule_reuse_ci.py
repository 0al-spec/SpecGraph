"""Exercise the catalog-authority adapter independently of analyzer matching."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/check_rule_reuse.sh"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def commit(root: Path) -> str:
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--allow-empty",
        "-qm",
        "fixture",
    )
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def adapter(tmp_path: Path):
    if shutil.which("jq") is None:
        pytest.skip("CI adapter requires jq")
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    (root / "tools").mkdir()
    catalog = root / "tools/rule_reuse_catalog.toml"
    analyzer = tmp_path / "analyzer"
    analyzer.write_text(
        '#!/usr/bin/env bash\nset -eu\nprintf "%s\\n" "$@" > "$FAKE_OUTPUT/arguments.txt"\n'
        "while [[ $# -gt 0 ]]; do\n"
        '  if [[ "$1" == --output ]]; then cp "$FAKE_OUTPUT/fixture.json" "$2"; fi\n'
        '  shift\ndone\nexit "${FAKE_EXIT:-0}"\n',
        encoding="utf-8",
    )
    analyzer.chmod(0o755)
    output = tmp_path / "output"
    output.mkdir()
    report = {
        "artifact_kind": "rule_reuse_report",
        "schema_version": 1,
        "status": "complete",
        "before_reimplementations": 0,
        "after_reimplementations": 1,
        "new_reimplementations": 1,
        "new_near_matches": 0,
        "reused_specifications": 0,
        "base_revision": "fixture-base",
        "head_revision": "fixture-head",
    }
    (output / "fixture.json").write_text(json.dumps(report), encoding="utf-8")

    def run(base: str, head: str, *, status="complete", exit_code="0", stale=False):
        report["status"] = status
        report["base_revision"] = base
        report["head_revision"] = "stale-head" if stale else head
        (output / "fixture.json").write_text(json.dumps(report), encoding="utf-8")
        return subprocess.run(
            ["bash", str(SCRIPT), str(root), str(analyzer), base, head, str(output)],
            env={**os.environ, "FAKE_OUTPUT": str(output), "FAKE_EXIT": exit_code},
            capture_output=True,
            text=True,
            check=False,
        )

    return root, catalog, output, run


def test_first_activation_is_visibly_report_only(adapter):
    root, catalog, output, run = adapter
    base = commit(root)
    catalog.write_text("head-catalog\n", encoding="utf-8")
    result = run(base, commit(root))
    assert result.returncode == 0, result.stderr
    assert "bootstrap" in result.stdout
    assert "--strict" not in (output / "arguments.txt").read_text()
    assert (output / "mode.txt").read_text().strip() == "bootstrap"
    assert "New exact copies: 1" in (output / "summary.md").read_text()


def test_base_catalog_is_authoritative_even_when_head_changes_it(adapter):
    root, catalog, output, run = adapter
    catalog.write_text("reviewed-base-catalog\n", encoding="utf-8")
    base = commit(root)
    catalog.write_text("weakened-head-catalog\n", encoding="utf-8")
    result = run(base, commit(root))
    assert result.returncode == 0, result.stderr
    assert (output / "catalog.toml").read_text() == "reviewed-base-catalog\n"
    assert "--strict" in (output / "arguments.txt").read_text()
    assert (output / "mode.txt").read_text().strip() == "enforcing"


def test_deleting_head_catalog_cannot_reset_activation(adapter):
    root, catalog, output, run = adapter
    catalog.write_text("reviewed\n", encoding="utf-8")
    base = commit(root)
    catalog.unlink()
    assert run(base, commit(root)).returncode != 0
    assert not (output / "arguments.txt").exists()


def test_analyzer_failure_is_preserved_and_report_is_retained(adapter):
    root, catalog, output, run = adapter
    catalog.write_text("reviewed\n", encoding="utf-8")
    base = commit(root)
    assert run(base, commit(root), exit_code="7").returncode == 7
    assert (output / "report.json").is_file()
    assert not (output / "summary.md").exists()


def test_bootstrap_incomplete_evidence_is_not_success(adapter):
    root, catalog, output, run = adapter
    base = commit(root)
    catalog.write_text("head\n", encoding="utf-8")
    assert run(base, commit(root), status="incomplete").returncode != 0
    assert not (output / "summary.md").exists()


def test_complete_report_for_other_revisions_is_rejected(adapter):
    root, catalog, output, run = adapter
    base = commit(root)
    catalog.write_text("head\n", encoding="utf-8")
    assert run(base, commit(root), stale=True).returncode != 0
    assert not (output / "summary.md").exists()
