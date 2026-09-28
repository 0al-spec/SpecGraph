#!/usr/bin/env python3
"""Extract versioned SpecGraph Intent Atoms from an exact Git revision."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

PROFILE_FILE = Path(__file__).with_name("intent_atoms_profile.json")
ANALYZER_VERSION = "1.0.0"


def _git(repo: str, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", repo, *args],
        check=True,
        capture_output=True,
    ).stdout


def _valid_spec_root(spec_root: str) -> str:
    path = PurePosixPath(spec_root)
    if path.is_absolute() or not path.parts or ".." in path.parts or "." in path.parts:
        raise ValueError("spec root must be a repository-relative path without traversal")
    return path.as_posix().rstrip("/")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _node_identity(document: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    metadata = _mapping(document.get("metadata"))
    node_id = metadata.get("id", document.get("id"))
    kind = metadata.get("type", document.get("kind"))
    status = metadata.get("status", document.get("status"))
    return (
        node_id.strip() if isinstance(node_id, str) and node_id.strip() else None,
        kind.strip() if isinstance(kind, str) and kind.strip() else None,
        status.strip() if isinstance(status, str) and status.strip() else None,
    )


def _diagnostic(code: str, path: str, message: str, *, severity: str = "error") -> dict[str, str]:
    return {"code": code, "path": path, "severity": severity, "message": message}


def _atom(
    *,
    node_id: str,
    path: str,
    source_field: str,
    index: int,
    text: str,
    origin: str,
    atom_id: str | None = None,
    declared_type: str | None = None,
    scope: str | None = None,
    premises: Any = None,
    verifiable_by: Any = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "node_id": node_id,
        "source_path": path,
        "source_field": source_field,
        "element_index": index,
        "text": text.strip(),
        "origin": origin,
        "atom_id": atom_id,
    }
    if declared_type is not None:
        result["declared_type"] = declared_type
    if scope is not None:
        result["scope"] = scope
    if premises is not None:
        result["premises"] = premises
    if verifiable_by is not None:
        result["verifiable_by"] = verifiable_by
    return result


def _first_declared_field(
    document: dict[str, Any], spec: dict[str, Any], field: str
) -> tuple[str, Any] | None:
    candidates = []
    if field in document:
        candidates.append((field, document[field]))
    if field in spec:
        candidates.append((f"spec.{field}", spec[field]))
    if len(candidates) > 1:
        raise ValueError(f"field {field!r} is declared in both node and spec payload")
    return candidates[0] if candidates else None


def _extract_node(
    *, document: dict[str, Any], path: str
) -> tuple[list[dict[str, Any]], list[dict[str, str]], str | None]:
    diagnostics: list[dict[str, str]] = []
    node_id, _kind, _status = _node_identity(document)
    if node_id is None:
        return [], [_diagnostic("missing_node_id", path, "node has no non-empty stable id")], None

    payload = _mapping(document.get("spec"))
    if not payload:
        payload = _mapping(document.get("specification"))
    explicit = _first_declared_field(document, payload, "atoms")
    acceptance = _first_declared_field(document, payload, "acceptance")
    atoms: list[dict[str, Any]] = []
    origin_mode = "absent"

    if explicit is not None:
        atoms_value = explicit[1]
        if not isinstance(atoms_value, dict) or "intents" not in atoms_value:
            diagnostics.append(
                _diagnostic("invalid_explicit_atoms", path, f"{explicit[0]} must contain intents[]")
            )
            return atoms, diagnostics, "explicit_intents"
        intents = atoms_value["intents"]
        if not isinstance(intents, list):
            diagnostics.append(
                _diagnostic("invalid_explicit_atoms", path, f"{explicit[0]}.intents must be a list")
            )
            return atoms, diagnostics, "explicit_intents"
        origin_mode = "explicit_intents"
        seen_ids: set[str] = set()
        for index, item in enumerate(intents):
            if not isinstance(item, dict):
                diagnostics.append(
                    _diagnostic(
                        "invalid_intent_atom",
                        path,
                        f"{explicit[0]}.intents[{index}] must be an object",
                    )
                )
                continue
            statement = item.get("statement")
            if not isinstance(statement, str) or not statement.strip():
                diagnostics.append(
                    _diagnostic(
                        "invalid_intent_atom",
                        path,
                        f"{explicit[0]}.intents[{index}].statement must be a non-empty string",
                    )
                )
                continue
            raw_id = item.get("id")
            atom_id = raw_id.strip() if isinstance(raw_id, str) and raw_id.strip() else None
            if raw_id is not None and atom_id is None:
                diagnostics.append(
                    _diagnostic(
                        "invalid_intent_atom",
                        path,
                        f"{explicit[0]}.intents[{index}].id must be non-empty",
                    )
                )
                continue
            if atom_id is not None and atom_id in seen_ids:
                diagnostics.append(
                    _diagnostic(
                        "duplicate_atom_id", path, f"duplicate explicit atom id {atom_id!r}"
                    )
                )
                continue
            if atom_id is not None:
                seen_ids.add(atom_id)
            declared_type = item.get("type")
            scope = item.get("scope")
            atoms.append(
                _atom(
                    node_id=node_id,
                    path=path,
                    source_field=f"{explicit[0]}.intents",
                    index=index,
                    text=statement,
                    origin="explicit_intent",
                    atom_id=atom_id,
                    declared_type=declared_type if isinstance(declared_type, str) else None,
                    scope=scope if isinstance(scope, str) else None,
                    premises=item.get("premises"),
                    verifiable_by=item.get("verifiable_by"),
                )
            )
        if acceptance is not None:
            diagnostics.append(
                _diagnostic(
                    "acceptance_not_counted",
                    path,
                    "explicit atoms take precedence; acceptance items remain non-counted context",
                    severity="info",
                )
            )
        return atoms, diagnostics, origin_mode

    if acceptance is None:
        return atoms, diagnostics, origin_mode
    values = acceptance[1]
    if not isinstance(values, list):
        diagnostics.append(
            _diagnostic("invalid_acceptance", path, f"{acceptance[0]} must be a list of strings")
        )
        return atoms, diagnostics, "acceptance"

    origin_mode = "acceptance"
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            diagnostics.append(
                _diagnostic(
                    "invalid_acceptance_item",
                    path,
                    f"{acceptance[0]}[{index}] must be a non-empty string",
                )
            )
            continue
        atoms.append(
            _atom(
                node_id=node_id,
                path=path,
                source_field=acceptance[0],
                index=index,
                text=value,
                origin="acceptance_criterion",
            )
        )
    return atoms, diagnostics, origin_mode


def build_snapshot(*, repo: str, revision: str, spec_root: str = "specs/nodes") -> dict[str, Any]:
    """Build a deterministic snapshot by reading tracked YAML at a Git commit."""
    spec_root = _valid_spec_root(spec_root)
    commit = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip()
    # Pin the profile to this analyzer checkout so older commits can be replayed
    # without requiring them to contain this tool or its profile.
    profile_bytes = PROFILE_FILE.read_bytes()
    profile = json.loads(profile_bytes)
    if profile.get("profile_id") != "specgraph-intent-atoms-v1" or profile.get("version") != 1:
        raise ValueError("unsupported Intent Atoms profile")
    archive = _git(repo, "archive", "--format=tar", commit, spec_root)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        yaml_members = [
            member
            for member in bundle.getmembers()
            if member.isfile() and member.name.endswith((".yaml", ".yml"))
        ]
        documents = {
            member.name: bundle.extractfile(member).read()
            for member in yaml_members
            if bundle.extractfile(member) is not None
        }
    relative_paths = sorted(documents)

    all_atoms: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    seen_nodes: set[str] = set()
    node_records: list[dict[str, Any]] = []
    modes: Counter[str] = Counter()
    for path in relative_paths:
        try:
            raw = documents[path]
            document = yaml.safe_load(raw.decode("utf-8"))
        except (subprocess.CalledProcessError, UnicodeDecodeError, yaml.YAMLError) as exc:
            diagnostics.append(_diagnostic("unreadable_yaml", path, str(exc).splitlines()[0]))
            continue
        if not isinstance(document, dict):
            diagnostics.append(
                _diagnostic("invalid_node_document", path, "YAML document must be a mapping")
            )
            continue
        node_id, kind, status = _node_identity(document)
        atoms, node_diagnostics, mode = _extract_node(document=document, path=path)
        diagnostics.extend(node_diagnostics)
        if node_id is not None and node_id in seen_nodes:
            diagnostics.append(
                _diagnostic("duplicate_node_id", path, f"duplicate node id {node_id!r}")
            )
        elif node_id is not None:
            seen_nodes.add(node_id)
        if node_id is not None:
            modes[mode] += 1
            provenance = _mapping(document.get("provenance"))
            authority = provenance.get("authority")
            authored_by = provenance.get("authoredBy", provenance.get("authored_by"))
            node_records.append(
                {
                    "node_id": node_id,
                    "source_path": path,
                    "kind": kind,
                    "status": status,
                    "provenance": {
                        "authority": authority if isinstance(authority, str) else None,
                        "authored_by": authored_by if isinstance(authored_by, str) else None,
                    },
                    "atom_count": len(atoms),
                    "mode": mode,
                }
            )
        all_atoms.extend(atoms)

    diagnostics.sort(key=lambda item: (item["path"], item["code"], item["message"]))
    node_records.sort(key=lambda item: (item["node_id"], item["source_path"]))
    all_atoms.sort(
        key=lambda item: (
            item["node_id"],
            item["source_path"],
            item["source_field"],
            item["element_index"],
        )
    )
    return {
        "artifact_kind": "specgraph_intent_atoms_snapshot",
        "schema_version": 1,
        "profile": {
            "profile_id": profile["profile_id"],
            "version": profile["version"],
            "sha256": hashlib.sha256(profile_bytes).hexdigest(),
        },
        "analyzer_version": ANALYZER_VERSION,
        "commit_sha": commit,
        "spec_root": spec_root,
        "completeness": (
            "incomplete" if any(item["severity"] == "error" for item in diagnostics) else "complete"
        ),
        "summary": {
            "scanned_yaml_file_count": len(relative_paths),
            "node_count": len(node_records),
            "atom_count": len(all_atoms),
            "node_count_by_mode": dict(sorted(modes.items())),
            "atom_count_by_origin": dict(
                sorted(Counter(atom["origin"] for atom in all_atoms).items())
            ),
            "diagnostic_count": len(diagnostics),
        },
        "nodes": node_records,
        "atoms": all_atoms,
        "diagnostics": diagnostics,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot = subparsers.add_parser("snapshot", help="snapshot atoms from an exact Git revision")
    snapshot.add_argument("--repo", required=True, help="path to a Git repository")
    snapshot.add_argument("--revision", required=True, help="commit, tag, or ref to inspect")
    snapshot.add_argument("--spec-root", default="specs/nodes")
    snapshot.add_argument("--output", help="write JSON here; stdout when omitted")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = build_snapshot(repo=args.repo, revision=args.revision, spec_root=args.spec_root)
        encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            with open(args.output, "w", encoding="utf-8") as output:
                output.write(encoded)
        else:
            sys.stdout.write(encoded)
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"intent-atoms: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
