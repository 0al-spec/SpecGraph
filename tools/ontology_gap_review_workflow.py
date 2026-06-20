#!/usr/bin/env python3
"""Build a read-only ontology gap review workflow surface."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ontology_imports import ROOT, relative_path, write_json
from ontology_package_authoring import build_authoring_surface
from spec_ontology_validation_report import build_validation_report

PROPOSAL_ID = "0138"
SCHEMA_VERSION = 1
DEFAULT_OUTPUT_PATH = ROOT / "runs/ontology_gap_review_workflow.json"
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
    return TOKEN_RE.sub("-", value.casefold()).strip("-") or "gap"


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


def _gap_key(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text.casefold()
    return "unknown"


def _group_id(kind: str, key: str) -> str:
    return f"ontology-gap-review-{_slug(kind)}-{_slug(key)}"


def _dedupe_append(
    items: list[dict[str, Any]],
    item: dict[str, Any],
    key_fields: tuple[str, ...],
) -> None:
    key = tuple(item.get(field) for field in key_fields)
    if any(tuple(existing.get(field) for field in key_fields) == key for existing in items):
        return
    items.append(item)


def _ensure_group(
    groups: dict[str, dict[str, Any]],
    *,
    gap_kind: str,
    key: str,
    proposed_term: str | None = None,
    proposed_relation: str | None = None,
    missing_ref: str | None = None,
    recommended_owner_action: str,
    recommended_route: str,
) -> dict[str, Any]:
    group_key = f"{gap_kind}:{key}"
    if group_key not in groups:
        groups[group_key] = {
            "group_id": _group_id(gap_kind, key),
            "gap_key": group_key,
            "gap_kind": gap_kind,
            "proposed_term": proposed_term,
            "proposed_relation": proposed_relation,
            "missing_ref": missing_ref,
            "recommended_owner_action": recommended_owner_action,
            "recommended_route": recommended_route,
            "source_specs": [],
            "affected_generated_artifacts": [],
            "source_gap_refs": [],
            "source_findings": [],
            "source_refs": [],
            "review_state": "needs_owner_review",
            "canonical_mutations_allowed": False,
        }
    group = groups[group_key]
    if proposed_term and not group.get("proposed_term"):
        group["proposed_term"] = proposed_term
    if proposed_relation and not group.get("proposed_relation"):
        group["proposed_relation"] = proposed_relation
    if missing_ref and not group.get("missing_ref"):
        group["missing_ref"] = missing_ref
    return group


def _add_source_refs(group: dict[str, Any], refs: list[Any]) -> None:
    for ref in refs:
        source_ref = _text(ref)
        if source_ref and source_ref not in group["source_refs"]:
            group["source_refs"].append(source_ref)


def _add_gap_ref(group: dict[str, Any], gap_ref: str | None, source_artifact: str) -> None:
    if not gap_ref:
        return
    _dedupe_append(
        group["source_gap_refs"],
        {"gap_ref": gap_ref, "source_artifact": source_artifact},
        ("gap_ref", "source_artifact"),
    )


def _add_finding(group: dict[str, Any], finding: dict[str, Any], source_artifact: str) -> None:
    _dedupe_append(
        group["source_findings"],
        {
            "finding_id": finding.get("finding_id"),
            "classification": finding.get("classification"),
            "severity": finding.get("severity"),
            "suggested_action": finding.get("suggested_action"),
            "source_artifact": source_artifact,
        },
        ("finding_id", "source_artifact"),
    )


def ingest_package_gap_preview(
    groups: dict[str, dict[str, Any]],
    gap_preview: dict[str, Any],
    *,
    source_artifact: str,
) -> None:
    for raw_gap in _list(gap_preview.get("gaps")):
        gap = _dict(raw_gap)
        missing_ref = _text(gap.get("missing_ref"))
        proposed_term = _text(gap.get("missing_concept")) or missing_ref.rsplit(":", 1)[-1]
        key = _gap_key(proposed_term, missing_ref, gap.get("gap_id"))
        group = _ensure_group(
            groups,
            gap_kind="package_term",
            key=key,
            proposed_term=proposed_term,
            missing_ref=missing_ref,
            recommended_owner_action="draft_project_local_ontology_package_update",
            recommended_route=_text(gap.get("recommended_route"), "ontology_package_draft"),
        )
        _add_gap_ref(group, _text(gap.get("gap_id")), source_artifact)
        _add_source_refs(group, _list(gap.get("source_refs")))


def ingest_validation_report(
    groups: dict[str, dict[str, Any]],
    validation_report: dict[str, Any],
    *,
    source_artifact: str,
) -> None:
    for raw_entry in _list(validation_report.get("entries")):
        entry = _dict(raw_entry)
        spec_id = _text(entry.get("spec_id"))
        path = _text(entry.get("path"))
        for raw_finding in _list(entry.get("findings")):
            finding = _dict(raw_finding)
            classification = _text(finding.get("classification"), "unknown")
            if finding.get("relation_ref"):
                relation_ref = _text(finding.get("relation_ref"))
                key = _gap_key(relation_ref, finding.get("finding_id"))
                group = _ensure_group(
                    groups,
                    gap_kind="relation",
                    key=key,
                    proposed_relation=relation_ref,
                    missing_ref=relation_ref,
                    recommended_owner_action="review_relation_candidate_or_package_gap",
                    recommended_route="ontology_owner_review",
                )
            else:
                term = _text(finding.get("term")) or _text(finding.get("gap_ref"))
                key = _gap_key(term, finding.get("gap_ref"), finding.get("finding_id"))
                group = _ensure_group(
                    groups,
                    gap_kind="legacy_term",
                    key=key,
                    proposed_term=term,
                    missing_ref=_text(finding.get("gap_ref")),
                    recommended_owner_action="review_legacy_term_for_package_draft",
                    recommended_route="ontology_owner_review",
                )
            _dedupe_append(
                group["source_specs"],
                {
                    "spec_id": spec_id,
                    "path": path,
                    "finding_id": finding.get("finding_id"),
                    "classification": classification,
                    "source": finding.get("source"),
                },
                ("spec_id", "path", "finding_id"),
            )
            _add_gap_ref(group, _text(finding.get("gap_ref")), source_artifact)
            _add_finding(group, finding, source_artifact)


def ingest_generated_artifact(
    groups: dict[str, dict[str, Any]],
    artifact: dict[str, Any],
    *,
    path: Path | None = None,
) -> None:
    source_ref = _text(artifact.get("source_ref"), _path_ref(path) or "generated_artifact")
    target = _dict(artifact.get("target_artifact"))
    for raw_gap in _list(artifact.get("ontology_gaps")):
        gap = _dict(raw_gap)
        proposed_term = _text(gap.get("proposed_term"))
        proposed_relation = _text(gap.get("proposed_relation"))
        missing_ref = _text(gap.get("missing_ref"))
        gap_kind = "generated_relation" if proposed_relation else "generated_term"
        key = _gap_key(proposed_term, proposed_relation, missing_ref, gap.get("gap_id"))
        group = _ensure_group(
            groups,
            gap_kind=gap_kind,
            key=key,
            proposed_term=proposed_term or None,
            proposed_relation=proposed_relation or None,
            missing_ref=missing_ref or None,
            recommended_owner_action="request_ontology_owner_decision",
            recommended_route="ontology_owner_review",
        )
        _dedupe_append(
            group["affected_generated_artifacts"],
            {
                "source_ref": source_ref,
                "path": _path_ref(path),
                "artifact_kind": artifact.get("artifact_kind"),
                "target_artifact_kind": target.get("kind"),
                "target_artifact_title": target.get("title"),
                "gap_status": gap.get("status"),
            },
            ("source_ref", "path", "target_artifact_title"),
        )
        _add_gap_ref(group, _text(gap.get("gap_id")), source_ref)
        _add_source_refs(group, _list(gap.get("source_refs")))


def normalize_group(group: dict[str, Any]) -> dict[str, Any]:
    group["source_specs"] = sorted(
        group["source_specs"], key=lambda item: (item.get("spec_id") or "", item.get("path") or "")
    )
    group["affected_generated_artifacts"] = sorted(
        group["affected_generated_artifacts"],
        key=lambda item: (item.get("source_ref") or "", item.get("path") or ""),
    )
    group["source_gap_refs"] = sorted(
        group["source_gap_refs"], key=lambda item: item.get("gap_ref") or ""
    )
    group["source_findings"] = sorted(
        group["source_findings"], key=lambda item: item.get("finding_id") or ""
    )
    group["source_refs"] = sorted(group["source_refs"])
    group["source_spec_count"] = len(group["source_specs"])
    group["affected_generated_artifact_count"] = len(group["affected_generated_artifacts"])
    return group


def build_gap_review_workflow(
    *,
    package_gap_preview: dict[str, Any] | None = None,
    validation_report: dict[str, Any] | None = None,
    generated_artifacts: list[tuple[dict[str, Any], Path | None]] | None = None,
) -> dict[str, Any]:
    package_gap_preview = package_gap_preview or build_authoring_surface("gaps")
    validation_report = validation_report or build_validation_report()
    generated_artifacts = generated_artifacts or []

    groups: dict[str, dict[str, Any]] = {}
    ingest_package_gap_preview(
        groups,
        package_gap_preview,
        source_artifact="ontology_package_gap_preview",
    )
    ingest_validation_report(
        groups,
        validation_report,
        source_artifact="spec_ontology_validation_report",
    )
    for artifact, path in generated_artifacts:
        ingest_generated_artifact(groups, artifact, path=path)

    gap_groups = sorted(
        (normalize_group(group) for group in groups.values()),
        key=lambda item: (item["gap_kind"], item.get("proposed_term") or "", item["group_id"]),
    )
    source_spec_ids = {
        spec["spec_id"]
        for group in gap_groups
        for spec in group["source_specs"]
        if spec.get("spec_id")
    }
    generated_refs = {
        artifact["source_ref"]
        for group in gap_groups
        for artifact in group["affected_generated_artifacts"]
        if artifact.get("source_ref")
    }
    action_counts: dict[str, int] = {}
    for group in gap_groups:
        action = str(group["recommended_owner_action"])
        action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "artifact_kind": "ontology_gap_review_workflow",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "status": "review_required" if gap_groups else "clear",
        "review_state": "ready_for_review" if gap_groups else "clear",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "package_gap_preview": package_gap_preview.get("artifact_kind"),
            "spec_ontology_validation_report": validation_report.get("artifact_kind"),
            "generated_artifact_count": len(generated_artifacts),
        },
        "validation_modes": {
            "legacy_specs": "report_only",
            "generated_artifacts": "review_required",
            "owner_decisions": "not_imported",
        },
        "summary": {
            "gap_group_count": len(gap_groups),
            "source_spec_count": len(source_spec_ids),
            "affected_generated_artifact_count": len(generated_refs),
            "recommended_owner_action_counts": action_counts,
            "next_gap": "review_grouped_ontology_gaps" if gap_groups else "none",
        },
        "gap_groups": gap_groups,
        "operator_actions": [
            {
                "action": "inspect_gap_group",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            },
            {
                "action": "acknowledge_gap_review",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            },
            {
                "action": "request_ontology_owner_decision",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "mutates_canonical_specs": False,
            },
        ],
        "authority_boundary": {
            "gap_review_workflow_is_authority": False,
            "may_execute_prompt_agent": False,
            "may_write_ontology_package": False,
            "may_write_ontology_lockfile": False,
            "may_mutate_canonical_specs": False,
            "may_mark_candidate_accepted": False,
            "may_import_owner_decision": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-gap-preview", type=Path)
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--generated-artifact", action="append", default=[], type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def _resolve(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    args = parse_args()
    package_gap_path = _resolve(args.package_gap_preview)
    validation_path = _resolve(args.validation_report)
    generated_paths = [_resolve(path) for path in args.generated_artifact]
    generated_artifacts = [(load_json(path), path) for path in generated_paths if path is not None]
    output_path = _resolve(args.output)
    assert output_path is not None

    report = build_gap_review_workflow(
        package_gap_preview=load_json(package_gap_path) if package_gap_path else None,
        validation_report=load_json(validation_path) if validation_path else None,
        generated_artifacts=generated_artifacts,
    )
    if args.write:
        path = write_json(output_path, report)
        print(relative_path(path))
    else:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
