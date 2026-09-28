from __future__ import annotations

from tools.intent_atoms_pr_comment import COMMENT_MARKER, render_comment


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
