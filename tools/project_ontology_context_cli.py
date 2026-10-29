#!/usr/bin/env python3
"""Capture a read-only, explicitly selected project ontology context."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

from project_ontology_context import capture_project_context

PROJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def workspace_path(root: Path, path: Path) -> Path:
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"path is outside workspace: {path}")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
        epilog="Exit status: 0 verified, 1 unavailable, 2 invalid or CLI/input error.",
    )
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--project-id")
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--ontologyc", type=Path)
    parser.add_argument("--compiler-sha256")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.workspace_root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError("workspace must be an existing directory")
        config_path = workspace_path(root, Path("specgraph.project.yaml"))
        config = {}
        if config_path.is_file() and (args.project_id is None or args.selection is None):
            config = yaml.safe_load(config_path.read_text())
            if (
                not isinstance(config, dict)
                or config.get("artifact_kind") != "specgraph_project_config"
                or type(config.get("schema_version")) is not int
                or config["schema_version"] != 1
            ):
                raise ValueError("invalid specgraph.project.yaml")
        project_id = args.project_id if args.project_id is not None else config.get("project_id")
        if not isinstance(project_id, str) or not PROJECT_ID.fullmatch(project_id):
            raise ValueError("a valid --project-id or configured project_id is required")
        selection = args.selection
        if selection is None and "ontology_context" in config:
            context = config["ontology_context"]
            if not isinstance(context, dict):
                raise ValueError("ontology_context must be a mapping")
            selected = context.get("selection")
            if selected is not None:
                if not isinstance(selected, str) or not selected.strip():
                    raise ValueError("ontology_context.selection must be a non-empty path")
                selection = Path(selected)
        if selection is not None:
            selection = workspace_path(root, selection).relative_to(root)
        output = workspace_path(root, args.output) if args.output is not None else None
        if output is not None and not output.parent.is_dir():
            raise ValueError("output parent directory must exist")
        if output is not None:
            protected = {config_path}
            if selection is not None:
                selection_file = workspace_path(root, selection)
                protected.add(selection_file)
                try:
                    payload = yaml.safe_load(selection_file.read_text())
                    packages = payload.get("packages", []) if isinstance(payload, dict) else []
                    if isinstance(packages, list):
                        for package in packages:
                            if isinstance(package, dict):
                                for key in ("source", "ir"):
                                    if isinstance(package.get(key), str):
                                        protected.add(workspace_path(root, Path(package[key])))
                except (OSError, UnicodeError, yaml.YAMLError, ValueError):
                    pass  # Capture reports malformed or unavailable selections.
            if output in protected:
                raise ValueError(
                    "output must not overwrite project configuration or ontology inputs"
                )
            if output.exists():
                try:
                    previous = json.loads(output.read_text())
                except (OSError, UnicodeError, json.JSONDecodeError) as error:
                    raise ValueError("output already exists and is not a context report") from error
                if (
                    not isinstance(previous, dict)
                    or previous.get("artifact_kind") != "project_ontology_context_report"
                ):
                    raise ValueError("output already exists and is not a context report")
        result = capture_project_context(
            root,
            project_id=project_id,
            selection_path=selection,
            ontologyc=args.ontologyc,
            compiler_sha256=args.compiler_sha256,
        )
        report = json.dumps(result.report(), indent=2, sort_keys=True) + "\n"
        if output is not None:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=output.parent, delete=False
                ) as stream:
                    temporary = Path(stream.name)
                    stream.write(report)
                os.replace(temporary, output)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        sys.stdout.write(report)
        return {"verified": 0, "unavailable": 1, "invalid": 2}[result.outcome]
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
