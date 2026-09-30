#!/usr/bin/env python3
"""Render a bounded, aggregate-only SpecificationMetrics PR comment."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

COMMENT_MARKER = "<!-- specificationmetrics-pr-report-v1 -->"
EXPECTED_PROJECT = "0al-spec/SpecGraph"


def _count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _source_revision(report: dict[str, Any]) -> str:
    primary = report.get("primary")
    value = primary.get("source_revision") if isinstance(primary, dict) else None
    if not isinstance(value, str) or len(value) not in (40, 64):
        return "unavailable"
    if any(character not in "0123456789abcdef" for character in value.lower()):
        return "unavailable"
    return value[:12]


def _count_line(label: str, before: dict[str, Any], after: dict[str, Any], field: str) -> str:
    old = _count(before.get(field))
    new = _count(after.get(field))
    if old is None or new is None:
        return f"| {label} | unavailable | unavailable |"
    return f"| {label} | {old} | {new} ({new - old:+d}) |"


def _ratio(value: Any) -> str:
    if value is None:
        return "n/a"
    number = _number(value)
    return "unavailable" if number is None else f"{number:.6g}"


def _display_count(report: dict[str, Any], field: str) -> str:
    value = _count(report.get(field))
    return str(value) if value is not None else "unavailable"


def _valid_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def render_comment(
    before: dict[str, Any], after: dict[str, Any], diff: dict[str, Any], run_url: str
) -> str:
    """Only include validated aggregate data; never echo source text or file paths."""
    if any(
        report.get("schema_version") != 1 or report.get("project") != EXPECTED_PROJECT
        for report in (before, after)
    ):
        raise ValueError("collection snapshot has an unexpected schema or project")
    if any(
        report.get("status") not in {"complete", "provisional", "partial"}
        for report in (before, after)
    ):
        raise ValueError("collection snapshot has an invalid status")
    old = before.get("primary")
    new = after.get("primary")
    if not isinstance(old, dict) or not isinstance(new, dict):
        raise ValueError("collection is missing its primary S/U report")
    if any(
        _count(report.get(field)) is None
        for report in (old, new)
        for field in ("specification_definitions", "remaining_opportunities")
    ):
        raise ValueError("collection has invalid primary S/U counts")
    if (
        not _valid_digest(before.get("contract_digest"))
        or not _valid_digest(old.get("source_digest"))
        or not _valid_digest(new.get("source_digest"))
        or before.get("contract_digest") != after.get("contract_digest")
        or diff.get("contract_digest") != after.get("contract_digest")
        or diff.get("before_source_digest") != old.get("source_digest")
        or diff.get("after_source_digest") != new.get("source_digest")
    ):
        raise ValueError("comparison does not match the collection contracts and source snapshots")
    expected_url_prefix = "https://github.com/0al-spec/SpecGraph/actions/runs/"
    if (
        not run_url.startswith(expected_url_prefix)
        or not run_url[len(expected_url_prefix) :].isdigit()
    ):
        raise ValueError("workflow run URL is invalid")

    lines = [
        COMMENT_MARKER,
        "### SpecificationMetrics · diagnostic PR measurement",
        "",
        "| Metric | Base | PR head (Δ) |",
        "|---|---:|---:|",
        _count_line("Specifications (S)", old, new, "specification_definitions"),
        _count_line("Remaining opportunities (U)", old, new, "remaining_opportunities"),
        f"| S/U | {_ratio(old.get('ratio'))} | {_ratio(new.get('ratio'))} |",
        (
            f"| Dead Specifications | {_display_count(old, 'dead_specifications')} | "
            f"{_display_count(new, 'dead_specifications')} |"
        ),
        (
            f"| Unknown Specifications | {_display_count(old, 'unknown_specifications')} | "
            f"{_display_count(new, 'unknown_specifications')} |"
        ),
        "",
        f"**Collection:** base `{before['status']}`, head `{after['status']}`.",
        (
            f"**Primary provisional:** base `{old.get('provisional') is True}`, "
            f"head `{new.get('provisional') is True}`."
        ),
        (
            f"**Revisions:** `{_source_revision(before)}` → `{_source_revision(after)}`; "
            f"contract `{after['contract_digest'][:12]}`."
        ),
        "",
    ]
    supplementary = diff.get("supplementary")
    supplementary = supplementary if isinstance(supplementary, dict) else {}
    for name, title, keys in (
        (
            "python_complexity",
            "Python CC / Cog",
            ("cc_sum", "cc_max", "cog_sum", "cog_max", "sloc"),
        ),
        (
            "duplication",
            "Clone pairs / duplicate lines / tokens",
            ("clone_pairs", "duplicate_lines", "duplicate_tokens"),
        ),
    ):
        item = supplementary.get(name)
        deltas = item.get("delta") if isinstance(item, dict) else None
        if (
            not isinstance(deltas, dict)
            or not isinstance(item, dict)
            or item.get("status") != "comparable"
        ):
            lines.append(f"- **{title}:** not comparable; see pinned-tool diagnostics.")
            continue
        rendered = []
        for key in keys:
            value = _number(deltas.get(key))
            if value is not None:
                rendered.append(f"{key} {value:+g}")
        lines.append(
            f"- **{title}:** " + ("; ".join(rendered) if rendered else "no deltas available")
        )
    lines.extend(
        [
            "",
            "Scope: files assigned `application` by the manifest; `tests/` is `test`, "
            "and the comment renderer is `framework`.",
            "Informational only. Counts and metrics do not decide eligibility, correctness, "
            "or merge readiness.",
            f"[Collection run]({run_url})",
        ]
    )
    return "\n".join(lines)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--diff", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    payload = {
        "body": render_comment(
            _read(args.before), _read(args.after), _read(args.diff), args.run_url
        )
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
