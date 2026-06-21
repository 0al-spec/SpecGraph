"""Build the final read-only gate before Platform promotion request handoff."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0154"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.promotion-gate.v0.1"
PRE_SIB_CONTRACT_REF = "specgraph.idea-to-spec.pre-sib-coherence-report.v0.1"
REPAIR_LOOP_CONTRACT_REF = "specgraph.idea-to-spec.candidate-repair-loop.v0.1"
MATERIALIZATION_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-materialization.v0.1"
DEFAULT_PRE_SIB_PATH = ROOT / "runs" / "pre_sib_coherence_report.json"
DEFAULT_REPAIR_LOOP_PATH = ROOT / "runs" / "candidate_repair_loop_report.json"
DEFAULT_MATERIALIZATION_PATH = ROOT / "runs" / "candidate_spec_materialization_report.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_to_spec_promotion_gate.json"
PROMOTION_PATH_PREFIXES = ("specs/", "docs/proposals/", "runs/")


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
        "source": "idea_to_spec_promotion_gate",
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
        "may_open_pull_request": False,
        "may_publish_read_model": False,
    }


def _validate_artifact(
    *,
    artifact: dict[str, Any],
    artifact_name: str,
    expected_kind: str,
    expected_contract: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if artifact.get("artifact_kind") != expected_kind:
        findings.append(
            _finding(
                finding_id=f"{artifact_name}_wrong_artifact_kind",
                severity="review_required",
                message=f"{artifact_name} must be {expected_kind}.",
                evidence={"artifact_kind": artifact.get("artifact_kind")},
            )
        )
    if artifact.get("contract_ref") != expected_contract:
        findings.append(
            _finding(
                finding_id=f"{artifact_name}_contract_ref_unsupported",
                severity="review_required",
                message=f"{artifact_name} contract_ref must be {expected_contract}.",
                evidence={"contract_ref": artifact.get("contract_ref")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if artifact.get(field) is not False:
            findings.append(
                _finding(
                    finding_id=f"{artifact_name}_authority_expanded",
                    severity="review_required",
                    message=f"{artifact_name} {field} must be false.",
                    evidence={field: artifact.get(field)},
                )
            )
    return findings


def _promotion_path_allowed(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or "/../" in f"/{normalized}/":
        return False
    return any(normalized.startswith(prefix) for prefix in PROMOTION_PATH_PREFIXES)


def _promotion_paths(materialization: dict[str, Any]) -> list[str]:
    request_paths = _text_list(_dict(materialization.get("promotion_request")).get("paths"))
    if request_paths:
        return request_paths
    return [
        _text(item.get("promotion_path") or item.get("path"))
        for item in _list(materialization.get("materialized_files"))
        if isinstance(item, dict) and _text(item.get("promotion_path") or item.get("path"))
    ]


def _readiness_ready(artifact: dict[str, Any]) -> bool:
    return _dict(artifact.get("readiness")).get("ready") is True


def _pre_sib_original_blocked(pre_sib: dict[str, Any], materialization: dict[str, Any]) -> bool:
    if _readiness_ready(pre_sib):
        return False
    return _text(materialization.get("materialization_source")) != "repair_loop_preview"


def _gate_findings(
    *,
    pre_sib: dict[str, Any],
    repair_loop: dict[str, Any],
    materialization: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings = (
        _validate_artifact(
            artifact=pre_sib,
            artifact_name="pre_sib_report",
            expected_kind="pre_sib_coherence_report",
            expected_contract=PRE_SIB_CONTRACT_REF,
        )
        + _validate_artifact(
            artifact=repair_loop,
            artifact_name="repair_loop",
            expected_kind="candidate_repair_loop_report",
            expected_contract=REPAIR_LOOP_CONTRACT_REF,
        )
        + _validate_artifact(
            artifact=materialization,
            artifact_name="materialization_report",
            expected_kind="candidate_spec_materialization_report",
            expected_contract=MATERIALIZATION_CONTRACT_REF,
        )
    )
    warnings: list[dict[str, Any]] = []

    if _pre_sib_original_blocked(pre_sib, materialization):
        blocked_by = _text_list(_dict(pre_sib.get("readiness")).get("blocked_by"))
        findings.append(
            _finding(
                finding_id="pre_sib_not_ready_without_repair_preview",
                severity="review_required",
                message=(
                    "Original pre-SIB report is not ready and materialization did not "
                    "use a repair loop preview."
                ),
                evidence={"blocked_by": blocked_by},
            )
        )
    elif not _readiness_ready(pre_sib):
        blocked_by = _text_list(_dict(pre_sib.get("readiness")).get("blocked_by"))
        warnings.append(
            _finding(
                finding_id="pre_sib_findings_repaired_by_preview",
                severity="warning",
                message=(
                    "Original pre-SIB findings are allowed only because repair preview was used."
                ),
                evidence={"blocked_by": blocked_by},
            )
        )

    if not _readiness_ready(repair_loop):
        findings.append(
            _finding(
                finding_id="repair_loop_not_ready",
                severity="review_required",
                message="Repair loop must be ready before promotion handoff.",
                evidence={"readiness": _dict(repair_loop.get("readiness"))},
            )
        )

    context_required_count = _dict(repair_loop.get("summary")).get("context_required_count", 0)
    if not isinstance(context_required_count, int):
        context_required_count = 0
    if context_required_count > 0:
        findings.append(
            _finding(
                finding_id="repair_context_required",
                severity="review_required",
                message="Owner/operator context is still required before Platform promotion.",
                evidence={"context_required_count": context_required_count},
            )
        )

    if not _readiness_ready(materialization):
        findings.append(
            _finding(
                finding_id="materialization_not_ready",
                severity="review_required",
                message="Candidate spec materialization must be ready before promotion handoff.",
                evidence={"readiness": _dict(materialization.get("readiness"))},
            )
        )

    paths = _promotion_paths(materialization)
    if not paths:
        findings.append(
            _finding(
                finding_id="promotion_paths_missing",
                severity="review_required",
                message="Platform promotion request requires at least one materialized path.",
            )
        )
    for index, path in enumerate(paths):
        if not _promotion_path_allowed(path):
            findings.append(
                _finding(
                    finding_id="promotion_path_not_allowed",
                    severity="review_required",
                    message="Promotion paths must stay under specs/, docs/proposals/, or runs/.",
                    evidence={"index": index, "path": path},
                )
            )

    materialized_count = len(_list(materialization.get("materialized_files")))
    if paths and materialized_count and len(paths) != materialized_count:
        findings.append(
            _finding(
                finding_id="promotion_path_count_mismatch",
                severity="review_required",
                message="Promotion path count must match materialized file count.",
                evidence={
                    "promotion_path_count": len(paths),
                    "materialized_file_count": materialized_count,
                },
            )
        )
    return findings, warnings


def build_idea_to_spec_promotion_gate(
    *,
    pre_sib: dict[str, Any],
    repair_loop: dict[str, Any],
    materialization: dict[str, Any],
    pre_sib_path: Path | None = None,
    repair_loop_path: Path | None = None,
    materialization_path: Path | None = None,
) -> dict[str, Any]:
    findings, warnings = _gate_findings(
        pre_sib=pre_sib,
        repair_loop=repair_loop,
        materialization=materialization,
    )
    promotion_paths = _promotion_paths(materialization)
    ready = not findings
    return {
        "artifact_kind": "idea_to_spec_promotion_gate",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "pre_sib": _source_artifact(pre_sib, pre_sib_path),
            "repair_loop": _source_artifact(repair_loop, repair_loop_path),
            "materialization": _source_artifact(materialization, materialization_path),
        },
        "metric_snapshot": {
            "pre_sib": _dict(pre_sib.get("metrics")),
            "repair_delta": _dict(repair_loop.get("metric_delta_projection")),
            "materialized_file_count": len(_list(materialization.get("materialized_files"))),
            "promotion_path_count": len(promotion_paths),
        },
        "promotion_request": {
            "path_argument": "--path",
            "paths": promotion_paths if ready else [],
            "platform_artifact_kind": "platform_graph_repository_promotion_request",
            "next_command": "platform.py graph-repository promotion-request",
        },
        "readiness": {
            "ready": ready,
            "review_state": "ready_for_platform_promotion_request"
            if ready
            else "idea_to_spec_promotion_blocked",
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "Platform graph-repository promotion-request"
            if ready
            else "owner/operator repair before promotion",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_intent_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
        },
        "findings": findings,
        "warnings": warnings,
        "summary": {
            "status": "ready_for_platform_promotion_request"
            if ready
            else "idea_to_spec_promotion_blocked",
            "finding_count": len(findings),
            "warning_count": len(warnings),
            "promotion_path_count": len(promotion_paths) if ready else 0,
            "materialized_file_count": len(_list(materialization.get("materialized_files"))),
        },
    }


def _source_artifact(artifact: dict[str, Any], path: Path | None) -> dict[str, Any]:
    return {
        "artifact_kind": artifact.get("artifact_kind"),
        "contract_ref": artifact.get("contract_ref"),
        "proposal_id": artifact.get("proposal_id"),
        "source_ref": _relative_ref(path) if path is not None else None,
        "readiness": _dict(artifact.get("readiness")),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pre-sib", default=DEFAULT_PRE_SIB_PATH, type=Path)
    parser.add_argument("--repair-loop", default=DEFAULT_REPAIR_LOOP_PATH, type=Path)
    parser.add_argument("--materialization", default=DEFAULT_MATERIALIZATION_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    pre_sib = load_json(args.pre_sib)
    repair_loop = load_json(args.repair_loop)
    materialization = load_json(args.materialization)
    report = build_idea_to_spec_promotion_gate(
        pre_sib=pre_sib,
        repair_loop=repair_loop,
        materialization=materialization,
        pre_sib_path=args.pre_sib,
        repair_loop_path=args.repair_loop,
        materialization_path=args.materialization,
    )
    write_json(report, args.output)
    print(
        f"{report['readiness']['review_state']}: "
        f"{report['summary']['promotion_path_count']} promotion paths"
    )
    if args.strict and not report["readiness"]["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
