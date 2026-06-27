"""Build a review-only materialized candidate preview from a rerun preview."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0167"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.rerun-materialization.v0.1"
RERUN_PREVIEW_CONTRACT_REF = "specgraph.idea-to-spec.rerun-preview.v0.1"
CANDIDATE_GRAPH_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph.v0.1"
DEFAULT_RERUN_PREVIEW_PATH = ROOT / "runs" / "idea_to_spec_rerun_preview.json"
DEFAULT_CANDIDATE_GRAPH_PATH = ROOT / "runs" / "candidate_spec_graph.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_to_spec_rerun_materialization.json"

RAW_TRACE_FIELDS = {
    "operator_note",
    "operator_notes",
    "private_note",
    "raw_intent",
    "raw_intent_text",
    "raw_model_output",
    "raw_operator_note",
    "raw_prompt",
    "raw_response",
    "raw_text",
}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _relative_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _public_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _public_safe(item)
            for key, item in value.items()
            if isinstance(key, str) and key not in RAW_TRACE_FIELDS and not key.startswith("raw_")
        }
    if isinstance(value, list):
        return [_public_safe(item) for item in value]
    return value


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
        "source": "idea_to_spec_rerun_materialization",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_apply_answers_to_source_artifacts": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_accept_ontology_terms": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
    }


def _validate_inputs(
    *,
    rerun_preview: dict[str, Any],
    candidate_graph: dict[str, Any],
    candidate_graph_path: Path | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    expected = (
        (
            "rerun_preview",
            rerun_preview,
            "idea_to_spec_rerun_preview",
            RERUN_PREVIEW_CONTRACT_REF,
        ),
        (
            "candidate_graph",
            candidate_graph,
            "candidate_spec_graph",
            CANDIDATE_GRAPH_CONTRACT_REF,
        ),
    )
    for name, artifact, artifact_kind, contract_ref in expected:
        if artifact.get("artifact_kind") != artifact_kind:
            findings.append(
                _finding(
                    finding_id=f"{name}_wrong_artifact_kind",
                    severity="review_required",
                    message=f"{name} must use artifact_kind {artifact_kind}.",
                    evidence={"artifact_kind": artifact.get("artifact_kind")},
                )
            )
        if artifact.get("contract_ref") != contract_ref:
            findings.append(
                _finding(
                    finding_id=f"{name}_contract_ref_unsupported",
                    severity="review_required",
                    message=f"{name} contract_ref must be {contract_ref}.",
                    evidence={"contract_ref": artifact.get("contract_ref")},
                )
            )
        if artifact.get("schema_version") != SCHEMA_VERSION:
            findings.append(
                _finding(
                    finding_id=f"{name}_schema_version_unsupported",
                    severity="review_required",
                    message=f"{name} schema_version must be 1.",
                    evidence={"schema_version": artifact.get("schema_version")},
                )
            )
        for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
            if artifact.get(field) is not False:
                findings.append(
                    _finding(
                        finding_id=f"{name}_authority_expanded",
                        severity="review_required",
                        message=f"{name} {field} must be false.",
                        evidence={field: artifact.get(field)},
                    )
                )
    readiness = _dict(rerun_preview.get("readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="rerun_preview_not_ready",
                severity="review_required",
                message="Rerun materialization requires ready idea_to_spec_rerun_preview.",
                evidence={"readiness": readiness},
            )
        )
    candidate_readiness = _dict(candidate_graph.get("pre_sib_readiness"))
    if candidate_readiness and candidate_readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="candidate_graph_not_ready_for_materialization",
                severity="review_required",
                message="Rerun materialization requires candidate graph pre-SIB readiness.",
                evidence={"pre_sib_readiness": candidate_readiness},
            )
        )
    preview_candidate_source = _text(
        _dict(_dict(rerun_preview.get("source_artifacts")).get("candidate_graph")).get("source_ref")
    )
    expected_candidate_source = (
        _relative_ref(candidate_graph_path)
        if candidate_graph_path
        else "inline:candidate_spec_graph"
    )
    if preview_candidate_source and preview_candidate_source != expected_candidate_source:
        findings.append(
            _finding(
                finding_id="rerun_preview_candidate_graph_mismatch",
                severity="review_required",
                message="Rerun preview must be built from the same candidate graph input.",
                evidence={
                    "rerun_preview_candidate_graph_source_ref": preview_candidate_source,
                    "candidate_graph_source_ref": expected_candidate_source,
                },
            )
        )
    return findings


def _resolved_ontology_gap_index(rerun_preview: dict[str, Any]) -> dict[str, dict[str, Any]]:
    gap_preview = _dict(_dict(rerun_preview.get("rerun_preview")).get("ontology_gap_preview"))
    index: dict[str, dict[str, Any]] = {}
    for raw_item in _list(gap_preview.get("resolved_ontology_gaps")):
        item = _dict(raw_item)
        gap_id = _text(item.get("gap_id"))
        if gap_id:
            index[gap_id] = item
    return index


def _resolved_ontology_gap_matches(
    resolved: dict[str, Any],
    *,
    node_id: str,
    gap: dict[str, Any],
) -> bool:
    if _text(gap.get("kind")) != "ontology_gap":
        return False
    if _text(resolved.get("node_id")) and _text(resolved.get("node_id")) != node_id:
        return False
    if _text(resolved.get("term")) and _text(resolved.get("term")) != _text(gap.get("term")):
        return False
    if _text(resolved.get("source_ref")) and _text(resolved.get("source_ref")) != _text(
        gap.get("source_ref")
    ):
        return False
    return True


def _candidate_gap_index_key(*, node_id: str, gap_id: str) -> str:
    return f"{node_id}.gaps.{gap_id}"


def _resolved_candidate_gap_index(rerun_preview: dict[str, Any]) -> dict[str, dict[str, Any]]:
    gap_preview = _dict(_dict(rerun_preview.get("rerun_preview")).get("candidate_gap_preview"))
    index: dict[str, dict[str, Any]] = {}
    for raw_item in _list(gap_preview.get("resolved_candidate_gaps")):
        item = _dict(raw_item)
        node_id = _text(item.get("node_id"))
        gap_id = _text(item.get("gap_id"))
        if node_id and gap_id:
            index[_candidate_gap_index_key(node_id=node_id, gap_id=gap_id)] = item
    return index


def _resolved_candidate_gap_matches(
    resolved: dict[str, Any],
    *,
    node_id: str,
    gap: dict[str, Any],
) -> bool:
    if _text(gap.get("kind")) == "ontology_gap":
        return False
    if _text(resolved.get("node_id")) and _text(resolved.get("node_id")) != node_id:
        return False
    target_ref = _text(resolved.get("target_ref"))
    if target_ref and target_ref != f"{node_id}.gaps.{_text(gap.get('id'))}":
        return False
    if _text(resolved.get("kind")) and _text(resolved.get("kind")) != _text(gap.get("kind")):
        return False
    if _text(resolved.get("source_ref")) and _text(resolved.get("source_ref")) != _text(
        gap.get("source_ref")
    ):
        return False
    if _text(resolved.get("statement")) and _text(resolved.get("statement")) != _text(
        gap.get("statement")
    ):
        return False
    return True


def _candidate_graph_counts(candidate_graph: dict[str, Any]) -> dict[str, int]:
    nodes = [_dict(item) for item in _list(candidate_graph.get("nodes"))]
    return {
        "node_count": len(nodes),
        "edge_count": len(_list(candidate_graph.get("edges"))),
        "gap_count": sum(len(_list(node.get("gaps"))) for node in nodes),
        "requirement_count": sum(len(_list(node.get("requirements"))) for node in nodes),
        "acceptance_criteria_count": sum(
            len(_list(node.get("acceptance_criteria"))) for node in nodes
        ),
        "claim_count": sum(len(_list(node.get("claims"))) for node in nodes),
    }


def _refresh_candidate_graph_summary(candidate_graph: dict[str, Any]) -> None:
    summary = dict(_dict(candidate_graph.get("summary")))
    summary.update(_candidate_graph_counts(candidate_graph))
    candidate_graph["summary"] = summary


def _empty_delta(candidate_graph: dict[str, Any]) -> dict[str, Any]:
    unresolved_ontology_gap_ids: list[str] = []
    unresolved_candidate_gap_ids: list[str] = []
    for raw_node in _list(candidate_graph.get("nodes")):
        node = _dict(raw_node)
        for raw_gap in _list(node.get("gaps")):
            gap = _dict(raw_gap)
            gap_id = _text(gap.get("id"))
            if not gap_id:
                continue
            if _text(gap.get("kind")) == "ontology_gap":
                unresolved_ontology_gap_ids.append(gap_id)
            else:
                unresolved_candidate_gap_ids.append(gap_id)
    return {
        "removed_gap_ids": [],
        "unresolved_ontology_gap_ids": unresolved_ontology_gap_ids,
        "unresolved_candidate_gap_ids": unresolved_candidate_gap_ids,
        "resolved_ontology_gap_count": 0,
        "unresolved_ontology_gap_count": len(unresolved_ontology_gap_ids),
        "resolved_candidate_gap_count": 0,
        "unresolved_candidate_gap_count": len(unresolved_candidate_gap_ids),
        "ontology_resolution_records": [],
        "candidate_resolution_records": [],
        "resolution_records": [],
    }


def _materialize_candidate_graph_preview(
    *,
    rerun_preview: dict[str, Any],
    candidate_graph: dict[str, Any],
    candidate_graph_preview_ref: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved_ontology_index = _resolved_ontology_gap_index(rerun_preview)
    resolved_candidate_index = _resolved_candidate_gap_index(rerun_preview)
    preview = copy.deepcopy(candidate_graph)
    removed_gap_ids: list[str] = []
    ontology_resolution_records: list[dict[str, Any]] = []
    candidate_resolution_records: list[dict[str, Any]] = []
    resolution_records: list[dict[str, Any]] = []
    unresolved_ontology_gap_ids: list[str] = []
    unresolved_candidate_gap_ids: list[str] = []
    for raw_node in _list(preview.get("nodes")):
        node = _dict(raw_node)
        remaining_gaps: list[Any] = []
        node_ontology_resolutions: list[dict[str, Any]] = []
        node_candidate_resolutions: list[dict[str, Any]] = []
        node_id = _text(node.get("id"))
        for raw_gap in _list(node.get("gaps")):
            gap = _dict(raw_gap)
            gap_id = _text(gap.get("id"))
            gap_kind = _text(gap.get("kind"))
            resolved_ontology = resolved_ontology_index.get(gap_id)
            if resolved_ontology and _resolved_ontology_gap_matches(
                resolved_ontology,
                node_id=node_id,
                gap=gap,
            ):
                record = {
                    "gap_id": gap_id,
                    "term": _text(gap.get("term")),
                    "source_ref": _text(gap.get("source_ref")),
                    "decision_id": _text(resolved_ontology.get("decision_id")),
                    "decision_term": _text(resolved_ontology.get("decision_term")),
                    "match_kind": _text(resolved_ontology.get("match_kind")),
                    "confidence": _text(resolved_ontology.get("confidence")),
                    "match": _public_safe(_dict(resolved_ontology.get("match"))),
                    "resolution_preview": _public_safe(
                        _dict(resolved_ontology.get("resolution_preview"))
                    ),
                }
                record = {
                    key: value for key, value in record.items() if value not in ("", None, [], {})
                }
                node_ontology_resolutions.append(record)
                ontology_resolution_records.append({"node_id": node_id, **record})
                resolution_records.append(
                    {"resolution_source": "ontology_gap_preview", "node_id": node_id, **record}
                )
                removed_gap_ids.append(gap_id)
                continue
            resolved_candidate = resolved_candidate_index.get(
                _candidate_gap_index_key(node_id=node_id, gap_id=gap_id)
            )
            if resolved_candidate and _resolved_candidate_gap_matches(
                resolved_candidate,
                node_id=node_id,
                gap=gap,
            ):
                record = {
                    "gap_id": gap_id,
                    "gap_kind": gap_kind,
                    "source_ref": _text(gap.get("source_ref")),
                    "statement": _text(gap.get("statement")),
                    "request_id": _text(resolved_candidate.get("request_id")),
                    "answer_kind": _text(resolved_candidate.get("answer_kind")),
                    "resolution_kind": _text(resolved_candidate.get("resolution_kind")),
                    "match_kind": _text(resolved_candidate.get("match_kind")),
                    "confidence": _text(resolved_candidate.get("confidence")),
                    "match": _public_safe(_dict(resolved_candidate.get("match"))),
                    "resolution_preview": _public_safe(
                        _dict(resolved_candidate.get("resolution_preview"))
                    ),
                }
                record = {
                    key: value for key, value in record.items() if value not in ("", None, [], {})
                }
                node_candidate_resolutions.append(record)
                candidate_resolution_records.append({"node_id": node_id, **record})
                resolution_records.append(
                    {"resolution_source": "candidate_gap_preview", "node_id": node_id, **record}
                )
                removed_gap_ids.append(gap_id)
                continue
            remaining_gaps.append(raw_gap)
            if gap_id and gap_kind == "ontology_gap":
                unresolved_ontology_gap_ids.append(gap_id)
            elif gap_id:
                unresolved_candidate_gap_ids.append(gap_id)
        node["gaps"] = remaining_gaps
        if node_ontology_resolutions:
            existing_resolutions = [
                item
                for item in _list(node.get("ontology_gap_resolutions"))
                if isinstance(item, dict)
            ]
            node["ontology_gap_resolutions"] = existing_resolutions + node_ontology_resolutions
        if node_candidate_resolutions:
            existing_resolutions = [
                item
                for item in _list(node.get("candidate_gap_resolutions"))
                if isinstance(item, dict)
            ]
            node["candidate_gap_resolutions"] = existing_resolutions + node_candidate_resolutions
    preview["source_ref"] = candidate_graph_preview_ref
    _refresh_candidate_graph_summary(preview)
    preview["rerun_materialization"] = {
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "state": "review_only",
        "removed_gap_ids": removed_gap_ids,
        "resolution_count": len(resolution_records),
        "ontology_resolution_count": len(ontology_resolution_records),
        "candidate_resolution_count": len(candidate_resolution_records),
    }
    delta = {
        "removed_gap_ids": removed_gap_ids,
        "unresolved_ontology_gap_ids": unresolved_ontology_gap_ids,
        "unresolved_candidate_gap_ids": unresolved_candidate_gap_ids,
        "resolved_ontology_gap_count": len(ontology_resolution_records),
        "unresolved_ontology_gap_count": len(unresolved_ontology_gap_ids),
        "resolved_candidate_gap_count": len(candidate_resolution_records),
        "unresolved_candidate_gap_count": len(unresolved_candidate_gap_ids),
        "ontology_resolution_records": ontology_resolution_records,
        "candidate_resolution_records": candidate_resolution_records,
        "resolution_records": resolution_records,
    }
    return preview, delta


def build_idea_to_spec_rerun_materialization(
    *,
    rerun_preview: dict[str, Any],
    candidate_graph: dict[str, Any],
    rerun_preview_path: Path | None = None,
    candidate_graph_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    findings = _validate_inputs(
        rerun_preview=rerun_preview,
        candidate_graph=candidate_graph,
        candidate_graph_path=candidate_graph_path,
    )
    candidate_graph_preview_ref = (
        f"{_relative_ref(output_path)}#candidate_graph_preview"
        if output_path
        else "inline:idea_to_spec_rerun_materialization#candidate_graph_preview"
    )
    if findings:
        candidate_graph_preview = copy.deepcopy(candidate_graph)
        candidate_graph_preview["source_ref"] = candidate_graph_preview_ref
        _refresh_candidate_graph_summary(candidate_graph_preview)
        delta = _empty_delta(candidate_graph_preview)
    else:
        candidate_graph_preview, delta = _materialize_candidate_graph_preview(
            rerun_preview=rerun_preview,
            candidate_graph=candidate_graph,
            candidate_graph_preview_ref=candidate_graph_preview_ref,
        )
    ready = not findings
    return {
        "artifact_kind": "idea_to_spec_rerun_materialization",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "rerun_preview": {
                "artifact_kind": rerun_preview.get("artifact_kind"),
                "contract_ref": rerun_preview.get("contract_ref"),
                "source_ref": (
                    _relative_ref(rerun_preview_path)
                    if rerun_preview_path
                    else "inline:idea_to_spec_rerun_preview"
                ),
            },
            "candidate_graph": {
                "artifact_kind": candidate_graph.get("artifact_kind"),
                "contract_ref": candidate_graph.get("contract_ref"),
                "source_ref": (
                    _relative_ref(candidate_graph_path)
                    if candidate_graph_path
                    else "inline:candidate_spec_graph"
                ),
            },
        },
        "materialization_preview": {
            "candidate_graph_preview": _public_safe(candidate_graph_preview),
            "delta": delta,
        },
        "readiness": {
            "ready": ready,
            "review_state": (
                "rerun_materialization_ready" if ready else "rerun_materialization_review_required"
            ),
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "runs/candidate_spec_graph.json",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_idea_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
            "raw_operator_note_published": False,
        },
        "findings": findings,
        "summary": {
            "status": (
                "rerun_materialization_ready" if ready else "rerun_materialization_review_required"
            ),
            "resolved_ontology_gap_count": delta["resolved_ontology_gap_count"],
            "unresolved_ontology_gap_count": delta["unresolved_ontology_gap_count"],
            "resolved_candidate_gap_count": delta["resolved_candidate_gap_count"],
            "unresolved_candidate_gap_count": delta["unresolved_candidate_gap_count"],
            "removed_gap_count": len(delta["removed_gap_ids"]),
            "finding_count": len(findings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rerun-preview", default=DEFAULT_RERUN_PREVIEW_PATH, type=Path)
    parser.add_argument("--candidate-graph", default=DEFAULT_CANDIDATE_GRAPH_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_idea_to_spec_rerun_materialization(
        rerun_preview=load_json(args.rerun_preview),
        candidate_graph=load_json(args.candidate_graph),
        rerun_preview_path=args.rerun_preview,
        candidate_graph_path=args.candidate_graph,
        output_path=args.output,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('removed_gap_count', 0)} gaps removed in preview -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
