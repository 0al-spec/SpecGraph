#!/usr/bin/env python3
"""Extract versioned SpecGraph Intent Atoms from an exact Git revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

PROFILE_FILE = Path(__file__).with_name("intent_atoms_profile.json")
ANALYZER_VERSION = "1.0.1"


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


def _profile_digest(profile: dict[str, Any]) -> str:
    canonical = json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalise_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _read_tree_documents(
    *, repo: str, commit: str, spec_root: str
) -> tuple[dict[str, bytes], list[dict[str, str]]]:
    try:
        root_type = _git(repo, "cat-file", "-t", f"{commit}:{spec_root}").decode().strip()
    except subprocess.CalledProcessError:
        return {}, [
            _diagnostic(
                "missing_spec_root",
                spec_root,
                "the selected revision does not contain this tracked specification directory",
            )
        ]
    if root_type != "tree":
        return {}, [
            _diagnostic(
                "invalid_spec_root",
                spec_root,
                f"the selected revision contains a {root_type}, not a directory, at this path",
            )
        ]

    listing = _git(
        repo,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        commit,
        "--",
        f":(literal){spec_root}",
    )
    documents: dict[str, bytes] = {}
    diagnostics: list[dict[str, str]] = []
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        header, separator, path_bytes = entry.partition(b"\t")
        if not separator:
            diagnostics.append(
                _diagnostic("invalid_tree_entry", spec_root, "could not parse a Git tree entry")
            )
            continue
        try:
            mode, object_type, object_id = header.decode("ascii").split(" ")
        except ValueError:
            diagnostics.append(
                _diagnostic("invalid_tree_entry", spec_root, "could not parse a Git tree entry")
            )
            continue
        path = path_bytes.decode("utf-8", errors="replace")
        if not path.endswith((".yaml", ".yml")):
            continue
        if object_type != "blob" or mode not in {"100644", "100755"}:
            diagnostics.append(
                _diagnostic(
                    "unsupported_yaml_entry",
                    path,
                    f"expected a regular tracked file, found mode {mode} and type {object_type}",
                )
            )
            continue
        documents[path] = _git(repo, "cat-file", "blob", object_id)
    return documents, diagnostics


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
        "text": _normalise_text(text),
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
) -> tuple[list[dict[str, Any]], list[dict[str, str]], str]:
    diagnostics: list[dict[str, str]] = []
    node_id, _kind, _status = _node_identity(document)
    if node_id is None:
        return (
            [],
            [_diagnostic("missing_node_id", path, "node has no non-empty stable id")],
            "invalid",
        )

    payload: dict[str, Any] = {}
    for envelope in ("spec", "specification"):
        if envelope not in document:
            continue
        value = document[envelope]
        if not isinstance(value, dict):
            diagnostics.append(
                _diagnostic(
                    "invalid_spec_envelope",
                    path,
                    f"{envelope} must be a mapping when present",
                )
            )
        elif not payload:
            payload = value
    try:
        explicit = _first_declared_field(document, payload, "atoms")
        acceptance = _first_declared_field(document, payload, "acceptance")
    except ValueError as exc:
        diagnostics.append(_diagnostic("ambiguous_field_declaration", path, str(exc)))
        return [], diagnostics, "ambiguous"
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
            elif atom_id is not None:
                seen_ids.add(atom_id)
            optional_strings: dict[str, str | None] = {}
            for attribute in ("type", "scope"):
                value = item.get(attribute)
                if value is None:
                    optional_strings[attribute] = None
                elif isinstance(value, str) and value.strip():
                    optional_strings[attribute] = value.strip()
                else:
                    diagnostics.append(
                        _diagnostic(
                            "invalid_intent_atom_attribute",
                            path,
                            f"{explicit[0]}.intents[{index}].{attribute} must be a "
                            "non-empty string",
                        )
                    )
                    optional_strings[attribute] = None
            optional_references: dict[str, list[str] | None] = {}
            for attribute in ("premises", "verifiable_by"):
                value = item.get(attribute)
                if value is None:
                    optional_references[attribute] = None
                elif isinstance(value, list) and all(
                    isinstance(reference, str) and reference.strip() for reference in value
                ):
                    optional_references[attribute] = [reference.strip() for reference in value]
                else:
                    diagnostics.append(
                        _diagnostic(
                            "invalid_intent_atom_attribute",
                            path,
                            f"{explicit[0]}.intents[{index}].{attribute} must be a list of "
                            "non-empty strings",
                        )
                    )
                    optional_references[attribute] = None
            atoms.append(
                _atom(
                    node_id=node_id,
                    path=path,
                    source_field=f"{explicit[0]}.intents",
                    index=index,
                    text=statement,
                    origin="explicit_intent",
                    atom_id=atom_id,
                    declared_type=optional_strings["type"],
                    scope=optional_strings["scope"],
                    premises=optional_references["premises"],
                    verifiable_by=optional_references["verifiable_by"],
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
    profile = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    if profile.get("profile_id") != "specgraph-intent-atoms-v1" or profile.get("version") != 1:
        raise ValueError("unsupported Intent Atoms profile")
    documents, tree_diagnostics = _read_tree_documents(
        repo=repo, commit=commit, spec_root=spec_root
    )
    relative_paths = sorted(documents)

    all_atoms: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = list(tree_diagnostics)
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
            "sha256": _profile_digest(profile),
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
