#!/usr/bin/env python3
"""Build read-only SpecGraph ontology import surfaces for proposal 0060."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "tools" / "ontology_import_policy.json"
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


def ontologyc_adapter_report_contract(policy: dict[str, Any]) -> dict[str, Any]:
    contract = policy.get("ontologyc_adapter_report_contract")
    if not isinstance(contract, dict):
        raise ValueError("policy.ontologyc_adapter_report_contract must be an object")
    return contract


def resolve_report_file(report_path: Path, relative: str, context: str) -> Path:
    return resolve_fixture_file(report_path, relative, context)


def output_ref_entries(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    spec = require_object(payload, "spec", "adapter_output")
    refs = spec.get("refs")
    if not isinstance(refs, list):
        raise ValueError("adapter_output.spec.refs must be a list")
    entries = {}
    for index, item in enumerate(refs):
        if not isinstance(item, dict):
            raise ValueError(f"adapter_output.spec.refs[{index}] must be an object")
        alias = require_string(item, "alias", f"adapter_output.spec.refs[{index}]")
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


def output_gap_refs(payload: dict[str, Any]) -> list[str]:
    spec = require_object(payload, "spec", "adapter_output")
    gaps = spec.get("gaps")
    if not isinstance(gaps, list):
        raise ValueError("adapter_output.spec.gaps must be a list")
    missing_refs = []
    for index, item in enumerate(gaps):
        if not isinstance(item, dict):
            raise ValueError(f"adapter_output.spec.gaps[{index}] must be an object")
        gap_spec = require_object(item, "spec", f"adapter_output.spec.gaps[{index}]")
        missing_refs.append(
            require_string(gap_spec, "missingConcept", f"adapter_output.spec.gaps[{index}].spec")
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
        _, _, package_field = field.partition(".")
        if not package_field:
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
    output_entries = output_ref_entries(concept_refs_output)
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
    output_gaps = sorted(output_gap_refs(ontology_gaps_output))
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


def build_ontology_import_surfaces(
    fixture_path: Path,
    *,
    policy_path: Path = POLICY_PATH,
    adapter_report_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    policy = load_json(policy_path)
    fixture = load_yaml(fixture_path)
    validate_fixture(policy, fixture)

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
    surfaces = build_ontology_import_surfaces(
        fixture_path,
        adapter_report_path=adapter_report_path,
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
