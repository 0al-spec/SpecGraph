#!/usr/bin/env python3
"""Build read-only SpecGraph ontology import surfaces for proposal 0060."""

from __future__ import annotations

import argparse
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
    require_layout_path(layout, "semantic_context_pack")
    require_layout_path(layout, "semantic_lint_smoke")
    boundary = require_object(policy, "authority_boundary", "semantic_control_policy")
    for field in (
        "context_pack_is_authority",
        "lint_report_is_authority",
        "smoke_report_is_authority",
        "ontology_delta_candidate_is_authority",
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
    accepted_relation_refs = {entry["source_ref"] for entry in accepted_relations}
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
                if accepted_relation_ref in accepted_relation_refs
                else "unresolved_relation_ref"
            ),
            "reason": str(control.get("reason", "")).strip(),
        }
        if accepted_relation_ref in accepted_by_ref:
            conflict["accepted_relation"] = accepted_by_ref[accepted_relation_ref]
        relation_conflicts.append(conflict)

    raw_gaps = gap_index.get("gaps")
    if not isinstance(raw_gaps, list):
        raise ValueError("ontology_import_gap_index.gaps must be a list")
    unresolved_gaps = [copy_json_object(gap) for gap in raw_gaps if isinstance(gap, dict)]
    raw_evidence = governance_evidence_index.get("evidence")
    if not isinstance(raw_evidence, list):
        raise ValueError("ontology_governance_evidence_index.evidence must be a list")
    governance_evidence = [
        copy_json_object(evidence) for evidence in raw_evidence if isinstance(evidence, dict)
    ]
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
    suggested_actions = require_object(
        contract, "suggested_actions", "semantic_control_policy.semantic_lint_contract"
    )
    aliases = semantic_control_map(semantic_policy, "aliases")
    deprecated_terms = semantic_control_map(semantic_policy, "deprecated_terms")
    relation_conflicts = semantic_control_map(semantic_policy, "relation_conflicts")
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

    term_results: list[dict[str, Any]] = []
    statuses: list[str] = []
    classification_counts = {
        classification: 0
        for classification in require_string_list(
            contract, "term_classifications", "semantic_control_policy.semantic_lint_contract"
        )
    }
    for index, raw_term in enumerate(detected_terms):
        if not isinstance(raw_term, dict):
            raise ValueError(
                f"semantic_control_policy.smoke_fixture.detected_terms[{index}] must be an object"
            )
        term = require_string(
            raw_term,
            "term",
            f"semantic_control_policy.smoke_fixture.detected_terms[{index}]",
        )
        normalized = normalize_term(term)
        source_ref = str(raw_term.get("source_ref", "")).strip()
        result: dict[str, Any] = {
            "term": term,
            "normalized_term": normalized,
            "source_ref": source_ref or None,
        }

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
            surfaces["semantic_context_pack"] = build_ontology_semantic_context_pack(
                semantic_policy,
                semantic_policy_path=semantic_policy_path,
                import_policy=policy,
                package_index=package_index,
                gap_index=gap_index,
                governance_evidence_index=governance_evidence_index,
                binding_preview=binding_preview,
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
    if "semantic_context_pack" in surfaces:
        destinations["semantic_context_pack"] = require_surface_output_artifact(
            surfaces["semantic_context_pack"], "semantic_context_pack"
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
