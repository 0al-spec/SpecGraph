#!/usr/bin/env python3
"""Render an Intent Atoms diff as a safe, updatable GitHub PR comment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

COMMENT_MARKER = "<!-- specgraph-intent-atoms-v1 -->"


def _digest(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 64:
        return "unavailable"
    if any(character not in "0123456789abcdef" for character in value.lower()):
        return "unavailable"
    return value


def _revision(value: Any) -> str:
    if not isinstance(value, str) or len(value) not in (40, 64):
        return "unavailable"
    if any(character not in "0123456789abcdef" for character in value.lower()):
        return "unavailable"
    return value


def _count(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def proposal_lines(report: dict[str, Any], proposal_report: dict[str, Any]) -> list[str]:
    """Keep declared proposal obligations in their own revision-bound scope."""
    lines = ["", "### Proposal obligations · draft", ""]
    profile = proposal_report.get("profile")
    profile = profile if isinstance(profile, dict) else {}
    spec_profile = report.get("profile")
    spec_profile = spec_profile if isinstance(spec_profile, dict) else {}
    same_revisions = all(
        _revision(proposal_report.get(key)) != "unavailable"
        and proposal_report.get(key) == report.get(key)
        for key in ("before_commit_sha", "after_commit_sha")
    )
    same_analysis = (
        profile.get("profile_id") == "specgraph-intent-atoms-v1"
        and _digest(profile.get("sha256")) != "unavailable"
        and profile.get("sha256") == spec_profile.get("sha256")
        and _digest(proposal_report.get("analyzer_sha256")) != "unavailable"
        and proposal_report.get("analyzer_sha256") == report.get("analyzer_sha256")
        and proposal_report.get("analyzer_version") == report.get("analyzer_version")
    )
    if (
        proposal_report.get("artifact_kind") != "specgraph_intent_atoms_diff"
        or report.get("spec_root") != "specs/nodes"
        or proposal_report.get("spec_root") != "docs/proposals"
        or not same_revisions
        or not same_analysis
    ):
        lines.append("**Status:** unavailable — proposal scope, revisions or analyzer mismatch")
        return lines
    summary = proposal_report.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    fields = (
        "before_atom_count",
        "after_atom_count",
        "added_count",
        "removed_count",
        "modified_count",
    )
    valid_counts = all(type(summary.get(key)) is int and summary[key] >= 0 for key in fields)
    complete = (
        proposal_report.get("completeness") == "complete"
        and summary.get("counts_are_partial") is False
        and valid_counts
    )
    if complete:
        before, after = summary["before_atom_count"], summary["after_atom_count"]
        lines.extend(
            [
                "**Status:** complete for declared fields",
                f"**Count:** {before} → {after} ({after - before:+d})",
                "**Diff:** "
                f"+{summary['added_count']} added, "
                f"−{summary['removed_count']} removed, "
                f"{summary['modified_count']} modified",
            ]
        )
    else:
        lines.append("**Status:** incomplete — proposal counts are withheld")
    lines.extend(
        [
            "**Coverage:** explicit YAML declarations in `docs/proposals`; "
            "unannotated Markdown is not assessed.",
            "Draft counts are separate from specification counts; "
            "they do not establish review, approval or canonical promotion.",
        ]
    )
    return lines


def render_comment(report: dict[str, Any], proposal_report: dict[str, Any] | None = None) -> str:
    """Render only validated aggregate fields; never echo PR-authored atom text."""
    summary = report.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    profile = report.get("profile")
    profile = profile if isinstance(profile, dict) else {}
    diagnostics = report.get("diagnostics")
    diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
    before_diagnostics = diagnostics.get("before")
    after_diagnostics = diagnostics.get("after")
    before_diagnostics = before_diagnostics if isinstance(before_diagnostics, list) else []
    after_diagnostics = after_diagnostics if isinstance(after_diagnostics, list) else []

    base_sha = _revision(report.get("before_commit_sha"))
    head_sha = _revision(report.get("after_commit_sha"))
    status = report.get("completeness")
    complete = status == "complete" and not summary.get("counts_are_partial", True)
    lines = [COMMENT_MARKER, "### Intent Atoms · v1", ""]
    if report.get("spec_root") == "specs/nodes":
        lines.extend(["**Scope:** specification YAML in `specs/nodes`", ""])

    if complete:
        before_count = _count(summary.get("before_atom_count"))
        after_count = _count(summary.get("after_atom_count"))
        delta = summary.get("net_count_delta")
        if not isinstance(delta, int) or isinstance(delta, bool):
            delta = after_count - before_count
        lines.extend(
            [
                "**Status:** complete",
                f"**Count:** {before_count} → {after_count} ({delta:+d})",
                "**Diff:** "
                f"+{_count(summary.get('added_count'))} added, "
                f"−{_count(summary.get('removed_count'))} removed, "
                f"{_count(summary.get('modified_count'))} modified",
            ]
        )
    else:
        lines.extend(
            [
                "**Status:** incomplete — counts are withheld from the metric",
                f"**Diagnostics:** base {len(before_diagnostics)}, head {len(after_diagnostics)}",
            ]
        )

    lines.extend(
        [
            f"**Revisions:** `{base_sha[:12]}` → `{head_sha[:12]}`",
            "**Profile:** `specgraph-intent-atoms-v1` "
            f"(SHA-256 `{_digest(profile.get('sha256'))[:12]}`)",
            f"**Analyzer:** `{report.get('analyzer_version', 'unavailable')}` "
            f"(SHA-256 `{_digest(report.get('analyzer_sha256'))[:12]}`)",
        ]
    )
    if proposal_report is not None:
        lines.extend(proposal_lines(report, proposal_report))
    lines.extend(["", "Informational only; this report does not gate merge readiness."])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--proposal-report", type=Path)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        parser.error("report must be a JSON object")
    proposal_report = None
    if args.proposal_report:
        proposal_report = json.loads(args.proposal_report.read_text(encoding="utf-8"))
        if not isinstance(proposal_report, dict):
            parser.error("proposal report must be a JSON object")
    payload = {"body": render_comment(report, proposal_report)}
    args.payload.parent.mkdir(parents=True, exist_ok=True)
    args.payload.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
