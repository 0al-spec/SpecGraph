#!/usr/bin/env python3
"""Install a pinned SpecGraph source snapshot and run it in a product workspace."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

COMMIT = re.compile(r"^[0-9a-f]{40}$")
REMOTE_SOURCE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*://|[^/]+:)")


def resolve_git_source(source: str, caller_root: Path) -> str:
    """Resolve local paths before Git changes cwd, preserving remote syntax."""
    if not source:
        raise ValueError("Git source must not be empty")
    if REMOTE_SOURCE.match(source):
        return source
    return str((caller_root / Path(source).expanduser()).resolve())


def execute(arguments: list[str], *, cwd: Path | None = None) -> None:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(arguments, cwd=cwd, env=environment, stdout=sys.stderr, check=True)


def extract_snapshot(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r") as bundle:
        for item in bundle.getmembers():
            path = PurePosixPath(item.name)
            if path.is_absolute() or ".." in path.parts or not (item.isfile() or item.isdir()):
                raise ValueError(f"Unsupported archive member: {item.name}")
        bundle.extractall(destination)  # All member paths and types were checked above.


def install(source: str, revision: str, destination: Path) -> dict[str, str]:
    version = ".".join(map(str, sys.version_info[:3]))
    interpreter = sys.executable or "<unknown executable>"
    if sys.version_info < (3, 10):  # noqa: UP036 -- standalone bootstrap can run on older Python
        raise ValueError(
            f"Python 3.10 or newer is required; found Python {version} at {interpreter}"
        )
    print(f"Using Python {version} at {interpreter}", file=sys.stderr)
    if not COMMIT.fullmatch(revision):
        raise ValueError("Revision must be a full lowercase Git commit SHA")
    if shutil.which("git") is None:
        raise ValueError("Git is required for installation")
    source = resolve_git_source(source, Path.cwd())
    target = destination.expanduser().absolute()
    if target.is_symlink() or target.exists():
        raise ValueError("Installation destination already exists")
    if not target.parent.is_dir():
        raise ValueError("Installation destination parent must already exist")
    target.mkdir()
    snapshot = target / "source"
    snapshot.mkdir()
    # Temporary Git objects are discarded; the installed snapshot has no .git.
    # An interrupted or failed installation is left in place for inspection and
    # cannot be mistaken for a ready installation without runtime.json.
    with tempfile.TemporaryDirectory(prefix="specgraph-install-") as temporary:
        temp = Path(temporary)
        git = temp / "source.git"
        execute(["git", "init", "--bare", "--quiet", str(git)])
        execute(["git", "-C", str(git), "fetch", "--quiet", "--depth=1", "--", source, revision])
        selected = subprocess.check_output(
            ["git", "-C", str(git), "rev-parse", "FETCH_HEAD^{commit}"], text=True
        ).strip()
        if selected != revision:
            raise ValueError("Fetched commit does not match requested revision")
        archive = temp / "snapshot.tar"
        execute(["git", "-C", str(git), "archive", "--format=tar", f"--output={archive}", revision])
        extract_snapshot(archive, snapshot)
        if not (snapshot / "tools" / "native_runtime.py").is_file():
            raise ValueError("Selected revision does not contain the native runtime launcher")
        execute([sys.executable, "-m", "venv", str(target / "venv")])
        python = target / "venv" / "bin" / "python"
        # Build from a temporary copy so package-manager build products never
        # modify the runtime snapshot, which is also the supervisor's tool root.
        build_source = temp / "build-source"
        shutil.copytree(snapshot, build_source)
        execute([str(python), "-m", "pip", "install", str(build_source)])
    launcher = target / "specgraph-runtime"
    command = [
        str(python),
        str(snapshot / "tools" / "native_runtime.py"),
        "run",
        "--installation",
        str(target),
    ]
    launcher.write_text("#!/bin/sh\nexec " + " ".join(map(shlex.quote, command)) + ' "$@"\n')
    launcher.chmod(0o755)
    receipt = {
        "artifact_kind": "specgraph_native_runtime",
        "schema_version": 1,
        "status": "installed",
        "source_commit": selected,
        "python_version": subprocess.check_output(
            [str(python), "-I", "-c", "import platform; print(platform.python_version())"],
            text=True,
        ).strip(),
    }
    (target / "runtime.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return {**receipt, "launcher": str(launcher)}


def run(installation: Path, workspace: Path, operation: str, arguments: list[str]) -> int:
    # Imported only after installation: the standalone bootstrap has no
    # SpecificationCore dependency until it has created its own environment.
    from native_runtime_context import RuntimeReadyFacts
    from native_runtime_ready_spec import RUNTIME_READY_SPEC

    root = installation.expanduser().resolve(strict=True)
    receipt = json.loads((root / "runtime.json").read_text())
    if not isinstance(receipt, dict):
        raise ValueError("Installation receipt must be an object")
    facts = RuntimeReadyFacts(
        artifact_kind=str(receipt.get("artifact_kind", "")),
        status=str(receipt.get("status", "")),
        schema_version=receipt.get("schema_version"),
        source_commit=str(receipt.get("source_commit", "")),
    )
    if not RUNTIME_READY_SPEC.is_satisfied_by(facts):
        raise ValueError("Installation is not ready")
    project = workspace.expanduser().resolve()
    if project == root or root in project.parents:
        raise ValueError("Workspace must be outside the installed runtime")
    source = root / "source"
    python = root / "venv" / "bin" / "python"
    if operation == "init":
        command = [
            str(python),
            str(source / "tools" / "supervisor.py"),
            "--init-product-workspace",
            "--workspace-root",
            str(project),
            *arguments,
        ]
        cwd = source
    elif operation == "next-move":
        command = [
            str(python),
            str(source / "tools" / "product_workspace_next_moves.py"),
            "--workspace-root",
            str(project),
            *arguments,
        ]
        cwd = project
    elif operation == "ontology-context":
        if any(
            arg == "--workspace-root" or arg.startswith("--workspace-root=") for arg in arguments
        ):
            raise ValueError("ontology-context workspace is selected by --workspace")
        command = [
            str(python),
            str(source / "tools" / "project_ontology_context_cli.py"),
            "--workspace-root",
            str(project),
            *arguments,
        ]
        cwd = project
    elif operation == "supervisor":
        command = [str(python), str(source / "tools" / "supervisor.py"), *arguments]
        cwd = project
    else:
        command = [str(python), "-I", "-m", "specgraph", *arguments]
        cwd = project
    if operation != "init" and not project.is_dir():
        raise ValueError("Workspace must be an existing directory")
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    return subprocess.run(command, cwd=cwd, env=environment, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install")
    setup.add_argument("--source", required=True, help="Git repository path or URL")
    setup.add_argument("--revision", required=True, help="Full commit SHA")
    setup.add_argument("--destination", required=True, type=Path)
    launch = commands.add_parser("run")
    launch.add_argument("--installation", required=True, type=Path)
    launch.add_argument("--workspace", required=True, type=Path)
    launch.add_argument(
        "operation", choices=("init", "next-move", "supervisor", "draft", "ontology-context")
    )
    args, extra = parser.parse_known_args(argv)
    if extra and extra[0] == "--":
        extra.pop(0)
    try:
        if args.command == "install":
            if extra:
                parser.error("install does not accept extra arguments")
            print(json.dumps(install(args.source, args.revision, args.destination), indent=2))
            return 0
        return run(args.installation, args.workspace, args.operation, extra)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
