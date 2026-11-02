"""Bounded document-class check over independently captured metamodel bytes.

The caller must verify that the disposition is the trusted, source-bound human
decision. Its shape and digest here are not proof of authorship or approval.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
from typing import Any

import yaml

from ontology_snapshot import OntologySnapshotError, parse_ontology_ir
from project_ontology_context.capture import _load_yaml
from project_ontology_context.model import ContextResult
from project_ontology_context.vocabulary import capture_vocabulary

PROFILE = "specgraph-external-specification-artifact-v1"
PACKAGE = ("org.0al.specgraph.core", "sgcore", "0.1.0")
SOURCE_SHA256 = "5bfa2ff40b6174def589546ab2fea2501e1f256c4f1446f36c45c7f3fffcd929"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_digest(value: object) -> str:
    return _digest(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    )


def assess_metamodel(
    context: ContextResult | None,
    *,
    document: bytes,
    document_path: str,
    target_id: str,
    decision: dict[str, Any] | None,
    mapping: dict[str, Any] | None,
) -> dict[str, Any]:
    """Check one explicit class mapping; caller owns decision trust and path capture."""
    result: dict[str, Any] = {
        "check_scope": "specification_metamodel",
        "outcome": "unavailable",
        "diagnostics": [],
        "project_context": None,
        "analysis_profile": None,
        "summary": None,
    }

    def fail(outcome: str, detail: str) -> dict[str, Any]:
        result.update(outcome=outcome, diagnostics=[detail])
        return result

    try:
        path = PurePosixPath(document_path)
        if (
            not isinstance(document_path, str)
            or not document_path
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != document_path
            or not isinstance(document, bytes)
            or not isinstance(target_id, str)
            or not target_id
        ):
            raise ValueError("document identity or normalized workspace-relative path is invalid")
        payload = _load_yaml(document)
        if not isinstance(payload, dict) or payload.get("id") != target_id:
            raise ValueError("document id does not match target identity")
        if mapping is not None:
            if not isinstance(mapping, dict) or any(
                mapping.get(key) != value
                for key, value in (
                    ("profile", PROFILE),
                    ("document_kind", "spec"),
                    ("ontology_class", "sgcore:Spec"),
                )
            ):
                raise ValueError("explicit Spec mapping is malformed or unsupported")
            if payload.get("kind") != "spec":
                raise ValueError("mapped document kind differs from kind: spec")
            mapping_sha = _json_digest(mapping)
        else:
            mapping_sha = None
        if decision is not None:
            if not isinstance(decision, dict) or decision.get("profile") != PROFILE:
                raise ValueError("applicability disposition profile is invalid")
            decision_sha = _json_digest(decision)
        else:
            decision_sha = None
        if context is not None and context.outcome == "invalid":
            raise ValueError("metamodel context is invalid")
        if context is None or context.outcome != "verified":
            return fail("unavailable", "verified metamodel context is unavailable")
        if context.members != (PACKAGE,) or context.captured_members != (PACKAGE,):
            raise ValueError("selected metamodel package is not the pinned sgcore package")
        if len(context.snapshots) != 1:
            raise ValueError("metamodel snapshot count differs from selected package")
        snapshot = context.snapshots[0]
        if snapshot.source_sha256 != SOURCE_SHA256:
            raise ValueError("metamodel source pin differs from approved source")
        vocabulary = capture_vocabulary(context)
        ir = parse_ontology_ir(snapshot.ir_bytes)
        if not isinstance(ir, dict) or ir.get("sourceDigest") != "sha256:" + SOURCE_SHA256:
            raise ValueError("metamodel IR sourceDigest does not match source")
        if snapshot.compiler_source_digest != "sha256:" + SOURCE_SHA256:
            raise ValueError("compiler source digest does not match source")
        matches = [
            s for s in vocabulary.symbols if s.reference == "sgcore:Spec" and s.kind == "class"
        ]
        if len(matches) != 1:
            raise ValueError("metamodel does not export exactly one sgcore:Spec class")
        if mapping is None:
            return fail("unavailable", "explicit document class mapping is unavailable")
        if decision is None or decision.get("outcome") != "approved":
            return fail("unavailable", "applicability disposition is not approved")
        result.update(
            outcome="analyzed",
            project_context=vocabulary.metadata(context),
            analysis_profile=PROFILE,
            summary={
                "document": {"id": target_id, "path": document_path, "sha256": _digest(document)},
                "mapping_sha256": mapping_sha,
                "decision_sha256": decision_sha,
                "decision_provenance": "caller_attributed_not_attested",
                "class_check": {
                    "ontology_ref": "sgcore:Spec",
                    "source": "/kind",
                    "result": "matched",
                    "origin": matches[0].origin(),
                },
                "node_membership": "not_assessed",
                "lifecycle": "not_assessed",
                "semantic_approval": "not_established",
                "canonical_mutations_allowed": False,
            },
        )
        return result
    except OntologySnapshotError as error:
        return fail(error.outcome, str(error))
    except (TypeError, ValueError, UnicodeError, yaml.YAMLError) as error:
        return fail("invalid", str(error))
