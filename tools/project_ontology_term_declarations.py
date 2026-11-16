"""Read explicitly declared ontology terms and their YAML locations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode
from yaml.tokens import AliasToken

PROFILE = "specgraph-explicit-terms-v1"


def _fields(node: MappingNode) -> dict[str, Any]:
    fields = {}
    for key, value in node.value:
        if not isinstance(key, ScalarNode) or key.tag != "tag:yaml.org,2002:str":
            raise ValueError("mapping keys must be strings")
        if key.value in fields:
            raise ValueError(f"duplicate YAML key: {key.value}")
        fields[key.value] = value
    return fields


def source_position(node: ScalarNode) -> dict[str, Any]:
    start, end = node.start_mark, node.end_mark
    return {
        "start": {"line": start.line + 1, "column": start.column + 1, "offset": start.index},
        "end": {"line": end.line + 1, "column": end.column + 1, "offset": end.index},
    }


def _explicit(node: MappingNode) -> tuple[str | None, list[tuple[str, ScalarNode]]]:
    top = _fields(node)
    identity = top.get("id")
    if identity is not None and (
        not isinstance(identity, ScalarNode) or identity.tag != "tag:yaml.org,2002:str"
    ):
        raise ValueError("spec id must be a string")
    terms = []
    contexts = [("", top)]
    if "specification" in top:
        if not isinstance(top["specification"], MappingNode):
            raise ValueError("specification must be a mapping")
        specification = _fields(top["specification"])
        contexts.append(("specification.", specification))
        if "terminology" in specification:
            terminology = specification["terminology"]
            if not isinstance(terminology, MappingNode):
                raise ValueError("specification.terminology must be a mapping")
            _fields(terminology)
            terms.extend(("specification.terminology", key) for key, _ in terminology.value)
    for prefix, fields in contexts:
        if "ontology_refs" not in fields:
            continue
        refs = fields["ontology_refs"]
        if not isinstance(refs, SequenceNode):
            raise ValueError(f"{prefix}ontology_refs must be a list")
        for index, item in enumerate(refs.value):
            if not isinstance(item, ScalarNode) or item.tag != "tag:yaml.org,2002:str":
                raise ValueError(f"{prefix}ontology_refs entries must be strings")
            terms.append((f"{prefix}ontology_refs[{index}]", item))
    return identity.value if identity is not None else None, terms


def read_term_declarations(name: str, raw: bytes) -> tuple[str, list[tuple[str, ScalarNode]]]:
    text = raw.decode("utf-8")
    if any(isinstance(token, AliasToken) for token in yaml.scan(text)):
        raise ValueError(f"YAML aliases are unsupported for source locations: {name}")
    node = yaml.compose(text)
    if not isinstance(node, MappingNode):
        raise ValueError(f"spec is not a YAML mapping: {name}")
    spec_id, terms = _explicit(node)
    return spec_id or Path(name).stem, terms


def term_field_path(field: str, term: str) -> str:
    if field == "specification.terminology":
        return f"{field}[{json.dumps(term, ensure_ascii=False)}]"
    return field
