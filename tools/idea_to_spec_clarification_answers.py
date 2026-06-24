"""Validate idea-to-spec clarification answers without applying mutations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0164"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.clarification-answers.v0.1"
ANSWER_SET_CONTRACT_REF = "specgraph.idea-to-spec.clarification-answer-set.v0.1"
REQUESTS_CONTRACT_REF = "specgraph.idea-to-spec.clarification-requests.v0.1"
DEFAULT_REQUESTS_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "idea_to_spec_clarification_answers"
    / "clarification_requests_blocking.json"
)
DEFAULT_ANSWER_SET_PATH = (
    ROOT / "tests" / "fixtures" / "idea_to_spec_clarification_answers" / "answers_ready.json"
)
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_to_spec_clarification_answers.json"

ACCEPTED_STATUSES = {"accepted_for_candidate", "accepted_for_review"}
ANSWER_AUTHORITIES = {
    "operator_approved",
    "owner_approved",
    "agent_proposed",
    "deferred_by_operator",
}
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


def _text_list(value: Any) -> list[str]:
    return [item.strip() for item in _list(value) if isinstance(item, str) and item.strip()]


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
        "source": "idea_to_spec_clarification_answers",
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
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
    }


def _validate_root(
    clarification_requests: dict[str, Any],
    answer_set: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if clarification_requests.get("artifact_kind") != "idea_to_spec_clarification_requests":
        findings.append(
            _finding(
                finding_id="clarification_requests_wrong_artifact_kind",
                severity="review_required",
                message="Answer validation requires idea_to_spec_clarification_requests input.",
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
    if answer_set.get("artifact_kind") != "idea_to_spec_clarification_answer_set":
        findings.append(
            _finding(
                finding_id="answer_set_wrong_artifact_kind",
                severity="review_required",
                message="Answer validation requires idea_to_spec_clarification_answer_set input.",
                evidence={"artifact_kind": answer_set.get("artifact_kind")},
            )
        )
    if answer_set.get("contract_ref") != ANSWER_SET_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="answer_set_contract_ref_unsupported",
                severity="review_required",
                message=f"Answer set contract_ref must be {ANSWER_SET_CONTRACT_REF}.",
                evidence={"contract_ref": answer_set.get("contract_ref")},
            )
        )
    for name, artifact in (
        ("clarification_requests", clarification_requests),
        ("answer_set", answer_set),
    ):
        if artifact.get("schema_version") != SCHEMA_VERSION:
            findings.append(
                _finding(
                    finding_id=f"{name}_schema_version_unsupported",
                    severity="review_required",
                    message=f"{name} schema_version must be 1.",
                    evidence={"schema_version": artifact.get("schema_version")},
                )
            )
    return findings


def _request_index(clarification_requests: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for raw_request in _list(clarification_requests.get("clarification_requests")):
        request = _dict(raw_request)
        request_id = _text(request.get("id"))
        if request_id:
            index[request_id] = request
    return index


def _normalize_answer(
    answer: dict[str, Any],
    *,
    request: dict[str, Any] | None,
    index: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    request_id = _text(answer.get("request_id"))
    answer_kind = _text(answer.get("answer_kind"))
    authority = _text(answer.get("authority"))
    status = _text(answer.get("status"), "proposed")
    findings: list[dict[str, Any]] = []
    if not request_id:
        findings.append(
            _finding(
                finding_id="answer_request_id_missing",
                severity="review_required",
                message="Clarification answer requires request_id.",
                evidence={"index": index},
            )
        )
    if request is None and request_id:
        findings.append(
            _finding(
                finding_id="answer_request_unknown",
                severity="review_required",
                message="Clarification answer must reference an existing request id.",
                evidence={"request_id": request_id, "index": index},
            )
        )
    allowed_actions = _text_list(_dict(request or {}).get("suggested_actions"))
    if answer_kind and allowed_actions and answer_kind not in allowed_actions:
        findings.append(
            _finding(
                finding_id="answer_kind_not_allowed",
                severity="review_required",
                message="Clarification answer_kind must match one of request.suggested_actions.",
                evidence={
                    "request_id": request_id,
                    "answer_kind": answer_kind,
                    "allowed_actions": allowed_actions,
                },
            )
        )
    if not answer_kind:
        findings.append(
            _finding(
                finding_id="answer_kind_missing",
                severity="review_required",
                message="Clarification answer requires answer_kind.",
                evidence={"request_id": request_id, "index": index},
            )
        )
    if authority not in ANSWER_AUTHORITIES:
        findings.append(
            _finding(
                finding_id="answer_authority_unsupported",
                severity="review_required",
                message="Clarification answer requires supported authority.",
                evidence={
                    "request_id": request_id,
                    "authority": authority,
                    "supported": sorted(ANSWER_AUTHORITIES),
                },
            )
        )
    if status not in ACCEPTED_STATUSES and status not in {"proposed", "rejected", "deferred"}:
        findings.append(
            _finding(
                finding_id="answer_status_unsupported",
                severity="review_required",
                message="Clarification answer status is unsupported.",
                evidence={"request_id": request_id, "status": status},
            )
        )
    normalized = {
        "request_id": request_id,
        "answer_kind": answer_kind,
        "status": status,
        "authority": authority,
        "value": _public_safe(_dict(answer.get("value"))),
        "rationale": _text(answer.get("rationale")),
        "request_snapshot": {
            "kind": _dict(request or {}).get("kind"),
            "severity": _dict(request or {}).get("severity"),
            "target_artifact": _dict(request or {}).get("target_artifact"),
            "target_ref": _dict(request or {}).get("target_ref"),
            "suggested_answer_shape": _dict(request or {}).get("suggested_answer_shape"),
        },
    }
    return normalized, findings


def _duplicate_answer_findings(answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    findings: list[dict[str, Any]] = []
    for index, answer in enumerate(answers):
        request_id = _text(answer.get("request_id"))
        if not request_id:
            continue
        if request_id in seen:
            findings.append(
                _finding(
                    finding_id="answer_request_duplicate",
                    severity="review_required",
                    message="Only one clarification answer is allowed per request in one set.",
                    evidence={
                        "request_id": request_id,
                        "first_index": seen[request_id],
                        "duplicate_index": index,
                    },
                )
            )
        else:
            seen[request_id] = index
    return findings


def build_idea_to_spec_clarification_answers(
    *,
    clarification_requests: dict[str, Any],
    answer_set: dict[str, Any],
    requests_path: Path | None = None,
    answer_set_path: Path | None = None,
) -> dict[str, Any]:
    findings = _validate_root(clarification_requests, answer_set)
    requests_by_id = _request_index(clarification_requests)
    normalized_answers: list[dict[str, Any]] = []
    raw_answers = [_dict(item) for item in _list(answer_set.get("answers"))]
    findings.extend(_duplicate_answer_findings(raw_answers))
    for index, answer in enumerate(raw_answers):
        request = requests_by_id.get(_text(answer.get("request_id")))
        normalized, answer_findings = _normalize_answer(answer, request=request, index=index)
        normalized_answers.append(normalized)
        findings.extend(answer_findings)

    answers_by_request = {
        answer["request_id"]: answer
        for answer in normalized_answers
        if _text(answer.get("request_id")) and answer.get("status") in ACCEPTED_STATUSES
    }
    blocking_requests = [
        request
        for request in requests_by_id.values()
        if _text(request.get("severity")) == "blocking"
    ]
    unresolved_blocking = [
        {
            "request_id": request.get("id"),
            "kind": request.get("kind"),
            "target_artifact": request.get("target_artifact"),
            "target_ref": request.get("target_ref"),
        }
        for request in blocking_requests
        if request.get("id") not in answers_by_request
    ]
    accepted_count = sum(
        1 for answer in normalized_answers if answer.get("status") in ACCEPTED_STATUSES
    )
    ready = not findings and not unresolved_blocking
    source_requests_ref = (
        _relative_ref(requests_path) if requests_path else "inline:clarification_requests"
    )
    source_answer_set_ref = (
        _relative_ref(answer_set_path) if answer_set_path else "inline:answer_set"
    )
    return {
        "artifact_kind": "idea_to_spec_clarification_answers",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "clarification_requests": {
                "artifact_kind": clarification_requests.get("artifact_kind"),
                "contract_ref": clarification_requests.get("contract_ref"),
                "source_ref": source_requests_ref,
                "request_count": len(requests_by_id),
            },
            "answer_set": {
                "artifact_kind": answer_set.get("artifact_kind"),
                "contract_ref": answer_set.get("contract_ref"),
                "source_ref": source_answer_set_ref,
                "answer_count": len(raw_answers),
            },
        },
        "answers": normalized_answers,
        "unresolved_blocking_requests": unresolved_blocking,
        "readiness": {
            "ready": ready,
            "review_state": "answers_ready_for_rerun" if ready else "answers_review_required",
            "blocked_by": [finding["finding_id"] for finding in findings]
            + [
                request["request_id"]
                for request in unresolved_blocking
                if _text(request.get("request_id"))
            ],
            "next_artifact": "runs/user_idea_intake_source.json",
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
            "status": "answers_ready_for_rerun" if ready else "answers_review_required",
            "answer_count": len(normalized_answers),
            "accepted_answer_count": accepted_count,
            "blocking_request_count": len(blocking_requests),
            "unresolved_blocking_count": len(unresolved_blocking),
            "finding_count": len(findings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", default=DEFAULT_REQUESTS_PATH, type=Path)
    parser.add_argument("--answers", default=DEFAULT_ANSWER_SET_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(args.requests),
        answer_set=load_json(args.answers),
        requests_path=args.requests,
        answer_set_path=args.answers,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('accepted_answer_count', 0)}/"
        f"{summary.get('blocking_request_count', 0)} blocking answers accepted -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
