"""Build a generic user-idea intake session into an intake source."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0162"
SCHEMA_VERSION = 1
RAW_INPUT_CONTRACT_REF = "specgraph.idea-to-spec.user-idea-raw-input.v0.1"
SESSION_CONTRACT_REF = "specgraph.idea-to-spec.user-idea-intake-session.v0.1"
SOURCE_CONTRACT_REF = "specgraph.idea-to-spec.user-idea-intake-source.v0.1"
DEFAULT_INPUT_PATH = (
    ROOT / "tests" / "fixtures" / "user_idea_intake_session" / "raw_idea_ready.json"
)
DEFAULT_SESSION_OUTPUT_PATH = ROOT / "runs" / "user_idea_intake_session.json"
DEFAULT_SOURCE_OUTPUT_PATH = ROOT / "runs" / "user_idea_intake_source.json"

CANDIDATE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
RAW_TRACE_FIELDS = {
    "private_note",
    "raw_intent",
    "raw_intent_text",
    "raw_model_output",
    "raw_operator_note",
    "raw_prompt",
    "raw_response",
}
REQUIRED_EVENT_STORMING_CATEGORIES = (
    "actors",
    "domain_events",
    "commands",
    "constraints",
)
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
CATEGORY_ALIASES = {
    "domain_events": ("events",),
    "external_systems": ("external_dependencies", "systems"),
    "risks": ("open_risks",),
    "assumptions": ("open_assumptions",),
    "vocabulary_questions": ("questions", "vocabulary_gaps"),
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


def _slug(value: str, fallback: str = "idea-candidate") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _slug_to_project_id(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.split("-") if part)


def _slug_to_domain_ref(value: str) -> str:
    return f"domain.{value.replace('-', '_')}"


def _slug_to_context_ref(value: str) -> str:
    return f"context.{value.replace('-', '_')}"


def _relative_ref(path: Path) -> str:
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
        "source": "user_idea_intake_session",
        "evidence": evidence or {},
    }


def _question(
    *,
    question_id: str,
    kind: str,
    question: str,
    blocks: list[str],
) -> dict[str, Any]:
    return {
        "id": question_id,
        "kind": kind,
        "question": question,
        "blocks": blocks,
    }


def _clean_entry(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _clean_entry(item) for key, item in value.items() if key not in RAW_TRACE_FIELDS
        }
    if isinstance(value, list):
        return [_clean_entry(item) for item in value]
    return value


def _input_contract_findings(raw_input: dict[str, Any]) -> list[dict[str, Any]]:
    invalid: list[str] = []
    artifact_kind = raw_input.get("artifact_kind")
    contract_ref = raw_input.get("contract_ref")
    if artifact_kind == "user_idea_intake_source" and contract_ref == SOURCE_CONTRACT_REF:
        return []
    if artifact_kind not in {"user_idea_raw_input", "user_idea_intake_raw_input"}:
        invalid.append("artifact_kind")
    if raw_input.get("schema_version") != SCHEMA_VERSION:
        invalid.append("schema_version")
    if contract_ref != RAW_INPUT_CONTRACT_REF:
        invalid.append("contract_ref")
    if not invalid:
        return []
    return [
        _finding(
            finding_id="user_idea_raw_input_contract_invalid",
            severity="review_required",
            message="User idea intake session requires a valid raw-input contract.",
            evidence={
                "invalid_fields": invalid,
                "expected": {
                    "artifact_kind": "user_idea_raw_input",
                    "schema_version": SCHEMA_VERSION,
                    "contract_ref": RAW_INPUT_CONTRACT_REF,
                },
            },
        )
    ]


def _workspace(
    raw_input: dict[str, Any],
    *,
    intent: dict[str, str],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    workspace = _dict(raw_input.get("workspace")) or _dict(raw_input.get("workspace_hints"))
    candidate = _dict(raw_input.get("candidate"))
    display_name = _text(
        workspace.get("display_name"),
        _text(candidate.get("display_name"), _text(raw_input.get("display_name"))),
    )
    if not display_name:
        display_name = _text(intent.get("summary"), _text(intent.get("text")))
        display_name = display_name.split(".")[0][:64].strip()
    candidate_id_raw = _text(
        workspace.get("candidate_id"),
        _text(candidate.get("candidate_id"), _text(raw_input.get("candidate_id"))),
    )
    candidate_id = candidate_id_raw or _slug(display_name)
    public_route = _text(
        workspace.get("public_route"),
        _text(candidate.get("public_route"), f"/{candidate_id}"),
    )
    findings: list[dict[str, Any]] = []
    if not display_name:
        findings.append(
            _finding(
                finding_id="user_idea_session_display_name_missing",
                severity="review_required",
                message=(
                    "User idea intake session requires a workspace display_name "
                    "or derivable idea summary."
                ),
            )
        )
        display_name = _slug_to_project_id(candidate_id)
    if not CANDIDATE_ID_RE.fullmatch(candidate_id):
        findings.append(
            _finding(
                finding_id="user_idea_session_candidate_id_invalid",
                severity="review_required",
                message="Candidate id must be a stable lowercase slug.",
                evidence={"candidate_id": candidate_id},
            )
        )
    if (
        public_route == "/"
        or not public_route.startswith("/")
        or "//" in public_route
        or "?" in public_route
        or "#" in public_route
    ):
        findings.append(
            _finding(
                finding_id="user_idea_session_public_route_invalid",
                severity="review_required",
                message="Public route must be a non-root absolute path.",
                evidence={"public_route": public_route},
            )
        )
    return {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "public_route": public_route,
    }, findings


def _intent(
    raw_input: dict[str, Any],
    *,
    idea_text: str | None = None,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    idea = _dict(raw_input.get("idea"))
    intent = _dict(raw_input.get("intent"))
    text = _text(
        idea_text,
        _text(
            intent.get("text"),
            _text(
                idea.get("text"),
                _text(raw_input.get("intent_text"), _text(raw_input.get("raw_idea"))),
            ),
        ),
    )
    summary = _text(
        intent.get("summary"),
        _text(idea.get("summary"), _text(raw_input.get("intent_summary"))),
    )
    findings: list[dict[str, Any]] = []
    if not text and not summary:
        findings.append(
            _finding(
                finding_id="user_idea_session_intent_missing",
                severity="review_required",
                message="User idea intake session requires idea text or summary.",
            )
        )
    if not summary and text:
        summary = text.split(".")[0][:180].strip()
    return {"text": text, "summary": summary}, findings


def _frame(
    raw_input: dict[str, Any],
    *,
    workspace: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    frame = _dict(raw_input.get("active_frame_hints")) or _dict(raw_input.get("active_frame"))
    candidate_id = workspace["candidate_id"]
    prepared_source_input = (
        raw_input.get("artifact_kind") == "user_idea_intake_source"
        and raw_input.get("contract_ref") == SOURCE_CONTRACT_REF
    )
    normalized = {
        "project": _text(frame.get("project"), _slug_to_project_id(candidate_id)),
        "subsystem": _text(frame.get("subsystem"), "product_specification"),
        "lifecycle_phase": _text(frame.get("lifecycle_phase"), "idea_intake"),
        "ontology_refs": _text_list(frame.get("ontology_refs")),
        "ontology_layer_refs": _text_list(frame.get("ontology_layer_refs")),
        "domain_refs": _text_list(frame.get("domain_refs")),
        "context_refs": _text_list(frame.get("context_refs")),
        "model_applicability_refs": _text_list(frame.get("model_applicability_refs")),
    }
    findings: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    if prepared_source_input:
        if not normalized["ontology_refs"]:
            normalized["ontology_refs"] = ["ontology://specgraph-core"]
        if not normalized["ontology_layer_refs"]:
            normalized["ontology_layer_refs"] = ["objective", "mechanics"]
        if not normalized["domain_refs"]:
            normalized["domain_refs"] = [_slug_to_domain_ref(candidate_id)]
        if not normalized["context_refs"]:
            normalized["context_refs"] = [
                "context.idea_to_spec",
                _slug_to_context_ref(candidate_id),
            ]
        if not normalized["model_applicability_refs"]:
            normalized["model_applicability_refs"] = [
                "model-applicability://specgraph-core/product-spec-mvp"
            ]
        return normalized, findings, questions
    required = {
        "ontology_refs": "Which ontology package or ontology ref should constrain the first spec?",
        "ontology_layer_refs": (
            "Which ontology layers apply to this idea: objective, mechanics, "
            "governance, evidence, or another layer?"
        ),
        "domain_refs": "Which product domain should bound the language and terms?",
        "context_refs": "Which context should claims and requirements stay within?",
        "model_applicability_refs": (
            "Which model applicability profile should gate the generated candidate graph?"
        ),
    }
    for field, question_text in required.items():
        if normalized[field]:
            continue
        fallback: list[str] = []
        if field == "domain_refs":
            fallback = [_slug_to_domain_ref(candidate_id)]
        elif field == "context_refs":
            fallback = ["context.idea_to_spec", _slug_to_context_ref(candidate_id)]
        normalized[field] = fallback
        findings.append(
            _finding(
                finding_id=f"user_idea_session_{field}_missing",
                severity="review_required",
                message=f"Active frame requires {field}.",
                evidence={"field": field, "default_preview": fallback},
            )
        )
        questions.append(
            _question(
                question_id=f"question.active-frame.{field}",
                kind="active_frame",
                question=question_text,
                blocks=[f"active_frame_hints.{field}"],
            )
        )
    return normalized, findings, questions


def _category_items(event_storming: dict[str, Any], category: str) -> list[Any]:
    if category in event_storming:
        return _list(event_storming.get(category))
    for alias in CATEGORY_ALIASES.get(category, ()):
        if alias in event_storming:
            return _list(event_storming.get(alias))
    return []


def _event_storming(
    raw_input: dict[str, Any],
) -> tuple[dict[str, list[Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    event_storming = _dict(raw_input.get("event_storming_hints")) or _dict(
        raw_input.get("event_storming")
    )
    normalized: dict[str, list[Any]] = {}
    for category in EVENT_STORMING_CATEGORIES:
        normalized[category] = [
            _clean_entry(item) for item in _category_items(event_storming, category)
        ]
    findings: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    question_text = {
        "actors": "Who are the primary actors or roles in this product idea?",
        "domain_events": "Which important domain events should the specification preserve?",
        "commands": "Which user or system commands should trigger those events?",
        "constraints": "Which constraints, policies, or non-goals bound the first candidate graph?",
    }
    for category in REQUIRED_EVENT_STORMING_CATEGORIES:
        if normalized[category]:
            continue
        findings.append(
            _finding(
                finding_id=f"user_idea_session_{category}_missing",
                severity="review_required",
                message=f"Event-storming intake requires {category}.",
                evidence={"category": category},
            )
        )
        questions.append(
            _question(
                question_id=f"question.event-storming.{category}",
                kind="event_storming",
                question=question_text[category],
                blocks=[f"event_storming_hints.{category}"],
            )
        )
    return normalized, findings, questions


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_infer_domain_model": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_accept_ontology_terms": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
    }


def _source_payload(
    *,
    workspace: dict[str, str],
    intent: dict[str, str],
    frame: dict[str, Any],
    event_storming: dict[str, list[Any]],
    source_ref: str,
    source_path: Path | None,
    session_digest: str,
) -> dict[str, Any]:
    return {
        "artifact_kind": "user_idea_intake_source",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": SOURCE_CONTRACT_REF,
        "source_ref": source_ref,
        "workspace": workspace,
        "intent": intent,
        "active_frame_hints": frame,
        "event_storming_hints": event_storming,
        "source_session": {
            "artifact_kind": "user_idea_intake_session",
            "contract_ref": SESSION_CONTRACT_REF,
            "proposal_id": PROPOSAL_ID,
            "source_ref": _relative_ref(source_path) if source_path else "cli:idea-text",
            "session_digest": session_digest,
        },
    }


def build_user_idea_intake_session(
    raw_input: dict[str, Any],
    *,
    source_path: Path | None = None,
    source_output_path: Path | None = None,
    idea_text: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    contract_findings = _input_contract_findings(raw_input)
    intent, intent_findings = _intent(raw_input, idea_text=idea_text)
    workspace, workspace_findings = _workspace(raw_input, intent=intent)
    frame, frame_findings, frame_questions = _frame(raw_input, workspace=workspace)
    event_storming, event_findings, event_questions = _event_storming(raw_input)
    findings = (
        contract_findings + intent_findings + workspace_findings + frame_findings + event_findings
    )
    questions = frame_questions + event_questions
    source_ref = _text(
        raw_input.get("source_ref"),
        f"product://{workspace['candidate_id']}/root-intent",
    )
    ready = not findings
    status = "ready_for_event_storming_intake" if ready else "needs_clarification"
    session = {
        "artifact_kind": "user_idea_intake_session",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": SESSION_CONTRACT_REF,
        "proposal_id": PROPOSAL_ID,
        "source_ref": _relative_ref(source_path) if source_path else "cli:idea-text",
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "workspace": workspace,
        "intent": {
            "summary": intent["summary"],
            "raw_text_digest": hashlib.sha256(intent["text"].encode("utf-8")).hexdigest()
            if intent["text"]
            else None,
            "raw_text_published": False,
        },
        "active_frame_hints": frame,
        "event_storming_summary": {
            f"{category}_count": len(event_storming[category])
            for category in EVENT_STORMING_CATEGORIES
        },
        "clarification_questions": questions,
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_idea_text_published_in_session": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
            "raw_operator_note_published": False,
        },
        "findings": findings,
        "readiness": {
            "ready": ready,
            "review_state": status,
            "blocked_by": [finding["finding_id"] for finding in findings],
        },
        "summary": {
            "status": status,
            "finding_count": len(findings),
            "clarification_question_count": len(questions),
            "source_written": False,
        },
    }
    source: dict[str, Any] | None = None
    if ready:
        session_digest = _digest(session)
        source = _source_payload(
            workspace=workspace,
            intent=intent,
            frame=frame,
            event_storming=event_storming,
            source_ref=source_ref,
            source_path=source_path,
            session_digest=session_digest,
        )
        session["source_output"] = {
            "artifact_kind": "user_idea_intake_source",
            "contract_ref": SOURCE_CONTRACT_REF,
            "path": _relative_ref(source_output_path) if source_output_path else None,
            "digest": _digest(source),
        }
        session["summary"]["source_written"] = source_output_path is not None
    else:
        session["source_output"] = {
            "artifact_kind": "user_idea_intake_source",
            "contract_ref": SOURCE_CONTRACT_REF,
            "path": _relative_ref(source_output_path) if source_output_path else None,
            "written": False,
            "reason": "intake_session_needs_clarification",
        }
    return session, source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None, type=Path)
    parser.add_argument("--idea-text", default=None)
    parser.add_argument("--session-output", default=DEFAULT_SESSION_OUTPUT_PATH, type=Path)
    parser.add_argument("--source-output", default=DEFAULT_SOURCE_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_path: Path | None
    if args.input is not None:
        input_path = args.input
        source_path = input_path
        raw_input = load_json(input_path)
    elif args.idea_text is None:
        input_path = DEFAULT_INPUT_PATH
        source_path = input_path
        raw_input = load_json(input_path)
    else:
        source_path = None
        raw_input = {}
    if args.idea_text is not None:
        raw_input = {
            **raw_input,
            "artifact_kind": raw_input.get("artifact_kind", "user_idea_raw_input"),
            "schema_version": raw_input.get("schema_version", SCHEMA_VERSION),
            "contract_ref": raw_input.get("contract_ref", RAW_INPUT_CONTRACT_REF),
            "idea": {
                **_dict(raw_input.get("idea")),
                "text": args.idea_text,
            },
        }
    session, source = build_user_idea_intake_session(
        raw_input,
        source_path=source_path,
        source_output_path=args.source_output,
        idea_text=args.idea_text,
    )
    write_json(session, args.session_output)
    if source is not None:
        write_json(source, args.source_output)
    summary = _dict(session.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('finding_count', 0)} findings, "
        f"{summary.get('clarification_question_count', 0)} questions -> "
        f"{_relative_ref(args.session_output)}"
    )
    if source is not None:
        print(f"source_written -> {_relative_ref(args.source_output)}")
    if args.strict and not _dict(session.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
