"""Import SpecSpace-owned raw idea entry requests into real-idea intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import user_idea_intake_interview

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0202"
SCHEMA_VERSION = 1
STATE_KIND = "specspace_real_idea_entry_request_state"
PREVIEW_KIND = "specspace_real_idea_entry_request_import_preview"
PREVIEW_CONTRACT_REF = (
    "specgraph.idea-to-spec.specspace-real-idea-entry-request-import-preview.v0.1"
)
MATERIALIZATION_KIND = "real_idea_entry_request_intake_report"
MATERIALIZATION_CONTRACT_REF = "specgraph.idea-to-spec.real-idea-entry-request-intake.v0.1"
DEFAULT_RUN_DIR = ROOT / "runs" / "real_idea_smoke"
RESERVED_RUN_DIRS = {"runs"}
AUTHORITY_FALSE_FIELDS = (
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
    "may_execute_specgraph",
    "may_execute_platform",
    "may_execute_prompt_agent",
    "may_apply_to_specgraph",
    "may_mutate_user_intent",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_accept_ontology_terms",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_execute_git_service_operation",
    "may_publish_read_model",
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _text_or_none(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _text_list(value: Any) -> list[str]:
    return [item.strip() for item in _list(value) if isinstance(item, str) and item.strip()]


def _slug(value: str, fallback: str = "real-idea") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _digest(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _relative_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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


def _reject_reserved_run_dir(run_dir_ref: str) -> None:
    if run_dir_ref in RESERVED_RUN_DIRS:
        raise SystemExit(
            f"REAL_IDEA_SMOKE_RUN_DIR={run_dir_ref} is reserved for shared SpecGraph runs. "
            "Use a child directory such as runs/real_idea_smoke or runs/<id>."
        )


def _guard_run_child(path: Path, *, run_dir: Path, field: str) -> Path:
    _ref, repo_path = _repo_relative_path(path, field=field)
    try:
        repo_path.resolve().relative_to(run_dir.resolve())
    except ValueError as exc:
        raise SystemExit(f"{field} must stay inside REAL_IDEA_SMOKE_RUN_DIR.") from exc
    return repo_path


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
        "source": "real_idea_entry_request_import",
        "evidence": evidence or {},
    }


def _first_authority_true(value: Any) -> str | None:
    raw = _dict(value)
    for key, item in raw.items():
        if item is True and (key in AUTHORITY_FALSE_FIELDS or key.startswith("may_")):
            return key
    return None


def _authority_findings(value: Any, *, prefix: str = "") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def visit(item: Any, path: str) -> None:
        if isinstance(item, dict):
            field = _first_authority_true(item)
            if field:
                findings.append(
                    _finding(
                        finding_id="real_idea_entry_authority_expanded",
                        severity="blocking",
                        message=(
                            "Real idea entry request cannot grant execution or mutation authority."
                        ),
                        evidence={"field": f"{path}.{field}" if path else field},
                    )
                )
            for key, child in item.items():
                if isinstance(key, str):
                    visit(child, f"{path}.{key}" if path else key)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, prefix)
    return findings


def _request_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [_dict(item) for item in _list(state.get("requests"))]


def _select_request(
    state: dict[str, Any],
    *,
    workspace_id: str | None,
    request_id: str | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    findings = []
    if state.get("artifact_kind") != STATE_KIND:
        return None, [
            _finding(
                finding_id="real_idea_entry_state_kind_invalid",
                severity="blocking",
                message="SpecSpace entry request state has invalid artifact_kind.",
                evidence={"artifact_kind": state.get("artifact_kind")},
            )
        ]
    findings.extend(_authority_findings(state))
    privacy = _dict(state.get("privacy_boundary"))
    if privacy.get("public_safe") is True or privacy.get("raw_idea_text_public_safe") is True:
        findings.append(
            _finding(
                finding_id="real_idea_entry_privacy_claim_invalid",
                severity="blocking",
                message="Raw idea entry state cannot claim public-safe raw idea text.",
            )
        )
    candidates = []
    for request in _request_rows(state):
        if request_id and request.get("request_id") != request_id:
            continue
        if workspace_id and request.get("workspace_id") != workspace_id:
            continue
        if request.get("status") == "submitted":
            candidates.append(request)
    if not candidates:
        findings.append(
            _finding(
                finding_id="real_idea_entry_submitted_request_missing",
                severity="blocking",
                message=(
                    "No submitted real idea entry request matched the selected workspace/session."
                ),
                evidence={"workspace_id": workspace_id, "request_id": request_id},
            )
        )
        return None, findings
    if len(candidates) > 1:
        findings.append(
            _finding(
                finding_id="real_idea_entry_submitted_request_ambiguous",
                severity="blocking",
                message="Exactly one submitted real idea entry request is required.",
                evidence={"submitted_request_count": len(candidates)},
            )
        )
        return None, findings
    request = candidates[0]
    findings.extend(_authority_findings(request, prefix="request"))
    if not _text(request.get("idea_text")):
        findings.append(
            _finding(
                finding_id="real_idea_entry_text_missing",
                severity="blocking",
                message="Submitted real idea entry request must include idea_text.",
            )
        )
    return request, findings


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_specgraph": False,
        "may_execute_platform": False,
        "may_execute_prompt_agent": False,
        "may_mutate_user_intent": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_accept_ontology_terms": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
    }


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_idea_text_published": False,
        "raw_idea_text_public_safe": False,
        "raw_prompt_published": False,
        "raw_model_output_published": False,
        "local_state_path_published": False,
    }


def build_preview(
    *,
    state: dict[str, Any],
    state_path: Path,
    workspace_id: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    request, findings = _select_request(
        state,
        workspace_id=workspace_id,
        request_id=request_id,
    )
    blocking = [finding for finding in findings if finding["severity"] == "blocking"]
    ready = request is not None and not blocking
    request_meta: dict[str, Any] | None = None
    if request is not None:
        workspace = _text(request.get("workspace_id"))
        display_name = _text_or_none(request.get("workspace_display_name")) or workspace
        request_meta = {
            "request_id": request.get("request_id"),
            "workspace_id": workspace,
            "candidate_id": _slug(workspace or display_name or "real-idea"),
            "display_name": display_name,
            "public_route": _text_or_none(request.get("public_route_hint")) or f"/{workspace}",
            "idea_summary_hint": _text_or_none(request.get("idea_summary_hint")),
            "domain_hint_count": len(_text_list(request.get("domain_hints"))),
            "constraint_count": len(_text_list(request.get("constraints"))),
            "idea_text_digest": _digest({"idea_text": request.get("idea_text")}),
        }
    return {
        "artifact_kind": PREVIEW_KIND,
        "schema_version": SCHEMA_VERSION,
        "contract_ref": PREVIEW_CONTRACT_REF,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "readiness": {
            "ready": ready,
            "review_state": "real_idea_entry_request_ready_for_intake"
            if ready
            else "real_idea_entry_request_review_required",
            "blocked_by": [finding["finding_id"] for finding in blocking],
            "next_artifact": "user_idea_intake_session" if ready else None,
        },
        "source_artifacts": {
            "specspace_entry_request_state": {
                "source_ref": _relative_ref(state_path),
                "artifact_kind": state.get("artifact_kind"),
                "digest": _digest(state),
            }
        },
        "selected_request": request_meta,
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "summary": {
            "status": "real_idea_entry_request_ready_for_intake"
            if ready
            else "real_idea_entry_request_review_required",
            "ready": ready,
            "finding_count": len(findings),
            "request_selected": request is not None,
        },
    }


def _preview_selected_request(preview: dict[str, Any]) -> dict[str, Any]:
    selected = _dict(preview.get("selected_request"))
    if not selected:
        raise SystemExit("Import preview does not select a real idea entry request.")
    if _dict(preview.get("readiness")).get("ready") is not True:
        raise SystemExit("Import preview is not ready for materialization.")
    return selected


def build_materialization(
    *,
    state: dict[str, Any],
    state_path: Path,
    preview: dict[str, Any],
    preview_path: Path,
    run_dir: Path,
    raw_output_path: Path,
    session_output_path: Path,
    source_output_path: Path,
    report_output_path: Path,
) -> dict[str, Any]:
    if preview.get("artifact_kind") != PREVIEW_KIND:
        raise SystemExit("Import preview artifact_kind is unsupported.")
    preview_source = _dict(
        _dict(preview.get("source_artifacts")).get("specspace_entry_request_state")
    )
    if preview_source.get("source_ref") != _relative_ref(state_path):
        raise SystemExit(
            "Import preview source_ref does not match the selected entry request state."
        )
    if preview_source.get("digest") != _digest(state):
        raise SystemExit("Import preview is stale for the selected entry request state.")
    selected = _preview_selected_request(preview)
    request, findings = _select_request(
        state,
        workspace_id=_text(selected.get("workspace_id")),
        request_id=_text(selected.get("request_id")),
    )
    if request is None:
        raise SystemExit("Selected real idea entry request is no longer available.")
    blocking = [finding for finding in findings if finding.get("severity") == "blocking"]
    if blocking:
        raise SystemExit("Selected real idea entry request no longer passes import validation.")
    selected_digest = selected.get("idea_text_digest")
    current_digest = _digest({"idea_text": request.get("idea_text")})
    if selected_digest != current_digest:
        raise SystemExit("Selected real idea entry request text changed after import preview.")
    idea_text = _text(request.get("idea_text"))
    idea_summary = _text(request.get("idea_summary_hint"))
    display_name = _text(request.get("workspace_display_name")) or _text(
        selected.get("display_name")
    )
    workspace_id = _text(request.get("workspace_id"))
    candidate_id = _slug(workspace_id or display_name)
    public_route = _text(request.get("public_route_hint")) or f"/{workspace_id}"
    domain_refs = [
        item if item.startswith("domain.") else f"domain.{_slug(item)}"
        for item in _text_list(request.get("domain_hints"))
    ]
    constraints = _text_list(request.get("constraints"))
    raw_input, session, interview_report, source = user_idea_intake_interview.build_interview(
        base_input=None,
        base_input_path=None,
        idea_text=idea_text,
        idea_summary=idea_summary,
        candidate_id=candidate_id,
        display_name=display_name,
        public_route=public_route,
        project="SpecGraph",
        subsystem="Product Workspace",
        lifecycle_phase="idea_intake",
        ontology_refs=["ontology://specgraph-core"],
        ontology_layer_refs=["ontology-layer://core"],
        domain_refs=domain_refs,
        context_refs=[f"context.{candidate_id}"],
        model_applicability_refs=["model-applicability://product-idea-to-spec"],
        event_entries={"constraints": constraints},
        clarification_requests=None,
        clarification_requests_path=None,
        clarification_answers=None,
        clarification_answers_path=None,
        raw_output_path=raw_output_path,
        session_output_path=session_output_path,
        source_output_path=source_output_path,
    )
    write_json(raw_input, raw_output_path)
    write_json(session, session_output_path)
    write_json(interview_report, report_output_path)
    if source is not None:
        write_json(source, source_output_path)
    elif source_output_path.exists():
        source_output_path.unlink()
    readiness = _dict(session.get("readiness"))
    ready = readiness.get("ready") is True
    return {
        "artifact_kind": MATERIALIZATION_KIND,
        "schema_version": SCHEMA_VERSION,
        "contract_ref": MATERIALIZATION_CONTRACT_REF,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "run_dir": _relative_ref(run_dir),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "specspace_entry_request_state": _relative_ref(state_path),
            "import_preview": _relative_ref(preview_path),
        },
        "output_artifacts": {
            "raw_input": _relative_ref(raw_output_path),
            "intake_session": _relative_ref(session_output_path),
            "intake_source": _relative_ref(source_output_path) if source is not None else None,
            "interview_report": _relative_ref(report_output_path),
        },
        "readiness": {
            "ready": True,
            "review_state": "real_idea_entry_request_intake_materialized",
            "blocked_by": [],
            "next_artifact": "idea_intake_clarification_requests"
            if not ready
            else "user_idea_intake_source",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "summary": {
            "status": "real_idea_entry_request_intake_materialized",
            "intake_session_ready": ready,
            "source_written": source is not None,
            "clarification_question_count": len(_list(session.get("clarification_questions"))),
            "candidate_id": candidate_id,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    preview = subcommands.add_parser("preview")
    preview.add_argument("--specspace-entry-requests", type=Path, required=True)
    preview.add_argument("--workspace-id", default="")
    preview.add_argument("--request-id", default="")
    preview.add_argument("--output", type=Path, required=True)
    preview.add_argument("--strict", action="store_true")

    materialize = subcommands.add_parser("materialize")
    materialize.add_argument("--specspace-entry-requests", type=Path, required=True)
    materialize.add_argument("--import-preview", type=Path, required=True)
    materialize.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    materialize.add_argument("--raw-output", type=Path, required=True)
    materialize.add_argument("--session-output", type=Path, required=True)
    materialize.add_argument("--source-output", type=Path, required=True)
    materialize.add_argument("--interview-report-output", type=Path, required=True)
    materialize.add_argument("--output", type=Path, required=True)
    materialize.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preview":
        state_ref, state_path = _repo_relative_path(
            args.specspace_entry_requests,
            field="--specspace-entry-requests",
        )
        state = load_json(state_path)
        preview = build_preview(
            state=state,
            state_path=state_path,
            workspace_id=_text_or_none(args.workspace_id),
            request_id=_text_or_none(args.request_id),
        )
        _ref, output_path = _repo_relative_path(args.output, field="--output")
        write_json(preview, output_path)
        print(f"{preview['summary']['status']}: {state_ref} -> {_relative_ref(output_path)}")
        return 0 if (not args.strict or preview["readiness"]["ready"]) else 1

    run_dir_ref, run_dir = _repo_relative_path(args.run_dir, field="--run-dir")
    _reject_reserved_run_dir(run_dir_ref)
    state_ref, state_path = _repo_relative_path(
        args.specspace_entry_requests,
        field="--specspace-entry-requests",
    )
    preview_ref, preview_path = _repo_relative_path(
        args.import_preview,
        field="--import-preview",
    )
    raw_output = _guard_run_child(args.raw_output, run_dir=run_dir, field="--raw-output")
    session_output = _guard_run_child(
        args.session_output, run_dir=run_dir, field="--session-output"
    )
    source_output = _guard_run_child(args.source_output, run_dir=run_dir, field="--source-output")
    interview_report_output = _guard_run_child(
        args.interview_report_output,
        run_dir=run_dir,
        field="--interview-report-output",
    )
    output = _guard_run_child(args.output, run_dir=run_dir, field="--output")
    report = build_materialization(
        state=load_json(state_path),
        state_path=state_path,
        preview=load_json(preview_path),
        preview_path=preview_path,
        run_dir=run_dir,
        raw_output_path=raw_output,
        session_output_path=session_output,
        source_output_path=source_output,
        report_output_path=interview_report_output,
    )
    write_json(report, output)
    print(f"{report['summary']['status']}: {state_ref} + {preview_ref} -> {_relative_ref(output)}")
    return 0 if (not args.strict or report["readiness"]["ready"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
