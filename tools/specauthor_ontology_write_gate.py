"""Ontology-aware write gate for SpecAuthor-generated graph artifacts."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TERM_BINDING_GATE_PATH = ROOT / "tools" / "ontology_term_binding_gate.py"

_TERM_GATE_SPEC = importlib.util.spec_from_file_location(
    "specauthor_ontology_term_binding_gate",
    TERM_BINDING_GATE_PATH,
)
if _TERM_GATE_SPEC is None or _TERM_GATE_SPEC.loader is None:
    raise RuntimeError("Cannot load ontology_term_binding_gate.py")
_TERM_GATE = importlib.util.module_from_spec(_TERM_GATE_SPEC)
_TERM_GATE_SPEC.loader.exec_module(_TERM_GATE)

DEFAULT_TERM_POLICY_PATH = _TERM_GATE.DEFAULT_POLICY_PATH
build_term_binding_gate_report = _TERM_GATE.build_term_binding_gate_report
load_json = _TERM_GATE.load_json

PROPOSAL_ID = "0136"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "specauthor_ontology_write_gate_report.json"

REQUIRED_FRAME_LIST_FIELDS = ("ontology_refs", "domain_refs", "context_refs")
REQUIRED_FRAME_TEXT_FIELDS = ("project", "target_artifact", "lifecycle_phase")
DECISION_CLAIM_TYPES = {"decision", "invariant", "security_constraint"}
STRONG_CLAIM_TYPES = DECISION_CLAIM_TYPES | {
    "constraint",
    "architectural_decision",
    "runtime_behavior",
    "product_claim",
    "security_claim",
}
LOW_RELIABILITY_VALUES = {"R0", "R1", "R2"}
HIGH_RELIABILITY_VALUES = {"R3", "R4", "R5"}
VALID_F_VALUES = {"F0", "F1", "F2", "F3", "F4", "F5"}
VALID_R_VALUES = {"R0", "R1", "R2", "R3", "R4", "R5"}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) and value else default


def _source_ref(artifact: dict[str, Any], artifact_path: Path | None) -> str:
    source_ref = _text(artifact.get("source_ref"))
    if source_ref:
        return source_ref
    if artifact_path is None:
        return "generated_artifact"
    try:
        return artifact_path.relative_to(ROOT).as_posix()
    except ValueError:
        return artifact_path.as_posix()


def _finding(
    *,
    finding_id: str,
    severity: str,
    message: str,
    source_ref: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "message": message,
        "source_ref": source_ref,
        "evidence": evidence or {},
    }


def _has_nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _has_nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _claim_id(claim: dict[str, Any], index: int) -> str:
    return _text(claim.get("id"), f"claim[{index}]")


def _claim_type(claim: dict[str, Any]) -> str:
    return _text(claim.get("type"), "claim")


def _is_strong_claim(claim: dict[str, Any]) -> bool:
    claim_type = _claim_type(claim)
    return claim_type in STRONG_CLAIM_TYPES or _text(claim.get("strength")) == "strong"


def _r_rank(value: str) -> int | None:
    if len(value) != 2 or value[0] != "R":
        return None
    try:
        return int(value[1])
    except ValueError:
        return None


def _validate_active_frame(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    frame = artifact.get("active_frame")
    completion_request = artifact.get("context_completion_request")

    if not isinstance(frame, dict):
        findings.append(
            _finding(
                finding_id="active_frame_missing",
                severity="review_required",
                message="Generated graph artifacts require active_frame before graph write.",
                source_ref=source_ref,
            )
        )
        return findings, warnings

    missing_text = [
        field for field in REQUIRED_FRAME_TEXT_FIELDS if not _has_nonempty_text(frame.get(field))
    ]
    missing_lists = [
        field for field in REQUIRED_FRAME_LIST_FIELDS if not _has_nonempty_list(frame.get(field))
    ]
    if missing_text or missing_lists:
        findings.append(
            _finding(
                finding_id="active_frame_incomplete",
                severity="review_required",
                message=(
                    "active_frame must resolve project, target artifact, lifecycle, "
                    "ontology, domain, and context."
                ),
                source_ref=source_ref,
                evidence={"missing_text": missing_text, "missing_lists": missing_lists},
            )
        )

    if isinstance(completion_request, dict):
        findings.append(
            _finding(
                finding_id="context_completion_required",
                severity="review_required",
                message="ContextCompletionRequest cannot be persisted as a final graph spec.",
                source_ref=source_ref,
                evidence=completion_request,
            )
        )
    elif completion_request is not None:
        warnings.append(
            _finding(
                finding_id="context_completion_request_invalid_shape",
                severity="warning",
                message="context_completion_request should be an object when present.",
                source_ref=source_ref,
            )
        )

    return findings, warnings


def _validate_claims(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    claims = artifact.get("claims")

    if not isinstance(claims, list):
        inventory = _dict(artifact.get("claim_inventory"))
        if inventory.get("strong_claims_present") is False:
            return findings, warnings
        findings.append(
            _finding(
                finding_id="claim_records_missing",
                severity="review_required",
                message=(
                    "Generated graph artifacts require claims[] or "
                    "claim_inventory.strong_claims_present=false."
                ),
                source_ref=source_ref,
            )
        )
        return findings, warnings

    for index, raw_claim in enumerate(claims):
        claim = _dict(raw_claim)
        if not claim:
            findings.append(
                _finding(
                    finding_id="claim_record_invalid",
                    severity="review_required",
                    message="claims[] entries must be objects.",
                    source_ref=source_ref,
                    evidence={"index": index},
                )
            )
            continue
        if not _is_strong_claim(claim):
            continue
        calibration = _dict(claim.get("calibration"))
        claim_ref = _claim_id(claim, index)
        f_value = _text(calibration.get("F"))
        r_value = _text(calibration.get("R"))
        g_value = _dict(calibration.get("G"))
        missing: list[str] = []
        if f_value not in VALID_F_VALUES:
            missing.append("calibration.F")
        if r_value not in VALID_R_VALUES:
            missing.append("calibration.R")
        if not _has_nonempty_list(g_value.get("applies_to")):
            missing.append("calibration.G.applies_to")
        if missing:
            findings.append(
                _finding(
                    finding_id="strong_claim_without_fgr",
                    severity="review_required",
                    message="Strong claims require F/G/R calibration with explicit scope.",
                    source_ref=source_ref,
                    evidence={"claim": claim_ref, "missing": missing},
                )
            )
            continue

        if _claim_type(claim) in DECISION_CLAIM_TYPES and r_value in LOW_RELIABILITY_VALUES:
            findings.append(
                _finding(
                    finding_id="low_reliability_claim_marked_decision",
                    severity="review_required",
                    message=(
                        "Low-reliability claims must be emitted as hypothesis, risk, "
                        "or proposal, not decisions."
                    ),
                    source_ref=source_ref,
                    evidence={"claim": claim_ref, "type": _claim_type(claim), "R": r_value},
                )
            )

        evidence_refs = _list(claim.get("evidence_refs"))
        if not evidence_refs and r_value in HIGH_RELIABILITY_VALUES:
            findings.append(
                _finding(
                    finding_id="unsupported_high_reliability_claim",
                    severity="review_required",
                    message="Claims without evidence_refs cannot claim R3-R5 reliability.",
                    source_ref=source_ref,
                    evidence={"claim": claim_ref, "R": r_value},
                )
            )

        assumptions = _list(g_value.get("assumptions"))
        if not assumptions:
            warnings.append(
                _finding(
                    finding_id="strong_claim_without_assumptions",
                    severity="warning",
                    message="Strong claim scope should list assumptions.",
                    source_ref=source_ref,
                    evidence={"claim": claim_ref},
                )
            )

    return findings, warnings


def build_specauthor_ontology_write_gate_report(
    artifact: dict[str, Any],
    *,
    term_policy: dict[str, Any],
    artifact_path: Path | None = None,
) -> dict[str, Any]:
    source_ref = _source_ref(artifact, artifact_path)
    active_frame_findings, active_frame_warnings = _validate_active_frame(
        artifact,
        source_ref=source_ref,
    )
    claim_findings, claim_warnings = _validate_claims(artifact, source_ref=source_ref)
    term_report = build_term_binding_gate_report(
        artifact,
        policy=term_policy,
        artifact_path=artifact_path,
    )
    term_findings = _list(term_report.get("findings"))
    term_warnings = _list(term_report.get("warnings"))

    findings = active_frame_findings + claim_findings + term_findings
    warnings = active_frame_warnings + claim_warnings + term_warnings
    would_reject = bool(findings)
    context_completion_pending = any(
        finding.get("finding_id") == "context_completion_required" for finding in findings
    )
    review_state = (
        "context_completion_required"
        if context_completion_pending
        else "review_required"
        if would_reject
        else "clear"
    )
    write_decision = "reject_graph_write" if would_reject else "allow_graph_write"

    return {
        "artifact_kind": "specauthor_ontology_write_gate_report",
        "schema_version": 1,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "source_artifact": {
            "artifact_kind": artifact.get("artifact_kind"),
            "source_ref": source_ref,
        },
        "policy_refs": {
            "claim_prompt_contract": (
                "docs/proposals/0126_specauthor_claim_calibration_prompt_contract.md"
            ),
            "term_binding_policy": "tools/ontology_term_binding_policy.json",
        },
        "validation_modes": {
            "generated_artifacts": "hard_write_gate",
            "legacy_specs": "not_applicable",
        },
        "ok": not would_reject,
        "review_state": review_state,
        "write_decision": write_decision,
        "would_reject_in_hard_gate": would_reject,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "authority_boundary": {
            "may_write_ontology_package": False,
            "may_write_ontology_lockfile": False,
            "may_mutate_canonical_specs": False,
            "may_mark_candidate_accepted": False,
            "may_execute_prompt_agent": False,
        },
        "term_binding_gate": {
            "artifact_kind": term_report.get("artifact_kind"),
            "review_state": term_report.get("review_state"),
            "would_reject_in_hard_gate": term_report.get("would_reject_in_hard_gate"),
            "summary": term_report.get("summary", {}),
        },
        "findings": findings,
        "warnings": warnings,
        "summary": {
            "finding_count": len(findings),
            "warning_count": len(warnings),
            "active_frame_finding_count": len(active_frame_findings),
            "claim_finding_count": len(claim_findings),
            "term_binding_finding_count": len(term_findings),
        },
    }


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--term-policy", default=DEFAULT_TERM_POLICY_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifact = load_json(args.artifact)
    term_policy = load_json(args.term_policy)
    report = build_specauthor_ontology_write_gate_report(
        artifact,
        term_policy=term_policy,
        artifact_path=args.artifact,
    )
    write_report(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and report["would_reject_in_hard_gate"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
