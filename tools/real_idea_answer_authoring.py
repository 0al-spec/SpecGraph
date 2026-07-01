"""Build, validate, and materialize first-class real-idea answer templates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import idea_intake_clarification_rerun
import idea_to_spec_answer_rerun_input
import idea_to_spec_clarification_answers
import product_ontology_gap_review_decisions

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0194"
SCHEMA_VERSION = 1
TEMPLATE_CONTRACT_REF = "specgraph.idea-to-spec.real-idea-answer-template.v0.1"
REPORT_CONTRACT_REF = "specgraph.idea-to-spec.real-idea-answer-authoring-report.v0.1"
ANSWER_SET_CONTRACT_REF = "specgraph.idea-to-spec.clarification-answer-set.v0.1"
REQUESTS_CONTRACT_REF = "specgraph.idea-to-spec.clarification-requests.v0.1"

DEFAULT_RUN_DIR = ROOT / "runs" / "real_idea_smoke"
RESERVED_RUN_DIRS = {"runs"}
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
PRIVATE_TEXT_MARKERS = (
    "/Users/",
    "/home/",
    "/private/",
    "/tmp/",
    "\\",
    "-----BEGIN",
    "api-key",
    "apikey",
    "api_key",
    "authorization",
    "bearer ",
    "password",
    "secret",
    "token=",
)
FALSE_AUTHORITY_FIELDS = {
    "may_execute_prompt_agent",
    "may_infer_domain_model",
    "may_apply_answers_to_source_artifacts",
    "may_apply_decisions_to_source_artifacts",
    "may_mutate_user_intent",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_write_ontology_lockfile",
    "may_accept_ontology_terms",
    "may_mark_candidate_graph_accepted",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_publish_read_model",
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


def _slug(value: str, fallback: str = "answer") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _repo_relative_path(value: str | Path, *, field: str) -> tuple[str, Path]:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (ROOT / path).resolve()
    try:
        rel = resolved.relative_to(ROOT)
    except ValueError as exc:
        raise SystemExit(f"{field} must stay inside the SpecGraph repository: {value}") from exc
    if not rel.parts:
        raise SystemExit(f"{field} must not point to the repository root.")
    return rel.as_posix(), ROOT / rel


def _relative_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        digest = hashlib.sha256(path.resolve().as_posix().encode("utf-8")).hexdigest()[:16]
        return f"external:{digest}:{path.name}"


def _reject_reserved_run_dir(run_dir_ref: str) -> None:
    if run_dir_ref in RESERVED_RUN_DIRS:
        raise SystemExit(
            f"REAL_IDEA_SMOKE_RUN_DIR={run_dir_ref} is reserved for shared SpecGraph runs. "
            "Use a child directory such as runs/real_idea_smoke or runs/<id>."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


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
        "source": "real_idea_answer_authoring",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {field: False for field in sorted(FALSE_AUTHORITY_FIELDS)}


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_idea_text_published": False,
        "raw_prompt_published": False,
        "raw_model_output_published": False,
        "raw_operator_note_published": False,
    }


def _request_index(clarification_requests: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for raw_request in _list(clarification_requests.get("clarification_requests")):
        request = _dict(raw_request)
        request_id = _text(request.get("id"))
        if request_id:
            index[request_id] = request
    return index


def _stage_request_path(stage: str, run_dir: Path) -> Path:
    if stage == "intake":
        return run_dir / "idea_intake_clarification_requests.json"
    if stage == "repair":
        return run_dir / "idea_to_spec_clarification_requests.json"
    repair = run_dir / "idea_to_spec_clarification_requests.json"
    intake = run_dir / "idea_intake_clarification_requests.json"
    if repair.exists():
        return repair
    return intake


def _detect_stage(stage: str, run_dir: Path, requests_path: Path) -> str:
    if stage in {"intake", "repair"}:
        return stage
    if requests_path.name == "idea_intake_clarification_requests.json":
        return "intake"
    if requests_path.name == "idea_to_spec_clarification_requests.json":
        return "repair"
    if requests_path == run_dir / "idea_intake_clarification_requests.json":
        return "intake"
    return "repair"


def _target_type(request: dict[str, Any], stage: str) -> str:
    kind = _text(request.get("kind"))
    if stage == "intake" or kind in {
        "missing_context",
        "missing_event_storming_context",
    }:
        return "intake_clarification"
    if kind == "ontology_gap":
        return "ontology_gap"
    if kind == "candidate_gap":
        return "candidate_gap"
    return "repair_clarification"


def _default_action(request: dict[str, Any]) -> str:
    actions = _text_list(request.get("suggested_actions"))
    for preferred in (
        "answer_question",
        "provide_candidate_context",
        "propose_project_local_term",
        "bind_existing_term",
        "alias",
        "reject",
        "defer",
        "defer_candidate",
    ):
        if preferred in actions:
            return preferred
    return actions[0] if actions else ""


def _value_template(action: str, request: dict[str, Any]) -> Any:
    shape = _text(request.get("suggested_answer_shape"))
    kind = _text(request.get("kind"))
    target_ref = _text(request.get("target_ref"))
    if action == "bind_existing_term":
        return {"term": "", "ontology_ref": ""}
    if action == "alias":
        return {"term": "", "alias_of": ""}
    if action == "propose_project_local_term":
        return {"terms": [""], "term_scope": "project_local"}
    if action in {"reject", "reject_candidate"}:
        return {"reason": ""}
    if action in {"defer", "defer_candidate"}:
        return {"follow_up": ""}
    if action == "provide_candidate_context":
        return {
            "resolution_intent": "add_enforcement_mechanism",
            "affected_refs": [target_ref] if target_ref else [],
            "context": "",
            "evidence_refs": [],
        }
    if action == "answer_question":
        if (
            "ontology_ref[]" in shape
            or "domain_ref[]" in shape
            or "context_ref[]" in shape
            or "ontology_layer_ref[]" in shape
            or "model_applicability_ref[]" in shape
        ):
            return {"refs": [""]}
        if "event_storming_entry[]" in shape or kind == "missing_event_storming_context":
            return {"entries": [""]}
        return {"answer": ""}
    return {"answer": ""}


def _required_fields(action: str, request: dict[str, Any]) -> list[str]:
    if action == "bind_existing_term":
        return ["value.term", "value.ontology_ref"]
    if action == "alias":
        return ["value.term", "value.alias_of"]
    if action == "propose_project_local_term":
        return ["value.terms[]"]
    if action in {"reject", "reject_candidate"}:
        return ["value.reason"]
    if action in {"defer", "defer_candidate"}:
        return ["value.follow_up"]
    if action == "provide_candidate_context":
        return ["value.context"]
    if action == "answer_question":
        return ["value"]
    return ["value"]


def _substantive(value: Any) -> bool:
    safe = _public_safe(value)
    if isinstance(safe, str):
        return bool(_text(safe))
    if isinstance(safe, list):
        return any(_substantive(item) for item in safe)
    if isinstance(safe, dict):
        return any(_substantive(item) for item in safe.values())
    return safe not in (None, "", [], {})


def _field_present(value: Any, field: str) -> bool:
    if field == "value":
        return _substantive(value)
    if not field.startswith("value."):
        return True
    path = field.removeprefix("value.")
    current = value
    if path.endswith("[]"):
        key = path[:-2]
        if not isinstance(current, dict):
            return False
        return bool(_text_list(current.get(key)))
    if not isinstance(current, dict):
        return False
    return _substantive(current.get(path))


def _answer_target(request: dict[str, Any], *, stage: str, index: int) -> dict[str, Any]:
    request_id = _text(request.get("id"), f"request-{index}")
    action = _default_action(request)
    value = _value_template(action, request)
    return {
        "target_id": f"answer-target.{_slug(request_id)}",
        "target_type": _target_type(request, stage),
        "request_id": request_id,
        "request_kind": _text(request.get("kind")),
        "severity": _text(request.get("severity")),
        "status": _text(request.get("status"), "open"),
        "question": _text(request.get("question")),
        "target_artifact": _text(request.get("target_artifact")),
        "target_ref": _text(request.get("target_ref")),
        "blocks": _text_list(request.get("blocks")),
        "accepted_actions": _text_list(request.get("suggested_actions")),
        "suggested_answer_shape": _text(request.get("suggested_answer_shape")),
        "value_templates_by_action": {
            allowed: _value_template(allowed, request)
            for allowed in _text_list(request.get("suggested_actions"))
        },
        "required_fields_by_action": {
            allowed: _required_fields(allowed, request)
            for allowed in _text_list(request.get("suggested_actions"))
        },
        "evidence_refs": [
            _public_safe(_dict(item)) for item in _list(request.get("source_findings"))
        ],
        "operator_answer": {
            "request_id": request_id,
            "answer_kind": action,
            "status": "proposed",
            "authority": "operator_approved",
            "value": value,
            "rationale": "",
        },
    }


def build_template(
    *,
    clarification_requests: dict[str, Any],
    requests_path: Path,
    stage: str,
    run_dir: Path,
) -> dict[str, Any]:
    requests = [_dict(item) for item in _list(clarification_requests.get("clarification_requests"))]
    targets = [
        _answer_target(request, stage=stage, index=index) for index, request in enumerate(requests)
    ]
    findings: list[dict[str, Any]] = []
    if clarification_requests.get("artifact_kind") != "idea_to_spec_clarification_requests":
        findings.append(
            _finding(
                finding_id="clarification_requests_wrong_artifact_kind",
                severity="review_required",
                message="Answer template requires idea_to_spec_clarification_requests input.",
                evidence={"artifact_kind": clarification_requests.get("artifact_kind")},
            )
        )
    if clarification_requests.get("contract_ref") != REQUESTS_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="clarification_requests_contract_ref_unsupported",
                severity="review_required",
                message=f"Clarification requests contract_ref must be {REQUESTS_CONTRACT_REF}.",
                evidence={"contract_ref": clarification_requests.get("contract_ref")},
            )
        )
    if not targets:
        findings.append(
            _finding(
                finding_id="answer_targets_missing",
                severity="review_required",
                message="No clarification requests are available for answer authoring.",
            )
        )
    ready = not findings
    return {
        "artifact_kind": "real_idea_answer_template",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": TEMPLATE_CONTRACT_REF,
        "generated_at": _now_iso(),
        "stage": stage,
        "run_dir": _relative_ref(run_dir),
        "source_artifacts": {
            "clarification_requests": {
                "artifact_kind": clarification_requests.get("artifact_kind"),
                "contract_ref": clarification_requests.get("contract_ref"),
                "source_ref": _relative_ref(requests_path),
                "request_count": len(requests),
            }
        },
        "answer_targets": targets,
        "operator_answers": [target["operator_answer"] for target in targets],
        "answer_set_contract": {
            "artifact_kind": "idea_to_spec_clarification_answer_set",
            "contract_ref": ANSWER_SET_CONTRACT_REF,
            "schema_version": SCHEMA_VERSION,
        },
        "readiness": {
            "ready": ready,
            "review_state": (
                "answer_template_ready" if ready else "answer_template_review_required"
            ),
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "real_idea_answer_set.json",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "summary": {
            "status": ("answer_template_ready" if ready else "answer_template_review_required"),
            "stage": stage,
            "target_count": len(targets),
            "blocking_target_count": sum(
                1 for target in targets if target["severity"] == "blocking"
            ),
            "finding_count": len(findings),
        },
    }


def _answer_edit_rank(answer: dict[str, Any]) -> tuple[int, int]:
    status = _text(answer.get("status"))
    accepted = int(status in {"accepted_for_candidate", "accepted_for_review"})
    substantive = int(_substantive(answer.get("value")) or bool(_text(answer.get("rationale"))))
    return accepted, substantive


def _prefer_answer(top_answer: dict[str, Any], nested_answer: dict[str, Any]) -> dict[str, Any]:
    top_rank = _answer_edit_rank(top_answer)
    nested_rank = _answer_edit_rank(nested_answer)
    if nested_rank > top_rank:
        return nested_answer
    return top_answer


def _template_answers(answer_input: dict[str, Any]) -> list[dict[str, Any]]:
    top_answers = [_dict(item) for item in _list(answer_input.get("operator_answers"))]
    nested_answers = [
        _dict(_dict(target).get("operator_answer"))
        for target in _list(answer_input.get("answer_targets"))
    ]
    if not top_answers:
        return nested_answers
    if not nested_answers:
        return top_answers
    merged: list[dict[str, Any]] = []
    max_len = max(len(top_answers), len(nested_answers))
    for index in range(max_len):
        top_answer = top_answers[index] if index < len(top_answers) else {}
        nested_answer = nested_answers[index] if index < len(nested_answers) else {}
        merged.append(_prefer_answer(top_answer, nested_answer))
    return merged


def _answers_from_input(
    answer_input: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    artifact_kind = _text(answer_input.get("artifact_kind"))
    if artifact_kind == "real_idea_answer_template":
        return _template_answers(answer_input), "real_idea_answer_template"
    if artifact_kind == "idea_to_spec_clarification_answer_set":
        return [_dict(item) for item in _list(answer_input.get("answers"))], artifact_kind
    return [_dict(item) for item in _list(answer_input.get("answers"))], artifact_kind or "unknown"


def answer_set_from_input(answer_input: dict[str, Any]) -> dict[str, Any]:
    answers, _ = _answers_from_input(answer_input)
    if answer_input.get("artifact_kind") == "idea_to_spec_clarification_answer_set":
        answer_set = dict(answer_input)
        answer_set["answers"] = [_public_safe(answer) for answer in answers]
        return answer_set
    return {
        "artifact_kind": "idea_to_spec_clarification_answer_set",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": ANSWER_SET_CONTRACT_REF,
        "answers": [_public_safe(answer) for answer in answers],
    }


def _scan_authority_and_raw(value: Any, *, path: str = "$") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}" if path else key
            key_lower = key.lower() if isinstance(key, str) else ""
            if (
                isinstance(key, str)
                and (key.startswith("raw_") or key in RAW_TRACE_FIELDS)
                and not (path.endswith("privacy_boundary") and item is False)
            ):
                findings.append(
                    _finding(
                        finding_id="raw_trace_field_present",
                        severity="review_required",
                        message="Answer authoring input must not contain raw trace fields.",
                        evidence={"path": key_path},
                    )
                )
            if isinstance(key, str) and key.startswith("may_") and item is not False:
                findings.append(
                    _finding(
                        finding_id="authority_field_expanded",
                        severity="review_required",
                        message="Answer authoring may_* authority fields must be explicitly false.",
                        evidence={"path": key_path},
                    )
                )
            if key_lower and any(marker.lower() in key_lower for marker in PRIVATE_TEXT_MARKERS):
                findings.append(
                    _finding(
                        finding_id="private_text_marker_present",
                        severity="review_required",
                        message="Answer authoring input contains private/local text markers.",
                        evidence={"path": key_path},
                    )
                )
            findings.extend(_scan_authority_and_raw(item, path=key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_scan_authority_and_raw(item, path=f"{path}[{index}]"))
    elif isinstance(value, str):
        lowered = value.lower()
        if any(marker.lower() in lowered for marker in PRIVATE_TEXT_MARKERS):
            findings.append(
                _finding(
                    finding_id="private_text_marker_present",
                    severity="review_required",
                    message="Answer authoring input contains private/local text markers.",
                    evidence={"path": path},
                )
            )
    return findings


def _required_value_findings(
    *,
    answer_set: dict[str, Any],
    clarification_requests: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = _request_index(clarification_requests)
    findings: list[dict[str, Any]] = []
    for index, answer in enumerate([_dict(item) for item in _list(answer_set.get("answers"))]):
        if _text(answer.get("status")) not in {
            "accepted_for_candidate",
            "accepted_for_review",
        }:
            continue
        request_id = _text(answer.get("request_id"))
        request = requests.get(request_id)
        if not request:
            continue
        action = _text(answer.get("answer_kind"))
        value = answer.get("value")
        for field in _required_fields(action, request):
            if not _field_present(value, field):
                findings.append(
                    _finding(
                        finding_id="answer_required_field_empty",
                        severity="review_required",
                        message="Answer is missing a required typed value field.",
                        evidence={
                            "request_id": request_id,
                            "answer_kind": action,
                            "field": field,
                            "index": index,
                        },
                    )
                )
    return findings


def build_validation(
    *,
    clarification_requests: dict[str, Any],
    requests_path: Path,
    answer_input: dict[str, Any],
    answers_path: Path,
    stage: str,
    run_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    answer_set = answer_set_from_input(answer_input)
    validated_answers = idea_to_spec_clarification_answers.build_idea_to_spec_clarification_answers(
        clarification_requests=clarification_requests,
        answer_set=answer_set,
        requests_path=requests_path,
        answer_set_path=answers_path,
    )
    findings = [
        *_scan_authority_and_raw(answer_input),
        *_required_value_findings(
            answer_set=answer_set,
            clarification_requests=clarification_requests,
        ),
    ]
    validator_ready = _dict(validated_answers.get("readiness")).get("ready") is True
    ready = validator_ready and not findings
    report = _authoring_report(
        operation="validate",
        status=("answers_ready_for_materialization" if ready else "answers_review_required"),
        stage=stage,
        run_dir=run_dir,
        requests_path=requests_path,
        answers_path=answers_path,
        answer_set=answer_set,
        validated_answers=validated_answers,
        findings=findings,
        outputs={},
    )
    return answer_set, validated_answers, report


def _authoring_report(
    *,
    operation: str,
    status: str,
    stage: str,
    run_dir: Path,
    requests_path: Path,
    answers_path: Path | None,
    answer_set: dict[str, Any] | None,
    validated_answers: dict[str, Any] | None,
    findings: list[dict[str, Any]],
    outputs: dict[str, Any],
) -> dict[str, Any]:
    answer_count = len(_list(_dict(answer_set or {}).get("answers")))
    validated_summary = _dict(_dict(validated_answers or {}).get("summary"))
    ready = status.endswith("ready") or status in {
        "answers_ready_for_materialization",
        "answers_materialized",
    }
    return {
        "artifact_kind": "real_idea_answer_authoring_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": REPORT_CONTRACT_REF,
        "generated_at": _now_iso(),
        "operation": operation,
        "stage": stage,
        "run_dir": _relative_ref(run_dir),
        "source_artifacts": {
            "clarification_requests": {
                "source_ref": _relative_ref(requests_path),
                "artifact_kind": None,
                "contract_ref": REQUESTS_CONTRACT_REF,
            },
            "answers": {
                "source_ref": _relative_ref(answers_path) if answers_path else None,
                "answer_count": answer_count,
                "answer_set_digest": _digest(answer_set) if answer_set else None,
            },
        },
        "validated_answers": {
            "artifact_kind": _dict(validated_answers or {}).get("artifact_kind"),
            "contract_ref": _dict(validated_answers or {}).get("contract_ref"),
            "ready": _dict(_dict(validated_answers or {}).get("readiness")).get("ready"),
            "review_state": _dict(_dict(validated_answers or {}).get("readiness")).get(
                "review_state"
            ),
            "accepted_answer_count": validated_summary.get("accepted_answer_count", 0),
            "unresolved_blocking_count": validated_summary.get("unresolved_blocking_count", 0),
        },
        "outputs": outputs,
        "readiness": {
            "ready": ready and not findings,
            "review_state": status,
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": outputs.get("next_artifact"),
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "summary": {
            "status": status if not findings else "answers_review_required",
            "stage": stage,
            "answer_count": answer_count,
            "accepted_answer_count": validated_summary.get("accepted_answer_count", 0),
            "finding_count": len(findings),
        },
    }


def _write_intake_stage_artifacts(
    *,
    answer_set: dict[str, Any],
    run_dir: Path,
    requests_path: Path,
    answer_set_output: Path,
    validated_answers_output: Path,
) -> dict[str, Any]:
    raw_input = run_dir / "local_operator_user_idea_raw_input.json"
    rerun_input_output = run_dir / "idea_intake_answer_rerun_input.json"
    clarified_raw_output = run_dir / "local_operator_clarified_user_idea_raw_input.json"
    clarified_session_output = run_dir / "clarified_user_idea_intake_session.json"
    clarified_source_output = run_dir / "clarified_user_idea_intake_source.json"
    rerun_report_output = run_dir / "idea_intake_clarification_rerun_report.json"
    (
        validated_answers,
        rerun_input,
        clarified_raw,
        clarified_session,
        _clarified_source,
        rerun_report,
    ) = idea_intake_clarification_rerun.build_intake_clarification_rerun(
        raw_input=load_json(raw_input),
        raw_input_path=raw_input,
        clarification_requests=load_json(requests_path),
        clarification_requests_path=requests_path,
        answer_set=answer_set,
        answer_set_path=answer_set_output,
        validated_answers_path=validated_answers_output,
        rerun_input_path=rerun_input_output,
        clarified_raw_output_path=clarified_raw_output,
        clarified_session_output_path=clarified_session_output,
        clarified_source_output_path=clarified_source_output,
    )
    write_json(validated_answers, validated_answers_output)
    write_json(rerun_input, rerun_input_output)
    write_json(clarified_raw, clarified_raw_output)
    write_json(clarified_session, clarified_session_output)
    if clarified_source_output.exists():
        clarified_source_output.unlink()
    write_json(rerun_report, rerun_report_output)
    findings: list[dict[str, Any]] = []
    if _dict(rerun_report.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="intake_rerun_not_ready",
                severity="review_required",
                message="Intake answer materialization produced a not-ready rerun report.",
                evidence={
                    "review_state": _dict(rerun_report.get("readiness")).get("review_state"),
                    "blocked_by": _list(_dict(rerun_report.get("readiness")).get("blocked_by")),
                },
            )
        )
    if _dict(clarified_session.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="clarified_intake_session_not_ready",
                severity="review_required",
                message="Intake answer materialization did not produce a ready clarified session.",
                evidence={
                    "review_state": _dict(clarified_session.get("readiness")).get("review_state"),
                    "blocked_by": _list(
                        _dict(clarified_session.get("readiness")).get("blocked_by")
                    ),
                },
            )
        )
    outputs = {
        "validated_answers": _relative_ref(validated_answers_output),
        "rerun_input": _relative_ref(rerun_input_output),
        "clarified_raw_input": _relative_ref(clarified_raw_output),
        "clarified_intake_session": _relative_ref(clarified_session_output),
        "rerun_report": _relative_ref(rerun_report_output),
        "next_artifact": _relative_ref(clarified_session_output),
    }
    return {"outputs": outputs, "findings": findings}


def _write_repair_stage_artifacts(
    *,
    validated_answers: dict[str, Any],
    validated_answers_output: Path,
    run_dir: Path,
) -> dict[str, Any]:
    ontology_decisions_output = run_dir / "product_ontology_gap_review_decisions.json"
    rerun_input_output = run_dir / "idea_to_spec_answer_rerun_input.json"
    build_gap_decisions = (
        product_ontology_gap_review_decisions.build_product_ontology_gap_review_decisions
    )
    ontology_decisions = build_gap_decisions(
        answers_report=validated_answers,
        answers_path=validated_answers_output,
    )
    write_json(ontology_decisions, ontology_decisions_output)
    rerun_input = idea_to_spec_answer_rerun_input.build_idea_to_spec_answer_rerun_input(
        answers_report=validated_answers,
        ontology_decisions_report=ontology_decisions,
        answers_path=validated_answers_output,
        ontology_decisions_path=ontology_decisions_output,
    )
    write_json(rerun_input, rerun_input_output)
    findings: list[dict[str, Any]] = []
    if _dict(ontology_decisions.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="ontology_decisions_not_ready",
                severity="review_required",
                message="Repair answer materialization produced not-ready ontology decisions.",
                evidence={
                    "review_state": _dict(ontology_decisions.get("readiness")).get("review_state"),
                    "blocked_by": _list(
                        _dict(ontology_decisions.get("readiness")).get("blocked_by")
                    ),
                },
            )
        )
    if _dict(rerun_input.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="repair_rerun_input_not_ready",
                severity="review_required",
                message="Repair answer materialization produced a not-ready rerun input.",
                evidence={
                    "review_state": _dict(rerun_input.get("readiness")).get("review_state"),
                    "blocked_by": _list(_dict(rerun_input.get("readiness")).get("blocked_by")),
                },
            )
        )
    outputs = {
        "validated_answers": _relative_ref(validated_answers_output),
        "ontology_decisions": _relative_ref(ontology_decisions_output),
        "rerun_input": _relative_ref(rerun_input_output),
        "next_artifact": _relative_ref(rerun_input_output),
    }
    return {"outputs": outputs, "findings": findings}


def build_materialization(
    *,
    clarification_requests: dict[str, Any],
    requests_path: Path,
    answer_input: dict[str, Any],
    answers_path: Path,
    answer_set_output: Path,
    validated_answers_output: Path,
    stage: str,
    run_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    answer_set, validated_answers, validation_report = build_validation(
        clarification_requests=clarification_requests,
        requests_path=requests_path,
        answer_input=answer_input,
        answers_path=answers_path,
        stage=stage,
        run_dir=run_dir,
    )
    validation_ready = _dict(validation_report.get("readiness")).get("ready") is True
    outputs: dict[str, Any] = {}
    findings = list(_list(validation_report.get("findings")))
    status = "answers_materialized" if validation_ready else "answers_review_required"
    if validation_ready:
        outputs.update(
            {
                "answer_set": _relative_ref(answer_set_output),
                "validated_answers": _relative_ref(validated_answers_output),
            }
        )
        write_json(answer_set, answer_set_output)
        write_json(validated_answers, validated_answers_output)
        if stage == "intake":
            stage_result = _write_intake_stage_artifacts(
                answer_set=answer_set,
                run_dir=run_dir,
                requests_path=requests_path,
                answer_set_output=answer_set_output,
                validated_answers_output=validated_answers_output,
            )
            outputs.update(_dict(stage_result.get("outputs")))
            findings.extend(_list(stage_result.get("findings")))
        elif stage == "repair":
            stage_result = _write_repair_stage_artifacts(
                validated_answers=validated_answers,
                validated_answers_output=validated_answers_output,
                run_dir=run_dir,
            )
            outputs.update(_dict(stage_result.get("outputs")))
            findings.extend(_list(stage_result.get("findings")))
        if findings:
            status = "answers_review_required"
    report = _authoring_report(
        operation="materialize",
        status=status,
        stage=stage,
        run_dir=run_dir,
        requests_path=requests_path,
        answers_path=answers_path,
        answer_set=answer_set,
        validated_answers=validated_answers,
        findings=findings,
        outputs=outputs,
    )
    return answer_set, validated_answers, report


def _write_template(args: argparse.Namespace) -> int:
    run_dir_ref, run_dir = _repo_relative_path(args.run_dir, field="REAL_IDEA_SMOKE_RUN_DIR")
    _reject_reserved_run_dir(run_dir_ref)
    requests_path = args.requests or _stage_request_path(args.stage, run_dir)
    stage = _detect_stage(args.stage, run_dir, requests_path)
    template = build_template(
        clarification_requests=load_json(requests_path),
        requests_path=requests_path,
        stage=stage,
        run_dir=run_dir,
    )
    write_json(template, args.output)
    report = _authoring_report(
        operation="template",
        status=_dict(template.get("summary")).get("status", "answer_template_review_required"),
        stage=stage,
        run_dir=run_dir,
        requests_path=requests_path,
        answers_path=args.output,
        answer_set=answer_set_from_input(template),
        validated_answers=None,
        findings=[_dict(item) for item in _list(template.get("findings"))],
        outputs={
            "template": _relative_ref(args.output),
            "next_artifact": _relative_ref(args.output),
        },
    )
    write_json(report, args.report)
    print(
        f"{template['summary']['status']}: "
        f"{template['summary']['target_count']} targets -> {_relative_ref(args.output)}"
    )
    if args.strict and _dict(template.get("readiness")).get("ready") is not True:
        return 1
    return 0


def _validate_answers(args: argparse.Namespace) -> int:
    run_dir_ref, run_dir = _repo_relative_path(args.run_dir, field="REAL_IDEA_SMOKE_RUN_DIR")
    _reject_reserved_run_dir(run_dir_ref)
    requests_path = args.requests or _stage_request_path(args.stage, run_dir)
    stage = _detect_stage(args.stage, run_dir, requests_path)
    answer_set, _validated, report = build_validation(
        clarification_requests=load_json(requests_path),
        requests_path=requests_path,
        answer_input=load_json(args.answers),
        answers_path=args.answers,
        stage=stage,
        run_dir=run_dir,
    )
    if args.answer_set_output:
        write_json(answer_set, args.answer_set_output)
    write_json(report, args.report)
    print(
        f"{report['summary']['status']}: "
        f"{report['summary']['accepted_answer_count']} accepted answers -> "
        f"{_relative_ref(args.report)}"
    )
    if args.strict and _dict(report.get("readiness")).get("ready") is not True:
        return 1
    return 0


def _materialize_answers(args: argparse.Namespace) -> int:
    run_dir_ref, run_dir = _repo_relative_path(args.run_dir, field="REAL_IDEA_SMOKE_RUN_DIR")
    _reject_reserved_run_dir(run_dir_ref)
    requests_path = args.requests or _stage_request_path(args.stage, run_dir)
    stage = _detect_stage(args.stage, run_dir, requests_path)
    answer_set_output = args.answer_set_output or (run_dir / "real_idea_answer_set.json")
    if args.validated_answers_output:
        validated_answers_output = args.validated_answers_output
    elif stage == "intake":
        validated_answers_output = run_dir / "idea_intake_clarification_answers.json"
    else:
        validated_answers_output = run_dir / "idea_to_spec_clarification_answers.json"
    _answer_set, _validated, report = build_materialization(
        clarification_requests=load_json(requests_path),
        requests_path=requests_path,
        answer_input=load_json(args.answers),
        answers_path=args.answers,
        answer_set_output=answer_set_output,
        validated_answers_output=validated_answers_output,
        stage=stage,
        run_dir=run_dir,
    )
    write_json(report, args.report)
    print(
        f"{report['summary']['status']}: "
        f"{report['summary']['accepted_answer_count']} accepted answers -> "
        f"{_relative_ref(args.report)}"
    )
    if args.strict and _dict(report.get("readiness")).get("ready") is not True:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("template", "validate", "materialize"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--stage", choices=("auto", "intake", "repair"), default="auto")
        sub.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
        sub.add_argument("--requests", type=Path)
        sub.add_argument(
            "--report",
            type=Path,
            default=DEFAULT_RUN_DIR / "real_idea_answer_authoring_report.json",
        )
        sub.add_argument("--strict", action="store_true")
        if command == "template":
            sub.add_argument(
                "--output",
                type=Path,
                default=DEFAULT_RUN_DIR / "real_idea_answer_template.json",
            )
            sub.set_defaults(func=_write_template)
        else:
            sub.add_argument("--answers", type=Path, required=True)
            sub.add_argument("--answer-set-output", type=Path)
            if command == "validate":
                sub.set_defaults(func=_validate_answers)
            else:
                sub.add_argument("--validated-answers-output", type=Path)
                sub.set_defaults(func=_materialize_answers)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
