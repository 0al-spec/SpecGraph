"""Contract validator for SpecAuthor-generated graph artifact drafts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0137"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.specauthor.generated-artifact.v0.1"
DEFAULT_ARTIFACT_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "specauthor_generated_artifact_contract"
    / "generated_spec_ready.json"
)
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "specauthor_generated_artifact_contract_report.json"
PROMPT_CONTRACT_REF = "docs/proposals/0126_specauthor_claim_calibration_prompt_contract.md"
WRITE_GATE_TARGET = "specauthor-ontology-write-gate"
ONTOLOGY_LAYERS = {"objective", "mechanics", "execution", "meta", "multi_agent"}
STRONG_CLAIM_TYPES = {
    "constraint",
    "decision",
    "invariant",
    "architectural_decision",
    "runtime_behavior",
    "product_claim",
    "security_claim",
    "security_constraint",
}

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
    "domain_refs",
    "context_refs",
)
SUPPORTED_TARGET_ARTIFACT_KINDS = {
    "ADR",
    "AgentPassportDraft",
    "HCSConfigSpec",
    "HypercodeSpec",
    "Proposal",
    "RFCSection",
}
SUPPORTED_DRAFT_FORMATS = {"markdown", "yaml", "json"}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) and value.strip() else default


def _has_concrete_text_list(value: Any) -> bool:
    return isinstance(value, list) and any(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _text_list(value: Any) -> list[str]:
    return [item.strip() for item in _list(value) if isinstance(item, str) and bool(item.strip())]


def _is_strong_claim(claim: dict[str, Any]) -> bool:
    claim_type = _text(claim.get("type"), "claim")
    return claim_type in STRONG_CLAIM_TYPES or _text(claim.get("strength")) == "strong"


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
    return "generated_artifact"


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


def _validate_root(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if artifact.get("artifact_kind") != "generated_spec_artifact":
        findings.append(
            _finding(
                finding_id="wrong_artifact_kind",
                severity="review_required",
                message=(
                    "SpecAuthor contract artifacts must use artifact_kind=generated_spec_artifact."
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
                message="generated_spec_artifact schema_version must be 1.",
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
                message="generated_spec_artifact requires a stable source_ref.",
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
    authority_boundary = artifact.get("authority_boundary")
    if authority_boundary is not None and not isinstance(authority_boundary, dict):
        findings.append(
            _finding(
                finding_id="authority_expansion",
                severity="review_required",
                message="authority_boundary must not expand producer authority.",
                source_ref=source_ref,
                evidence={"authority_boundary": authority_boundary},
            )
        )
    if isinstance(authority_boundary, dict):
        invalid_boundary_fields = [
            field
            for field in (
                "may_execute_prompt_agent",
                "may_write_ontology_package",
                "may_write_ontology_lockfile",
                "may_mutate_canonical_specs",
                "may_mark_candidate_accepted",
            )
            if authority_boundary.get(field) is not False
        ]
        if invalid_boundary_fields:
            findings.append(
                _finding(
                    finding_id="authority_expansion",
                    severity="review_required",
                    message="authority_boundary must keep generated artifacts review-only.",
                    source_ref=source_ref,
                    evidence={"invalid": invalid_boundary_fields},
                )
            )
    return findings


def _validate_producer(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    producer = artifact.get("producer")
    if not isinstance(producer, dict):
        return [
            _finding(
                finding_id="producer_missing",
                severity="review_required",
                message="generated_spec_artifact requires producer metadata.",
                source_ref=source_ref,
            )
        ]

    missing: list[str] = []
    if _text(producer.get("agent_id")) != "SpecAuthorAgent":
        missing.append("producer.agent_id")
    if _text(producer.get("prompt_contract_ref")) != PROMPT_CONTRACT_REF:
        missing.append("producer.prompt_contract_ref")
    if not _text(producer.get("invocation_ref")):
        missing.append("producer.invocation_ref")
    if missing:
        return [
            _finding(
                finding_id="producer_incomplete",
                severity="review_required",
                message=(
                    "producer metadata must identify SpecAuthorAgent, prompt "
                    "contract, and invocation."
                ),
                source_ref=source_ref,
                evidence={"missing_or_invalid": missing},
            )
        ]
    return []


def _validate_active_frame(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    frame = artifact.get("active_frame")
    if not isinstance(frame, dict):
        return [
            _finding(
                finding_id="active_frame_missing",
                severity="review_required",
                message="generated_spec_artifact requires active_frame.",
                source_ref=source_ref,
            )
        ]

    missing_text = [field for field in REQUIRED_FRAME_TEXT_FIELDS if not _text(frame.get(field))]
    missing_lists = [
        field
        for field in REQUIRED_FRAME_LIST_FIELDS
        if not _has_concrete_text_list(frame.get(field))
    ]
    findings: list[dict[str, Any]] = []
    if missing_text or missing_lists:
        findings.append(
            _finding(
                finding_id="active_frame_incomplete",
                severity="review_required",
                message=(
                    "active_frame must resolve project, subsystem, artifact, ontology, "
                    "ontology layer, domain, and context."
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
    if invalid_layers:
        findings.append(
            _finding(
                finding_id="active_frame_invalid_ontology_layers",
                severity="review_required",
                message="active_frame.ontology_layer_refs must use known ontology layers.",
                source_ref=source_ref,
                evidence={
                    "invalid_layers": invalid_layers,
                    "known_layers": sorted(ONTOLOGY_LAYERS),
                },
            )
        )
    return findings


def _validate_target_artifact(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    target = artifact.get("target_artifact")
    if not isinstance(target, dict):
        return [
            _finding(
                finding_id="target_artifact_missing",
                severity="review_required",
                message="generated_spec_artifact requires target_artifact metadata.",
                source_ref=source_ref,
            )
        ]

    missing: list[str] = []
    if _text(target.get("kind")) not in SUPPORTED_TARGET_ARTIFACT_KINDS:
        missing.append("target_artifact.kind")
    if not _text(target.get("title")):
        missing.append("target_artifact.title")
    if _text(target.get("intended_status")) not in {"draft", "proposal", "review_required"}:
        missing.append("target_artifact.intended_status")
    if target.get("canonical_write_intent") is not False:
        missing.append("target_artifact.canonical_write_intent")
    findings: list[dict[str, Any]] = []
    if missing:
        findings.append(
            _finding(
                finding_id="target_artifact_incomplete",
                severity="review_required",
                message="target_artifact must be an explicitly review-scoped draft target.",
                source_ref=source_ref,
                evidence={"missing_or_invalid": missing},
            )
        )

    frame = artifact.get("active_frame")
    frame_target = _text(_dict(frame).get("target_artifact"))
    metadata_target = _text(target.get("kind"))
    if frame_target and metadata_target and frame_target != metadata_target:
        findings.append(
            _finding(
                finding_id="target_artifact_identity_conflict",
                severity="review_required",
                message=("active_frame.target_artifact must match target_artifact.kind."),
                source_ref=source_ref,
                evidence={
                    "active_frame.target_artifact": frame_target,
                    "target_artifact.kind": metadata_target,
                },
            )
        )
    return findings


def _validate_draft(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    draft = artifact.get("draft")
    if not isinstance(draft, dict):
        return [
            _finding(
                finding_id="draft_missing",
                severity="review_required",
                message="generated_spec_artifact requires a draft payload.",
                source_ref=source_ref,
            )
        ]

    missing: list[str] = []
    if _text(draft.get("format")) not in SUPPORTED_DRAFT_FORMATS:
        missing.append("draft.format")
    if not _text(draft.get("content")):
        missing.append("draft.content")
    if not missing:
        return []
    return [
        _finding(
            finding_id="draft_incomplete",
            severity="review_required",
            message="draft payload must declare format and non-empty content.",
            source_ref=source_ref,
            evidence={"missing_or_invalid": missing},
        )
    ]


def _validate_materialization_intent(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    intent = artifact.get("materialization_intent")
    if not isinstance(intent, dict):
        return [
            _finding(
                finding_id="materialization_intent_missing",
                severity="review_required",
                message="generated_spec_artifact requires materialization_intent.",
                source_ref=source_ref,
            )
        ]

    invalid: list[str] = []
    if _text(intent.get("mode")) != "review_required":
        invalid.append("materialization_intent.mode")
    if intent.get("requires_write_gate") is not True:
        invalid.append("materialization_intent.requires_write_gate")
    if _text(intent.get("write_gate")) != WRITE_GATE_TARGET:
        invalid.append("materialization_intent.write_gate")
    for field in (
        "may_write_ontology_package",
        "may_write_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
    ):
        if intent.get(field) is not False:
            invalid.append(f"materialization_intent.{field}")

    completion_request = artifact.get("context_completion_request")
    if completion_request is not None and not isinstance(completion_request, dict):
        invalid.append("context_completion_request")
    if isinstance(completion_request, dict):
        invalid.append("context_completion_request")

    if not invalid:
        return []
    return [
        _finding(
            finding_id="materialization_intent_invalid",
            severity="review_required",
            message="materialization_intent must route to review-required write-gate flow only.",
            source_ref=source_ref,
            evidence={"invalid": invalid},
        )
    ]


def _validate_record_lists(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    invalid = [
        field
        for field in ("new_terms", "term_bindings", "ontology_gaps", "claims")
        if not isinstance(artifact.get(field), list)
    ]
    findings: list[dict[str, Any]] = []
    if invalid:
        findings.append(
            _finding(
                finding_id="record_lists_invalid",
                severity="review_required",
                message=(
                    "generated_spec_artifact requires list-valued term, gap, and claim records."
                ),
                source_ref=source_ref,
                evidence={"invalid": invalid},
            )
        )

    malformed_term_bindings = [
        index
        for index, entry in enumerate(_list(artifact.get("term_bindings")))
        if not isinstance(entry, dict)
    ]
    if malformed_term_bindings:
        findings.append(
            _finding(
                finding_id="term_binding_entries_invalid",
                severity="review_required",
                message="term_bindings entries must be object records.",
                source_ref=source_ref,
                evidence={"invalid_indices": malformed_term_bindings},
            )
        )
    return findings


def _validate_claim_layer_context(
    artifact: dict[str, Any],
    *,
    source_ref: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    active_layers = set(_text_list(_dict(artifact.get("active_frame")).get("ontology_layer_refs")))
    for index, raw_claim in enumerate(_list(artifact.get("claims"))):
        claim = _dict(raw_claim)
        if not claim or not _is_strong_claim(claim):
            continue
        claim_layers = _text_list(claim.get("ontology_layer_refs") or claim.get("layer_refs"))
        claim_ref = _text(claim.get("id"), f"claim[{index}]")
        if not claim_layers:
            findings.append(
                _finding(
                    finding_id="strong_claim_without_layer_context",
                    severity="review_required",
                    message="Strong claims must declare ontology_layer_refs.",
                    source_ref=source_ref,
                    evidence={"claim": claim_ref},
                )
            )
            continue
        invalid_layers = [layer for layer in claim_layers if layer not in ONTOLOGY_LAYERS]
        if invalid_layers:
            findings.append(
                _finding(
                    finding_id="strong_claim_invalid_ontology_layers",
                    severity="review_required",
                    message="Strong claim ontology_layer_refs must use known ontology layers.",
                    source_ref=source_ref,
                    evidence={
                        "claim": claim_ref,
                        "invalid_layers": invalid_layers,
                        "known_layers": sorted(ONTOLOGY_LAYERS),
                    },
                )
            )
            continue
        outside_frame = sorted(set(claim_layers) - active_layers)
        if active_layers and outside_frame:
            findings.append(
                _finding(
                    finding_id="strong_claim_layer_outside_active_frame",
                    severity="review_required",
                    message="Strong claim ontology_layer_refs must stay within active_frame.",
                    source_ref=source_ref,
                    evidence={
                        "claim": claim_ref,
                        "outside_frame": outside_frame,
                        "active_frame_layers": sorted(active_layers),
                    },
                )
            )
    return findings


def build_specauthor_generated_artifact_contract_report(
    artifact: dict[str, Any],
    *,
    artifact_path: Path | None = None,
) -> dict[str, Any]:
    source_ref = _source_ref(artifact, artifact_path)
    findings: list[dict[str, Any]] = []
    findings.extend(_validate_root(artifact, source_ref=source_ref))
    findings.extend(_validate_producer(artifact, source_ref=source_ref))
    findings.extend(_validate_active_frame(artifact, source_ref=source_ref))
    findings.extend(_validate_target_artifact(artifact, source_ref=source_ref))
    findings.extend(_validate_draft(artifact, source_ref=source_ref))
    findings.extend(_validate_materialization_intent(artifact, source_ref=source_ref))
    findings.extend(_validate_record_lists(artifact, source_ref=source_ref))
    findings.extend(_validate_claim_layer_context(artifact, source_ref=source_ref))

    would_reject = bool(findings)
    return {
        "artifact_kind": "specauthor_generated_artifact_contract_report",
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
            "downstream_write_gate": WRITE_GATE_TARGET,
        },
        "validation_modes": {
            "generated_artifact_contract": "hard_contract",
            "downstream_write_gate": "required_before_graph_write",
        },
        "ok": not would_reject,
        "review_state": "review_required" if would_reject else "clear",
        "write_gate_ready": not would_reject,
        "would_reject_in_contract": would_reject,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "authority_boundary": {
            "may_execute_prompt_agent": False,
            "may_write_ontology_package": False,
            "may_write_ontology_lockfile": False,
            "may_mutate_canonical_specs": False,
            "may_mark_candidate_accepted": False,
        },
        "findings": findings,
        "warnings": [],
        "summary": {
            "finding_count": len(findings),
            "warning_count": 0,
            "claim_count": len(_list(artifact.get("claims"))),
            "term_binding_count": len(_list(artifact.get("term_bindings"))),
            "ontology_gap_count": len(_list(artifact.get("ontology_gaps"))),
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
    report = build_specauthor_generated_artifact_contract_report(
        artifact,
        artifact_path=args.artifact,
    )
    write_report(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and report["would_reject_in_contract"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
