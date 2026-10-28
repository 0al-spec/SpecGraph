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
        'out=""; base=""; head=""; catalog=""\n'
        "while [[ $# -gt 0 ]]; do\n"
        '  case "$1" in\n'
        "    --output) out=$2;;\n"
        "    --base) base=$2;;\n"
        "    --head) head=$2;;\n"
        "    --catalog) catalog=$2;;\n"
        "  esac\n"
        "  shift\n"
        "done\n"
        'printf "%s %s %s\\n" "$catalog" "$base" "$head" >> "$FAKE_OUTPUT/calls.txt"\n'
        'if [[ "${FAKE_STALE:-no}" == yes ]]; then head=stale-head; fi\n'
        'jq --arg base "$base" --arg head "$head" '
        '\'.base_revision=$base | .head_revision=$head\' "$FAKE_OUTPUT/fixture.json" > "$out"\n'
        'if [[ "$out" == */head-catalog-validation.json ]]; then exit "${FAKE_HEAD_EXIT:-0}"; fi\n'
        'exit "${FAKE_EXIT:-0}"\n',
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

    def run(
        base: str,
        head: str,
        *,
        status="complete",
        exit_code="0",
        stale=False,
        head_exit="0",
        pr_head=None,
    ):
        report["status"] = status
        report["base_revision"] = base
        report["head_revision"] = "stale-head" if stale else head
        (output / "fixture.json").write_text(json.dumps(report), encoding="utf-8")
        args = ["bash", str(SCRIPT), str(root), str(analyzer), base, head, str(output)]
        if pr_head is not None:
            args = [
                "bash",
                str(ROOT / "tools/check_rule_reuse_merge.sh"),
                str(root),
                str(analyzer),
                base,
                pr_head,
                head,
                str(output),
            ]
        return subprocess.run(
            args,
            env={
                **os.environ,
                "FAKE_OUTPUT": str(output),
                "FAKE_EXIT": exit_code,
                "FAKE_STALE": "yes" if stale else "no",
                "FAKE_HEAD_EXIT": head_exit,
            },
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


def test_bad_future_catalog_fails_before_base_comparison(adapter):
    root, catalog, output, run = adapter
    catalog.write_text("reviewed-base\n", encoding="utf-8")
    base = commit(root)
    catalog.write_text("malformed-head\n", encoding="utf-8")
    assert run(base, commit(root), head_exit="9").returncode == 9
    calls = (output / "calls.txt").read_text().splitlines()
    assert len(calls) == 1 and "head-catalog.toml" in calls[0]
    assert not (output / "report.json").exists()


def test_base_catalog_is_validated_separately_from_future_catalog(adapter):
    root, catalog, output, run = adapter
    catalog.write_text("base\n", encoding="utf-8")
    base = commit(root)
    catalog.write_text("head\n", encoding="utf-8")
    head = commit(root)
    assert run(base, head).returncode == 0
    calls = (output / "calls.txt").read_text().splitlines()
    assert len(calls) == 2
    assert calls[0].endswith(f"{head} {head}") and "head-catalog.toml" in calls[0]
    assert calls[1].endswith(f"{base} {head}")
    assert (output / "catalog.toml").read_text() == "base\n"


def test_stale_branch_uses_valid_merge_result_containing_base_catalog(adapter):
    root, catalog, output, run = adapter
    initial = commit(root)
    git(root, "branch", "feature", initial)
    catalog.write_text("catalog-added-on-base\n", encoding="utf-8")
    base = commit(root)
    git(root, "checkout", "feature")
    (root / "tools").mkdir(exist_ok=True)
    (root / "tools/new.py").write_text("pass\n", encoding="utf-8")
    pr_head = commit(root)
    assert not catalog.exists()
    git(root, "checkout", "--detach", base)
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "merge",
        "--no-ff",
        "--no-edit",
        pr_head,
    )
    merge = git(root, "rev-parse", "HEAD")
    result = run(base, merge, pr_head=pr_head)
    assert result.returncode == 0, result.stderr
    assert (output / "mode.txt").read_text().strip() == "enforcing"
    assert (output / "head-catalog.toml").read_text() == "catalog-added-on-base\n"
    comparison = json.loads((output / "comparison.json").read_text())
    assert comparison == {
        "base_revision": base,
        "pr_head_revision": pr_head,
        "merge_revision": merge,
    }


def test_merge_from_other_pr_is_rejected_before_analysis(adapter):
    root, catalog, output, run = adapter
    catalog.write_text("catalog\n", encoding="utf-8")
    base = commit(root)
    head = commit(root)
    assert run(base, head, pr_head=head).returncode != 0
    assert not (output / "arguments.txt").exists()


def synthetic_merge(root, tree, *parents):
    args = [
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit-tree",
        tree,
    ]
    for parent in parents:
        args.extend(("-p", parent))
    return git(root, *args, "-m", "synthetic merge")


@pytest.mark.parametrize(
    "case", ["valid", "wrong_base_parent", "changed_base_tree", "third_parent", "unrelated_head"]
)
def test_virtual_base_requires_exact_provenance_and_tree(adapter, case):
    root, catalog, output, run = adapter
    initial = commit(root)
    catalog.write_text("reviewed catalog\n")
    base = commit(root)
    (root / "tools/change.py").write_text("value = 1\n")
    head = commit(root)
    base_tree = git(root, "rev-parse", f"{base}^{{tree}}")
    head_tree = git(root, "rev-parse", f"{head}^{{tree}}")
    if case == "unrelated_head":
        head = initial
    virtual = synthetic_merge(
        root,
        head_tree if case == "changed_base_tree" else base_tree,
        initial,
        initial if case == "wrong_base_parent" else base,
        *([head] if case == "third_parent" else []),
    )
    merged = synthetic_merge(root, head_tree, virtual, head)
    result = run(base, merged, pr_head=head)
    if case == "valid":
        assert result.returncode == 0, result.stderr
        assert (output / "catalog.toml").read_text() == "reviewed catalog\n"
        assert (output / "calls.txt").read_text().splitlines()[-1].endswith(f"{base} {merged}")
    else:
        assert result.returncode != 0
        assert not (output / "arguments.txt").exists()


def test_virtual_base_rejects_stale_event_and_wrong_pr_head(adapter):
    root, catalog, output, run = adapter
    initial = commit(root)
    catalog.write_text("base\n")
    base = commit(root)
    (root / "tools/change.py").write_text("pass\n")
    head = commit(root)
    virtual = synthetic_merge(root, git(root, "rev-parse", f"{base}^{{tree}}"), initial, base)
    merged = synthetic_merge(root, git(root, "rev-parse", f"{head}^{{tree}}"), virtual, head)
    assert run(initial, merged, pr_head=head).returncode != 0
    assert run(base, merged, pr_head=initial).returncode != 0
    assert not (output / "arguments.txt").exists()


def test_freshness_requires_live_open_pr_with_exact_base_head_and_merge():
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    from rule_reuse_pr_freshness import verify_pull_request

    payload = {
        "state": "open",
        "base": {"sha": "base"},
        "head": {"sha": "head"},
        "merge_commit_sha": "merge",
    }
    verify_pull_request(payload, "base", "head", "merge")
    for modified in (
        {**payload, "state": "closed"},
        {**payload, "base": {"sha": "stale"}},
        {**payload, "head": {"sha": "stale"}},
        {**payload, "merge_commit_sha": "stale"},
        {**payload, "merge_commit_sha": None},
        {**payload, "base": None},
    ):
        with pytest.raises(ValueError):
            verify_pull_request(modified, "base", "head", "merge")


def test_freshness_cli_fails_closed_when_github_is_unavailable(tmp_path, monkeypatch, capsys):
    import sys
    from urllib.error import URLError

    sys.path.insert(0, str(ROOT / "tools"))
    import rule_reuse_pr_freshness as freshness

    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repository")
    monkeypatch.setenv("RULE_PR_NUMBER", "123")
    monkeypatch.setenv("GH_TOKEN", "fixture-token")
    monkeypatch.setenv("GITHUB_API_URL", "https://api.example.invalid")
    receipt = tmp_path / "freshness.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "freshness",
            "--base",
            "base",
            "--head",
            "head",
            "--merge",
            "merge",
            "--output",
            str(receipt),
        ],
    )

    def unavailable(request, timeout):
        assert request.full_url == "https://api.example.invalid/repos/owner/repository/pulls/123"
        raise URLError("unavailable")

    monkeypatch.setattr(freshness, "urlopen", unavailable)
    assert freshness.main() == 1
    assert "unavailable" in capsys.readouterr().err
    assert not receipt.exists()


def test_workflow_selects_merge_sha_and_preserves_pr_head_provenance():
    import yaml

    job = yaml.safe_load((ROOT / ".github/workflows/python-ci.yml").read_text())["jobs"][
        "registered-rule-reuse"
    ]
    assert job["steps"][0]["with"]["ref"] == "${{ github.sha }}"
    assert job["env"]["RULE_MERGE"] == "${{ github.sha }}"
    assert job["env"]["RULE_PR_HEAD"] == "${{ github.event.pull_request.head.sha }}"
    assert job["permissions"]["pull-requests"] == "read"
    steps = job["steps"]
    gate = next(
        i for i, step in enumerate(steps) if "check_rule_reuse_merge.sh" in step.get("run", "")
    )
    assert "rule_reuse_pr_freshness.py" in steps[gate - 1]["run"]
    assert "rule_reuse_pr_freshness.py" in steps[gate + 1]["run"]
    assert "GH_TOKEN" not in steps[gate].get("env", {})
    assert any("check_rule_reuse_merge.sh" in step.get("run", "") for step in job["steps"])
