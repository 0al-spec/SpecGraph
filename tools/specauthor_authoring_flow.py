"""Build a review-only SpecAuthorAgent authoring-flow invocation artifact."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
PROPOSAL_ID = "0146"
CONTRACT_REF = "specgraph.specauthor.prompt-side-authoring-flow.v0.1"
INVOCATION_CONTRACT_REF = "specgraph.specauthor.invocation-artifact.v0.1"
PROMPT_CONTRACT_REF = "docs/proposals/0126_specauthor_claim_calibration_prompt_contract.md"
GENERATED_ARTIFACT_CONTRACT_REF = "specgraph.specauthor.generated-artifact.v0.1"
POLICY_PATH = ROOT / "tools" / "specauthor_prompt_side_authoring_policy.json"
DEFAULT_CONTEXT_PATH = (
    ROOT / "tests" / "fixtures" / "specauthor_authoring_flow" / "active_context_ready.json"
)
DEFAULT_GENERATED_ARTIFACT_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "specauthor_generated_artifact_contract"
    / "generated_spec_ready.json"
)
DEFAULT_TERM_POLICY_PATH = ROOT / "tools" / "ontology_term_binding_policy.json"
DEFAULT_INVOCATION_OUTPUT_PATH = ROOT / "runs" / "specauthor_invocation_artifact.json"
DEFAULT_CONTRACT_OUTPUT_PATH = ROOT / "runs" / "specauthor_invocation_artifact_contract_report.json"
DEFAULT_FLOW_REPORT_OUTPUT_PATH = ROOT / "runs" / "specauthor_authoring_flow_report.json"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _text_list(value: Any) -> list[str]:
    return (
        [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if isinstance(value, list)
        else []
    )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _relative_ref(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _summarize_generated_artifact(
    artifact: dict[str, Any],
    artifact_path: Path,
) -> dict[str, Any]:
    return {
        "artifact_kind": artifact.get("artifact_kind"),
        "schema_version": artifact.get("schema_version"),
        "contract_ref": artifact.get("contract_ref"),
        "source_ref": _text(artifact.get("source_ref"), _relative_ref(artifact_path)),
    }


def _default_operator_decision() -> dict[str, Any]:
    return {
        "decision_state": "pending_review",
        "reviewer": None,
        "rationale": None,
        "may_execute_prompt_agent": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mutate_canonical_specs": False,
        "may_import_owner_decision": False,
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mutate_canonical_specs": False,
        "may_mark_candidate_accepted": False,
        "may_import_owner_decision": False,
    }


def _sanitized_operator_decision(value: Any) -> dict[str, Any]:
    decision = _dict(value) or _default_operator_decision()
    sanitized = {
        **decision,
        "may_execute_prompt_agent": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mutate_canonical_specs": False,
        "may_mark_candidate_accepted": False,
        "may_import_owner_decision": False,
    }
    if not _text(sanitized.get("decision_state")):
        sanitized["decision_state"] = "pending_review"
    return sanitized


def _finding(
    *,
    finding_id: str,
    severity: str,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "finding_id": finding_id,
        "severity": severity,
        "message": message,
        "source": "specauthor_authoring_flow",
    }
    if evidence:
        finding["evidence"] = evidence
    return finding


def _frame_mismatch_findings(
    *,
    context_frame: dict[str, Any],
    generated_frame: dict[str, Any],
) -> list[dict[str, Any]]:
    if not context_frame or not generated_frame:
        return []
    scalar_fields = (
        "project",
        "subsystem",
        "agent_layer",
        "target_artifact",
        "lifecycle_phase",
    )
    list_fields = (
        "ontology_refs",
        "ontology_layer_refs",
        "domain_refs",
        "context_refs",
    )
    mismatches: list[dict[str, Any]] = []
    for field in scalar_fields:
        context_value = _text(context_frame.get(field))
        generated_value = _text(generated_frame.get(field))
        if context_value and generated_value and context_value != generated_value:
            mismatches.append(
                {
                    "field": field,
                    "context_value": context_value,
                    "generated_artifact_value": generated_value,
                }
            )
    for field in list_fields:
        context_values = sorted(_text_list(context_frame.get(field)))
        generated_values = sorted(_text_list(generated_frame.get(field)))
        if context_values and generated_values and context_values != generated_values:
            mismatches.append(
                {
                    "field": field,
                    "context_value": context_values,
                    "generated_artifact_value": generated_values,
                }
            )
    if not mismatches:
        return []
    return [
        _finding(
            finding_id="active_frame_mismatch",
            severity="review_required",
            message=(
                "SpecAuthor authoring flow context active_frame must match the generated "
                "artifact active_frame before invocation review can become ready."
            ),
            evidence={"mismatches": mismatches},
        )
    ]


def _validator_warnings(*reports: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for report in reports:
        for warning in report.get("warnings", []):
            if isinstance(warning, dict):
                warnings.append(warning)
    return warnings


def build_specauthor_invocation_artifact(
    *,
    context: dict[str, Any],
    generated_artifact: dict[str, Any],
    generated_artifact_path: Path,
    generated_artifact_contract_report: dict[str, Any],
    write_gate_report: dict[str, Any],
) -> dict[str, Any]:
    active_frame = _dict(context.get("active_frame")) or _dict(
        generated_artifact.get("active_frame")
    )
    invocation = _dict(context.get("invocation"))
    user_intent = _dict(context.get("user_intent"))
    invocation_id = _text(
        invocation.get("invocation_id"),
        _text(context.get("invocation_id"), "specauthor-invocation-0146-local"),
    )
    model_applicability = _dict(context.get("model_applicability"))
    operator_decision = _sanitized_operator_decision(context.get("operator_decision"))
    return {
        "artifact_kind": "specauthor_invocation_artifact",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": INVOCATION_CONTRACT_REF,
        "source_ref": _text(
            context.get("source_ref"),
            f"runs/specauthor_invocation_artifact.json#{invocation_id}",
        ),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "invocation": {
            "invocation_id": invocation_id,
            "agent_id": "SpecAuthorAgent",
            "mode": _text(
                invocation.get("mode"),
                _text(context.get("mode"), "draft_authoring"),
            ),
            "prompt_contract_ref": _text(
                invocation.get("prompt_contract_ref"),
                PROMPT_CONTRACT_REF,
            ),
            "user_intent": {
                "text": _text(user_intent.get("text"), _text(context.get("intent_text"))),
                "source_ref": _text(
                    user_intent.get("source_ref"),
                    _text(context.get("intent_source_ref"), "operator://local-intent"),
                ),
            },
        },
        "active_frame": active_frame,
        "model_applicability": model_applicability,
        "validation_chain": {
            "generated_artifact": _summarize_generated_artifact(
                generated_artifact,
                generated_artifact_path,
            ),
            "generated_artifact_contract_report": generated_artifact_contract_report,
            "write_gate_report": write_gate_report,
        },
        "operator_decision": operator_decision,
        "authority_boundary": _authority_boundary(),
    }


def build_specauthor_authoring_flow_report(
    *,
    context: dict[str, Any],
    generated_artifact: dict[str, Any],
    generated_artifact_path: Path,
    term_policy: dict[str, Any],
    invocation_output_path: Path,
    contract_output_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    generated_contract = _load_module(
        ROOT / "tools" / "specauthor_generated_artifact_contract.py",
        "specauthor_generated_artifact_contract_for_authoring_flow",
    )
    write_gate = _load_module(
        ROOT / "tools" / "specauthor_ontology_write_gate.py",
        "specauthor_ontology_write_gate_for_authoring_flow",
    )
    invocation_contract = _load_module(
        ROOT / "tools" / "specauthor_invocation_artifact_contract.py",
        "specauthor_invocation_artifact_contract_for_authoring_flow",
    )

    generated_report = generated_contract.build_specauthor_generated_artifact_contract_report(
        generated_artifact,
        artifact_path=generated_artifact_path,
    )
    write_gate_report = write_gate.build_specauthor_ontology_write_gate_report(
        generated_artifact,
        term_policy=term_policy,
        artifact_path=generated_artifact_path,
    )
    invocation_artifact = build_specauthor_invocation_artifact(
        context=context,
        generated_artifact=generated_artifact,
        generated_artifact_path=generated_artifact_path,
        generated_artifact_contract_report=generated_report,
        write_gate_report=write_gate_report,
    )
    invocation_contract_report = (
        invocation_contract.build_specauthor_invocation_artifact_contract_report(
            invocation_artifact,
            artifact_path=invocation_output_path,
        )
    )
    context_frame = _dict(context.get("active_frame"))
    generated_frame = _dict(generated_artifact.get("active_frame"))
    flow_findings = _frame_mismatch_findings(
        context_frame=context_frame,
        generated_frame=generated_frame,
    )
    invocation_findings = [
        finding
        for finding in invocation_contract_report.get("findings", [])
        if isinstance(finding, dict)
    ]
    warnings = _validator_warnings(
        generated_report,
        write_gate_report,
        invocation_contract_report,
    )
    findings = invocation_findings + flow_findings
    flow_ok = invocation_contract_report.get("ok") is True and not flow_findings
    flow_report = {
        "artifact_kind": "specauthor_authoring_flow_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "contract_ref": CONTRACT_REF,
        "policy_ref": _relative_ref(POLICY_PATH),
        "prompt_contract_ref": PROMPT_CONTRACT_REF,
        "outputs": {
            "invocation_artifact": _relative_ref(invocation_output_path),
            "invocation_artifact_contract_report": _relative_ref(contract_output_path),
        },
        "ok": flow_ok,
        "review_state": "ready_for_operator_review" if flow_ok else "review_required",
        "validation_chain_summary": {
            "generated_artifact_contract_ok": generated_report.get("ok") is True,
            "write_gate_ok": write_gate_report.get("ok") is True,
            "invocation_contract_ok": invocation_contract_report.get("ok") is True,
            "write_decision": write_gate_report.get("write_decision"),
            "invocation_review_state": invocation_contract_report.get("review_state"),
        },
        "active_frame_summary": {
            "ontology_ref_count": len(
                _text_list(_dict(invocation_artifact.get("active_frame")).get("ontology_refs"))
            ),
            "ontology_layer_refs": _text_list(
                _dict(invocation_artifact.get("active_frame")).get("ontology_layer_refs")
            ),
            "model_applicability_refs": _text_list(
                _dict(invocation_artifact.get("active_frame")).get("model_applicability_refs")
            ),
            "domain_refs": _text_list(
                _dict(invocation_artifact.get("active_frame")).get("domain_refs")
            ),
            "context_refs": _text_list(
                _dict(invocation_artifact.get("active_frame")).get("context_refs")
            ),
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_prompt_published": False,
            "raw_model_output_published": False,
        },
        "findings": findings,
        "warnings": warnings,
        "summary": {
            "finding_count": len(findings),
            "warning_count": len(warnings),
        },
    }
    return invocation_artifact, invocation_contract_report, flow_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", default=DEFAULT_CONTEXT_PATH, type=Path)
    parser.add_argument(
        "--generated-artifact",
        default=DEFAULT_GENERATED_ARTIFACT_PATH,
        type=Path,
    )
    parser.add_argument("--term-policy", default=DEFAULT_TERM_POLICY_PATH, type=Path)
    parser.add_argument("--invocation-output", default=DEFAULT_INVOCATION_OUTPUT_PATH, type=Path)
    parser.add_argument("--contract-output", default=DEFAULT_CONTRACT_OUTPUT_PATH, type=Path)
    parser.add_argument(
        "--flow-report-output",
        default=DEFAULT_FLOW_REPORT_OUTPUT_PATH,
        type=Path,
    )
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    context = load_json(args.context)
    generated_artifact = load_json(args.generated_artifact)
    term_policy = load_json(args.term_policy)
    invocation_artifact, contract_report, flow_report = build_specauthor_authoring_flow_report(
        context=context,
        generated_artifact=generated_artifact,
        generated_artifact_path=args.generated_artifact,
        term_policy=term_policy,
        invocation_output_path=args.invocation_output,
        contract_output_path=args.contract_output,
    )
    write_json(invocation_artifact, args.invocation_output)
    write_json(contract_report, args.contract_output)
    write_json(flow_report, args.flow_report_output)
    print(json.dumps(flow_report, indent=2, sort_keys=True))
    if args.strict and not flow_report["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
