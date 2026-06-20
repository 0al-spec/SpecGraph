#!/usr/bin/env python3
"""Build a read-only owner-decision import v2 review surface."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ontology_gap_review_workflow import DEFAULT_OUTPUT_PATH as DEFAULT_GAP_REVIEW_PATH
from ontology_gap_review_workflow import build_gap_review_workflow
from ontology_imports import ROOT, relative_path, write_json
from spec_ontology_validation_report import DEFAULT_OUTPUT_PATH as DEFAULT_VALIDATION_REPORT_PATH
from spec_ontology_validation_report import build_validation_report

PROPOSAL_ID = "0139"
SCHEMA_VERSION = 1
DEFAULT_OUTPUT_PATH = ROOT / "runs/ontology_owner_decision_import_v2.json"
DEFAULT_DECISION_IMPORT_PREVIEW_PATH = ROOT / "runs/ontology_decision_import_preview.json"
DEFAULT_CLOSED_LOOP_EVIDENCE_PATH = ROOT / "runs/ontology_closed_loop_evidence.json"
DEFAULT_WRITE_GATE_REPORT_PATH = ROOT / "runs/specauthor_ontology_write_gate_report.json"
TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) and value.strip() else default


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


def _slug(value: str) -> str:
    return TOKEN_RE.sub("-", value.casefold()).strip("-") or "item"


def _key(value: Any) -> str:
    return _text(value).casefold()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _path_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return relative_path(path)
    except ValueError:
        return path.as_posix()


def _source_artifact_ref(payload: dict[str, Any], fallback_path: Path | None) -> str:
    output_artifact = _text(payload.get("output_artifact"))
    if output_artifact:
        return output_artifact
    path_ref = _path_ref(fallback_path)
    if path_ref:
        return path_ref
    return _text(payload.get("artifact_kind"), "not_configured")


def _load_optional_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return load_json(path)


def _decision_previews(decision_import_preview: dict[str, Any]) -> list[dict[str, Any]]:
    if decision_import_preview.get("artifact_kind") != "ontology_decision_import_preview":
        return []
    return [
        entry
        for entry in _list(decision_import_preview.get("decision_import_previews"))
        if isinstance(entry, dict)
    ]


def _closed_loop_entries(*sources: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    for source in sources:
        for collection_name in ("evidence_entries", "closed_loop_entries"):
            for raw_entry in _list(source.get(collection_name)):
                entry = _dict(raw_entry)
                candidate_id = _text(entry.get("candidate_id"))
                intake_id = _text(entry.get("intake_id"))
                if candidate_id and intake_id:
                    entries[(candidate_id, intake_id)] = entry
    return entries


def _index_validation_findings(validation_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    findings: dict[str, dict[str, Any]] = {}
    for raw_entry in _list(validation_report.get("entries")):
        entry = _dict(raw_entry)
        spec_id = _text(entry.get("spec_id"))
        path = _text(entry.get("path"))
        for raw_finding in _list(entry.get("findings")):
            finding = _dict(raw_finding)
            finding_id = _text(finding.get("finding_id"))
            if not finding_id:
                continue
            findings[finding_id] = {
                "finding_id": finding_id,
                "spec_id": spec_id,
                "path": path,
                "classification": finding.get("classification"),
                "severity": finding.get("severity"),
                "term": finding.get("term"),
                "relation_ref": finding.get("relation_ref"),
                "gap_ref": finding.get("gap_ref"),
                "suggested_action": finding.get("suggested_action"),
            }
    return findings


def _index_gap_groups(
    gap_review_workflow: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    groups = [
        group for group in _list(gap_review_workflow.get("gap_groups")) if isinstance(group, dict)
    ]
    index: dict[str, list[dict[str, Any]]] = {}

    def add(alias: Any, group: dict[str, Any]) -> None:
        key = _key(alias)
        if not key:
            return
        index.setdefault(key, [])
        if not any(existing.get("group_id") == group.get("group_id") for existing in index[key]):
            index[key].append(group)

    for group in groups:
        add(group.get("group_id"), group)
        add(group.get("proposed_term"), group)
        add(group.get("proposed_relation"), group)
        add(group.get("missing_ref"), group)
        for raw_gap in _list(group.get("source_gap_refs")):
            add(_dict(raw_gap).get("gap_ref"), group)
        for raw_finding in _list(group.get("source_findings")):
            add(_dict(raw_finding).get("finding_id"), group)
    return groups, index


def _match_gap_groups(
    preview: dict[str, Any],
    evidence_entry: dict[str, Any],
    gap_index: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    aliases: list[Any] = [
        evidence_entry.get("term"),
        preview.get("proposed_term"),
        preview.get("proposed_relation"),
        preview.get("missing_ref"),
        preview.get("matched_gap_group_id"),
        preview.get("matched_closed_loop_evidence_id"),
    ]
    aliases.extend(_list(evidence_entry.get("blocking_item_ids")))
    aliases.extend(_list(preview.get("source_gap_refs")))

    matches: list[dict[str, Any]] = []
    for alias in aliases:
        for group in gap_index.get(_key(alias), []):
            if not any(existing.get("group_id") == group.get("group_id") for existing in matches):
                matches.append(group)
    return matches


def _source_specs(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    specs: list[dict[str, Any]] = []
    for group in groups:
        for raw_spec in _list(group.get("source_specs")):
            spec = _dict(raw_spec)
            item = {
                "spec_id": spec.get("spec_id"),
                "path": spec.get("path"),
                "finding_id": spec.get("finding_id"),
                "classification": spec.get("classification"),
            }
            key = (
                _text(item.get("spec_id")),
                _text(item.get("path")),
                _text(item.get("finding_id")),
            )
            if key not in seen:
                seen.add(key)
                specs.append(item)
    return specs


def _generated_artifacts(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    artifacts: list[dict[str, Any]] = []
    for group in groups:
        for raw_artifact in _list(group.get("affected_generated_artifacts")):
            artifact = _dict(raw_artifact)
            item = {
                "source_ref": artifact.get("source_ref"),
                "path": artifact.get("path"),
                "artifact_kind": artifact.get("artifact_kind"),
                "target_artifact_kind": artifact.get("target_artifact_kind"),
                "target_artifact_title": artifact.get("target_artifact_title"),
                "gap_status": artifact.get("gap_status"),
            }
            key = (_text(item.get("source_ref")), _text(item.get("path")))
            if key not in seen:
                seen.add(key)
                artifacts.append(item)
    return artifacts


def _gap_refs(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    refs: list[dict[str, Any]] = []
    for group in groups:
        for raw_ref in _list(group.get("source_gap_refs")):
            ref = _dict(raw_ref)
            item = {
                "gap_ref": ref.get("gap_ref"),
                "source_artifact": ref.get("source_artifact"),
            }
            key = (_text(item.get("gap_ref")), _text(item.get("source_artifact")))
            if key not in seen:
                seen.add(key)
                refs.append(item)
    return refs


def _compliance_findings(
    groups: list[dict[str, Any]],
    validation_findings: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    findings: list[dict[str, Any]] = []
    for group in groups:
        for raw_finding in _list(group.get("source_findings")):
            finding = _dict(raw_finding)
            finding_id = _text(finding.get("finding_id"))
            if not finding_id or finding_id in seen:
                continue
            seen.add(finding_id)
            findings.append(
                validation_findings.get(
                    finding_id,
                    {
                        "finding_id": finding_id,
                        "classification": finding.get("classification"),
                        "severity": finding.get("severity"),
                        "suggested_action": finding.get("suggested_action"),
                    },
                )
            )
    return findings


def _write_gate_findings(
    groups: list[dict[str, Any]],
    write_gate_reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    generated_refs = {
        _text(artifact.get("source_ref"))
        for artifact in _generated_artifacts(groups)
        if _text(artifact.get("source_ref"))
    }
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for report in write_gate_reports:
        if report.get("artifact_kind") != "specauthor_ontology_write_gate_report":
            continue
        report_source = _text(_dict(report.get("source_artifact")).get("source_ref"))
        for raw_finding in _list(report.get("findings")):
            finding = _dict(raw_finding)
            source_ref = _text(finding.get("source_ref"), report_source)
            if generated_refs and source_ref not in generated_refs:
                continue
            item = {
                "finding_id": finding.get("finding_id"),
                "severity": finding.get("severity"),
                "message": finding.get("message"),
                "source_ref": source_ref,
            }
            key = (_text(item.get("finding_id")), source_ref)
            if key not in seen:
                seen.add(key)
                findings.append(item)
    return findings


def _after_semantic_status(preview: dict[str, Any], matched_groups: list[dict[str, Any]]) -> str:
    decision_state = _text(preview.get("decision_state"))
    preview_state = _text(preview.get("preview_state"))
    if preview_state == "unmatched_decision":
        return "owner_decision_without_matching_evidence"
    if not matched_groups:
        return "owner_decision_without_gap_review_match"
    if decision_state == "accepted" and _bool(preview.get("import_recommended")):
        return "owner_accepted_pending_operator_import"
    if decision_state == "accepted":
        return "owner_accepted_pending_blocker_resolution"
    if decision_state == "rejected":
        return "owner_rejected_no_import"
    if decision_state == "needs_clarification":
        return "owner_clarification_requested"
    return "owner_decision_pending_review"


def _required_operator_action(after_status: str, preview: dict[str, Any]) -> str:
    if after_status == "owner_accepted_pending_operator_import":
        return "inspect_and_acknowledge_owner_acceptance"
    if after_status == "owner_rejected_no_import":
        return "inspect_and_acknowledge_owner_rejection"
    if after_status == "owner_clarification_requested":
        return "request_owner_clarification"
    if after_status.endswith("without_gap_review_match"):
        return "review_unmatched_owner_decision"
    return _text(preview.get("required_human_action"), "operator_review_owner_decision")


def _public_decision_fields(preview: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_id": preview.get("decision_id"),
        "candidate_id": preview.get("candidate_id"),
        "intake_id": preview.get("intake_id"),
        "decision_state": preview.get("decision_state"),
        "preview_state": preview.get("preview_state"),
        "ontology_decision_ref": preview.get("ontology_decision_ref"),
        "decided_at": preview.get("decided_at"),
        "import_recommended": _bool(preview.get("import_recommended")),
    }


def build_owner_decision_import_v2(
    *,
    decision_import_preview: dict[str, Any] | None = None,
    closed_loop_evidence: dict[str, Any] | None = None,
    review_dashboard: dict[str, Any] | None = None,
    gap_review_workflow: dict[str, Any] | None = None,
    validation_report: dict[str, Any] | None = None,
    write_gate_reports: list[dict[str, Any]] | None = None,
    source_paths: dict[str, Path | None] | None = None,
) -> dict[str, Any]:
    decision_import_preview = decision_import_preview or {}
    closed_loop_evidence = closed_loop_evidence or {}
    review_dashboard = review_dashboard or {}
    gap_review_workflow = gap_review_workflow or build_gap_review_workflow()
    validation_report = validation_report or build_validation_report()
    write_gate_reports = write_gate_reports or []
    source_paths = source_paths or {}

    gap_groups, gap_index = _index_gap_groups(gap_review_workflow)
    closed_loop_by_key = _closed_loop_entries(closed_loop_evidence, review_dashboard)
    validation_findings = _index_validation_findings(validation_report)

    reviews: list[dict[str, Any]] = []
    matched_group_ids: set[str] = set()
    for preview in _decision_previews(decision_import_preview):
        candidate_id = _text(preview.get("candidate_id"))
        intake_id = _text(preview.get("intake_id"))
        evidence_entry = closed_loop_by_key.get((candidate_id, intake_id), {})
        matched_groups = _match_gap_groups(preview, evidence_entry, gap_index)
        matched_group_ids.update(
            _text(group.get("group_id")) for group in matched_groups if _text(group.get("group_id"))
        )
        source_specs = _source_specs(matched_groups)
        generated_artifacts = _generated_artifacts(matched_groups)
        gap_refs = _gap_refs(matched_groups)
        compliance_findings = _compliance_findings(matched_groups, validation_findings)
        write_gate_findings = _write_gate_findings(matched_groups, write_gate_reports)
        after_status = _after_semantic_status(preview, matched_groups)
        review_id = (
            "ontology-owner-decision-import-v2-"
            f"{_slug(_text(preview.get('decision_id'), candidate_id))}"
        )
        reviews.append(
            {
                "review_id": review_id,
                **_public_decision_fields(preview),
                "matched_closed_loop_evidence": {
                    "evidence_id": evidence_entry.get("evidence_id"),
                    "term": evidence_entry.get("term"),
                    "source_intake_state": evidence_entry.get("source_intake_state"),
                    "evidence_state": evidence_entry.get("evidence_state"),
                    "required_human_action": evidence_entry.get("required_human_action"),
                },
                "matched_gap_groups": [
                    {
                        "group_id": group.get("group_id"),
                        "gap_kind": group.get("gap_kind"),
                        "proposed_term": group.get("proposed_term"),
                        "proposed_relation": group.get("proposed_relation"),
                        "missing_ref": group.get("missing_ref"),
                        "review_state": group.get("review_state"),
                        "recommended_owner_action": group.get("recommended_owner_action"),
                        "recommended_route": group.get("recommended_route"),
                    }
                    for group in matched_groups
                ],
                "affected_review_items": {
                    "source_specs": source_specs,
                    "affected_generated_artifacts": generated_artifacts,
                    "source_gap_refs": gap_refs,
                },
                "linked_evidence_refs": [
                    ref
                    for ref in [
                        evidence_entry.get("evidence_id"),
                        preview.get("matched_closed_loop_evidence_id"),
                        preview.get("ontology_decision_ref"),
                    ]
                    if _text(ref)
                ],
                "compliance_findings": compliance_findings,
                "write_gate_findings": write_gate_findings,
                "before_semantic_status": {
                    "gap_review_state": "needs_owner_review" if matched_groups else "unmatched",
                    "closed_loop_evidence_state": evidence_entry.get("evidence_state"),
                    "decision_preview_state": preview.get("preview_state"),
                    "compliance_finding_count": len(compliance_findings),
                    "write_gate_finding_count": len(write_gate_findings),
                },
                "after_semantic_status": {
                    "status": after_status,
                    "import_recommended": _bool(preview.get("import_recommended")),
                    "canonical_mutations_allowed": False,
                    "writes_ontology_package": False,
                    "updates_ontology_lockfile": False,
                    "mutates_canonical_specs": False,
                    "closes_semantic_gate": False,
                },
                "required_operator_action": _required_operator_action(after_status, preview),
            }
        )

    accepted_count = sum(1 for review in reviews if review["decision_state"] == "accepted")
    rejected_count = sum(1 for review in reviews if review["decision_state"] == "rejected")
    clarification_count = sum(
        1 for review in reviews if review["decision_state"] == "needs_clarification"
    )
    importable_count = sum(1 for review in reviews if review["import_recommended"])
    unmatched_decision_count = sum(
        1
        for review in reviews
        if review["after_semantic_status"]["status"]
        in {
            "owner_decision_without_matching_evidence",
            "owner_decision_without_gap_review_match",
        }
    )
    unresolved_gap_group_count = len(
        [
            group
            for group in gap_groups
            if _text(group.get("group_id"))
            and _text(group.get("group_id")) not in matched_group_ids
        ]
    )
    if not reviews:
        status = "no_decisions"
        next_gap = "collect_ontology_owner_decisions"
    elif unmatched_decision_count:
        status = "unmatched_decisions"
        next_gap = "review_unmatched_owner_decisions"
    elif clarification_count:
        status = "needs_clarification"
        next_gap = "request_owner_clarification"
    elif importable_count:
        status = "ready_for_operator_ack"
        next_gap = "operator_acknowledge_owner_decisions"
    elif rejected_count and rejected_count == len(reviews):
        status = "owner_rejections_ready_for_ack"
        next_gap = "acknowledge_owner_rejections"
    else:
        status = "owner_decisions_review_required"
        next_gap = "review_owner_decision_status"

    return {
        "artifact_kind": "ontology_owner_decision_import_v2",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "status": status,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "ontology_decision_import_preview": _source_artifact_ref(
                decision_import_preview,
                source_paths.get("decision_import_preview"),
            ),
            "ontology_closed_loop_evidence": _source_artifact_ref(
                closed_loop_evidence,
                source_paths.get("closed_loop_evidence"),
            ),
            "ontology_review_dashboard": _source_artifact_ref(
                review_dashboard,
                source_paths.get("review_dashboard"),
            )
            if review_dashboard
            else "not_configured",
            "ontology_gap_review_workflow": _source_artifact_ref(
                gap_review_workflow,
                source_paths.get("gap_review_workflow"),
            ),
            "spec_ontology_validation_report": _source_artifact_ref(
                validation_report,
                source_paths.get("validation_report"),
            ),
            "specauthor_ontology_write_gate_reports": [
                _source_artifact_ref(report, None) for report in write_gate_reports
            ],
        },
        "summary": {
            "status": status,
            "review_count": len(reviews),
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "clarification_count": clarification_count,
            "importable_count": importable_count,
            "unmatched_decision_count": unmatched_decision_count,
            "matched_gap_group_count": len(matched_group_ids),
            "unresolved_gap_group_count": unresolved_gap_group_count,
            "compliance_finding_count": sum(
                len(review["compliance_findings"]) for review in reviews
            ),
            "write_gate_finding_count": sum(
                len(review["write_gate_findings"]) for review in reviews
            ),
            "next_gap": next_gap,
        },
        "decision_import_reviews": reviews,
        "unresolved_gap_group_count": unresolved_gap_group_count,
        "operator_actions": [
            {
                "action": "inspect_owner_decision_import_review",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            },
            {
                "action": "acknowledge_owner_decision_status",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            },
        ],
        "authority_boundary": {
            "owner_decision_import_v2_is_authority": False,
            "may_execute_prompt_agent": False,
            "may_write_ontology_package": False,
            "may_write_ontology_lockfile": False,
            "may_mutate_canonical_specs": False,
            "may_mark_candidate_accepted": False,
            "may_import_owner_decision": False,
            "may_close_semantic_gate": False,
        },
    }


def require_owner_decision_import_v2(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("artifact_kind") != "ontology_owner_decision_import_v2":
        raise ValueError("report.artifact_kind must be ontology_owner_decision_import_v2")
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"report.schema_version must be {SCHEMA_VERSION}")
    if report.get("proposal_id") != PROPOSAL_ID:
        raise ValueError(f"report.proposal_id must be {PROPOSAL_ID}")
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if report.get(field) is not False:
            raise ValueError(f"report.{field} must be false")
    reviews = report.get("decision_import_reviews")
    if not isinstance(reviews, list):
        raise ValueError("report.decision_import_reviews must be a list")
    for index, raw_review in enumerate(reviews):
        review = _dict(raw_review)
        context = f"report.decision_import_reviews[{index}]"
        if not _text(review.get("review_id")):
            raise ValueError(f"{context}.review_id must be present")
        after_status = _dict(review.get("after_semantic_status"))
        for field in (
            "canonical_mutations_allowed",
            "writes_ontology_package",
            "updates_ontology_lockfile",
            "mutates_canonical_specs",
            "closes_semantic_gate",
        ):
            if after_status.get(field) is not False:
                raise ValueError(f"{context}.after_semantic_status.{field} must be false")
        if "decided_by" in review or "reason" in review:
            raise ValueError(f"{context} must not publish raw owner identity or reason text")
    authority_boundary = _dict(report.get("authority_boundary"))
    for field in (
        "owner_decision_import_v2_is_authority",
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_write_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_import_owner_decision",
        "may_close_semantic_gate",
    ):
        if authority_boundary.get(field) is not False:
            raise ValueError(f"report.authority_boundary.{field} must be false")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-import-preview", type=Path)
    parser.add_argument("--closed-loop-evidence", type=Path)
    parser.add_argument("--review-dashboard", type=Path)
    parser.add_argument("--gap-review-workflow", type=Path)
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--write-gate-report", action="append", default=[], type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def _resolve(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else ROOT / path


def _load_write_gate_report(path: Path) -> dict[str, Any]:
    report = load_json(path)
    report.setdefault("output_artifact", _path_ref(path))
    return report


def main() -> int:
    args = parse_args()
    decision_import_path = (
        _resolve(args.decision_import_preview) or DEFAULT_DECISION_IMPORT_PREVIEW_PATH
    )
    closed_loop_path = _resolve(args.closed_loop_evidence) or DEFAULT_CLOSED_LOOP_EVIDENCE_PATH
    review_dashboard_path = _resolve(args.review_dashboard)
    gap_review_path = _resolve(args.gap_review_workflow)
    validation_path = _resolve(args.validation_report)
    write_gate_paths = [_resolve(path) for path in args.write_gate_report]
    if not write_gate_paths and DEFAULT_WRITE_GATE_REPORT_PATH.exists():
        write_gate_paths = [DEFAULT_WRITE_GATE_REPORT_PATH]
    output_path = _resolve(args.output)
    assert output_path is not None

    report = build_owner_decision_import_v2(
        decision_import_preview=_load_optional_json(decision_import_path),
        closed_loop_evidence=_load_optional_json(closed_loop_path),
        review_dashboard=_load_optional_json(review_dashboard_path),
        gap_review_workflow=load_json(gap_review_path) if gap_review_path else None,
        validation_report=load_json(validation_path) if validation_path else None,
        write_gate_reports=[
            _load_write_gate_report(path)
            for path in write_gate_paths
            if path is not None and path.exists()
        ],
        source_paths={
            "decision_import_preview": decision_import_path,
            "closed_loop_evidence": closed_loop_path,
            "review_dashboard": review_dashboard_path,
            "gap_review_workflow": gap_review_path or DEFAULT_GAP_REVIEW_PATH,
            "validation_report": validation_path or DEFAULT_VALIDATION_REPORT_PATH,
        },
    )
    require_owner_decision_import_v2(report)
    if args.write:
        path = write_json(output_path, report)
        print(relative_path(path))
    else:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
