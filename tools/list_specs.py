#!/usr/bin/env python3
"""List spec nodes with queue-oriented views."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

# Import supervisor module from same directory.
_supervisor_path = Path(__file__).resolve().parent / "supervisor.py"
_spec = importlib.util.spec_from_file_location("list_specs_supervisor", _supervisor_path)
assert _spec and _spec.loader
supervisor = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = supervisor
_spec.loader.exec_module(supervisor)


def classify_spec(spec: object, index: dict[str, object]) -> tuple[str, str, str]:
    deps = []
    blocked_by = []
    for dep_id in spec.depends_on:
        deps.append(dep_id)
        dep = index.get(dep_id)
        if dep is None:
            blocked_by.append(f"{dep_id} (missing)")
        elif dep.status not in supervisor.READY_DEP_STATUSES:
            blocked_by.append(f"{dep_id} ({dep.status})")

    gate_state = str(spec.data.get("gate_state", "none") or "none")
    required_action = str(spec.data.get("required_human_action", "-") or "-")

    if gate_state == "review_pending":
        return "review_pending", ", ".join(blocked_by) if blocked_by else "-", required_action

    if blocked_by:
        return "blocked", ", ".join(blocked_by), required_action

    if gate_state in {"blocked", "split_required", "redirected", "escalated"}:
        return "blocked", gate_state, required_action

    if (
        spec.status in supervisor.WORKABLE_STATUSES
        and supervisor.dependencies_ready(spec, index)
        and gate_state not in supervisor.BLOCKING_GATE_STATES
    ):
        return "ready", "-", required_action

    return "other", "-", required_action


def build_rows(specs: list[object], view: str) -> list[dict[str, str]]:
    index = supervisor.index_specs(specs)
    rows: list[dict[str, str]] = []

    for spec in specs:
        queue, blocked_by, required_action = classify_spec(spec, index)
        if view != "all" and queue != view:
            continue

        deps = ", ".join(spec.depends_on) if spec.depends_on else "-"
        rows.append(
            {
                "ID": spec.id or "(no id)",
                "Title": spec.title or "(no title)",
                "Status": spec.status,
                "Maturity": f"{spec.maturity:.1f}",
                "Queue": queue,
                "Depends On": deps,
                "Blocked By": blocked_by,
                "Gate": str(spec.data.get("gate_state", "none") or "none"),
                "Required Action": required_action,
            }
        )

    return rows


def print_markdown_table(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("No specs matched the selected view.")
        return

    headers = [
        "ID",
        "Title",
        "Status",
        "Maturity",
        "Queue",
        "Depends On",
        "Blocked By",
        "Gate",
        "Required Action",
    ]
    widths = {h: len(h) for h in headers}
    for row in rows:
        for header in headers:
            widths[header] = max(widths[header], len(row[header]))

    header_line = "| " + " | ".join(h.ljust(widths[h]) for h in headers) + " |"
    sep_line = "| " + " | ".join("-" * widths[h] for h in headers) + " |"
    print(header_line)
    print(sep_line)
    for row in rows:
        print("| " + " | ".join(row[h].ljust(widths[h]) for h in headers) + " |")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List SpecGraph queue views")
    parser.add_argument(
        "--view",
        choices=["all", "ready", "blocked", "review_pending"],
        default="all",
        help="Filter by queue type (default: all)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        specs = supervisor.load_specs()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not specs:
        print("No spec nodes found.")
        return 0

    rows = build_rows(specs, view=args.view)
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print_markdown_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
