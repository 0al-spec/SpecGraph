#!/usr/bin/env python3
"""Run ontology advice with exact imported packages from the active Git index."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

MAX_BYTES = 4 * 1024 * 1024
FOUNDATION_IDS = frozenset({"ontology.foundation", "specgraph.foundation"})
YAML_PATHS = (":(top,icase,glob)**/*.yaml", ":(top,icase,glob)**/*.yml")


def git(*arguments: str, allow_no_match: bool = False) -> bytes:
    environment = os.environ | {"GIT_NO_LAZY_FETCH": "1"}
    result = subprocess.run(["git", *arguments], capture_output=True, check=False, env=environment)
    if result.returncode and not (allow_no_match and result.returncode == 1):
        raise RuntimeError(f"git {arguments[0]} failed: {os.fsdecode(result.stderr).strip()}")
    return result.stdout


def paths(data: bytes) -> list[str]:
    return [os.fsdecode(part) for part in data.split(b"\0") if part]


def read_indexed(path: str) -> tuple[str, bytes]:
    entries = git("ls-files", "--stage", "--full-name", "-z", "--", f":(top,literal){path}").split(
        b"\0"
    )
    entries = [entry for entry in entries if entry]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ValueError("index file is missing or unmerged")
    header, indexed_path = entries[0].split(b"\t", 1)
    mode, oid_bytes, stage = header.split(b" ")
    if not mode.startswith(b"100") or stage != b"0" or os.fsdecode(indexed_path) != path:
        raise ValueError("index file is not a resolved regular file")
    oid = oid_bytes.decode("ascii")
    size = int(git("cat-file", "-s", oid))
    if size > MAX_BYTES:
        raise ValueError(f"index blob exceeds {MAX_BYTES} bytes")
    return oid, git("cat-file", "blob", oid)


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate keys rather than guess which import declaration applies."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError(f"duplicate YAML key {key!r}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def package(source: bytes) -> dict | None:
    document = yaml.load(source, Loader=UniqueKeyLoader)
    if not isinstance(document, dict) or document.get("kind") != "DomainOntologyPackage":
        return None
    return document


def identity(document: dict) -> tuple[str, str] | None:
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        return None
    package_id, version = metadata.get("id"), metadata.get("version")
    if not isinstance(package_id, str) or not isinstance(version, str):
        return None
    return package_id, version


def imports(document: dict) -> list[tuple[str, str]]:
    spec = document.get("spec")
    entries = spec.get("imports", []) if isinstance(spec, dict) else []
    if not isinstance(entries, list):
        return []
    return [
        (entry["id"], entry["version"])
        for entry in entries
        if isinstance(entry, dict)
        and isinstance(entry.get("id"), str)
        and isinstance(entry.get("version"), str)
        and entry["id"] not in FOUNDATION_IDS
    ]


def select_imports() -> tuple[list[str], list[str]]:
    changed = set(
        paths(
            git(
                "diff",
                "--cached",
                "--name-only",
                "--no-relative",
                "--no-renames",
                "--diff-filter=AMT",
                "-z",
                "--",
                *YAML_PATHS,
            )
        )
    )
    candidates = set(
        paths(
            git(
                "grep",
                "--cached",
                "--full-name",
                "--name-only",
                "-z",
                "-e",
                "DomainOntologyPackage",
                "--",
                *YAML_PATHS,
                allow_no_match=True,
            )
        )
    )
    records: dict[tuple[str, str], list[tuple[str, str, dict]]] = {}
    roots: list[tuple[str, dict]] = []
    messages: list[str] = []
    for path in sorted(candidates | changed):
        try:
            oid, source = read_indexed(path)
            document = package(source)
        except (RuntimeError, ValueError, yaml.YAMLError, TypeError) as error:
            if path in changed:
                messages.append(
                    f"{path!r}: import selection could not read staged package: {error}"
                )
            continue
        if document is None:
            continue
        if path in changed:
            roots.append((path, document))
        if (key := identity(document)) is not None:
            records.setdefault(key, []).append((path, oid, document))

    selected: set[str] = set()
    seen: set[tuple[str, str]] = set()
    pending = [(path, key) for path, document in roots for key in imports(document)]
    while pending:
        origin, key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        matches = records.get(key, [])
        if not matches:
            messages.append(
                f"{origin!r}: imported package {key[0]}@{key[1]} is unavailable in the active index"
            )
            continue
        if len({record[1] for record in matches}) != 1:
            messages.append(
                f"{origin!r}: imported package {key[0]}@{key[1]} is ambiguous: "
                + ", ".join(repr(item[0]) for item in matches)
            )
            continue
        path, _, document = min(
            matches, key=lambda item: (not item[0].startswith("ontology/packages/"), item[0])
        )
        selected.add(path)
        pending.extend((path, dependency) for dependency in imports(document))
    return sorted(selected), messages


def install(compiler: str) -> None:
    probe = subprocess.run(
        [compiler, "advise-staged", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if probe.returncode or "--import" not in probe.stdout:
        raise ValueError("compiler must support advise-staged --import")
    hook_help = subprocess.run(["git", "hook", "-h"], capture_output=True, check=False)
    if b"git hook list" not in hook_help.stdout + hook_help.stderr:
        raise ValueError("configured hooks require Git 2.54 or compatible support")
    common = Path(
        os.fsdecode(git("rev-parse", "--path-format=absolute", "--git-common-dir")).strip()
    )
    directory = common / "specgraph"
    directory.mkdir(exist_ok=True)
    destination = directory / "ontology_advice_staged.py"
    with tempfile.NamedTemporaryFile(
        dir=directory, prefix="ontology-advice-", delete=False
    ) as temporary:
        temporary.write(Path(__file__).read_bytes())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    command = " ".join(
        shlex.quote(value) for value in (sys.executable, str(destination), "--compiler", compiler)
    )
    command += (
        ' || echo "[ontology advice] import selection unavailable; packages were not checked" >&2'
    )
    git("config", "--local", "hook.ontology-package-advice.command", command)
    git("config", "--local", "hook.ontology-package-advice.event", "pre-commit")
    print(f"Installed index-aware ontology advice in {directory}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compiler", required=True, help="Path to ontologyc with advise-staged support"
    )
    parser.add_argument(
        "--install", action="store_true", help="Install the shared-clone pre-commit hook"
    )
    options = parser.parse_args()
    compiler = str(Path(options.compiler).resolve(strict=True))
    if options.install:
        install(compiler)
        return 0
    selected, messages = select_imports()
    for message in messages:
        print(f"[ontology advice] {message}", file=sys.stderr)
    arguments = [compiler, "advise-staged"]
    for path in selected:
        arguments.extend(("--import", path))
    return subprocess.run(arguments, check=False).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[ontology advice] import selection failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
