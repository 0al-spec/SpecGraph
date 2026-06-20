#!/usr/bin/env python3
"""Build review-only project-local ontology package authoring surfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ontology_imports import (
    POLICY_PATH,
    ROOT,
    build_ontology_import_surfaces,
    load_json,
    relative_path,
    write_json,
)

PROPOSAL_ID = "0133"
SCHEMA_VERSION = 1

OUTPUTS = {
    "validate": Path("runs/ontology_package_authoring_report.json"),
    "preview": Path("runs/ontology_package_preview.json"),
    "gaps": Path("runs/ontology_package_gap_preview.json"),
}


def default_fixture_paths(policy: dict[str, Any]) -> tuple[Path, Path, Path]:
    layout = policy.get("repository_layout")
    if not isinstance(layout, dict):
        raise ValueError("policy.repository_layout must be an object")
    return (
        ROOT / str(layout["default_fixture"]),
        ROOT / str(layout["default_adapter_report"]),
        ROOT / str(layout["default_compatibility_report"]),
    )


def common_authority_boundary(make_target: str) -> dict[str, Any]:
    return {
        "make_target": make_target,
        "canonical_mutations_allowed": False,
        "writes_canonical_specs": False,
        "updates_ontology_lockfile": False,
        "accepts_terms": False,
        "prompt_agent_execution_allowed": False,
        "specspace_mutations_allowed": False,
        "allowed_output_roots": ["runs/"],
    }


def package_summary(surfaces: dict[str, dict[str, Any]]) -> dict[str, Any]:
    package_index = surfaces["package_index"]
    binding_preview = surfaces["binding_preview"]
    gap_index = surfaces["gap_index"]
    diff_preview = surfaces["compatibility_diff_preview"]
    return {
        "package_count": len(package_index.get("packages", [])),
        "resolved_ref_count": len(binding_preview.get("resolved_refs", [])),
        "unresolved_ref_count": len(binding_preview.get("unresolved_refs", [])),
        "gap_count": len(gap_index.get("gaps", [])),
        "compatibility_status": diff_preview.get("summary", {}).get("status"),
        "breaking_change_count": diff_preview.get("summary", {}).get("breaking_change_count"),
        "next_gap": "review_project_local_ontology_package_authoring",
    }


def build_validate_surface(
    surfaces: dict[str, dict[str, Any]],
    *,
    fixture_path: Path,
) -> dict[str, Any]:
    package_index = surfaces["package_index"]
    package = package_index["packages"][0]
    return {
        "artifact_kind": "ontology_package_authoring_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "status": "passed",
        "review_state": "ready_for_review",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_fixture": relative_path(fixture_path),
        "package": {
            "package_id": package["package_id"],
            "namespace": package["namespace"],
            "version": package["version"],
            "authority_class": package["authority_class"],
            "source_uri": package["source_uri"],
            "materialized_ir": package["materialized_ir"],
        },
        "summary": package_summary(surfaces),
        "authority_boundary": common_authority_boundary("ontology-package-validate"),
    }


def build_preview_surface(
    surfaces: dict[str, dict[str, Any]],
    *,
    fixture_path: Path,
) -> dict[str, Any]:
    package_index = surfaces["package_index"]
    binding_preview = surfaces["binding_preview"]
    gap_index = surfaces["gap_index"]
    diff_preview = surfaces["compatibility_diff_preview"]
    package = package_index["packages"][0]
    return {
        "artifact_kind": "ontology_package_preview",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "status": "ready_for_review",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_fixture": relative_path(fixture_path),
        "package": {
            "package_id": package["package_id"],
            "namespace": package["namespace"],
            "version": package["version"],
            "authority_class": package["authority_class"],
            "source_uri": package["source_uri"],
            "materialized_ir": package["materialized_ir"],
        },
        "resolved_refs": binding_preview.get("resolved_refs", []),
        "unresolved_refs": binding_preview.get("unresolved_refs", []),
        "gap_summary": {
            "gap_count": len(gap_index.get("gaps", [])),
            "gap_ids": [gap.get("gap_id") for gap in gap_index.get("gaps", [])],
        },
        "compatibility_summary": diff_preview.get("summary", {}),
        "required_specgraph_actions": diff_preview.get("required_specgraph_actions", []),
        "compatibility_changes": diff_preview.get("changes", {}),
        "authority_boundary": common_authority_boundary("ontology-package-preview"),
    }


def build_gap_surface(
    surfaces: dict[str, dict[str, Any]],
    *,
    fixture_path: Path,
) -> dict[str, Any]:
    gap_index = surfaces["gap_index"]
    return {
        "artifact_kind": "ontology_package_gap_preview",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "status": "review_required" if gap_index.get("gaps") else "clean",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_fixture": relative_path(fixture_path),
        "summary": {
            "gap_count": len(gap_index.get("gaps", [])),
            "next_gap": "review_ontology_package_gaps" if gap_index.get("gaps") else "none",
        },
        "gaps": gap_index.get("gaps", []),
        "authority_boundary": common_authority_boundary("ontology-package-gaps"),
    }


def build_authoring_surface(mode: str, *, policy_path: Path = POLICY_PATH) -> dict[str, Any]:
    policy = load_json(policy_path)
    fixture_path, adapter_report_path, compatibility_report_path = default_fixture_paths(policy)
    surfaces = build_ontology_import_surfaces(
        fixture_path,
        policy_path=policy_path,
        adapter_report_path=adapter_report_path,
        compatibility_report_path=compatibility_report_path,
        semantic_policy_path=None,
    )
    if mode == "validate":
        return build_validate_surface(surfaces, fixture_path=fixture_path)
    if mode == "preview":
        return build_preview_surface(surfaces, fixture_path=fixture_path)
    if mode == "gaps":
        return build_gap_surface(surfaces, fixture_path=fixture_path)
    raise ValueError(f"Unsupported authoring mode: {mode}")


def output_path_for_mode(mode: str) -> Path:
    try:
        return ROOT / OUTPUTS[mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported authoring mode: {mode}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(OUTPUTS), required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--policy", default=str(POLICY_PATH))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = ROOT / policy_path
    surface = build_authoring_surface(args.mode, policy_path=policy_path)
    if args.write:
        path = write_json(output_path_for_mode(args.mode), surface)
        print(relative_path(path))
    else:
        print(json.dumps(surface, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
