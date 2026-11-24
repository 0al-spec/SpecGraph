"""Inventory explicit terms using captured ontology IR; prose is not assessed.

Profile specgraph-explicit-terms-v1 reads specification.terminology mapping keys,
root ontology_refs, and specification.ontology_refs lists. Locations are 1-based,
with end positions exclusive; offsets are Unicode character offsets.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from ontology_snapshot import OntologySnapshotError
from project_ontology_context import ContextResult
from project_ontology_context.vocabulary import capture_vocabulary
from project_ontology_term_declarations import (
    PROFILE,
    read_term_declarations,
    source_position,
    term_field_path,
)
from spec_ontology_binding_index import slug


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    try:
        vocabulary = capture_vocabulary(context)
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
                or (documents is None and not resolved.is_file())
                or (resolved.exists() and not resolved.is_file())
                or path.name != resolved.name
            ):
                raise ValueError(f"spec path is not a regular file inside selected root: {name}")
            if name in seen_paths:
                raise ValueError(f"duplicate document path: {name}")
            seen_paths.add(name)
            spec_id, terms = read_term_declarations(name, raw)
            if spec_id in seen_ids:
                raise ValueError(f"duplicate spec identity: {spec_id}")
            seen_ids.add(spec_id)
            source_hash = _sha(raw)
            inputs.append({"path": name, "sha256": source_hash})
            for field, term_node in terms:
                term = term_node.value
                matches = vocabulary.candidates(term)
                candidates = sorted({s.reference for s in matches})
                if ":" in term:
                    resolution = (
                        "structurally_resolved_candidate"
                        if len(matches) == 1
                        else "ambiguous"
                        if matches
                        else "unknown"
                    )
                    classification = "missing_ontology_ref"
                else:
                    resolution = (
                        "spelling_candidate"
                        if len(matches) == 1
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
                    "field_path": term_field_path(field, term),
                    "location": source_position(term_node),
                    "source_sha256": source_hash,
                    "resolution": resolution,
                    "candidates": candidates,
                    "candidate_origins": [s.origin() for s in matches],
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
            "project_context": vocabulary.metadata(context),
            "inputs": {"specs_root": selected_root.relative_to(root).as_posix(), "specs": inputs},
            "entries": entries,
            "prose": "unassessed",
            "grounded": False,
            "full_spec_conformance": "not_assessed",
            "canonical_mutations_allowed": False,
        }
    except OntologySnapshotError as error:
        return failure(error.outcome, str(error))
    except (OSError, ValueError, TypeError, yaml.YAMLError, UnicodeError) as error:
        return failure("invalid", f"cannot inventory inputs: {error}")
