"""Build advisory reports from captured package vocabularies and one spec corpus."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from ontology_snapshot import OntologySnapshotError
from project_ontology_check_scopes import (
    CHECK_SCOPES,
    DEFAULT_SCOPES,
    SCOPED_ANALYSIS_PROFILE,
    SCOPED_SCHEMA_VERSION,
    ScopeFacts,
    normalize_requested_scopes,
)
from project_ontology_context import ContextResult
from project_ontology_context.vocabulary import capture_vocabulary
from project_ontology_scope_outcome_spec import REQUESTED_SCOPES_ANALYZED_SPEC
from spec_ontology_binding_index import build_binding_index, snapshot_evidence
from spec_ontology_validation_report import build_validation_report


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_context_reports(
    context: ContextResult,
    *,
    workspace_root: Path,
    specs_root: Path,
    documents: tuple[tuple[str, bytes], ...] | None = None,
    requested_scopes: tuple[str, ...] = DEFAULT_SCOPES,
) -> dict[str, Any]:
    """Analyze explicitly requested scopes; never reopen ontology inputs or fall back."""

    assessments: dict[str, dict[str, Any]] = {}
    bundle: dict[str, Any] = {
        "schema_version": SCOPED_SCHEMA_VERSION,
        "analysis_profile": SCOPED_ANALYSIS_PROFILE,
        "requested_scopes": [],
        "assessments": assessments,
        "outcome": "unavailable",
        "diagnostics": [],
        "inputs": None,
        "binding_index": None,
        "validation_report": None,
        "semantic_approval": "not_established",
        "full_spec_conformance": "not_assessed",
    }
    try:
        requested = normalize_requested_scopes(requested_scopes)
    except ValueError as error:
        bundle.update(outcome="invalid", diagnostics=[str(error)])
        return bundle
    bundle["requested_scopes"] = list(requested)
    for scope in CHECK_SCOPES:
        assessments[scope] = {
            "check_scope": scope,
            "outcome": "unavailable" if scope in requested else "not_requested",
            "diagnostics": [],
            "project_context": None,
            "analysis_profile": None,
            "summary": None,
        }
    if "specification_metamodel" in requested:
        assessments["specification_metamodel"]["diagnostics"] = [
            "Meta source, applicability profile and supported checking are not established."
        ]

    def finish() -> dict[str, Any]:
        outcomes = tuple(assessments[scope]["outcome"] for scope in requested)
        facts = ScopeFacts(requested, outcomes)
        bundle["outcome"] = (
            "invalid"
            if "invalid" in outcomes
            else "analyzed"
            if REQUESTED_SCOPES_ANALYZED_SPEC.is_satisfied_by(facts)
            else "unavailable"
        )
        bundle["diagnostics"] = [
            detail for scope in requested for detail in assessments[scope]["diagnostics"]
        ] or ([] if requested else ["No ontology check scope was requested."])
        return bundle

    def failure(outcome: str, detail: str) -> dict[str, Any]:
        assessments["domain_vocabulary"].update(outcome=outcome, diagnostics=[detail])
        return finish()

    # This slice cannot execute meta rules. No domain work is implied by a meta request.
    if "domain_vocabulary" not in requested:
        return finish()

    root = Path(workspace_root).resolve()
    if not root.is_dir() or root != Path(context.workspace).resolve():
        return failure("invalid", "workspace does not match captured project context")
    if context.outcome == "invalid":
        details = "; ".join(c.detail for c in context.checks if c.outcome == "invalid")
        return failure("invalid", f"invalid context: {details or 'no diagnostic supplied'}")
    if context.outcome not in {"verified", "unavailable"}:
        return failure("invalid", "unknown context outcome")
    try:
        vocabulary = capture_vocabulary(context)
        selected_root = (root / specs_root).resolve()
        if not selected_root.is_relative_to(root) or not selected_root.is_dir():
            return failure("invalid", "specs_root must be an existing directory inside workspace")
        parsed_documents: list[tuple[str, dict[str, Any]]] = []
        identities: list[dict[str, str]] = []
        spec_ids: set[str] = set()
        seen_paths: set[str] = set()
        selected = documents
        if selected is None:
            selected = tuple(
                (path.relative_to(root).as_posix(), path.read_bytes())
                for path in sorted(selected_root.glob("SG-SPEC-*.yaml"))
                if path.resolve().is_relative_to(selected_root) and path.is_file()
            )
            if len(selected) != len(list(selected_root.glob("SG-SPEC-*.yaml"))):
                return failure("invalid", "spec path escapes selected root or is not a file")
        for name, raw in sorted(selected, key=lambda item: item[0]):
            if not isinstance(name, str) or not name or not isinstance(raw, bytes):
                raise ValueError(
                    "document must have a normalized workspace-relative path and bytes"
                )
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or path.as_posix() != name:
                raise ValueError(
                    "document must have a normalized workspace-relative path and bytes"
                )
            resolved = (root / path).resolve()
            if not resolved.is_relative_to(selected_root):
                raise ValueError(f"spec path escapes selected root: {name}")
            if documents is None and (not resolved.is_file() or path.name != resolved.name):
                raise ValueError(f"spec path is not a regular file inside selected root: {name}")
            if name in seen_paths:
                raise ValueError(f"duplicate document path: {name}")
            seen_paths.add(name)
            document = yaml.safe_load(raw)
            if not isinstance(document, dict):
                return failure("invalid", f"spec is not a YAML mapping: {path.name}")
            spec_id = str(document.get("id", path.stem))
            if spec_id in spec_ids:
                return failure("invalid", f"duplicate spec identity: {spec_id}")
            spec_ids.add(spec_id)
            parsed_documents.append((name, document))
            identities.append({"path": name, "sha256": _sha256(raw)})
        inputs = {"specs_root": selected_root.relative_to(root).as_posix(), "specs": identities}
        metadata = vocabulary.metadata(context)
        index = build_binding_index(
            vocabulary=vocabulary,
            documents=tuple(parsed_documents),
            check_scope="domain_vocabulary",
        )
        report = build_validation_report(
            vocabulary=vocabulary, binding_index=index, check_scope="domain_vocabulary"
        )
        for result in (index, report):
            result["schema_version"] = SCOPED_SCHEMA_VERSION
            result["analysis_profile"] = SCOPED_ANALYSIS_PROFILE
            result["ontology_ir_ref"] = None
            result["project_context"] = dict(metadata)
            result["inputs"] = inputs
            if vocabulary.composed:
                result["ontology_verification"] = {
                    "status": "compiler_checked",
                    "scope": metadata["scope"],
                    "members": metadata["members"],
                    "foundation_catalog": metadata["foundation_catalog"],
                }
            else:
                result["ontology_verification"] = snapshot_evidence(context.snapshots[0])
        bundle.update(inputs=inputs, binding_index=index, validation_report=report)
        assessments["domain_vocabulary"].update(
            outcome="analyzed",
            project_context=metadata,
            analysis_profile=SCOPED_ANALYSIS_PROFILE,
            summary={"binding_index": index["summary"], "validation_report": report["summary"]},
        )
        return finish()
    except OntologySnapshotError as error:
        return failure(error.outcome, str(error))
    except (OSError, ValueError, yaml.YAMLError, UnicodeError) as error:
        return failure("invalid", f"cannot capture or analyze inputs: {error}")
