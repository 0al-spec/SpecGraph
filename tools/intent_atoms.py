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
ANALYZER_FILE = Path(__file__)
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
    blob_paths: list[tuple[str, str]] = []
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
        blob_paths.append((path, object_id))

    documents: dict[str, bytes] = {}
    if blob_paths:
        request = b"".join(object_id.encode("ascii") + b"\n" for _, object_id in blob_paths)
        output = subprocess.run(
            ["git", "-C", repo, "cat-file", "--batch"],
            input=request,
            check=True,
            capture_output=True,
        ).stdout
        offset = 0
        for path, object_id in blob_paths:
            header_end = output.find(b"\n", offset)
            if header_end < 0:
                raise ValueError("Git returned a truncated cat-file batch header")
            header = output[offset:header_end].split()
            if len(header) != 3 or header[0].decode("ascii") != object_id or header[1] != b"blob":
                raise ValueError("Git returned an unexpected cat-file batch header")
            try:
                size = int(header[2])
            except ValueError as exc:
                raise ValueError("Git returned an invalid cat-file blob size") from exc
            content_start = header_end + 1
            content_end = content_start + size
            if content_end >= len(output) or output[content_end : content_end + 1] != b"\n":
                raise ValueError("Git returned a truncated cat-file batch blob")
            documents[path] = output[content_start:content_end]
            offset = content_end + 1
    return documents, diagnostics


def _analyzer_digest() -> str:
    return hashlib.sha256(ANALYZER_FILE.read_bytes()).hexdigest()


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
        "analyzer_sha256": _analyzer_digest(),
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


def _snapshot_compatibility(snapshot: dict[str, Any]) -> tuple[Any, ...]:
    profile = snapshot.get("profile")
    profile = profile if isinstance(profile, dict) else {}
    return (
        profile.get("profile_id"),
        profile.get("version"),
        profile.get("sha256"),
        snapshot.get("analyzer_version"),
        snapshot.get("analyzer_sha256"),
        snapshot.get("spec_root"),
    )


def _explicit_atom_key(atom: dict[str, Any]) -> tuple[str, str, str] | None:
    atom_id = atom.get("atom_id")
    if atom.get("origin") != "explicit_intent" or not isinstance(atom_id, str) or not atom_id:
        return None
    return (str(atom.get("node_id", "")), "explicit_intent", atom_id)


def _text_atom_key(atom: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(atom.get("node_id", "")),
        str(atom.get("origin", "")),
        _normalise_text(str(atom.get("text", ""))),
    )


def _atom_sort_key(atom: dict[str, Any]) -> tuple[str, str, int, str]:
    return (
        str(atom.get("node_id", "")),
        str(atom.get("source_path", "")),
        int(atom.get("element_index", 0)),
        str(atom.get("text", "")),
    )


def _node_modes(snapshot: dict[str, Any]) -> dict[str, str]:
    return {
        str(item["node_id"]): str(item["mode"])
        for item in snapshot.get("nodes", [])
        if isinstance(item, dict) and item.get("node_id") and item.get("mode")
    }


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare two compatible snapshots without guessing cross-node identity."""
    if _snapshot_compatibility(before) != _snapshot_compatibility(after):
        raise ValueError("snapshots use different profile, analyzer, or spec-root contracts")

    before_atoms = [item for item in before.get("atoms", []) if isinstance(item, dict)]
    after_atoms = [item for item in after.get("atoms", []) if isinstance(item, dict)]
    before_explicit = {
        key: atom for atom in before_atoms if (key := _explicit_atom_key(atom)) is not None
    }
    after_explicit = {
        key: atom for atom in after_atoms if (key := _explicit_atom_key(atom)) is not None
    }

    added: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []
    matched_explicit = set(before_explicit) & set(after_explicit)
    for key in sorted(matched_explicit):
        old_atom = before_explicit[key]
        new_atom = after_explicit[key]
        if old_atom.get("text") != new_atom.get("text"):
            modified.append(
                {
                    "node_id": key[0],
                    "atom_id": key[2],
                    "before": {
                        "text": old_atom.get("text"),
                        "source_path": old_atom.get("source_path"),
                        "source_field": old_atom.get("source_field"),
                    },
                    "after": {
                        "text": new_atom.get("text"),
                        "source_path": new_atom.get("source_path"),
                        "source_field": new_atom.get("source_field"),
                    },
                }
            )
    for key in sorted(set(before_explicit) - matched_explicit):
        removed.append(before_explicit[key])
    for key in sorted(set(after_explicit) - matched_explicit):
        added.append(after_explicit[key])

    before_text_counts: Counter[tuple[str, str, str]] = Counter()
    after_text_counts: Counter[tuple[str, str, str]] = Counter()
    before_text_records: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    after_text_records: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for atom in before_atoms:
        if _explicit_atom_key(atom) is None:
            key = _text_atom_key(atom)
            before_text_counts[key] += 1
            before_text_records.setdefault(key, []).append(atom)
    for atom in after_atoms:
        if _explicit_atom_key(atom) is None:
            key = _text_atom_key(atom)
            after_text_counts[key] += 1
            after_text_records.setdefault(key, []).append(atom)

    for key in sorted(set(before_text_counts) | set(after_text_counts)):
        removed_count = max(0, before_text_counts[key] - after_text_counts[key])
        added_count = max(0, after_text_counts[key] - before_text_counts[key])
        removed.extend(sorted(before_text_records.get(key, []), key=_atom_sort_key)[:removed_count])
        added.extend(sorted(after_text_records.get(key, []), key=_atom_sort_key)[:added_count])

    added.sort(key=_atom_sort_key)
    removed.sort(key=_atom_sort_key)
    modified.sort(key=lambda item: (item["node_id"], item["atom_id"]))
    is_complete = (
        before.get("completeness") == "complete" and after.get("completeness") == "complete"
    )
    before_count = len(before_atoms)
    after_count = len(after_atoms)
    before_modes = _node_modes(before)
    after_modes = _node_modes(after)
    mode_transitions = [
        {"node_id": node_id, "before": before_modes[node_id], "after": after_modes[node_id]}
        for node_id in sorted(set(before_modes) & set(after_modes))
        if before_modes[node_id] != after_modes[node_id]
    ]
    return {
        "artifact_kind": "specgraph_intent_atoms_diff",
        "schema_version": 1,
        "profile": before.get("profile"),
        "analyzer_version": before.get("analyzer_version"),
        "analyzer_sha256": before.get("analyzer_sha256"),
        "spec_root": before.get("spec_root"),
        "before_commit_sha": before.get("commit_sha"),
        "after_commit_sha": after.get("commit_sha"),
        "completeness": "complete" if is_complete else "incomplete",
        "summary": {
            "counts_are_partial": not is_complete,
            "before_atom_count": before_count,
            "after_atom_count": after_count,
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "unchanged_count": before_count - len(removed) - len(modified),
            "net_count_delta": after_count - before_count,
        },
        "added": added,
        "removed": removed,
        "modified": modified,
        "diagnostics": {
            "before": before.get("diagnostics", []),
            "after": after.get("diagnostics", []),
            "mode_transitions": mode_transitions,
        },
    }


def _first_parent_revisions(repo: str, revision: str, count: int) -> tuple[str, list[str]]:
    tip = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip()
    output = _git(repo, "rev-list", "--first-parent", f"--max-count={count}", tip)
    commits = [item for item in output.decode().splitlines() if item]
    commits.reverse()
    return tip, commits


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_replay(
    *, repo: str, revision: str, count: int, output_dir: str | Path, spec_root: str = "specs/nodes"
) -> dict[str, Any]:
    """Write snapshots and adjacent diffs for a pinned first-parent history window."""
    if count < 1:
        raise ValueError("replay count must be at least 1")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError("replay output directory must be empty")

    tip, commits = _first_parent_revisions(repo, revision, count)
    snapshots: list[dict[str, Any]] = []
    snapshot_files: list[str] = []
    for commit in commits:
        snapshot = build_snapshot(repo=repo, revision=commit, spec_root=spec_root)
        filename = f"snapshot-{commit}.json"
        _write_json(destination / filename, snapshot)
        snapshots.append(snapshot)
        snapshot_files.append(filename)

    diff_files: list[str] = []
    diffs: list[dict[str, Any]] = []
    for before, after in zip(snapshots, snapshots[1:], strict=False):
        diff = diff_snapshots(before, after)
        filename = f"diff-{before['commit_sha']}-{after['commit_sha']}.json"
        _write_json(destination / filename, diff)
        diffs.append(diff)
        diff_files.append(filename)

    manifest = {
        "artifact_kind": "specgraph_intent_atoms_replay_manifest",
        "schema_version": 1,
        "selection": {
            "tip_revision": revision,
            "tip_commit_sha": tip,
            "first_parent": True,
            "requested_count": count,
            "actual_count": len(commits),
            "commit_shas_oldest_to_newest": commits,
        },
        "profile": snapshots[-1]["profile"] if snapshots else None,
        "analyzer_version": ANALYZER_VERSION,
        "analyzer_sha256": _analyzer_digest(),
        "spec_root": spec_root,
        "completeness": "complete"
        if all(item["completeness"] == "complete" for item in snapshots)
        else "incomplete",
        "snapshot_files": snapshot_files,
        "diff_files": diff_files,
        "summary": {
            "snapshot_count": len(snapshots),
            "diff_count": len(diffs),
            "incomplete_snapshot_count": sum(
                item["completeness"] != "complete" for item in snapshots
            ),
            "net_atom_count_delta": (
                snapshots[-1]["summary"]["atom_count"] - snapshots[0]["summary"]["atom_count"]
                if snapshots and all(item["completeness"] == "complete" for item in snapshots)
                else None
            ),
            "added_count_total": sum(item["summary"]["added_count"] for item in diffs),
            "removed_count_total": sum(item["summary"]["removed_count"] for item in diffs),
            "modified_count_total": sum(item["summary"]["modified_count"] for item in diffs),
            "source_mode_transition_count": sum(
                len(item["diagnostics"]["mode_transitions"]) for item in diffs
            ),
        },
    }
    _write_json(destination / "manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot = subparsers.add_parser("snapshot", help="snapshot atoms from an exact Git revision")
    snapshot.add_argument("--repo", required=True, help="path to a Git repository")
    snapshot.add_argument("--revision", required=True, help="commit, tag, or ref to inspect")
    snapshot.add_argument("--spec-root", default="specs/nodes")
    snapshot.add_argument("--output", help="write JSON here; stdout when omitted")
    diff = subparsers.add_parser("diff", help="compare two exact Git revisions")
    diff.add_argument("--repo", required=True)
    diff.add_argument("--base", required=True)
    diff.add_argument("--head", required=True)
    diff.add_argument("--spec-root", default="specs/nodes")
    diff.add_argument("--output", help="write JSON here; stdout when omitted")
    replay = subparsers.add_parser("replay", help="replay a first-parent history window")
    replay.add_argument("--repo", required=True)
    replay.add_argument("--revision", default="main")
    replay.add_argument("--count", type=int, default=30)
    replay.add_argument("--spec-root", default="specs/nodes")
    replay.add_argument("--output-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "snapshot":
            report = build_snapshot(
                repo=args.repo, revision=args.revision, spec_root=args.spec_root
            )
        elif args.command == "diff":
            before = build_snapshot(repo=args.repo, revision=args.base, spec_root=args.spec_root)
            after = build_snapshot(repo=args.repo, revision=args.head, spec_root=args.spec_root)
            report = diff_snapshots(before, after)
        else:
            report = build_replay(
                repo=args.repo,
                revision=args.revision,
                count=args.count,
                output_dir=args.output_dir,
                spec_root=args.spec_root,
            )
        encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        output_path = getattr(args, "output", None)
        if output_path:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(encoded, encoding="utf-8")
        elif args.command == "replay":
            sys.stdout.write(encoded)
        else:
            sys.stdout.write(encoded)
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"intent-atoms: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
