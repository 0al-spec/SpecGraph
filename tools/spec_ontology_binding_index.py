#!/usr/bin/env python3
"""Build a report-only ontology binding index for legacy SpecGraph specs."""

from __future__ import annotations

import argparse
import json
import re
import sys
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
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def slug(value: str) -> str:
    return TOKEN_RE.sub("-", value.lower()).strip("-") or "term"


def symbol_keys(value: str) -> set[str]:
    local = value.rsplit(":", 1)[-1]
    camel_split = CAMEL_BOUNDARY_RE.sub("-", local)
    keys = {slug(local), slug(camel_split), slug(value)}
    keys.update(key.replace("-", "") for key in list(keys))
    return {key for key in keys if key}


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
            entry = {"ontology_ref": fqid, "kind": kind, "symbol": symbol}
            for key in symbol_keys(symbol) | symbol_keys(fqid):
                symbols[key] = entry
    return symbols


def has_ir_ref(ir_symbols: dict[str, dict[str, str]], ontology_ref: str) -> bool:
    return any(symbol["ontology_ref"] == ontology_ref for symbol in ir_symbols.values())


def add_structural_binding(
    bindings: list[dict[str, str]],
    gaps: list[dict[str, str]],
    ir_symbols: dict[str, dict[str, str]],
    *,
    spec_id: str,
    term: str,
    ontology_ref: str,
    kind: str,
    source: str,
) -> None:
    if has_ir_ref(ir_symbols, ontology_ref):
        add_binding(
            bindings,
            term=term,
            ontology_ref=ontology_ref,
            kind=kind,
            source=source,
        )
        return
    gaps.append(
        {
            "gap_id": f"ontology-gap-{spec_id.lower()}-{slug(term)}",
            "term": term,
            "classification": "missing_ontology_ref",
            "source": source,
        }
    )


def add_relation_candidate(
    relation_candidates: list[dict[str, Any]],
    gaps: list[dict[str, str]],
    ir_symbols: dict[str, dict[str, str]],
    *,
    spec_id: str,
    relation_ref: str,
    domain_ref: str,
    range_ref: str,
    source: str,
    target_count: int,
) -> None:
    missing_refs = [
        ref for ref in (relation_ref, domain_ref, range_ref) if not has_ir_ref(ir_symbols, ref)
    ]
    if not missing_refs:
        relation_candidates.append(
            {
                "relation_ref": relation_ref,
                "domain_ref": domain_ref,
                "range_ref": range_ref,
                "source": source,
                "target_count": target_count,
            }
        )
        return
    gaps.append(
        {
            "gap_id": f"ontology-gap-{spec_id.lower()}-{slug(relation_ref)}",
            "term": relation_ref,
            "classification": "missing_ontology_ref",
            "source": source,
        }
    )


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
        add_structural_binding(
            bindings,
            gaps,
            ir_symbols,
            spec_id=spec_id,
            term="spec",
            ontology_ref="sgcore:Spec",
            kind="class",
            source="kind",
        )

    if spec.get("id"):
        add_structural_binding(
            bindings,
            gaps,
            ir_symbols,
            spec_id=spec_id,
            term="node",
            ontology_ref="sgcore:Node",
            kind="class",
            source="id",
        )

    acceptance = spec.get("acceptance")
    if isinstance(acceptance, list) and acceptance:
        add_structural_binding(
            bindings,
            gaps,
            ir_symbols,
            spec_id=spec_id,
            term="acceptance",
            ontology_ref="sgcore:AcceptanceCriterion",
            kind="class",
            source="acceptance",
        )
        add_relation_candidate(
            relation_candidates,
            gaps,
            ir_symbols,
            spec_id=spec_id,
            relation_ref="sgcore:hasAcceptanceCriterion",
            domain_ref="sgcore:Spec",
            range_ref="sgcore:AcceptanceCriterion",
            source="acceptance",
            target_count=len(acceptance),
        )

    acceptance_evidence = spec.get("acceptance_evidence")
    if isinstance(acceptance_evidence, list) and acceptance_evidence:
        add_structural_binding(
            bindings,
            gaps,
            ir_symbols,
            spec_id=spec_id,
            term="acceptance_evidence",
            ontology_ref="sgcore:Evidence",
            kind="class",
            source="acceptance_evidence",
        )
        add_relation_candidate(
            relation_candidates,
            gaps,
            ir_symbols,
            spec_id=spec_id,
            relation_ref="sgcore:evidenceSupportsCriterion",
            domain_ref="sgcore:Evidence",
            range_ref="sgcore:AcceptanceCriterion",
            source="acceptance_evidence",
            target_count=len(acceptance_evidence),
        )

    for key in terminology_keys(spec):
        matched = next(
            (
                ir_symbols.get(symbol_key)
                for symbol_key in symbol_keys(key)
                if symbol_key in ir_symbols
            ),
            None,
        )
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


def resolve_output_path(output: str) -> Path:
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path = output_path.resolve()
    runs_root = (ROOT / "runs").resolve()
    if runs_root not in (output_path, *output_path.parents):
        raise ValueError(f"--output must stay under {relative_path(runs_root)}")
    if output_path.suffix != ".json":
        raise ValueError("--output must be a JSON artifact")
    return output_path


def main() -> int:
    args = parse_args()
    ir_path = Path(args.ontology_ir)
    if not ir_path.is_absolute():
        ir_path = ROOT / ir_path
    specs_root = Path(args.specs_root)
    if not specs_root.is_absolute():
        specs_root = ROOT / specs_root
    try:
        output_path = resolve_output_path(args.output)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    index = build_binding_index(specs_root=specs_root, ir_path=ir_path)
    if args.write:
        path = write_json(output_path, index)
        print(relative_path(path))
    else:
        print(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
