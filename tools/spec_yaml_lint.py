#!/usr/bin/env python3
"""Lint SpecGraph YAML files for syntax, duplicate keys, and canonical formatting."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from spec_yaml import discover_paths, inspect_yaml, lint_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lint SpecGraph YAML files", allow_abbrev=False)
    parser.add_argument(
        "--workspace-root", type=Path, help="limit paths to a workspace and emit JSON"
    )
    parser.add_argument(
        "paths", nargs="*", help="YAML files to lint (defaults to specs/nodes/*.yaml)"
    )
    return parser


def lint_workspace(workspace: Path, paths: list[str]) -> int:
    root = workspace.resolve(strict=True)
    if not paths:
        raise ValueError("specify at least one workspace-relative YAML file")
    selected = []
    for value in paths:
        relative = Path(value)
        if (
            relative.parts[:2] not in {("specs", "nodes"), ("docs", "drafts")}
            or ".." in relative.parts
            or relative.suffix not in {".yaml", ".yml"}
        ):
            raise ValueError(
                "lint paths must be workspace-relative YAML under specs/nodes or docs/drafts"
            )
        path = root / relative
        if path.resolve() != path or (path.exists() and not path.is_file()):
            raise ValueError("lint paths must identify regular files and cannot traverse symlinks")
        selected.append((relative, path))

    files = []
    for relative, path in selected:
        result = inspect_yaml(path)
        files.append(
            {
                "path": relative.as_posix(),
                "checks_run": list(result.checks_run),
                "issues": [issue.message for issue in result.issues],
            }
        )
    failed = any(entry["issues"] for entry in files)
    report = {
        "artifact_kind": "specgraph_yaml_lint",
        "schema_version": 1,
        "status": "failed" if failed else "passed",
        "files": files,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(failed)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.workspace_root is not None:
        try:
            return lint_workspace(args.workspace_root, args.paths)
        except (OSError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))

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
