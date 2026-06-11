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
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


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


def build_ontology_import_surfaces(
    fixture_path: Path,
    *,
    policy_path: Path = POLICY_PATH,
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

    return {
        "package_index": package_index,
        "gap_index": gap_index,
        "governance_evidence_index": governance_evidence_index,
        "binding_preview": binding_preview,
        "prompt_invocation_index": prompt_invocation_index,
    }


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture_path = Path(args.fixture)
    if not fixture_path.is_absolute():
        fixture_path = ROOT / fixture_path
    surfaces = build_ontology_import_surfaces(fixture_path)
    if args.write:
        written = write_ontology_import_surfaces(surfaces)
        for path in written:
            print(relative_path(path))
    else:
        print(json.dumps(surfaces, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
