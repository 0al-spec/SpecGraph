#!/usr/bin/env python3
"""Format SpecGraph YAML files into canonical repository style."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

import yaml

from spec_yaml import canonicalize_text, discover_paths, format_file
from spec_yaml_workspace import selected_yaml_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Format SpecGraph YAML files", allow_abbrev=False)
    parser.add_argument("--workspace-root", type=Path, help="select a workspace and emit JSON")
    parser.add_argument(
        "paths", nargs="*", help="YAML files to format (defaults to specs/nodes/*.yaml)"
    )
    return parser


def format_workspace(workspace: Path, paths: list[str]) -> int:
    selected = list(dict.fromkeys(selected_yaml_files(workspace, paths)))
    prepared = []
    # Parse the complete selection before changing any file.
    for relative, path in selected:
        raw = path.read_bytes()
        canonical = canonicalize_text(raw.decode("utf-8")).encode("utf-8")
        prepared.append((relative, path, raw, canonical))
    files = []
    for relative, path, raw, canonical in prepared:
        entry = {
            "path": relative.as_posix(),
            "status": "unchanged",
            "before_sha256": hashlib.sha256(raw).hexdigest(),
            "after_sha256": hashlib.sha256(raw).hexdigest(),
        }
        temporary = None
        try:
            # Recheck the selection and bytes before replacing the file.
            selected_yaml_files(workspace, [relative.as_posix()])
            if path.read_bytes() != raw:
                raise ValueError("file changed since it was read")
            if canonical != raw:
                mode = stat.S_IMODE(path.stat().st_mode)
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(canonical)
                    stream.flush()
                    os.fchmod(stream.fileno(), mode)
                os.replace(temporary, path)
                entry["status"] = "changed"
                entry["after_sha256"] = hashlib.sha256(canonical).hexdigest()
        except (OSError, RuntimeError, ValueError) as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
            entry["after_sha256"] = None
            files.append(entry)
            break
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        files.append(entry)
    failed = any(entry["status"] == "failed" for entry in files)
    print(
        json.dumps(
            {
                "artifact_kind": "specgraph_yaml_format",
                "schema_version": 1,
                "status": "failed" if failed else "complete",
                "files": files,
                "not_attempted": [relative.as_posix() for relative, _ in selected[len(files) :]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(failed)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.workspace_root is not None:
        try:
            return format_workspace(args.workspace_root, args.paths)
        except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
            parser.error(str(exc))

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
