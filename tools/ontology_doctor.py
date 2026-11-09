#!/usr/bin/env python3
"""Inspect the selected project's ontology prerequisites without changing the workspace."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

VERSION = re.compile(r"^(?:ontologyc\s+)?v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)$")


def compiler_info(path: Path | None, expected_sha256: str | None) -> dict:
    if path is None or not path.is_file() or not os.access(path, os.X_OK):
        return {"status": "unavailable", "path": str(path) if path else None, "version": None}
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        return {"status": "unavailable", "path": str(path), "version": None, "detail": str(error)}
    version = None
    if expected_sha256 is not None and digest != expected_sha256:
        return {
            "status": "invalid",
            "path": str(path.resolve()),
            "version": None,
            "sha256": digest,
            "provenance": "not_verified",
            "detail": "compiler SHA-256 mismatch",
        }
    try:
        result = subprocess.run(
            [str(path), "--version"], capture_output=True, text=True, timeout=3, check=False
        )
        match = VERSION.fullmatch(result.stdout.strip()) if result.returncode == 0 else None
        if match:
            version = match.group(1)
    except OSError as error:
        return {
            "status": "unavailable",
            "path": str(path.resolve()),
            "version": None,
            "sha256": digest,
            "provenance": "not_verified",
            "detail": f"Cannot launch compiler: {error}",
        }
    except (subprocess.TimeoutExpired, UnicodeError):
        pass
    return {
        "status": "available",
        "path": str(path.resolve()),
        "version": version,
        "sha256": digest,
        "provenance": "not_verified",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--project-id")
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--ontologyc", type=Path)
    parser.add_argument("--compiler-sha256")
    args = parser.parse_args(argv)
    root = args.workspace_root.expanduser().resolve()
    if not root.is_dir():
        print(json.dumps({"error": "workspace must be an existing directory"}), file=sys.stderr)
        return 2
    detected = shutil.which("ontologyc") if args.ontologyc is None else None
    compiler = args.ontologyc
    if compiler is None and detected:
        compiler = Path(detected)
    if compiler is not None and not compiler.is_absolute():
        compiler = root / compiler
    info = compiler_info(compiler, args.compiler_sha256)
    command = [
        sys.executable,
        str(Path(__file__).with_name("project_ontology_context_cli.py")),
        "--workspace-root",
        str(root),
    ]
    for flag, value in (
        ("--project-id", args.project_id),
        ("--selection", args.selection),
        ("--ontologyc", compiler),
        ("--compiler-sha256", args.compiler_sha256),
    ):
        if value is not None:
            command.extend((flag, str(value)))
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    try:
        context = json.loads(result.stdout) if result.stdout else None
        error = json.loads(result.stderr) if result.stderr else None
    except json.JSONDecodeError:
        context, error = None, {"error": "ontology-context produced an unreadable response"}
    hints = []
    if info["status"] != "available":
        hints.append(
            "Install a trusted ontologyc from https://github.com/0al-spec/Ontology/releases "
            "and run specgraph-runtime --workspace . ontology-doctor -- "
            "--ontologyc /path/to/ontologyc."
        )
    if context is not None:
        checks = context.get("checks", [])
        if any(c["check"] == "selection" and c["outcome"] == "unavailable" for c in checks):
            hints.append(
                "Create ontology/context.yaml with pinned package source and IR and configure "
                "ontology_context.selection; see docs/project_ontology_context.md for the template."
            )
        if context.get("outcome") != "verified" and not hints:
            hints.append("Review the context checks, package pins and compiler diagnostics.")
    elif error:
        hints.append(
            "Fix the project configuration or supply --project-id; "
            "see docs/project_ontology_context.md."
        )
    payload = {
        "artifact_kind": "specgraph_ontology_doctor",
        "schema_version": 1,
        "compiler": info,
        "context": context,
        "context_error": error,
        "next_steps": hints,
        "semantic_approval": "not_established",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if info["status"] == "invalid":
        return 2
    if info["status"] == "unavailable" and result.returncode == 0:
        return 1
    return result.returncode if result.returncode in (0, 1, 2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
