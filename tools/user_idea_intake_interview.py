"""Capture operator real-idea intake into the existing intake-session gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import idea_to_spec_clarification_answers as answer_validator
import user_idea_intake_session as session_tool

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0184"
SCHEMA_VERSION = 1
RAW_INPUT_CONTRACT_REF = "specgraph.idea-to-spec.user-idea-raw-input.v0.1"
REPORT_CONTRACT_REF = "specgraph.idea-to-spec.user-idea-intake-interview.v0.1"
CLARIFICATION_REQUESTS_CONTRACT_REF = "specgraph.idea-to-spec.clarification-requests.v0.1"
CLARIFICATION_ANSWER_SET_CONTRACT_REF = "specgraph.idea-to-spec.clarification-answer-set.v0.1"
DEFAULT_RAW_OUTPUT_PATH = ROOT / "runs" / "local_operator_user_idea_raw_input.json"
DEFAULT_SESSION_OUTPUT_PATH = ROOT / "runs" / "user_idea_intake_session.json"
DEFAULT_SOURCE_OUTPUT_PATH = ROOT / "runs" / "user_idea_intake_source.json"
DEFAULT_REPORT_OUTPUT_PATH = ROOT / "runs" / "user_idea_intake_interview_report.json"
IDEA_TEXT_ENV = "SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT"

EVENT_STORMING_CATEGORIES = (
    "actors",
    "domain_events",
    "commands",
    "policies",
    "external_systems",
    "constraints",
    "risks",
    "assumptions",
    "vocabulary_questions",
)
ACTIVE_FRAME_LIST_FIELDS = {
    "ontology_refs",
    "ontology_layer_refs",
    "domain_refs",
    "context_refs",
    "model_applicability_refs",
}
ACCEPTED_ANSWER_STATUSES = {"accepted_for_candidate", "accepted_for_review"}
APPLY_ANSWER_KINDS = {"answer_question", "provide_candidate_context"}
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
AUTHORITY_KEYS = {
    "may_execute_prompt_agent",
    "may_infer_domain_model",
    "may_mutate_user_intent",
    "may_apply_clarification_answers",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_write_ontology_lockfile",
    "may_accept_ontology_terms",
    "may_mark_candidate_graph_accepted",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_publish_read_model",
    "may_apply_state",
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
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
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,;\n]+", value) if part.strip()]
    return [item.strip() for item in _list(value) if isinstance(item, str) and item.strip()]


def _slug(value: str, fallback: str = "idea-candidate") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _relative_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _digest(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


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
        "source": "user_idea_intake_interview",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_mutate_user_intent": False,
        "may_apply_clarification_answers": False,
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


def _public_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _public_safe(item)
            for key, item in value.items()
            if isinstance(key, str)
            and key not in RAW_TRACE_FIELDS
            and key not in AUTHORITY_KEYS
            and key != "authority_boundary"
            and not key.startswith("raw_")
        }
    if isinstance(value, list):
        return [_public_safe(item) for item in value]
    return value


def _authority_findings(value: Any, *, source: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def visit(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    continue
                child_path = f"{path}.{key}" if path else key
                if key in AUTHORITY_KEYS and child is not False:
                    findings.append(
                        _finding(
                            finding_id="user_idea_interview_authority_expanded",
                            severity="blocked",
                            message=(
                                "Real idea intake inputs cannot grant execution "
                                "or mutation authority."
                            ),
                            evidence={"source": source, "field": child_path, "value": child},
                        )
                    )
                visit(child, child_path)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, "")
    return findings


def _has_authority_finding(findings: list[dict[str, Any]]) -> bool:
    return any(
        finding.get("finding_id") == "user_idea_interview_authority_expanded"
        for finding in findings
    )


def _entry(label: str, *, kind: str) -> dict[str, str]:
    slug = _slug(label)
    if kind == "constraints":
        return {"id": f"constraint.{slug}", "statement": label}
    if kind == "risks":
        return {"id": f"risk.{slug}", "statement": label}
    if kind == "assumptions":
        return {"id": f"assumption.{slug}", "statement": label}
    if kind == "vocabulary_questions":
        return {"id": f"question.{slug}", "question": label}
    prefix = {
        "actors": "actor",
        "domain_events": "event",
        "commands": "command",
        "policies": "policy",
        "external_systems": "external-system",
    }.get(kind, "entry")
    return {"id": f"{prefix}.{slug}", "name": label}


def _entries(values: list[str], *, kind: str) -> list[dict[str, Any]]:
    return [_entry(value, kind=kind) for value in values if value.strip()]


def _answer_value(answer: dict[str, Any]) -> Any:
    value = answer.get("value")
    if isinstance(value, dict):
        for key in ("refs", "terms", "entries", "items", "values"):
            if key in value:
                return value[key]
        if "text" in value:
            return value["text"]
    return value


def _answer_target_map(clarification_requests: dict[str, Any]) -> dict[str, str]:
    targets: dict[str, str] = {}
    for raw_request in _list(clarification_requests.get("clarification_requests")):
        request = _dict(raw_request)
        request_id = _text(request.get("id"))
        target_ref = _text(request.get("target_ref"))
        if request_id and target_ref:
            targets[request_id] = target_ref
    return targets


def _public_summary_findings(raw_input: dict[str, Any]) -> list[dict[str, Any]]:
    idea = _dict(raw_input.get("idea"))
    workspace = _dict(raw_input.get("workspace"))
    if not _text(idea.get("text")):
        return []
    missing: list[str] = []
    if not _text(idea.get("summary")):
        missing.append("idea.summary")
    if not _text(workspace.get("display_name")):
        missing.append("workspace.display_name")
    if not missing:
        return []
    return [
        _finding(
            finding_id="user_idea_interview_public_summary_missing",
            severity="review_required",
            message=(
                "Real idea intake requires public-safe idea.summary and "
                "workspace.display_name before source generation can proceed."
            ),
            evidence={"missing": missing},
        )
    ]


def _session_input(raw_input: dict[str, Any], *, strip_raw_text: bool) -> dict[str, Any]:
    if not strip_raw_text:
        return raw_input
    safe_input = copy.deepcopy(raw_input)
    idea = _dict(safe_input.get("idea"))
    idea.pop("text", None)
    safe_input["idea"] = idea
    return safe_input


def _apply_value(raw_input: dict[str, Any], *, target_ref: str, value: Any) -> bool:
    if target_ref.startswith("active_frame_hints."):
        field = target_ref.removeprefix("active_frame_hints.")
        if field not in ACTIVE_FRAME_LIST_FIELDS:
            return False
        values = _text_list(value)
        if not values:
            return False
        frame = raw_input.setdefault("active_frame_hints", {})
        if not isinstance(frame, dict):
            raw_input["active_frame_hints"] = {}
            frame = raw_input["active_frame_hints"]
        frame[field] = values
        return True
    if target_ref.startswith("event_storming_hints."):
        category = target_ref.removeprefix("event_storming_hints.")
        if category not in EVENT_STORMING_CATEGORIES:
            return False
        event_storming = raw_input.setdefault("event_storming_hints", {})
        if not isinstance(event_storming, dict):
            raw_input["event_storming_hints"] = {}
            event_storming = raw_input["event_storming_hints"]
        if isinstance(value, list):
            entries = [
                _public_safe(item) for item in value if isinstance(item, dict) or _text(item)
            ]
            if entries and all(isinstance(item, str) for item in entries):
                entries = _entries([str(item) for item in entries], kind=category)
        else:
            entries = _entries(_text_list(value), kind=category)
        if not entries:
            return False
        event_storming[category] = entries
        return True
    return False


def _apply_clarification_answers(
    raw_input: dict[str, Any],
    *,
    clarification_requests: dict[str, Any] | None,
    clarification_answers: dict[str, Any] | None,
) -> tuple[int, int, list[dict[str, Any]]]:
    if clarification_requests is None and clarification_answers is None:
        return 0, 0, []
    findings: list[dict[str, Any]] = []
    if not clarification_requests or not clarification_answers:
        findings.append(
            _finding(
                finding_id="user_idea_interview_clarification_pair_missing",
                severity="review_required",
                message="Clarification answer application requires both requests and answers.",
            )
        )
        return 0, 0, findings
    if clarification_requests.get("contract_ref") != CLARIFICATION_REQUESTS_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="user_idea_interview_clarification_requests_contract_invalid",
                severity="review_required",
                message="Clarification requests contract_ref is unsupported.",
                evidence={"contract_ref": clarification_requests.get("contract_ref")},
            )
        )
    if clarification_answers.get("contract_ref") != CLARIFICATION_ANSWER_SET_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="user_idea_interview_clarification_answers_contract_invalid",
                severity="review_required",
                message="Clarification answer set contract_ref is unsupported.",
                evidence={"contract_ref": clarification_answers.get("contract_ref")},
            )
        )
    if findings:
        return 0, 0, findings
    answer_report = answer_validator.build_idea_to_spec_clarification_answers(
        clarification_requests=clarification_requests,
        answer_set=clarification_answers,
    )
    validation_findings = _list(answer_report.get("findings"))
    if validation_findings:
        return 0, 0, [_public_safe(_dict(finding)) for finding in validation_findings]
    targets = _answer_target_map(clarification_requests)
    applied = 0
    ignored = 0
    for raw_answer in _list(answer_report.get("answers")):
        answer = _dict(raw_answer)
        if _text(answer.get("status")) not in ACCEPTED_ANSWER_STATUSES:
            ignored += 1
            continue
        if _text(answer.get("answer_kind")) not in APPLY_ANSWER_KINDS:
            ignored += 1
            continue
        request_id = _text(answer.get("request_id"))
        target_ref = targets.get(request_id, "")
        if not target_ref:
            ignored += 1
            continue
        if _apply_value(raw_input, target_ref=target_ref, value=_answer_value(answer)):
            applied += 1
        else:
            ignored += 1
    return applied, ignored, findings


def _base_raw_input(
    *,
    base_input: dict[str, Any] | None,
    idea_text: str,
    idea_summary: str,
    candidate_id: str,
    display_name: str,
    public_route: str,
    project: str,
    subsystem: str,
    lifecycle_phase: str,
) -> dict[str, Any]:
    raw_input = dict(_public_safe(base_input or {}))
    raw_input["artifact_kind"] = "user_idea_raw_input"
    raw_input["schema_version"] = SCHEMA_VERSION
    raw_input["contract_ref"] = RAW_INPUT_CONTRACT_REF
    idea = dict(_dict(raw_input.get("idea")))
    if idea_text:
        idea["text"] = idea_text
    if idea_summary:
        idea["summary"] = idea_summary
    raw_input["idea"] = idea
    workspace = dict(_dict(raw_input.get("workspace")))
    if candidate_id:
        workspace["candidate_id"] = candidate_id
    if display_name:
        workspace["display_name"] = display_name
    if public_route:
        workspace["public_route"] = public_route
    raw_input["workspace"] = workspace
    frame = dict(_dict(raw_input.get("active_frame_hints")))
    if project:
        frame["project"] = project
    if subsystem:
        frame["subsystem"] = subsystem
    if lifecycle_phase:
        frame["lifecycle_phase"] = lifecycle_phase
    raw_input["active_frame_hints"] = frame
    raw_input["event_storming_hints"] = dict(_dict(raw_input.get("event_storming_hints")))
    return raw_input


def _extend_list(target: dict[str, Any], key: str, values: list[str]) -> None:
    if not values:
        return
    existing = _text_list(target.get(key))
    target[key] = [*existing, *values]


def build_interview(
    *,
    base_input: dict[str, Any] | None,
    base_input_path: Path | None,
    idea_text: str,
    idea_summary: str,
    candidate_id: str,
    display_name: str,
    public_route: str,
    project: str,
    subsystem: str,
    lifecycle_phase: str,
    ontology_refs: list[str],
    ontology_layer_refs: list[str],
    domain_refs: list[str],
    context_refs: list[str],
    model_applicability_refs: list[str],
    event_entries: dict[str, list[str]],
    clarification_requests: dict[str, Any] | None,
    clarification_requests_path: Path | None,
    clarification_answers: dict[str, Any] | None,
    clarification_answers_path: Path | None,
    raw_output_path: Path,
    session_output_path: Path,
    source_output_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    raw_input = _base_raw_input(
        base_input=base_input,
        idea_text=idea_text,
        idea_summary=idea_summary,
        candidate_id=candidate_id,
        display_name=display_name,
        public_route=public_route,
        project=project,
        subsystem=subsystem,
        lifecycle_phase=lifecycle_phase,
    )
    raw_input["local_only"] = True
    raw_input["raw_text_published"] = False
    frame = _dict(raw_input.get("active_frame_hints"))
    _extend_list(frame, "ontology_refs", ontology_refs)
    _extend_list(frame, "ontology_layer_refs", ontology_layer_refs)
    _extend_list(frame, "domain_refs", domain_refs)
    _extend_list(frame, "context_refs", context_refs)
    _extend_list(frame, "model_applicability_refs", model_applicability_refs)
    event_storming = _dict(raw_input.get("event_storming_hints"))
    for category, values in event_entries.items():
        event_storming.setdefault(category, [])
        if isinstance(event_storming[category], list):
            event_storming[category].extend(_entries(values, kind=category))
    findings = _authority_findings(base_input or {}, source="base_input")
    findings.extend(
        _authority_findings(clarification_answers or {}, source="clarification_answers")
    )
    findings.extend(_public_summary_findings(raw_input))
    applied_answers = 0
    ignored_answers = 0
    answer_findings: list[dict[str, Any]] = []
    if not _has_authority_finding(findings):
        applied_answers, ignored_answers, answer_findings = _apply_clarification_answers(
            raw_input,
            clarification_requests=clarification_requests,
            clarification_answers=clarification_answers,
        )
        findings.extend(answer_findings)
    session, source = session_tool.build_user_idea_intake_session(
        _session_input(raw_input, strip_raw_text=bool(_public_summary_findings(raw_input))),
        source_path=raw_output_path,
        source_output_path=source_output_path,
    )
    if findings:
        review_state = (
            "blocked_authority_boundary"
            if _has_authority_finding(findings)
            else "intake_interview_review_required"
        )
        session["readiness"]["ready"] = False
        session["readiness"]["review_state"] = review_state
        session["readiness"]["blocked_by"] = [
            *session["readiness"].get("blocked_by", []),
            *[finding["finding_id"] for finding in findings],
        ]
        session["findings"] = [*session.get("findings", []), *findings]
        session["summary"]["status"] = review_state
        session["summary"]["finding_count"] = len(session["findings"])
        session["summary"]["source_written"] = False
        session["source_output"] = {
            "artifact_kind": "user_idea_intake_source",
            "contract_ref": session_tool.SOURCE_CONTRACT_REF,
            "path": _relative_ref(source_output_path),
            "written": False,
            "digest": None,
            "reason": "intake_interview_not_trusted",
        }
        source = None
    report_findings = [_public_safe(_dict(finding)) for finding in _list(session.get("findings"))]
    report = {
        "artifact_kind": "user_idea_intake_interview_report",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": REPORT_CONTRACT_REF,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "source_refs": {
            "base_input": _relative_ref(base_input_path),
            "clarification_requests": _relative_ref(clarification_requests_path),
            "clarification_answers": _relative_ref(clarification_answers_path),
        },
        "output_refs": {
            "raw_input": _relative_ref(raw_output_path),
            "intake_session": _relative_ref(session_output_path),
            "intake_source": _relative_ref(source_output_path) if source is not None else None,
        },
        "raw_input": {
            "artifact_kind": "user_idea_raw_input",
            "contract_ref": RAW_INPUT_CONTRACT_REF,
            "digest": _digest(raw_input),
            "local_only": True,
            "raw_text_published": False,
        },
        "clarification_answer_application": {
            "applied_count": applied_answers,
            "ignored_count": ignored_answers,
        },
        "intake_session": {
            "artifact_kind": session.get("artifact_kind"),
            "contract_ref": session.get("contract_ref"),
            "digest": _digest(session),
            "review_state": _dict(session.get("readiness")).get("review_state"),
            "ready": bool(_dict(session.get("readiness")).get("ready")),
            "clarification_question_count": len(_list(session.get("clarification_questions"))),
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_idea_text_published_in_report": False,
            "raw_idea_text_published_in_session": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
            "raw_operator_note_published": False,
        },
        "findings": report_findings,
        "summary": {
            "status": _dict(session.get("summary")).get("status", "unknown"),
            "ready_for_event_storming_intake": bool(_dict(session.get("readiness")).get("ready")),
            "source_written": source is not None,
            "finding_count": len(report_findings),
            "clarification_question_count": len(_list(session.get("clarification_questions"))),
        },
    }
    return raw_input, session, report, source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--idea-text", default="")
    parser.add_argument("--idea-text-file", type=Path, default=None)
    parser.add_argument("--idea-summary", default="")
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--display-name", default="")
    parser.add_argument("--public-route", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--subsystem", default="")
    parser.add_argument("--lifecycle-phase", default="")
    parser.add_argument("--ontology-ref", action="append", default=[])
    parser.add_argument("--ontology-layer-ref", action="append", default=[])
    parser.add_argument("--domain-ref", action="append", default=[])
    parser.add_argument("--context-ref", action="append", default=[])
    parser.add_argument("--model-applicability-ref", action="append", default=[])
    parser.add_argument("--actor", action="append", default=[])
    parser.add_argument("--domain-event", action="append", default=[])
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--policy", action="append", default=[])
    parser.add_argument("--external-system", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--risk", action="append", default=[])
    parser.add_argument("--assumption", action="append", default=[])
    parser.add_argument("--vocabulary-question", action="append", default=[])
    parser.add_argument("--clarification-requests", type=Path, default=None)
    parser.add_argument("--clarification-answers", type=Path, default=None)
    parser.add_argument("--raw-output", type=Path, default=DEFAULT_RAW_OUTPUT_PATH)
    parser.add_argument("--session-output", type=Path, default=DEFAULT_SESSION_OUTPUT_PATH)
    parser.add_argument("--source-output", type=Path, default=DEFAULT_SOURCE_OUTPUT_PATH)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT_PATH)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    idea_text = args.idea_text or os.environ.get(IDEA_TEXT_ENV, "")
    if args.idea_text_file:
        idea_text = args.idea_text_file.read_text(encoding="utf-8").strip()
    base_input = load_json(args.input) if args.input else None
    clarification_requests = (
        load_json(args.clarification_requests) if args.clarification_requests else None
    )
    clarification_answers = (
        load_json(args.clarification_answers) if args.clarification_answers else None
    )
    raw_input, session, report, source = build_interview(
        base_input=base_input,
        base_input_path=args.input,
        idea_text=idea_text,
        idea_summary=args.idea_summary,
        candidate_id=args.candidate_id,
        display_name=args.display_name,
        public_route=args.public_route,
        project=args.project,
        subsystem=args.subsystem,
        lifecycle_phase=args.lifecycle_phase,
        ontology_refs=args.ontology_ref,
        ontology_layer_refs=args.ontology_layer_ref,
        domain_refs=args.domain_ref,
        context_refs=args.context_ref,
        model_applicability_refs=args.model_applicability_ref,
        event_entries={
            "actors": args.actor,
            "domain_events": args.domain_event,
            "commands": args.command,
            "policies": args.policy,
            "external_systems": args.external_system,
            "constraints": args.constraint,
            "risks": args.risk,
            "assumptions": args.assumption,
            "vocabulary_questions": args.vocabulary_question,
        },
        clarification_requests=clarification_requests,
        clarification_requests_path=args.clarification_requests,
        clarification_answers=clarification_answers,
        clarification_answers_path=args.clarification_answers,
        raw_output_path=args.raw_output,
        session_output_path=args.session_output,
        source_output_path=args.source_output,
    )
    write_json(raw_input, args.raw_output)
    write_json(session, args.session_output)
    write_json(report, args.report_output)
    if source is not None:
        write_json(source, args.source_output)
    elif args.source_output.exists():
        args.source_output.unlink()
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('clarification_question_count', 0)} questions -> "
        f"{_relative_ref(args.report_output)}"
    )
    if args.strict and not summary.get("ready_for_event_storming_intake"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
