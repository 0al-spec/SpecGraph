#!/usr/bin/env python3
"""Backfill canonical spec timestamps from git history or filesystem metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import subprocess
import sys
from pathlib import Path

try:
    from spec_yaml import (
        ROOT,
        canonical_timestamp_text,
        discover_paths,
        dump_canonical_yaml,
        load_yaml_text,
        with_spec_timestamps,
    )
except ModuleNotFoundError:
    spec_yaml_path = Path(__file__).resolve().with_name("spec_yaml.py")
    spec = importlib.util.spec_from_file_location("_spec_yaml_backfill_runtime", spec_yaml_path)
    if spec is None or spec.loader is None:
        raise
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    ROOT = module.ROOT
    canonical_timestamp_text = module.canonical_timestamp_text
    discover_paths = module.discover_paths
    dump_canonical_yaml = module.dump_canonical_yaml
    load_yaml_text = module.load_yaml_text
    with_spec_timestamps = module.with_spec_timestamps


def filesystem_timestamp(path: Path, *, created: bool) -> str:
    stat_result = path.stat()
    if created and hasattr(stat_result, "st_birthtime"):
        raw_value = float(stat_result.st_birthtime)
    else:
        raw_value = float(stat_result.st_mtime)
    timestamp = dt.datetime.fromtimestamp(raw_value, tz=dt.timezone.utc).isoformat()
    return canonical_timestamp_text(timestamp)


def git_timestamp(path: Path, *, created: bool) -> str | None:
    try:
        relpath = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return None
    args = ["git", "log"]
    if created:
        args.extend(["--follow", "--diff-filter=A", "--format=%aI", "--reverse"])
    else:
        args.extend(["-1", "--format=%aI"])
    args.extend(["--", relpath])
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    value = lines[0] if created else lines[-1]
    return canonical_timestamp_text(value)


def derive_timestamps(path: Path, *, prefer_filesystem: bool = False) -> tuple[str, str]:
    if prefer_filesystem:
        created_at = filesystem_timestamp(path, created=True)
        updated_at = filesystem_timestamp(path, created=False)
        return created_at, updated_at

    created_at = git_timestamp(path, created=True) or filesystem_timestamp(path, created=True)
    updated_at = git_timestamp(path, created=False) or filesystem_timestamp(path, created=False)
    if updated_at < created_at:
        updated_at = created_at
    return created_at, updated_at


def backfill_file(path: Path, *, prefer_filesystem: bool = False) -> bool:
    source = path.read_text(encoding="utf-8")
    data = load_yaml_text(source)
    created_at, updated_at = derive_timestamps(path, prefer_filesystem=prefer_filesystem)
    updated = with_spec_timestamps(
        data,
        created_at=created_at,
        updated_at=updated_at,
    )
    rendered = dump_canonical_yaml(updated)
    if rendered == source:
        return False
    path.write_text(rendered, encoding="utf-8")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill spec created_at / updated_at timestamps")
    parser.add_argument(
        "paths",
        nargs="*",
        help="YAML files to update (defaults to specs/nodes/*.yaml)",
    )
    parser.add_argument(
        "--prefer-filesystem",
        action="store_true",
        help="Use filesystem times instead of git history when deriving timestamps",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    changed_any = False
    for path in discover_paths(args.paths):
        try:
            changed = backfill_file(path, prefer_filesystem=args.prefer_filesystem)
        except Exception as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            return 1
        if changed:
            changed_any = True
            print(f"backfilled: {path}")

    if not changed_any:
        print("spec timestamps already backfilled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
