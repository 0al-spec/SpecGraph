"""Materialize review-only rerun artifacts from a SpecSpace repair draft preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import (  # noqa: E402
    idea_to_spec_answer_rerun_input,
    idea_to_spec_clarification_answers,
    idea_to_spec_repair_session_journal,
    idea_to_spec_rerun_materialization,
    idea_to_spec_rerun_preview,
    product_ontology_gap_review_decisions,
)

PROPOSAL_ID = "0173"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.specspace-repair-draft-rerun.v0.1"
IMPORT_PREVIEW_KIND = "specspace_repair_draft_import_preview"
IMPORT_PREVIEW_CONTRACT_REF = "specgraph.idea-to-spec.specspace-repair-draft-import-preview.v0.1"
ANSWER_SET_CONTRACT_REF = "specgraph.idea-to-spec.clarification-answer-set.v0.1"

DEFAULT_IMPORT_PREVIEW_PATH = ROOT / "runs" / "specspace_repair_draft_import_preview.json"
DEFAULT_REPAIR_SESSION_PATH = ROOT / "runs" / "idea_to_spec_repair_session.json"
DEFAULT_CLARIFICATION_REQUESTS_PATH = ROOT / "runs" / "idea_to_spec_clarification_requests.json"
DEFAULT_ACTIVE_CANDIDATE_PATH = ROOT / "runs" / "active_idea_to_spec_candidate.json"
DEFAULT_INTAKE_PATH = ROOT / "runs" / "idea_event_storming_intake.json"
DEFAULT_CANDIDATE_GRAPH_PATH = ROOT / "runs" / "candidate_spec_graph.json"
DEFAULT_PROMOTION_GATE_PATH = ROOT / "runs" / "idea_to_spec_promotion_gate.json"
DEFAULT_CLARIFICATION_ANSWERS_OUTPUT = ROOT / "runs" / "idea_to_spec_clarification_answers.json"
DEFAULT_ONTOLOGY_DECISIONS_OUTPUT = ROOT / "runs" / "product_ontology_gap_review_decisions.json"
DEFAULT_RERUN_INPUT_OUTPUT = ROOT / "runs" / "idea_to_spec_answer_rerun_input.json"
DEFAULT_RERUN_PREVIEW_OUTPUT = ROOT / "runs" / "idea_to_spec_rerun_preview.json"
DEFAULT_RERUN_MATERIALIZATION_OUTPUT = ROOT / "runs" / "idea_to_spec_rerun_materialization.json"
DEFAULT_REPAIR_SESSION_OUTPUT = ROOT / "runs" / "idea_to_spec_repair_session.json"
DEFAULT_REPORT_OUTPUT = ROOT / "runs" / "specspace_repair_draft_rerun_report.json"

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
AUTHORITY_FALSE_FIELDS = (
    "may_execute_prompt_agent",
    "may_apply_to_specgraph",
    "may_apply_answers",
    "may_apply_decisions",
    "may_apply_answers_to_source_artifacts",
    "may_apply_decisions_to_source_artifacts",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_write_ontology_lockfile",
    "may_accept_ontology_terms",
    "may_mark_candidate_graph_accepted",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_publish_read_model",
)
ANSWER_CANDIDATE_STATUSES = {
    "accepted_for_candidate",
    "accepted_for_review",
    "deferred",
}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _relative_ref(path: Path | None) -> str:
    if path is None:
        return "inline:unknown"
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        "source": "specspace_repair_drafts_to_rerun_artifacts",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_apply_drafts_to_source_artifacts": False,
        "may_apply_answers_to_source_artifacts": False,
        "may_apply_decisions_to_source_artifacts": False,
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


def _first_authority_expansion(boundary: Any) -> str | None:
    if not isinstance(boundary, dict):
        return "authority_boundary_missing"
    for field in AUTHORITY_FALSE_FIELDS:
        if boundary.get(field) is True:
            return field
    return None


def _validate_import_preview(import_preview: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if import_preview.get("artifact_kind") != IMPORT_PREVIEW_KIND:
        findings.append(
            _finding(
                finding_id="import_preview_wrong_artifact_kind",
                severity="review_required",
                message=f"Import preview must use artifact_kind {IMPORT_PREVIEW_KIND}.",
                evidence={"artifact_kind": import_preview.get("artifact_kind")},
            )
        )
    if import_preview.get("contract_ref") != IMPORT_PREVIEW_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="import_preview_contract_ref_unsupported",
                severity="review_required",
                message=f"Import preview contract_ref must be {IMPORT_PREVIEW_CONTRACT_REF}.",
                evidence={"contract_ref": import_preview.get("contract_ref")},
            )
        )
    if import_preview.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="import_preview_schema_version_unsupported",
                severity="review_required",
                message="Import preview schema_version must be 1.",
                evidence={"schema_version": import_preview.get("schema_version")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if import_preview.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="import_preview_authority_expanded",
                    severity="review_required",
                    message=f"Import preview {field} must be false.",
                    evidence={field: import_preview.get(field)},
                )
            )
    boundary_expansion = _first_authority_expansion(import_preview.get("authority_boundary"))
    if boundary_expansion:
        findings.append(
            _finding(
                finding_id="import_preview_authority_boundary_expanded",
                severity="review_required",
                message="Import preview authority boundary must remain review-only.",
                evidence={boundary_expansion: True},
            )
        )
    readiness = _dict(import_preview.get("readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="import_preview_not_ready_for_rerun",
                severity="review_required",
                message="SpecSpace repair draft rerun requires a ready import preview.",
                evidence={"readiness": readiness},
            )
        )
    return findings


def _validate_import_preview_refs(
    import_preview: dict[str, Any],
    *,
    repair_session: dict[str, Any],
    repair_session_path: Path,
    clarification_requests_path: Path,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    sources = _dict(import_preview.get("source_artifacts"))
    expected_sources = {
        "idea_to_spec_repair_session": _relative_ref(repair_session_path),
        "idea_to_spec_clarification_requests": _relative_ref(clarification_requests_path),
    }
    for key, expected_ref in expected_sources.items():
        actual_ref = _text(_dict(sources.get(key)).get("source_ref"))
        if actual_ref != expected_ref:
            findings.append(
                _finding(
                    finding_id=f"import_preview_{key}_source_ref_mismatch",
                    severity="review_required",
                    message=(
                        f"Import preview source ref for {key} must match the rerun input path."
                    ),
                    evidence={"actual": actual_ref, "expected": expected_ref},
                )
            )

    preview_session = _dict(import_preview.get("session"))
    active_session = _dict(repair_session.get("session"))
    for field in (
        "session_id",
        "candidate_id",
        "workflow_lane",
        "governance_profile",
        "target_repository_role",
    ):
        actual = _text(preview_session.get(field))
        expected = _text(active_session.get(field))
        if actual != expected:
            findings.append(
                _finding(
                    finding_id=f"import_preview_session_{field}_mismatch",
                    severity="review_required",
                    message=f"Import preview session {field} must match the rerun session.",
                    evidence={"actual": actual, "expected": expected},
                )
            )
    return findings


def _draft_provenance(import_preview: dict[str, Any]) -> list[dict[str, Any]]:
    import_data = _dict(import_preview.get("import_preview"))
    provenance: list[dict[str, Any]] = []
    for candidate in [
        _dict(item) for item in _list(import_data.get("clarification_answer_candidates"))
    ]:
        source_draft_id = _text(candidate.get("source_draft_id"))
        request_id = _text(candidate.get("request_id"))
        if not source_draft_id and not request_id:
            continue
        request_snapshot = _dict(candidate.get("request_snapshot"))
        provenance.append(
            _public_safe(
                {
                    "request_id": request_id,
                    "answer_kind": candidate.get("answer_kind"),
                    "status": candidate.get("status"),
                    "source_draft_id": source_draft_id,
                    "target_ref": request_snapshot.get("target_ref"),
                    "target_artifact": request_snapshot.get("target_artifact"),
                }
            )
        )
    return provenance


def _answer_set_from_import_preview(
    import_preview: dict[str, Any],
    *,
    import_preview_findings: list[dict[str, Any]],
    import_preview_path: Path | None,
) -> dict[str, Any]:
    import_data = _dict(import_preview.get("import_preview"))
    candidates = [
        _dict(candidate) for candidate in _list(import_data.get("clarification_answer_candidates"))
    ]
    answers: list[dict[str, Any]] = []
    if not import_preview_findings:
        for candidate in candidates:
            status = _text(candidate.get("status"))
            if status not in ANSWER_CANDIDATE_STATUSES:
                continue
            answers.append(
                _public_safe(
                    {
                        "request_id": candidate.get("request_id"),
                        "answer_kind": candidate.get("answer_kind"),
                        "status": status,
                        "authority": candidate.get("authority"),
                        "value": candidate.get("value"),
                        "rationale": (
                            "Imported from SpecSpace repair draft preview "
                            f"{candidate.get('source_draft_id') or 'unknown-draft'}."
                        ),
                        "source_draft_id": candidate.get("source_draft_id"),
                    }
                )
            )
    return {
        "artifact_kind": "idea_to_spec_clarification_answer_set",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": ANSWER_SET_CONTRACT_REF,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "specspace_repair_draft_import_preview": {
                "artifact_kind": import_preview.get("artifact_kind"),
                "contract_ref": import_preview.get("contract_ref"),
                "source_ref": _relative_ref(import_preview_path),
            }
        },
        "answers": answers,
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "redaction_enforced_by": "recursive_public_safe_field_filter",
            "raw_idea_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
            "raw_operator_note_published": False,
        },
        "summary": {
            "status": (
                "answer_set_ready"
                if not import_preview_findings
                else "answer_set_blocked_by_import_preview"
            ),
            "answer_count": len(answers),
            "import_preview_finding_count": len(import_preview_findings),
        },
    }


def _source_refs(
    *,
    import_preview_path: Path,
    repair_session_path: Path,
    clarification_requests_path: Path,
) -> dict[str, Any]:
    return {
        "specspace_repair_draft_import_preview": _relative_ref(import_preview_path),
        "previous_repair_session": _relative_ref(repair_session_path),
        "clarification_requests": _relative_ref(clarification_requests_path),
    }


def _set_nested_source_ref(artifact: dict[str, Any], path: tuple[str, ...], value: str) -> None:
    cursor = artifact
    for key in path[:-1]:
        nested = cursor.get(key)
        if not isinstance(nested, dict):
            nested = {}
            cursor[key] = nested
        cursor = nested
    cursor[path[-1]] = value


def _normalize_chain_source_refs(
    *,
    ontology_decisions: dict[str, Any],
    rerun_input: dict[str, Any],
    rerun_preview: dict[str, Any],
    rerun_materialization: dict[str, Any],
    clarification_answers_output: Path,
    ontology_decisions_output: Path,
    rerun_input_output: Path,
    rerun_preview_output: Path,
) -> None:
    # The sibling builders do not all share identical external-path fallback
    # semantics. Normalize the refs to the paths this bridge will write so the
    # repair-session journal can prove the exact custom-output chain.
    _set_nested_source_ref(
        ontology_decisions,
        ("source_artifacts", "clarification_answers", "source_ref"),
        _relative_ref(clarification_answers_output),
    )
    _set_nested_source_ref(
        rerun_input,
        ("source_artifacts", "clarification_answers", "source_ref"),
        _relative_ref(clarification_answers_output),
    )
    _set_nested_source_ref(
        rerun_input,
        ("source_artifacts", "product_ontology_gap_review_decisions", "source_ref"),
        _relative_ref(ontology_decisions_output),
    )
    _set_nested_source_ref(
        rerun_preview,
        ("source_artifacts", "rerun_input", "source_ref"),
        _relative_ref(rerun_input_output),
    )
    _set_nested_source_ref(
        rerun_materialization,
        ("source_artifacts", "rerun_preview", "source_ref"),
        _relative_ref(rerun_preview_output),
    )


def build_specspace_repair_drafts_to_rerun_artifacts(
    *,
    import_preview: dict[str, Any],
    repair_session: dict[str, Any],
    clarification_requests: dict[str, Any],
    active_candidate: dict[str, Any],
    intake: dict[str, Any],
    candidate_graph: dict[str, Any],
    promotion_gate: dict[str, Any],
    import_preview_path: Path,
    repair_session_path: Path,
    clarification_requests_path: Path,
    active_candidate_path: Path,
    intake_path: Path,
    candidate_graph_path: Path,
    promotion_gate_path: Path,
    clarification_answers_output: Path,
    ontology_decisions_output: Path,
    rerun_input_output: Path,
    rerun_preview_output: Path,
    rerun_materialization_output: Path,
    repair_session_output: Path,
    operator_ref: str = "local_operator:unattributed",
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    import_preview_findings = _validate_import_preview(import_preview)
    import_preview_findings.extend(
        _validate_import_preview_refs(
            import_preview,
            repair_session=repair_session,
            repair_session_path=repair_session_path,
            clarification_requests_path=clarification_requests_path,
        )
    )
    answer_set = _answer_set_from_import_preview(
        import_preview,
        import_preview_findings=import_preview_findings,
        import_preview_path=import_preview_path,
    )
    clarification_answers = (
        idea_to_spec_clarification_answers.build_idea_to_spec_clarification_answers(
            clarification_requests=clarification_requests,
            answer_set=answer_set,
            requests_path=clarification_requests_path,
            answer_set_path=None,
        )
    )
    ontology_decisions = (
        product_ontology_gap_review_decisions.build_product_ontology_gap_review_decisions(
            answers_report=clarification_answers,
            answers_path=clarification_answers_output,
        )
    )
    rerun_input = idea_to_spec_answer_rerun_input.build_idea_to_spec_answer_rerun_input(
        answers_report=clarification_answers,
        ontology_decisions_report=ontology_decisions,
        answers_path=clarification_answers_output,
        ontology_decisions_path=ontology_decisions_output,
    )
    rerun_preview = idea_to_spec_rerun_preview.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake,
        candidate_graph=candidate_graph,
        rerun_input_path=rerun_input_output,
        intake_path=intake_path,
        candidate_graph_path=candidate_graph_path,
    )
    rerun_materialization = (
        idea_to_spec_rerun_materialization.build_idea_to_spec_rerun_materialization(
            rerun_preview=rerun_preview,
            candidate_graph=candidate_graph,
            rerun_preview_path=rerun_preview_output,
            candidate_graph_path=candidate_graph_path,
            output_path=rerun_materialization_output,
        )
    )
    _normalize_chain_source_refs(
        ontology_decisions=ontology_decisions,
        rerun_input=rerun_input,
        rerun_preview=rerun_preview,
        rerun_materialization=rerun_materialization,
        clarification_answers_output=clarification_answers_output,
        ontology_decisions_output=ontology_decisions_output,
        rerun_input_output=rerun_input_output,
        rerun_preview_output=rerun_preview_output,
    )
    updated_repair_session = (
        idea_to_spec_repair_session_journal.build_idea_to_spec_repair_session_journal(
            active_candidate=active_candidate,
            clarification_requests=clarification_requests,
            clarification_answers=clarification_answers,
            ontology_decisions=ontology_decisions,
            rerun_input=rerun_input,
            rerun_preview=rerun_preview,
            rerun_materialization=rerun_materialization,
            promotion_gate=promotion_gate,
            active_candidate_path=active_candidate_path,
            clarification_requests_path=clarification_requests_path,
            clarification_answers_path=clarification_answers_output,
            ontology_decisions_path=ontology_decisions_output,
            rerun_input_path=rerun_input_output,
            rerun_preview_path=rerun_preview_output,
            rerun_materialization_path=rerun_materialization_output,
            promotion_gate_path=promotion_gate_path,
            session_id=_text(_dict(repair_session.get("session")).get("session_id")) or None,
            operator_ref=operator_ref,
        )
    )
    artifacts = {
        "clarification_answers": clarification_answers,
        "ontology_decisions": ontology_decisions,
        "rerun_input": rerun_input,
        "rerun_preview": rerun_preview,
        "rerun_materialization": rerun_materialization,
        "repair_session": updated_repair_session,
    }
    source_refs = _source_refs(
        import_preview_path=import_preview_path,
        repair_session_path=repair_session_path,
        clarification_requests_path=clarification_requests_path,
    )
    output_refs = {
        "clarification_answers": _relative_ref(clarification_answers_output),
        "ontology_decisions": _relative_ref(ontology_decisions_output),
        "rerun_input": _relative_ref(rerun_input_output),
        "rerun_preview": _relative_ref(rerun_preview_output),
        "rerun_materialization": _relative_ref(rerun_materialization_output),
        "repair_session": _relative_ref(repair_session_output),
    }
    findings = list(import_preview_findings)
    for key, artifact in artifacts.items():
        findings.extend(
            {
                **finding,
                "source_artifact_key": key,
            }
            for finding in _list(artifact.get("findings"))
            if isinstance(finding, dict)
        )
    ready = not findings
    import_data = _dict(import_preview.get("import_preview"))
    draft_provenance = _draft_provenance(import_preview)
    report = {
        "artifact_kind": "specspace_repair_draft_rerun_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": source_refs,
        "written_artifacts": output_refs,
        "import_preview_summary": _public_safe(_dict(import_preview.get("summary"))),
        "answer_set_summary": answer_set["summary"],
        "draft_provenance": draft_provenance,
        "rerun_artifact_summaries": {
            key: _public_safe(_dict(artifact.get("summary"))) for key, artifact in artifacts.items()
        },
        "gap_count_semantics": {
            "unresolved_ontology_gap_count": (
                "Actual count from idea_to_spec_rerun_materialization after replaying "
                "ready draft-derived decisions."
            ),
            "would_leave_unresolved_gap_count": (
                "Preview estimate copied from specspace_repair_draft_import_preview before "
                "materialization; use unresolved_ontology_gap_count after rerun."
            ),
        },
        "readiness": {
            "ready": ready,
            "review_state": (
                "repair_draft_rerun_ready" if ready else "repair_draft_rerun_review_required"
            ),
            "blocked_by": [
                _text(finding.get("finding_id"))
                for finding in findings
                if _text(finding.get("finding_id"))
            ],
            "next_artifact": (
                "SpecSpace product repair workspace"
                if ready
                else "repair invalid SpecSpace repair draft rerun inputs"
            ),
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
            "status": (
                "repair_draft_rerun_ready" if ready else "repair_draft_rerun_review_required"
            ),
            "accepted_for_rerun_count": _dict(import_preview.get("summary")).get(
                "accepted_for_rerun_count", 0
            ),
            "deferred_count": _dict(import_preview.get("summary")).get("deferred_count", 0),
            "invalid_draft_count": _dict(import_preview.get("summary")).get(
                "invalid_draft_count", 0
            ),
            "superseded_draft_count": _dict(import_preview.get("summary")).get(
                "superseded_draft_count", 0
            ),
            "clarification_answer_count": len(_list(clarification_answers.get("answers"))),
            "ontology_decision_count": len(_list(ontology_decisions.get("decisions"))),
            "resolved_ontology_gap_count": _dict(rerun_materialization.get("summary")).get(
                "resolved_ontology_gap_count", 0
            ),
            "unresolved_ontology_gap_count": _dict(rerun_materialization.get("summary")).get(
                "unresolved_ontology_gap_count", 0
            ),
            "would_leave_unresolved_gap_count": import_data.get("would_leave_unresolved_gaps", 0),
            "draft_provenance_count": len(draft_provenance),
            "finding_count": len(findings),
        },
    }
    return report, artifacts


def _write_artifacts(
    *,
    report: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    clarification_answers_output: Path,
    ontology_decisions_output: Path,
    rerun_input_output: Path,
    rerun_preview_output: Path,
    rerun_materialization_output: Path,
    repair_session_output: Path,
    report_output: Path,
) -> None:
    if _dict(report.get("readiness")).get("ready") is not True:
        write_json(report, report_output)
        return
    write_json(artifacts["clarification_answers"], clarification_answers_output)
    write_json(artifacts["ontology_decisions"], ontology_decisions_output)
    write_json(artifacts["rerun_input"], rerun_input_output)
    write_json(artifacts["rerun_preview"], rerun_preview_output)
    write_json(artifacts["rerun_materialization"], rerun_materialization_output)
    for key, path in (
        ("clarification_answers", clarification_answers_output),
        ("ontology_decisions", ontology_decisions_output),
        ("rerun_input", rerun_input_output),
        ("rerun_preview", rerun_preview_output),
        ("rerun_materialization", rerun_materialization_output),
    ):
        source = _dict(artifacts["repair_session"].get("source_artifacts")).get(key)
        if isinstance(source, dict):
            source["sha256"] = _sha256(path)
    write_json(artifacts["repair_session"], repair_session_output)
    write_json(report, report_output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-preview", default=DEFAULT_IMPORT_PREVIEW_PATH, type=Path)
    parser.add_argument("--repair-session", default=DEFAULT_REPAIR_SESSION_PATH, type=Path)
    parser.add_argument(
        "--clarification-requests",
        default=DEFAULT_CLARIFICATION_REQUESTS_PATH,
        type=Path,
    )
    parser.add_argument("--active-candidate", default=DEFAULT_ACTIVE_CANDIDATE_PATH, type=Path)
    parser.add_argument("--intake", default=DEFAULT_INTAKE_PATH, type=Path)
    parser.add_argument("--candidate-graph", default=DEFAULT_CANDIDATE_GRAPH_PATH, type=Path)
    parser.add_argument("--promotion-gate", default=DEFAULT_PROMOTION_GATE_PATH, type=Path)
    parser.add_argument(
        "--clarification-answers-output",
        default=DEFAULT_CLARIFICATION_ANSWERS_OUTPUT,
        type=Path,
    )
    parser.add_argument(
        "--ontology-decisions-output",
        default=DEFAULT_ONTOLOGY_DECISIONS_OUTPUT,
        type=Path,
    )
    parser.add_argument("--rerun-input-output", default=DEFAULT_RERUN_INPUT_OUTPUT, type=Path)
    parser.add_argument("--rerun-preview-output", default=DEFAULT_RERUN_PREVIEW_OUTPUT, type=Path)
    parser.add_argument(
        "--rerun-materialization-output",
        default=DEFAULT_RERUN_MATERIALIZATION_OUTPUT,
        type=Path,
    )
    parser.add_argument("--repair-session-output", default=DEFAULT_REPAIR_SESSION_OUTPUT, type=Path)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT, type=Path)
    parser.add_argument("--operator-ref", default="local_operator:unattributed")
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report, artifacts = build_specspace_repair_drafts_to_rerun_artifacts(
        import_preview=load_json(args.import_preview),
        repair_session=load_json(args.repair_session),
        clarification_requests=load_json(args.clarification_requests),
        active_candidate=load_json(args.active_candidate),
        intake=load_json(args.intake),
        candidate_graph=load_json(args.candidate_graph),
        promotion_gate=load_json(args.promotion_gate),
        import_preview_path=args.import_preview,
        repair_session_path=args.repair_session,
        clarification_requests_path=args.clarification_requests,
        active_candidate_path=args.active_candidate,
        intake_path=args.intake,
        candidate_graph_path=args.candidate_graph,
        promotion_gate_path=args.promotion_gate,
        clarification_answers_output=args.clarification_answers_output,
        ontology_decisions_output=args.ontology_decisions_output,
        rerun_input_output=args.rerun_input_output,
        rerun_preview_output=args.rerun_preview_output,
        rerun_materialization_output=args.rerun_materialization_output,
        repair_session_output=args.repair_session_output,
        operator_ref=args.operator_ref,
    )
    _write_artifacts(
        report=report,
        artifacts=artifacts,
        clarification_answers_output=args.clarification_answers_output,
        ontology_decisions_output=args.ontology_decisions_output,
        rerun_input_output=args.rerun_input_output,
        rerun_preview_output=args.rerun_preview_output,
        rerun_materialization_output=args.rerun_materialization_output,
        repair_session_output=args.repair_session_output,
        report_output=args.report_output,
    )
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('clarification_answer_count', 0)} answers, "
        f"{summary.get('ontology_decision_count', 0)} ontology decisions, "
        f"{summary.get('unresolved_ontology_gap_count', 0)} unresolved ontology gaps -> "
        f"{_relative_ref(args.report_output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
