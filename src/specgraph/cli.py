"""Installed facade over the unchanged SpecDraft note and preview commands."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .distribution import DEFAULT_SKILL, SKILL_FILES, install_skill, project_skill_destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SpecGraph portable SpecDraft tools")
    parser.add_argument("--version", action="version", version=f"specgraph {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("notes", add_help=False, help="Read or update an explicit sketch")
    commands.add_parser("preview", add_help=False, help="Serve a read-only loopback preview")
    skill = commands.add_parser("skill", help="Install the version-matched, self-contained skill")
    skill.add_argument("operation", choices=("install",))
    skill.add_argument("--name", choices=tuple(SKILL_FILES), default=DEFAULT_SKILL)
    target = skill.add_mutually_exclusive_group(required=True)
    target.add_argument("--destination", type=Path)
    target.add_argument("--project", type=Path, help="Existing project root for .codex/skills")
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
        destination = (
            args.destination
            if args.destination is not None
            else project_skill_destination(args.project, args.name)
        )
        result = install_skill(destination, args.name)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
