"""Inventory explicit terms using captured ontology IR; prose is not assessed.

Profile specgraph-explicit-terms-v1 reads specification.terminology mapping keys,
root ontology_refs, and specification.ontology_refs lists. Locations are 1-based,
with end positions exclusive; offsets are Unicode character offsets.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode
from yaml.tokens import AliasToken

from project_ontology_context import ContextResult
from spec_ontology_binding_index import slug, symbol_keys

PROFILE = "specgraph-explicit-terms-v1"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fields(node: MappingNode) -> dict[str, Any]:
    fields = {}
    for key, value in node.value:
        if not isinstance(key, ScalarNode) or key.tag != "tag:yaml.org,2002:str":
            raise ValueError("mapping keys must be strings")
        if key.value in fields:
            raise ValueError(f"duplicate YAML key: {key.value}")
        fields[key.value] = value
    return fields


def _position(node: ScalarNode) -> dict[str, Any]:
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


def build_term_inventory(
    context: ContextResult,
    *,
    workspace_root: Path,
    specs_root: Path,
    documents: tuple[tuple[str, bytes], ...] | None = None,
) -> dict[str, Any]:
    """Return structural candidates only, never semantic approval or conformance."""

    def failure(outcome: str, diagnostic: str) -> dict[str, Any]:
        return {
            "artifact_kind": "project_ontology_term_inventory",
            "schema_version": 1,
            "outcome": outcome,
            "diagnostics": [diagnostic],
            "entries": [],
            "inputs": None,
            "analysis_profile": PROFILE,
            "prose": "unassessed",
            "grounded": False,
        }

    root = Path(workspace_root).resolve()
    if not root.is_dir() or root != Path(context.workspace).resolve():
        return failure("invalid", "workspace does not match captured project context")
    if context.outcome == "invalid":
        return failure(
            "invalid",
            "invalid context: "
            + "; ".join(c.detail for c in context.checks if c.outcome == "invalid"),
        )
    if context.outcome not in {"verified", "unavailable"}:
        return failure("invalid", "unknown context outcome")
    if len(context.members) > 1:
        return failure("unavailable", "multiple-member inventory is unsupported")
    if (
        len(context.members) != 1
        or len(context.snapshots) != 1
        or len(context.captured_members) != 1
    ):
        return failure("unavailable", "exactly one selected and captured member is required")
    member = context.members[0]
    if context.captured_members[0] != member:
        return failure("invalid", "captured member identity differs from selection")
    checks = [c for c in context.checks if c.check == "member_capture" and c.package == member[0]]
    if len(checks) != 1 or checks[0].outcome != "verified":
        return failure("unavailable", "selected member lacks one successful capture check")
    snapshot = context.snapshots[0]
    if (
        _sha(snapshot.source_bytes) != snapshot.source_sha256
        or _sha(snapshot.ir_bytes) != snapshot.ir_sha256
    ):
        return failure("invalid", "captured source or IR digest mismatch")
    try:
        ir = json.loads(snapshot.ir_bytes)
        if (
            not isinstance(ir, dict)
            or tuple(ir.get(k) for k in ("id", "namespace", "version")) != member
        ):
            return failure("invalid", "captured IR identity differs from selection")
        refs: dict[str, int] = defaultdict(int)
        names: dict[str, set[str]] = defaultdict(set)
        for section in ("classes", "relations"):
            values = ir.get(section, [])
            if not isinstance(values, list):
                raise ValueError(f"IR {section} must be a list")
            for item in values:
                if (
                    not isinstance(item, dict)
                    or not isinstance(item.get("fqid"), str)
                    or not isinstance(item.get("id"), str)
                ):
                    continue
                ref = item["fqid"]
                refs[ref] += 1
                aliases = item.get("aliases", [])
                spellings = [item["id"], ref] + (
                    [v for v in aliases if isinstance(v, str)] if isinstance(aliases, list) else []
                )
                for name in spellings:
                    for key in symbol_keys(name):
                        names[key].add(ref)
        selected_root = (root / specs_root).resolve()
        if not selected_root.is_relative_to(root) or not selected_root.is_dir():
            return failure("invalid", "specs_root must be an existing directory inside workspace")
        selected = documents
        if selected is None:
            selected = tuple(
                (p.relative_to(root).as_posix(), p.read_bytes())
                for p in sorted(selected_root.glob("SG-SPEC-*.yaml"))
                if p.resolve().is_relative_to(selected_root) and p.is_file()
            )
            # Do not silently omit symlinks or other invalid entries.
            if len(selected) != len(list(selected_root.glob("SG-SPEC-*.yaml"))):
                return failure("invalid", "spec path escapes selected root or is not a file")
        entries = []
        inputs = []
        seen_paths: set[str] = set()
        seen_ids: set[str] = set()
        for name, raw in sorted(selected, key=lambda item: item[0]):
            path = Path(name)
            if (
                not isinstance(name, str)
                or not name
                or path.is_absolute()
                or ".." in path.parts
                or path.as_posix() != name
                or not isinstance(raw, bytes)
            ):
                raise ValueError(
                    "document must have a normalized workspace-relative path and bytes"
                )
            resolved = (root / path).resolve()
            if (
                not resolved.is_relative_to(selected_root)
                or not resolved.is_file()
                or path.name != resolved.name
            ):
                raise ValueError(f"spec path is not a regular file inside selected root: {name}")
            if name in seen_paths:
                raise ValueError(f"duplicate document path: {name}")
            seen_paths.add(name)
            text = raw.decode("utf-8")
            if any(isinstance(token, AliasToken) for token in yaml.scan(text)):
                raise ValueError(f"YAML aliases are unsupported for source locations: {name}")
            node = yaml.compose(text)
            if not isinstance(node, MappingNode):
                raise ValueError(f"spec is not a YAML mapping: {name}")
            spec_id, terms = _explicit(node)
            spec_id = spec_id or path.stem
            if spec_id in seen_ids:
                raise ValueError(f"duplicate spec identity: {spec_id}")
            seen_ids.add(spec_id)
            source_hash = _sha(raw)
            inputs.append({"path": name, "sha256": source_hash})
            for field, term_node in terms:
                term = term_node.value
                candidates = sorted(
                    set().union(*(names.get(key, set()) for key in symbol_keys(term)))
                )
                if ":" in term:
                    exact_count = refs.get(term, 0)
                    resolution = (
                        "structurally_resolved_candidate"
                        if exact_count == 1
                        else "ambiguous"
                        if exact_count > 1
                        else "unknown"
                    )
                    candidates = [term] if exact_count else []
                    classification = "missing_ontology_ref"
                else:
                    resolution = (
                        "spelling_candidate"
                        if len(candidates) == 1
                        else "ambiguous"
                        if candidates
                        else "unknown"
                    )
                    classification = "legacy_unknown_term"
                entry = {
                    "term": term,
                    "spec_id": spec_id,
                    "path": name,
                    "source": field,
                    "field_path": (
                        f"{field}[{json.dumps(term, ensure_ascii=False)}]"
                        if field == "specification.terminology"
                        else field
                    ),
                    "location": _position(term_node),
                    "source_sha256": source_hash,
                    "resolution": resolution,
                    "candidates": candidates,
                    "authority": "structural_advisory_only",
                }
                if resolution in {"unknown", "ambiguous"}:
                    entry.update(
                        {
                            "gap_id": f"ontology-gap-{spec_id.lower()}-{slug(term)}",
                            "classification": classification,
                        }
                    )
                entries.append(entry)
        return {
            "artifact_kind": "project_ontology_term_inventory",
            "schema_version": 1,
            "outcome": "analyzed",
            "diagnostics": [],
            "analysis_profile": PROFILE,
            "project_context": {
                "project_id": context.project_id,
                "workspace": str(root),
                "context_revision": context.revision,
                "context_outcome": context.outcome,
                "scope": "single_member_local_symbols",
                "verified_closure": False,
                "semantic_approval": "not_established",
                "selected_member": {"id": member[0], "namespace": member[1], "version": member[2]},
                "source_sha256": snapshot.source_sha256,
                "ir_sha256": snapshot.ir_sha256,
                "compiler_sha256": snapshot.compiler_sha256,
            },
            "inputs": {"specs_root": selected_root.relative_to(root).as_posix(), "specs": inputs},
            "entries": entries,
            "prose": "unassessed",
            "grounded": False,
            "full_spec_conformance": "not_assessed",
            "canonical_mutations_allowed": False,
        }
    except (OSError, ValueError, TypeError, yaml.YAMLError, UnicodeError) as error:
        return failure("invalid", f"cannot inventory inputs: {error}")
