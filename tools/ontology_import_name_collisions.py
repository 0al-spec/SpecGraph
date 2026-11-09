#!/usr/bin/env python3
"""Detect new same-named declarations in locally available import closures."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ontology_name_collisions import SECTIONS, CollisionKey, Definition, collisions, report
from project_ontology_context.foundation import ACTION_PIN, LEGACY_PIN, PIN

ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = (".",)
PROJECT_PREFIX = "org.0al.specgraph."
FOUNDATION_FILES = {
    "tools/project_ontology_context/pinned_foundation/exports.json": PIN,
    "tools/project_ontology_context/pinned_foundation/exports-0.2.0.json": ACTION_PIN,
}
FOUNDATION_IDS = {(pin.id, pin.version) for pin in (PIN, LEGACY_PIN, ACTION_PIN)}


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate mappings instead of silently dropping declarations."""

    def construct_mapping(self, node: yaml.nodes.MappingNode, deep: bool = False) -> dict:
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError(f"duplicate YAML key {key!r}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


@dataclass(frozen=True)
class Package:
    path: str
    identity: tuple[str, str]
    namespace: str
    imports: tuple[tuple[str, str], ...]
    sections: dict[str, dict[str, Any]]
    source_id: str | None = None
    pointer_root: str = "/spec"


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def required_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a nonempty string")
    return value


def parse_package(path: str, content: bytes) -> Package | None:
    if b"DomainOntologyPackage" not in content:
        return None
    loader = UniqueKeyLoader(content)
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    if not isinstance(data, dict) or data.get("kind") != "DomainOntologyPackage":
        return None
    metadata, spec = data.get("metadata"), data.get("spec")
    if not isinstance(metadata, dict) or not isinstance(spec, dict):
        raise ValueError(f"{path}: missing metadata or spec")
    package_id = required_string(metadata.get("id"), f"{path}: package id")
    version = required_string(metadata.get("version"), f"{path}: package version")
    namespace = required_string(metadata.get("namespace"), f"{path}: namespace")
    if ":" in namespace:
        raise ValueError(f"{path}: namespace must not contain ':'")
    imports = spec.get("imports", [])
    if not isinstance(imports, list) or any(not isinstance(item, dict) for item in imports):
        raise ValueError(f"{path}: imports must be a list of package references")
    identities = tuple(
        (
            required_string(item.get("id"), f"{path}: import id"),
            required_string(item.get("version"), f"{path}: import version"),
        )
        for item in imports
    )
    sections = {}
    for section in SECTIONS:
        values = spec.get(section, {})
        if not isinstance(values, dict) or any(
            not isinstance(key, str) or not key for key in values
        ):
            raise ValueError(f"{path}: {section} must be a mapping of names")
        sections[section] = values
    return Package(path, (package_id, version), namespace, identities, sections)


def catalog(root: Path, revision: str | None) -> dict[tuple[str, str], Package]:
    command = (
        ("ls-tree", "-r", "-z", "--name-only", revision, "--")
        if revision
        else ("ls-files", "-z", "--")
    )
    paths = git(root, *command, *SEARCH_ROOTS).decode("utf-8").split("\0")
    packages: dict[tuple[str, str], Package] = {}

    def content(path: str) -> bytes:
        local = root / path
        if revision:
            return git(root, "show", f"{revision}:{path}")
        if local.is_symlink():
            raise ValueError(f"{path}: symbolic links are not supported")
        return local.read_bytes()

    for path in sorted(
        p for p in paths if p.endswith((".yaml", ".yml")) and not p.startswith("tests/")
    ):
        package = parse_package(path, content(path))
        if package is None:
            continue
        if package.identity in packages:
            first = packages[package.identity]
            raise ValueError(
                f"ambiguous package {package.identity[0]}@{package.identity[1]}: "
                f"{first.path}, {package.path}"
            )
        packages[package.identity] = package

    for path, pin in FOUNDATION_FILES.items():
        if path not in paths:
            continue
        payload = content(path)
        if revision is None and hashlib.sha256(payload).hexdigest() != pin.source_sha256:
            raise ValueError(f"{path}: pinned foundation digest does not match")
        exports = json.loads(payload)
        if not isinstance(exports, dict) or (
            exports.get("schemaVersion"),
            exports.get("id"),
            exports.get("version"),
        ) != (1, pin.id, pin.version):
            raise ValueError(f"{path}: invalid foundation identity")
        sections: dict[str, dict[str, Any]] = {section: {} for section in SECTIONS}
        for section in ("classes", "protocols"):
            names = exports.get(section)
            if not isinstance(names, list) or any(not isinstance(x, str) or not x for x in names):
                raise ValueError(f"{path}: invalid foundation {section}")
            if len(names) != len(set(names)):
                raise ValueError(f"{path}: duplicate foundation {section}")
            sections[section] = dict.fromkeys(names, {})
        aliases = (pin, LEGACY_PIN) if pin == PIN else (pin,)
        for alias in aliases:
            identity = (alias.id, alias.version)
            if identity in packages:
                raise ValueError(f"ambiguous package {alias.id}@{alias.version}")
            packages[identity] = Package(path, identity, alias.namespace, (), sections, pin.id, "")
    return packages


def import_collisions(
    packages: dict[tuple[str, str], Package],
) -> tuple[dict[CollisionKey, tuple[Definition, Definition]], set[tuple[str, str, str]]]:
    found: dict[CollisionKey, tuple[Definition, Definition]] = {}
    missing: set[tuple[str, str, str]] = set()
    local_ids = {identity[0] for identity in packages}
    for start in sorted(packages):
        pending = [start]
        visited: dict[str, str] = {}
        closure: list[Package] = []
        while pending:
            identity = pending.pop()
            package = packages.get(identity)
            if package is None:
                continue
            previous = visited.get(identity[0])
            if previous is not None:
                if previous != identity[1]:
                    raise ValueError(f"conflicting versions of {identity[0]} in {start[0]} imports")
                continue
            visited[identity[0]] = identity[1]
            closure.append(package)
            for imported in package.imports:
                if imported not in packages:
                    if (
                        imported in FOUNDATION_IDS
                        or imported[0] in local_ids
                        or imported[0].startswith(PROJECT_PREFIX)
                    ):
                        raise ValueError(f"missing project import {imported[0]}@{imported[1]}")
                    missing.add((package.path, *imported))
                else:
                    pending.append(imported)

        graph: dict[str, Any] = {"schemaVersion": "ontology.diagram-projection/v1", "view": "full"}
        for section in SECTIONS:
            graph[section] = []
            for package in closure:
                for name in package.sections[section]:
                    pointer_name = name.replace("~", "~0").replace("/", "~1")
                    graph[section].append(
                        {
                            "fqid": f"{package.namespace}:{name}",
                            "source": {
                                "id": package.source_id or package.identity[0],
                                "version": package.identity[1],
                                "pointer": f"{package.pointer_root}/{section}/{pointer_name}",
                            },
                        }
                    )
        found.update(collisions(graph))
    return found, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--base-ref", default="origin/main")
    args = parser.parse_args(argv)
    try:
        base = git(
            args.root, "rev-parse", "--verify", "--end-of-options", f"{args.base_ref}^{{commit}}"
        )
        before, _ = import_collisions(catalog(args.root, base.decode().strip()))
        head_packages = catalog(args.root, None)
        after, missing = import_collisions(head_packages)
    except (
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
        yaml.YAMLError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"ontology import collision check failed: {error}", file=sys.stderr)
        return 2
    report("Existing import-closure collisions (unresolved)", set(before) & set(after), after)
    added = set(after) - set(before)
    report("New import-closure collisions", added, after)
    affected = {(item.package, item.version) for key in added for item in after[key]}
    for identity in sorted(affected):
        print(f"  Source {identity[0]}@{identity[1]}: {head_packages[identity].path}")
    print(f"Resolved import-closure collisions: {len(set(before) - set(after))}")
    for path, package_id, version in sorted(missing):
        print(f"External import {package_id}@{version} in {path}: not checked (source unavailable)")
    return 1 if added else 0


if __name__ == "__main__":
    raise SystemExit(main())
