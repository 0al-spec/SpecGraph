"""Run an explicit read-only ontology advisory check for one target spec."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from project_ontology_context import capture_project_context
from project_ontology_report_freshness import (
    FreshnessResult,
    assess_report_freshness,
    bind_report_bundle,
)
from project_ontology_term_inventory import build_term_inventory
from spec_ontology_context_reports import build_context_reports

_TARGET = re.compile(r"SG-SPEC-[0-9]{4}\Z")
_PRODUCER_FILES = (
    "spec_ontology_context_reports.py",
    "spec_ontology_binding_index.py",
    "spec_ontology_validation_report.py",
    "ontology_imports.py",
    "ontology_snapshot.py",
)


def _producer() -> tuple[str, dict[str, str]]:
    root = Path(__file__).resolve().parent
    hashes = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in _PRODUCER_FILES
    }
    encoded = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
    return "specgraph-local-symbol-advisory-v1:sha256:" + hashlib.sha256(
        encoded
    ).hexdigest(), hashes


def _previous(path: Path | None, root: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if path is None:
        return None, None
    try:
        selected = (root / path).resolve()
        if not selected.is_relative_to(root):
            return None, FreshnessResult("invalid", ("previous report escapes workspace",)).report()
        data = json.loads(selected.read_bytes())
        if (
            not isinstance(data, dict)
            or data.get("artifact_kind") != "project_ontology_target_check"
            or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1
        ):
            return None, FreshnessResult("invalid", ("previous report shape is invalid",)).report()
        return data, None
    except FileNotFoundError:
        return None, FreshnessResult("unavailable", ("previous report is unavailable",)).report()
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, FreshnessResult("invalid", (f"cannot read previous report: {error}",)).report()


def build_target_context_check(
    workspace_root: Path,
    *,
    project_id: str,
    target_spec_id: str,
    selection_path: Path | None,
    ontologyc: Path | None,
    compiler_sha256: str | None = None,
    previous_report_path: Path | None = None,
) -> dict[str, Any]:
    """Capture one context and one target; never mutate canonical data or approve terms."""
    root = Path(workspace_root).resolve()
    output: dict[str, Any] = {
        "artifact_kind": "project_ontology_target_check",
        "schema_version": 1,
        "project_id": project_id,
        "workspace": str(root),
        "target_spec_id": target_spec_id,
        "outcome": "unavailable",
        "diagnostics": [],
        "target": None,
        "context": None,
        "bundle": None,
        "inventory": None,
        "input_binding": None,
        "producer": None,
        "previous_freshness": None,
        "scope": "explicit_target_advisory_check",
        "semantic_approval": "not_established",
        "full_spec_conformance": "not_assessed",
        "canonical_mutations_allowed": False,
        "policy_activation_allowed": False,
    }
    if not isinstance(target_spec_id, str) or not _TARGET.fullmatch(target_spec_id):
        output.update(outcome="invalid", diagnostics=["target_spec_id must be SG-SPEC-NNNN"])
        return output
    specs_root = root / "specs" / "nodes"
    target = specs_root / f"{target_spec_id}.yaml"
    try:
        resolved = target.resolve()
        if (
            not specs_root.resolve().is_relative_to(root)
            or not resolved.is_relative_to(specs_root.resolve())
            or not resolved.is_file()
            or resolved.name != target.name
        ):
            raise ValueError("target is missing or escapes the workspace spec root")
        raw = resolved.read_bytes()
        doc = yaml.safe_load(raw)
        if not isinstance(doc, dict) or doc.get("id") != target_spec_id:
            raise ValueError("target YAML id does not match target_spec_id")
        relative = target.relative_to(root).as_posix()
        documents = ((relative, raw),)
        output["target"] = {
            "id": target_spec_id,
            "path": relative,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    except (OSError, ValueError, yaml.YAMLError, UnicodeError) as error:
        output.update(outcome="invalid", diagnostics=[f"target capture failed: {error}"])
        return output
    context = capture_project_context(
        root,
        project_id=project_id,
        selection_path=selection_path,
        ontologyc=ontologyc,
        compiler_sha256=compiler_sha256,
    )
    output["context"] = context.report()
    bundle = build_context_reports(
        context, workspace_root=root, specs_root=specs_root, documents=documents
    )
    inventory = build_term_inventory(
        context, workspace_root=root, specs_root=specs_root, documents=documents
    )
    output["bundle"] = bundle
    output["inventory"] = inventory
    output["outcome"] = (
        "invalid"
        if "invalid" in {context.outcome, bundle["outcome"], inventory["outcome"]}
        else "unavailable"
        if context.outcome != "verified"
        or bundle["outcome"] != "analyzed"
        or inventory["outcome"] != "analyzed"
        else "checked"
    )
    output["diagnostics"] = (
        [c.detail for c in context.checks if c.outcome != "verified"]
        + bundle["diagnostics"]
        + inventory["diagnostics"]
    )
    producer_identity = None
    if bundle["outcome"] == "analyzed":
        try:
            producer_identity, hashes = _producer()
            output["producer"] = {
                "identity": producer_identity,
                "source_sha256": hashes,
                "provenance": "caller_attributed_not_attested",
            }
            output["input_binding"] = bind_report_bundle(
                bundle, producer_identity=producer_identity
            ).report()
        except (OSError, ValueError, TypeError) as error:
            output["outcome"] = "unavailable" if output["outcome"] != "invalid" else "invalid"
            output["diagnostics"].append(f"cannot bind advisory producer inputs: {error}")
    previous, previous_failure = _previous(previous_report_path, root)
    if previous_failure is not None:
        output["previous_freshness"] = previous_failure
    elif previous is not None:
        if previous.get("target_spec_id") != target_spec_id:
            output["previous_freshness"] = FreshnessResult(
                "stale", ("previous target differs",)
            ).report()
        else:
            output["previous_freshness"] = assess_report_freshness(
                previous.get("bundle"),
                input_binding=previous.get("input_binding"),
                context=context,
                workspace_root=root,
                specs_root=specs_root,
                producer_identity=producer_identity,
                documents=documents,
            ).report()
    return output
