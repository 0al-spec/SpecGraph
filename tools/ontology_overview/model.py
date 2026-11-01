"""Immutable selected roles and deterministic HC/HCS rendering."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*\Z")
PROFILE = "specgraph-ontology-overview-v1"
FIELDS = frozenset(
    {
        "ontology_ref",
        "ontology_source",
        "ontology_sha256",
        "composition_ref",
        "scenario_source",
        "scenario_sha256",
        "production_path",
        "production_symbol",
        "production_anchor",
        "production_sha256",
    }
)


class OverviewError(ValueError):
    def __init__(self, message: str, *, outcome: str = "invalid"):
        super().__init__(message)
        self.outcome = outcome


def text(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(ord(c) < 32 or c in "\x7f\u0085\u2028\u2029" for c in value)
    ):
        raise OverviewError("mapping values must be nonempty, single-line strings")
    return value


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class Role:
    name: str
    identity: str
    source_type: str
    properties: tuple[tuple[str, str], ...]
    children: tuple[Role, ...]

    def walk(self, parent: tuple[str, ...] = ()):
        path = (*parent, self.name)
        yield path, self
        for child in self.children:
            yield from child.walk(path)


def selected_role(ir: object) -> Role:
    """Read the reference compiler's resolved IR, not another HC/HCS parser."""
    if not isinstance(ir, dict) or ir.get("version") != "hypercode.ir/v2":
        raise OverviewError("expected Hypercode IR v2")
    if ir.get("context") != {}:
        raise OverviewError("this export profile requires the empty Hypercode context")
    roots = ir.get("nodes")
    if not isinstance(roots, list) or len(roots) != 1:
        raise OverviewError("select exactly one composition root")

    def read(node: object) -> Role:
        if not isinstance(node, dict) or not isinstance(node.get("properties"), dict):
            raise OverviewError("malformed Hypercode role")
        values = {
            key: text(entry.get("value") if isinstance(entry, dict) else None)
            for key, entry in node["properties"].items()
            if key in FIELDS | {"overview_name", "role_id"}
        }
        source_type = text(node.get("type"))
        name = values.get("overview_name", source_type)
        if not NAME.fullmatch(name):
            raise OverviewError(f"overview_name must be a simple HC name: {name!r}")
        identity = text(values.get("role_id", node.get("id")))
        if node.get("id") is not None and identity != node["id"]:
            raise OverviewError("role_id disagrees with the source HC id")
        if "ontology_ref" not in values:
            raise OverviewError(f"missing ontology_ref for role {identity}")
        children = node.get("children")
        if not isinstance(children, list):
            raise OverviewError("malformed Hypercode children")
        return Role(
            name,
            identity,
            source_type,
            tuple(sorted((k, v) for k, v in values.items() if k in FIELDS)),
            tuple(read(child) for child in children),
        )

    root = read(roots[0])
    roles = tuple(root.walk())
    if len({role.identity for _, role in roles}) != len(roles):
        raise OverviewError("each selected role must have a distinct identity")
    for _, role in roles:
        if len({child.name for child in role.children}) != len(role.children):
            raise OverviewError("duplicate sibling overview names need explicit disambiguation")
    return root


def render(root: Role, bindings: dict[str, dict[str, str]]) -> tuple[bytes, bytes]:
    roles = tuple(root.walk())
    hc = "".join(f"{'  ' * (len(path) - 1)}{role.name}\n" for path, role in roles).encode()
    hcs = []
    for path, role in roles:
        properties = {
            **bindings[role.identity],
            "role_id": role.identity,
            "source_type": role.source_type,
        }
        if role is root:
            properties.update(
                projection_profile=PROFILE, composition_status="proposed", hc_sha256=sha(hc)
            )
        hcs.append(f"{' > '.join(path)}:\n")
        hcs.extend(f'  {key}: "{text(value)}"\n' for key, value in sorted(properties.items()))
        hcs.append("\n")
    return hc, ("".join(hcs).rstrip("\n") + "\n").encode()
