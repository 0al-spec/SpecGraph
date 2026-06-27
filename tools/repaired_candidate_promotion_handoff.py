"""Build repaired idea-to-spec promotion handoff artifacts from rerun materialization."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import active_idea_to_spec_candidate_source  # noqa: E402
import candidate_repair_loop  # noqa: E402
import candidate_spec_materialization  # noqa: E402
import idea_to_spec_promotion_gate  # noqa: E402
import idea_to_spec_repair_session_journal  # noqa: E402
import pre_sib_coherence_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0177"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.repaired-candidate-promotion-handoff.v0.1"
RERUN_MATERIALIZATION_CONTRACT_REF = "specgraph.idea-to-spec.rerun-materialization.v0.1"
CANDIDATE_GRAPH_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph.v0.1"
RAW_TRACE_FIELDS = {
    "operator_note",
    "operator_notes",
    "private_notes",
    "raw_intent_text",
    "raw_idea_text",
    "raw_model_output",
    "raw_operator_note",
    "raw_prompt",
}

DEFAULT_INTAKE_PATH = ROOT / "runs" / "idea_event_storming_intake.json"
DEFAULT_CLARIFICATION_REQUESTS_PATH = ROOT / "runs" / "idea_to_spec_clarification_requests.json"
DEFAULT_CLARIFICATION_ANSWERS_PATH = ROOT / "runs" / "idea_to_spec_clarification_answers.json"
DEFAULT_ONTOLOGY_DECISIONS_PATH = ROOT / "runs" / "product_ontology_gap_review_decisions.json"
DEFAULT_RERUN_INPUT_PATH = ROOT / "runs" / "idea_to_spec_answer_rerun_input.json"
DEFAULT_RERUN_PREVIEW_PATH = ROOT / "runs" / "idea_to_spec_rerun_preview.json"
DEFAULT_RERUN_MATERIALIZATION_PATH = ROOT / "runs" / "idea_to_spec_rerun_materialization.json"

DEFAULT_REPAIRED_CANDIDATE_GRAPH_OUTPUT = ROOT / "runs" / "repaired_candidate_spec_graph.json"
DEFAULT_REPAIRED_PRE_SIB_OUTPUT = ROOT / "runs" / "repaired_pre_sib_coherence_report.json"
DEFAULT_REPAIRED_REPAIR_LOOP_OUTPUT = ROOT / "runs" / "repaired_candidate_repair_loop_report.json"
DEFAULT_REPAIRED_MATERIALIZATION_OUTPUT_DIR = (
    ROOT / "runs" / "repaired_materialized_candidate_specs"
)
DEFAULT_REPAIRED_MATERIALIZATION_OUTPUT = (
    ROOT / "runs" / "repaired_candidate_spec_materialization_report.json"
)
DEFAULT_REPAIRED_PROMOTION_GATE_OUTPUT = ROOT / "runs" / "repaired_idea_to_spec_promotion_gate.json"
DEFAULT_REPAIRED_ACTIVE_CANDIDATE_OUTPUT = (
    ROOT / "runs" / "repaired_active_idea_to_spec_candidate.json"
)
DEFAULT_REPAIRED_REPAIR_SESSION_OUTPUT = ROOT / "runs" / "repaired_idea_to_spec_repair_session.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "repaired_candidate_promotion_handoff_report.json"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


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


def _relative_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(_repo_path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    output_path = _repo_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        "source": "repaired_candidate_promotion_handoff",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_accept_ontology_terms": False,
        "may_mark_candidate_graph_accepted": False,
        "may_materialize_candidate_approval_decision": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
    }


def _artifact_ref(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_kind": payload.get("artifact_kind"),
        "contract_ref": payload.get("contract_ref"),
        "proposal_id": payload.get("proposal_id"),
        "source_ref": _relative_ref(_repo_path(path)),
        "readiness": _public_safe(_dict(payload.get("readiness"))),
        "summary": _public_safe(_dict(payload.get("summary"))),
    }


def _validate_rerun_materialization(
    rerun_materialization: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if rerun_materialization.get("artifact_kind") != "idea_to_spec_rerun_materialization":
        findings.append(
            _finding(
                finding_id="rerun_materialization_wrong_artifact_kind",
                severity="review_required",
                message="Repaired handoff requires idea_to_spec_rerun_materialization input.",
                evidence={"artifact_kind": rerun_materialization.get("artifact_kind")},
            )
        )
    if rerun_materialization.get("contract_ref") != RERUN_MATERIALIZATION_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="rerun_materialization_contract_ref_unsupported",
                severity="review_required",
                message=(
                    "idea_to_spec_rerun_materialization contract_ref must be "
                    f"{RERUN_MATERIALIZATION_CONTRACT_REF}."
                ),
                evidence={"contract_ref": rerun_materialization.get("contract_ref")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if rerun_materialization.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="rerun_materialization_authority_expanded",
                    severity="review_required",
                    message=f"Rerun materialization {field} must be false.",
                    evidence={field: rerun_materialization.get(field)},
                )
            )
    if _dict(rerun_materialization.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="rerun_materialization_not_ready",
                severity="review_required",
                message="Rerun materialization must be ready before repaired handoff.",
                evidence={"readiness": _dict(rerun_materialization.get("readiness"))},
            )
        )
    return findings


def _candidate_graph_preview(
    rerun_materialization: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    preview = _dict(
        _dict(rerun_materialization.get("materialization_preview")).get("candidate_graph_preview")
    )
    if not preview:
        findings.append(
            _finding(
                finding_id="candidate_graph_preview_missing",
                severity="review_required",
                message="Rerun materialization must contain a candidate_graph_preview.",
            )
        )
        return {}, findings
    if preview.get("artifact_kind") != "candidate_spec_graph":
        findings.append(
            _finding(
                finding_id="candidate_graph_preview_wrong_artifact_kind",
                severity="review_required",
                message="Nested repaired preview must be a candidate_spec_graph.",
                evidence={"artifact_kind": preview.get("artifact_kind")},
            )
        )
    if preview.get("contract_ref") != CANDIDATE_GRAPH_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="candidate_graph_preview_contract_ref_unsupported",
                severity="review_required",
                message=(
                    f"Nested candidate graph contract_ref must be {CANDIDATE_GRAPH_CONTRACT_REF}."
                ),
                evidence={"contract_ref": preview.get("contract_ref")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if preview.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="candidate_graph_preview_authority_expanded",
                    severity="review_required",
                    message=f"Nested candidate graph {field} must be false.",
                    evidence={field: preview.get(field)},
                )
            )
    if not _list(preview.get("nodes")):
        findings.append(
            _finding(
                finding_id="candidate_graph_preview_nodes_missing",
                severity="review_required",
                message="Nested repaired candidate graph must contain candidate nodes.",
            )
        )
    return preview, findings


def _product_source_ref(candidate_graph: dict[str, Any]) -> str:
    candidates = [
        _text(_dict(candidate_graph.get("source_intake")).get("source_ref")),
        _text(candidate_graph.get("source_ref")),
    ]
    for source_ref in candidates:
        if source_ref.startswith("product://"):
            return source_ref
    return ""


def _repaired_candidate_graph(
    *,
    rerun_materialization: dict[str, Any],
    rerun_materialization_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    preview, findings = _candidate_graph_preview(rerun_materialization)
    if findings:
        return preview, findings

    repaired_graph = copy.deepcopy(preview)
    preview_source_ref = _text(preview.get("source_ref"))
    product_source_ref = _product_source_ref(preview)
    if product_source_ref:
        repaired_graph["source_ref"] = product_source_ref
    else:
        findings.append(
            _finding(
                finding_id="candidate_graph_product_source_ref_missing",
                severity="review_required",
                message=(
                    "Repaired candidate graph must preserve a product:// source_ref so "
                    "active candidate identity checks remain candidate-scoped."
                ),
                evidence={"preview_source_ref": preview_source_ref},
            )
        )
    repaired_graph["repaired_candidate_promotion_handoff"] = {
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "state": "review_only",
        "source_rerun_materialization_ref": _relative_ref(_repo_path(rerun_materialization_path)),
        "source_candidate_graph_preview_ref": preview_source_ref,
    }
    return repaired_graph, findings


def _active_candidate_config(
    *,
    intake_path: Path,
    repaired_candidate_graph_output: Path,
    repaired_pre_sib_output: Path,
    repaired_repair_loop_output: Path,
    repaired_materialization_output: Path,
    repaired_promotion_gate_output: Path,
) -> dict[str, Any]:
    return {
        "artifact_kind": "active_idea_to_spec_candidate_source_config",
        "schema_version": 1,
        "contract_ref": active_idea_to_spec_candidate_source.CONFIG_CONTRACT_REF,
        "artifacts": {
            "intake": _relative_ref(_repo_path(intake_path)),
            "candidate_graph": _relative_ref(_repo_path(repaired_candidate_graph_output)),
            "pre_sib": _relative_ref(_repo_path(repaired_pre_sib_output)),
            "repair_loop": _relative_ref(_repo_path(repaired_repair_loop_output)),
            "materialization": _relative_ref(_repo_path(repaired_materialization_output)),
            "promotion_gate": _relative_ref(_repo_path(repaired_promotion_gate_output)),
        },
        "_artifact_paths_source": "repaired_candidate_promotion_handoff",
        "_config_source_mode": "repaired_candidate_promotion_handoff",
    }


def _repair_loop_for_repaired_handoff(
    repair_loop: dict[str, Any],
    *,
    pre_sib_report: dict[str, Any],
) -> dict[str, Any]:
    if _dict(pre_sib_report.get("readiness")).get("ready") is not True:
        return repair_loop
    if _dict(repair_loop.get("readiness")).get("ready") is True:
        return repair_loop
    if _list(repair_loop.get("findings")):
        return repair_loop
    summary = _dict(repair_loop.get("summary"))
    if summary.get("applied_action_count", 0) != 0:
        return repair_loop
    if summary.get("context_required_count", 0) != 0:
        return repair_loop

    normalized = copy.deepcopy(repair_loop)
    readiness = dict(_dict(normalized.get("readiness")))
    readiness.update(
        {
            "ready": True,
            "review_state": "repair_preview_ready",
            "blocked_by": [],
        }
    )
    normalized["readiness"] = readiness
    normalized_summary = dict(summary)
    normalized_summary.update(
        {
            "status": "repair_preview_ready",
            "no_op_repair_loop": True,
        }
    )
    normalized["summary"] = normalized_summary
    normalized["repaired_candidate_promotion_handoff"] = {
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "state": "clean_pre_sib_pass_through",
        "reason": "repaired pre-SIB report is already ready and no repair action is required",
    }
    return normalized


def _readiness_findings(
    *,
    repaired_active_candidate: dict[str, Any],
    repaired_promotion_gate: dict[str, Any],
    repaired_repair_session: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if _dict(repaired_active_candidate.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="repaired_active_candidate_not_ready",
                severity="review_required",
                message="Repaired active candidate source must be ready for approval review.",
                evidence={"readiness": _dict(repaired_active_candidate.get("readiness"))},
            )
        )
    if _dict(repaired_promotion_gate.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="repaired_promotion_gate_not_ready",
                severity="review_required",
                message="Repaired promotion gate must be ready for promotion request handoff.",
                evidence={"readiness": _dict(repaired_promotion_gate.get("readiness"))},
            )
        )
    session_readiness = _dict(repaired_repair_session.get("readiness"))
    if session_readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="repaired_session_journal_not_ready",
                severity="review_required",
                message="Repaired repair-session journal must be ready before handoff.",
                evidence={"readiness": session_readiness},
            )
        )
    readiness_impact = _dict(repaired_repair_session.get("readiness_impact"))
    if readiness_impact.get("ready_for_candidate_approval") is not True:
        findings.append(
            _finding(
                finding_id="repaired_session_not_ready_for_candidate_approval",
                severity="review_required",
                message="Repaired repair session must be ready for candidate approval.",
                evidence={
                    "readiness_impact": readiness_impact,
                    "summary": _dict(repaired_repair_session.get("summary")),
                },
            )
        )
    if readiness_impact.get("ready_for_platform_promotion") is not False:
        findings.append(
            _finding(
                finding_id="repaired_session_platform_promotion_boundary_expanded",
                severity="review_required",
                message=(
                    "Repaired handoff must not become platform-promotion ready before an "
                    "explicit candidate approval decision."
                ),
                evidence={
                    "ready_for_platform_promotion": readiness_impact.get(
                        "ready_for_platform_promotion"
                    )
                },
            )
        )
    return findings


def build_repaired_candidate_promotion_handoff(
    *,
    intake: dict[str, Any],
    clarification_requests: dict[str, Any],
    clarification_answers: dict[str, Any],
    ontology_decisions: dict[str, Any],
    rerun_input: dict[str, Any],
    rerun_preview: dict[str, Any],
    rerun_materialization: dict[str, Any],
    intake_path: Path = DEFAULT_INTAKE_PATH,
    clarification_requests_path: Path = DEFAULT_CLARIFICATION_REQUESTS_PATH,
    clarification_answers_path: Path = DEFAULT_CLARIFICATION_ANSWERS_PATH,
    ontology_decisions_path: Path = DEFAULT_ONTOLOGY_DECISIONS_PATH,
    rerun_input_path: Path = DEFAULT_RERUN_INPUT_PATH,
    rerun_preview_path: Path = DEFAULT_RERUN_PREVIEW_PATH,
    rerun_materialization_path: Path = DEFAULT_RERUN_MATERIALIZATION_PATH,
    repaired_candidate_graph_output: Path = DEFAULT_REPAIRED_CANDIDATE_GRAPH_OUTPUT,
    repaired_pre_sib_output: Path = DEFAULT_REPAIRED_PRE_SIB_OUTPUT,
    repaired_repair_loop_output: Path = DEFAULT_REPAIRED_REPAIR_LOOP_OUTPUT,
    repaired_materialization_output_dir: Path = DEFAULT_REPAIRED_MATERIALIZATION_OUTPUT_DIR,
    repaired_materialization_output: Path = DEFAULT_REPAIRED_MATERIALIZATION_OUTPUT,
    repaired_promotion_gate_output: Path = DEFAULT_REPAIRED_PROMOTION_GATE_OUTPUT,
    repaired_active_candidate_output: Path = DEFAULT_REPAIRED_ACTIVE_CANDIDATE_OUTPUT,
    repaired_repair_session_output: Path = DEFAULT_REPAIRED_REPAIR_SESSION_OUTPUT,
    session_id: str | None = None,
    operator_ref: str = "local_operator:unattributed",
) -> dict[str, Any]:
    findings = _validate_rerun_materialization(rerun_materialization)
    repaired_graph, graph_findings = _repaired_candidate_graph(
        rerun_materialization=rerun_materialization,
        rerun_materialization_path=rerun_materialization_path,
    )
    findings.extend(graph_findings)

    generated: dict[str, dict[str, Any]] = {}
    if not findings:
        # Downstream builders consume artifact paths, so each repaired stage is
        # persisted before the next stage. The final handoff report is the
        # authoritative signal that the staged outputs form a complete chain.
        write_json(repaired_graph, repaired_candidate_graph_output)
        repaired_pre_sib = pre_sib_coherence_report.build_pre_sib_coherence_report(
            repaired_graph,
            candidate_graph_path=_repo_path(repaired_candidate_graph_output),
        )
        write_json(repaired_pre_sib, repaired_pre_sib_output)
        repaired_repair_loop = candidate_repair_loop.build_candidate_repair_loop_report(
            candidate_graph=repaired_graph,
            pre_sib_report=repaired_pre_sib,
            candidate_graph_path=_repo_path(repaired_candidate_graph_output),
            pre_sib_report_path=_repo_path(repaired_pre_sib_output),
            output_path=_repo_path(repaired_repair_loop_output),
        )
        repaired_repair_loop = _repair_loop_for_repaired_handoff(
            repaired_repair_loop,
            pre_sib_report=repaired_pre_sib,
        )
        write_json(repaired_repair_loop, repaired_repair_loop_output)
        repaired_materialization = (
            candidate_spec_materialization.build_candidate_spec_materialization_report(
                candidate_graph=repaired_graph,
                repair_loop=repaired_repair_loop,
                candidate_graph_path=_repo_path(repaired_candidate_graph_output),
                repair_loop_path=_repo_path(repaired_repair_loop_output),
                output_dir=_repo_path(repaired_materialization_output_dir),
            )
        )
        write_json(repaired_materialization, repaired_materialization_output)
        repaired_promotion_gate = idea_to_spec_promotion_gate.build_idea_to_spec_promotion_gate(
            pre_sib=repaired_pre_sib,
            repair_loop=repaired_repair_loop,
            materialization=repaired_materialization,
            pre_sib_path=_repo_path(repaired_pre_sib_output),
            repair_loop_path=_repo_path(repaired_repair_loop_output),
            materialization_path=_repo_path(repaired_materialization_output),
        )
        write_json(repaired_promotion_gate, repaired_promotion_gate_output)
        active_config = _active_candidate_config(
            intake_path=intake_path,
            repaired_candidate_graph_output=repaired_candidate_graph_output,
            repaired_pre_sib_output=repaired_pre_sib_output,
            repaired_repair_loop_output=repaired_repair_loop_output,
            repaired_materialization_output=repaired_materialization_output,
            repaired_promotion_gate_output=repaired_promotion_gate_output,
        )
        active_candidate_artifacts = {
            "intake": (_repo_path(intake_path), intake),
            "candidate_graph": (_repo_path(repaired_candidate_graph_output), repaired_graph),
            "pre_sib": (_repo_path(repaired_pre_sib_output), repaired_pre_sib),
            "repair_loop": (_repo_path(repaired_repair_loop_output), repaired_repair_loop),
            "materialization": (
                _repo_path(repaired_materialization_output),
                repaired_materialization,
            ),
            "promotion_gate": (_repo_path(repaired_promotion_gate_output), repaired_promotion_gate),
        }
        repaired_active_candidate = (
            active_idea_to_spec_candidate_source.build_active_idea_to_spec_candidate_source(
                active_config,
                loaded_artifacts=active_candidate_artifacts,
            )
        )
        write_json(repaired_active_candidate, repaired_active_candidate_output)
        repaired_repair_session = (
            idea_to_spec_repair_session_journal.build_idea_to_spec_repair_session_journal(
                active_candidate=repaired_active_candidate,
                clarification_requests=clarification_requests,
                clarification_answers=clarification_answers,
                ontology_decisions=ontology_decisions,
                rerun_input=rerun_input,
                rerun_preview=rerun_preview,
                rerun_materialization=rerun_materialization,
                promotion_gate=repaired_promotion_gate,
                active_candidate_path=_repo_path(repaired_active_candidate_output),
                clarification_requests_path=_repo_path(clarification_requests_path),
                clarification_answers_path=_repo_path(clarification_answers_path),
                ontology_decisions_path=_repo_path(ontology_decisions_path),
                rerun_input_path=_repo_path(rerun_input_path),
                rerun_preview_path=_repo_path(rerun_preview_path),
                rerun_materialization_path=_repo_path(rerun_materialization_path),
                promotion_gate_path=_repo_path(repaired_promotion_gate_output),
                session_id=session_id,
                operator_ref=operator_ref,
            )
        )
        write_json(repaired_repair_session, repaired_repair_session_output)
        generated = {
            "repaired_candidate_graph": repaired_graph,
            "repaired_pre_sib": repaired_pre_sib,
            "repaired_repair_loop": repaired_repair_loop,
            "repaired_materialization": repaired_materialization,
            "repaired_promotion_gate": repaired_promotion_gate,
            "repaired_active_candidate": repaired_active_candidate,
            "repaired_repair_session": repaired_repair_session,
        }
        findings.extend(
            _readiness_findings(
                repaired_active_candidate=repaired_active_candidate,
                repaired_promotion_gate=repaired_promotion_gate,
                repaired_repair_session=repaired_repair_session,
            )
        )

    ready = not findings
    repaired_session = generated.get("repaired_repair_session", {})
    readiness_impact = _dict(repaired_session.get("readiness_impact"))
    output_paths = {
        "repaired_candidate_graph": repaired_candidate_graph_output,
        "repaired_pre_sib": repaired_pre_sib_output,
        "repaired_repair_loop": repaired_repair_loop_output,
        "repaired_materialization": repaired_materialization_output,
        "repaired_promotion_gate": repaired_promotion_gate_output,
        "repaired_active_candidate": repaired_active_candidate_output,
        "repaired_repair_session": repaired_repair_session_output,
    }
    return {
        "artifact_kind": "repaired_candidate_promotion_handoff_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "intake": _artifact_ref(intake_path, intake),
            "clarification_requests": _artifact_ref(
                clarification_requests_path,
                clarification_requests,
            ),
            "clarification_answers": _artifact_ref(
                clarification_answers_path,
                clarification_answers,
            ),
            "ontology_decisions": _artifact_ref(ontology_decisions_path, ontology_decisions),
            "rerun_input": _artifact_ref(rerun_input_path, rerun_input),
            "rerun_preview": _artifact_ref(rerun_preview_path, rerun_preview),
            "rerun_materialization": _artifact_ref(
                rerun_materialization_path,
                rerun_materialization,
            ),
        },
        "output_artifacts": {
            key: _artifact_ref(path, generated[key])
            for key, path in output_paths.items()
            if key in generated
        },
        "readiness": {
            "ready": ready,
            "review_state": "repaired_candidate_promotion_handoff_ready"
            if ready
            else "repaired_candidate_promotion_handoff_review_required",
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "candidate_approval_decision"
            if ready
            else "repair remaining candidate handoff blockers",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "redaction_enforced_by": "recursive_public_safe_field_filter",
            "raw_idea_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
            "raw_operator_note_published": False,
        },
        "findings": findings,
        "summary": {
            "status": "repaired_candidate_promotion_handoff_ready"
            if ready
            else "repaired_candidate_promotion_handoff_review_required",
            "finding_count": len(findings),
            "generated_artifact_count": len(generated),
            "removed_gap_count": _dict(rerun_materialization.get("summary")).get(
                "removed_gap_count",
                0,
            ),
            "resolved_ontology_gap_count": _dict(rerun_materialization.get("summary")).get(
                "resolved_ontology_gap_count",
                0,
            ),
            "unresolved_ontology_gap_count": _dict(rerun_materialization.get("summary")).get(
                "unresolved_ontology_gap_count",
                0,
            ),
            "resolved_candidate_gap_count": _dict(rerun_materialization.get("summary")).get(
                "resolved_candidate_gap_count",
                0,
            ),
            "unresolved_candidate_gap_count": _dict(rerun_materialization.get("summary")).get(
                "unresolved_candidate_gap_count",
                0,
            ),
            "ready_for_candidate_approval": readiness_impact.get(
                "ready_for_candidate_approval",
                False,
            ),
            "ready_for_platform_promotion": readiness_impact.get(
                "ready_for_platform_promotion",
                False,
            ),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", default=DEFAULT_INTAKE_PATH, type=Path)
    parser.add_argument(
        "--clarification-requests",
        default=DEFAULT_CLARIFICATION_REQUESTS_PATH,
        type=Path,
    )
    parser.add_argument(
        "--clarification-answers",
        default=DEFAULT_CLARIFICATION_ANSWERS_PATH,
        type=Path,
    )
    parser.add_argument("--ontology-decisions", default=DEFAULT_ONTOLOGY_DECISIONS_PATH, type=Path)
    parser.add_argument("--rerun-input", default=DEFAULT_RERUN_INPUT_PATH, type=Path)
    parser.add_argument("--rerun-preview", default=DEFAULT_RERUN_PREVIEW_PATH, type=Path)
    parser.add_argument(
        "--rerun-materialization",
        default=DEFAULT_RERUN_MATERIALIZATION_PATH,
        type=Path,
    )
    parser.add_argument(
        "--repaired-candidate-graph-output",
        default=DEFAULT_REPAIRED_CANDIDATE_GRAPH_OUTPUT,
        type=Path,
    )
    parser.add_argument(
        "--repaired-pre-sib-output",
        default=DEFAULT_REPAIRED_PRE_SIB_OUTPUT,
        type=Path,
    )
    parser.add_argument(
        "--repaired-repair-loop-output",
        default=DEFAULT_REPAIRED_REPAIR_LOOP_OUTPUT,
        type=Path,
    )
    parser.add_argument(
        "--repaired-materialization-output-dir",
        default=DEFAULT_REPAIRED_MATERIALIZATION_OUTPUT_DIR,
        type=Path,
    )
    parser.add_argument(
        "--repaired-materialization-output",
        default=DEFAULT_REPAIRED_MATERIALIZATION_OUTPUT,
        type=Path,
    )
    parser.add_argument(
        "--repaired-promotion-gate-output",
        default=DEFAULT_REPAIRED_PROMOTION_GATE_OUTPUT,
        type=Path,
    )
    parser.add_argument(
        "--repaired-active-candidate-output",
        default=DEFAULT_REPAIRED_ACTIVE_CANDIDATE_OUTPUT,
        type=Path,
    )
    parser.add_argument(
        "--repaired-repair-session-output",
        default=DEFAULT_REPAIRED_REPAIR_SESSION_OUTPUT,
        type=Path,
    )
    parser.add_argument("--session-id")
    parser.add_argument("--operator-ref", default="local_operator:unattributed")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_repaired_candidate_promotion_handoff(
        intake=load_json(args.intake),
        clarification_requests=load_json(args.clarification_requests),
        clarification_answers=load_json(args.clarification_answers),
        ontology_decisions=load_json(args.ontology_decisions),
        rerun_input=load_json(args.rerun_input),
        rerun_preview=load_json(args.rerun_preview),
        rerun_materialization=load_json(args.rerun_materialization),
        intake_path=args.intake,
        clarification_requests_path=args.clarification_requests,
        clarification_answers_path=args.clarification_answers,
        ontology_decisions_path=args.ontology_decisions,
        rerun_input_path=args.rerun_input,
        rerun_preview_path=args.rerun_preview,
        rerun_materialization_path=args.rerun_materialization,
        repaired_candidate_graph_output=args.repaired_candidate_graph_output,
        repaired_pre_sib_output=args.repaired_pre_sib_output,
        repaired_repair_loop_output=args.repaired_repair_loop_output,
        repaired_materialization_output_dir=args.repaired_materialization_output_dir,
        repaired_materialization_output=args.repaired_materialization_output,
        repaired_promotion_gate_output=args.repaired_promotion_gate_output,
        repaired_active_candidate_output=args.repaired_active_candidate_output,
        repaired_repair_session_output=args.repaired_repair_session_output,
        session_id=args.session_id,
        operator_ref=args.operator_ref,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('resolved_ontology_gap_count', 0)} ontology gaps, "
        f"{summary.get('resolved_candidate_gap_count', 0)} candidate gaps, "
        f"approval_ready={summary.get('ready_for_candidate_approval', False)} -> "
        f"{_relative_ref(_repo_path(args.output))}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
