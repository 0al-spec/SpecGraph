#!/usr/bin/env python3
"""Read-only discovery, validation, and lookup for canonical Decision nodes."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from spec_yaml import canonical_timestamp_text, load_yaml_text

API_VERSION = "specgraph.io/v0alpha1"
NODE_STATUSES = {"idea", "stub", "outlined", "specified", "linked", "reviewed", "frozen"}
AUTHORITIES = {"authored", "imported", "inferred", "distilled"}


@dataclass(frozen=True)
class DecisionNode:
    """Validated, immutable read model for a canonical Decision node."""

    path: Path
    id: str
    key: str
    title: str
    status: str
    created_at: str
    updated_at: str
    revision: int
    statement: str
    rationale: str
    authority: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "title": self.title,
            "status": self.status,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "revision": self.revision,
            "statement": self.statement,
            "rationale": self.rationale,
            "authority": self.authority,
            "path": self.path.as_posix(),
        }


class DecisionDocumentError(ValueError):
    """A canonical Decision document does not satisfy the node contract."""

    def __init__(self, path: Path, issues: list[str]) -> None:
        self.path = path
        self.issues = tuple(issues)
        super().__init__(f"{path}: " + "; ".join(issues))


class DecisionWorkspaceError(ValueError):
    """The workspace contains a YAML document that cannot be inspected."""


class DecisionIndexError(ValueError):
    """The read-only index contains ambiguous identities or a missing lookup."""


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _required_text(mapping: Mapping[str, Any], field: str, label: str, issues: list[str]) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{label} must be a non-empty string")
        return ""
    return value.strip()


def _timestamp(mapping: Mapping[str, Any], field: str, label: str, issues: list[str]) -> str:
    value = mapping.get(field)
    if not isinstance(value, (str, datetime)):
        issues.append(f"{label} must be a timezone-aware ISO 8601 timestamp")
        return ""
    try:
        return canonical_timestamp_text(value)
    except (TypeError, ValueError):
        issues.append(f"{label} must be a timezone-aware ISO 8601 timestamp")
        return ""


def parse_decision_document(data: Mapping[str, Any], path: Path) -> DecisionNode:
    """Validate a canonical Decision envelope without changing its source file."""
    issues: list[str] = []
    if data.get("apiVersion") != API_VERSION:
        issues.append(f"apiVersion must be {API_VERSION}")
    if data.get("kind") != "Node":
        issues.append("kind must be Node")

    metadata = _mapping(data.get("metadata"))
    if metadata is None:
        metadata = {}
        issues.append("metadata must be a mapping")
    node_id = _required_text(metadata, "id", "metadata.id", issues)
    key = _required_text(metadata, "key", "metadata.key", issues)
    node_type = _required_text(metadata, "type", "metadata.type", issues)
    title = _required_text(metadata, "title", "metadata.title", issues)
    status = _required_text(metadata, "status", "metadata.status", issues)
    if node_type and node_type != "decision":
        issues.append("metadata.type must be decision")
    if status and status not in NODE_STATUSES:
        issues.append(f"metadata.status must be one of: {', '.join(sorted(NODE_STATUSES))}")

    created_at = _timestamp(metadata, "createdAt", "metadata.createdAt", issues)
    updated_at = _timestamp(metadata, "updatedAt", "metadata.updatedAt", issues)
    if created_at and updated_at and updated_at < created_at:
        issues.append("metadata.updatedAt must not be earlier than metadata.createdAt")
    revision = metadata.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        issues.append("metadata.revision must be a positive integer")

    spec = _mapping(data.get("spec"))
    if spec is None:
        spec = {}
        issues.append("spec must be a mapping")
    statement = _required_text(spec, "statement", "spec.statement", issues)
    rationale = _required_text(spec, "rationale", "spec.rationale", issues)
    if "alternativesConsidered" in spec:
        alternatives = spec["alternativesConsidered"]
        if not isinstance(alternatives, list):
            issues.append("spec.alternativesConsidered must be a list when provided")
        else:
            for index, alternative in enumerate(alternatives, start=1):
                if _mapping(alternative) is None:
                    issues.append(f"spec.alternativesConsidered[{index}] must be a mapping")

    provenance = _mapping(data.get("provenance"))
    if provenance is None:
        provenance = {}
        issues.append("provenance must be a mapping")
    authority = _required_text(provenance, "authority", "provenance.authority", issues)
    if authority and authority not in AUTHORITIES:
        issues.append(f"provenance.authority must be one of: {', '.join(sorted(AUTHORITIES))}")
    sources = provenance.get("sources")
    if sources is not None and not isinstance(sources, list):
        issues.append("provenance.sources must be a list when provided")
    elif isinstance(sources, list):
        for index, source in enumerate(sources, start=1):
            source_mapping = _mapping(source)
            if source_mapping is None:
                issues.append(f"provenance.sources[{index}] must be a mapping")
            else:
                _required_text(source_mapping, "doc", f"provenance.sources[{index}].doc", issues)
                section = source_mapping.get("section")
                if section is not None and (not isinstance(section, str) or not section.strip()):
                    issues.append(f"provenance.sources[{index}].section must be a non-empty string")
    authored_by = provenance.get("authoredBy")
    if authored_by is not None and (not isinstance(authored_by, str) or not authored_by.strip()):
        issues.append("provenance.authoredBy must be a non-empty string when provided")

    lifecycle = data.get("lifecycle")
    if lifecycle is not None and not isinstance(lifecycle, Mapping):
        issues.append("lifecycle must be a mapping when provided")
    elif isinstance(lifecycle, Mapping):
        superseded_by = lifecycle.get("supersededBy")
        if superseded_by is not None and (
            not isinstance(superseded_by, str) or not superseded_by.strip()
        ):
            issues.append("lifecycle.supersededBy must be a non-empty key or null")
        for field in ("validFrom", "validUntil"):
            value = lifecycle.get(field)
            if value is None:
                continue
            try:
                canonical_timestamp_text(value)
            except (TypeError, ValueError):
                issues.append(
                    f"lifecycle.{field} must be a timezone-aware ISO 8601 timestamp or null"
                )

    if issues:
        raise DecisionDocumentError(path, issues)

    return DecisionNode(
        path=path,
        id=node_id,
        key=key,
        title=title,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        revision=revision,
        statement=statement,
        rationale=rationale,
        authority=authority,
    )


@dataclass(frozen=True)
class DecisionIndex:
    """Read-only indexes over validated Decision records."""

    by_id: Mapping[str, DecisionNode]
    by_key: Mapping[str, DecisionNode]

    def get_by_id(self, node_id: str) -> DecisionNode:
        try:
            return self.by_id[node_id]
        except KeyError as exc:
            raise DecisionIndexError(f"unknown Decision id: {node_id}") from exc

    def get_by_key(self, key: str) -> DecisionNode:
        try:
            return self.by_key[key]
        except KeyError as exc:
            raise DecisionIndexError(f"unknown Decision key: {key}") from exc


def index_decisions(nodes: list[DecisionNode]) -> DecisionIndex:
    """Build distinct ID and key indexes, rejecting ambiguity deterministically."""
    by_id: dict[str, DecisionNode] = {}
    by_key: dict[str, DecisionNode] = {}
    issues: list[str] = []
    for node in sorted(nodes, key=lambda item: item.path.as_posix()):
        for value, index, label in (
            (node.id, by_id, "id"),
            (node.key, by_key, "key"),
        ):
            previous = index.get(value)
            if previous is not None:
                issues.append(
                    f"duplicate Decision {label} {value!r}: {previous.path} and {node.path}"
                )
            else:
                index[value] = node
    if issues:
        raise DecisionIndexError("; ".join(issues))
    return DecisionIndex(MappingProxyType(by_id), MappingProxyType(by_key))


def load_decision_index(specs_root: Path) -> DecisionIndex:
    """Discover canonical Decision nodes below a product workspace specs root."""
    root = specs_root.resolve()
    if not root.is_dir():
        raise DecisionWorkspaceError(f"specs root is not a directory: {root}")
    paths = sorted((*root.rglob("*.yaml"), *root.rglob("*.yml")))
    nodes: list[DecisionNode] = []
    for path in paths:
        try:
            data = load_yaml_text(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DecisionWorkspaceError(f"{path}: unable to inspect YAML: {exc}") from exc
        metadata = _mapping(data.get("metadata"))
        if data.get("kind") != "Node" or metadata is None or metadata.get("type") != "decision":
            continue
        try:
            nodes.append(parse_decision_document(data, path))
        except DecisionDocumentError as exc:
            raise DecisionWorkspaceError(str(exc)) from exc
    return index_decisions(nodes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only canonical Decision index")
    parser.add_argument("specs_root", type=Path, help="Product workspace specs root")
    identity = parser.add_mutually_exclusive_group()
    identity.add_argument("--key", help="Look up a Decision by metadata.key")
    identity.add_argument("--id", help="Look up a Decision by metadata.id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.key is not None and not args.key.strip():
        print("--key must be a non-empty Decision key", file=sys.stderr)
        return 2
    if args.id is not None and not args.id.strip():
        print("--id must be a non-empty Decision id", file=sys.stderr)
        return 2
    try:
        index = load_decision_index(args.specs_root)
        if args.key is not None:
            records = [index.get_by_key(args.key)]
        elif args.id is not None:
            records = [index.get_by_id(args.id)]
        else:
            records = [index.by_key[key] for key in sorted(index.by_key)]
    except (DecisionWorkspaceError, DecisionIndexError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps([record.as_dict() for record in records], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
