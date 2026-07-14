"""Materialize review-only candidate spec YAML previews."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from spec_yaml import dump_canonical_yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0153"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-materialization.v0.1"
CANDIDATE_GRAPH_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph.v0.1"
REPAIR_LOOP_CONTRACT_REF = "specgraph.idea-to-spec.candidate-repair-loop.v0.1"
DEFAULT_CANDIDATE_GRAPH_PATH = (
    ROOT / "tests" / "fixtures" / "candidate_repair_loop" / "candidate_graph_repairable.json"
)
DEFAULT_REPAIR_LOOP_PATH = ROOT / "runs" / "candidate_repair_loop_report.json"
DEFAULT_OUTPUT_DIR = ROOT / "runs" / "materialized_candidate_specs"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "candidate_spec_materialization_report.json"
DISPLAY_ALIAS_MAX_LENGTH = 64
PRODUCT_SOURCE_REF_RE = re.compile(
    r"^product://(?P<candidate_id>[a-z0-9][a-z0-9-]{1,62}[a-z0-9])/.+$"
)
DISPLAY_ALIAS_PRIVATE_MARKERS = (
    "/Users/",
    "/home/",
    "/private/",
    "/tmp/",
    "/var/folders/",
    "-----BEGIN",
    "api-key",
    "apikey",
    "api_key",
    "bearer ",
    "token=",
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _text_list(value: Any) -> list[str]:
    return [item.strip() for item in _list(value) if isinstance(item, str) and item.strip()]


def _display_alias(value: Any) -> str:
    if not isinstance(value, str) or any(ord(character) < 32 for character in value):
        return ""
    alias = " ".join(value.split())
    if not alias or len(alias) > DISPLAY_ALIAS_MAX_LENGTH:
        return ""
    lowered = alias.lower()
    if any(marker.lower() in lowered for marker in DISPLAY_ALIAS_PRIVATE_MARKERS):
        return ""
    return alias


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _relative_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finding(
    *,
    finding_id: str,
    severity: str,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "message": message,
        "source": "candidate_spec_materialization",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
    }


def _validate_candidate_graph(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if candidate_graph.get("artifact_kind") != "candidate_spec_graph":
        findings.append(
            _finding(
                finding_id="candidate_graph_wrong_artifact_kind",
                severity="review_required",
                message="Materialization requires candidate_spec_graph input.",
                evidence={"artifact_kind": candidate_graph.get("artifact_kind")},
            )
        )
    if candidate_graph.get("contract_ref") != CANDIDATE_GRAPH_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="candidate_graph_contract_ref_unsupported",
                severity="review_required",
                message=(
                    f"candidate_spec_graph contract_ref must be {CANDIDATE_GRAPH_CONTRACT_REF}."
                ),
                evidence={"contract_ref": candidate_graph.get("contract_ref")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if candidate_graph.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="candidate_graph_authority_expanded",
                    severity="review_required",
                    message=f"candidate graph {field} must be false.",
                    evidence={field: candidate_graph.get(field)},
                )
            )
    if not _nodes(candidate_graph):
        findings.append(
            _finding(
                finding_id="candidate_graph_nodes_missing",
                severity="review_required",
                message="Materialization requires at least one candidate node.",
            )
        )
    for node in _nodes(candidate_graph):
        if node.get("display_alias") not in (None, "") and not _display_alias(
            node.get("display_alias")
        ):
            findings.append(
                _finding(
                    finding_id="candidate_node_display_alias_invalid",
                    severity="review_required",
                    message=(
                        "Materialization requires public-safe single-line candidate "
                        "display aliases."
                    ),
                    evidence={"node_id": _text(node.get("id"))},
                )
            )
    return findings


def _validate_repair_loop(repair_loop: dict[str, Any] | None) -> list[dict[str, Any]]:
    if repair_loop is None:
        return []
    findings: list[dict[str, Any]] = []
    if repair_loop.get("artifact_kind") != "candidate_repair_loop_report":
        findings.append(
            _finding(
                finding_id="repair_loop_wrong_artifact_kind",
                severity="review_required",
                message="Repair preview input must be candidate_repair_loop_report.",
                evidence={"artifact_kind": repair_loop.get("artifact_kind")},
            )
        )
    if repair_loop.get("contract_ref") != REPAIR_LOOP_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="repair_loop_contract_ref_unsupported",
                severity="review_required",
                message=(
                    f"candidate_repair_loop_report contract_ref must be {REPAIR_LOOP_CONTRACT_REF}."
                ),
                evidence={"contract_ref": repair_loop.get("contract_ref")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if repair_loop.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="repair_loop_authority_expanded",
                    severity="review_required",
                    message=f"repair loop {field} must be false.",
                    evidence={field: repair_loop.get(field)},
                )
            )
    return findings


def _nodes(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [node for node in _list(candidate_graph.get("nodes")) if isinstance(node, dict)]


def _edges(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [edge for edge in _list(candidate_graph.get("edges")) if isinstance(edge, dict)]


def _candidate_scope(
    candidate_graph: dict[str, Any],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    source_ref = _text(candidate_graph.get("source_ref"))
    if not source_ref:
        return {}, [
            _finding(
                finding_id="candidate_materialization_scope_missing",
                severity="review_required",
                message="Materialization requires candidate graph source_ref provenance.",
            )
        ]
    product_match = PRODUCT_SOURCE_REF_RE.fullmatch(source_ref)
    if product_match:
        candidate_id = product_match.group("candidate_id")
        return {
            "namespace": candidate_id,
            "derivation": "product_source_ref",
            "source_ref_sha256": hashlib.sha256(source_ref.encode("utf-8")).hexdigest(),
        }, []
    if source_ref.startswith("product://"):
        return {}, [
            _finding(
                finding_id="candidate_materialization_product_scope_invalid",
                severity="review_required",
                message=(
                    "Product candidate source_ref must contain a stable lowercase candidate slug."
                ),
                evidence={
                    "source_ref_sha256": hashlib.sha256(source_ref.encode("utf-8")).hexdigest()
                },
            )
        ]
    source_digest = hashlib.sha256(source_ref.encode("utf-8")).hexdigest()
    return {
        "namespace": f"source-{source_digest[:12]}",
        "derivation": "source_ref_digest",
        "source_ref_sha256": source_digest,
    }, []


def _materialized_id(candidate_scope: str, candidate_node_id: str) -> str:
    return (
        f"CANDIDATE-{_slug(candidate_scope, 'candidate').upper()}-"
        f"{_slug(candidate_node_id, 'spec').upper()}"
    )


def _materialized_filename(candidate_scope: str, candidate_node_id: str) -> str:
    return f"{_materialized_id(candidate_scope, candidate_node_id)}.yaml"


def _edge_materializes_dependency(edge: dict[str, Any]) -> bool:
    if edge.get("materialization_dependency") is False:
        return False
    if edge.get("review_only") is True:
        return False
    return True


def _candidate_graph_for_materialization(
    candidate_graph: dict[str, Any],
    repair_loop: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    preview = _dict((repair_loop or {}).get("revised_candidate_graph_preview"))
    if preview and _nodes(preview):
        return preview, "repair_loop_preview"
    return candidate_graph, "candidate_graph"


def _depends_on_for(node_id: str, graph: dict[str, Any], id_map: dict[str, str]) -> list[str]:
    depends_on: list[str] = []
    for edge in _edges(graph):
        if not _edge_materializes_dependency(edge):
            continue
        if _text(edge.get("from")) != node_id:
            continue
        target = _text(edge.get("to"))
        materialized = id_map.get(target)
        if materialized and materialized not in depends_on:
            depends_on.append(materialized)
    return depends_on


def _statements(items: list[Any]) -> list[str]:
    statements = []
    for item in items:
        if not isinstance(item, dict):
            continue
        statement = _text(item.get("statement") or item.get("description") or item.get("id"))
        if statement:
            statements.append(statement)
    return statements


def _build_spec_yaml(
    *,
    node: dict[str, Any],
    graph: dict[str, Any],
    id_map: dict[str, str],
    output_path: Path,
    generated_at: str,
    source_ref: str,
) -> dict[str, Any]:
    node_id = _text(node.get("id"), "candidate-node")
    candidate_title = _text(node.get("title"), node_id)
    display_alias = _display_alias(node.get("display_alias"))
    requirements = [item for item in _list(node.get("requirements")) if isinstance(item, dict)]
    acceptance_criteria = [
        item for item in _list(node.get("acceptance_criteria")) if isinstance(item, dict)
    ]
    claims = [item for item in _list(node.get("claims")) if isinstance(item, dict)]
    gaps = [item for item in _list(node.get("gaps")) if isinstance(item, dict)]
    acceptance = _statements(acceptance_criteria) or _statements(requirements)
    if not acceptance:
        acceptance = ["Review candidate requirements and acceptance criteria before promotion."]
    return {
        "id": id_map[node_id],
        "title": display_alias or candidate_title,
        "kind": "spec",
        "created_at": generated_at,
        "updated_at": generated_at,
        "status": "stub",
        "maturity": 0.0,
        "depends_on": _depends_on_for(node_id, graph, id_map),
        "relates_to": [],
        "inputs": [source_ref],
        "outputs": [_relative_ref(output_path)],
        "allowed_paths": [_relative_ref(output_path)],
        "acceptance": acceptance,
        "acceptance_evidence": [],
        "prompt": _text(
            node.get("description"),
            f"Review materialized candidate node {node_id} before canonical promotion.",
        ),
        "specification": {
            "materialization_mode": "candidate_review_preview",
            "candidate_source_id": node_id,
            "candidate_display_alias": display_alias or None,
            "candidate_source_title": candidate_title,
            "candidate_kind": _text(node.get("kind")),
            "description": _text(node.get("description")),
            "source_event_refs": _text_list(node.get("source_event_refs")),
            "ontology_refs": _text_list(node.get("ontology_refs")),
            "domain_refs": _text_list(node.get("domain_refs")),
            "context_refs": _text_list(node.get("context_refs")),
            "requirements": requirements,
            "acceptance_criteria": acceptance_criteria,
            "claims": claims,
            "gaps": gaps,
        },
        "gate_state": "review_pending",
        "required_human_action": "review_candidate_spec_materialization",
    }


def build_candidate_spec_materialization_report(
    *,
    candidate_graph: dict[str, Any],
    repair_loop: dict[str, Any] | None = None,
    candidate_graph_path: Path | None = None,
    repair_loop_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    findings = _validate_candidate_graph(candidate_graph) + _validate_repair_loop(repair_loop)
    candidate_scope, scope_findings = _candidate_scope(candidate_graph)
    findings.extend(scope_findings)
    graph, source_kind = _candidate_graph_for_materialization(candidate_graph, repair_loop)
    if source_kind == "repair_loop_preview":
        findings.extend(_validate_candidate_graph(graph))
    blocking_findings = [
        finding for finding in findings if finding.get("severity") == "review_required"
    ]
    generated_at = _now_iso()
    source_ref = _text(graph.get("source_ref")) or (
        _relative_ref(candidate_graph_path)
        if candidate_graph_path is not None
        else "candidate_graph"
    )
    materialized_files: list[dict[str, Any]] = []
    local_files_written: list[str] = []
    if not blocking_findings:
        nodes = _nodes(graph)
        scope_namespace = candidate_scope["namespace"]
        id_map = {
            _text(node.get("id"), f"candidate-node-{index}"): _materialized_id(
                scope_namespace, _text(node.get("id"), f"candidate-node-{index}")
            )
            for index, node in enumerate(nodes, start=1)
        }
        for node in nodes:
            node_id = _text(node.get("id"), "candidate-node")
            output_path = output_dir / _materialized_filename(scope_namespace, node_id)
            spec_yaml = _build_spec_yaml(
                node=node,
                graph=graph,
                id_map=id_map,
                output_path=output_path,
                generated_at=generated_at,
                source_ref=source_ref,
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(dump_canonical_yaml(spec_yaml), encoding="utf-8")
            local_ref = _relative_ref(output_path)
            local_files_written.append(local_ref)
            materialized_files.append(
                {
                    "candidate_node_id": node_id,
                    "display_alias": _display_alias(node.get("display_alias")) or None,
                    "materialized_id": spec_yaml["id"],
                    "path": local_ref,
                    "promotion_path": local_ref,
                }
            )
    ready = not blocking_findings and bool(materialized_files)
    return {
        "artifact_kind": "candidate_spec_materialization_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": generated_at,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_candidate_graph": {
            "artifact_kind": candidate_graph.get("artifact_kind"),
            "contract_ref": candidate_graph.get("contract_ref"),
            "source_ref": _relative_ref(candidate_graph_path)
            if candidate_graph_path is not None
            else _text(candidate_graph.get("source_ref"), "unknown"),
        },
        "source_repair_loop": {
            "artifact_kind": (repair_loop or {}).get("artifact_kind"),
            "contract_ref": (repair_loop or {}).get("contract_ref"),
            "source_ref": _relative_ref(repair_loop_path) if repair_loop_path is not None else None,
        },
        "materialization_source": source_kind,
        "candidate_scope": candidate_scope or None,
        "materialized_files": materialized_files,
        "promotion_request": {
            "path_argument": "--path",
            "paths": [item["promotion_path"] for item in materialized_files],
            "platform_artifact_kind": "platform_graph_repository_promotion_request",
        },
        "readiness": {
            "ready": ready,
            "review_state": "materialized_candidate_review_ready"
            if ready
            else "candidate_materialization_review_required",
            "blocked_by": [finding["finding_id"] for finding in blocking_findings],
            "next_artifact": "Platform graph-repository promotion-request",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_intent_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
        },
        "findings": blocking_findings,
        "warnings": [],
        "local_files_written": local_files_written,
        "summary": {
            "status": "materialized_candidate_review_ready"
            if ready
            else "candidate_materialization_review_required",
            "materialized_file_count": len(materialized_files),
            "candidate_node_count": len(_nodes(graph)),
            "finding_count": len(blocking_findings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-graph", default=DEFAULT_CANDIDATE_GRAPH_PATH, type=Path)
    parser.add_argument("--repair-loop", type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate_graph = load_json(args.candidate_graph)
    repair_loop = load_json(args.repair_loop) if args.repair_loop else None
    report = build_candidate_spec_materialization_report(
        candidate_graph=candidate_graph,
        repair_loop=repair_loop,
        candidate_graph_path=args.candidate_graph,
        repair_loop_path=args.repair_loop,
        output_dir=args.output_dir,
    )
    write_json(report, args.output)
    print(
        f"{report['readiness']['review_state']}: "
        f"{report['summary']['materialized_file_count']} files"
    )
    if args.strict and not report["readiness"]["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
