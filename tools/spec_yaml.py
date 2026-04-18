#!/usr/bin/env python3
"""Shared helpers for canonical SpecGraph YAML formatting and linting."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLOB = "specs/nodes/*.yaml"
SPEC_TIMESTAMP_FIELDS = ("created_at", "updated_at")


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


def canonical_timestamp_text(value: Any) -> str:
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("timestamp must be a non-empty string")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone information")
    return (
        parsed.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def normalize_spec_timestamp_fields(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    for field in SPEC_TIMESTAMP_FIELDS:
        value = normalized.get(field)
        if value is None:
            continue
        normalized[field] = canonical_timestamp_text(str(value))
    return normalized


def with_spec_timestamps(
    data: dict[str, Any],
    *,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    preserved_items = [
        (key, value) for key, value in data.items() if key not in set(SPEC_TIMESTAMP_FIELDS)
    ]
    created_value = created_at if created_at is not None else data.get("created_at")
    updated_value = updated_at if updated_at is not None else data.get("updated_at")
    normalized_created = canonical_timestamp_text(str(created_value)) if created_value else ""
    normalized_updated = canonical_timestamp_text(str(updated_value)) if updated_value else ""
    if not normalized_created and normalized_updated:
        normalized_created = normalized_updated
    if not normalized_updated and normalized_created:
        normalized_updated = normalized_created

    rebuilt: dict[str, Any] = {}
    inserted = False
    for key, value in preserved_items:
        rebuilt[key] = value
        if key == "kind":
            if normalized_created:
                rebuilt["created_at"] = normalized_created
            if normalized_updated:
                rebuilt["updated_at"] = normalized_updated
            inserted = True
    if not inserted:
        if normalized_created:
            rebuilt["created_at"] = normalized_created
        if normalized_updated:
            rebuilt["updated_at"] = normalized_updated
        for key, value in preserved_items:
            rebuilt[key] = value
    return rebuilt


def canonicalize_text(text: str) -> str:
    data = load_yaml_text(text)
    data = normalize_spec_timestamp_fields(data)
    return dump_canonical_yaml(data)


def _validate_spec_shape(data: dict[str, Any]) -> list[str]:
    messages: list[str] = []

    for field in SPEC_TIMESTAMP_FIELDS:
        value = data.get(field)
        if isinstance(value, dt.datetime):
            text_value = canonical_timestamp_text(value)
        else:
            text_value = str(value).strip() if value is not None else ""
        if not text_value:
            messages.append(f"{field} must be a non-empty ISO 8601 timestamp string")
            continue
        try:
            canonical_timestamp_text(value)
        except ValueError as exc:
            messages.append(f"{field} is invalid: {exc}")
    created_at = data.get("created_at")
    updated_at = data.get("updated_at")
    if isinstance(created_at, str) and isinstance(updated_at, str):
        try:
            created_value = canonical_timestamp_text(created_at)
            updated_value = canonical_timestamp_text(updated_at)
        except ValueError:
            pass
        else:
            if updated_value < created_value:
                messages.append("updated_at must not be earlier than created_at")

    acceptance = data.get("acceptance", [])
    if not isinstance(acceptance, list):
        messages.append("acceptance must be a list")
    else:
        for index, item in enumerate(acceptance, start=1):
            if not isinstance(item, str):
                messages.append(f"acceptance[{index}] must be a string; avoid unquoted ': ' values")

    acceptance_evidence = data.get("acceptance_evidence", [])
    if not isinstance(acceptance_evidence, list):
        messages.append("acceptance_evidence must be a list")
    else:
        for index, item in enumerate(acceptance_evidence, start=1):
            if isinstance(item, str):
                continue
            if isinstance(item, dict):
                criterion = item.get("criterion")
                evidence = item.get("evidence")
                if isinstance(criterion, str) and isinstance(evidence, str):
                    continue
            messages.append(
                "acceptance_evidence"
                f"[{index}] must be a string or a mapping with string criterion and evidence"
            )

    return messages


def lint_file(path: Path) -> list[LintIssue]:
    issues: list[LintIssue] = []
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [LintIssue(path=path, message="file does not exist")]

    try:
        data = load_yaml_text(source)
    except Exception as exc:
        return [LintIssue(path=path, message=str(exc))]

    for message in _validate_spec_shape(data):
        issues.append(LintIssue(path=path, message=message))

    canonical = dump_canonical_yaml(data)
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
