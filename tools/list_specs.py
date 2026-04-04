#!/usr/bin/env python3
"""List all spec nodes as a Markdown table."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Import supervisor module from same directory
_supervisor_path = Path(__file__).resolve().parent / "supervisor.py"
_spec = importlib.util.spec_from_file_location("list_specs_supervisor", _supervisor_path)
assert _spec and _spec.loader
supervisor = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = supervisor
_spec.loader.exec_module(supervisor)


def main() -> int:
    try:
        specs = supervisor.load_specs()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not specs:
        print("No spec nodes found.")
        return 0

    index = supervisor.index_specs(specs)

    # Build table rows
    rows: list[dict[str, str]] = []
    for spec in specs:
        deps = ", ".join(spec.depends_on) if spec.depends_on else "-"
        blocked_by = []
        for dep_id in spec.depends_on:
            dep = index.get(dep_id)
            if dep is None:
                blocked_by.append(f"{dep_id} (missing)")
            elif dep.status not in supervisor.READY_DEP_STATUSES:
                blocked_by.append(f"{dep_id} ({dep.status})")
        blocked = ", ".join(blocked_by) if blocked_by else "-"
        rows.append(
            {
                "ID": spec.id or "(no id)",
                "Title": spec.title or "(no title)",
                "Status": spec.status,
                "Maturity": f"{spec.maturity:.1f}",
                "Depends On": deps,
                "Blocked By": blocked,
            }
        )

    # Calculate column widths
    headers = ["ID", "Title", "Status", "Maturity", "Depends On", "Blocked By"]
    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(row[h]))

    # Render Markdown table
    header_line = "| " + " | ".join(h.ljust(widths[h]) for h in headers) + " |"
    sep_line = "| " + " | ".join("-" * widths[h] for h in headers) + " |"
    print(header_line)
    print(sep_line)
    for row in rows:
        print("| " + " | ".join(row[h].ljust(widths[h]) for h in headers) + " |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
