#!/usr/bin/env python3
"""Agent-callable read_notes and update_notes tools, using JSON over stdin/stdout."""

import argparse
import json
import sys
from pathlib import Path

from conversation_notes.api import read_notes, update_notes
from conversation_notes.model import NotesError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=("read_notes", "update_notes"))
    parser.add_argument("--workspace", type=Path, required=True, help="Dedicated sketch directory")
    parser.add_argument("--input", type=Path, help="JSON request; update_notes defaults to stdin")
    parser.add_argument("--node-id", help="Read only this node and its descendants")
    parser.add_argument("--history-limit", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        if args.tool == "read_notes":
            if args.input:
                raise NotesError("--input is only used by update_notes")
            result = read_notes(
                args.workspace, node_id=args.node_id, history_limit=args.history_limit
            )
        else:
            if args.node_id or args.history_limit:
                raise NotesError("--node-id and --history-limit are only used by read_notes")
            raw = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
            result = update_notes(args.workspace, json.loads(raw))
    except (NotesError, OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
