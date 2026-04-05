#!/usr/bin/env python3
"""Lint SpecGraph YAML files for syntax, duplicate keys, and canonical formatting."""

from __future__ import annotations

import argparse
import sys

from spec_yaml import discover_paths, lint_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lint SpecGraph YAML files")
    parser.add_argument(
        "paths", nargs="*", help="YAML files to lint (defaults to specs/nodes/*.yaml)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    issues = []
    for path in discover_paths(args.paths):
        issues.extend(lint_file(path))

    if issues:
        for issue in issues:
            print(f"{issue.path}: {issue.message}", file=sys.stderr)
        return 1

    print("spec YAML lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
