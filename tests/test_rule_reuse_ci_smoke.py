"""Check snapshot provenance independently of analyzer matching."""

import json
import subprocess
from pathlib import Path

from tools import rule_reuse_ci_smoke as smoke


def test_dirty_fixture_does_not_change_recorded_snapshot(tmp_path, monkeypatch):
    repo = tmp_path / "source"
    repo.mkdir()
    smoke.git(repo, "init", "-q")
    fixture = repo / "tests/fixtures/rule_reuse/workspace_allocation_copy.py"
    fixture.parent.mkdir(parents=True)
    original = "def policy(value):\n    return value is True\n\n"
    fixture.write_text(original, encoding="utf-8")
    catalog = repo / "tools/rule_reuse_catalog.toml"
    catalog.parent.mkdir()
    catalog.write_text("schema_version = 1\n", encoding="utf-8")
    revision = smoke.commit(repo)
    fixture.write_text("uncommitted invalid fixture!", encoding="utf-8")
    observed = []

    def gate(args, **kwargs):
        # Only the external analyzer is simulated. Git commits and fixture
        # selection use the real smoke producer and an actual dirty checkout.
        root, base, head, output = Path(args[2]), args[4], args[5], Path(args[6])
        output.mkdir()
        copied = root / "tools/smoke_copy.py"
        code = copied.read_text(encoding="utf-8") if copied.exists() else None
        observed.append(code)
        exact = int(code == original)
        near = int(code == original.replace("is True", "is False", 1))
        report = {
            "status": "complete",
            "base_revision": base,
            "head_revision": head,
            "new_reimplementations": exact,
            "new_near_matches": near,
            "findings": []
            if code is None
            else [
                {
                    "rule_id": "subject_publication.workspace_allocation",
                    "path": "tools/smoke_copy.py",
                    "introduced": True,
                    "kind": "reimplementation" if exact else "near_match",
                }
            ],
        }
        (output / "report.json").write_text(json.dumps(report), encoding="utf-8")
        (output / "mode.txt").write_text("enforcing\n", encoding="utf-8")
        return subprocess.CompletedProcess(
            args, exact, "", "rule reuse gate failed:" if exact else ""
        )

    # check_output uses subprocess.run internally; preserve actual Git calls.
    real_run = subprocess.run

    def run(args, **kwargs):
        return gate(args, **kwargs) if args[0] == "bash" else real_run(args, **kwargs)

    monkeypatch.setattr(smoke.subprocess, "run", run)
    result = smoke.smoke(repo, tmp_path / "analyzer", tmp_path / "output")
    assert result["source_revision"] == revision
    assert result["status"] == "complete"
    assert observed == [None, original, original.replace("is True", "is False", 1)]
    assert fixture.read_text(encoding="utf-8") == "uncommitted invalid fixture!"
