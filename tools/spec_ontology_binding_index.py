#!/usr/bin/env python3
"""Build a report-only ontology binding index for legacy SpecGraph specs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

from ontology_imports import ROOT, load_json, relative_path, write_json

PROPOSAL_ID = "0134"
SCHEMA_VERSION = 1
DEFAULT_IR_PATH = ROOT / "ontology/packages/specgraph-core/generated/ontology.normalized.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs/spec_ontology_binding_index.json"
SPEC_ROOT = ROOT / "specs/nodes"
TOKEN_RE = re.compile(r"[^a-z0-9]+")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def slug(value: str) -> str:
    return TOKEN_RE.sub("-", value.lower()).strip("-") or "term"


def ontology_symbols(ir: dict[str, Any]) -> dict[str, dict[str, str]]:
    symbols: dict[str, dict[str, str]] = {}
    for section, kind in (("classes", "class"), ("relations", "relation")):
        values = ir.get(section, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            fqid = item.get("fqid")
            symbol = item.get("id")
            if not isinstance(fqid, str) or not isinstance(symbol, str):
                continue
            symbols[symbol.lower()] = {"ontology_ref": fqid, "kind": kind, "symbol": symbol}
            symbols[slug(symbol)] = {"ontology_ref": fqid, "kind": kind, "symbol": symbol}
    return symbols


def terminology_keys(spec: dict[str, Any]) -> list[str]:
    specification = spec.get("specification")
    if not isinstance(specification, dict):
        return []
    terminology = specification.get("terminology")
    if not isinstance(terminology, dict):
        return []
    return sorted(str(key) for key in terminology)


def add_binding(
    bindings: list[dict[str, str]],
    *,
    term: str,
    ontology_ref: str,
    kind: str,
    source: str,
) -> None:
    candidate = {
        "term": term,
        "ontology_ref": ontology_ref,
        "kind": kind,
        "source": source,
    }
    if candidate not in bindings:
        bindings.append(candidate)


def spec_entry(path: Path, ir_symbols: dict[str, dict[str, str]]) -> dict[str, Any]:
    spec = load_yaml(path)
    spec_id = str(spec.get("id", path.stem))
    bindings: list[dict[str, str]] = []
    relation_candidates: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []

    if str(spec.get("kind", "")).lower() == "spec":
        add_binding(
            bindings,
            term="spec",
            ontology_ref="sgcore:Spec",
            kind="class",
            source="kind",
        )

    if spec.get("id"):
        add_binding(
            bindings,
            term="node",
            ontology_ref="sgcore:Node",
            kind="class",
            source="id",
        )

    acceptance = spec.get("acceptance")
    if isinstance(acceptance, list) and acceptance:
        add_binding(
            bindings,
            term="acceptance",
            ontology_ref="sgcore:AcceptanceCriterion",
            kind="class",
            source="acceptance",
        )
        relation_candidates.append(
            {
                "relation_ref": "sgcore:hasAcceptanceCriterion",
                "domain_ref": "sgcore:Spec",
                "range_ref": "sgcore:AcceptanceCriterion",
                "source": "acceptance",
                "target_count": len(acceptance),
            }
        )

    acceptance_evidence = spec.get("acceptance_evidence")
    if isinstance(acceptance_evidence, list) and acceptance_evidence:
        add_binding(
            bindings,
            term="acceptance_evidence",
            ontology_ref="sgcore:Evidence",
            kind="class",
            source="acceptance_evidence",
        )
        relation_candidates.append(
            {
                "relation_ref": "sgcore:evidenceSupportsCriterion",
                "domain_ref": "sgcore:Evidence",
                "range_ref": "sgcore:AcceptanceCriterion",
                "source": "acceptance_evidence",
                "target_count": len(acceptance_evidence),
            }
        )

    for key in terminology_keys(spec):
        normalized = slug(key)
        matched = ir_symbols.get(key.lower()) or ir_symbols.get(normalized)
        if matched:
            add_binding(
                bindings,
                term=key,
                ontology_ref=matched["ontology_ref"],
                kind=matched["kind"],
                source="specification.terminology",
            )
            continue
        gaps.append(
            {
                "gap_id": f"ontology-gap-{spec_id.lower()}-{slug(key)}",
                "term": key,
                "classification": "legacy_unknown_term",
                "source": "specification.terminology",
            }
        )

    return {
        "spec_id": spec_id,
        "path": relative_path(path),
        "status": "legacy_report_only",
        "accepted_bindings": sorted(bindings, key=lambda item: (item["source"], item["term"])),
        "relation_candidates": relation_candidates,
        "gaps": gaps,
    }


def build_binding_index(
    *,
    specs_root: Path = SPEC_ROOT,
    ir_path: Path = DEFAULT_IR_PATH,
) -> dict[str, Any]:
    ir = load_json(ir_path)
    ir_symbols = ontology_symbols(ir)
    entries = [spec_entry(path, ir_symbols) for path in sorted(specs_root.glob("SG-SPEC-*.yaml"))]
    accepted_binding_count = sum(len(entry["accepted_bindings"]) for entry in entries)
    relation_candidate_count = sum(len(entry["relation_candidates"]) for entry in entries)
    gap_count = sum(len(entry["gaps"]) for entry in entries)
    return {
        "artifact_kind": "spec_ontology_binding_index",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "status": "report_only",
        "review_state": "ready_for_review",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "legacy_corpus": True,
        "ontology_ir_ref": relative_path(ir_path),
        "summary": {
            "spec_count": len(entries),
            "accepted_binding_count": accepted_binding_count,
            "relation_candidate_count": relation_candidate_count,
            "gap_count": gap_count,
            "next_gap": "review_legacy_spec_ontology_bindings",
        },
        "entries": entries,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ontology-ir", default=str(DEFAULT_IR_PATH))
    parser.add_argument("--specs-root", default=str(SPEC_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ir_path = Path(args.ontology_ir)
    if not ir_path.is_absolute():
        ir_path = ROOT / ir_path
    specs_root = Path(args.specs_root)
    if not specs_root.is_absolute():
        specs_root = ROOT / specs_root
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    index = build_binding_index(specs_root=specs_root, ir_path=ir_path)
    if args.write:
        path = write_json(output_path, index)
        print(relative_path(path))
    else:
        print(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
