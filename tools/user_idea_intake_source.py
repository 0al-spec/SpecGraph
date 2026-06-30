"""Build a generic user-idea source into an event-storming seed."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0158"
SCHEMA_VERSION = 1
SOURCE_CONTRACT_REF = "specgraph.idea-to-spec.user-idea-intake-source.v0.1"
SEED_CONTRACT_REF = "specgraph.idea-to-spec.event-storming-seed.v0.1"
DEFAULT_INPUT_PATH = ROOT / "tests" / "fixtures" / "user_idea_intake" / "source_ready.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_event_storming_seed.json"

CANDIDATE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
RAW_TRACE_FIELDS = {
    "raw_intent",
    "raw_intent_text",
    "raw_model_output",
    "raw_operator_note",
    "raw_prompt",
    "raw_response",
    "raw_text",
}
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


def _append_unique(items: list[str], value: str) -> list[str]:
    if value and value not in items:
        return [*items, value]
    return items


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
        "source": "user_idea_intake_source",
        "evidence": evidence or {},
    }


def _source_contract_findings(source: dict[str, Any]) -> list[dict[str, Any]]:
    invalid: list[str] = []
    if source.get("artifact_kind") != "user_idea_intake_source":
        invalid.append("artifact_kind")
    if source.get("schema_version") != SCHEMA_VERSION:
        invalid.append("schema_version")
    if source.get("contract_ref") != SOURCE_CONTRACT_REF:
        invalid.append("contract_ref")
    if not invalid:
        return []
    return [
        _finding(
            finding_id="user_idea_source_contract_invalid",
            severity="review_required",
            message="User idea intake source requires a valid source contract.",
            evidence={
                "invalid_fields": invalid,
                "expected": {
                    "artifact_kind": "user_idea_intake_source",
                    "schema_version": SCHEMA_VERSION,
                    "contract_ref": SOURCE_CONTRACT_REF,
                },
            },
        )
    ]


def _workspace(source: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    workspace = _dict(source.get("workspace"))
    candidate = _dict(source.get("candidate"))
    display_name = _text(
        workspace.get("display_name"),
        _text(candidate.get("display_name"), _text(source.get("display_name"))),
    )
    candidate_id_raw = _text(
        workspace.get("candidate_id"),
        _text(candidate.get("candidate_id"), _text(source.get("candidate_id"))),
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
                finding_id="user_idea_display_name_missing",
                severity="review_required",
                message="User idea intake source requires a workspace display_name.",
            )
        )
        display_name = _slug_to_project_id(candidate_id)
    if not CANDIDATE_ID_RE.fullmatch(candidate_id):
        findings.append(
            _finding(
                finding_id="user_idea_candidate_id_invalid",
                severity="review_required",
                message="User idea intake source candidate_id must be a stable lowercase slug.",
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
                finding_id="user_idea_public_route_invalid",
                severity="review_required",
                message="User idea intake source public_route must be a non-root absolute path.",
                evidence={"public_route": public_route},
            )
        )
    return {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "public_route": public_route,
    }, findings


def _intent(source: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    intent = _dict(source.get("intent"))
    text = _text(intent.get("text"), _text(source.get("intent_text")))
    summary = _text(intent.get("summary"), _text(source.get("intent_summary")))
    findings: list[dict[str, Any]] = []
    if not text and not summary:
        findings.append(
            _finding(
                finding_id="user_idea_intent_missing",
                severity="review_required",
                message="User idea intake source requires intent text or summary.",
            )
        )
    return {"text": text, "summary": summary}, findings


def _frame(
    source: dict[str, Any],
    *,
    workspace: dict[str, str],
) -> dict[str, Any]:
    frame = _dict(source.get("active_frame_hints")) or _dict(source.get("active_frame"))
    candidate_id = workspace["candidate_id"]
    context_refs = _text_list(frame.get("context_refs"))
    if not context_refs:
        context_refs = ["context.idea_to_spec", _slug_to_context_ref(candidate_id)]
    domain_refs = _text_list(frame.get("domain_refs")) or [_slug_to_domain_ref(candidate_id)]
    domain_refs = _append_unique(domain_refs, _slug_to_domain_ref(candidate_id))
    return {
        "project": _text(frame.get("project"), _slug_to_project_id(candidate_id)),
        "subsystem": _text(frame.get("subsystem"), "product_specification"),
        "lifecycle_phase": _text(frame.get("lifecycle_phase"), "idea_intake"),
        "ontology_refs": _text_list(frame.get("ontology_refs")) or ["ontology://specgraph-core"],
        "ontology_layer_refs": _text_list(frame.get("ontology_layer_refs"))
        or ["objective", "mechanics"],
        "domain_refs": domain_refs,
        "context_refs": context_refs,
        "model_applicability_refs": _text_list(frame.get("model_applicability_refs"))
        or ["model-applicability://specgraph-core/product-spec-mvp"],
    }


def _clean_entry(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _clean_entry(item) for key, item in value.items() if key not in RAW_TRACE_FIELDS
        }
    if isinstance(value, list):
        return [_clean_entry(item) for item in value]
    return value


def _category_items(event_storming: dict[str, Any], category: str) -> list[Any]:
    if category in event_storming:
        return _list(event_storming.get(category))
    for alias in CATEGORY_ALIASES.get(category, ()):
        if alias in event_storming:
            return _list(event_storming.get(alias))
    return []


def _event_storming(source: dict[str, Any]) -> dict[str, list[Any]]:
    event_storming = _dict(source.get("event_storming_hints")) or _dict(
        source.get("event_storming")
    )
    normalized: dict[str, list[Any]] = {}
    for category in EVENT_STORMING_CATEGORIES:
        normalized[category] = [
            _clean_entry(item) for item in _category_items(event_storming, category)
        ]
    if not normalized["constraints"]:
        normalized["constraints"] = [
            {
                "id": "constraint.pre-canonical-review-boundary",
                "kind": "process",
                "statement": (
                    "The idea-to-spec intake remains pre-canonical until candidate "
                    "graph validation and approval gates pass."
                ),
            }
        ]
    return normalized


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_infer_domain_model": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_create_branch_or_commit": False,
    }


def build_user_idea_event_storming_seed(
    source: dict[str, Any],
    *,
    source_path: Path | None = None,
) -> dict[str, Any]:
    workspace, workspace_findings = _workspace(source)
    intent, intent_findings = _intent(source)
    findings = _source_contract_findings(source) + workspace_findings + intent_findings
    source_ref = _text(
        source.get("source_ref"),
        f"product://{workspace['candidate_id']}/root-intent",
    )
    seed = {
        "artifact_kind": "idea_event_storming_seed",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": SEED_CONTRACT_REF,
        "source_ref": source_ref,
        "intent": intent,
        "active_frame": _frame(source, workspace=workspace),
        "event_storming": _event_storming(source),
        "source_intake": {
            "artifact_kind": source.get("artifact_kind"),
            "contract_ref": source.get("contract_ref"),
            "proposal_id": PROPOSAL_ID,
            "source_contract_ref": SOURCE_CONTRACT_REF,
            "source_ref": _relative_ref(source_path) if source_path else None,
            "generated_at": _now_iso(),
            "workspace": workspace,
            "authority_boundary": _authority_boundary(),
            "privacy_boundary": {
                "raw_intent_text_published": False,
                "raw_prompt_published": False,
                "raw_model_output_published": False,
                "raw_operator_note_published": False,
            },
            "findings": findings,
            "summary": {
                "status": (
                    "ready_for_event_storming_intake" if not findings else "source_review_required"
                ),
                "finding_count": len(findings),
            },
        },
    }
    return seed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = load_json(args.input)
    seed = build_user_idea_event_storming_seed(source, source_path=args.input)
    write_json(seed, args.output)
    summary = _dict(_dict(seed.get("source_intake")).get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('finding_count', 0)} findings -> {_relative_ref(args.output)}"
    )
    if args.strict and summary.get("finding_count", 0) != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
