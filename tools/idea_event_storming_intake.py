"""Build a review-only event-storming intake artifact for idea-to-spec flows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0149"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.event-storming-intake.v0.1"
SEED_CONTRACT_REF = "specgraph.idea-to-spec.event-storming-seed.v0.1"
DEFAULT_INPUT_PATH = ROOT / "tests" / "fixtures" / "idea_event_storming_intake" / "idea_ready.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_event_storming_intake.json"

REQUIRED_ACTIVE_FRAME_LIST_FIELDS = (
    "ontology_refs",
    "domain_refs",
    "context_refs",
)
OPTIONAL_ACTIVE_FRAME_LIST_FIELDS = (
    "ontology_layer_refs",
    "model_applicability_refs",
)
ACTIVE_FRAME_TEXT_FIELDS = (
    "project",
    "subsystem",
    "lifecycle_phase",
)
REQUIRED_CATEGORIES = ("actors", "domain_events", "commands", "constraints")
ALL_CATEGORIES = (
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
CATEGORY_LABEL_FIELDS = {
    "actors": ("name",),
    "domain_events": ("name",),
    "commands": ("name",),
    "policies": ("name",),
    "external_systems": ("name",),
    "constraints": ("statement", "name"),
    "risks": ("statement", "name"),
    "assumptions": ("statement", "name"),
    "vocabulary_questions": ("question", "term", "name"),
}
LIST_FIELDS = {
    "ontology_refs",
    "domain_refs",
    "context_refs",
    "actor_refs",
    "produces_event_refs",
    "trigger_event_refs",
    "command_refs",
    "candidate_refs",
    "assumptions",
}
RAW_TRACE_FIELDS = {
    "raw_intent",
    "raw_intent_text",
    "raw_model_output",
    "raw_operator_note",
    "raw_prompt",
    "raw_response",
    "raw_text",
}
PRIVATE_TRACE_FIELDS = RAW_TRACE_FIELDS | {"operator_note", "operator_notes"}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _public_safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _public_safe_value(item)
            for key, item in value.items()
            if isinstance(key, str)
            and key not in PRIVATE_TRACE_FIELDS
            and not key.startswith("raw_")
        }
    if isinstance(value, list):
        return [_public_safe_value(item) for item in value]
    return value


def _public_safe_summary(value: Any) -> dict[str, Any]:
    safe_value = _public_safe_value(_dict(value))
    return safe_value if isinstance(safe_value, dict) else {}


def _text_list(value: Any) -> list[str]:
    return [item.strip() for item in _list(value) if isinstance(item, str) and item.strip()]


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _relative_ref(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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
        "source": "idea_event_storming_intake",
        "evidence": evidence or {},
    }


def _raw_intent(seed: dict[str, Any]) -> dict[str, Any]:
    intent = _dict(seed.get("intent"))
    text = _text(intent.get("text"), _text(seed.get("intent_text")))
    summary = _text(intent.get("summary"), _text(seed.get("intent_summary")))
    source_ref = _text(
        intent.get("source_ref"),
        _text(seed.get("source_ref"), "operator://idea-event-storming-local"),
    )
    digest_source = text or summary or source_ref
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
    return {
        "source_ref": source_ref,
        "text_sha256": digest,
        "summary": summary or "Summary unavailable; see source_ref.",
        "raw_text_published": False,
    }


def _active_frame(seed: dict[str, Any]) -> dict[str, Any]:
    frame = _dict(seed.get("active_frame"))
    normalized: dict[str, Any] = {}
    for field in ACTIVE_FRAME_TEXT_FIELDS:
        value = _text(frame.get(field))
        if value:
            normalized[field] = value
    for field in REQUIRED_ACTIVE_FRAME_LIST_FIELDS + OPTIONAL_ACTIVE_FRAME_LIST_FIELDS:
        normalized[field] = _text_list(frame.get(field))
    return normalized


def _category_items(
    event_storming: dict[str, Any],
    category: str,
) -> tuple[list[Any], dict[str, Any] | None]:
    source_key = ""
    if category in event_storming:
        source_key = category
    else:
        for alias in CATEGORY_ALIASES.get(category, ()):
            if alias in event_storming:
                source_key = alias
                break
    if not source_key:
        return [], None
    raw_items = event_storming.get(source_key)
    if isinstance(raw_items, list):
        return raw_items, None
    if isinstance(raw_items, (dict, str)):
        return [raw_items], None
    return [], _finding(
        finding_id="event_storming_category_malformed",
        severity="review_required",
        message="Event-storming categories must be arrays, objects, or non-empty strings.",
        evidence={
            "category": category,
            "source_key": source_key,
            "value_type": type(raw_items).__name__,
        },
    )


def _normalize_list_field(
    value: Any,
    *,
    category: str,
    entry_id: str,
    field: str,
    index: int,
) -> tuple[list[str], dict[str, Any] | None]:
    if not isinstance(value, list):
        return [], _finding(
            finding_id="event_storming_list_field_malformed",
            severity="review_required",
            message=(
                "Event-storming list-valued relationship fields must be arrays "
                "of non-empty strings."
            ),
            evidence={
                "category": category,
                "entry_id": entry_id,
                "field": field,
                "index": index,
                "value_type": type(value).__name__,
            },
        )
    values = _text_list(value)
    if len(values) != len(value):
        return values, _finding(
            finding_id="event_storming_list_field_malformed",
            severity="review_required",
            message=(
                "Event-storming list-valued relationship fields must be arrays "
                "of non-empty strings."
            ),
            evidence={
                "category": category,
                "entry_id": entry_id,
                "field": field,
                "index": index,
                "value_type": "list",
            },
        )
    return values, None


def _seed_contract_findings(seed: dict[str, Any]) -> list[dict[str, Any]]:
    invalid: list[str] = []
    if seed.get("artifact_kind") != "idea_event_storming_seed":
        invalid.append("artifact_kind")
    if seed.get("schema_version") != SCHEMA_VERSION:
        invalid.append("schema_version")
    if seed.get("contract_ref") != SEED_CONTRACT_REF:
        invalid.append("contract_ref")
    if not invalid:
        return []
    return [
        _finding(
            finding_id="idea_event_storming_seed_contract_invalid",
            severity="review_required",
            message="Idea event-storming intake requires a valid seed contract.",
            evidence={
                "invalid_fields": invalid,
                "expected": {
                    "artifact_kind": "idea_event_storming_seed",
                    "schema_version": SCHEMA_VERSION,
                    "contract_ref": SEED_CONTRACT_REF,
                },
                "actual": {
                    "artifact_kind": seed.get("artifact_kind"),
                    "schema_version": seed.get("schema_version"),
                    "contract_ref": seed.get("contract_ref"),
                },
            },
        )
    ]


def _source_intake_findings(seed: dict[str, Any]) -> list[dict[str, Any]]:
    source_intake = _dict(seed.get("source_intake"))
    source_findings = [
        finding
        for finding in _list(source_intake.get("findings"))
        if isinstance(finding, dict) and finding.get("severity") == "review_required"
    ]
    if not source_findings:
        return []
    return [
        _finding(
            finding_id="source_intake_review_required",
            severity="review_required",
            message="Idea event-storming seed source requires review before intake can proceed.",
            evidence={
                "source_finding_ids": [
                    finding.get("finding_id", "unknown") for finding in source_findings
                ],
                "source_contract_ref": source_intake.get("source_contract_ref"),
            },
        )
    ]


def _label_for_entry(entry: dict[str, Any], category: str) -> str:
    for field in CATEGORY_LABEL_FIELDS[category]:
        value = _text(entry.get(field))
        if value:
            return value
    return ""


def _normalize_entry(
    value: Any, category: str, index: int
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if isinstance(value, str):
        fields = CATEGORY_LABEL_FIELDS[category]
        entry: dict[str, Any] = {fields[0]: value}
    elif isinstance(value, dict):
        entry = dict(value)
    else:
        return None, [
            _finding(
                finding_id="event_storming_entry_invalid",
                severity="review_required",
                message="Event-storming entries must be objects or non-empty strings.",
                evidence={"category": category, "index": index},
            )
        ]

    label = _label_for_entry(entry, category)
    if not label:
        return None, [
            _finding(
                finding_id="event_storming_entry_missing_label",
                severity="review_required",
                message="Event-storming entries require a name, statement, term, or question.",
                evidence={"category": category, "index": index},
            )
        ]

    entry_id = _text(entry.get("id"), f"{category}.{_slug(label, str(index + 1))}")
    normalized: dict[str, Any] = {"id": entry_id}
    findings: list[dict[str, Any]] = []
    for key, item in entry.items():
        if key == "id" or key in RAW_TRACE_FIELDS:
            continue
        if key in LIST_FIELDS:
            normalized[key], finding = _normalize_list_field(
                item,
                category=category,
                entry_id=entry_id,
                field=key,
                index=index,
            )
            if finding:
                findings.append(finding)
        elif isinstance(item, str):
            item_text = item.strip()
            if item_text:
                normalized[key] = item_text
        elif isinstance(item, (bool, int, float)):
            normalized[key] = item
        elif isinstance(item, list):
            normalized[key] = item
        elif isinstance(item, dict):
            normalized[key] = item
    return normalized, findings


def _event_storming(
    seed: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    event_storming = _dict(seed.get("event_storming"))
    findings: list[dict[str, Any]] = []
    normalized: dict[str, list[dict[str, Any]]] = {}
    for category in ALL_CATEGORIES:
        entries: list[dict[str, Any]] = []
        seen_ids: dict[str, int] = {}
        category_items, category_finding = _category_items(event_storming, category)
        if category_finding:
            findings.append(category_finding)
        for index, value in enumerate(category_items):
            entry, entry_findings = _normalize_entry(value, category, index)
            findings.extend(entry_findings)
            if entry:
                entry_id = _text(entry.get("id"))
                if entry_id in seen_ids:
                    findings.append(
                        _finding(
                            finding_id="event_storming_duplicate_id",
                            severity="review_required",
                            message="Event-storming entry ids must be unique within a category.",
                            evidence={
                                "category": category,
                                "entry_id": entry_id,
                                "first_index": seen_ids[entry_id],
                                "duplicate_index": index,
                            },
                        )
                    )
                else:
                    seen_ids[entry_id] = index
                entries.append(entry)
        normalized[category] = entries
        if category in REQUIRED_CATEGORIES and not entries:
            findings.append(
                _finding(
                    finding_id="event_storming_category_missing",
                    severity="review_required",
                    message=f"Event-storming intake requires at least one {category} entry.",
                    evidence={"category": category},
                )
            )
    return normalized, findings


def _unknown_refs(
    *,
    entries: list[dict[str, Any]],
    field: str,
    known: set[str],
    category: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for entry in entries:
        unknown = [ref for ref in _text_list(entry.get(field)) if ref not in known]
        if unknown:
            findings.append(
                _finding(
                    finding_id="event_storming_unknown_ref",
                    severity="review_required",
                    message="Event-storming references must point to known intake entries.",
                    evidence={
                        "category": category,
                        "entry_id": entry.get("id"),
                        "field": field,
                        "unknown_refs": unknown,
                    },
                )
            )
    return findings


def _relationship_findings(event_storming: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    actor_ids = {entry["id"] for entry in event_storming["actors"]}
    event_ids = {entry["id"] for entry in event_storming["domain_events"]}
    command_ids = {entry["id"] for entry in event_storming["commands"]}
    findings: list[dict[str, Any]] = []
    findings.extend(
        _unknown_refs(
            entries=event_storming["domain_events"],
            field="actor_refs",
            known=actor_ids,
            category="domain_events",
        )
    )
    findings.extend(
        _unknown_refs(
            entries=event_storming["commands"],
            field="actor_refs",
            known=actor_ids,
            category="commands",
        )
    )
    findings.extend(
        _unknown_refs(
            entries=event_storming["commands"],
            field="produces_event_refs",
            known=event_ids,
            category="commands",
        )
    )
    findings.extend(
        _unknown_refs(
            entries=event_storming["policies"],
            field="trigger_event_refs",
            known=event_ids,
            category="policies",
        )
    )
    findings.extend(
        _unknown_refs(
            entries=event_storming["policies"],
            field="command_refs",
            known=command_ids,
            category="policies",
        )
    )
    return findings


def _frame_findings(active_frame: dict[str, Any]) -> list[dict[str, Any]]:
    missing: list[str] = []
    for field in ACTIVE_FRAME_TEXT_FIELDS:
        if not _text(active_frame.get(field)):
            missing.append(field)
    for field in REQUIRED_ACTIVE_FRAME_LIST_FIELDS:
        if not _text_list(active_frame.get(field)):
            missing.append(field)
    if not missing:
        return []
    return [
        _finding(
            finding_id="active_frame_incomplete",
            severity="review_required",
            message="Idea-to-spec intake requires ontology/domain/context active frame.",
            evidence={"missing": missing},
        )
    ]


def _intent_findings(seed: dict[str, Any]) -> list[dict[str, Any]]:
    intent = _dict(seed.get("intent"))
    if not _text(intent.get("text"), _text(seed.get("intent_text"))) and not _text(
        intent.get("summary"),
        _text(seed.get("intent_summary")),
    ):
        return [
            _finding(
                finding_id="intent_missing",
                severity="review_required",
                message="Idea event-storming intake requires raw intent text or an intent summary.",
            )
        ]
    if not _text(intent.get("summary"), _text(seed.get("intent_summary"))):
        return [
            _finding(
                finding_id="intent_summary_missing",
                severity="warning",
                message="Intent summary is missing; raw intent text is digested but not published.",
            )
        ]
    return []


def _context_completion_questions(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for finding in findings:
        finding_id = finding.get("finding_id")
        evidence = _dict(finding.get("evidence"))
        if finding_id == "active_frame_incomplete":
            for field in _text_list(evidence.get("missing")):
                questions.append(
                    {
                        "id": f"context-question.{field}",
                        "kind": "active_frame",
                        "question": f"Which {field} should bind this idea-to-spec intake?",
                        "blocks_candidate_graph": True,
                    }
                )
        if finding_id == "event_storming_category_missing":
            category = _text(evidence.get("category"))
            if category:
                questions.append(
                    {
                        "id": f"context-question.{category}",
                        "kind": "event_storming_category",
                        "question": f"Which {category} are known for this product idea?",
                        "blocks_candidate_graph": True,
                    }
                )
    return questions


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
    }


def _source_intake(seed: dict[str, Any]) -> dict[str, Any] | None:
    raw_source_intake = seed.get("source_intake")
    if not isinstance(raw_source_intake, dict):
        return None
    source_intake = _dict(raw_source_intake)
    workspace = _dict(source_intake.get("workspace"))
    return {
        "artifact_kind": source_intake.get("artifact_kind"),
        "contract_ref": source_intake.get("contract_ref"),
        "source_contract_ref": source_intake.get("source_contract_ref"),
        "source_ref": source_intake.get("source_ref"),
        "workspace": {
            "candidate_id": _text(workspace.get("candidate_id")),
            "display_name": _text(workspace.get("display_name")),
            "public_route": _text(workspace.get("public_route")),
        },
        "summary": _public_safe_summary(source_intake.get("summary")),
    }


def build_idea_event_storming_intake(
    seed: dict[str, Any],
    *,
    source_path: Path | None = None,
) -> dict[str, Any]:
    active_frame = _active_frame(seed)
    event_storming, event_findings = _event_storming(seed)
    findings = (
        _seed_contract_findings(seed)
        + _source_intake_findings(seed)
        + _intent_findings(seed)
        + _frame_findings(active_frame)
        + event_findings
        + _relationship_findings(event_storming)
    )
    blocking_findings = [
        finding for finding in findings if finding.get("severity") == "review_required"
    ]
    warnings = [finding for finding in findings if finding.get("severity") == "warning"]
    ok = not blocking_findings
    source_ref = _text(seed.get("source_ref"))
    if not source_ref and source_path is not None:
        source_ref = _relative_ref(source_path)
    source_intake = _source_intake(seed)
    intake = {
        "artifact_kind": "idea_event_storming_intake",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "seed_contract_ref": _text(seed.get("contract_ref"), SEED_CONTRACT_REF),
        "source_ref": source_ref or "operator://idea-event-storming-local",
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "root_intent": _raw_intent(seed),
        "active_frame": active_frame,
        "event_storming": event_storming,
        "context_completion_questions": _context_completion_questions(blocking_findings),
        "candidate_graph_readiness": {
            "ready": ok,
            "review_state": "ready_for_candidate_graph" if ok else "context_completion_required",
            "next_artifact": "runs/candidate_spec_graph.json",
            "blocked_by": [finding["finding_id"] for finding in blocking_findings],
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_intent_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
        },
        "findings": blocking_findings,
        "warnings": warnings,
        "summary": {
            "status": "ready_for_candidate_graph" if ok else "context_completion_required",
            "actor_count": len(event_storming["actors"]),
            "domain_event_count": len(event_storming["domain_events"]),
            "command_count": len(event_storming["commands"]),
            "policy_count": len(event_storming["policies"]),
            "external_system_count": len(event_storming["external_systems"]),
            "constraint_count": len(event_storming["constraints"]),
            "risk_count": len(event_storming["risks"]),
            "assumption_count": len(event_storming["assumptions"]),
            "vocabulary_question_count": len(event_storming["vocabulary_questions"]),
            "finding_count": len(blocking_findings),
            "warning_count": len(warnings),
        },
    }
    if source_intake is not None:
        intake["source_intake"] = source_intake
    return intake


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    seed = load_json(args.input)
    intake = build_idea_event_storming_intake(seed, source_path=args.input)
    write_json(intake, args.output)
    print(json.dumps(intake, indent=2, sort_keys=True))
    if args.strict and not intake["candidate_graph_readiness"]["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
