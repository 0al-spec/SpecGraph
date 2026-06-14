#!/usr/bin/env python3
"""Build read-only SpecGraph ontology import surfaces for proposal 0060."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "tools" / "ontology_import_policy.json"
SEMANTIC_CONTROL_POLICY_PATH = Path("tools") / "ontology_semantic_control_policy.json"
DEFAULT_SEMANTIC_POLICY = object()
CONCEPT_REF_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*:[A-Za-z][A-Za-z0-9_]*$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

REF_CATEGORIES = {
    "classes": "class",
    "relations": "relation",
    "policies": "policy",
    "stateMachines": "state_machine",
    "protocols": "protocol",
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(rendered, encoding="utf-8")
    return path


def relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"external:{resolved.name}"


def symbol_slug(ref: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", ref.lower()).strip("-")


def ontology_ref_map(ir: dict[str, Any]) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for section, kind in REF_CATEGORIES.items():
        values = ir.get(section, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            fqid = item.get("fqid")
            if not isinstance(fqid, str) or ":" not in fqid:
                continue
            refs[fqid] = {
                "ref": fqid,
                "kind": kind,
                "id": item.get("id"),
                "uri": item.get("uri"),
            }
    return refs


def required_package_fields(policy: dict[str, Any]) -> set[str]:
    contract = policy.get("package_ref_contract")
    if not isinstance(contract, dict):
        raise ValueError("policy.package_ref_contract must be an object")
    fields = contract.get("required_fields")
    if not isinstance(fields, list) or not all(isinstance(item, str) for item in fields):
        raise ValueError("policy.package_ref_contract.required_fields must be a list of strings")
    return set(fields)


def require_object(mapping: dict[str, Any], field: str, context: str) -> dict[str, Any]:
    value = mapping.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"{context}.{field} must be an object")
    return value


def require_string(mapping: dict[str, Any], field: str, context: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}.{field} must be a non-empty string")
    return value


def validate_concept_ref(ref: str, context: str) -> None:
    if not CONCEPT_REF_PATTERN.fullmatch(ref):
        raise ValueError(f"{context} must match <namespace>:<symbol>")


def validate_fixture(policy: dict[str, Any], fixture: dict[str, Any]) -> None:
    require_string(fixture, "proposal_id", "fixture")
    package = require_object(fixture, "package", "fixture")
    missing = sorted(required_package_fields(policy) - set(package))
    if missing:
        raise ValueError(f"fixture.package missing required fields: {', '.join(missing)}")
    for field in sorted(required_package_fields(policy)):
        require_string(package, field, "fixture.package")
    binding = require_object(fixture, "binding", "fixture")
    subject = require_object(binding, "subject", "fixture.binding")
    require_string(subject, "id", "fixture.binding.subject")
    require_string(subject, "kind", "fixture.binding.subject")
    refs = binding.get("refs")
    if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
        raise ValueError("fixture.binding.refs must be a list of strings")
    for index, ref in enumerate(refs):
        validate_concept_ref(ref, f"fixture.binding.refs[{index}]")


def resolve_fixture_file(fixture_path: Path, relative: str, context: str) -> Path:
    relative_path_value = Path(relative)
    if relative_path_value.is_absolute() or ".." in relative_path_value.parts:
        raise ValueError(f"{context} must stay within the fixture directory")
    fixture_dir = fixture_path.parent.resolve()
    candidate = (fixture_dir / relative_path_value).resolve()
    if not candidate.is_relative_to(fixture_dir):
        raise ValueError(f"{context} must stay within the fixture directory")
    return candidate


def validate_ir_metadata(ir: dict[str, Any], package: dict[str, Any]) -> None:
    expected = {
        "id": package["package_id"],
        "namespace": package["namespace"],
        "version": package["version"],
        "sourceDigest": package["digest"],
    }
    mismatches = []
    for field, expected_value in expected.items():
        actual_value = ir.get(field)
        if actual_value != expected_value:
            mismatches.append(f"{field} expected {expected_value!r}, got {actual_value!r}")
    if mismatches:
        raise ValueError(f"normalized IR metadata mismatch: {'; '.join(mismatches)}")


def governance_evidence_for(package_ref: str, governance: Any) -> list[dict[str, Any]]:
    if not isinstance(governance, dict):
        return []
    evidence_refs = {
        key: value
        for key, value in sorted(governance.items())
        if (key.endswith("_ref") or key.endswith("_refs")) and value
    }
    if not evidence_refs:
        return []
    return [
        {
            "package_ref": package_ref,
            "lifecycle_state": governance.get("lifecycle_state", "unknown"),
            **evidence_refs,
        }
    ]


def allowed_output_roots(policy: dict[str, Any]) -> list[Path]:
    contract = policy.get("derived_output_contract")
    if not isinstance(contract, dict):
        raise ValueError("policy.derived_output_contract must be an object")
    raw_roots = contract.get("allowed_output_roots")
    if not isinstance(raw_roots, list) or not all(isinstance(item, str) for item in raw_roots):
        raise ValueError(
            "policy.derived_output_contract.allowed_output_roots must be a list of strings"
        )
    roots = []
    for raw_root in raw_roots:
        root = Path(raw_root)
        if root.is_absolute() or ".." in root.parts:
            raise ValueError(
                "policy.derived_output_contract.allowed_output_roots must be relative paths"
            )
        roots.append(root)
    return roots


def resolve_allowed_output_path(out_dir: Path, relative: str, allowed_roots: list[Path]) -> Path:
    relative_path_value = Path(relative)
    if relative_path_value.is_absolute() or ".." in relative_path_value.parts:
        raise ValueError(f"output path {relative!r} must be relative and stay within allowed roots")
    if not any(
        relative_path_value == root or relative_path_value.is_relative_to(root)
        for root in allowed_roots
    ):
        allowed = ", ".join(root.as_posix() for root in allowed_roots)
        raise ValueError(f"output path {relative!r} is outside allowed output roots: {allowed}")
    output_root = out_dir.resolve()
    path = (output_root / relative_path_value).resolve()
    if not path.is_relative_to(output_root):
        raise ValueError(f"output path {relative!r} must stay within the output directory")
    return path


def require_layout_path(layout: dict[str, Any], key: str) -> str:
    value = layout.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"policy.repository_layout.{key} must be a non-empty string")
    return value


def require_surface_output_artifact(surface: dict[str, Any], key: str) -> str:
    value = surface.get("output_artifact")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}.output_artifact must be a non-empty string")
    return value


def optional_string(mapping: dict[str, Any], field: str, context: str) -> str:
    if field not in mapping or mapping[field] is None:
        return ""
    value = mapping[field]
    if not isinstance(value, str):
        raise ValueError(f"{context}.{field} must be a string when provided")
    return value.strip()


def require_bool(mapping: dict[str, Any], field: str, context: str) -> bool:
    value = mapping.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"{context}.{field} must be a boolean")
    return value


def require_int(mapping: dict[str, Any], field: str, context: str) -> int:
    value = mapping.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{context}.{field} must be an integer")
    return value


def require_string_list(mapping: dict[str, Any], field: str, context: str) -> list[str]:
    value = mapping.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{context}.{field} must be a list of strings")
    return value


def require_digest(value: str, context: str) -> None:
    if not DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{context} must be a sha256:<64 lowercase hex> digest")


def normalize_term(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("_", " "))


def ontologyc_adapter_report_contract(policy: dict[str, Any]) -> dict[str, Any]:
    contract = policy.get("ontologyc_adapter_report_contract")
    if not isinstance(contract, dict):
        raise ValueError("policy.ontologyc_adapter_report_contract must be an object")
    return contract


def resolve_report_file(report_path: Path, relative: str, context: str) -> Path:
    return resolve_fixture_file(report_path, relative, context)


def output_ref_entries(payload: dict[str, Any], context: str) -> dict[str, dict[str, Any]]:
    spec = require_object(payload, "spec", context)
    refs = spec.get("refs")
    if not isinstance(refs, list):
        raise ValueError(f"{context}.spec.refs must be a list")
    entries = {}
    for index, item in enumerate(refs):
        if not isinstance(item, dict):
            raise ValueError(f"{context}.spec.refs[{index}] must be an object")
        alias = require_string(item, "alias", f"{context}.spec.refs[{index}]")
        if alias in entries:
            raise ValueError(f"{context}.spec.refs[{index}].alias duplicates {alias!r}")
        entries[alias] = item
    return entries


def ontologyc_ref_kind(section: str, item: dict[str, Any]) -> str:
    if section == "classes":
        value = item.get("kind")
        return value if isinstance(value, str) and value.strip() else "Class"
    return {
        "relations": "Relation",
        "policies": "Policy",
        "stateMachines": "StateMachine",
        "protocols": "Protocol",
    }.get(section, "Concept")


def ontologyc_output_ref_map(ir: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ontology_id = require_string(ir, "id", "normalized_ir")
    namespace = require_string(ir, "namespace", "normalized_ir")
    version = require_string(ir, "version", "normalized_ir")
    refs: dict[str, dict[str, Any]] = {}
    for section in REF_CATEGORIES:
        values = ir.get(section, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            alias = item.get("fqid")
            if not isinstance(alias, str) or not alias:
                continue
            refs[alias] = {
                "concept": item.get("id"),
                "kindOfConcept": ontologyc_ref_kind(section, item),
                "namespace": namespace,
                "ontology": ontology_id,
                "uri": item.get("uri"),
                "version": version,
            }
    return refs


def output_gap_refs(payload: dict[str, Any], context: str) -> list[str]:
    spec = require_object(payload, "spec", context)
    gaps = spec.get("gaps")
    if not isinstance(gaps, list):
        raise ValueError(f"{context}.spec.gaps must be a list")
    missing_refs = []
    for index, item in enumerate(gaps):
        if not isinstance(item, dict):
            raise ValueError(f"{context}.spec.gaps[{index}] must be an object")
        gap_spec = require_object(item, "spec", f"{context}.spec.gaps[{index}]")
        missing_refs.append(
            require_string(gap_spec, "missingConcept", f"{context}.spec.gaps[{index}].spec")
        )
    return missing_refs


def validate_ontology_lock_output(payload: dict[str, Any], package: dict[str, Any]) -> None:
    if require_string(payload, "kind", "ontology_lock_output") != "OntologyLockfile":
        raise ValueError("ontology_lock_output.kind must be OntologyLockfile")
    spec = require_object(payload, "spec", "ontology_lock_output")
    resolved = spec.get("resolved")
    if not isinstance(resolved, list) or not resolved:
        raise ValueError("ontology_lock_output.spec.resolved must be a non-empty list")
    first = resolved[0]
    if not isinstance(first, dict):
        raise ValueError("ontology_lock_output.spec.resolved[0] must be an object")
    expected = {
        "ontology": package["package_id"],
        "namespace": package["namespace"],
        "version": package["version"],
        "digest": package["digest"],
    }
    mismatches = [
        f"{field} expected {expected_value!r}, got {first.get(field)!r}"
        for field, expected_value in expected.items()
        if first.get(field) != expected_value
    ]
    digest = require_string(first, "digest", "ontology_lock_output.spec.resolved[0]")
    require_digest(digest, "ontology_lock_output.spec.resolved[0].digest")
    if mismatches:
        raise ValueError(f"ontology_lock_output metadata mismatch: {'; '.join(mismatches)}")


def validate_ontologyc_adapter_report(
    policy: dict[str, Any],
    *,
    fixture_path: Path,
    report_path: Path,
    fixture: dict[str, Any],
    package: dict[str, Any],
    ir: dict[str, Any],
    ir_path: Path,
    resolved_refs: list[dict[str, Any]],
    unresolved_refs: list[str],
) -> list[dict[str, Any]]:
    contract = ontologyc_adapter_report_contract(policy)
    report = load_yaml(report_path)

    accepted_kind = require_string(contract, "accepted_report_kind", "adapter_report_contract")
    if require_string(report, "artifact_kind", "adapter_report") != accepted_kind:
        raise ValueError(f"adapter_report.artifact_kind must be {accepted_kind}")
    contract_schema_version = require_int(contract, "schema_version", "adapter_report_contract")
    if require_int(report, "schema_version", "adapter_report") != contract_schema_version:
        raise ValueError("adapter_report.schema_version does not match policy")
    if require_string(report, "proposal_id", "adapter_report") != fixture["proposal_id"]:
        raise ValueError("adapter_report.proposal_id does not match fixture")

    producer = require_object(report, "producer", "adapter_report")
    if require_string(producer, "tool", "adapter_report.producer") != require_string(
        contract, "accepted_tool", "adapter_report_contract"
    ):
        raise ValueError("adapter_report.producer.tool is not accepted")
    if require_string(producer, "command", "adapter_report.producer") != require_string(
        contract, "accepted_command", "adapter_report_contract"
    ):
        raise ValueError("adapter_report.producer.command is not accepted")

    report_package = require_object(report, "package", "adapter_report")
    required_fields = require_string_list(
        contract, "required_package_fields", "adapter_report_contract"
    )
    for field in required_fields:
        require_string(report_package, field, "adapter_report.package")
    require_digest(report_package["digest"], "adapter_report.package.digest")

    authority_fields = require_string_list(contract, "authority_fields", "adapter_report_contract")
    for field in authority_fields:
        prefix, _, package_field = field.partition(".")
        if prefix != "package" or not package_field:
            raise ValueError("adapter_report_contract.authority_fields must use package.<field>")
        if report_package.get(package_field) != package.get(package_field):
            raise ValueError(f"adapter_report.package.{package_field} does not match fixture")

    inputs = require_object(report, "inputs", "adapter_report")
    required_input_refs = require_string_list(
        contract, "required_input_refs", "adapter_report_contract"
    )
    for field in required_input_refs:
        require_string(inputs, field, "adapter_report.inputs")

    validate_ir_metadata(ir, report_package)
    normalized_ir_ref = resolve_report_file(
        report_path,
        inputs["normalized_ir_ref"],
        "adapter_report.inputs.normalized_ir_ref",
    )
    if ir_path != normalized_ir_ref:
        raise ValueError("adapter_report.inputs.normalized_ir_ref does not match fixture IR")

    binding_ref = resolve_report_file(
        report_path,
        inputs["binding_ref"],
        "adapter_report.inputs.binding_ref",
    )
    if binding_ref != fixture_path.resolve():
        raise ValueError("adapter_report.inputs.binding_ref does not match fixture")

    outputs = require_object(report, "outputs", "adapter_report")
    required_output_refs = require_string_list(
        contract, "required_output_refs", "adapter_report_contract"
    )
    for field in required_output_refs:
        require_string(outputs, field, "adapter_report.outputs")

    concept_refs_output = load_yaml(
        resolve_report_file(
            report_path,
            outputs["concept_refs_ref"],
            "adapter_report.outputs.concept_refs_ref",
        )
    )
    if require_string(concept_refs_output, "kind", "concept_refs_output") != "ConceptRefSet":
        raise ValueError("concept_refs_output.kind must be ConceptRefSet")
    concept_metadata = require_object(concept_refs_output, "metadata", "concept_refs_output")
    for field, expected in (
        ("ontology", report_package["package_id"]),
        ("namespace", report_package["namespace"]),
        ("version", report_package["version"]),
    ):
        if concept_metadata.get(field) != expected:
            raise ValueError(f"concept_refs_output.metadata.{field} does not match package")
    output_entries = output_ref_entries(concept_refs_output, "concept_refs_output")
    expected_aliases = sorted(entry["source_ref"] for entry in resolved_refs)
    if sorted(output_entries) != expected_aliases:
        raise ValueError("concept_refs_output aliases do not match resolved report refs")
    expected_output_refs = ontologyc_output_ref_map(ir)
    for alias in expected_aliases:
        output_entry = output_entries[alias]
        expected_entry = expected_output_refs.get(alias)
        if not expected_entry:
            raise ValueError(f"concept_refs_output alias {alias!r} is missing from normalized IR")
        for field, expected_value in expected_entry.items():
            if output_entry.get(field) != expected_value:
                raise ValueError(
                    f"concept_refs_output {alias}.{field} expected {expected_value!r}, "
                    f"got {output_entry.get(field)!r}"
                )

    ontology_gaps_output = load_yaml(
        resolve_report_file(
            report_path,
            outputs["ontology_gaps_ref"],
            "adapter_report.outputs.ontology_gaps_ref",
        )
    )
    if require_string(ontology_gaps_output, "kind", "ontology_gaps_output") != "OntologyGapSet":
        raise ValueError("ontology_gaps_output.kind must be OntologyGapSet")
    output_gaps = sorted(output_gap_refs(ontology_gaps_output, "ontology_gaps_output"))
    if output_gaps != sorted(unresolved_refs):
        raise ValueError("ontology_gaps_output gaps do not match unresolved report refs")

    ontology_lock_output = load_yaml(
        resolve_report_file(
            report_path,
            outputs["ontology_lock_ref"],
            "adapter_report.outputs.ontology_lock_ref",
        )
    )
    validate_ontology_lock_output(ontology_lock_output, report_package)

    summary = require_object(report, "summary", "adapter_report")
    status = require_string(summary, "status", "adapter_report.summary")
    if status not in require_string_list(contract, "status_values", "adapter_report_contract"):
        raise ValueError("adapter_report.summary.status is not accepted")
    if status != require_string(contract, "smoke_required_status", "adapter_report_contract"):
        raise ValueError("adapter_report.summary.status is not ready for smoke")
    if require_int(summary, "resolved_ref_count", "adapter_report.summary") != len(resolved_refs):
        raise ValueError("adapter_report.summary.resolved_ref_count does not match outputs")
    if require_int(summary, "gap_count", "adapter_report.summary") != len(unresolved_refs):
        raise ValueError("adapter_report.summary.gap_count does not match outputs")
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if require_bool(summary, field, "adapter_report.summary") is not False:
            raise ValueError(f"adapter_report.summary.{field} must be false")

    boundary = require_object(report, "authority_boundary", "adapter_report")
    if (
        require_string(boundary, "digest_authority", "adapter_report.authority_boundary")
        != "normalized_ir_sourceDigest"
    ):
        raise ValueError(
            "adapter_report.authority_boundary.digest_authority must be normalized_ir_sourceDigest"
        )
    for field in (
        "report_is_authority",
        "ontology_lock_is_canonical",
        "automatic_import_lock_update",
        "automatic_canonical_node_update",
    ):
        if require_bool(boundary, field, "adapter_report.authority_boundary") is not False:
            raise ValueError(f"adapter_report.authority_boundary.{field} must be false")

    return [
        {
            "check_id": "adapter_report_shape_valid",
            "status": "passed",
            "detail": "accepted ontologyc adapter report shape",
        },
        {
            "check_id": "adapter_report_source_version_digest_match",
            "status": "passed",
            "detail": "package source, version, and digest match fixture and normalized IR",
        },
        {
            "check_id": "adapter_report_outputs_resolve",
            "status": "passed",
            "detail": "concept refs, ontology lock, and ontology gaps resolve under fixture root",
        },
        {
            "check_id": "adapter_report_counts_match_outputs",
            "status": "passed",
            "detail": "reported resolved refs and gaps match output artifacts",
        },
        {
            "check_id": "adapter_report_authority_boundary_preserved",
            "status": "passed",
            "detail": "report remains evidence only and cannot mutate canonical SpecGraph state",
        },
    ]


def build_ontologyc_adapter_report_smoke(
    policy: dict[str, Any],
    *,
    fixture_path: Path,
    report_path: Path,
    fixture: dict[str, Any],
    package: dict[str, Any],
    ir: dict[str, Any],
    ir_path: Path,
    resolved_refs: list[dict[str, Any]],
    unresolved_refs: list[str],
) -> dict[str, Any]:
    checks = validate_ontologyc_adapter_report(
        policy,
        fixture_path=fixture_path,
        report_path=report_path,
        fixture=fixture,
        package=package,
        ir=ir,
        ir_path=ir_path,
        resolved_refs=resolved_refs,
        unresolved_refs=unresolved_refs,
    )
    contract = ontologyc_adapter_report_contract(policy)
    return {
        "artifact_kind": "ontologyc_adapter_report_smoke",
        "schema_version": 1,
        "proposal_id": fixture["proposal_id"],
        "source_fixture": relative_path(fixture_path),
        "source_report": relative_path(report_path),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "accepted_report_kind": require_string(
            contract, "accepted_report_kind", "adapter_report_contract"
        ),
        "adapter_command": require_string(contract, "accepted_command", "adapter_report_contract"),
        "source_authority": {
            "package_id": package["package_id"],
            "namespace": package["namespace"],
            "version": package["version"],
            "source_uri": package["source_uri"],
            "source_ref": package.get("source_ref"),
            "digest": package["digest"],
            "digest_validation": contract.get("digest_validation"),
        },
        "checks": checks,
        "summary": {
            "status": "passed",
            "resolved_ref_count": len(resolved_refs),
            "gap_count": len(unresolved_refs),
            "next_gap": "review_ontology_import_gap" if unresolved_refs else "none",
        },
    }


def require_semantic_control_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if policy.get("artifact_kind") != "ontology_semantic_control_policy":
        raise ValueError(
            "semantic_control_policy.artifact_kind must be ontology_semantic_control_policy"
        )
    if require_int(policy, "schema_version", "semantic_control_policy") != 1:
        raise ValueError("semantic_control_policy.schema_version must be 1")
    if require_string(policy, "proposal_id", "semantic_control_policy") != "0103":
        raise ValueError("semantic_control_policy.proposal_id must be 0103")
    layout = require_object(policy, "repository_layout", "semantic_control_policy")
    require_layout_path(layout, "ontology_delta_candidate_review_packet")
    require_layout_path(layout, "semantic_context_pack")
    require_layout_path(layout, "semantic_lint_input")
    require_layout_path(layout, "semantic_lint_report")
    require_layout_path(layout, "semantic_review_surface")
    require_layout_path(layout, "supervisor_semantic_gate")
    require_layout_path(layout, "ontology_delta_draft_intake")
    require_layout_path(layout, "ontology_closed_loop_evidence")
    require_layout_path(layout, "ontology_review_dashboard")
    require_layout_path(layout, "ontology_owner_decision_report")
    require_layout_path(layout, "ontology_decision_import_preview")
    require_layout_path(layout, "semantic_lint_smoke")
    boundary = require_object(policy, "authority_boundary", "semantic_control_policy")
    for field in (
        "context_pack_is_authority",
        "semantic_lint_input_is_authority",
        "lint_report_is_authority",
        "smoke_report_is_authority",
        "ontology_delta_candidate_is_authority",
        "semantic_review_surface_is_authority",
        "supervisor_semantic_gate_is_authority",
        "ontology_delta_draft_intake_is_authority",
        "ontology_closed_loop_evidence_is_authority",
        "ontology_review_dashboard_is_authority",
        "ontology_owner_decision_report_is_authority",
        "ontology_decision_import_preview_is_authority",
        "prompt_agent_execution_allowed",
        "automatic_import_lock_update",
        "automatic_canonical_node_update",
        "canonical_mutations_allowed",
    ):
        if require_bool(boundary, field, "semantic_control_policy.authority_boundary") is not False:
            raise ValueError(f"semantic_control_policy.authority_boundary.{field} must be false")
    for field in ("ontology_governance_required", "specgraph_proposal_review_required"):
        if require_bool(boundary, field, "semantic_control_policy.authority_boundary") is not True:
            raise ValueError(f"semantic_control_policy.authority_boundary.{field} must be true")

    output_contract = require_object(policy, "derived_output_contract", "semantic_control_policy")
    for field in (
        "canonical_mutations_allowed",
        "tracked_artifacts_written",
        "writes_canonical_specs",
    ):
        if (
            require_bool(
                output_contract,
                field,
                "semantic_control_policy.derived_output_contract",
            )
            is not False
        ):
            raise ValueError(
                f"semantic_control_policy.derived_output_contract.{field} must be false"
            )
    allowed_roots = require_string_list(
        output_contract,
        "allowed_output_roots",
        "semantic_control_policy.derived_output_contract",
    )
    normalized_roots = {Path(root).as_posix().rstrip("/") for root in allowed_roots}
    if normalized_roots != {"runs"}:
        raise ValueError(
            "semantic_control_policy.derived_output_contract.allowed_output_roots "
            "must only allow runs/"
        )

    contract = require_object(policy, "semantic_lint_contract", "semantic_control_policy")
    classifications = require_string_list(
        contract, "term_classifications", "semantic_control_policy.semantic_lint_contract"
    )
    statuses = require_string_list(
        contract, "term_statuses", "semantic_control_policy.semantic_lint_contract"
    )
    priority = require_string_list(
        contract, "summary_status_priority", "semantic_control_policy.semantic_lint_contract"
    )
    required_classifications = {
        "accepted_term",
        "accepted_alias",
        "deprecated_term",
        "ambiguous_term",
        "unknown_term",
        "out_of_domain_term",
        "relation_conflict",
        "candidate_delta_term",
    }
    missing_classifications = sorted(required_classifications - set(classifications))
    if missing_classifications:
        raise ValueError(
            "semantic_control_policy.semantic_lint_contract.term_classifications "
            f"missing: {', '.join(missing_classifications)}"
        )
    if not priority or any(status not in statuses for status in priority):
        raise ValueError(
            "semantic_control_policy.semantic_lint_contract.summary_status_priority "
            "must reference declared statuses"
        )
    suggestions = require_object(
        contract, "suggested_actions", "semantic_control_policy.semantic_lint_contract"
    )
    for classification in classifications:
        require_string(suggestions, classification, "semantic_control_policy.suggested_actions")

    source_contract = require_object(policy, "source_surface_contract", "semantic_control_policy")
    required_artifact_kinds = require_string_list(
        source_contract,
        "required_artifact_kinds",
        "semantic_control_policy.source_surface_contract",
    )
    if not required_artifact_kinds:
        raise ValueError("semantic_control_policy.source_surface_contract requires artifacts")
    flags = require_object(
        source_contract,
        "required_authority_flags",
        "semantic_control_policy.source_surface_contract",
    )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if (
            require_bool(flags, field, "semantic_control_policy.required_authority_flags")
            is not False
        ):
            raise ValueError(
                f"semantic_control_policy.required_authority_flags.{field} must be false"
            )
    context_contract = require_object(
        policy, "semantic_context_pack_contract", "semantic_control_policy"
    )
    if (
        require_string(
            context_contract,
            "artifact_kind",
            "semantic_control_policy.semantic_context_pack_contract",
        )
        != "ontology_semantic_context_pack"
    ):
        raise ValueError(
            "semantic_control_policy.semantic_context_pack_contract.artifact_kind "
            "must be ontology_semantic_context_pack"
        )
    target = require_object(
        context_contract, "target", "semantic_control_policy.semantic_context_pack_contract"
    )
    require_string(
        target, "target_kind", "semantic_control_policy.semantic_context_pack_contract.target"
    )
    require_string(
        target, "target_ref", "semantic_control_policy.semantic_context_pack_contract.target"
    )
    context_surfaces = set(
        require_string_list(
            context_contract,
            "required_source_surfaces",
            "semantic_control_policy.semantic_context_pack_contract",
        )
    )
    missing_context_surfaces = sorted(context_surfaces - set(required_artifact_kinds))
    if missing_context_surfaces:
        raise ValueError(
            "semantic_control_policy.semantic_context_pack_contract.required_source_surfaces "
            f"not declared by source_surface_contract: {', '.join(missing_context_surfaces)}"
        )
    consumer_boundary = require_object(
        context_contract,
        "consumer_boundary",
        "semantic_control_policy.semantic_context_pack_contract",
    )
    for field in ("for_prompt_agent_input", "for_specspace_review_surface"):
        if (
            require_bool(
                consumer_boundary,
                field,
                "semantic_control_policy.semantic_context_pack_contract.consumer_boundary",
            )
            is not True
        ):
            raise ValueError(
                "semantic_control_policy.semantic_context_pack_contract.consumer_boundary."
                f"{field} must be true"
            )
    for field in (
        "may_expand_terms_without_review",
        "may_execute_prompt_agent",
        "may_mutate_canonical_specs",
    ):
        if (
            require_bool(
                consumer_boundary,
                field,
                "semantic_control_policy.semantic_context_pack_contract.consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.semantic_context_pack_contract.consumer_boundary."
                f"{field} must be false"
            )
    require_string(
        context_contract, "next_gap", "semantic_control_policy.semantic_context_pack_contract"
    )
    lint_input_contract = require_object(
        policy, "semantic_lint_input_contract", "semantic_control_policy"
    )
    if (
        require_string(
            lint_input_contract,
            "artifact_kind",
            "semantic_control_policy.semantic_lint_input_contract",
        )
        != "ontology_semantic_lint_input"
    ):
        raise ValueError(
            "semantic_control_policy.semantic_lint_input_contract.artifact_kind "
            "must be ontology_semantic_lint_input"
        )
    lint_input_target = require_object(
        lint_input_contract, "target", "semantic_control_policy.semantic_lint_input_contract"
    )
    require_string(
        lint_input_target,
        "target_kind",
        "semantic_control_policy.semantic_lint_input_contract.target",
    )
    require_string(
        lint_input_target,
        "target_ref",
        "semantic_control_policy.semantic_lint_input_contract.target",
    )
    require_string_list(
        lint_input_contract,
        "source_output_kinds",
        "semantic_control_policy.semantic_lint_input_contract",
    )
    require_string_list(
        lint_input_contract,
        "input_sections",
        "semantic_control_policy.semantic_lint_input_contract",
    )
    require_string(
        lint_input_contract,
        "extraction_mode",
        "semantic_control_policy.semantic_lint_input_contract",
    )
    lint_input_consumer_boundary = require_object(
        lint_input_contract,
        "consumer_boundary",
        "semantic_control_policy.semantic_lint_input_contract",
    )
    for field in ("for_semantic_lint_report", "for_supervisor_gate_evidence"):
        if (
            require_bool(
                lint_input_consumer_boundary,
                field,
                "semantic_control_policy.semantic_lint_input_contract.consumer_boundary",
            )
            is not True
        ):
            raise ValueError(
                "semantic_control_policy.semantic_lint_input_contract.consumer_boundary."
                f"{field} must be true"
            )
    for field in (
        "may_parse_arbitrary_text",
        "may_execute_prompt_agent",
        "may_mutate_canonical_specs",
    ):
        if (
            require_bool(
                lint_input_consumer_boundary,
                field,
                "semantic_control_policy.semantic_lint_input_contract.consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.semantic_lint_input_contract.consumer_boundary."
                f"{field} must be false"
            )
    require_string(
        lint_input_contract, "next_gap", "semantic_control_policy.semantic_lint_input_contract"
    )
    lint_input_sources = require_object(
        policy, "semantic_lint_input_sources", "semantic_control_policy"
    )
    if (
        require_string(
            lint_input_sources,
            "artifact_kind",
            "semantic_control_policy.semantic_lint_input_sources",
        )
        != "ontology_semantic_lint_input_source_set"
    ):
        raise ValueError(
            "semantic_control_policy.semantic_lint_input_sources.artifact_kind must be "
            "ontology_semantic_lint_input_source_set"
        )
    raw_source_outputs = lint_input_sources.get("source_outputs")
    if not isinstance(raw_source_outputs, list) or not raw_source_outputs:
        raise ValueError(
            "semantic_control_policy.semantic_lint_input_sources.source_outputs "
            "must be a non-empty list"
        )
    allowed_source_kinds = set(
        require_string_list(
            lint_input_contract,
            "source_output_kinds",
            "semantic_control_policy.semantic_lint_input_contract",
        )
    )
    for source_index, raw_source in enumerate(raw_source_outputs):
        if not isinstance(raw_source, dict):
            raise ValueError(
                "semantic_control_policy.semantic_lint_input_sources."
                f"source_outputs[{source_index}] must be an object"
            )
        source_context = (
            f"semantic_control_policy.semantic_lint_input_sources.source_outputs[{source_index}]"
        )
        require_string(raw_source, "source_id", source_context)
        source_kind = require_string(raw_source, "source_kind", source_context)
        if source_kind not in allowed_source_kinds:
            raise ValueError(
                f"{source_context}.source_kind must be declared by source_output_kinds"
            )
        source_path = require_string(raw_source, "path", source_context)
        source_path_value = Path(source_path)
        if source_path_value.is_absolute() or ".." in source_path_value.parts:
            raise ValueError(f"{source_context}.path must be a relative repository path")
        raw_terms = raw_source.get("terms")
        if not isinstance(raw_terms, list) or not raw_terms:
            raise ValueError(f"{source_context}.terms must be a non-empty list")
        for term_index, raw_term in enumerate(raw_terms):
            if not isinstance(raw_term, dict):
                raise ValueError(f"{source_context}.terms[{term_index}] must be an object")
            require_string(raw_term, "term", f"{source_context}.terms[{term_index}]")
            optional_string(raw_term, "source_ref", f"{source_context}.terms[{term_index}]")

    report_contract = require_object(
        policy, "semantic_lint_report_contract", "semantic_control_policy"
    )
    if (
        require_string(
            report_contract,
            "artifact_kind",
            "semantic_control_policy.semantic_lint_report_contract",
        )
        != "ontology_semantic_lint_report"
    ):
        raise ValueError(
            "semantic_control_policy.semantic_lint_report_contract.artifact_kind "
            "must be ontology_semantic_lint_report"
        )
    if (
        require_string(
            report_contract,
            "source_context_pack_artifact_kind",
            "semantic_control_policy.semantic_lint_report_contract",
        )
        != "ontology_semantic_context_pack"
    ):
        raise ValueError(
            "semantic_control_policy.semantic_lint_report_contract."
            "source_context_pack_artifact_kind must be ontology_semantic_context_pack"
        )
    if (
        require_string(
            report_contract,
            "source_lint_input_artifact_kind",
            "semantic_control_policy.semantic_lint_report_contract",
        )
        != "ontology_semantic_lint_input"
    ):
        raise ValueError(
            "semantic_control_policy.semantic_lint_report_contract."
            "source_lint_input_artifact_kind must be ontology_semantic_lint_input"
        )
    report_target = require_object(
        report_contract, "target", "semantic_control_policy.semantic_lint_report_contract"
    )
    require_string(
        report_target, "target_kind", "semantic_control_policy.semantic_lint_report_contract.target"
    )
    require_string(
        report_target, "target_ref", "semantic_control_policy.semantic_lint_report_contract.target"
    )
    report_consumer_boundary = require_object(
        report_contract,
        "consumer_boundary",
        "semantic_control_policy.semantic_lint_report_contract",
    )
    for field in ("for_supervisor_gate_evidence", "for_specspace_review_surface"):
        if (
            require_bool(
                report_consumer_boundary,
                field,
                "semantic_control_policy.semantic_lint_report_contract.consumer_boundary",
            )
            is not True
        ):
            raise ValueError(
                "semantic_control_policy.semantic_lint_report_contract.consumer_boundary."
                f"{field} must be true"
            )
    for field in (
        "may_execute_prompt_agent",
        "may_mutate_canonical_specs",
        "may_write_ontology_delta",
    ):
        if (
            require_bool(
                report_consumer_boundary,
                field,
                "semantic_control_policy.semantic_lint_report_contract.consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.semantic_lint_report_contract.consumer_boundary."
                f"{field} must be false"
            )
    require_string(
        report_contract, "next_gap", "semantic_control_policy.semantic_lint_report_contract"
    )
    delta_contract = require_object(
        policy, "ontology_delta_candidate_review_packet_contract", "semantic_control_policy"
    )
    if (
        require_string(
            delta_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
        )
        != "ontology_delta_candidate_review_packet"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_delta_candidate_review_packet_contract."
            "artifact_kind must be ontology_delta_candidate_review_packet"
        )
    if (
        require_string(
            delta_contract,
            "source_lint_report_artifact_kind",
            "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
        )
        != "ontology_semantic_lint_report"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_delta_candidate_review_packet_contract."
            "source_lint_report_artifact_kind must be ontology_semantic_lint_report"
        )
    delta_target = require_object(
        delta_contract,
        "target",
        "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
    )
    require_string(
        delta_target,
        "target_kind",
        "semantic_control_policy.ontology_delta_candidate_review_packet_contract.target",
    )
    require_string(
        delta_target,
        "target_ref",
        "semantic_control_policy.ontology_delta_candidate_review_packet_contract.target",
    )
    require_string(
        delta_contract,
        "candidate_source",
        "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
    )
    delta_actions = require_string_list(
        delta_contract,
        "review_actions",
        "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
    )
    required_delta_actions = {
        "approve_for_ontology_package_draft",
        "reject_candidate",
        "request_clarification",
    }
    missing_delta_actions = sorted(required_delta_actions - set(delta_actions))
    if missing_delta_actions:
        raise ValueError(
            "semantic_control_policy.ontology_delta_candidate_review_packet_contract."
            f"review_actions missing: {', '.join(missing_delta_actions)}"
        )
    delta_consumer_boundary = require_object(
        delta_contract,
        "consumer_boundary",
        "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
    )
    for field in ("for_supervisor_gate_evidence", "for_specspace_review_surface"):
        if (
            require_bool(
                delta_consumer_boundary,
                field,
                "semantic_control_policy.ontology_delta_candidate_review_packet_contract."
                "consumer_boundary",
            )
            is not True
        ):
            raise ValueError(
                "semantic_control_policy.ontology_delta_candidate_review_packet_contract."
                f"consumer_boundary.{field} must be true"
            )
    for field in (
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
    ):
        if (
            require_bool(
                delta_consumer_boundary,
                field,
                "semantic_control_policy.ontology_delta_candidate_review_packet_contract."
                "consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.ontology_delta_candidate_review_packet_contract."
                f"consumer_boundary.{field} must be false"
            )
    require_string(
        delta_contract,
        "next_gap",
        "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
    )
    review_surface_contract = require_object(
        policy, "semantic_review_surface_contract", "semantic_control_policy"
    )
    if (
        require_string(
            review_surface_contract,
            "artifact_kind",
            "semantic_control_policy.semantic_review_surface_contract",
        )
        != "ontology_semantic_review_surface"
    ):
        raise ValueError(
            "semantic_control_policy.semantic_review_surface_contract.artifact_kind "
            "must be ontology_semantic_review_surface"
        )
    expected_source_artifacts = {
        "source_context_pack_artifact_kind": "ontology_semantic_context_pack",
        "source_lint_report_artifact_kind": "ontology_semantic_lint_report",
        "source_delta_candidate_review_packet_artifact_kind": (
            "ontology_delta_candidate_review_packet"
        ),
    }
    for field, expected in expected_source_artifacts.items():
        if (
            require_string(
                review_surface_contract,
                field,
                "semantic_control_policy.semantic_review_surface_contract",
            )
            != expected
        ):
            raise ValueError(
                "semantic_control_policy.semantic_review_surface_contract."
                f"{field} must be {expected}"
            )
    review_surface_target = require_object(
        review_surface_contract,
        "target",
        "semantic_control_policy.semantic_review_surface_contract",
    )
    require_string(
        review_surface_target,
        "target_kind",
        "semantic_control_policy.semantic_review_surface_contract.target",
    )
    require_string(
        review_surface_target,
        "target_ref",
        "semantic_control_policy.semantic_review_surface_contract.target",
    )
    review_item_sources = set(
        require_string_list(
            review_surface_contract,
            "review_item_sources",
            "semantic_control_policy.semantic_review_surface_contract",
        )
    )
    required_review_item_sources = {
        "blocking_findings",
        "review_required_findings",
        "ontology_delta_candidates",
    }
    missing_review_item_sources = sorted(required_review_item_sources - review_item_sources)
    if missing_review_item_sources:
        raise ValueError(
            "semantic_control_policy.semantic_review_surface_contract.review_item_sources "
            f"missing: {', '.join(missing_review_item_sources)}"
        )
    if not require_string_list(
        review_surface_contract,
        "display_sections",
        "semantic_control_policy.semantic_review_surface_contract",
    ):
        raise ValueError(
            "semantic_control_policy.semantic_review_surface_contract.display_sections "
            "must be non-empty"
        )
    review_surface_actions = require_string_list(
        review_surface_contract,
        "review_actions",
        "semantic_control_policy.semantic_review_surface_contract",
    )
    supported_review_surface_actions = {
        "replace_with_accepted_term",
        "use_accepted_relation",
        "emit_ontology_gap",
        "approve_for_ontology_package_draft",
        "reject_candidate",
        "request_clarification",
    }
    missing_review_surface_actions = sorted(
        supported_review_surface_actions - set(review_surface_actions)
    )
    if missing_review_surface_actions:
        raise ValueError(
            "semantic_control_policy.semantic_review_surface_contract.review_actions "
            f"missing: {', '.join(missing_review_surface_actions)}"
        )
    unsupported_review_surface_actions = sorted(
        set(review_surface_actions) - supported_review_surface_actions
    )
    if unsupported_review_surface_actions:
        raise ValueError(
            "semantic_control_policy.semantic_review_surface_contract.review_actions "
            f"contains unsupported action: {', '.join(unsupported_review_surface_actions)}"
        )
    review_surface_consumer_boundary = require_object(
        review_surface_contract,
        "consumer_boundary",
        "semantic_control_policy.semantic_review_surface_contract",
    )
    for field in ("for_supervisor_gate_evidence", "for_specspace_review_surface"):
        if (
            require_bool(
                review_surface_consumer_boundary,
                field,
                "semantic_control_policy.semantic_review_surface_contract.consumer_boundary",
            )
            is not True
        ):
            raise ValueError(
                "semantic_control_policy.semantic_review_surface_contract.consumer_boundary."
                f"{field} must be true"
            )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
    ):
        if (
            require_bool(
                review_surface_consumer_boundary,
                field,
                "semantic_control_policy.semantic_review_surface_contract.consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.semantic_review_surface_contract.consumer_boundary."
                f"{field} must be false"
            )
    require_string(
        review_surface_contract,
        "next_gap",
        "semantic_control_policy.semantic_review_surface_contract",
    )
    supervisor_gate_contract = require_object(
        policy, "supervisor_semantic_gate_contract", "semantic_control_policy"
    )
    if (
        require_string(
            supervisor_gate_contract,
            "artifact_kind",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        )
        != "ontology_supervisor_semantic_gate"
    ):
        raise ValueError(
            "semantic_control_policy.supervisor_semantic_gate_contract.artifact_kind "
            "must be ontology_supervisor_semantic_gate"
        )
    if (
        require_string(
            supervisor_gate_contract,
            "source_review_surface_artifact_kind",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        )
        != "ontology_semantic_review_surface"
    ):
        raise ValueError(
            "semantic_control_policy.supervisor_semantic_gate_contract."
            "source_review_surface_artifact_kind must be ontology_semantic_review_surface"
        )
    supervisor_gate_target = require_object(
        supervisor_gate_contract,
        "target",
        "semantic_control_policy.supervisor_semantic_gate_contract",
    )
    require_string(
        supervisor_gate_target,
        "target_kind",
        "semantic_control_policy.supervisor_semantic_gate_contract.target",
    )
    require_string(
        supervisor_gate_target,
        "target_ref",
        "semantic_control_policy.supervisor_semantic_gate_contract.target",
    )
    gate_states = set(
        require_string_list(
            supervisor_gate_contract,
            "gate_states",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        )
    )
    required_gate_states = {"clear", "review_pending", "blocked"}
    missing_gate_states = sorted(required_gate_states - gate_states)
    if missing_gate_states:
        raise ValueError(
            "semantic_control_policy.supervisor_semantic_gate_contract.gate_states "
            f"missing: {', '.join(missing_gate_states)}"
        )
    blocking_states = set(
        require_string_list(
            supervisor_gate_contract,
            "blocking_review_states",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        )
    )
    if "blocked" not in blocking_states:
        raise ValueError(
            "semantic_control_policy.supervisor_semantic_gate_contract."
            "blocking_review_states must include blocked"
        )
    review_states = set(
        require_string_list(
            supervisor_gate_contract,
            "review_required_states",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        )
    )
    required_review_states = {"needs_review", "needs_ontology_owner_review"}
    missing_review_states = sorted(required_review_states - review_states)
    if missing_review_states:
        raise ValueError(
            "semantic_control_policy.supervisor_semantic_gate_contract.review_required_states "
            f"missing: {', '.join(missing_review_states)}"
        )
    if not require_string_list(
        supervisor_gate_contract,
        "evidence_sections",
        "semantic_control_policy.supervisor_semantic_gate_contract",
    ):
        raise ValueError(
            "semantic_control_policy.supervisor_semantic_gate_contract.evidence_sections "
            "must be non-empty"
        )
    if not require_string_list(
        supervisor_gate_contract,
        "failure_modes",
        "semantic_control_policy.supervisor_semantic_gate_contract",
    ):
        raise ValueError(
            "semantic_control_policy.supervisor_semantic_gate_contract.failure_modes "
            "must be non-empty"
        )
    invocation_boundary = require_object(
        supervisor_gate_contract,
        "typed_invocation_boundary",
        "semantic_control_policy.supervisor_semantic_gate_contract",
    )
    require_string(
        invocation_boundary,
        "input_artifact",
        "semantic_control_policy.supervisor_semantic_gate_contract.typed_invocation_boundary",
    )
    require_string(
        invocation_boundary,
        "output_artifact",
        "semantic_control_policy.supervisor_semantic_gate_contract.typed_invocation_boundary",
    )
    for field in (
        "prompt_agent_executed",
        "prompt_agent_execution_allowed",
        "supervisor_prompt_mutation_allowed",
    ):
        if (
            require_bool(
                invocation_boundary,
                field,
                "semantic_control_policy.supervisor_semantic_gate_contract."
                "typed_invocation_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.supervisor_semantic_gate_contract."
                f"typed_invocation_boundary.{field} must be false"
            )
    supervisor_gate_consumer_boundary = require_object(
        supervisor_gate_contract,
        "consumer_boundary",
        "semantic_control_policy.supervisor_semantic_gate_contract",
    )
    if (
        require_bool(
            supervisor_gate_consumer_boundary,
            "for_supervisor_gate_evidence",
            "semantic_control_policy.supervisor_semantic_gate_contract.consumer_boundary",
        )
        is not True
    ):
        raise ValueError(
            "semantic_control_policy.supervisor_semantic_gate_contract.consumer_boundary."
            "for_supervisor_gate_evidence must be true"
        )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
    ):
        if (
            require_bool(
                supervisor_gate_consumer_boundary,
                field,
                "semantic_control_policy.supervisor_semantic_gate_contract.consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.supervisor_semantic_gate_contract.consumer_boundary."
                f"{field} must be false"
            )
    require_string(
        supervisor_gate_contract,
        "next_gap",
        "semantic_control_policy.supervisor_semantic_gate_contract",
    )
    draft_intake_contract = require_object(
        policy, "ontology_delta_draft_intake_contract", "semantic_control_policy"
    )
    if (
        require_string(
            draft_intake_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_delta_draft_intake_contract",
        )
        != "ontology_delta_draft_intake"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_delta_draft_intake_contract.artifact_kind "
            "must be ontology_delta_draft_intake"
        )
    expected_draft_sources = {
        "source_supervisor_semantic_gate_artifact_kind": "ontology_supervisor_semantic_gate",
        "source_delta_candidate_review_packet_artifact_kind": (
            "ontology_delta_candidate_review_packet"
        ),
    }
    for field, expected in expected_draft_sources.items():
        if (
            require_string(
                draft_intake_contract,
                field,
                "semantic_control_policy.ontology_delta_draft_intake_contract",
            )
            != expected
        ):
            raise ValueError(
                "semantic_control_policy.ontology_delta_draft_intake_contract."
                f"{field} must be {expected}"
            )
    draft_intake_target = require_object(
        draft_intake_contract,
        "target",
        "semantic_control_policy.ontology_delta_draft_intake_contract",
    )
    require_string(
        draft_intake_target,
        "target_kind",
        "semantic_control_policy.ontology_delta_draft_intake_contract.target",
    )
    require_string(
        draft_intake_target,
        "target_ref",
        "semantic_control_policy.ontology_delta_draft_intake_contract.target",
    )
    require_string(
        draft_intake_contract,
        "candidate_source",
        "semantic_control_policy.ontology_delta_draft_intake_contract",
    )
    allowed_intake_states = set(
        require_string_list(
            draft_intake_contract,
            "allowed_intake_states",
            "semantic_control_policy.ontology_delta_draft_intake_contract",
        )
    )
    required_intake_states = {
        "blocked_by_semantic_gate",
        "awaiting_ontology_owner_review",
        "no_candidates",
    }
    missing_intake_states = sorted(required_intake_states - allowed_intake_states)
    if missing_intake_states:
        raise ValueError(
            "semantic_control_policy.ontology_delta_draft_intake_contract."
            f"allowed_intake_states missing: {', '.join(missing_intake_states)}"
        )
    required_gate_states = set(
        require_string_list(
            draft_intake_contract,
            "required_gate_states",
            "semantic_control_policy.ontology_delta_draft_intake_contract",
        )
    )
    missing_required_gate_states = sorted(
        {"blocked", "review_pending", "clear"} - required_gate_states
    )
    if missing_required_gate_states:
        raise ValueError(
            "semantic_control_policy.ontology_delta_draft_intake_contract."
            f"required_gate_states missing: {', '.join(missing_required_gate_states)}"
        )
    blocked_gate_states = set(
        require_string_list(
            draft_intake_contract,
            "blocked_gate_states",
            "semantic_control_policy.ontology_delta_draft_intake_contract",
        )
    )
    if "blocked" not in blocked_gate_states:
        raise ValueError(
            "semantic_control_policy.ontology_delta_draft_intake_contract."
            "blocked_gate_states must include blocked"
        )
    review_required_candidate_states = set(
        require_string_list(
            draft_intake_contract,
            "review_required_candidate_states",
            "semantic_control_policy.ontology_delta_draft_intake_contract",
        )
    )
    if "needs_ontology_owner_review" not in review_required_candidate_states:
        raise ValueError(
            "semantic_control_policy.ontology_delta_draft_intake_contract."
            "review_required_candidate_states must include needs_ontology_owner_review"
        )
    draft_intake_consumer_boundary = require_object(
        draft_intake_contract,
        "consumer_boundary",
        "semantic_control_policy.ontology_delta_draft_intake_contract",
    )
    if (
        require_bool(
            draft_intake_consumer_boundary,
            "for_ontology_owner_draft_intake",
            "semantic_control_policy.ontology_delta_draft_intake_contract.consumer_boundary",
        )
        is not True
    ):
        raise ValueError(
            "semantic_control_policy.ontology_delta_draft_intake_contract.consumer_boundary."
            "for_ontology_owner_draft_intake must be true"
        )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
    ):
        if (
            require_bool(
                draft_intake_consumer_boundary,
                field,
                "semantic_control_policy.ontology_delta_draft_intake_contract.consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.ontology_delta_draft_intake_contract."
                f"consumer_boundary.{field} must be false"
            )
    require_string(
        draft_intake_contract,
        "next_gap",
        "semantic_control_policy.ontology_delta_draft_intake_contract",
    )
    closed_loop_contract = require_object(
        policy, "ontology_closed_loop_evidence_contract", "semantic_control_policy"
    )
    if (
        require_string(
            closed_loop_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_closed_loop_evidence_contract",
        )
        != "ontology_closed_loop_evidence"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_closed_loop_evidence_contract.artifact_kind "
            "must be ontology_closed_loop_evidence"
        )
    if (
        require_string(
            closed_loop_contract,
            "source_delta_draft_intake_artifact_kind",
            "semantic_control_policy.ontology_closed_loop_evidence_contract",
        )
        != "ontology_delta_draft_intake"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_closed_loop_evidence_contract."
            "source_delta_draft_intake_artifact_kind must be ontology_delta_draft_intake"
        )
    closed_loop_target = require_object(
        closed_loop_contract,
        "target",
        "semantic_control_policy.ontology_closed_loop_evidence_contract",
    )
    require_string(
        closed_loop_target,
        "target_kind",
        "semantic_control_policy.ontology_closed_loop_evidence_contract.target",
    )
    require_string(
        closed_loop_target,
        "target_ref",
        "semantic_control_policy.ontology_closed_loop_evidence_contract.target",
    )
    evidence_states = set(
        require_string_list(
            closed_loop_contract,
            "evidence_states",
            "semantic_control_policy.ontology_closed_loop_evidence_contract",
        )
    )
    required_evidence_states = {
        "blocked_by_semantic_gate",
        "pending_ontology_owner_decision",
        "no_candidates",
    }
    missing_evidence_states = sorted(required_evidence_states - evidence_states)
    if missing_evidence_states:
        raise ValueError(
            "semantic_control_policy.ontology_closed_loop_evidence_contract."
            f"evidence_states missing: {', '.join(missing_evidence_states)}"
        )
    require_string(
        closed_loop_contract,
        "closed_loop_source",
        "semantic_control_policy.ontology_closed_loop_evidence_contract",
    )
    closed_loop_consumer_boundary = require_object(
        closed_loop_contract,
        "consumer_boundary",
        "semantic_control_policy.ontology_closed_loop_evidence_contract",
    )
    if (
        require_bool(
            closed_loop_consumer_boundary,
            "for_specgraph_evidence_review",
            "semantic_control_policy.ontology_closed_loop_evidence_contract.consumer_boundary",
        )
        is not True
    ):
        raise ValueError(
            "semantic_control_policy.ontology_closed_loop_evidence_contract.consumer_boundary."
            "for_specgraph_evidence_review must be true"
        )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_close_semantic_gate",
    ):
        if (
            require_bool(
                closed_loop_consumer_boundary,
                field,
                "semantic_control_policy.ontology_closed_loop_evidence_contract.consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.ontology_closed_loop_evidence_contract."
                f"consumer_boundary.{field} must be false"
            )
    require_string(
        closed_loop_contract,
        "next_gap",
        "semantic_control_policy.ontology_closed_loop_evidence_contract",
    )
    dashboard_contract = require_object(
        policy, "ontology_review_dashboard_contract", "semantic_control_policy"
    )
    if (
        require_string(
            dashboard_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_review_dashboard_contract",
        )
        != "ontology_review_dashboard"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_review_dashboard_contract.artifact_kind "
            "must be ontology_review_dashboard"
        )
    expected_dashboard_sources = {
        "source_review_surface_artifact_kind": "ontology_semantic_review_surface",
        "source_supervisor_semantic_gate_artifact_kind": "ontology_supervisor_semantic_gate",
        "source_delta_draft_intake_artifact_kind": "ontology_delta_draft_intake",
        "source_closed_loop_evidence_artifact_kind": "ontology_closed_loop_evidence",
    }
    for field, expected in expected_dashboard_sources.items():
        if (
            require_string(
                dashboard_contract,
                field,
                "semantic_control_policy.ontology_review_dashboard_contract",
            )
            != expected
        ):
            raise ValueError(
                "semantic_control_policy.ontology_review_dashboard_contract."
                f"{field} must be {expected}"
            )
    dashboard_target = require_object(
        dashboard_contract,
        "target",
        "semantic_control_policy.ontology_review_dashboard_contract",
    )
    require_string(
        dashboard_target,
        "target_kind",
        "semantic_control_policy.ontology_review_dashboard_contract.target",
    )
    require_string(
        dashboard_target,
        "target_ref",
        "semantic_control_policy.ontology_review_dashboard_contract.target",
    )
    dashboard_sections = set(
        require_string_list(
            dashboard_contract,
            "dashboard_sections",
            "semantic_control_policy.ontology_review_dashboard_contract",
        )
    )
    required_dashboard_sections = {
        "status_summary",
        "gate",
        "blocking_items",
        "review_required_items",
        "delta_candidates",
        "draft_requests",
        "closed_loop_entries",
        "review_actions",
        "source_artifacts",
        "authority_boundary",
    }
    missing_dashboard_sections = sorted(required_dashboard_sections - dashboard_sections)
    if missing_dashboard_sections:
        raise ValueError(
            "semantic_control_policy.ontology_review_dashboard_contract.dashboard_sections "
            f"missing: {', '.join(missing_dashboard_sections)}"
        )
    dashboard_states = set(
        require_string_list(
            dashboard_contract,
            "status_states",
            "semantic_control_policy.ontology_review_dashboard_contract",
        )
    )
    required_dashboard_states = {
        "blocked_by_semantic_gate",
        "pending_ontology_owner_decision",
        "review_pending",
        "clear",
        "no_candidates",
    }
    missing_dashboard_states = sorted(required_dashboard_states - dashboard_states)
    if missing_dashboard_states:
        raise ValueError(
            "semantic_control_policy.ontology_review_dashboard_contract.status_states "
            f"missing: {', '.join(missing_dashboard_states)}"
        )
    dashboard_consumer_boundary = require_object(
        dashboard_contract,
        "consumer_boundary",
        "semantic_control_policy.ontology_review_dashboard_contract",
    )
    for field in ("for_specgraph_review_dashboard", "for_specspace_review_dashboard"):
        if (
            require_bool(
                dashboard_consumer_boundary,
                field,
                "semantic_control_policy.ontology_review_dashboard_contract.consumer_boundary",
            )
            is not True
        ):
            raise ValueError(
                "semantic_control_policy.ontology_review_dashboard_contract."
                f"consumer_boundary.{field} must be true"
            )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_import_owner_decision",
        "may_close_semantic_gate",
    ):
        if (
            require_bool(
                dashboard_consumer_boundary,
                field,
                "semantic_control_policy.ontology_review_dashboard_contract.consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.ontology_review_dashboard_contract."
                f"consumer_boundary.{field} must be false"
            )
    require_string(
        dashboard_contract,
        "next_gap",
        "semantic_control_policy.ontology_review_dashboard_contract",
    )
    owner_decision_contract = require_object(
        policy, "ontology_owner_decision_report_contract", "semantic_control_policy"
    )
    if (
        require_string(
            owner_decision_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_owner_decision_report_contract",
        )
        != "ontology_owner_decision_report"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_owner_decision_report_contract.artifact_kind "
            "must be ontology_owner_decision_report"
        )
    if (
        require_string(
            owner_decision_contract,
            "source_closed_loop_evidence_artifact_kind",
            "semantic_control_policy.ontology_owner_decision_report_contract",
        )
        != "ontology_closed_loop_evidence"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_owner_decision_report_contract."
            "source_closed_loop_evidence_artifact_kind must be ontology_closed_loop_evidence"
        )
    owner_decision_target = require_object(
        owner_decision_contract,
        "target",
        "semantic_control_policy.ontology_owner_decision_report_contract",
    )
    require_string(
        owner_decision_target,
        "target_kind",
        "semantic_control_policy.ontology_owner_decision_report_contract.target",
    )
    require_string(
        owner_decision_target,
        "target_ref",
        "semantic_control_policy.ontology_owner_decision_report_contract.target",
    )
    decision_states = set(
        require_string_list(
            owner_decision_contract,
            "decision_states",
            "semantic_control_policy.ontology_owner_decision_report_contract",
        )
    )
    required_decision_states = {"accepted", "rejected", "needs_clarification"}
    missing_decision_states = sorted(required_decision_states - decision_states)
    if missing_decision_states:
        raise ValueError(
            "semantic_control_policy.ontology_owner_decision_report_contract.decision_states "
            f"missing: {', '.join(missing_decision_states)}"
        )
    required_decision_fields = set(
        require_string_list(
            owner_decision_contract,
            "required_decision_fields",
            "semantic_control_policy.ontology_owner_decision_report_contract",
        )
    )
    expected_decision_fields = {
        "decision_id",
        "candidate_id",
        "intake_id",
        "decision_state",
        "ontology_decision_ref",
        "decided_by",
        "decided_at",
        "accepted_ontology_delta",
        "imports_into_specgraph",
        "closes_semantic_gate",
        "mutates_canonical_specs",
    }
    missing_decision_fields = sorted(expected_decision_fields - required_decision_fields)
    if missing_decision_fields:
        raise ValueError(
            "semantic_control_policy.ontology_owner_decision_report_contract."
            f"required_decision_fields missing: {', '.join(missing_decision_fields)}"
        )
    owner_decision_consumer_boundary = require_object(
        owner_decision_contract,
        "consumer_boundary",
        "semantic_control_policy.ontology_owner_decision_report_contract",
    )
    for field in ("for_specgraph_decision_import_preview", "for_specspace_review_dashboard"):
        if (
            require_bool(
                owner_decision_consumer_boundary,
                field,
                "semantic_control_policy.ontology_owner_decision_report_contract.consumer_boundary",
            )
            is not True
        ):
            raise ValueError(
                "semantic_control_policy.ontology_owner_decision_report_contract."
                f"consumer_boundary.{field} must be true"
            )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_import_into_specgraph",
        "may_close_semantic_gate",
    ):
        if (
            require_bool(
                owner_decision_consumer_boundary,
                field,
                "semantic_control_policy.ontology_owner_decision_report_contract.consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.ontology_owner_decision_report_contract."
                f"consumer_boundary.{field} must be false"
            )
    owner_decision_fixture = require_object(
        policy, "owner_decision_fixture", "semantic_control_policy"
    )
    if (
        require_string(
            owner_decision_fixture,
            "artifact_kind",
            "semantic_control_policy.owner_decision_fixture",
        )
        != "ontology_owner_decision_fixture"
    ):
        raise ValueError(
            "semantic_control_policy.owner_decision_fixture.artifact_kind must be "
            "ontology_owner_decision_fixture"
        )
    owner_fixture_decisions = owner_decision_fixture.get("decisions")
    if not isinstance(owner_fixture_decisions, list):
        raise ValueError("semantic_control_policy.owner_decision_fixture.decisions must be a list")
    for index, raw_decision in enumerate(owner_fixture_decisions):
        if not isinstance(raw_decision, dict):
            raise ValueError(
                f"semantic_control_policy.owner_decision_fixture.decisions[{index}] "
                "must be an object"
            )
        for field in sorted(required_decision_fields):
            if field in {
                "accepted_ontology_delta",
                "imports_into_specgraph",
                "closes_semantic_gate",
                "mutates_canonical_specs",
            }:
                require_bool(
                    raw_decision,
                    field,
                    f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
                )
            else:
                require_string(
                    raw_decision,
                    field,
                    f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
                )
        decision_state = require_string(
            raw_decision,
            "decision_state",
            f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
        )
        if decision_state not in decision_states:
            raise ValueError(
                "semantic_control_policy.owner_decision_fixture.decisions"
                f"[{index}].decision_state must be declared by decision_states"
            )
        if require_bool(
            raw_decision,
            "accepted_ontology_delta",
            f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
        ) != (decision_state == "accepted"):
            raise ValueError(
                "semantic_control_policy.owner_decision_fixture.decisions"
                f"[{index}].accepted_ontology_delta must match accepted decision_state"
            )
        for field in ("imports_into_specgraph", "closes_semantic_gate", "mutates_canonical_specs"):
            if (
                require_bool(
                    raw_decision,
                    field,
                    f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
                )
                is not False
            ):
                raise ValueError(
                    "semantic_control_policy.owner_decision_fixture.decisions"
                    f"[{index}].{field} must be false"
                )
    require_string(
        owner_decision_contract,
        "next_gap",
        "semantic_control_policy.ontology_owner_decision_report_contract",
    )
    decision_import_contract = require_object(
        policy, "ontology_decision_import_preview_contract", "semantic_control_policy"
    )
    if (
        require_string(
            decision_import_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_decision_import_preview_contract",
        )
        != "ontology_decision_import_preview"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_decision_import_preview_contract.artifact_kind "
            "must be ontology_decision_import_preview"
        )
    if (
        require_string(
            decision_import_contract,
            "source_review_dashboard_artifact_kind",
            "semantic_control_policy.ontology_decision_import_preview_contract",
        )
        != "ontology_review_dashboard"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_decision_import_preview_contract."
            "source_review_dashboard_artifact_kind must be ontology_review_dashboard"
        )
    if (
        require_string(
            decision_import_contract,
            "source_owner_decision_report_artifact_kind",
            "semantic_control_policy.ontology_decision_import_preview_contract",
        )
        != "ontology_owner_decision_report"
    ):
        raise ValueError(
            "semantic_control_policy.ontology_decision_import_preview_contract."
            "source_owner_decision_report_artifact_kind must be ontology_owner_decision_report"
        )
    decision_import_target = require_object(
        decision_import_contract,
        "target",
        "semantic_control_policy.ontology_decision_import_preview_contract",
    )
    require_string(
        decision_import_target,
        "target_kind",
        "semantic_control_policy.ontology_decision_import_preview_contract.target",
    )
    require_string(
        decision_import_target,
        "target_ref",
        "semantic_control_policy.ontology_decision_import_preview_contract.target",
    )
    preview_states = set(
        require_string_list(
            decision_import_contract,
            "preview_states",
            "semantic_control_policy.ontology_decision_import_preview_contract",
        )
    )
    required_preview_states = {
        "blocked_by_semantic_gate",
        "ready_for_operator_review",
        "rejected_by_owner",
        "needs_clarification",
        "unmatched_decision",
        "no_decisions",
    }
    missing_preview_states = sorted(required_preview_states - preview_states)
    if missing_preview_states:
        raise ValueError(
            "semantic_control_policy.ontology_decision_import_preview_contract.preview_states "
            f"missing: {', '.join(missing_preview_states)}"
        )
    decision_import_consumer_boundary = require_object(
        decision_import_contract,
        "consumer_boundary",
        "semantic_control_policy.ontology_decision_import_preview_contract",
    )
    for field in ("for_specgraph_decision_import_preview", "for_specspace_review_dashboard"):
        if (
            require_bool(
                decision_import_consumer_boundary,
                field,
                "semantic_control_policy.ontology_decision_import_preview_contract."
                "consumer_boundary",
            )
            is not True
        ):
            raise ValueError(
                "semantic_control_policy.ontology_decision_import_preview_contract."
                f"consumer_boundary.{field} must be true"
            )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_apply_preview",
        "may_import_into_specgraph",
        "may_close_semantic_gate",
    ):
        if (
            require_bool(
                decision_import_consumer_boundary,
                field,
                "semantic_control_policy.ontology_decision_import_preview_contract."
                "consumer_boundary",
            )
            is not False
        ):
            raise ValueError(
                "semantic_control_policy.ontology_decision_import_preview_contract."
                f"consumer_boundary.{field} must be false"
            )
    require_string(
        decision_import_contract,
        "next_gap",
        "semantic_control_policy.ontology_decision_import_preview_contract",
    )
    return policy


def semantic_control_map(
    semantic_policy: dict[str, Any],
    section: str,
    *,
    key_field: str = "term",
) -> dict[str, dict[str, Any]]:
    controls = require_object(semantic_policy, "semantic_controls", "semantic_control_policy")
    values = controls.get(section, [])
    if not isinstance(values, list):
        raise ValueError(f"semantic_control_policy.semantic_controls.{section} must be a list")
    entries: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            raise ValueError(
                f"semantic_control_policy.semantic_controls.{section}[{index}] must be an object"
            )
        key = normalize_term(
            require_string(
                item,
                key_field,
                f"semantic_control_policy.semantic_controls.{section}[{index}]",
            )
        )
        if key in entries:
            raise ValueError(
                f"semantic_control_policy.semantic_controls.{section}[{index}] duplicates {key!r}"
            )
        entries[key] = item
    return entries


def semantic_term_status(classification: str) -> str:
    return {
        "accepted_term": "grounded",
        "accepted_alias": "grounded_with_aliases",
        "deprecated_term": "blocked_deprecated_terms",
        "ambiguous_term": "review_required_ambiguous_terms",
        "unknown_term": "review_required_unknown_terms",
        "out_of_domain_term": "blocked_out_of_domain",
        "relation_conflict": "blocked_relation_conflict",
        "candidate_delta_term": "review_required_unknown_terms",
    }.get(classification, "review_required_unknown_terms")


def semantic_summary_status(statuses: list[str], semantic_policy: dict[str, Any]) -> str:
    if not statuses:
        return "grounded"
    contract = require_object(semantic_policy, "semantic_lint_contract", "semantic_control_policy")
    priority = require_string_list(
        contract, "summary_status_priority", "semantic_control_policy.semantic_lint_contract"
    )
    present = set(statuses)
    for status in priority:
        if status in present:
            return status
    return sorted(present)[0]


def semantic_next_gap(status: str, semantic_policy: dict[str, Any]) -> str:
    defaults = require_object(semantic_policy, "next_gap_defaults", "semantic_control_policy")
    return require_string(defaults, status, "semantic_control_policy.next_gap_defaults")


def validate_semantic_source_surfaces(
    semantic_policy: dict[str, Any],
    *,
    package_index: dict[str, Any],
    gap_index: dict[str, Any],
    governance_evidence_index: dict[str, Any],
    binding_preview: dict[str, Any],
) -> None:
    source_contract = require_object(
        semantic_policy, "source_surface_contract", "semantic_control_policy"
    )
    required_artifact_kinds = set(
        require_string_list(
            source_contract,
            "required_artifact_kinds",
            "semantic_control_policy.source_surface_contract",
        )
    )
    surfaces = {
        "ontology_package_index": package_index,
        "ontology_import_gap_index": gap_index,
        "ontology_governance_evidence_index": governance_evidence_index,
        "ontology_binding_preview": binding_preview,
    }
    missing = sorted(required_artifact_kinds - set(surfaces))
    if missing:
        raise ValueError(f"semantic source surfaces missing: {', '.join(missing)}")
    for artifact_kind in sorted(required_artifact_kinds):
        surface = surfaces[artifact_kind]
        if require_string(surface, "artifact_kind", artifact_kind) != artifact_kind:
            raise ValueError(f"{artifact_kind}.artifact_kind must be {artifact_kind}")
        for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
            if require_bool(surface, field, artifact_kind) is not False:
                raise ValueError(f"{artifact_kind}.{field} must be false")


def build_semantic_term_results(
    semantic_policy: dict[str, Any],
    *,
    detected_terms: list[Any],
    detected_terms_context: str,
    accepted_by_ref: dict[str, dict[str, Any]],
    gap_by_ref: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
    contract = require_object(semantic_policy, "semantic_lint_contract", "semantic_control_policy")
    suggested_actions = require_object(
        contract, "suggested_actions", "semantic_control_policy.semantic_lint_contract"
    )
    aliases = semantic_control_map(semantic_policy, "aliases")
    deprecated_terms = semantic_control_map(semantic_policy, "deprecated_terms")
    relation_conflicts = semantic_control_map(semantic_policy, "relation_conflicts")
    classification_counts = {
        classification: 0
        for classification in require_string_list(
            contract, "term_classifications", "semantic_control_policy.semantic_lint_contract"
        )
    }
    term_results: list[dict[str, Any]] = []
    statuses: list[str] = []
    for index, raw_term in enumerate(detected_terms):
        if not isinstance(raw_term, dict):
            raise ValueError(f"{detected_terms_context}[{index}] must be an object")
        term = require_string(raw_term, "term", f"{detected_terms_context}[{index}]")
        normalized = normalize_term(term)
        source_ref = optional_string(raw_term, "source_ref", f"{detected_terms_context}[{index}]")
        result: dict[str, Any] = {
            "term": term,
            "normalized_term": normalized,
            "source_ref": source_ref or None,
        }
        for evidence_field in (
            "source_output_id",
            "source_output_kind",
            "source_path",
            "source_span",
            "extraction_mode",
        ):
            if evidence_field in raw_term:
                result[evidence_field] = copy.deepcopy(raw_term[evidence_field])

        if normalized in relation_conflicts:
            control = relation_conflicts[normalized]
            classification = "relation_conflict"
            result["accepted_relation_ref"] = require_string(
                control, "accepted_relation_ref", "semantic_control_policy.relation_conflicts"
            )
            result["reason"] = str(control.get("reason", "")).strip()
        elif normalized in deprecated_terms:
            control = deprecated_terms[normalized]
            classification = "deprecated_term"
            result["replacement_ref"] = require_string(
                control, "replacement_ref", "semantic_control_policy.deprecated_terms"
            )
            result["reason"] = str(control.get("reason", "")).strip()
        elif source_ref and source_ref in accepted_by_ref:
            classification = "accepted_term"
            result["concept_ref"] = accepted_by_ref[source_ref]
        elif normalized in aliases:
            control = aliases[normalized]
            concept_ref = require_string(control, "concept_ref", "semantic_control_policy.aliases")
            if concept_ref not in accepted_by_ref:
                classification = "unknown_term"
                result["unresolved_alias_ref"] = concept_ref
            else:
                classification = "accepted_alias"
                result["concept_ref"] = accepted_by_ref[concept_ref]
                result["alias_of"] = concept_ref
                result["reason"] = str(control.get("reason", "")).strip()
        elif source_ref and source_ref in gap_by_ref:
            classification = "unknown_term"
            result["gap"] = gap_by_ref[source_ref]
        else:
            classification = "unknown_term"

        status = semantic_term_status(classification)
        statuses.append(status)
        classification_counts[classification] += 1
        result["classification"] = classification
        result["status"] = status
        result["suggested_action"] = require_string(
            suggested_actions, classification, "semantic_control_policy.suggested_actions"
        )
        term_results.append(result)
    return term_results, statuses, classification_counts


def build_ontology_semantic_context_pack(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    import_policy: dict[str, Any],
    package_index: dict[str, Any],
    gap_index: dict[str, Any],
    governance_evidence_index: dict[str, Any],
    binding_preview: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    validate_semantic_source_surfaces(
        semantic_policy,
        package_index=package_index,
        gap_index=gap_index,
        governance_evidence_index=governance_evidence_index,
        binding_preview=binding_preview,
    )
    context_contract = require_object(
        semantic_policy, "semantic_context_pack_contract", "semantic_control_policy"
    )
    import_layout = require_object(import_policy, "repository_layout", "ontology_import_policy")
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    target = copy_json_object(
        require_object(
            context_contract, "target", "semantic_control_policy.semantic_context_pack_contract"
        )
    )
    consumer_boundary = copy_json_object(
        require_object(
            context_contract,
            "consumer_boundary",
            "semantic_control_policy.semantic_context_pack_contract",
        )
    )

    raw_packages = package_index.get("packages")
    if not isinstance(raw_packages, list):
        raise ValueError("ontology_package_index.packages must be a list")
    packages: list[dict[str, Any]] = []
    for index, raw_package in enumerate(raw_packages):
        if not isinstance(raw_package, dict):
            raise ValueError(f"ontology_package_index.packages[{index}] must be an object")
        package = copy_json_object(raw_package)
        package.setdefault(
            "package_ref",
            f"{package.get('package_id', '')}@{package.get('version', '')}",
        )
        packages.append(package)

    raw_resolved_refs = binding_preview.get("resolved_refs")
    if not isinstance(raw_resolved_refs, list):
        raise ValueError("ontology_binding_preview.resolved_refs must be a list")
    accepted_terms: list[dict[str, Any]] = []
    accepted_relations: list[dict[str, Any]] = []
    accepted_by_ref: dict[str, dict[str, Any]] = {}
    for index, raw_ref in enumerate(raw_resolved_refs):
        if not isinstance(raw_ref, dict):
            raise ValueError(f"ontology_binding_preview.resolved_refs[{index}] must be an object")
        source_ref = require_string(
            raw_ref, "source_ref", f"ontology_binding_preview.resolved_refs[{index}]"
        )
        entry = copy_json_object(raw_ref)
        entry["preferred_term"] = source_ref.rsplit(":", maxsplit=1)[-1]
        accepted_by_ref[source_ref] = entry
        if entry.get("kind") == "relation":
            accepted_relations.append(entry)
        else:
            accepted_terms.append(entry)

    aliases = []
    for normalized_term, control in sorted(
        semantic_control_map(semantic_policy, "aliases").items()
    ):
        concept_ref = require_string(control, "concept_ref", "semantic_control_policy.aliases")
        alias = {
            "term": require_string(control, "term", "semantic_control_policy.aliases"),
            "normalized_term": normalized_term,
            "concept_ref": concept_ref,
            "status": "grounded" if concept_ref in accepted_by_ref else "unresolved_alias_ref",
            "reason": str(control.get("reason", "")).strip(),
        }
        if concept_ref in accepted_by_ref:
            alias["concept"] = accepted_by_ref[concept_ref]
        aliases.append(alias)

    deprecated_terms = []
    for normalized_term, control in sorted(
        semantic_control_map(semantic_policy, "deprecated_terms").items()
    ):
        replacement_ref = require_string(
            control, "replacement_ref", "semantic_control_policy.deprecated_terms"
        )
        deprecated = {
            "term": require_string(control, "term", "semantic_control_policy.deprecated_terms"),
            "normalized_term": normalized_term,
            "replacement_ref": replacement_ref,
            "replacement_status": (
                "grounded" if replacement_ref in accepted_by_ref else "unresolved_replacement_ref"
            ),
            "reason": str(control.get("reason", "")).strip(),
        }
        if replacement_ref in accepted_by_ref:
            deprecated["replacement"] = accepted_by_ref[replacement_ref]
        deprecated_terms.append(deprecated)

    relation_conflicts = []
    accepted_relations_by_ref = {entry["source_ref"]: entry for entry in accepted_relations}
    for normalized_term, control in sorted(
        semantic_control_map(semantic_policy, "relation_conflicts").items()
    ):
        accepted_relation_ref = require_string(
            control, "accepted_relation_ref", "semantic_control_policy.relation_conflicts"
        )
        conflict = {
            "term": require_string(control, "term", "semantic_control_policy.relation_conflicts"),
            "normalized_term": normalized_term,
            "accepted_relation_ref": accepted_relation_ref,
            "status": (
                "grounded"
                if accepted_relation_ref in accepted_relations_by_ref
                else "unresolved_relation_ref"
            ),
            "reason": str(control.get("reason", "")).strip(),
        }
        if accepted_relation_ref in accepted_relations_by_ref:
            conflict["accepted_relation"] = accepted_relations_by_ref[accepted_relation_ref]
        relation_conflicts.append(conflict)

    raw_gaps = gap_index.get("gaps")
    if not isinstance(raw_gaps, list):
        raise ValueError("ontology_import_gap_index.gaps must be a list")
    unresolved_gaps = []
    for index, gap in enumerate(raw_gaps):
        if not isinstance(gap, dict):
            raise ValueError(f"ontology_import_gap_index.gaps[{index}] must be an object")
        unresolved_gaps.append(copy_json_object(gap))
    raw_evidence = governance_evidence_index.get("evidence")
    if not isinstance(raw_evidence, list):
        raise ValueError("ontology_governance_evidence_index.evidence must be a list")
    governance_evidence = []
    for index, evidence in enumerate(raw_evidence):
        if not isinstance(evidence, dict):
            raise ValueError(
                f"ontology_governance_evidence_index.evidence[{index}] must be an object"
            )
        governance_evidence.append(copy_json_object(evidence))
    status = "ready_with_gaps" if unresolved_gaps else "ready"
    if not governance_evidence:
        status = "missing_governance_evidence"

    return {
        "artifact_kind": require_string(
            context_contract,
            "artifact_kind",
            "semantic_control_policy.semantic_context_pack_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0104",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_surfaces": {
            "ontology_package_index": require_layout_path(import_layout, "package_index"),
            "ontology_import_gap_index": require_layout_path(import_layout, "gap_index"),
            "ontology_governance_evidence_index": require_layout_path(
                import_layout, "governance_evidence_index"
            ),
            "ontology_binding_preview": require_layout_path(import_layout, "binding_preview"),
        },
        "target_scope": target,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "packages": packages,
        "accepted_terms": accepted_terms,
        "accepted_relations": accepted_relations,
        "aliases": aliases,
        "deprecated_terms": deprecated_terms,
        "relation_conflicts": relation_conflicts,
        "unresolved_gaps": unresolved_gaps,
        "governance_evidence": governance_evidence,
        "consumer_boundary": consumer_boundary,
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": status,
            "package_count": len(packages),
            "accepted_term_count": len(accepted_terms),
            "accepted_relation_count": len(accepted_relations),
            "alias_count": len(aliases),
            "deprecated_term_count": len(deprecated_terms),
            "relation_conflict_count": len(relation_conflicts),
            "unresolved_gap_count": len(unresolved_gaps),
            "governance_evidence_count": len(governance_evidence),
            "next_gap": require_string(
                context_contract,
                "next_gap",
                "semantic_control_policy.semantic_context_pack_contract",
            ),
        },
        "output_artifact": require_layout_path(semantic_layout, "semantic_context_pack"),
    }


def require_ontology_semantic_context_pack(context_pack: dict[str, Any]) -> dict[str, Any]:
    if context_pack.get("artifact_kind") != "ontology_semantic_context_pack":
        raise ValueError("context_pack.artifact_kind must be ontology_semantic_context_pack")
    if require_int(context_pack, "schema_version", "context_pack") != 1:
        raise ValueError("context_pack.schema_version must be 1")
    if require_string(context_pack, "proposal_id", "context_pack") != "0104":
        raise ValueError("context_pack.proposal_id must be 0104")
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if require_bool(context_pack, field, "context_pack") is not False:
            raise ValueError(f"context_pack.{field} must be false")
    boundary = require_object(context_pack, "authority_boundary", "context_pack")
    if require_bool(boundary, "context_pack_is_authority", "context_pack.authority_boundary"):
        raise ValueError("context_pack.authority_boundary.context_pack_is_authority must be false")
    consumer_boundary = require_object(context_pack, "consumer_boundary", "context_pack")
    for field in (
        "may_expand_terms_without_review",
        "may_execute_prompt_agent",
        "may_mutate_canonical_specs",
    ):
        if require_bool(consumer_boundary, field, "context_pack.consumer_boundary") is not False:
            raise ValueError(f"context_pack.consumer_boundary.{field} must be false")
    return context_pack


def resolve_repository_input_path(raw_path: str, context: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{context} must be a relative repository path")
    candidate = (ROOT / path).resolve()
    if not candidate.is_relative_to(ROOT.resolve()):
        raise ValueError(f"{context} must stay within the repository")
    return candidate


def text_position_for_offset(text: str, offset: int) -> tuple[int, int]:
    prefix = text[:offset]
    line = prefix.count("\n") + 1
    last_newline = prefix.rfind("\n")
    column = offset + 1 if last_newline == -1 else offset - last_newline
    return line, column


def build_ontology_semantic_lint_input(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    lint_input_contract = require_object(
        semantic_policy, "semantic_lint_input_contract", "semantic_control_policy"
    )
    lint_input_sources = require_object(
        semantic_policy, "semantic_lint_input_sources", "semantic_control_policy"
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    extraction_mode = require_string(
        lint_input_contract,
        "extraction_mode",
        "semantic_control_policy.semantic_lint_input_contract",
    )
    allowed_source_kinds = set(
        require_string_list(
            lint_input_contract,
            "source_output_kinds",
            "semantic_control_policy.semantic_lint_input_contract",
        )
    )
    raw_source_outputs = lint_input_sources.get("source_outputs")
    if not isinstance(raw_source_outputs, list) or not raw_source_outputs:
        raise ValueError(
            "semantic_control_policy.semantic_lint_input_sources.source_outputs "
            "must be a non-empty list"
        )

    source_outputs: list[dict[str, Any]] = []
    detected_terms: list[dict[str, Any]] = []
    for source_index, raw_source in enumerate(raw_source_outputs):
        if not isinstance(raw_source, dict):
            raise ValueError(
                "semantic_control_policy.semantic_lint_input_sources."
                f"source_outputs[{source_index}] must be an object"
            )
        source_context = (
            f"semantic_control_policy.semantic_lint_input_sources.source_outputs[{source_index}]"
        )
        source_id = require_string(raw_source, "source_id", source_context)
        source_kind = require_string(raw_source, "source_kind", source_context)
        if source_kind not in allowed_source_kinds:
            raise ValueError(
                f"{source_context}.source_kind must be declared by source_output_kinds"
            )
        source_path = require_string(raw_source, "path", source_context)
        resolved_path = resolve_repository_input_path(source_path, f"{source_context}.path")
        text = resolved_path.read_text(encoding="utf-8")
        source_terms = raw_source.get("terms")
        if not isinstance(source_terms, list) or not source_terms:
            raise ValueError(f"{source_context}.terms must be a non-empty list")
        output_term_count = 0
        for term_index, raw_term in enumerate(source_terms):
            if not isinstance(raw_term, dict):
                raise ValueError(f"{source_context}.terms[{term_index}] must be an object")
            term_context = f"{source_context}.terms[{term_index}]"
            term = require_string(raw_term, "term", term_context)
            source_ref = optional_string(raw_term, "source_ref", term_context)
            start_offset = text.find(term)
            if start_offset < 0:
                raise ValueError(f"{term_context}.term {term!r} was not found in {source_path}")
            end_offset = start_offset + len(term)
            line, column = text_position_for_offset(text, start_offset)
            detected_terms.append(
                {
                    "term": term,
                    "source_ref": source_ref or None,
                    "source_output_id": source_id,
                    "source_output_kind": source_kind,
                    "source_path": source_path,
                    "source_span": {
                        "line": line,
                        "column": column,
                        "start_offset": start_offset,
                        "end_offset": end_offset,
                    },
                    "extraction_mode": extraction_mode,
                }
            )
            output_term_count += 1
        source_outputs.append(
            {
                "source_id": source_id,
                "source_kind": source_kind,
                "path": source_path,
                "text_sha256": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "declared_term_count": output_term_count,
            }
        )

    return {
        "artifact_kind": require_string(
            lint_input_contract,
            "artifact_kind",
            "semantic_control_policy.semantic_lint_input_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0116",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "target": copy_json_object(
            require_object(
                lint_input_contract,
                "target",
                "semantic_control_policy.semantic_lint_input_contract",
            )
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_outputs": source_outputs,
        "detected_terms": detected_terms,
        "extraction_summary": {
            "mode": extraction_mode,
            "source_output_count": len(source_outputs),
            "detected_term_count": len(detected_terms),
            "term_source": "semantic_lint_input_sources.source_outputs[].terms",
            "arbitrary_text_parsed": False,
            "prompt_agent_executed": False,
        },
        "consumer_boundary": copy_json_object(
            require_object(
                lint_input_contract,
                "consumer_boundary",
                "semantic_control_policy.semantic_lint_input_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": "ready",
            "source_output_count": len(source_outputs),
            "detected_term_count": len(detected_terms),
            "next_gap": require_string(
                lint_input_contract,
                "next_gap",
                "semantic_control_policy.semantic_lint_input_contract",
            ),
        },
        "output_artifact": require_layout_path(semantic_layout, "semantic_lint_input"),
    }


def require_ontology_semantic_lint_input(lint_input: dict[str, Any]) -> dict[str, Any]:
    if lint_input.get("artifact_kind") != "ontology_semantic_lint_input":
        raise ValueError("lint_input.artifact_kind must be ontology_semantic_lint_input")
    if require_int(lint_input, "schema_version", "lint_input") != 1:
        raise ValueError("lint_input.schema_version must be 1")
    if require_string(lint_input, "proposal_id", "lint_input") != "0116":
        raise ValueError("lint_input.proposal_id must be 0116")
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if require_bool(lint_input, field, "lint_input") is not False:
            raise ValueError(f"lint_input.{field} must be false")
    require_surface_output_artifact(lint_input, "semantic_lint_input")
    source_outputs = lint_input.get("source_outputs")
    if not isinstance(source_outputs, list) or not source_outputs:
        raise ValueError("lint_input.source_outputs must be a non-empty list")
    detected_terms = lint_input.get("detected_terms")
    if not isinstance(detected_terms, list) or not detected_terms:
        raise ValueError("lint_input.detected_terms must be a non-empty list")
    extraction_summary = require_object(lint_input, "extraction_summary", "lint_input")
    if require_bool(extraction_summary, "arbitrary_text_parsed", "lint_input.extraction_summary"):
        raise ValueError("lint_input.extraction_summary.arbitrary_text_parsed must be false")
    if require_bool(extraction_summary, "prompt_agent_executed", "lint_input.extraction_summary"):
        raise ValueError("lint_input.extraction_summary.prompt_agent_executed must be false")
    consumer_boundary = require_object(lint_input, "consumer_boundary", "lint_input")
    for field in ("for_semantic_lint_report", "for_supervisor_gate_evidence"):
        if require_bool(consumer_boundary, field, "lint_input.consumer_boundary") is not True:
            raise ValueError(f"lint_input.consumer_boundary.{field} must be true")
    for field in (
        "may_parse_arbitrary_text",
        "may_execute_prompt_agent",
        "may_mutate_canonical_specs",
    ):
        if require_bool(consumer_boundary, field, "lint_input.consumer_boundary") is not False:
            raise ValueError(f"lint_input.consumer_boundary.{field} must be false")
    authority_boundary = require_object(lint_input, "authority_boundary", "lint_input")
    if require_bool(
        authority_boundary, "semantic_lint_input_is_authority", "lint_input.authority_boundary"
    ):
        raise ValueError(
            "lint_input.authority_boundary.semantic_lint_input_is_authority must be false"
        )
    return lint_input


def build_ontology_semantic_lint_report(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    context_pack: dict[str, Any],
    lint_input: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    require_ontology_semantic_context_pack(context_pack)
    require_ontology_semantic_lint_input(lint_input)
    report_contract = require_object(
        semantic_policy, "semantic_lint_report_contract", "semantic_control_policy"
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    detected_terms = lint_input.get("detected_terms")
    if not isinstance(detected_terms, list) or not detected_terms:
        raise ValueError("lint_input.detected_terms must be a non-empty list")

    accepted_by_ref: dict[str, dict[str, Any]] = {}
    for section in ("accepted_terms", "accepted_relations"):
        entries = context_pack.get(section)
        if not isinstance(entries, list):
            raise ValueError(f"context_pack.{section} must be a list")
        for index, raw_entry in enumerate(entries):
            if not isinstance(raw_entry, dict):
                raise ValueError(f"context_pack.{section}[{index}] must be an object")
            source_ref = require_string(raw_entry, "source_ref", f"context_pack.{section}[{index}]")
            accepted_by_ref[source_ref] = copy_json_object(raw_entry)

    raw_gaps = context_pack.get("unresolved_gaps")
    if not isinstance(raw_gaps, list):
        raise ValueError("context_pack.unresolved_gaps must be a list")
    gap_by_ref = {
        str(gap.get("missing_concept", {}).get("ref", "")).strip(): copy_json_object(gap)
        for gap in raw_gaps
        if isinstance(gap, dict) and isinstance(gap.get("missing_concept"), dict)
    }

    term_results, statuses, classification_counts = build_semantic_term_results(
        semantic_policy,
        detected_terms=detected_terms,
        detected_terms_context="lint_input.detected_terms",
        accepted_by_ref=accepted_by_ref,
        gap_by_ref=gap_by_ref,
    )
    summary_status = semantic_summary_status(statuses, semantic_policy)
    blocking_findings = [
        copy_json_object(finding)
        for finding in term_results
        if str(finding.get("status", "")).startswith("blocked_")
    ]
    review_required_findings = [
        copy_json_object(finding)
        for finding in term_results
        if str(finding.get("status", "")).startswith("review_required_")
    ]
    candidate_delta_terms = []
    for finding in term_results:
        if finding.get("classification") != "unknown_term":
            continue
        gap = finding.get("gap")
        if not isinstance(gap, dict):
            continue
        missing_concept = gap.get("missing_concept")
        if not isinstance(missing_concept, dict):
            continue
        candidate_delta_terms.append(
            {
                "term": finding["term"],
                "source_ref": finding.get("source_ref"),
                "missing_concept": copy_json_object(missing_concept),
                "gap_id": gap.get("gap_id"),
                "recommended_route": gap.get("recommended_route"),
                "suggested_action": finding["suggested_action"],
            }
        )

    action_terms: dict[str, list[str]] = {}
    for finding in term_results:
        action = str(finding.get("suggested_action", "")).strip()
        if not action:
            continue
        action_terms.setdefault(action, []).append(str(finding["term"]))
    recommended_actions = [
        {
            "action": action,
            "term_count": len(terms),
            "terms": terms,
        }
        for action, terms in sorted(action_terms.items())
    ]

    return {
        "artifact_kind": require_string(
            report_contract,
            "artifact_kind",
            "semantic_control_policy.semantic_lint_report_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0105",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_context_pack": require_layout_path(semantic_layout, "semantic_context_pack"),
        "source_lint_input": require_surface_output_artifact(lint_input, "semantic_lint_input"),
        "context_pack_summary": copy_json_object(
            require_object(context_pack, "summary", "context_pack")
        ),
        "lint_input_summary": copy_json_object(require_object(lint_input, "summary", "lint_input")),
        "target": copy_json_object(
            require_object(
                report_contract, "target", "semantic_control_policy.semantic_lint_report_contract"
            )
        ),
        "input": {
            "artifact": require_surface_output_artifact(lint_input, "semantic_lint_input"),
            "detection_mode": require_string(
                require_object(lint_input, "extraction_summary", "lint_input"),
                "mode",
                "lint_input.extraction_summary",
            ),
            "source_outputs": [
                {
                    "source_id": require_string(
                        source_output, "source_id", "lint_input.source_outputs"
                    ),
                    "source_kind": require_string(
                        source_output, "source_kind", "lint_input.source_outputs"
                    ),
                    "path": require_string(source_output, "path", "lint_input.source_outputs"),
                    "text_sha256": require_string(
                        source_output, "text_sha256", "lint_input.source_outputs"
                    ),
                }
                for source_output in lint_input["source_outputs"]
                if isinstance(source_output, dict)
            ],
            "detected_term_count": len(term_results),
        },
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "findings": term_results,
        "blocking_findings": blocking_findings,
        "review_required_findings": review_required_findings,
        "candidate_delta_terms": candidate_delta_terms,
        "recommended_actions": recommended_actions,
        "consumer_boundary": copy_json_object(
            require_object(
                report_contract,
                "consumer_boundary",
                "semantic_control_policy.semantic_lint_report_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": summary_status,
            "finding_count": len(term_results),
            "classification_counts": {
                key: value for key, value in sorted(classification_counts.items()) if value
            },
            "review_required_count": len(review_required_findings),
            "blocking_count": len(blocking_findings),
            "candidate_delta_count": len(candidate_delta_terms),
            "next_review_gap": semantic_next_gap(summary_status, semantic_policy),
            "next_gap": require_string(
                report_contract,
                "next_gap",
                "semantic_control_policy.semantic_lint_report_contract",
            ),
        },
        "output_artifact": require_layout_path(semantic_layout, "semantic_lint_report"),
    }


def require_ontology_semantic_lint_report(lint_report: dict[str, Any]) -> dict[str, Any]:
    if lint_report.get("artifact_kind") != "ontology_semantic_lint_report":
        raise ValueError("lint_report.artifact_kind must be ontology_semantic_lint_report")
    if require_int(lint_report, "schema_version", "lint_report") != 1:
        raise ValueError("lint_report.schema_version must be 1")
    if require_string(lint_report, "proposal_id", "lint_report") != "0105":
        raise ValueError("lint_report.proposal_id must be 0105")
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if require_bool(lint_report, field, "lint_report") is not False:
            raise ValueError(f"lint_report.{field} must be false")
    boundary = require_object(lint_report, "authority_boundary", "lint_report")
    if require_bool(boundary, "lint_report_is_authority", "lint_report.authority_boundary"):
        raise ValueError("lint_report.authority_boundary.lint_report_is_authority must be false")
    require_string(lint_report, "source_lint_input", "lint_report")
    consumer_boundary = require_object(lint_report, "consumer_boundary", "lint_report")
    for field in (
        "may_execute_prompt_agent",
        "may_mutate_canonical_specs",
        "may_write_ontology_delta",
    ):
        if require_bool(consumer_boundary, field, "lint_report.consumer_boundary") is not False:
            raise ValueError(f"lint_report.consumer_boundary.{field} must be false")
    return lint_report


def build_ontology_delta_candidate_review_packet(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    lint_report: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    require_ontology_semantic_lint_report(lint_report)
    delta_contract = require_object(
        semantic_policy,
        "ontology_delta_candidate_review_packet_contract",
        "semantic_control_policy",
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    candidate_source = require_string(
        delta_contract,
        "candidate_source",
        "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
    )
    raw_candidates = lint_report.get(candidate_source)
    if not isinstance(raw_candidates, list):
        raise ValueError(f"lint_report.{candidate_source} must be a list")

    candidates = []
    for index, raw_candidate in enumerate(raw_candidates):
        if not isinstance(raw_candidate, dict):
            raise ValueError(f"lint_report.{candidate_source}[{index}] must be an object")
        term = require_string(raw_candidate, "term", f"lint_report.{candidate_source}[{index}]")
        missing_concept = require_object(
            raw_candidate, "missing_concept", f"lint_report.{candidate_source}[{index}]"
        )
        missing_ref = require_string(
            missing_concept,
            "ref",
            f"lint_report.{candidate_source}[{index}].missing_concept",
        )
        namespace_hint = require_string(
            missing_concept,
            "namespace_hint",
            f"lint_report.{candidate_source}[{index}].missing_concept",
        )
        concept_hint = require_string(
            missing_concept,
            "concept_hint",
            f"lint_report.{candidate_source}[{index}].missing_concept",
        )
        candidates.append(
            {
                "candidate_id": f"ontology-delta-candidate-{symbol_slug(missing_ref)}",
                "term": term,
                "source_ref": raw_candidate.get("source_ref"),
                "missing_concept": copy_json_object(missing_concept),
                "gap_id": raw_candidate.get("gap_id"),
                "recommended_route": raw_candidate.get("recommended_route"),
                "source_lint_action": raw_candidate.get("suggested_action"),
                "proposed_delta": {
                    "operation": "draft_ontology_concept",
                    "ref": missing_ref,
                    "namespace": namespace_hint,
                    "symbol": concept_hint,
                    "source": "ontology_semantic_lint_report_candidate",
                },
                "review_state": "needs_ontology_owner_review",
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            }
        )

    review_action_effects = {
        "approve_for_ontology_package_draft": "route_candidate_to_ontology_owner_package_draft",
        "reject_candidate": "close_candidate_without_delta",
        "request_clarification": "return_to_semantic_review_with_question",
    }
    review_actions = []
    for action in require_string_list(
        delta_contract,
        "review_actions",
        "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
    ):
        effect = review_action_effects.get(action)
        if effect is None:
            raise ValueError(
                "semantic_control_policy.ontology_delta_candidate_review_packet_contract."
                f"review_actions contains unsupported action {action!r}"
            )
        review_actions.append(
            {
                "action": action,
                "effect": effect,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            }
        )

    return {
        "artifact_kind": require_string(
            delta_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0106",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_lint_report": require_layout_path(semantic_layout, "semantic_lint_report"),
        "target": copy_json_object(
            require_object(
                delta_contract,
                "target",
                "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
            )
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "candidates": candidates,
        "review_actions": review_actions,
        "consumer_boundary": copy_json_object(
            require_object(
                delta_contract,
                "consumer_boundary",
                "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": "review_required" if candidates else "no_candidates",
            "candidate_count": len(candidates),
            "source_lint_status": require_object(lint_report, "summary", "lint_report").get(
                "status"
            ),
            "blocking_count": require_object(lint_report, "summary", "lint_report").get(
                "blocking_count"
            ),
            "next_gap": require_string(
                delta_contract,
                "next_gap",
                "semantic_control_policy.ontology_delta_candidate_review_packet_contract",
            ),
        },
        "output_artifact": require_layout_path(
            semantic_layout, "ontology_delta_candidate_review_packet"
        ),
    }


def require_ontology_delta_candidate_review_packet(
    review_packet: dict[str, Any],
) -> dict[str, Any]:
    if review_packet.get("artifact_kind") != "ontology_delta_candidate_review_packet":
        raise ValueError(
            "review_packet.artifact_kind must be ontology_delta_candidate_review_packet"
        )
    if require_int(review_packet, "schema_version", "review_packet") != 1:
        raise ValueError("review_packet.schema_version must be 1")
    if require_string(review_packet, "proposal_id", "review_packet") != "0106":
        raise ValueError("review_packet.proposal_id must be 0106")
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if require_bool(review_packet, field, "review_packet") is not False:
            raise ValueError(f"review_packet.{field} must be false")
    boundary = require_object(review_packet, "authority_boundary", "review_packet")
    if require_bool(
        boundary,
        "ontology_delta_candidate_is_authority",
        "review_packet.authority_boundary",
    ):
        raise ValueError(
            "review_packet.authority_boundary.ontology_delta_candidate_is_authority must be false"
        )
    consumer_boundary = require_object(review_packet, "consumer_boundary", "review_packet")
    for field in (
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
    ):
        if require_bool(consumer_boundary, field, "review_packet.consumer_boundary") is not False:
            raise ValueError(f"review_packet.consumer_boundary.{field} must be false")
    return review_packet


def semantic_review_finding_items(
    lint_report: dict[str, Any],
    field: str,
    *,
    review_state: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_findings = lint_report.get(field)
    if not isinstance(raw_findings, list):
        raise ValueError(f"lint_report.{field} must be a list")
    findings: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    for index, raw_finding in enumerate(raw_findings):
        if not isinstance(raw_finding, dict):
            raise ValueError(f"lint_report.{field}[{index}] must be an object")
        term = require_string(raw_finding, "term", f"lint_report.{field}[{index}]")
        classification = require_string(
            raw_finding,
            "classification",
            f"lint_report.{field}[{index}]",
        )
        status = require_string(raw_finding, "status", f"lint_report.{field}[{index}]")
        suggested_action = require_string(
            raw_finding,
            "suggested_action",
            f"lint_report.{field}[{index}]",
        )
        payload = copy_json_object(raw_finding)
        findings.append(payload)
        review_items.append(
            {
                "item_id": f"semantic-finding-{symbol_slug(term)}",
                "item_kind": "semantic_finding",
                "review_state": review_state,
                "source": f"ontology_semantic_lint_report.{field}",
                "term": term,
                "classification": classification,
                "status": status,
                "suggested_action": suggested_action,
                "payload": payload,
            }
        )
    return findings, review_items


def build_ontology_semantic_review_surface(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    context_pack: dict[str, Any],
    lint_report: dict[str, Any],
    review_packet: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    require_ontology_semantic_context_pack(context_pack)
    require_ontology_semantic_lint_report(lint_report)
    require_ontology_delta_candidate_review_packet(review_packet)

    review_surface_contract = require_object(
        semantic_policy, "semantic_review_surface_contract", "semantic_control_policy"
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    allowed_actions = set(
        require_string_list(
            review_surface_contract,
            "review_actions",
            "semantic_control_policy.semantic_review_surface_contract",
        )
    )

    blocking_findings, blocking_items = semantic_review_finding_items(
        lint_report, "blocking_findings", review_state="blocked"
    )
    review_required_findings, review_required_items = semantic_review_finding_items(
        lint_report, "review_required_findings", review_state="needs_review"
    )

    raw_candidates = review_packet.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError("review_packet.candidates must be a list")
    delta_candidates: list[dict[str, Any]] = []
    candidate_items: list[dict[str, Any]] = []
    packet_review_action_names = []
    raw_packet_actions = review_packet.get("review_actions")
    if not isinstance(raw_packet_actions, list):
        raise ValueError("review_packet.review_actions must be a list")
    for index, raw_action in enumerate(raw_packet_actions):
        if not isinstance(raw_action, dict):
            raise ValueError(f"review_packet.review_actions[{index}] must be an object")
        action = require_string(raw_action, "action", f"review_packet.review_actions[{index}]")
        if action not in allowed_actions:
            raise ValueError(
                "review_packet.review_actions contains action not declared by "
                f"semantic_review_surface_contract: {action}"
            )
        packet_review_action_names.append(action)

    for index, raw_candidate in enumerate(raw_candidates):
        if not isinstance(raw_candidate, dict):
            raise ValueError(f"review_packet.candidates[{index}] must be an object")
        candidate_id = require_string(
            raw_candidate,
            "candidate_id",
            f"review_packet.candidates[{index}]",
        )
        term = require_string(raw_candidate, "term", f"review_packet.candidates[{index}]")
        review_state = require_string(
            raw_candidate,
            "review_state",
            f"review_packet.candidates[{index}]",
        )
        payload = copy_json_object(raw_candidate)
        delta_candidates.append(payload)
        candidate_items.append(
            {
                "item_id": candidate_id,
                "item_kind": "ontology_delta_candidate",
                "review_state": review_state,
                "source": "ontology_delta_candidate_review_packet.candidates",
                "term": term,
                "suggested_actions": packet_review_action_names,
                "payload": payload,
            }
        )

    review_actions = []
    raw_lint_actions = lint_report.get("recommended_actions")
    if not isinstance(raw_lint_actions, list):
        raise ValueError("lint_report.recommended_actions must be a list")
    for index, raw_action in enumerate(raw_lint_actions):
        if not isinstance(raw_action, dict):
            raise ValueError(f"lint_report.recommended_actions[{index}] must be an object")
        action = require_string(
            raw_action,
            "action",
            f"lint_report.recommended_actions[{index}]",
        )
        if action not in allowed_actions:
            continue
        review_actions.append(
            {
                "action": action,
                "source": "ontology_semantic_lint_report.recommended_actions",
                "term_count": require_int(
                    raw_action,
                    "term_count",
                    f"lint_report.recommended_actions[{index}]",
                ),
                "terms": require_string_list(
                    raw_action,
                    "terms",
                    f"lint_report.recommended_actions[{index}]",
                ),
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            }
        )
    for index, raw_action in enumerate(raw_packet_actions):
        assert isinstance(raw_action, dict)
        action = require_string(raw_action, "action", f"review_packet.review_actions[{index}]")
        writes_ontology_package = require_bool(
            raw_action,
            "writes_ontology_package",
            f"review_packet.review_actions[{index}]",
        )
        mutates_canonical_specs = require_bool(
            raw_action,
            "mutates_canonical_specs",
            f"review_packet.review_actions[{index}]",
        )
        if writes_ontology_package:
            raise ValueError(
                f"review_packet.review_actions[{index}].writes_ontology_package must be false"
            )
        if mutates_canonical_specs:
            raise ValueError(
                f"review_packet.review_actions[{index}].mutates_canonical_specs must be false"
            )
        review_actions.append(
            {
                "action": action,
                "source": "ontology_delta_candidate_review_packet.review_actions",
                "effect": require_string(
                    raw_action,
                    "effect",
                    f"review_packet.review_actions[{index}]",
                ),
                "candidate_count": len(delta_candidates),
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            }
        )

    context_summary = require_object(context_pack, "summary", "context_pack")
    lint_summary = require_object(lint_report, "summary", "lint_report")
    packet_summary = require_object(review_packet, "summary", "review_packet")
    review_items = blocking_items + review_required_items + candidate_items
    return {
        "artifact_kind": require_string(
            review_surface_contract,
            "artifact_kind",
            "semantic_control_policy.semantic_review_surface_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0108",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_artifacts": {
            "semantic_context_pack": require_surface_output_artifact(
                context_pack, "semantic_context_pack"
            ),
            "semantic_lint_report": require_surface_output_artifact(
                lint_report, "semantic_lint_report"
            ),
            "ontology_delta_candidate_review_packet": require_surface_output_artifact(
                review_packet, "ontology_delta_candidate_review_packet"
            ),
        },
        "target": copy_json_object(
            require_object(
                review_surface_contract,
                "target",
                "semantic_control_policy.semantic_review_surface_contract",
            )
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "grounding_summary": {
            "source_context_status": require_string(
                context_summary, "status", "context_pack.summary"
            ),
            "source_lint_status": require_string(lint_summary, "status", "lint_report.summary"),
            "source_delta_candidate_status": require_string(
                packet_summary, "status", "review_packet.summary"
            ),
            "package_count": require_int(context_summary, "package_count", "context_pack.summary"),
            "accepted_term_count": require_int(
                context_summary, "accepted_term_count", "context_pack.summary"
            ),
            "accepted_relation_count": require_int(
                context_summary, "accepted_relation_count", "context_pack.summary"
            ),
            "alias_count": require_int(context_summary, "alias_count", "context_pack.summary"),
            "deprecated_term_count": require_int(
                context_summary, "deprecated_term_count", "context_pack.summary"
            ),
            "relation_conflict_count": require_int(
                context_summary, "relation_conflict_count", "context_pack.summary"
            ),
            "unresolved_gap_count": require_int(
                context_summary, "unresolved_gap_count", "context_pack.summary"
            ),
            "governance_evidence_count": require_int(
                context_summary, "governance_evidence_count", "context_pack.summary"
            ),
        },
        "display_sections": require_string_list(
            review_surface_contract,
            "display_sections",
            "semantic_control_policy.semantic_review_surface_contract",
        ),
        "blocking_findings": blocking_findings,
        "review_required_findings": review_required_findings,
        "delta_candidates": delta_candidates,
        "review_items": review_items,
        "review_actions": review_actions,
        "consumer_boundary": copy_json_object(
            require_object(
                review_surface_contract,
                "consumer_boundary",
                "semantic_control_policy.semantic_review_surface_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": require_string(lint_summary, "status", "lint_report.summary"),
            "blocking_count": require_int(lint_summary, "blocking_count", "lint_report.summary"),
            "review_required_count": require_int(
                lint_summary,
                "review_required_count",
                "lint_report.summary",
            ),
            "candidate_count": require_int(
                packet_summary, "candidate_count", "review_packet.summary"
            ),
            "review_item_count": len(review_items),
            "next_gap": require_string(
                review_surface_contract,
                "next_gap",
                "semantic_control_policy.semantic_review_surface_contract",
            ),
        },
        "output_artifact": require_layout_path(semantic_layout, "semantic_review_surface"),
    }


def require_ontology_semantic_review_surface(
    review_surface: dict[str, Any],
) -> dict[str, Any]:
    if review_surface.get("artifact_kind") != "ontology_semantic_review_surface":
        raise ValueError("review_surface.artifact_kind must be ontology_semantic_review_surface")
    if require_int(review_surface, "schema_version", "review_surface") != 1:
        raise ValueError("review_surface.schema_version must be 1")
    if require_string(review_surface, "proposal_id", "review_surface") != "0108":
        raise ValueError("review_surface.proposal_id must be 0108")
    if require_bool(review_surface, "canonical_mutations_allowed", "review_surface") is not False:
        raise ValueError("review_surface.canonical_mutations_allowed must be false")
    if require_bool(review_surface, "tracked_artifacts_written", "review_surface") is not False:
        raise ValueError("review_surface.tracked_artifacts_written must be false")
    require_surface_output_artifact(review_surface, "semantic_review_surface")
    require_object(review_surface, "source_artifacts", "review_surface")
    require_object(review_surface, "grounding_summary", "review_surface")
    require_object(review_surface, "summary", "review_surface")
    if not isinstance(review_surface.get("review_items"), list):
        raise ValueError("review_surface.review_items must be a list")
    if not isinstance(review_surface.get("review_actions"), list):
        raise ValueError("review_surface.review_actions must be a list")
    consumer_boundary = require_object(review_surface, "consumer_boundary", "review_surface")
    if (
        require_bool(
            consumer_boundary,
            "for_supervisor_gate_evidence",
            "review_surface.consumer_boundary",
        )
        is not True
    ):
        raise ValueError(
            "review_surface.consumer_boundary.for_supervisor_gate_evidence must be true"
        )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
    ):
        if require_bool(consumer_boundary, field, "review_surface.consumer_boundary") is not False:
            raise ValueError(f"review_surface.consumer_boundary.{field} must be false")
    authority_boundary = require_object(review_surface, "authority_boundary", "review_surface")
    for field in (
        "semantic_review_surface_is_authority",
        "supervisor_semantic_gate_is_authority",
        "prompt_agent_execution_allowed",
        "automatic_import_lock_update",
        "automatic_canonical_node_update",
        "canonical_mutations_allowed",
    ):
        if (
            require_bool(authority_boundary, field, "review_surface.authority_boundary")
            is not False
        ):
            raise ValueError(f"review_surface.authority_boundary.{field} must be false")
    return review_surface


def build_ontology_supervisor_semantic_gate(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    review_surface: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    require_ontology_semantic_review_surface(review_surface)

    gate_contract = require_object(
        semantic_policy, "supervisor_semantic_gate_contract", "semantic_control_policy"
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    semantic_review_surface_artifact = require_surface_output_artifact(
        review_surface, "semantic_review_surface"
    )
    supervisor_semantic_gate_artifact = require_layout_path(
        semantic_layout, "supervisor_semantic_gate"
    )
    source_artifacts = copy_json_object(
        require_object(review_surface, "source_artifacts", "review_surface")
    )
    source_artifacts["semantic_review_surface"] = semantic_review_surface_artifact
    summary = require_object(review_surface, "summary", "review_surface")
    review_items = review_surface["review_items"]
    assert isinstance(review_items, list)

    blocking_states = set(
        require_string_list(
            gate_contract,
            "blocking_review_states",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        )
    )
    review_states = set(
        require_string_list(
            gate_contract,
            "review_required_states",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        )
    )
    blocking_item_ids: list[str] = []
    review_required_item_ids: list[str] = []
    candidate_item_ids: list[str] = []
    for index, raw_item in enumerate(review_items):
        if not isinstance(raw_item, dict):
            raise ValueError(f"review_surface.review_items[{index}] must be an object")
        item_id = require_string(raw_item, "item_id", f"review_surface.review_items[{index}]")
        review_state = require_string(
            raw_item, "review_state", f"review_surface.review_items[{index}]"
        )
        item_kind = require_string(raw_item, "item_kind", f"review_surface.review_items[{index}]")
        if review_state in blocking_states:
            blocking_item_ids.append(item_id)
        elif review_state in review_states:
            review_required_item_ids.append(item_id)
        if item_kind == "ontology_delta_candidate":
            candidate_item_ids.append(item_id)

    blocking_count = require_int(summary, "blocking_count", "review_surface.summary")
    review_required_count = require_int(summary, "review_required_count", "review_surface.summary")
    candidate_count = require_int(summary, "candidate_count", "review_surface.summary")
    if blocking_count != len(blocking_item_ids):
        raise ValueError(
            "review_surface.summary.blocking_count must match blocking review item count"
        )
    if blocking_count or blocking_item_ids:
        gate_state = "blocked"
        outcome = "semantic_gate_blocked"
        required_human_action = "resolve_blocking_ontology_semantic_findings"
    elif review_required_count or candidate_count or review_required_item_ids:
        gate_state = "review_pending"
        outcome = "semantic_review_pending"
        required_human_action = "review_ontology_semantic_items"
    else:
        gate_state = "clear"
        outcome = "semantic_gate_clear"
        required_human_action = "none"

    gate_states = set(
        require_string_list(
            gate_contract,
            "gate_states",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        )
    )
    if gate_state not in gate_states:
        raise ValueError(
            "semantic_control_policy.supervisor_semantic_gate_contract.gate_states "
            f"does not declare computed gate state {gate_state}"
        )

    invocation_boundary = copy_json_object(
        require_object(
            gate_contract,
            "typed_invocation_boundary",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        )
    )
    invocation_boundary["input_artifact"] = semantic_review_surface_artifact
    invocation_boundary["output_artifact"] = supervisor_semantic_gate_artifact
    return {
        "artifact_kind": require_string(
            gate_contract,
            "artifact_kind",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0109",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_artifacts": source_artifacts,
        "target": copy_json_object(
            require_object(
                gate_contract,
                "target",
                "semantic_control_policy.supervisor_semantic_gate_contract",
            )
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "typed_invocation_boundary": invocation_boundary,
        "gate": {
            "gate_state": gate_state,
            "outcome": outcome,
            "required_human_action": required_human_action,
            "blocking_item_ids": blocking_item_ids,
            "review_required_item_ids": review_required_item_ids,
            "candidate_item_ids": candidate_item_ids,
        },
        "evidence_refs": {
            "evidence_sections": require_string_list(
                gate_contract,
                "evidence_sections",
                "semantic_control_policy.supervisor_semantic_gate_contract",
            ),
            "source_artifacts": source_artifacts,
            "review_item_ids": [
                require_string(item, "item_id", "review_surface.review_items")
                for item in review_items
                if isinstance(item, dict)
            ],
            "blocking_item_ids": blocking_item_ids,
            "review_required_item_ids": review_required_item_ids,
            "candidate_item_ids": candidate_item_ids,
        },
        "failure_modes": require_string_list(
            gate_contract,
            "failure_modes",
            "semantic_control_policy.supervisor_semantic_gate_contract",
        ),
        "consumer_boundary": copy_json_object(
            require_object(
                gate_contract,
                "consumer_boundary",
                "semantic_control_policy.supervisor_semantic_gate_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": gate_state,
            "source_status": require_string(summary, "status", "review_surface.summary"),
            "blocking_count": blocking_count,
            "review_required_count": review_required_count,
            "candidate_count": candidate_count,
            "review_item_count": require_int(
                summary, "review_item_count", "review_surface.summary"
            ),
            "next_gap": require_string(
                gate_contract,
                "next_gap",
                "semantic_control_policy.supervisor_semantic_gate_contract",
            ),
        },
        "output_artifact": supervisor_semantic_gate_artifact,
    }


def require_ontology_supervisor_semantic_gate(
    supervisor_gate: dict[str, Any],
) -> dict[str, Any]:
    if supervisor_gate.get("artifact_kind") != "ontology_supervisor_semantic_gate":
        raise ValueError("supervisor_gate.artifact_kind must be ontology_supervisor_semantic_gate")
    if require_int(supervisor_gate, "schema_version", "supervisor_gate") != 1:
        raise ValueError("supervisor_gate.schema_version must be 1")
    if require_string(supervisor_gate, "proposal_id", "supervisor_gate") != "0109":
        raise ValueError("supervisor_gate.proposal_id must be 0109")
    if require_bool(supervisor_gate, "canonical_mutations_allowed", "supervisor_gate") is not False:
        raise ValueError("supervisor_gate.canonical_mutations_allowed must be false")
    if require_bool(supervisor_gate, "tracked_artifacts_written", "supervisor_gate") is not False:
        raise ValueError("supervisor_gate.tracked_artifacts_written must be false")
    require_surface_output_artifact(supervisor_gate, "supervisor_semantic_gate")
    require_object(supervisor_gate, "source_artifacts", "supervisor_gate")
    gate = require_object(supervisor_gate, "gate", "supervisor_gate")
    gate_state = require_string(gate, "gate_state", "supervisor_gate.gate")
    if gate_state not in {"blocked", "review_pending", "clear"}:
        raise ValueError(
            "supervisor_gate.gate.gate_state must be blocked, review_pending, or clear"
        )
    require_string(gate, "required_human_action", "supervisor_gate.gate")
    for field in ("blocking_item_ids", "review_required_item_ids", "candidate_item_ids"):
        require_string_list(gate, field, "supervisor_gate.gate")
    consumer_boundary = require_object(supervisor_gate, "consumer_boundary", "supervisor_gate")
    if (
        require_bool(
            consumer_boundary,
            "for_supervisor_gate_evidence",
            "supervisor_gate.consumer_boundary",
        )
        is not True
    ):
        raise ValueError(
            "supervisor_gate.consumer_boundary.for_supervisor_gate_evidence must be true"
        )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
    ):
        if require_bool(consumer_boundary, field, "supervisor_gate.consumer_boundary") is not False:
            raise ValueError(f"supervisor_gate.consumer_boundary.{field} must be false")
    authority_boundary = require_object(supervisor_gate, "authority_boundary", "supervisor_gate")
    for field in (
        "supervisor_semantic_gate_is_authority",
        "prompt_agent_execution_allowed",
        "automatic_import_lock_update",
        "automatic_canonical_node_update",
        "canonical_mutations_allowed",
    ):
        if (
            require_bool(authority_boundary, field, "supervisor_gate.authority_boundary")
            is not False
        ):
            raise ValueError(f"supervisor_gate.authority_boundary.{field} must be false")
    return supervisor_gate


def build_ontology_delta_draft_intake(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    review_packet: dict[str, Any],
    supervisor_gate: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    require_ontology_delta_candidate_review_packet(review_packet)
    require_ontology_supervisor_semantic_gate(supervisor_gate)

    intake_contract = require_object(
        semantic_policy, "ontology_delta_draft_intake_contract", "semantic_control_policy"
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    gate = require_object(supervisor_gate, "gate", "supervisor_gate")
    gate_state = require_string(gate, "gate_state", "supervisor_gate.gate")
    blocked_gate_states = set(
        require_string_list(
            intake_contract,
            "blocked_gate_states",
            "semantic_control_policy.ontology_delta_draft_intake_contract",
        )
    )
    review_required_candidate_states = set(
        require_string_list(
            intake_contract,
            "review_required_candidate_states",
            "semantic_control_policy.ontology_delta_draft_intake_contract",
        )
    )
    raw_candidates = review_packet.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError("review_packet.candidates must be a list")

    draft_requests: list[dict[str, Any]] = []
    for index, raw_candidate in enumerate(raw_candidates):
        if not isinstance(raw_candidate, dict):
            raise ValueError(f"review_packet.candidates[{index}] must be an object")
        candidate_id = require_string(
            raw_candidate, "candidate_id", f"review_packet.candidates[{index}]"
        )
        term = require_string(raw_candidate, "term", f"review_packet.candidates[{index}]")
        review_state = require_string(
            raw_candidate, "review_state", f"review_packet.candidates[{index}]"
        )
        if gate_state in blocked_gate_states:
            intake_state = "blocked_by_semantic_gate"
            required_human_action = require_string(
                gate, "required_human_action", "supervisor_gate.gate"
            )
        elif review_state in review_required_candidate_states:
            intake_state = "awaiting_ontology_owner_review"
            required_human_action = "ontology_owner_review_delta_candidate"
        else:
            intake_state = "awaiting_ontology_owner_review"
            required_human_action = "ontology_owner_review_delta_candidate"
        draft_requests.append(
            {
                "intake_id": f"ontology-delta-draft-intake-{symbol_slug(candidate_id)}",
                "candidate_id": candidate_id,
                "term": term,
                "review_state": review_state,
                "intake_state": intake_state,
                "required_human_action": required_human_action,
                "blocked_by_gate_state": gate_state if gate_state in blocked_gate_states else "",
                "blocking_item_ids": require_string_list(
                    gate, "blocking_item_ids", "supervisor_gate.gate"
                ),
                "draft_delta": copy_json_object(
                    require_object(
                        raw_candidate,
                        "proposed_delta",
                        f"review_packet.candidates[{index}]",
                    )
                ),
                "writes_ontology_package": False,
                "updates_ontology_lockfile": False,
                "mutates_canonical_specs": False,
                "marks_candidate_accepted": False,
            }
        )

    if not draft_requests:
        intake_status = "no_candidates"
        required_human_action = "none"
    elif gate_state in blocked_gate_states:
        intake_status = "blocked_by_semantic_gate"
        required_human_action = require_string(
            gate, "required_human_action", "supervisor_gate.gate"
        )
    else:
        intake_status = "awaiting_ontology_owner_review"
        required_human_action = "ontology_owner_review_delta_candidate"
    allowed_intake_states = set(
        require_string_list(
            intake_contract,
            "allowed_intake_states",
            "semantic_control_policy.ontology_delta_draft_intake_contract",
        )
    )
    if intake_status not in allowed_intake_states:
        raise ValueError(
            "semantic_control_policy.ontology_delta_draft_intake_contract."
            f"allowed_intake_states does not declare computed state {intake_status}"
        )

    supervisor_source_artifacts = copy_json_object(
        require_object(supervisor_gate, "source_artifacts", "supervisor_gate")
    )
    source_artifacts = {
        **supervisor_source_artifacts,
        "supervisor_semantic_gate": require_surface_output_artifact(
            supervisor_gate, "supervisor_semantic_gate"
        ),
        "ontology_delta_candidate_review_packet": require_surface_output_artifact(
            review_packet, "ontology_delta_candidate_review_packet"
        ),
    }
    return {
        "artifact_kind": require_string(
            intake_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_delta_draft_intake_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0110",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_artifacts": source_artifacts,
        "target": copy_json_object(
            require_object(
                intake_contract,
                "target",
                "semantic_control_policy.ontology_delta_draft_intake_contract",
            )
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "gate": copy_json_object(gate),
        "draft_requests": draft_requests,
        "consumer_boundary": copy_json_object(
            require_object(
                intake_contract,
                "consumer_boundary",
                "semantic_control_policy.ontology_delta_draft_intake_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": intake_status,
            "gate_state": gate_state,
            "candidate_count": len(raw_candidates),
            "draft_request_count": len(draft_requests),
            "required_human_action": required_human_action,
            "next_gap": require_string(
                intake_contract,
                "next_gap",
                "semantic_control_policy.ontology_delta_draft_intake_contract",
            ),
        },
        "output_artifact": require_layout_path(semantic_layout, "ontology_delta_draft_intake"),
    }


def require_ontology_delta_draft_intake(
    draft_intake: dict[str, Any],
) -> dict[str, Any]:
    if draft_intake.get("artifact_kind") != "ontology_delta_draft_intake":
        raise ValueError("draft_intake.artifact_kind must be ontology_delta_draft_intake")
    if require_int(draft_intake, "schema_version", "draft_intake") != 1:
        raise ValueError("draft_intake.schema_version must be 1")
    if require_string(draft_intake, "proposal_id", "draft_intake") != "0110":
        raise ValueError("draft_intake.proposal_id must be 0110")
    if require_bool(draft_intake, "canonical_mutations_allowed", "draft_intake") is not False:
        raise ValueError("draft_intake.canonical_mutations_allowed must be false")
    if require_bool(draft_intake, "tracked_artifacts_written", "draft_intake") is not False:
        raise ValueError("draft_intake.tracked_artifacts_written must be false")
    require_surface_output_artifact(draft_intake, "ontology_delta_draft_intake")
    require_object(draft_intake, "source_artifacts", "draft_intake")
    require_object(draft_intake, "gate", "draft_intake")
    require_object(draft_intake, "summary", "draft_intake")
    if not isinstance(draft_intake.get("draft_requests"), list):
        raise ValueError("draft_intake.draft_requests must be a list")
    for index, raw_request in enumerate(draft_intake["draft_requests"]):
        if not isinstance(raw_request, dict):
            raise ValueError(f"draft_intake.draft_requests[{index}] must be an object")
        for field in (
            "writes_ontology_package",
            "updates_ontology_lockfile",
            "mutates_canonical_specs",
            "marks_candidate_accepted",
        ):
            if (
                require_bool(raw_request, field, f"draft_intake.draft_requests[{index}]")
                is not False
            ):
                raise ValueError(f"draft_intake.draft_requests[{index}].{field} must be false")
    consumer_boundary = require_object(draft_intake, "consumer_boundary", "draft_intake")
    if (
        require_bool(
            consumer_boundary,
            "for_ontology_owner_draft_intake",
            "draft_intake.consumer_boundary",
        )
        is not True
    ):
        raise ValueError(
            "draft_intake.consumer_boundary.for_ontology_owner_draft_intake must be true"
        )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
    ):
        if require_bool(consumer_boundary, field, "draft_intake.consumer_boundary") is not False:
            raise ValueError(f"draft_intake.consumer_boundary.{field} must be false")
    authority_boundary = require_object(draft_intake, "authority_boundary", "draft_intake")
    for field in (
        "ontology_delta_draft_intake_is_authority",
        "prompt_agent_execution_allowed",
        "automatic_import_lock_update",
        "automatic_canonical_node_update",
        "canonical_mutations_allowed",
    ):
        if require_bool(authority_boundary, field, "draft_intake.authority_boundary") is not False:
            raise ValueError(f"draft_intake.authority_boundary.{field} must be false")
    return draft_intake


def build_ontology_closed_loop_evidence(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    draft_intake: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    require_ontology_delta_draft_intake(draft_intake)

    closed_loop_contract = require_object(
        semantic_policy, "ontology_closed_loop_evidence_contract", "semantic_control_policy"
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    draft_requests = draft_intake["draft_requests"]
    assert isinstance(draft_requests, list)
    source_artifacts = copy_json_object(
        require_object(draft_intake, "source_artifacts", "draft_intake")
    )
    source_artifacts["ontology_delta_draft_intake"] = require_surface_output_artifact(
        draft_intake, "ontology_delta_draft_intake"
    )
    evidence_entries: list[dict[str, Any]] = []
    for index, raw_request in enumerate(draft_requests):
        if not isinstance(raw_request, dict):
            raise ValueError(f"draft_intake.draft_requests[{index}] must be an object")
        intake_id = require_string(
            raw_request, "intake_id", f"draft_intake.draft_requests[{index}]"
        )
        candidate_id = require_string(
            raw_request, "candidate_id", f"draft_intake.draft_requests[{index}]"
        )
        intake_state = require_string(
            raw_request, "intake_state", f"draft_intake.draft_requests[{index}]"
        )
        if intake_state == "blocked_by_semantic_gate":
            evidence_state = "blocked_by_semantic_gate"
            specgraph_review_state = "blocked"
        elif intake_state == "awaiting_ontology_owner_review":
            evidence_state = "pending_ontology_owner_decision"
            specgraph_review_state = "pending_ontology_owner_decision"
        else:
            raise ValueError(
                f"draft_intake.draft_requests[{index}].intake_state must be "
                "blocked_by_semantic_gate or awaiting_ontology_owner_review"
            )
        evidence_entries.append(
            {
                "evidence_id": f"ontology-closed-loop-evidence-{symbol_slug(candidate_id)}",
                "candidate_id": candidate_id,
                "intake_id": intake_id,
                "term": require_string(
                    raw_request, "term", f"draft_intake.draft_requests[{index}]"
                ),
                "source_intake_state": intake_state,
                "evidence_state": evidence_state,
                "specgraph_review_state": specgraph_review_state,
                "required_human_action": require_string(
                    raw_request,
                    "required_human_action",
                    f"draft_intake.draft_requests[{index}]",
                ),
                "ontology_decision_ref": "",
                "accepted_ontology_delta": False,
                "closes_semantic_gate": False,
                "mutates_canonical_specs": False,
                "blocking_item_ids": require_string_list(
                    raw_request,
                    "blocking_item_ids",
                    f"draft_intake.draft_requests[{index}]",
                ),
                "source_artifacts": source_artifacts,
            }
        )

    if not evidence_entries:
        closed_loop_status = "no_candidates"
        required_human_action = "none"
    elif any(entry["evidence_state"] == "blocked_by_semantic_gate" for entry in evidence_entries):
        closed_loop_status = "blocked_by_semantic_gate"
        required_human_action = "resolve_blocking_ontology_semantic_findings"
    else:
        closed_loop_status = "pending_ontology_owner_decision"
        required_human_action = "collect_ontology_owner_delta_decisions"
    evidence_states = set(
        require_string_list(
            closed_loop_contract,
            "evidence_states",
            "semantic_control_policy.ontology_closed_loop_evidence_contract",
        )
    )
    if closed_loop_status not in evidence_states:
        raise ValueError(
            "semantic_control_policy.ontology_closed_loop_evidence_contract."
            f"evidence_states does not declare computed state {closed_loop_status}"
        )
    return {
        "artifact_kind": require_string(
            closed_loop_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_closed_loop_evidence_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0111",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_artifacts": source_artifacts,
        "target": copy_json_object(
            require_object(
                closed_loop_contract,
                "target",
                "semantic_control_policy.ontology_closed_loop_evidence_contract",
            )
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "evidence_entries": evidence_entries,
        "consumer_boundary": copy_json_object(
            require_object(
                closed_loop_contract,
                "consumer_boundary",
                "semantic_control_policy.ontology_closed_loop_evidence_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": closed_loop_status,
            "evidence_entry_count": len(evidence_entries),
            "pending_decision_count": sum(
                1
                for entry in evidence_entries
                if entry["evidence_state"] == "pending_ontology_owner_decision"
            ),
            "blocked_entry_count": sum(
                1
                for entry in evidence_entries
                if entry["evidence_state"] == "blocked_by_semantic_gate"
            ),
            "required_human_action": required_human_action,
            "next_gap": require_string(
                closed_loop_contract,
                "next_gap",
                "semantic_control_policy.ontology_closed_loop_evidence_contract",
            ),
        },
        "output_artifact": require_layout_path(semantic_layout, "ontology_closed_loop_evidence"),
    }


def require_ontology_closed_loop_evidence(
    closed_loop_evidence: dict[str, Any],
) -> dict[str, Any]:
    if closed_loop_evidence.get("artifact_kind") != "ontology_closed_loop_evidence":
        raise ValueError("closed_loop_evidence.artifact_kind must be ontology_closed_loop_evidence")
    if require_int(closed_loop_evidence, "schema_version", "closed_loop_evidence") != 1:
        raise ValueError("closed_loop_evidence.schema_version must be 1")
    if require_string(closed_loop_evidence, "proposal_id", "closed_loop_evidence") != "0111":
        raise ValueError("closed_loop_evidence.proposal_id must be 0111")
    if (
        require_bool(closed_loop_evidence, "canonical_mutations_allowed", "closed_loop_evidence")
        is not False
    ):
        raise ValueError("closed_loop_evidence.canonical_mutations_allowed must be false")
    if (
        require_bool(closed_loop_evidence, "tracked_artifacts_written", "closed_loop_evidence")
        is not False
    ):
        raise ValueError("closed_loop_evidence.tracked_artifacts_written must be false")
    require_surface_output_artifact(closed_loop_evidence, "ontology_closed_loop_evidence")
    require_object(closed_loop_evidence, "source_artifacts", "closed_loop_evidence")
    require_object(closed_loop_evidence, "summary", "closed_loop_evidence")
    evidence_entries = closed_loop_evidence.get("evidence_entries")
    if not isinstance(evidence_entries, list):
        raise ValueError("closed_loop_evidence.evidence_entries must be a list")
    for index, raw_entry in enumerate(evidence_entries):
        if not isinstance(raw_entry, dict):
            raise ValueError(f"closed_loop_evidence.evidence_entries[{index}] must be an object")
        for field in (
            "accepted_ontology_delta",
            "closes_semantic_gate",
            "mutates_canonical_specs",
        ):
            if (
                require_bool(
                    raw_entry,
                    field,
                    f"closed_loop_evidence.evidence_entries[{index}]",
                )
                is not False
            ):
                raise ValueError(
                    f"closed_loop_evidence.evidence_entries[{index}].{field} must be false"
                )
    consumer_boundary = require_object(
        closed_loop_evidence, "consumer_boundary", "closed_loop_evidence"
    )
    if (
        require_bool(
            consumer_boundary,
            "for_specgraph_evidence_review",
            "closed_loop_evidence.consumer_boundary",
        )
        is not True
    ):
        raise ValueError(
            "closed_loop_evidence.consumer_boundary.for_specgraph_evidence_review must be true"
        )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_close_semantic_gate",
    ):
        if (
            require_bool(consumer_boundary, field, "closed_loop_evidence.consumer_boundary")
            is not False
        ):
            raise ValueError(f"closed_loop_evidence.consumer_boundary.{field} must be false")
    authority_boundary = require_object(
        closed_loop_evidence, "authority_boundary", "closed_loop_evidence"
    )
    for field in (
        "ontology_closed_loop_evidence_is_authority",
        "prompt_agent_execution_allowed",
        "automatic_import_lock_update",
        "automatic_canonical_node_update",
        "canonical_mutations_allowed",
    ):
        if (
            require_bool(authority_boundary, field, "closed_loop_evidence.authority_boundary")
            is not False
        ):
            raise ValueError(f"closed_loop_evidence.authority_boundary.{field} must be false")
    return closed_loop_evidence


def build_ontology_review_dashboard(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    review_surface: dict[str, Any],
    supervisor_gate: dict[str, Any],
    draft_intake: dict[str, Any],
    closed_loop_evidence: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    require_ontology_semantic_review_surface(review_surface)
    require_ontology_supervisor_semantic_gate(supervisor_gate)
    require_ontology_delta_draft_intake(draft_intake)
    require_ontology_closed_loop_evidence(closed_loop_evidence)

    dashboard_contract = require_object(
        semantic_policy, "ontology_review_dashboard_contract", "semantic_control_policy"
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    semantic_review_surface_artifact = require_surface_output_artifact(
        review_surface, "semantic_review_surface"
    )
    supervisor_semantic_gate_artifact = require_surface_output_artifact(
        supervisor_gate, "supervisor_semantic_gate"
    )
    ontology_delta_draft_intake_artifact = require_surface_output_artifact(
        draft_intake, "ontology_delta_draft_intake"
    )
    ontology_closed_loop_evidence_artifact = require_surface_output_artifact(
        closed_loop_evidence, "ontology_closed_loop_evidence"
    )

    supervisor_sources = require_object(supervisor_gate, "source_artifacts", "supervisor_gate")
    if supervisor_sources.get("semantic_review_surface") != semantic_review_surface_artifact:
        raise ValueError(
            "supervisor_gate.source_artifacts.semantic_review_surface must match "
            "review_surface.output_artifact"
        )
    draft_sources = require_object(draft_intake, "source_artifacts", "draft_intake")
    if draft_sources.get("supervisor_semantic_gate") != supervisor_semantic_gate_artifact:
        raise ValueError(
            "draft_intake.source_artifacts.supervisor_semantic_gate must match "
            "supervisor_gate.output_artifact"
        )
    evidence_sources = require_object(
        closed_loop_evidence, "source_artifacts", "closed_loop_evidence"
    )
    if evidence_sources.get("ontology_delta_draft_intake") != ontology_delta_draft_intake_artifact:
        raise ValueError(
            "closed_loop_evidence.source_artifacts.ontology_delta_draft_intake must match "
            "draft_intake.output_artifact"
        )

    source_artifacts = copy_json_object(
        require_object(closed_loop_evidence, "source_artifacts", "closed_loop_evidence")
    )
    source_artifacts["semantic_review_surface"] = semantic_review_surface_artifact
    source_artifacts["supervisor_semantic_gate"] = supervisor_semantic_gate_artifact
    source_artifacts["ontology_delta_draft_intake"] = ontology_delta_draft_intake_artifact
    source_artifacts["ontology_closed_loop_evidence"] = ontology_closed_loop_evidence_artifact

    gate = require_object(supervisor_gate, "gate", "supervisor_gate")
    review_summary = require_object(review_surface, "summary", "review_surface")
    intake_summary = require_object(draft_intake, "summary", "draft_intake")
    closed_loop_summary = require_object(closed_loop_evidence, "summary", "closed_loop_evidence")
    gate_state = require_string(gate, "gate_state", "supervisor_gate.gate")
    closed_loop_status = require_string(
        closed_loop_summary, "status", "closed_loop_evidence.summary"
    )
    if gate_state == "blocked" or closed_loop_status == "blocked_by_semantic_gate":
        dashboard_status = "blocked_by_semantic_gate"
    elif closed_loop_status == "pending_ontology_owner_decision":
        dashboard_status = "pending_ontology_owner_decision"
    elif gate_state == "review_pending":
        dashboard_status = "review_pending"
    elif closed_loop_status == "no_candidates":
        dashboard_status = "no_candidates"
    else:
        dashboard_status = "clear"
    status_states = set(
        require_string_list(
            dashboard_contract,
            "status_states",
            "semantic_control_policy.ontology_review_dashboard_contract",
        )
    )
    if dashboard_status not in status_states:
        raise ValueError(
            "semantic_control_policy.ontology_review_dashboard_contract.status_states "
            f"does not declare computed state {dashboard_status}"
        )

    review_items = review_surface.get("review_items")
    if not isinstance(review_items, list):
        raise ValueError("review_surface.review_items must be a list")
    review_items_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_item in enumerate(review_items):
        if not isinstance(raw_item, dict):
            raise ValueError(f"review_surface.review_items[{index}] must be an object")
        item_id = require_string(raw_item, "item_id", f"review_surface.review_items[{index}]")
        review_items_by_id[item_id] = raw_item

    blocking_item_ids = require_string_list(gate, "blocking_item_ids", "supervisor_gate.gate")
    review_required_item_ids = require_string_list(
        gate, "review_required_item_ids", "supervisor_gate.gate"
    )
    missing_blocking_item_ids = sorted(set(blocking_item_ids) - set(review_items_by_id))
    if missing_blocking_item_ids:
        raise ValueError(
            "supervisor_gate.gate.blocking_item_ids missing from review_surface.review_items: "
            f"{', '.join(missing_blocking_item_ids)}"
        )
    missing_review_required_item_ids = sorted(
        set(review_required_item_ids) - set(review_items_by_id)
    )
    if missing_review_required_item_ids:
        raise ValueError(
            "supervisor_gate.gate.review_required_item_ids missing from "
            f"review_surface.review_items: {', '.join(missing_review_required_item_ids)}"
        )
    blocking_items = [
        copy_json_object(review_items_by_id[item_id]) for item_id in blocking_item_ids
    ]
    review_required_items = [
        copy_json_object(review_items_by_id[item_id]) for item_id in review_required_item_ids
    ]

    delta_candidates = review_surface.get("delta_candidates")
    if not isinstance(delta_candidates, list):
        raise ValueError("review_surface.delta_candidates must be a list")
    draft_requests = draft_intake.get("draft_requests")
    if not isinstance(draft_requests, list):
        raise ValueError("draft_intake.draft_requests must be a list")
    evidence_entries = closed_loop_evidence.get("evidence_entries")
    if not isinstance(evidence_entries, list):
        raise ValueError("closed_loop_evidence.evidence_entries must be a list")
    review_actions = review_surface.get("review_actions")
    if not isinstance(review_actions, list):
        raise ValueError("review_surface.review_actions must be a list")

    if gate_state in {"blocked", "review_pending"}:
        required_human_action = require_string(
            gate, "required_human_action", "supervisor_gate.gate"
        )
    else:
        required_human_action = require_string(
            closed_loop_summary, "required_human_action", "closed_loop_evidence.summary"
        )

    return {
        "artifact_kind": require_string(
            dashboard_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_review_dashboard_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0113",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_artifacts": source_artifacts,
        "target": copy_json_object(
            require_object(
                dashboard_contract,
                "target",
                "semantic_control_policy.ontology_review_dashboard_contract",
            )
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "dashboard_sections": require_string_list(
            dashboard_contract,
            "dashboard_sections",
            "semantic_control_policy.ontology_review_dashboard_contract",
        ),
        "status_summary": {
            "status": dashboard_status,
            "gate_state": gate_state,
            "review_surface_status": require_string(
                review_summary, "status", "review_surface.summary"
            ),
            "intake_status": require_string(intake_summary, "status", "draft_intake.summary"),
            "closed_loop_status": closed_loop_status,
            "blocking_count": require_int(
                review_summary, "blocking_count", "review_surface.summary"
            ),
            "review_required_count": require_int(
                review_summary, "review_required_count", "review_surface.summary"
            ),
            "candidate_count": require_int(
                review_summary, "candidate_count", "review_surface.summary"
            ),
            "draft_request_count": require_int(
                intake_summary, "draft_request_count", "draft_intake.summary"
            ),
            "evidence_entry_count": require_int(
                closed_loop_summary, "evidence_entry_count", "closed_loop_evidence.summary"
            ),
            "pending_decision_count": require_int(
                closed_loop_summary, "pending_decision_count", "closed_loop_evidence.summary"
            ),
            "blocked_entry_count": require_int(
                closed_loop_summary, "blocked_entry_count", "closed_loop_evidence.summary"
            ),
            "required_human_action": required_human_action,
            "next_gap": require_string(
                dashboard_contract,
                "next_gap",
                "semantic_control_policy.ontology_review_dashboard_contract",
            ),
        },
        "gate": copy_json_object(gate),
        "blocking_items": blocking_items,
        "review_required_items": review_required_items,
        "delta_candidates": [
            copy_json_object(candidate)
            for candidate in delta_candidates
            if isinstance(candidate, dict)
        ],
        "draft_requests": [
            copy_json_object(request) for request in draft_requests if isinstance(request, dict)
        ],
        "closed_loop_entries": [
            copy_json_object(entry) for entry in evidence_entries if isinstance(entry, dict)
        ],
        "review_actions": [
            copy_json_object(action) for action in review_actions if isinstance(action, dict)
        ],
        "consumer_boundary": copy_json_object(
            require_object(
                dashboard_contract,
                "consumer_boundary",
                "semantic_control_policy.ontology_review_dashboard_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "output_artifact": require_layout_path(semantic_layout, "ontology_review_dashboard"),
    }


def require_ontology_review_dashboard(
    dashboard: dict[str, Any],
) -> dict[str, Any]:
    if dashboard.get("artifact_kind") != "ontology_review_dashboard":
        raise ValueError("dashboard.artifact_kind must be ontology_review_dashboard")
    if require_int(dashboard, "schema_version", "dashboard") != 1:
        raise ValueError("dashboard.schema_version must be 1")
    if require_string(dashboard, "proposal_id", "dashboard") != "0113":
        raise ValueError("dashboard.proposal_id must be 0113")
    if require_bool(dashboard, "canonical_mutations_allowed", "dashboard") is not False:
        raise ValueError("dashboard.canonical_mutations_allowed must be false")
    if require_bool(dashboard, "tracked_artifacts_written", "dashboard") is not False:
        raise ValueError("dashboard.tracked_artifacts_written must be false")
    require_surface_output_artifact(dashboard, "ontology_review_dashboard")
    require_object(dashboard, "source_artifacts", "dashboard")
    status_summary = require_object(dashboard, "status_summary", "dashboard")
    status = require_string(status_summary, "status", "dashboard.status_summary")
    if status not in {
        "blocked_by_semantic_gate",
        "pending_ontology_owner_decision",
        "review_pending",
        "clear",
        "no_candidates",
    }:
        raise ValueError("dashboard.status_summary.status is not a supported dashboard state")
    for field in (
        "blocking_items",
        "review_required_items",
        "delta_candidates",
        "draft_requests",
        "closed_loop_entries",
        "review_actions",
    ):
        if not isinstance(dashboard.get(field), list):
            raise ValueError(f"dashboard.{field} must be a list")
    consumer_boundary = require_object(dashboard, "consumer_boundary", "dashboard")
    for field in ("for_specgraph_review_dashboard", "for_specspace_review_dashboard"):
        if require_bool(consumer_boundary, field, "dashboard.consumer_boundary") is not True:
            raise ValueError(f"dashboard.consumer_boundary.{field} must be true")
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_import_owner_decision",
        "may_close_semantic_gate",
    ):
        if require_bool(consumer_boundary, field, "dashboard.consumer_boundary") is not False:
            raise ValueError(f"dashboard.consumer_boundary.{field} must be false")
    authority_boundary = require_object(dashboard, "authority_boundary", "dashboard")
    for field in (
        "ontology_review_dashboard_is_authority",
        "prompt_agent_execution_allowed",
        "automatic_import_lock_update",
        "automatic_canonical_node_update",
        "canonical_mutations_allowed",
    ):
        if require_bool(authority_boundary, field, "dashboard.authority_boundary") is not False:
            raise ValueError(f"dashboard.authority_boundary.{field} must be false")
    return dashboard


def build_ontology_owner_decision_report(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    closed_loop_evidence: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    require_ontology_closed_loop_evidence(closed_loop_evidence)

    owner_decision_contract = require_object(
        semantic_policy, "ontology_owner_decision_report_contract", "semantic_control_policy"
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    owner_decision_fixture = require_object(
        semantic_policy, "owner_decision_fixture", "semantic_control_policy"
    )
    raw_decisions = owner_decision_fixture.get("decisions")
    if not isinstance(raw_decisions, list):
        raise ValueError("semantic_control_policy.owner_decision_fixture.decisions must be a list")

    decision_states = set(
        require_string_list(
            owner_decision_contract,
            "decision_states",
            "semantic_control_policy.ontology_owner_decision_report_contract",
        )
    )
    evidence_entries = closed_loop_evidence.get("evidence_entries")
    if not isinstance(evidence_entries, list):
        raise ValueError("closed_loop_evidence.evidence_entries must be a list")
    closed_loop_by_decision_key: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw_entry in enumerate(evidence_entries):
        if not isinstance(raw_entry, dict):
            raise ValueError(f"closed_loop_evidence.evidence_entries[{index}] must be an object")
        candidate_id = require_string(
            raw_entry, "candidate_id", f"closed_loop_evidence.evidence_entries[{index}]"
        )
        intake_id = require_string(
            raw_entry, "intake_id", f"closed_loop_evidence.evidence_entries[{index}]"
        )
        closed_loop_by_decision_key[(candidate_id, intake_id)] = raw_entry

    decisions: list[dict[str, Any]] = []
    ignored_decisions: list[dict[str, Any]] = []
    for index, raw_decision in enumerate(raw_decisions):
        if not isinstance(raw_decision, dict):
            raise ValueError(
                f"semantic_control_policy.owner_decision_fixture.decisions[{index}] "
                "must be an object"
            )
        decision_state = require_string(
            raw_decision,
            "decision_state",
            f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
        )
        if decision_state not in decision_states:
            raise ValueError(
                "semantic_control_policy.owner_decision_fixture.decisions"
                f"[{index}].decision_state must be declared by decision_states"
            )
        accepted_ontology_delta = require_bool(
            raw_decision,
            "accepted_ontology_delta",
            f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
        )
        if accepted_ontology_delta != (decision_state == "accepted"):
            raise ValueError(
                "semantic_control_policy.owner_decision_fixture.decisions"
                f"[{index}].accepted_ontology_delta must match accepted decision_state"
            )
        decision_id = require_string(
            raw_decision,
            "decision_id",
            f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
        )
        candidate_id = require_string(
            raw_decision,
            "candidate_id",
            f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
        )
        intake_id = require_string(
            raw_decision,
            "intake_id",
            f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
        )
        decision = {
            "decision_id": decision_id,
            "candidate_id": candidate_id,
            "intake_id": intake_id,
            "decision_state": decision_state,
            "ontology_decision_ref": require_string(
                raw_decision,
                "ontology_decision_ref",
                f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
            ),
            "decided_by": require_string(
                raw_decision,
                "decided_by",
                f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
            ),
            "decided_at": require_string(
                raw_decision,
                "decided_at",
                f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
            ),
            "reason": optional_string(
                raw_decision,
                "reason",
                f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
            ),
            "accepted_ontology_delta": accepted_ontology_delta,
            "imports_into_specgraph": require_bool(
                raw_decision,
                "imports_into_specgraph",
                f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
            ),
            "closes_semantic_gate": require_bool(
                raw_decision,
                "closes_semantic_gate",
                f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
            ),
            "mutates_canonical_specs": require_bool(
                raw_decision,
                "mutates_canonical_specs",
                f"semantic_control_policy.owner_decision_fixture.decisions[{index}]",
            ),
        }
        for field in ("imports_into_specgraph", "closes_semantic_gate", "mutates_canonical_specs"):
            if decision[field] is not False:
                raise ValueError(
                    "semantic_control_policy.owner_decision_fixture.decisions"
                    f"[{index}].{field} must be false"
                )
        matched_entry = closed_loop_by_decision_key.get((candidate_id, intake_id))
        if matched_entry is None:
            ignored_decisions.append(
                {
                    "decision_id": decision_id,
                    "candidate_id": candidate_id,
                    "intake_id": intake_id,
                    "decision_state": decision_state,
                    "reason": "missing_closed_loop_evidence",
                }
            )
            continue
        source_evidence_state = require_string(
            matched_entry,
            "evidence_state",
            f"closed_loop_evidence.evidence_entries[{candidate_id}]",
        )
        source_intake_state = require_string(
            matched_entry,
            "source_intake_state",
            f"closed_loop_evidence.evidence_entries[{candidate_id}]",
        )
        if (
            source_evidence_state != "pending_ontology_owner_decision"
            or source_intake_state != "awaiting_ontology_owner_review"
        ):
            ignored_decisions.append(
                {
                    "decision_id": decision_id,
                    "candidate_id": candidate_id,
                    "intake_id": intake_id,
                    "decision_state": decision_state,
                    "source_evidence_state": source_evidence_state,
                    "source_intake_state": source_intake_state,
                    "reason": "closed_loop_evidence_not_pending_owner_decision",
                }
            )
            continue
        decision["source_evidence_id"] = require_string(
            matched_entry,
            "evidence_id",
            f"closed_loop_evidence.evidence_entries[{candidate_id}]",
        )
        decision["source_evidence_state"] = source_evidence_state
        decision["source_intake_state"] = source_intake_state
        decisions.append(decision)

    source_artifacts = copy_json_object(
        require_object(closed_loop_evidence, "source_artifacts", "closed_loop_evidence")
    )
    source_artifacts["ontology_closed_loop_evidence"] = require_surface_output_artifact(
        closed_loop_evidence, "ontology_closed_loop_evidence"
    )
    accepted_count = sum(1 for decision in decisions if decision["decision_state"] == "accepted")
    rejected_count = sum(1 for decision in decisions if decision["decision_state"] == "rejected")
    clarification_count = sum(
        1 for decision in decisions if decision["decision_state"] == "needs_clarification"
    )
    status = "decisions_available" if decisions else "no_decisions"
    return {
        "artifact_kind": require_string(
            owner_decision_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_owner_decision_report_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0114",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_artifacts": source_artifacts,
        "target": copy_json_object(
            require_object(
                owner_decision_contract,
                "target",
                "semantic_control_policy.ontology_owner_decision_report_contract",
            )
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "decisions": decisions,
        "ignored_decisions": ignored_decisions,
        "consumer_boundary": copy_json_object(
            require_object(
                owner_decision_contract,
                "consumer_boundary",
                "semantic_control_policy.ontology_owner_decision_report_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": status,
            "decision_count": len(decisions),
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "clarification_count": clarification_count,
            "ignored_decision_count": len(ignored_decisions),
            "next_gap": require_string(
                owner_decision_contract,
                "next_gap",
                "semantic_control_policy.ontology_owner_decision_report_contract",
            ),
        },
        "output_artifact": require_layout_path(semantic_layout, "ontology_owner_decision_report"),
    }


def require_ontology_owner_decision_report(
    owner_decision_report: dict[str, Any],
) -> dict[str, Any]:
    if owner_decision_report.get("artifact_kind") != "ontology_owner_decision_report":
        raise ValueError(
            "owner_decision_report.artifact_kind must be ontology_owner_decision_report"
        )
    if require_int(owner_decision_report, "schema_version", "owner_decision_report") != 1:
        raise ValueError("owner_decision_report.schema_version must be 1")
    if require_string(owner_decision_report, "proposal_id", "owner_decision_report") != "0114":
        raise ValueError("owner_decision_report.proposal_id must be 0114")
    if (
        require_bool(owner_decision_report, "canonical_mutations_allowed", "owner_decision_report")
        is not False
    ):
        raise ValueError("owner_decision_report.canonical_mutations_allowed must be false")
    if (
        require_bool(owner_decision_report, "tracked_artifacts_written", "owner_decision_report")
        is not False
    ):
        raise ValueError("owner_decision_report.tracked_artifacts_written must be false")
    require_surface_output_artifact(owner_decision_report, "ontology_owner_decision_report")
    require_object(owner_decision_report, "source_artifacts", "owner_decision_report")
    require_object(owner_decision_report, "summary", "owner_decision_report")
    ignored_decisions = owner_decision_report.get("ignored_decisions", [])
    if not isinstance(ignored_decisions, list):
        raise ValueError("owner_decision_report.ignored_decisions must be a list")
    decisions = owner_decision_report.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("owner_decision_report.decisions must be a list")
    for index, raw_decision in enumerate(decisions):
        if not isinstance(raw_decision, dict):
            raise ValueError(f"owner_decision_report.decisions[{index}] must be an object")
        for field in (
            "decision_id",
            "candidate_id",
            "intake_id",
            "ontology_decision_ref",
            "decided_by",
            "decided_at",
            "source_evidence_id",
            "source_evidence_state",
            "source_intake_state",
        ):
            require_string(raw_decision, field, f"owner_decision_report.decisions[{index}]")
        if (
            raw_decision["source_evidence_state"] != "pending_ontology_owner_decision"
            or raw_decision["source_intake_state"] != "awaiting_ontology_owner_review"
        ):
            raise ValueError(
                "owner_decision_report.decisions"
                f"[{index}] must reference pending owner-decision evidence"
            )
        decision_state = require_string(
            raw_decision, "decision_state", f"owner_decision_report.decisions[{index}]"
        )
        if decision_state not in {"accepted", "rejected", "needs_clarification"}:
            raise ValueError(
                f"owner_decision_report.decisions[{index}].decision_state must be supported"
            )
        accepted_ontology_delta = require_bool(
            raw_decision,
            "accepted_ontology_delta",
            f"owner_decision_report.decisions[{index}]",
        )
        if accepted_ontology_delta != (decision_state == "accepted"):
            raise ValueError(
                "owner_decision_report.decisions"
                f"[{index}].accepted_ontology_delta must match accepted decision_state"
            )
        for field in ("imports_into_specgraph", "closes_semantic_gate", "mutates_canonical_specs"):
            if (
                require_bool(raw_decision, field, f"owner_decision_report.decisions[{index}]")
                is not False
            ):
                raise ValueError(f"owner_decision_report.decisions[{index}].{field} must be false")
    consumer_boundary = require_object(
        owner_decision_report, "consumer_boundary", "owner_decision_report"
    )
    for field in ("for_specgraph_decision_import_preview", "for_specspace_review_dashboard"):
        if (
            require_bool(consumer_boundary, field, "owner_decision_report.consumer_boundary")
            is not True
        ):
            raise ValueError(f"owner_decision_report.consumer_boundary.{field} must be true")
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_import_into_specgraph",
        "may_close_semantic_gate",
    ):
        if (
            require_bool(consumer_boundary, field, "owner_decision_report.consumer_boundary")
            is not False
        ):
            raise ValueError(f"owner_decision_report.consumer_boundary.{field} must be false")
    authority_boundary = require_object(
        owner_decision_report, "authority_boundary", "owner_decision_report"
    )
    for field in (
        "ontology_owner_decision_report_is_authority",
        "prompt_agent_execution_allowed",
        "automatic_import_lock_update",
        "automatic_canonical_node_update",
        "canonical_mutations_allowed",
    ):
        if (
            require_bool(authority_boundary, field, "owner_decision_report.authority_boundary")
            is not False
        ):
            raise ValueError(f"owner_decision_report.authority_boundary.{field} must be false")
    return owner_decision_report


def build_ontology_decision_import_preview(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    dashboard: dict[str, Any],
    owner_decision_report: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    require_ontology_review_dashboard(dashboard)
    require_ontology_owner_decision_report(owner_decision_report)

    decision_import_contract = require_object(
        semantic_policy, "ontology_decision_import_preview_contract", "semantic_control_policy"
    )
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    dashboard_artifact = require_surface_output_artifact(dashboard, "ontology_review_dashboard")
    owner_decision_report_artifact = require_surface_output_artifact(
        owner_decision_report, "ontology_owner_decision_report"
    )
    dashboard_sources = require_object(dashboard, "source_artifacts", "dashboard")
    owner_decision_sources = require_object(
        owner_decision_report, "source_artifacts", "owner_decision_report"
    )
    for key in ("ontology_closed_loop_evidence",):
        if dashboard_sources.get(key) != owner_decision_sources.get(key):
            raise ValueError(
                "owner_decision_report.source_artifacts."
                f"{key} must match dashboard.source_artifacts.{key}"
            )
    dashboard_summary = require_object(dashboard, "status_summary", "dashboard")
    dashboard_status = require_string(dashboard_summary, "status", "dashboard.status_summary")
    preview_states = set(
        require_string_list(
            decision_import_contract,
            "preview_states",
            "semantic_control_policy.ontology_decision_import_preview_contract",
        )
    )

    closed_loop_entries = dashboard.get("closed_loop_entries")
    if not isinstance(closed_loop_entries, list):
        raise ValueError("dashboard.closed_loop_entries must be a list")
    closed_loop_by_decision_key: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw_entry in enumerate(closed_loop_entries):
        if not isinstance(raw_entry, dict):
            raise ValueError(f"dashboard.closed_loop_entries[{index}] must be an object")
        candidate_id = require_string(
            raw_entry, "candidate_id", f"dashboard.closed_loop_entries[{index}]"
        )
        intake_id = require_string(
            raw_entry, "intake_id", f"dashboard.closed_loop_entries[{index}]"
        )
        closed_loop_by_decision_key[(candidate_id, intake_id)] = raw_entry

    raw_decisions = owner_decision_report.get("decisions")
    if not isinstance(raw_decisions, list):
        raise ValueError("owner_decision_report.decisions must be a list")
    raw_ignored_decisions = owner_decision_report.get("ignored_decisions", [])
    if not isinstance(raw_ignored_decisions, list):
        raise ValueError("owner_decision_report.ignored_decisions must be a list")
    ignored_owner_decisions = [
        copy_json_object(decision)
        for decision in raw_ignored_decisions
        if isinstance(decision, dict)
    ]
    previews: list[dict[str, Any]] = []
    for index, raw_decision in enumerate(raw_decisions):
        if not isinstance(raw_decision, dict):
            raise ValueError(f"owner_decision_report.decisions[{index}] must be an object")
        context = f"owner_decision_report.decisions[{index}]"
        decision_id = require_string(raw_decision, "decision_id", context)
        candidate_id = require_string(raw_decision, "candidate_id", context)
        intake_id = require_string(raw_decision, "intake_id", context)
        decision_state = require_string(raw_decision, "decision_state", context)
        if decision_state not in {"accepted", "rejected", "needs_clarification"}:
            raise ValueError(f"{context}.decision_state must be supported")
        matched_entry = closed_loop_by_decision_key.get((candidate_id, intake_id))
        matched_evidence_id = ""
        matched_source_intake_state = ""
        matched_evidence_state = ""
        required_human_action = "review_unmatched_ontology_owner_decision"
        if matched_entry is None:
            preview_state = "unmatched_decision"
        else:
            matched_evidence_id = require_string(
                matched_entry,
                "evidence_id",
                f"dashboard.closed_loop_entries[{candidate_id}]",
            )
            matched_source_intake_state = require_string(
                matched_entry,
                "source_intake_state",
                f"dashboard.closed_loop_entries[{candidate_id}]",
            )
            matched_evidence_state = require_string(
                matched_entry,
                "evidence_state",
                f"dashboard.closed_loop_entries[{candidate_id}]",
            )
            if decision_state == "rejected":
                preview_state = "rejected_by_owner"
                required_human_action = "record_owner_rejection_without_import"
            elif decision_state == "needs_clarification":
                preview_state = "needs_clarification"
                required_human_action = "request_owner_clarification"
            elif (
                dashboard_status == "blocked_by_semantic_gate"
                or matched_evidence_state == "blocked_by_semantic_gate"
            ):
                preview_state = "blocked_by_semantic_gate"
                required_human_action = require_string(
                    matched_entry,
                    "required_human_action",
                    f"dashboard.closed_loop_entries[{candidate_id}]",
                )
            else:
                preview_state = "ready_for_operator_review"
                required_human_action = "operator_review_ontology_owner_decision"
        if preview_state not in preview_states:
            raise ValueError(
                "semantic_control_policy.ontology_decision_import_preview_contract."
                f"preview_states does not declare computed state {preview_state}"
            )
        import_recommended = (
            preview_state == "ready_for_operator_review" and decision_state == "accepted"
        )
        previews.append(
            {
                "preview_id": f"ontology-decision-import-preview-{symbol_slug(decision_id)}",
                "decision_id": decision_id,
                "candidate_id": candidate_id,
                "intake_id": intake_id,
                "decision_state": decision_state,
                "ontology_decision_ref": require_string(
                    raw_decision, "ontology_decision_ref", context
                ),
                "decided_by": require_string(raw_decision, "decided_by", context),
                "decided_at": require_string(raw_decision, "decided_at", context),
                "reason": optional_string(raw_decision, "reason", context),
                "accepted_ontology_delta": require_bool(
                    raw_decision, "accepted_ontology_delta", context
                ),
                "matched_closed_loop_evidence_id": matched_evidence_id,
                "matched_source_intake_state": matched_source_intake_state,
                "matched_evidence_state": matched_evidence_state,
                "preview_state": preview_state,
                "required_human_action": required_human_action,
                "import_recommended": import_recommended,
                "imports_into_specgraph": False,
                "closes_semantic_gate": False,
                "mutates_canonical_specs": False,
                "writes_ontology_package": False,
                "updates_ontology_lockfile": False,
            }
        )

    accepted_count = sum(1 for preview in previews if preview["decision_state"] == "accepted")
    rejected_count = sum(1 for preview in previews if preview["decision_state"] == "rejected")
    clarification_count = sum(
        1 for preview in previews if preview["decision_state"] == "needs_clarification"
    )
    importable_count = sum(1 for preview in previews if preview["import_recommended"])
    blocked_count = sum(
        1 for preview in previews if preview["preview_state"] == "blocked_by_semantic_gate"
    )
    unmatched_count = sum(
        1 for preview in previews if preview["preview_state"] == "unmatched_decision"
    )
    if not previews:
        status = "no_decisions"
    elif blocked_count:
        status = "blocked_by_semantic_gate"
    elif importable_count:
        status = "ready_for_operator_review"
    elif unmatched_count:
        status = "unmatched_decision"
    elif clarification_count:
        status = "needs_clarification"
    else:
        status = "rejected_by_owner"

    source_artifacts = copy_json_object(dashboard_sources)
    source_artifacts["ontology_review_dashboard"] = dashboard_artifact
    source_artifacts["ontology_owner_decision_report"] = owner_decision_report_artifact

    return {
        "artifact_kind": require_string(
            decision_import_contract,
            "artifact_kind",
            "semantic_control_policy.ontology_decision_import_preview_contract",
        ),
        "schema_version": 1,
        "proposal_id": "0115",
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_artifacts": source_artifacts,
        "target": copy_json_object(
            require_object(
                decision_import_contract,
                "target",
                "semantic_control_policy.ontology_decision_import_preview_contract",
            )
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "decision_import_previews": previews,
        "ignored_owner_decisions": ignored_owner_decisions,
        "consumer_boundary": copy_json_object(
            require_object(
                decision_import_contract,
                "consumer_boundary",
                "semantic_control_policy.ontology_decision_import_preview_contract",
            )
        ),
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": status,
            "preview_count": len(previews),
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "clarification_count": clarification_count,
            "importable_count": importable_count,
            "blocked_count": blocked_count,
            "unmatched_count": unmatched_count,
            "ignored_decision_count": len(ignored_owner_decisions),
            "next_gap": require_string(
                decision_import_contract,
                "next_gap",
                "semantic_control_policy.ontology_decision_import_preview_contract",
            ),
        },
        "output_artifact": require_layout_path(semantic_layout, "ontology_decision_import_preview"),
    }


def require_ontology_decision_import_preview(
    preview: dict[str, Any],
) -> dict[str, Any]:
    if preview.get("artifact_kind") != "ontology_decision_import_preview":
        raise ValueError(
            "decision_import_preview.artifact_kind must be ontology_decision_import_preview"
        )
    if require_int(preview, "schema_version", "decision_import_preview") != 1:
        raise ValueError("decision_import_preview.schema_version must be 1")
    if require_string(preview, "proposal_id", "decision_import_preview") != "0115":
        raise ValueError("decision_import_preview.proposal_id must be 0115")
    if require_bool(preview, "canonical_mutations_allowed", "decision_import_preview") is not False:
        raise ValueError("decision_import_preview.canonical_mutations_allowed must be false")
    if require_bool(preview, "tracked_artifacts_written", "decision_import_preview") is not False:
        raise ValueError("decision_import_preview.tracked_artifacts_written must be false")
    require_surface_output_artifact(preview, "ontology_decision_import_preview")
    require_object(preview, "source_artifacts", "decision_import_preview")
    summary = require_object(preview, "summary", "decision_import_preview")
    status = require_string(summary, "status", "decision_import_preview.summary")
    supported_states = {
        "blocked_by_semantic_gate",
        "ready_for_operator_review",
        "rejected_by_owner",
        "needs_clarification",
        "unmatched_decision",
        "no_decisions",
    }
    if status not in supported_states:
        raise ValueError("decision_import_preview.summary.status is not supported")
    decision_import_previews = preview.get("decision_import_previews")
    if not isinstance(decision_import_previews, list):
        raise ValueError("decision_import_preview.decision_import_previews must be a list")
    ignored_owner_decisions = preview.get("ignored_owner_decisions", [])
    if not isinstance(ignored_owner_decisions, list):
        raise ValueError("decision_import_preview.ignored_owner_decisions must be a list")
    for index, raw_entry in enumerate(decision_import_previews):
        if not isinstance(raw_entry, dict):
            raise ValueError(
                f"decision_import_preview.decision_import_previews[{index}] must be an object"
            )
        context = f"decision_import_preview.decision_import_previews[{index}]"
        require_string(raw_entry, "preview_id", context)
        require_string(raw_entry, "decision_id", context)
        require_string(raw_entry, "candidate_id", context)
        require_string(raw_entry, "intake_id", context)
        decision_state = require_string(raw_entry, "decision_state", context)
        if decision_state not in {"accepted", "rejected", "needs_clarification"}:
            raise ValueError(f"{context}.decision_state must be supported")
        accepted_ontology_delta = require_bool(raw_entry, "accepted_ontology_delta", context)
        preview_state = require_string(raw_entry, "preview_state", context)
        if preview_state not in supported_states - {"no_decisions"}:
            raise ValueError(f"{context}.preview_state must be supported")
        import_recommended = require_bool(raw_entry, "import_recommended", context)
        if import_recommended is not (preview_state == "ready_for_operator_review"):
            raise ValueError(
                f"{context}.import_recommended must match ready_for_operator_review state"
            )
        if preview_state == "ready_for_operator_review":
            if decision_state != "accepted" or accepted_ontology_delta is not True:
                raise ValueError(
                    f"{context}.ready_for_operator_review requires an accepted decision"
                )
            for field in (
                "matched_closed_loop_evidence_id",
                "matched_source_intake_state",
                "matched_evidence_state",
            ):
                require_string(raw_entry, field, context)
        for field in (
            "imports_into_specgraph",
            "closes_semantic_gate",
            "mutates_canonical_specs",
            "writes_ontology_package",
            "updates_ontology_lockfile",
        ):
            if require_bool(raw_entry, field, context) is not False:
                raise ValueError(f"{context}.{field} must be false")
    consumer_boundary = require_object(preview, "consumer_boundary", "decision_import_preview")
    for field in ("for_specgraph_decision_import_preview", "for_specspace_review_dashboard"):
        if (
            require_bool(consumer_boundary, field, "decision_import_preview.consumer_boundary")
            is not True
        ):
            raise ValueError(f"decision_import_preview.consumer_boundary.{field} must be true")
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_update_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_apply_preview",
        "may_import_into_specgraph",
        "may_close_semantic_gate",
    ):
        if (
            require_bool(consumer_boundary, field, "decision_import_preview.consumer_boundary")
            is not False
        ):
            raise ValueError(f"decision_import_preview.consumer_boundary.{field} must be false")
    authority_boundary = require_object(preview, "authority_boundary", "decision_import_preview")
    for field in (
        "ontology_decision_import_preview_is_authority",
        "prompt_agent_execution_allowed",
        "automatic_import_lock_update",
        "automatic_canonical_node_update",
        "canonical_mutations_allowed",
    ):
        if (
            require_bool(authority_boundary, field, "decision_import_preview.authority_boundary")
            is not False
        ):
            raise ValueError(f"decision_import_preview.authority_boundary.{field} must be false")
    return preview


def build_ontology_semantic_lint_smoke(
    semantic_policy: dict[str, Any],
    *,
    semantic_policy_path: Path,
    import_policy: dict[str, Any],
    package_index: dict[str, Any],
    gap_index: dict[str, Any],
    governance_evidence_index: dict[str, Any],
    binding_preview: dict[str, Any],
) -> dict[str, Any]:
    require_semantic_control_policy(semantic_policy)
    validate_semantic_source_surfaces(
        semantic_policy,
        package_index=package_index,
        gap_index=gap_index,
        governance_evidence_index=governance_evidence_index,
        binding_preview=binding_preview,
    )
    contract = require_object(semantic_policy, "semantic_lint_contract", "semantic_control_policy")
    smoke_fixture = require_object(semantic_policy, "smoke_fixture", "semantic_control_policy")
    detected_terms = smoke_fixture.get("detected_terms")
    if not isinstance(detected_terms, list) or not detected_terms:
        raise ValueError(
            "semantic_control_policy.smoke_fixture.detected_terms must be a non-empty list"
        )
    generated_text = require_string(
        smoke_fixture,
        "generated_text",
        "semantic_control_policy.smoke_fixture",
    )

    accepted_by_ref = {
        str(entry.get("source_ref", "")).strip(): entry
        for entry in binding_preview.get("resolved_refs", [])
        if isinstance(entry, dict) and str(entry.get("source_ref", "")).strip()
    }
    gap_by_ref = {
        str(gap.get("missing_concept", {}).get("ref", "")).strip(): gap
        for gap in gap_index.get("gaps", [])
        if isinstance(gap, dict) and isinstance(gap.get("missing_concept"), dict)
    }

    term_results, statuses, classification_counts = build_semantic_term_results(
        semantic_policy,
        detected_terms=detected_terms,
        detected_terms_context="semantic_control_policy.smoke_fixture.detected_terms",
        accepted_by_ref=accepted_by_ref,
        gap_by_ref=gap_by_ref,
    )

    summary_status = semantic_summary_status(statuses, semantic_policy)
    review_required_count = sum(1 for status in statuses if status.startswith("review_required_"))
    blocking_count = sum(1 for status in statuses if status.startswith("blocked_"))
    import_layout = require_object(import_policy, "repository_layout", "ontology_import_policy")
    semantic_layout = require_object(
        semantic_policy, "repository_layout", "semantic_control_policy"
    )
    return {
        "artifact_kind": require_string(
            contract, "smoke_artifact_kind", "semantic_control_policy.semantic_lint_contract"
        ),
        "schema_version": 1,
        "proposal_id": semantic_policy["proposal_id"],
        "policy_basis": semantic_policy["policy_basis"],
        "source_policy": relative_path(semantic_policy_path),
        "source_surfaces": {
            "ontology_package_index": require_layout_path(import_layout, "package_index"),
            "ontology_import_gap_index": require_layout_path(import_layout, "gap_index"),
            "ontology_governance_evidence_index": require_layout_path(
                import_layout, "governance_evidence_index"
            ),
            "ontology_binding_preview": require_layout_path(import_layout, "binding_preview"),
        },
        "target": copy_json_object(
            require_object(
                smoke_fixture,
                "target",
                "semantic_control_policy.smoke_fixture",
            )
        ),
        "input": {
            "generated_text_sha256": "sha256:"
            + hashlib.sha256(generated_text.encode("utf-8")).hexdigest(),
            "detected_term_count": len(term_results),
        },
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "term_results": term_results,
        "authority_boundary": copy_json_object(
            require_object(semantic_policy, "authority_boundary", "semantic_control_policy")
        ),
        "summary": {
            "status": summary_status,
            "term_count": len(term_results),
            "classification_counts": {
                key: value for key, value in sorted(classification_counts.items()) if value
            },
            "review_required_count": review_required_count,
            "blocking_count": blocking_count,
            "next_gap": semantic_next_gap(summary_status, semantic_policy),
        },
        "output_artifact": require_layout_path(semantic_layout, "semantic_lint_smoke"),
    }


def copy_json_object(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True))


def build_ontology_import_surfaces(
    fixture_path: Path,
    *,
    policy_path: Path = POLICY_PATH,
    adapter_report_path: Path | None = None,
    semantic_policy_path: Path | None | object = DEFAULT_SEMANTIC_POLICY,
) -> dict[str, dict[str, Any]]:
    policy = load_json(policy_path)
    fixture = load_yaml(fixture_path)
    validate_fixture(policy, fixture)
    import_layout = require_object(policy, "repository_layout", "ontology_import_policy")
    default_fixture_path = ROOT / require_layout_path(import_layout, "default_fixture")
    if semantic_policy_path is DEFAULT_SEMANTIC_POLICY:
        semantic_policy_path = (
            SEMANTIC_CONTROL_POLICY_PATH
            if fixture_path.resolve() == default_fixture_path.resolve()
            else None
        )

    package = fixture["package"]
    binding = fixture["binding"]
    ir_path = resolve_fixture_file(
        fixture_path,
        package["materialized_ir"],
        "fixture.package.materialized_ir",
    )
    ir = load_json(ir_path)
    validate_ir_metadata(ir, package)
    refs = ontology_ref_map(ir)

    requested_refs = list(binding["refs"])
    resolved_refs = [
        {
            "source_ref": ref,
            "target_package": f"{package['package_id']}@{package['version']}",
            "namespace": package["namespace"],
            **refs[ref],
        }
        for ref in requested_refs
        if ref in refs
    ]
    unresolved_refs = [ref for ref in requested_refs if ref not in refs]

    package_entry = {
        "package_id": package["package_id"],
        "namespace": package["namespace"],
        "version": package["version"],
        "source_uri": package["source_uri"],
        "source_ref": package.get("source_ref"),
        "digest": package["digest"],
        "authority_class": package.get("authority_class", "imported"),
        "accepted_by_proposal": package.get("accepted_by_proposal"),
        "materialized_ir": relative_path(ir_path),
        "lock": {
            "package_ref": f"{package['package_id']}@{package['version']}",
            "namespace": package["namespace"],
            "digest": package["digest"],
            "source_uri": package["source_uri"],
        },
    }

    package_index = {
        "artifact_kind": "ontology_package_index",
        "schema_version": 1,
        "proposal_id": fixture["proposal_id"],
        "source_fixture": relative_path(fixture_path),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "packages": [package_entry],
        "summary": {
            "imported_package_count": 1,
            "resolved_ref_count": len(resolved_refs),
            "unresolved_ref_count": len(unresolved_refs),
            "next_gap": "review_ontology_import_gap" if unresolved_refs else "none",
        },
    }

    subject = binding["subject"]
    binding_preview = {
        "artifact_kind": "ontology_binding_preview",
        "schema_version": 1,
        "proposal_id": fixture["proposal_id"],
        "source_fixture": relative_path(fixture_path),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "subject": subject,
        "package_ref": f"{package['package_id']}@{package['version']}",
        "resolved_refs": resolved_refs,
        "unresolved_refs": unresolved_refs,
        "review_state": "ready_for_review" if unresolved_refs else "clean",
        "next_gap": "review_ontology_import_gap" if unresolved_refs else "none",
    }

    gaps = []
    for ref in unresolved_refs:
        namespace_hint, _, concept_hint = ref.partition(":")
        gaps.append(
            {
                "gap_id": f"ontology-gap-{symbol_slug(ref)}",
                "needed_by": [fixture["proposal_id"], subject["id"]],
                "subject": subject,
                "missing_concept": {
                    "ref": ref,
                    "namespace_hint": namespace_hint,
                    "concept_hint": concept_hint,
                },
                "target_package": f"{package['package_id']}@{package['version']}",
                "severity": "medium",
                "recommended_route": "ontology_package_draft",
            }
        )

    gap_index = {
        "artifact_kind": "ontology_import_gap_index",
        "schema_version": 1,
        "proposal_id": fixture["proposal_id"],
        "source_fixture": relative_path(fixture_path),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "gaps": gaps,
        "summary": {
            "gap_count": len(gaps),
            "next_gap": "review_ontology_import_gap" if gaps else "none",
        },
    }

    package_ref = f"{package['package_id']}@{package['version']}"
    evidence = governance_evidence_for(package_ref, package.get("governance"))
    governance_evidence_index = {
        "artifact_kind": "ontology_governance_evidence_index",
        "schema_version": 1,
        "proposal_id": fixture["proposal_id"],
        "source_fixture": relative_path(fixture_path),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "evidence": evidence,
        "summary": {
            "evidence_count": len(evidence),
            "next_gap": "none" if evidence else "attach_ontology_governance_evidence",
        },
    }

    prompt_invocation_index = {
        "artifact_kind": "ontology_prompt_invocation_index",
        "schema_version": 1,
        "proposal_id": fixture["proposal_id"],
        "source_fixture": relative_path(fixture_path),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "invocations": [],
        "summary": {
            "invocation_count": 0,
            "status": "not_invoked",
            "next_gap": "none",
        },
    }

    surfaces = {
        "package_index": package_index,
        "gap_index": gap_index,
        "governance_evidence_index": governance_evidence_index,
        "binding_preview": binding_preview,
        "prompt_invocation_index": prompt_invocation_index,
    }
    if adapter_report_path is not None:
        if not adapter_report_path.is_absolute():
            adapter_report_path = ROOT / adapter_report_path
        require_string(package, "source_ref", "fixture.package")
        surfaces["adapter_report_smoke"] = build_ontologyc_adapter_report_smoke(
            policy,
            fixture_path=fixture_path,
            report_path=adapter_report_path,
            fixture=fixture,
            package=package,
            ir=ir,
            ir_path=ir_path,
            resolved_refs=resolved_refs,
            unresolved_refs=unresolved_refs,
        )
    if semantic_policy_path is not None:
        assert isinstance(semantic_policy_path, Path)
        if not semantic_policy_path.is_absolute():
            semantic_policy_path = ROOT / semantic_policy_path
        if semantic_policy_path.exists():
            semantic_policy = load_json(semantic_policy_path)
            semantic_context_pack = build_ontology_semantic_context_pack(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                import_policy=policy,
                package_index=package_index,
                gap_index=gap_index,
                governance_evidence_index=governance_evidence_index,
                binding_preview=binding_preview,
            )
            surfaces["semantic_context_pack"] = semantic_context_pack
            semantic_lint_input = build_ontology_semantic_lint_input(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
            )
            surfaces["semantic_lint_input"] = semantic_lint_input
            semantic_lint_report = build_ontology_semantic_lint_report(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                context_pack=semantic_context_pack,
                lint_input=semantic_lint_input,
            )
            surfaces["semantic_lint_report"] = semantic_lint_report
            surfaces["ontology_delta_candidate_review_packet"] = (
                build_ontology_delta_candidate_review_packet(
                    semantic_policy,
                    semantic_policy_path=semantic_policy_path,
                    lint_report=semantic_lint_report,
                )
            )
            surfaces["semantic_review_surface"] = build_ontology_semantic_review_surface(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                context_pack=semantic_context_pack,
                lint_report=semantic_lint_report,
                review_packet=surfaces["ontology_delta_candidate_review_packet"],
            )
            surfaces["supervisor_semantic_gate"] = build_ontology_supervisor_semantic_gate(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                review_surface=surfaces["semantic_review_surface"],
            )
            surfaces["ontology_delta_draft_intake"] = build_ontology_delta_draft_intake(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                review_packet=surfaces["ontology_delta_candidate_review_packet"],
                supervisor_gate=surfaces["supervisor_semantic_gate"],
            )
            surfaces["ontology_closed_loop_evidence"] = build_ontology_closed_loop_evidence(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                draft_intake=surfaces["ontology_delta_draft_intake"],
            )
            surfaces["ontology_review_dashboard"] = build_ontology_review_dashboard(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                review_surface=surfaces["semantic_review_surface"],
                supervisor_gate=surfaces["supervisor_semantic_gate"],
                draft_intake=surfaces["ontology_delta_draft_intake"],
                closed_loop_evidence=surfaces["ontology_closed_loop_evidence"],
            )
            surfaces["ontology_owner_decision_report"] = build_ontology_owner_decision_report(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                closed_loop_evidence=surfaces["ontology_closed_loop_evidence"],
            )
            surfaces["ontology_decision_import_preview"] = build_ontology_decision_import_preview(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                dashboard=surfaces["ontology_review_dashboard"],
                owner_decision_report=surfaces["ontology_owner_decision_report"],
            )
            surfaces["semantic_lint_smoke"] = build_ontology_semantic_lint_smoke(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                import_policy=policy,
                package_index=package_index,
                gap_index=gap_index,
                governance_evidence_index=governance_evidence_index,
                binding_preview=binding_preview,
            )
    return surfaces


def write_ontology_import_surfaces(
    surfaces: dict[str, dict[str, Any]],
    *,
    policy_path: Path = POLICY_PATH,
    out_dir: Path = ROOT,
) -> list[Path]:
    policy = load_json(policy_path)
    layout = policy.get("repository_layout")
    if not isinstance(layout, dict):
        raise ValueError("policy.repository_layout must be an object")
    roots = allowed_output_roots(policy)
    destinations = {
        "package_index": require_layout_path(layout, "package_index"),
        "gap_index": require_layout_path(layout, "gap_index"),
        "governance_evidence_index": require_layout_path(layout, "governance_evidence_index"),
        "binding_preview": require_layout_path(layout, "binding_preview"),
        "prompt_invocation_index": require_layout_path(layout, "prompt_invocation_index"),
    }
    if "adapter_report_smoke" in surfaces:
        destinations["adapter_report_smoke"] = require_layout_path(layout, "adapter_report_smoke")
    if "ontology_delta_candidate_review_packet" in surfaces:
        destinations["ontology_delta_candidate_review_packet"] = require_surface_output_artifact(
            surfaces["ontology_delta_candidate_review_packet"],
            "ontology_delta_candidate_review_packet",
        )
    if "semantic_context_pack" in surfaces:
        destinations["semantic_context_pack"] = require_surface_output_artifact(
            surfaces["semantic_context_pack"], "semantic_context_pack"
        )
    if "semantic_lint_input" in surfaces:
        destinations["semantic_lint_input"] = require_surface_output_artifact(
            surfaces["semantic_lint_input"], "semantic_lint_input"
        )
    if "semantic_lint_report" in surfaces:
        destinations["semantic_lint_report"] = require_surface_output_artifact(
            surfaces["semantic_lint_report"], "semantic_lint_report"
        )
    if "semantic_review_surface" in surfaces:
        destinations["semantic_review_surface"] = require_surface_output_artifact(
            surfaces["semantic_review_surface"], "semantic_review_surface"
        )
    if "supervisor_semantic_gate" in surfaces:
        destinations["supervisor_semantic_gate"] = require_surface_output_artifact(
            surfaces["supervisor_semantic_gate"], "supervisor_semantic_gate"
        )
    if "ontology_delta_draft_intake" in surfaces:
        destinations["ontology_delta_draft_intake"] = require_surface_output_artifact(
            surfaces["ontology_delta_draft_intake"], "ontology_delta_draft_intake"
        )
    if "ontology_closed_loop_evidence" in surfaces:
        destinations["ontology_closed_loop_evidence"] = require_surface_output_artifact(
            surfaces["ontology_closed_loop_evidence"], "ontology_closed_loop_evidence"
        )
    if "ontology_review_dashboard" in surfaces:
        destinations["ontology_review_dashboard"] = require_surface_output_artifact(
            surfaces["ontology_review_dashboard"], "ontology_review_dashboard"
        )
    if "ontology_owner_decision_report" in surfaces:
        destinations["ontology_owner_decision_report"] = require_surface_output_artifact(
            surfaces["ontology_owner_decision_report"], "ontology_owner_decision_report"
        )
    if "ontology_decision_import_preview" in surfaces:
        destinations["ontology_decision_import_preview"] = require_surface_output_artifact(
            surfaces["ontology_decision_import_preview"], "ontology_decision_import_preview"
        )
    if "semantic_lint_smoke" in surfaces:
        destinations["semantic_lint_smoke"] = require_surface_output_artifact(
            surfaces["semantic_lint_smoke"], "semantic_lint_smoke"
        )
    written = []
    for key, relative in destinations.items():
        payload = surfaces[key]
        path = resolve_allowed_output_path(out_dir, relative, roots)
        written.append(write_json(path, payload))
    return written


def parse_args() -> argparse.Namespace:
    policy = load_json(POLICY_PATH)
    layout = policy.get("repository_layout")
    if not isinstance(layout, dict):
        raise ValueError("policy.repository_layout must be an object")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        default=str(ROOT / str(layout["default_fixture"])),
        help="Ontology import fixture YAML path.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write derived surfaces to the paths declared in tools/ontology_import_policy.json.",
    )
    parser.add_argument(
        "--adapter-report",
        default=None,
        help=(
            "Ontologyc adapter report fixture YAML path. Defaults to the checked-in "
            "adapter report only when --fixture is the default fixture."
        ),
    )
    parser.add_argument(
        "--semantic-policy",
        default=None,
        help=(
            "Ontology semantic control policy JSON path. Defaults to the checked-in "
            "policy only when --fixture is the default fixture."
        ),
    )
    parser.add_argument(
        "--no-semantic-policy",
        action="store_true",
        help="Disable semantic-control derived surfaces for this run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_json(POLICY_PATH)
    layout = policy.get("repository_layout")
    if not isinstance(layout, dict):
        raise ValueError("policy.repository_layout must be an object")
    fixture_path = Path(args.fixture)
    if not fixture_path.is_absolute():
        fixture_path = ROOT / fixture_path
    default_fixture_path = ROOT / str(layout["default_fixture"])
    adapter_report_path = None
    if args.adapter_report:
        adapter_report_path = Path(args.adapter_report)
        if not adapter_report_path.is_absolute():
            adapter_report_path = ROOT / adapter_report_path
    elif fixture_path.resolve() == default_fixture_path.resolve():
        adapter_report_path = ROOT / str(layout["default_adapter_report"])
    if args.semantic_policy and args.no_semantic_policy:
        raise ValueError("--semantic-policy and --no-semantic-policy are mutually exclusive")
    semantic_policy_path = None
    if args.semantic_policy:
        semantic_policy_path = Path(args.semantic_policy)
        if not semantic_policy_path.is_absolute():
            semantic_policy_path = ROOT / semantic_policy_path
    elif not args.no_semantic_policy and fixture_path.resolve() == default_fixture_path.resolve():
        semantic_policy_path = SEMANTIC_CONTROL_POLICY_PATH
    surfaces = build_ontology_import_surfaces(
        fixture_path,
        adapter_report_path=adapter_report_path,
        semantic_policy_path=semantic_policy_path,
    )
    if args.write:
        written = write_ontology_import_surfaces(surfaces)
        for path in written:
            print(relative_path(path))
    else:
        print(json.dumps(surfaces, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
