#!/usr/bin/env python3
"""Format SpecGraph YAML files into canonical repository style."""

from __future__ import annotations

import argparse
import sys

from spec_yaml import discover_paths, format_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Format SpecGraph YAML files")
    parser.add_argument(
        "paths", nargs="*", help="YAML files to format (defaults to specs/nodes/*.yaml)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    formatted_any = False
    for path in discover_paths(args.paths):
        try:
            formatted = format_file(path)
        except Exception as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            return 1
        if formatted:
            formatted_any = True
            print(f"formatted: {path}")

    if not formatted_any:
        print("spec YAML already canonical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
