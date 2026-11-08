#!/usr/bin/env python3
"""Detect new same-named declarations across packages in a composed ontology."""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GRAPH = Path("specs/models/review/ontology-overview/generated/ontology.graph.json")
SECTIONS = ("classes", "relations", "protocols", "policies", "stateMachines")


@dataclass(frozen=True, order=True)
class Definition:
    package: str
    pointer: str
    fqid: str
    version: str

    @property
    def identity(self) -> tuple[str, str]:
        # A package version bump does not create a second declaration by itself.
        return self.package, self.pointer


CollisionKey = tuple[str, str, tuple[str, str], tuple[str, str]]


def declaration(record: Any, section: str) -> tuple[str, Definition]:
    if not isinstance(record, dict) or not isinstance(record.get("source"), dict):
        raise ValueError(f"{section} declaration has no source")
    source = record["source"]
    fqid, package, pointer, version = (
        record.get("fqid"),
        source.get("id"),
        source.get("pointer"),
        source.get("version"),
    )
    if not all(isinstance(item, str) and item for item in (fqid, package, pointer, version)):
        raise ValueError(f"{section} declaration has incomplete identity or source")
    namespace, separator, name = fqid.partition(":")
    if not namespace or not separator or not name:
        raise ValueError(f"{section} declaration has invalid fqid {fqid!r}")
    return name, Definition(package, pointer, fqid, version)


def declarations(graph: Any) -> list[tuple[str, str, Definition]]:
    if (
        not isinstance(graph, dict)
        or graph.get("schemaVersion") != "ontology.diagram-projection/v1"
    ):
        raise ValueError("expected an ontology.diagram-projection/v1 graph")
    if graph.get("view") != "full":
        raise ValueError("the collision check requires a full graph")

    result = []
    for section in SECTIONS:
        records = graph.get(section)
        if not isinstance(records, list):
            raise ValueError(f"graph section {section} must be a list")
        for record in records:
            name, definition = declaration(record, section)
            result.append((section, name, definition))
    return result


def collisions(graph: Any) -> dict[CollisionKey, tuple[Definition, Definition]]:
    groups: dict[tuple[str, str], dict[tuple[str, str], Definition]] = {}
    for section, name, definition in declarations(graph):
        groups.setdefault((section, name), {})[definition.identity] = definition

    result: dict[CollisionKey, tuple[Definition, Definition]] = {}
    for (section, name), by_identity in groups.items():
        for left, right in itertools.combinations(sorted(by_identity.values()), 2):
            if left.package != right.package:
                result[(section, name, left.identity, right.identity)] = (left, right)
    return result


def read_base(ref: str) -> Any:
    revision = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    data = subprocess.run(
        ["git", "show", f"{revision}:{GRAPH.as_posix()}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(data)


def report(
    label: str, keys: set[CollisionKey], found: dict[CollisionKey, tuple[Definition, Definition]]
) -> None:
    print(f"{label}: {len(keys)}")
    for key in sorted(keys):
        section, name, _, _ = key
        left, right = found[key]
        print(f"  {section} {name}")
        for definition in (left, right):
            print(
                f"    {definition.fqid} — {definition.package}@{definition.version} "
                f"{definition.pointer}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    base = parser.add_mutually_exclusive_group()
    base.add_argument("--base-ref", default=None, help="Git base revision (default: origin/main)")
    base.add_argument(
        "--base-graph", type=Path, help="base projection JSON instead of a Git revision"
    )
    parser.add_argument("--head-graph", type=Path, default=ROOT / GRAPH)
    args = parser.parse_args(argv)
    try:
        previous = (
            json.loads(args.base_graph.read_bytes())
            if args.base_graph
            else read_base(args.base_ref or "origin/main")
        )
        current = json.loads(args.head_graph.read_bytes())
        before, after = collisions(previous), collisions(current)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"ontology collision check failed: {error}", file=sys.stderr)
        return 2
    known = set(before) & set(after)
    added = set(after) - set(before)
    report("Existing collisions (unresolved)", known, after)
    report("New collisions", added, after)
    print(f"Resolved collisions: {len(set(before) - set(after))}")
    return 1 if added else 0


if __name__ == "__main__":
    raise SystemExit(main())
