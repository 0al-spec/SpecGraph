"""Installed facade over the unchanged SpecDraft note and preview commands."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .distribution import install_skill


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SpecGraph portable SpecDraft tools")
    parser.add_argument("--version", action="version", version=f"specgraph {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("notes", add_help=False, help="Read or update an explicit sketch")
    commands.add_parser("preview", add_help=False, help="Serve a read-only loopback preview")
    skill = commands.add_parser("skill", help="Install the version-matched, self-contained skill")
    skill.add_argument("operation", choices=("install",))
    skill.add_argument("--destination", required=True, type=Path)
    args, remaining = parser.parse_known_args(argv)
    if args.command == "notes":
        from conversation_notes_cli import main as notes_main

        return notes_main(remaining)
    if args.command == "preview":
        from specdraft_preview_cli import main as preview_main

        return preview_main(remaining)
    if remaining:
        parser.error(f"unrecognized arguments: {' '.join(remaining)}")
    try:
        result = install_skill(args.destination)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
