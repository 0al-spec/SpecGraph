#!/usr/bin/env python3
"""Shared helpers for canonical SpecGraph YAML formatting and linting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLOB = "specs/nodes/*.yaml"


class DuplicateKeyError(ValueError):
    """Raised when a YAML mapping contains duplicate keys."""


class SpecYamlLoader(yaml.SafeLoader):
    """Strict YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: SpecYamlLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(f"duplicate key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


SpecYamlLoader.add_constructor(  # type: ignore[arg-type]
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class LintIssue:
    path: Path
    message: str


def discover_paths(raw_paths: list[str]) -> list[Path]:
    if raw_paths:
        return [Path(path).resolve() for path in raw_paths]
    return sorted(path.resolve() for path in ROOT.glob(DEFAULT_GLOB))


def load_yaml_text(text: str) -> dict[str, Any]:
    data = yaml.load(text, Loader=SpecYamlLoader)
    if not isinstance(data, dict):
        raise ValueError("top-level YAML document must be a mapping")
    return data


def dump_canonical_yaml(data: dict[str, Any]) -> str:
    rendered = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )
    if not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def canonicalize_text(text: str) -> str:
    data = load_yaml_text(text)
    return dump_canonical_yaml(data)


def lint_file(path: Path) -> list[LintIssue]:
    issues: list[LintIssue] = []
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [LintIssue(path=path, message="file does not exist")]

    try:
        canonical = canonicalize_text(source)
    except Exception as exc:
        return [LintIssue(path=path, message=str(exc))]

    if source != canonical:
        issues.append(
            LintIssue(
                path=path,
                message=(
                    "file is not canonically formatted; run "
                    f"`python tools/spec_yaml_format.py {path}`"
                ),
            )
        )
    return issues


def format_file(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    canonical = canonicalize_text(source)
    if source == canonical:
        return False
    path.write_text(canonical, encoding="utf-8")
    return True
