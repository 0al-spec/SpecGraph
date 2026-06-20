#!/usr/bin/env python3
"""Build a review-first backfill plan for legacy specs against ontology findings."""

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

PROPOSAL_ID = "0140"
SCHEMA_VERSION = 1
DEFAULT_OUTPUT_PATH = ROOT / "runs/legacy_spec_ontology_backfill_plan.json"
TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) and value.strip() else default


def _slug(value: str) -> str:
    return TOKEN_RE.sub("-", value.casefold()).strip("-") or "item"


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


def _finding_id_set(group: dict[str, Any]) -> set[str]:
    return {
        _text(finding.get("finding_id"))
        for finding in _list(group.get("source_findings"))
        if _text(_dict(finding).get("finding_id"))
    }


def _gap_ref_set(group: dict[str, Any]) -> set[str]:
    return {
        _text(ref.get("gap_ref"))
        for ref in _list(group.get("source_gap_refs"))
        if _text(_dict(ref).get("gap_ref"))
    }


def index_gap_groups(gap_review_workflow: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}

    def add(key: str, group: dict[str, Any]) -> None:
        if not key:
            return
        index.setdefault(key, [])
        if not any(existing.get("group_id") == group.get("group_id") for existing in index[key]):
            index[key].append(group)

    for raw_group in _list(gap_review_workflow.get("gap_groups")):
        group = _dict(raw_group)
        for raw_spec in _list(group.get("source_specs")):
            spec = _dict(raw_spec)
            add(_text(spec.get("spec_id")), group)
            add(_text(spec.get("finding_id")), group)
        for finding_id in _finding_id_set(group):
            add(finding_id, group)
        for gap_ref in _gap_ref_set(group):
            add(gap_ref, group)
    return index


def _finding_summary(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        classification = _text(finding.get("classification"), "unknown")
        counts[classification] = counts.get(classification, 0) + 1
    return dict(sorted(counts.items()))


def _unknown_terms(findings: list[dict[str, Any]]) -> list[str]:
    terms = {
        _text(finding.get("term"))
        for finding in findings
        if _text(finding.get("classification")) == "unknown_legacy_term"
        and _text(finding.get("term"))
    }
    return sorted(terms, key=str.casefold)


def _relation_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relation_classes = {"unknown_relation", "relation_domain_range_mismatch"}
    result: list[dict[str, Any]] = []
    for finding in findings:
        if _text(finding.get("classification")) not in relation_classes:
            continue
        result.append(
            {
                "finding_id": finding.get("finding_id"),
                "classification": finding.get("classification"),
                "relation_ref": finding.get("relation_ref"),
                "severity": finding.get("severity"),
                "suggested_action": finding.get("suggested_action"),
            }
        )
    return result


def _missing_required_bindings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for finding in findings:
        if _text(finding.get("classification")) != "missing_required_binding":
            continue
        result.append(
            {
                "finding_id": finding.get("finding_id"),
                "severity": finding.get("severity"),
                "suggested_action": finding.get("suggested_action"),
                "message": finding.get("message"),
            }
        )
    return result


def _matched_gap_groups(
    spec_id: str,
    findings: list[dict[str, Any]],
    gap_group_index: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    keys = [spec_id]
    keys.extend(_text(finding.get("finding_id")) for finding in findings)
    keys.extend(_text(finding.get("gap_ref")) for finding in findings)
    for key in keys:
        for group in gap_group_index.get(key, []):
            if not any(existing.get("group_id") == group.get("group_id") for existing in matches):
                matches.append(group)
    return sorted(matches, key=lambda group: _text(group.get("group_id")))


def classify_spec_review(
    *,
    findings: list[dict[str, Any]],
    max_findings_per_small_pr_spec: int,
) -> tuple[str, str]:
    if not findings:
        return "clean_existing_bindings", "monitor_only"

    relation_findings = _relation_findings(findings)
    missing_bindings = _missing_required_bindings(findings)
    unknown_terms = _unknown_terms(findings)
    non_warning_findings = [
        finding for finding in findings if _text(finding.get("severity")) != "warning"
    ]

    if non_warning_findings:
        return "blocking_review_required", "review_non_warning_findings"
    if missing_bindings:
        return "binding_extraction_review_required", "review_binding_extraction"
    if relation_findings:
        return "relation_review_required", "review_relation_contract_or_gap"
    if unknown_terms and len(findings) <= max_findings_per_small_pr_spec:
        return "ready_for_small_pr_batch", "plan_small_reviewed_backfill_pr"
    if unknown_terms:
        return "new_term_decision_required", "review_unknown_terms_for_package_or_alias"
    return "warnings_only_review", "review_warning_findings"


def build_spec_review(
    entry: dict[str, Any],
    *,
    gap_group_index: dict[str, list[dict[str, Any]]],
    max_findings_per_small_pr_spec: int,
) -> dict[str, Any]:
    spec_id = _text(entry.get("spec_id"))
    findings = [_dict(finding) for finding in _list(entry.get("findings"))]
    unknown_terms = _unknown_terms(findings)
    relation_findings = _relation_findings(findings)
    missing_bindings = _missing_required_bindings(findings)
    gap_groups = _matched_gap_groups(spec_id, findings, gap_group_index)
    warning_count = sum(1 for finding in findings if _text(finding.get("severity")) == "warning")
    category, action = classify_spec_review(
        findings=findings,
        max_findings_per_small_pr_spec=max_findings_per_small_pr_spec,
    )
    return {
        "spec_id": spec_id,
        "path": entry.get("path"),
        "validation_status": entry.get("validation_status"),
        "backfill_category": category,
        "recommended_owner_action": action,
        "finding_count": len(findings),
        "warning_count": warning_count,
        "blocking_finding_count": len(findings) - warning_count,
        "finding_classification_counts": _finding_summary(findings),
        "unknown_terms": unknown_terms,
        "unknown_term_count": len(unknown_terms),
        "relation_findings": relation_findings,
        "relation_finding_count": len(relation_findings),
        "missing_required_bindings": missing_bindings,
        "matched_gap_groups": [
            {
                "group_id": group.get("group_id"),
                "gap_kind": group.get("gap_kind"),
                "proposed_term": group.get("proposed_term"),
                "proposed_relation": group.get("proposed_relation"),
                "recommended_owner_action": group.get("recommended_owner_action"),
                "recommended_route": group.get("recommended_route"),
            }
            for group in gap_groups
        ],
        "matched_gap_group_count": len(gap_groups),
        "canonical_mutations_allowed": False,
        "review_boundary": "plan_only",
    }


def build_small_pr_batches(
    spec_reviews: list[dict[str, Any]],
    *,
    max_specs_per_batch: int,
    max_findings_per_batch: int,
) -> list[dict[str, Any]]:
    candidates = [
        review
        for review in spec_reviews
        if review["backfill_category"] == "ready_for_small_pr_batch"
    ]
    candidates = sorted(candidates, key=lambda review: (review["finding_count"], review["spec_id"]))
    batches: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_findings = 0

    def flush() -> None:
        nonlocal current, current_findings
        if not current:
            return
        batch_number = len(batches) + 1
        batches.append(
            {
                "batch_id": f"legacy-spec-ontology-backfill-batch-{batch_number:03d}",
                "review_state": "ready_for_review",
                "recommended_pr_scope": "small_reviewed_terminology_backfill",
                "spec_count": len(current),
                "finding_count": current_findings,
                "specs": [
                    {
                        "spec_id": review["spec_id"],
                        "path": review["path"],
                        "finding_count": review["finding_count"],
                        "unknown_terms": review["unknown_terms"],
                        "matched_gap_group_count": review["matched_gap_group_count"],
                    }
                    for review in current
                ],
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            }
        )
        current = []
        current_findings = 0

    for review in candidates:
        finding_count = int(review["finding_count"])
        would_exceed_specs = len(current) >= max_specs_per_batch
        would_exceed_findings = current_findings + finding_count > max_findings_per_batch
        if current and (would_exceed_specs or would_exceed_findings):
            flush()
        current.append(review)
        current_findings += finding_count
    flush()
    return batches


def build_legacy_spec_ontology_backfill_plan(
    *,
    validation_report: dict[str, Any] | None = None,
    gap_review_workflow: dict[str, Any] | None = None,
    max_findings_per_small_pr_spec: int = 3,
    max_specs_per_batch: int = 5,
    max_findings_per_batch: int = 10,
    source_paths: dict[str, Path | None] | None = None,
) -> dict[str, Any]:
    validation_report = validation_report or build_validation_report()
    gap_review_workflow = gap_review_workflow or build_gap_review_workflow(
        validation_report=validation_report
    )
    source_paths = source_paths or {}
    effective_max_findings_per_small_pr_spec = min(
        max_findings_per_small_pr_spec,
        max_findings_per_batch,
    )

    gap_group_index = index_gap_groups(gap_review_workflow)
    entries = [
        entry for entry in _list(validation_report.get("entries")) if isinstance(entry, dict)
    ]
    spec_reviews = [
        build_spec_review(
            entry,
            gap_group_index=gap_group_index,
            max_findings_per_small_pr_spec=effective_max_findings_per_small_pr_spec,
        )
        for entry in entries
    ]
    category_counts: dict[str, int] = {}
    for review in spec_reviews:
        category = _text(review.get("backfill_category"), "unknown")
        category_counts[category] = category_counts.get(category, 0) + 1
    warning_only_specs = [
        review
        for review in spec_reviews
        if review["finding_count"] and review["warning_count"] == review["finding_count"]
    ]
    unknown_term_specs = [review for review in spec_reviews if review["unknown_term_count"]]
    large_new_term_specs = [
        review
        for review in spec_reviews
        if review["unknown_term_count"]
        and review["backfill_category"] != "ready_for_small_pr_batch"
    ]
    relation_review_specs = [review for review in spec_reviews if review["relation_finding_count"]]
    small_pr_batches = build_small_pr_batches(
        spec_reviews,
        max_specs_per_batch=max_specs_per_batch,
        max_findings_per_batch=max_findings_per_batch,
    )
    review_required_count = sum(1 for review in spec_reviews if review["finding_count"])
    status = "review_required" if review_required_count else "clear"

    return {
        "artifact_kind": "legacy_spec_ontology_backfill_plan",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "status": status,
        "review_state": "ready_for_review" if review_required_count else "clear",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "spec_ontology_validation_report": _source_artifact_ref(
                validation_report,
                source_paths.get("validation_report"),
            ),
            "ontology_gap_review_workflow": _source_artifact_ref(
                gap_review_workflow,
                source_paths.get("gap_review_workflow"),
            ),
        },
        "planning_thresholds": {
            "max_findings_per_small_pr_spec": max_findings_per_small_pr_spec,
            "effective_max_findings_per_small_pr_spec": (effective_max_findings_per_small_pr_spec),
            "max_specs_per_batch": max_specs_per_batch,
            "max_findings_per_batch": max_findings_per_batch,
        },
        "summary": {
            "status": status,
            "spec_count": len(spec_reviews),
            "review_required_spec_count": review_required_count,
            "clean_spec_count": len(spec_reviews) - review_required_count,
            "warning_only_spec_count": len(warning_only_specs),
            "new_term_decision_spec_count": len(unknown_term_specs),
            "large_new_term_decision_spec_count": len(large_new_term_specs),
            "relation_review_spec_count": len(relation_review_specs),
            "small_pr_candidate_spec_count": category_counts.get("ready_for_small_pr_batch", 0),
            "small_pr_batch_count": len(small_pr_batches),
            "finding_count": sum(review["finding_count"] for review in spec_reviews),
            "unknown_term_count": sum(review["unknown_term_count"] for review in spec_reviews),
            "category_counts": dict(sorted(category_counts.items())),
            "next_gap": "review_legacy_spec_backfill_batches" if review_required_count else "none",
        },
        "spec_reviews": spec_reviews,
        "small_pr_batches": small_pr_batches,
        "operator_actions": [
            {
                "action": "inspect_backfill_plan",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            },
            {
                "action": "select_small_backfill_batch_for_review",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            },
            {
                "action": "request_ontology_owner_term_decision",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            },
        ],
        "authority_boundary": {
            "legacy_backfill_plan_is_authority": False,
            "may_execute_prompt_agent": False,
            "may_write_ontology_package": False,
            "may_write_ontology_lockfile": False,
            "may_mutate_canonical_specs": False,
            "may_mark_candidate_accepted": False,
            "may_import_owner_decision": False,
        },
    }


def require_legacy_spec_ontology_backfill_plan(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("artifact_kind") != "legacy_spec_ontology_backfill_plan":
        raise ValueError("report.artifact_kind must be legacy_spec_ontology_backfill_plan")
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"report.schema_version must be {SCHEMA_VERSION}")
    if report.get("proposal_id") != PROPOSAL_ID:
        raise ValueError(f"report.proposal_id must be {PROPOSAL_ID}")
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if report.get(field) is not False:
            raise ValueError(f"report.{field} must be false")
    spec_reviews = report.get("spec_reviews")
    if not isinstance(spec_reviews, list):
        raise ValueError("report.spec_reviews must be a list")
    for index, raw_review in enumerate(spec_reviews):
        review = _dict(raw_review)
        context = f"report.spec_reviews[{index}]"
        if not _text(review.get("spec_id")):
            raise ValueError(f"{context}.spec_id must be present")
        if review.get("canonical_mutations_allowed") is not False:
            raise ValueError(f"{context}.canonical_mutations_allowed must be false")
    for index, raw_batch in enumerate(_list(report.get("small_pr_batches"))):
        batch = _dict(raw_batch)
        context = f"report.small_pr_batches[{index}]"
        for field in (
            "canonical_mutations_allowed",
            "writes_ontology_package",
            "mutates_canonical_specs",
        ):
            if batch.get(field) is not False:
                raise ValueError(f"{context}.{field} must be false")
    authority_boundary = _dict(report.get("authority_boundary"))
    for field in (
        "legacy_backfill_plan_is_authority",
        "may_execute_prompt_agent",
        "may_write_ontology_package",
        "may_write_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_import_owner_decision",
    ):
        if authority_boundary.get(field) is not False:
            raise ValueError(f"report.authority_boundary.{field} must be false")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--gap-review-workflow", type=Path)
    parser.add_argument("--max-findings-per-small-pr-spec", type=int, default=3)
    parser.add_argument("--max-specs-per-batch", type=int, default=5)
    parser.add_argument("--max-findings-per-batch", type=int, default=10)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def _resolve(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    args = parse_args()
    validation_path = _resolve(args.validation_report)
    gap_review_path = _resolve(args.gap_review_workflow)
    output_path = _resolve(args.output)
    assert output_path is not None

    report = build_legacy_spec_ontology_backfill_plan(
        validation_report=load_json(validation_path) if validation_path else None,
        gap_review_workflow=load_json(gap_review_path) if gap_review_path else None,
        max_findings_per_small_pr_spec=args.max_findings_per_small_pr_spec,
        max_specs_per_batch=args.max_specs_per_batch,
        max_findings_per_batch=args.max_findings_per_batch,
        source_paths={
            "validation_report": validation_path or DEFAULT_VALIDATION_REPORT_PATH,
            "gap_review_workflow": gap_review_path or DEFAULT_GAP_REVIEW_PATH,
        },
    )
    require_legacy_spec_ontology_backfill_plan(report)
    if args.write:
        path = write_json(output_path, report)
        print(relative_path(path))
    else:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
