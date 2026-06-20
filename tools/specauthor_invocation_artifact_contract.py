"""Contract validator for SpecAuthorAgent invocation artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0145"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.specauthor.invocation-artifact.v0.1"
PROMPT_CONTRACT_REF = "docs/proposals/0126_specauthor_claim_calibration_prompt_contract.md"
GENERATED_ARTIFACT_CONTRACT_REF = "specgraph.specauthor.generated-artifact.v0.1"
DEFAULT_ARTIFACT_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "specauthor_invocation_artifact_contract"
    / "invocation_ready.json"
)
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "specauthor_invocation_artifact_contract_report.json"

REQUIRED_FRAME_TEXT_FIELDS = (
    "project",
    "subsystem",
    "agent_layer",
    "target_artifact",
    "lifecycle_phase",
)
REQUIRED_FRAME_LIST_FIELDS = (
    "ontology_refs",
    "ontology_layer_refs",
    "model_applicability_refs",
    "domain_refs",
    "context_refs",
)
ONTOLOGY_LAYERS = {"objective", "mechanics", "execution", "meta", "multi_agent"}
SUPPORTED_INVOCATION_MODES = {"draft_authoring", "dry_run", "review_replay"}
SUPPORTED_OPERATOR_DECISIONS = {
    "pending_review",
    "approved_for_materialization",
    "needs_revision",
    "rejected",
}


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


def _has_concrete_text_list(value: Any) -> bool:
    return bool(_text_list(value))


def _invalid_text_list_entries(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return [
        index for index, item in enumerate(value) if not isinstance(item, str) or not item.strip()
    ]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _source_ref(artifact: dict[str, Any], artifact_path: Path | None) -> str:
    source_ref = _text(artifact.get("source_ref"))
    if source_ref:
        return source_ref
    if artifact_path is not None:
        try:
            return artifact_path.relative_to(ROOT).as_posix()
        except ValueError:
            return artifact_path.as_posix()
    return "specauthor_invocation_artifact"


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


def _validate_root(artifact: dict[str, Any], *, source_ref: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if artifact.get("artifact_kind") != "specauthor_invocation_artifact":
        findings.append(
            _finding(
                finding_id="wrong_artifact_kind",
                severity="review_required",
                message=(
                    "SpecAuthor invocation artifacts must use "
                    "artifact_kind=specauthor_invocation_artifact."
                ),
                source_ref=source_ref,
                evidence={"artifact_kind": artifact.get("artifact_kind")},
            )
        )
    if artifact.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="unsupported_schema_version",
                severity="review_required",
                message="specauthor_invocation_artifact schema_version must be 1.",
                source_ref=source_ref,
                evidence={"schema_version": artifact.get("schema_version")},
            )
        )
    if artifact.get("contract_ref") != CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="wrong_contract_ref",
                severity="review_required",
                message=f"contract_ref must be {CONTRACT_REF}.",
                source_ref=source_ref,
                evidence={"contract_ref": artifact.get("contract_ref")},
            )
        )
    if not _text(artifact.get("source_ref")):
        findings.append(
            _finding(
                finding_id="source_ref_missing",
                severity="review_required",
                message="specauthor_invocation_artifact requires a stable source_ref.",
                source_ref=source_ref,
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if artifact.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="authority_expansion",
                    severity="review_required",
                    message=f"{field} must be false.",
                    source_ref=source_ref,
                    evidence={field: artifact.get(field)},
                )
            )
    boundary = artifact.get("authority_boundary")
    if not isinstance(boundary, dict):
        findings.append(
            _finding(
                finding_id="authority_boundary_missing",
                severity="review_required",
                message=(
                    "authority_boundary is required and must keep invocation artifacts review-only."
                ),
                source_ref=source_ref,
            )
        )
        return findings
    invalid_boundary_fields = [
        field
        for field in (
            "may_execute_prompt_agent",
            "may_write_ontology_package",
            "may_write_ontology_lockfile",
            "may_mutate_canonical_specs",
            "may_mark_candidate_accepted",
            "may_import_owner_decision",
        )
        if boundary.get(field) is not False
    ]
    if invalid_boundary_fields:
        findings.append(
            _finding(
                finding_id="authority_expansion",
                severity="review_required",
                message=(
                    "SpecAuthor invocation artifacts must not expand runtime or mutation authority."
                ),
                source_ref=source_ref,
                evidence={"invalid": invalid_boundary_fields},
            )
        )
    return findings


def _validate_invocation(artifact: dict[str, Any], *, source_ref: str) -> list[dict[str, Any]]:
    invocation = artifact.get("invocation")
    if not isinstance(invocation, dict):
        return [
            _finding(
                finding_id="invocation_missing",
                severity="review_required",
                message="SpecAuthor invocation artifact requires invocation metadata.",
                source_ref=source_ref,
            )
        ]
    findings: list[dict[str, Any]] = []
    missing = [
        field
        for field in ("invocation_id", "agent_id", "mode", "prompt_contract_ref")
        if not _text(invocation.get(field))
    ]
    user_intent = invocation.get("user_intent")
    if not isinstance(user_intent, dict) or not _text(user_intent.get("text")):
        missing.append("user_intent.text")
    if missing:
        findings.append(
            _finding(
                finding_id="invocation_incomplete",
                severity="review_required",
                message=(
                    "invocation must include id, agent, mode, prompt contract, "
                    "and user intent text."
                ),
                source_ref=source_ref,
                evidence={"missing": missing},
            )
        )
    if invocation.get("agent_id") != "SpecAuthorAgent":
        findings.append(
            _finding(
                finding_id="unsupported_agent",
                severity="review_required",
                message="This contract currently applies only to SpecAuthorAgent.",
                source_ref=source_ref,
                evidence={"agent_id": invocation.get("agent_id")},
            )
        )
    if _text(invocation.get("mode")) not in SUPPORTED_INVOCATION_MODES:
        findings.append(
            _finding(
                finding_id="unsupported_invocation_mode",
                severity="review_required",
                message="invocation.mode is not supported.",
                source_ref=source_ref,
                evidence={
                    "mode": invocation.get("mode"),
                    "supported_modes": sorted(SUPPORTED_INVOCATION_MODES),
                },
            )
        )
    if invocation.get("prompt_contract_ref") != PROMPT_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="wrong_prompt_contract_ref",
                severity="review_required",
                message=f"invocation.prompt_contract_ref must be {PROMPT_CONTRACT_REF}.",
                source_ref=source_ref,
                evidence={"prompt_contract_ref": invocation.get("prompt_contract_ref")},
            )
        )
    return findings


def _validate_active_frame(artifact: dict[str, Any], *, source_ref: str) -> list[dict[str, Any]]:
    frame = artifact.get("active_frame")
    if not isinstance(frame, dict):
        return [
            _finding(
                finding_id="active_frame_missing",
                severity="review_required",
                message="SpecAuthor invocation artifacts require active_frame.",
                source_ref=source_ref,
            )
        ]
    findings: list[dict[str, Any]] = []
    missing_text = [field for field in REQUIRED_FRAME_TEXT_FIELDS if not _text(frame.get(field))]
    missing_lists = [
        field
        for field in REQUIRED_FRAME_LIST_FIELDS
        if not _has_concrete_text_list(frame.get(field))
    ]
    if missing_text or missing_lists:
        findings.append(
            _finding(
                finding_id="active_frame_incomplete",
                severity="review_required",
                message=(
                    "active_frame must resolve ontology/domain/context/layers plus "
                    "model applicability before invoking SpecAuthor."
                ),
                source_ref=source_ref,
                evidence={"missing_text": missing_text, "missing_lists": missing_lists},
            )
        )
    invalid_layers = [
        layer
        for layer in _text_list(frame.get("ontology_layer_refs"))
        if layer not in ONTOLOGY_LAYERS
    ]
    invalid_layer_entries = _invalid_text_list_entries(frame.get("ontology_layer_refs"))
    if invalid_layers or invalid_layer_entries:
        findings.append(
            _finding(
                finding_id="active_frame_invalid_ontology_layers",
                severity="review_required",
                message="active_frame.ontology_layer_refs must use known ontology layers.",
                source_ref=source_ref,
                evidence={
                    "invalid_layers": invalid_layers,
                    "invalid_entries": invalid_layer_entries,
                    "known_layers": sorted(ONTOLOGY_LAYERS),
                },
            )
        )
    return findings


def _validate_model_applicability(
    artifact: dict[str, Any], *, source_ref: str
) -> list[dict[str, Any]]:
    applicability = artifact.get("model_applicability")
    if not isinstance(applicability, dict):
        return [
            _finding(
                finding_id="model_applicability_missing",
                severity="review_required",
                message="SpecAuthor invocation artifacts require model_applicability review data.",
                source_ref=source_ref,
            )
        ]
    findings: list[dict[str, Any]] = []
    if not _text(applicability.get("package_ref")):
        findings.append(
            _finding(
                finding_id="model_applicability_incomplete",
                severity="review_required",
                message="model_applicability.package_ref is required.",
                source_ref=source_ref,
            )
        )
    for field in ("assumption_refs", "invalidation_trigger_refs"):
        if not _has_concrete_text_list(applicability.get(field)):
            findings.append(
                _finding(
                    finding_id="model_applicability_incomplete",
                    severity="review_required",
                    message=(
                        f"model_applicability.{field} must reference compiler-authored records."
                    ),
                    source_ref=source_ref,
                    evidence={field: applicability.get(field)},
                )
            )
    applies_to = _dict(applicability.get("applies_to"))
    frame = _dict(artifact.get("active_frame"))
    applies_domains = set(_text_list(applies_to.get("domains")))
    frame_domains = set(_text_list(frame.get("domain_refs")))
    if applies_domains and frame_domains and applies_domains.isdisjoint(frame_domains):
        findings.append(
            _finding(
                finding_id="model_applicability_domain_mismatch",
                severity="review_required",
                message=(
                    "active_frame.domain_refs must intersect "
                    "model_applicability.applies_to.domains."
                ),
                source_ref=source_ref,
                evidence={
                    "applies_to_domains": sorted(applies_domains),
                    "domain_refs": sorted(frame_domains),
                },
            )
        )
    return findings


def _validate_validation_chain(
    artifact: dict[str, Any], *, source_ref: str
) -> list[dict[str, Any]]:
    chain = artifact.get("validation_chain")
    if not isinstance(chain, dict):
        return [
            _finding(
                finding_id="validation_chain_missing",
                severity="review_required",
                message="SpecAuthor invocation artifacts require validation_chain.",
                source_ref=source_ref,
            )
        ]
    findings: list[dict[str, Any]] = []
    generated = _dict(chain.get("generated_artifact"))
    contract_report = _dict(chain.get("generated_artifact_contract_report"))
    write_gate_report = _dict(chain.get("write_gate_report"))

    if generated.get("artifact_kind") != "generated_spec_artifact":
        findings.append(
            _finding(
                finding_id="generated_artifact_ref_invalid",
                severity="review_required",
                message=(
                    "validation_chain.generated_artifact must reference generated_spec_artifact."
                ),
                source_ref=source_ref,
                evidence={"artifact_kind": generated.get("artifact_kind")},
            )
        )
    if generated.get("contract_ref") != GENERATED_ARTIFACT_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="generated_artifact_contract_ref_invalid",
                severity="review_required",
                message=(
                    f"generated artifact contract_ref must be {GENERATED_ARTIFACT_CONTRACT_REF}."
                ),
                source_ref=source_ref,
                evidence={"contract_ref": generated.get("contract_ref")},
            )
        )
    if contract_report.get("artifact_kind") != "specauthor_generated_artifact_contract_report":
        findings.append(
            _finding(
                finding_id="generated_artifact_contract_report_missing",
                severity="review_required",
                message="validation_chain must include a generated artifact contract report.",
                source_ref=source_ref,
            )
        )
    elif (
        contract_report.get("ok") is not True or contract_report.get("write_gate_ready") is not True
    ):
        findings.append(
            _finding(
                finding_id="generated_artifact_contract_failed",
                severity="review_required",
                message="Generated artifact contract must pass before invocation is review-ready.",
                source_ref=source_ref,
                evidence={
                    "ok": contract_report.get("ok"),
                    "write_gate_ready": contract_report.get("write_gate_ready"),
                    "finding_count": _dict(contract_report.get("summary")).get("finding_count"),
                },
            )
        )
    if write_gate_report.get("artifact_kind") != "specauthor_ontology_write_gate_report":
        findings.append(
            _finding(
                finding_id="write_gate_report_missing",
                severity="review_required",
                message="validation_chain must include a SpecAuthor ontology write-gate report.",
                source_ref=source_ref,
            )
        )
    elif (
        write_gate_report.get("ok") is not True
        or write_gate_report.get("write_decision") != "allow_graph_write"
        or write_gate_report.get("would_reject_in_hard_gate") is not False
    ):
        findings.append(
            _finding(
                finding_id="write_gate_not_clear",
                severity="review_required",
                message="Write gate must be clear before invocation can be operator-review ready.",
                source_ref=source_ref,
                evidence={
                    "ok": write_gate_report.get("ok"),
                    "write_decision": write_gate_report.get("write_decision"),
                    "would_reject_in_hard_gate": write_gate_report.get("would_reject_in_hard_gate"),
                    "finding_count": _dict(write_gate_report.get("summary")).get("finding_count"),
                },
            )
        )
    return findings


def _validate_operator_decision(
    artifact: dict[str, Any], *, source_ref: str
) -> list[dict[str, Any]]:
    decision = artifact.get("operator_decision")
    if not isinstance(decision, dict):
        return [
            _finding(
                finding_id="operator_decision_missing",
                severity="review_required",
                message="SpecAuthor invocation artifact requires operator_decision state.",
                source_ref=source_ref,
            )
        ]
    findings: list[dict[str, Any]] = []
    state = _text(decision.get("decision_state"))
    if state not in SUPPORTED_OPERATOR_DECISIONS:
        findings.append(
            _finding(
                finding_id="unsupported_operator_decision",
                severity="review_required",
                message="operator_decision.decision_state is not supported.",
                source_ref=source_ref,
                evidence={
                    "decision_state": decision.get("decision_state"),
                    "supported_decisions": sorted(SUPPORTED_OPERATOR_DECISIONS),
                },
            )
        )
    if state == "approved_for_materialization" and not _text(decision.get("reviewer")):
        findings.append(
            _finding(
                finding_id="operator_approval_missing_reviewer",
                severity="review_required",
                message="Approved materialization decisions require reviewer.",
                source_ref=source_ref,
            )
        )
    for field in (
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_write_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_import_owner_decision",
    ):
        if decision.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="operator_decision_authority_expansion",
                    severity="review_required",
                    message=f"operator_decision.{field} must be false in this contract.",
                    source_ref=source_ref,
                    evidence={field: decision.get(field)},
                )
            )
    return findings


def build_specauthor_invocation_artifact_contract_report(
    artifact: dict[str, Any],
    *,
    artifact_path: Path | None = None,
) -> dict[str, Any]:
    source_ref = _source_ref(artifact, artifact_path)
    findings: list[dict[str, Any]] = []
    findings.extend(_validate_root(artifact, source_ref=source_ref))
    findings.extend(_validate_invocation(artifact, source_ref=source_ref))
    findings.extend(_validate_active_frame(artifact, source_ref=source_ref))
    findings.extend(_validate_model_applicability(artifact, source_ref=source_ref))
    findings.extend(_validate_validation_chain(artifact, source_ref=source_ref))
    findings.extend(_validate_operator_decision(artifact, source_ref=source_ref))

    would_reject = bool(findings)
    frame = _dict(artifact.get("active_frame"))
    applicability = _dict(artifact.get("model_applicability"))
    operator_decision = _dict(artifact.get("operator_decision"))
    return {
        "artifact_kind": "specauthor_invocation_artifact_contract_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "source_artifact": {
            "artifact_kind": artifact.get("artifact_kind"),
            "schema_version": artifact.get("schema_version"),
            "contract_ref": artifact.get("contract_ref"),
            "source_ref": source_ref,
        },
        "contract": {
            "contract_ref": CONTRACT_REF,
            "prompt_contract_ref": PROMPT_CONTRACT_REF,
            "generated_artifact_contract_ref": GENERATED_ARTIFACT_CONTRACT_REF,
            "downstream_write_gate": "specauthor-ontology-write-gate",
        },
        "validation_modes": {
            "specauthor_invocation": "typed_review_boundary",
            "prompt_execution": "out_of_scope",
            "operator_decision": "acknowledgement_only",
        },
        "ok": not would_reject,
        "review_state": "review_required" if would_reject else "ready_for_operator_review",
        "invocation_ready": not would_reject,
        "operator_decision_required": operator_decision.get("decision_state") == "pending_review",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "authority_boundary": {
            "may_execute_prompt_agent": False,
            "may_write_ontology_package": False,
            "may_write_ontology_lockfile": False,
            "may_mutate_canonical_specs": False,
            "may_mark_candidate_accepted": False,
            "may_import_owner_decision": False,
        },
        "active_frame_summary": {
            "ontology_ref_count": len(_text_list(frame.get("ontology_refs"))),
            "ontology_layer_refs": _text_list(frame.get("ontology_layer_refs")),
            "model_applicability_refs": _text_list(frame.get("model_applicability_refs")),
            "domain_refs": _text_list(frame.get("domain_refs")),
            "context_refs": _text_list(frame.get("context_refs")),
        },
        "model_applicability_summary": {
            "package_ref": _text(applicability.get("package_ref")),
            "assumption_ref_count": len(_text_list(applicability.get("assumption_refs"))),
            "invalidation_trigger_ref_count": len(
                _text_list(applicability.get("invalidation_trigger_refs"))
            ),
        },
        "findings": findings,
        "warnings": [],
        "summary": {
            "finding_count": len(findings),
            "warning_count": 0,
            "validation_chain_present": isinstance(artifact.get("validation_chain"), dict),
            "operator_decision_state": _text(operator_decision.get("decision_state"), "missing"),
        },
    }


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default=DEFAULT_ARTIFACT_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifact = load_json(args.artifact)
    report = build_specauthor_invocation_artifact_contract_report(
        artifact,
        artifact_path=args.artifact,
    )
    write_report(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and not report["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
