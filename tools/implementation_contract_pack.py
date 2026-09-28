"""Proposal 0047: read-only, explicitly scoped implementation contract preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject shadowed requirements instead of silently keeping the last one."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("spec mappings require string keys")
            if key in result:
                raise ValueError(f"duplicate YAML key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def strings(value: object, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{label} must be a {'possibly empty ' if allow_empty else ''}string list")
    result = [text(item, label) for item in value]
    if len(result) != len(set(result)):
        raise ValueError(f"{label} contains duplicates")
    return result


def validate_observability(contract: object, scenario_ids: set[str]) -> dict:
    if not isinstance(contract, dict):
        raise ValueError("observability must be an object")
    strings(contract.get("non_interference"), "non_interference")
    excluded = strings(contract.get("excluded_attributes"), "excluded_attributes", allow_empty=True)
    obligations = contract.get("obligations")
    if not isinstance(obligations, list) or not obligations:
        raise ValueError("obligations must be a nonempty list")
    ids = set()
    for obligation in obligations:
        if not isinstance(obligation, dict):
            raise ValueError("obligation must be an object")
        identity = text(obligation.get("id"), "obligation.id")
        if identity in ids:
            raise ValueError(f"duplicate obligation: {identity}")
        ids.add(identity)
        text(obligation.get("event"), "event")
        text(obligation.get("boundary"), "boundary")
        attributes = strings(obligation.get("attributes"), "attributes", allow_empty=True)
        strings(obligation.get("expected_outcomes"), "expected_outcomes")
        refs = strings(obligation.get("scenario_ids"), "scenario_ids")
        if set(refs) - scenario_ids:
            raise ValueError(f"unknown scenario reference in {identity}")
        if set(attributes) & set(excluded):
            raise ValueError(f"excluded attribute requested in {identity}")
    return contract


def contained(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"path escapes workspace: {relative}")
    return path


def build_contract_pack(workspace_root: Path, target_spec: str) -> dict:
    """Project one explicit node; no inherited-policy inference or readiness grant."""
    if not re.fullmatch(r"[A-Z][A-Z0-9-]*-SPEC-[0-9]{4,}", target_spec):
        raise ValueError("invalid target spec ID")
    root = workspace_root.expanduser().resolve(strict=True)
    relative = f"specs/nodes/{target_spec}.yaml"
    raw = contained(root, relative).read_bytes()
    node = yaml.load(raw, Loader=UniqueKeyLoader)
    if not isinstance(node, dict) or node.get("id") != target_spec or node.get("kind") != "spec":
        raise ValueError("source must be the requested canonical spec node")
    title = text(node.get("title"), "title")
    status = text(node.get("status"), "status")
    gate = text(node.get("gate_state"), "gate_state")
    acceptance = strings(node.get("acceptance"), "acceptance")
    specification = node.get("specification")
    if not isinstance(specification, dict):
        raise ValueError("specification must be an object")
    scenarios = specification.get("bdd_scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("bdd_scenarios must be a list")
    scenario_ids = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("scenario must be an object")
        identity = text(scenario.get("id"), "scenario.id")
        strings(scenario.get("steps"), "scenario.steps")
        if identity in scenario_ids:
            raise ValueError(f"duplicate scenario: {identity}")
        scenario_ids.add(identity)
    blockers = []
    if gate != "none":
        blockers.append(f"source_gate:{gate}")
    if status not in {"linked", "reviewed", "frozen"}:
        blockers.append(f"source_status:{status}")
    contract = specification.get("observability")
    if contract is None:
        blockers.append("missing_observability_contract")
    else:
        contract = validate_observability(contract, scenario_ids)
    obligations = contract["obligations"] if contract else []
    tests = sorted({ref for item in obligations for ref in item["scenario_ids"]})
    preview_status = "blocked" if blockers else "review_required"
    return {
        "artifact_kind": "implementation_contract_pack_preview",
        "schema_version": 1,
        "proposal_id": "0047",
        "profile": "explicit_node_observability_v1",
        "status": preview_status,
        "blockers": blockers,
        "source": {
            "path": relative,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "spec_id": target_spec,
            "status": status,
            "gate_state": gate,
        },
        "title": title,
        "acceptance": acceptance,
        "specification": specification,
        "observability": contract,
        "context": {
            "refines": strings(node.get("refines", []), "refines", allow_empty=True),
            "depends_on": strings(node.get("depends_on", []), "depends_on", allow_empty=True),
            "inheritance": "not_evaluated",
            "scope": "explicit_target_only",
        },
        "implementation_work_preview": {
            "work_item_id": f"implementation_work::{target_spec}::observability_contract",
            "affected_spec_ids": [target_spec],
            "implementation_reason": "observability_contract",
            "readiness": preview_status,
            "blockers": blockers,
            "required_tests": tests,
            "expected_evidence": [item["id"] for item in obligations],
            "likely_code_refs": [],
            "next_gap": "review_observability_contract_pack",
        },
        "evidence_status": "not_evaluated",
        "canonical_mutations_allowed": False,
        "runtime_code_mutations_allowed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--target-spec", required=True)
    args = parser.parse_args(argv)
    try:
        result = build_contract_pack(args.workspace_root, args.target_spec)
        root = args.workspace_root.expanduser().resolve(strict=True)
        destination = contained(root, f"runs/implementation-contract-packs/{args.target_spec}.json")
        # A symlink into canonical sources must never turn preview output into a mutation.
        expected = root / "runs" / "implementation-contract-packs" / f"{args.target_spec}.json"
        if destination != expected:
            raise ValueError("derived output path must not contain symlinks")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=destination.parent, delete=False
            ) as file:
                temporary = Path(file.name)
                json.dump(result, file, indent=2, sort_keys=True)
                file.write("\n")
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        print(json.dumps({"status": result["status"], "artifact_path": str(destination)}))
        return 2 if result["status"] == "blocked" else 0
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"contract pack input error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
