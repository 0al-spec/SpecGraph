from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from runpy import run_path

import pytest

_HELPER = run_path(
    str(Path(__file__).resolve().parents[1] / "tools" / "intent_atoms_pr_comment.py")
)
COMMENT_MARKER = _HELPER["COMMENT_MARKER"]
render_comment = _HELPER["render_comment"]


def test_complete_report_renders_aggregates_without_atom_text() -> None:
    report = {
        "completeness": "complete",
        "before_commit_sha": "a" * 40,
        "after_commit_sha": "b" * 40,
        "profile": {"sha256": "c" * 64},
        "analyzer_version": "1.0.1",
        "analyzer_sha256": "d" * 64,
        "summary": {
            "before_atom_count": 7,
            "after_atom_count": 9,
            "net_count_delta": 2,
            "added_count": 3,
            "removed_count": 1,
            "modified_count": 0,
            "counts_are_partial": False,
        },
        "added": [{"text": "@everyone <script>untrusted spec text</script>"}],
    }

    comment = render_comment(report)

    assert COMMENT_MARKER in comment
    assert "**Count:** 7 → 9 (+2)" in comment
    assert "`aaaaaaaaaaaa` → `bbbbbbbbbbbb`" in comment
    assert "+3 added, −1 removed, 0 modified" in comment
    assert "untrusted spec text" not in comment


def test_incomplete_report_withholds_counts() -> None:
    report = {
        "completeness": "incomplete",
        "before_commit_sha": "a" * 40,
        "after_commit_sha": "b" * 40,
        "profile": {},
        "summary": {"before_atom_count": 7, "after_atom_count": 9, "counts_are_partial": True},
        "diagnostics": {"before": [{"code": "missing_spec_root"}], "after": []},
    }

    comment = render_comment(report)

    assert "**Status:** incomplete" in comment
    assert "base 1, head 0" in comment
    assert "**Count:**" not in comment
    assert "→ 9" not in comment


def scoped_report(root, before, after):
    return {
        "artifact_kind": "specgraph_intent_atoms_diff",
        "spec_root": root,
        "completeness": "complete",
        "before_commit_sha": "a" * 40,
        "after_commit_sha": "b" * 40,
        "profile": {"profile_id": "specgraph-intent-atoms-v1", "sha256": "c" * 64},
        "analyzer_version": "1.0.1",
        "analyzer_sha256": "d" * 64,
        "summary": {
            "before_atom_count": before,
            "after_atom_count": after,
            "added_count": max(0, after - before),
            "removed_count": max(0, before - after),
            "modified_count": 0,
            "counts_are_partial": False,
        },
    }


def test_proposal_counts_stay_separate_and_do_not_echo_untrusted_text():
    specs = scoped_report("specs/nodes", 302, 302)
    proposals = scoped_report("docs/proposals", 0, 8)
    proposals["added"] = [{"text": "@everyone <script>untrusted proposal text</script>"}]
    comment = render_comment(specs, proposals)
    assert "**Count:** 302 → 302 (+0)" in comment
    draft = comment.split("### Proposal obligations · draft")[1]
    assert "**Count:** 0 → 8 (+8)" in draft
    assert "unannotated Markdown is not assessed" in draft
    assert "310" not in comment
    assert "untrusted proposal text" not in comment


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("before_commit_sha", "e" * 40),
        ("after_commit_sha", "e" * 40),
        ("spec_root", "specs/nodes"),
        ("analyzer_sha256", "e" * 64),
        ("analyzer_version", "other"),
        ("profile", {"profile_id": "other", "sha256": "c" * 64}),
        ("profile", {"profile_id": "specgraph-intent-atoms-v1", "sha256": "e" * 64}),
    ],
)
def test_proposal_report_contract_mismatch_withholds_draft_counts(field, value):
    specs = scoped_report("specs/nodes", 302, 302)
    proposals = scoped_report("docs/proposals", 0, 8)
    proposals[field] = value
    comment = render_comment(specs, proposals)
    assert "**Count:** 302 → 302 (+0)" in comment
    draft = comment.split("### Proposal obligations · draft")[1]
    assert "**Status:** unavailable" in draft
    assert "**Count:**" not in draft


@pytest.mark.parametrize("value", [None, True, -1, "8"])
def test_invalid_proposal_counts_are_not_reported_as_zero(value):
    proposals = scoped_report("docs/proposals", 0, 8)
    proposals["summary"]["after_atom_count"] = value
    draft = render_comment(scoped_report("specs/nodes", 302, 302), proposals).split(
        "### Proposal obligations · draft"
    )[1]
    assert "**Status:** incomplete" in draft
    assert "**Count:**" not in draft


def test_incomplete_proposal_scope_does_not_hide_complete_specification_count():
    proposals = scoped_report("docs/proposals", 0, 8)
    proposals["completeness"] = "incomplete"
    proposals["summary"]["counts_are_partial"] = True
    comment = render_comment(scoped_report("specs/nodes", 302, 302), proposals)
    assert "**Count:** 302 → 302 (+0)" in comment
    draft = comment.split("### Proposal obligations · draft")[1]
    assert "**Status:** incomplete" in draft
    assert "**Count:**" not in draft


def test_modified_proposal_atom_can_leave_count_unchanged():
    proposals = scoped_report("docs/proposals", 8, 8)
    proposals["summary"]["modified_count"] = 1
    draft = render_comment(scoped_report("specs/nodes", 302, 302), proposals).split(
        "### Proposal obligations · draft"
    )[1]
    assert "**Count:** 8 → 8 (+0)" in draft
    assert "+0 added, −0 removed, 1 modified" in draft


def test_cli_combines_scopes_from_separate_report_files(tmp_path):
    specs = scoped_report("specs/nodes", 302, 302)
    proposals = scoped_report("docs/proposals", 0, 8)
    spec_path, proposal_path = tmp_path / "specs.json", tmp_path / "proposals.json"
    spec_path.write_text(json.dumps(specs))
    proposal_path.write_text(json.dumps(proposals))
    payload = tmp_path / "comment.json"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).resolve().parents[1] / "tools/intent_atoms_pr_comment.py"),
            "--report",
            str(spec_path),
            "--proposal-report",
            str(proposal_path),
            "--payload",
            str(payload),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(payload.read_text()) == {"body": render_comment(specs, proposals)}
