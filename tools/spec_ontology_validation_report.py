#!/usr/bin/env python3
"""Build a typed report-only validation surface for specs against ontology bindings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ontology_imports import ROOT, load_json, relative_path, write_json
from spec_ontology_binding_index import DEFAULT_IR_PATH, build_binding_index

PROPOSAL_ID = "0135"
SCHEMA_VERSION = 1
DEFAULT_OUTPUT_PATH = ROOT / "runs/spec_ontology_validation_report.json"


def relation_contracts(ir: dict[str, Any]) -> dict[str, dict[str, str]]:
    contracts: dict[str, dict[str, str]] = {}
    relations = ir.get("relations", [])
    if not isinstance(relations, list):
        return contracts
    for relation in relations:
        if not isinstance(relation, dict):
            continue
        fqid = relation.get("fqid")
        domain = relation.get("domain")
        range_ref = relation.get("range")
        if isinstance(fqid, str) and isinstance(domain, str) and isinstance(range_ref, str):
            contracts[fqid] = {"domain": domain, "range": range_ref}
    return contracts


def validate_entry(
    entry: dict[str, Any],
    *,
    relations: dict[str, dict[str, str]],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    bindings = entry.get("accepted_bindings", [])
    binding_refs = {
        binding.get("ontology_ref")
        for binding in bindings
        if isinstance(binding, dict) and isinstance(binding.get("ontology_ref"), str)
    }

    if "sgcore:Spec" not in binding_refs:
        findings.append(
            {
                "finding_id": f"{entry['spec_id']}.missing-spec-binding",
                "severity": "warning",
                "classification": "missing_required_binding",
                "message": "Legacy spec entry has no sgcore:Spec binding.",
                "suggested_action": "review_legacy_binding_extraction",
            }
        )
    else:
        checks.append(
            {
                "check_id": "required_binding.sgcore_spec",
                "status": "passed",
                "ontology_ref": "sgcore:Spec",
            }
        )

    for candidate in entry.get("relation_candidates", []):
        if not isinstance(candidate, dict):
            continue
        relation_ref = candidate.get("relation_ref")
        contract = relations.get(relation_ref)
        if not isinstance(relation_ref, str) or contract is None:
            findings.append(
                {
                    "finding_id": f"{entry['spec_id']}.unknown-relation.{relation_ref}",
                    "severity": "warning",
                    "classification": "unknown_relation",
                    "relation_ref": relation_ref,
                    "suggested_action": "emit_ontology_gap",
                }
            )
            continue
        domain_ok = candidate.get("domain_ref") == contract["domain"]
        range_ok = candidate.get("range_ref") == contract["range"]
        if not domain_ok or not range_ok:
            findings.append(
                {
                    "finding_id": f"{entry['spec_id']}.relation-domain-range.{relation_ref}",
                    "severity": "warning",
                    "classification": "relation_domain_range_mismatch",
                    "relation_ref": relation_ref,
                    "expected": contract,
                    "actual": {
                        "domain": candidate.get("domain_ref"),
                        "range": candidate.get("range_ref"),
                    },
                    "suggested_action": "review_relation_candidate",
                }
            )
            continue
        checks.append(
            {
                "check_id": f"relation_contract.{relation_ref}",
                "status": "passed",
                "relation_ref": relation_ref,
                "domain_ref": contract["domain"],
                "range_ref": contract["range"],
            }
        )

    for gap in entry.get("gaps", []):
        if not isinstance(gap, dict):
            continue
        findings.append(
            {
                "finding_id": f"{entry['spec_id']}.gap.{gap.get('term')}",
                "severity": "warning",
                "classification": "unknown_legacy_term",
                "term": gap.get("term"),
                "source": gap.get("source"),
                "gap_ref": gap.get("gap_id"),
                "suggested_action": "review_ontology_gap",
            }
        )

    return {
        "spec_id": entry["spec_id"],
        "path": entry["path"],
        "validation_status": "report_only_findings" if findings else "report_only_clean",
        "checks": checks,
        "findings": findings,
    }


def build_validation_report(*, ir_path: Path = DEFAULT_IR_PATH) -> dict[str, Any]:
    binding_index = build_binding_index(ir_path=ir_path)
    ir = load_json(ir_path)
    relations = relation_contracts(ir)
    entries = [
        validate_entry(entry, relations=relations)
        for entry in binding_index.get("entries", [])
        if isinstance(entry, dict)
    ]
    finding_count = sum(len(entry["findings"]) for entry in entries)
    warning_count = sum(
        1
        for entry in entries
        for finding in entry["findings"]
        if finding.get("severity") == "warning"
    )
    passed_check_count = sum(len(entry["checks"]) for entry in entries)
    return {
        "artifact_kind": "spec_ontology_validation_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "status": "report_only",
        "review_state": "ready_for_review",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "ontology_ir_ref": relative_path(ir_path),
        "source_binding_index_kind": binding_index["artifact_kind"],
        "validation_modes": {
            "legacy_specs": "report_only",
            "generated_artifacts": "review_required",
            "hard_gate_enabled": False,
        },
        "summary": {
            "spec_count": len(entries),
            "finding_count": finding_count,
            "warning_count": warning_count,
            "passed_check_count": passed_check_count,
            "next_gap": "review_spec_ontology_validation_findings",
        },
        "entries": entries,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ontology-ir", default=str(DEFAULT_IR_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ir_path = Path(args.ontology_ir)
    if not ir_path.is_absolute():
        ir_path = ROOT / ir_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    report = build_validation_report(ir_path=ir_path)
    if args.write:
        path = write_json(output_path, report)
        print(relative_path(path))
    else:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
