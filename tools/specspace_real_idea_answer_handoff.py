"""Import SpecSpace-owned real-idea answers and continue intake safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import real_idea_answer_authoring

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
PROPOSAL_ID = "0195"
IMPORT_PREVIEW_KIND = "specspace_real_idea_answer_import_preview"
IMPORT_PREVIEW_CONTRACT_REF = (
    "specgraph.idea-to-spec.specspace-real-idea-answer-import-preview.v0.1"
)
CONTINUATION_REPORT_KIND = "real_idea_answer_continuation_report"
CONTINUATION_REPORT_CONTRACT_REF = "specgraph.idea-to-spec.real-idea-answer-continuation.v0.1"
SPECSPACE_STATE_KIND = "specspace_idea_intake_clarification_answer_state"
ANSWER_SET_KIND = "idea_to_spec_clarification_answer_set"
ANSWER_SET_CONTRACT_REF = "specgraph.idea-to-spec.clarification-answer-set.v0.1"

DEFAULT_RUN_DIR = ROOT / "runs" / "real_idea_smoke"
RESERVED_RUN_DIRS = {"runs"}

TOP_LEVEL_FALSE_FIELDS = (
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
)
CONSUMER_FALSE_FIELDS = (
    "may_execute_specgraph",
    "may_execute_prompt_agent",
    "may_apply_to_specgraph",
    "may_apply_answers",
    "may_apply_answers_to_source_artifacts",
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
AUTHORITY_FALSE_FIELDS = (
    "intake_answer_state_is_authority",
    "specgraph_artifact_authority",
    "ontology_authority",
    "git_service_authority",
    "canonical_mutations_allowed",
    "may_mutate_user_intent",
    "may_publish_read_model",
)
ANSWER_FALSE_FIELDS = (
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
    "applies_to_specgraph",
    "applies_to_candidate_source",
    "mutates_user_intent",
    "mutates_canonical_specs",
    "writes_ontology_package",
    "accepts_ontology_terms",
    "creates_branch_or_commit",
    "opens_pull_request",
)
STATE_LEVEL_AUTHORITY_FIELDS = tuple(
    sorted(set(TOP_LEVEL_FALSE_FIELDS + CONSUMER_FALSE_FIELDS + AUTHORITY_FALSE_FIELDS))
)
PRIVATE_PATH_MARKERS = ("/Users/", "/home/", "\\Users\\")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _guard_output_path(path: Path, *, run_dir: Path, field: str) -> Path:
    _ref, repo_path = _repo_relative_path(path, field=field)
    try:
        repo_path.resolve().relative_to(run_dir.resolve())
    except ValueError as exc:
        raise SystemExit(f"{field} must stay inside REAL_IDEA_SMOKE_RUN_DIR.") from exc
    return repo_path


def _relative_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return real_idea_answer_authoring._relative_ref(path)


def _safe_string(value: str) -> str:
    lowered = value.lower()
    if any(marker.lower() in lowered for marker in PRIVATE_PATH_MARKERS):
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
        return f"redacted-local-ref:{digest}"
    return value


def _public_safe(value: Any) -> Any:
    sanitized = real_idea_answer_authoring._public_safe(value)
    if isinstance(sanitized, dict):
        return {key: _public_safe(item) for key, item in sanitized.items()}
    if isinstance(sanitized, list):
        return [_public_safe(item) for item in sanitized]
    if isinstance(sanitized, str):
        return _safe_string(sanitized)
    return sanitized


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_specgraph": False,
        "may_execute_prompt_agent": False,
        "may_apply_answers_to_source_artifacts": False,
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
        "raw_prompt_published": False,
        "raw_model_output_published": False,
        "raw_operator_note_published": False,
        "local_state_path_published": False,
    }


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
        "source": "specspace_real_idea_answer_handoff",
        "evidence": _public_safe(evidence or {}),
    }


def _first_true(value: Any, fields: tuple[str, ...]) -> str | None:
    raw = _dict(value)
    for field in fields:
        if raw.get(field) is True:
            return field
    return None


def _first_authority_true(value: Any, fields: tuple[str, ...]) -> str | None:
    raw = _dict(value)
    for field, item in raw.items():
        if item is not True or not isinstance(field, str):
            continue
        if field in fields or field.startswith("may_"):
            return field
    return None


def _answer_set_from_specspace_state(state: dict[str, Any]) -> dict[str, Any]:
    answer_set = _dict(state.get("answer_set"))
    if answer_set:
        return {
            **answer_set,
            "answers": [_public_safe(_dict(item)) for item in _list(answer_set.get("answers"))],
        }
    return {
        "artifact_kind": ANSWER_SET_KIND,
        "schema_version": SCHEMA_VERSION,
        "contract_ref": ANSWER_SET_CONTRACT_REF,
        "answers": [
            {
                "request_id": _text(answer.get("request_id")),
                "answer_kind": _text(answer.get("answer_kind")),
                "status": _text(answer.get("status"), "proposed"),
                "authority": _text(answer.get("authority"), "operator_approved"),
                "value": _public_safe(answer.get("value")),
                "rationale": _text(answer.get("rationale")),
            }
            for answer in [_dict(item) for item in _list(state.get("answers"))]
            if _text(answer.get("request_id")) and _text(answer.get("answer_kind"))
        ],
    }


def _validate_answer_set_authority(answer_set: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    expanded = _first_authority_true(
        answer_set,
        STATE_LEVEL_AUTHORITY_FIELDS + ANSWER_FALSE_FIELDS,
    )
    if expanded:
        findings.append(
            _finding(
                finding_id="specspace_answer_set_authority_expanded",
                severity="blocking",
                message="Nested SpecSpace answer set cannot claim mutation or execution authority.",
                evidence={"field": expanded},
            )
        )
    for index, answer in enumerate([_dict(item) for item in _list(answer_set.get("answers"))]):
        expanded = _first_authority_true(answer, ANSWER_FALSE_FIELDS)
        if expanded:
            findings.append(
                _finding(
                    finding_id="specspace_answer_set_row_authority_expanded",
                    severity="blocking",
                    message="Nested answer-set rows cannot claim mutation authority.",
                    evidence={
                        "index": index,
                        "request_id": answer.get("request_id"),
                        "field": expanded,
                    },
                )
            )
    return findings


def _expected_session(session: dict[str, Any]) -> dict[str, str]:
    workspace = _dict(session.get("workspace"))
    candidate_id = _text(workspace.get("candidate_id")) or _text(session.get("candidate_id"))
    return {
        "candidate_id": candidate_id,
        "workspace_id": candidate_id,
        "display_name": _text(workspace.get("display_name")),
        "public_route": _text(workspace.get("public_route")),
        "source_review_state": _text(_dict(session.get("readiness")).get("review_state")),
    }


def _validate_state_root(state: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if state.get("artifact_kind") != SPECSPACE_STATE_KIND:
        findings.append(
            _finding(
                finding_id="specspace_answer_state_wrong_artifact_kind",
                severity="blocking",
                message=f"SpecSpace answer state must use artifact_kind {SPECSPACE_STATE_KIND}.",
                evidence={"artifact_kind": state.get("artifact_kind")},
            )
        )
    if state.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="specspace_answer_state_schema_version_unsupported",
                severity="blocking",
                message="SpecSpace answer state schema_version must be 1.",
                evidence={"schema_version": state.get("schema_version")},
            )
        )
    if state.get("state_owner") != "SpecSpace":
        findings.append(
            _finding(
                finding_id="specspace_answer_state_owner_unsupported",
                severity="blocking",
                message="Intake answer state must be owned by SpecSpace.",
                evidence={"state_owner": state.get("state_owner")},
            )
        )
    for field, source, fields in (
        ("top_level", state, TOP_LEVEL_FALSE_FIELDS),
        ("consumer_boundary", state.get("consumer_boundary"), CONSUMER_FALSE_FIELDS),
        ("authority_boundary", state.get("authority_boundary"), AUTHORITY_FALSE_FIELDS),
    ):
        expanded = _first_authority_true(source, fields)
        if expanded:
            findings.append(
                _finding(
                    finding_id="specspace_answer_state_authority_expanded",
                    severity="blocking",
                    message="SpecSpace answer state cannot claim mutation or execution authority.",
                    evidence={"scope": field, "field": expanded},
                )
            )
    for answer in [_dict(item) for item in _list(state.get("answers"))]:
        expanded = _first_authority_true(answer, ANSWER_FALSE_FIELDS)
        if expanded:
            findings.append(
                _finding(
                    finding_id="specspace_answer_authority_expanded",
                    severity="blocking",
                    message="SpecSpace answer rows cannot claim mutation authority.",
                    evidence={"answer_id": answer.get("answer_id"), "field": expanded},
                )
            )
    findings.extend(_validate_answer_set_authority(_dict(state.get("answer_set"))))
    findings.extend(
        real_idea_answer_authoring._scan_authority_and_raw(
            {
                "answers": state.get("answers"),
                "answer_set": state.get("answer_set"),
            }
        )
    )
    return findings


def _validate_refs(
    *,
    state: dict[str, Any],
    session: dict[str, Any],
    template_path: Path,
    requests_path: Path,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    expected = _expected_session(session)
    expected_workspace = expected["workspace_id"]
    expected_candidate = expected["candidate_id"]
    if not expected_candidate:
        findings.append(
            _finding(
                finding_id="intake_session_candidate_id_missing",
                severity="blocking",
                message="Intake session must declare workspace.candidate_id.",
            )
        )
    selected_workspace = _text(state.get("selected_workspace_id"))
    if not selected_workspace:
        findings.append(
            _finding(
                finding_id="specspace_answer_state_workspace_missing",
                severity="blocking",
                message="SpecSpace answer state must declare selected_workspace_id.",
            )
        )
    elif expected_workspace and selected_workspace != expected_workspace:
        findings.append(
            _finding(
                finding_id="specspace_answer_state_workspace_mismatch",
                severity="blocking",
                message=(
                    "SpecSpace answer state selected_workspace_id does not match intake session."
                ),
                evidence={"expected": expected_workspace, "actual": selected_workspace},
            )
        )
    template_ref = _relative_ref(template_path)
    requests_ref = _relative_ref(requests_path)
    sources = _dict(state.get("source_artifacts"))
    source_template = _text(sources.get("real_idea_answer_template"))
    if not source_template:
        findings.append(
            _finding(
                finding_id="specspace_answer_template_ref_missing",
                severity="blocking",
                message="SpecSpace answer state must reference the selected answer template.",
                evidence={"expected": template_ref},
            )
        )
    elif source_template != template_ref:
        findings.append(
            _finding(
                finding_id="specspace_answer_template_ref_mismatch",
                severity="blocking",
                message="SpecSpace answer state template ref does not match selected template.",
                evidence={"expected": template_ref, "actual": source_template},
            )
        )
    source_requests = _text(sources.get("intake_clarification_requests"))
    if not source_requests:
        findings.append(
            _finding(
                finding_id="specspace_answer_requests_ref_missing",
                severity="blocking",
                message=(
                    "SpecSpace answer state must reference the selected clarification requests."
                ),
                evidence={"expected": requests_ref},
            )
        )
    elif source_requests != requests_ref:
        findings.append(
            _finding(
                finding_id="specspace_answer_requests_ref_mismatch",
                severity="blocking",
                message=(
                    "SpecSpace answer state request ref does not match selected "
                    "clarification requests."
                ),
                evidence={"expected": requests_ref, "actual": source_requests},
            )
        )
    for answer in [_dict(item) for item in _list(state.get("answers"))]:
        answer_id = _text(answer.get("answer_id"), _text(answer.get("request_id")))
        workspace_id = _text(answer.get("workspace_id"))
        candidate_id = _text(answer.get("candidate_id"))
        if expected_workspace and workspace_id and workspace_id != expected_workspace:
            findings.append(
                _finding(
                    finding_id="specspace_answer_workspace_mismatch",
                    severity="blocking",
                    message="SpecSpace answer workspace_id does not match intake session.",
                    evidence={
                        "answer_id": answer_id,
                        "expected": expected_workspace,
                        "actual": workspace_id,
                    },
                )
            )
        if expected_candidate and candidate_id and candidate_id != expected_candidate:
            findings.append(
                _finding(
                    finding_id="specspace_answer_candidate_mismatch",
                    severity="blocking",
                    message="SpecSpace answer candidate_id does not match intake session.",
                    evidence={
                        "answer_id": answer_id,
                        "expected": expected_candidate,
                        "actual": candidate_id,
                    },
                )
            )
        row_template = _text(answer.get("template_ref"))
        if row_template and row_template != template_ref:
            findings.append(
                _finding(
                    finding_id="specspace_answer_row_template_ref_mismatch",
                    severity="blocking",
                    message="SpecSpace answer row template_ref does not match selected template.",
                    evidence={
                        "answer_id": answer_id,
                        "expected": template_ref,
                        "actual": row_template,
                    },
                )
            )
        row_source = _text(answer.get("source_artifact"))
        if row_source and row_source != requests_ref:
            findings.append(
                _finding(
                    finding_id="specspace_answer_row_request_ref_mismatch",
                    severity="blocking",
                    message=(
                        "SpecSpace answer row source_artifact does not match selected requests."
                    ),
                    evidence={
                        "answer_id": answer_id,
                        "expected": requests_ref,
                        "actual": row_source,
                    },
                )
            )
    return findings


def _validate_import_preview_for_continuation(
    *,
    import_preview: dict[str, Any],
    import_preview_path: Path,
    requests_path: Path,
    run_dir: Path,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    expected_run_dir = _relative_ref(run_dir)
    preview_run_dir = _text(import_preview.get("run_dir"))
    if preview_run_dir != expected_run_dir:
        findings.append(
            _finding(
                finding_id="import_preview_run_dir_mismatch",
                severity="blocking",
                message="Import preview run_dir must match the selected run directory.",
                evidence={"expected": expected_run_dir, "actual": preview_run_dir},
            )
        )
    expected_preview_ref = _relative_ref(import_preview_path)
    preview_source_ref = _text(
        _dict(_dict(import_preview.get("source_artifacts")).get("specspace_answer_state")).get(
            "source_ref"
        )
    )
    if not preview_source_ref:
        findings.append(
            _finding(
                finding_id="import_preview_answer_state_ref_missing",
                severity="blocking",
                message="Import preview must record the SpecSpace answer state source ref.",
            )
        )
    expected_requests_ref = _relative_ref(requests_path)
    preview_requests_ref = _text(
        _dict(_dict(import_preview.get("source_artifacts")).get("clarification_requests")).get(
            "source_ref"
        )
    )
    if preview_requests_ref != expected_requests_ref:
        findings.append(
            _finding(
                finding_id="import_preview_requests_ref_mismatch",
                severity="blocking",
                message=(
                    "Import preview clarification-request source ref must match selected requests."
                ),
                evidence={"expected": expected_requests_ref, "actual": preview_requests_ref},
            )
        )
    if _relative_ref(import_preview_path) != expected_preview_ref:
        findings.append(
            _finding(
                finding_id="import_preview_source_ref_mismatch",
                severity="blocking",
                message="Import preview source ref could not be normalized for continuation.",
            )
        )
    return findings


def _copy_if_exists(source: Path, destination: Path) -> str | None:
    if not source.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return _relative_ref(destination)


def _stage_materialization(
    *,
    clarification_requests: dict[str, Any],
    requests_path: Path,
    answer_set: dict[str, Any],
    import_preview_path: Path,
    answer_set_output: Path,
    validated_answers_output: Path,
    run_dir: Path,
    stage: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    staging_dir = run_dir / ".specspace_real_idea_answer_handoff_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    raw_input = run_dir / "local_operator_user_idea_raw_input.json"
    if raw_input.exists():
        shutil.copy2(raw_input, staging_dir / raw_input.name)
    staged_answer_set = staging_dir / answer_set_output.name
    staged_validated_answers = staging_dir / validated_answers_output.name
    _answer_set, _validated, authoring_report = real_idea_answer_authoring.build_materialization(
        clarification_requests=clarification_requests,
        requests_path=requests_path,
        answer_input=answer_set,
        answers_path=import_preview_path,
        answer_set_output=staged_answer_set,
        validated_answers_output=staged_validated_answers,
        stage=stage,
        run_dir=staging_dir,
    )
    ready = _dict(authoring_report.get("readiness")).get("ready") is True
    published_outputs: dict[str, Any] = {}
    if ready:
        path_pairs = {
            "answer_set": (staged_answer_set, answer_set_output),
            "validated_answers": (staged_validated_answers, validated_answers_output),
            "rerun_input": (
                staging_dir / "idea_intake_answer_rerun_input.json",
                run_dir / "idea_intake_answer_rerun_input.json",
            ),
            "clarified_raw_input": (
                staging_dir / "local_operator_clarified_user_idea_raw_input.json",
                run_dir / "local_operator_clarified_user_idea_raw_input.json",
            ),
            "clarified_intake_session": (
                staging_dir / "clarified_user_idea_intake_session.json",
                run_dir / "clarified_user_idea_intake_session.json",
            ),
            "rerun_report": (
                staging_dir / "idea_intake_clarification_rerun_report.json",
                run_dir / "idea_intake_clarification_rerun_report.json",
            ),
        }
        for key, (source, destination) in path_pairs.items():
            published_outputs[key] = _copy_if_exists(source, destination)
        published_outputs["next_artifact"] = published_outputs.get(
            "clarified_intake_session"
        ) or published_outputs.get("rerun_input")
        authoring_report["outputs"] = {
            key: value for key, value in published_outputs.items() if value
        }
        authoring_report.setdefault("readiness", {})["next_artifact"] = published_outputs.get(
            "next_artifact"
        )
    shutil.rmtree(staging_dir)
    return authoring_report, published_outputs


def build_import_preview(
    *,
    specspace_answer_state: dict[str, Any],
    state_path: Path,
    template: dict[str, Any],
    template_path: Path,
    clarification_requests: dict[str, Any],
    requests_path: Path,
    intake_session: dict[str, Any],
    intake_session_path: Path,
    run_dir: Path,
    stage: str = "intake",
) -> dict[str, Any]:
    answer_set = _answer_set_from_specspace_state(specspace_answer_state)
    answer_count = len(_list(answer_set.get("answers")))
    findings: list[dict[str, Any]] = [
        *_validate_state_root(specspace_answer_state),
        *_validate_refs(
            state=specspace_answer_state,
            session=intake_session,
            template_path=template_path,
            requests_path=requests_path,
        ),
    ]
    if template.get("artifact_kind") != "real_idea_answer_template":
        findings.append(
            _finding(
                finding_id="real_idea_answer_template_wrong_artifact_kind",
                severity="blocking",
                message="Selected answer template must be real_idea_answer_template.",
                evidence={"artifact_kind": template.get("artifact_kind")},
            )
        )
    if _dict(template.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="real_idea_answer_template_not_ready",
                severity="blocking",
                message="Selected answer template is not ready.",
                evidence={"readiness": _dict(template.get("readiness"))},
            )
        )
    findings.extend(
        real_idea_answer_authoring.template_request_binding_findings(
            template=template,
            clarification_requests=clarification_requests,
            requests_path=requests_path,
        )
    )
    if not answer_count:
        findings.append(
            _finding(
                finding_id="specspace_answers_missing",
                severity="blocking",
                message="SpecSpace answer state does not contain answers for continuation.",
            )
        )
    answer_set_path_for_validation = state_path
    _normalized_answer_set, validated_answers, validation_report = (
        real_idea_answer_authoring.build_validation(
            clarification_requests=clarification_requests,
            requests_path=requests_path,
            answer_input=answer_set,
            answers_path=answer_set_path_for_validation,
            stage=stage,
            run_dir=run_dir,
        )
    )
    findings.extend(_list(validation_report.get("findings")))
    validated_ready = _dict(validation_report.get("readiness")).get("ready") is True
    ready = validated_ready and not findings
    accepted_count = _dict(validation_report.get("summary")).get("accepted_answer_count", 0)
    status = (
        "specspace_real_idea_answers_ready_for_continuation"
        if ready
        else "specspace_real_idea_answers_review_required"
    )
    expected = _expected_session(intake_session)
    return {
        "artifact_kind": IMPORT_PREVIEW_KIND,
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": IMPORT_PREVIEW_CONTRACT_REF,
        "generated_at": _now_iso(),
        "stage": stage,
        "run_dir": _relative_ref(run_dir),
        "session": expected,
        "source_artifacts": {
            "specspace_answer_state": {
                "artifact_kind": specspace_answer_state.get("artifact_kind"),
                "source_ref": _relative_ref(state_path),
                "answer_count": answer_count,
            },
            "real_idea_answer_template": {
                "artifact_kind": template.get("artifact_kind"),
                "contract_ref": template.get("contract_ref"),
                "source_ref": _relative_ref(template_path),
            },
            "clarification_requests": {
                "artifact_kind": clarification_requests.get("artifact_kind"),
                "contract_ref": clarification_requests.get("contract_ref"),
                "source_ref": _relative_ref(requests_path),
            },
            "intake_session": {
                "artifact_kind": intake_session.get("artifact_kind"),
                "source_ref": _relative_ref(intake_session_path),
            },
        },
        "import_preview": {
            "answer_set_candidate": answer_set if ready else {},
            "accepted_answer_count": accepted_count,
            "answer_count": answer_count,
            "validated_answers": {
                "artifact_kind": validated_answers.get("artifact_kind"),
                "contract_ref": validated_answers.get("contract_ref"),
                "ready": _dict(validated_answers.get("readiness")).get("ready"),
                "review_state": _dict(validated_answers.get("readiness")).get("review_state"),
                "summary": _public_safe(_dict(validated_answers.get("summary"))),
            },
        },
        "readiness": {
            "ready": ready,
            "review_state": status,
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "real_idea_answer_continuation_report.json",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "summary": {
            "status": status,
            "candidate_id": expected.get("candidate_id"),
            "workspace_id": expected.get("workspace_id"),
            "answer_count": answer_count,
            "accepted_answer_count": accepted_count,
            "finding_count": len(findings),
        },
    }


def build_continuation_report(
    *,
    import_preview: dict[str, Any],
    import_preview_path: Path,
    clarification_requests: dict[str, Any],
    requests_path: Path,
    answer_set_output: Path,
    validated_answers_output: Path,
    authoring_report_output: Path,
    run_dir: Path,
    stage: str = "intake",
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if import_preview.get("artifact_kind") != IMPORT_PREVIEW_KIND:
        findings.append(
            _finding(
                finding_id="import_preview_wrong_artifact_kind",
                severity="blocking",
                message=f"Import preview must use artifact_kind {IMPORT_PREVIEW_KIND}.",
                evidence={"artifact_kind": import_preview.get("artifact_kind")},
            )
        )
    if import_preview.get("contract_ref") != IMPORT_PREVIEW_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="import_preview_contract_ref_unsupported",
                severity="blocking",
                message=f"Import preview contract_ref must be {IMPORT_PREVIEW_CONTRACT_REF}.",
                evidence={"contract_ref": import_preview.get("contract_ref")},
            )
        )
    if _dict(import_preview.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="import_preview_not_ready_for_continuation",
                severity="blocking",
                message="SpecSpace real-idea answer import preview is not ready.",
                evidence={
                    "blocked_by": _list(_dict(import_preview.get("readiness")).get("blocked_by"))
                },
            )
        )
    findings.extend(
        _validate_import_preview_for_continuation(
            import_preview=import_preview,
            import_preview_path=import_preview_path,
            requests_path=requests_path,
            run_dir=run_dir,
        )
    )
    answer_set = _dict(_dict(import_preview.get("import_preview")).get("answer_set_candidate"))
    outputs: dict[str, Any] = {}
    status = "real_idea_answer_continuation_review_required"
    if not findings:
        authoring_report, published_outputs = _stage_materialization(
            clarification_requests=clarification_requests,
            requests_path=requests_path,
            answer_set=answer_set,
            import_preview_path=import_preview_path,
            answer_set_output=answer_set_output,
            validated_answers_output=validated_answers_output,
            run_dir=run_dir,
            stage=stage,
        )
        write_json(authoring_report, authoring_report_output)
        findings.extend(_list(authoring_report.get("findings")))
        outputs.update(
            {
                "authoring_report": _relative_ref(authoring_report_output),
                "answer_set": published_outputs.get("answer_set"),
                "validated_answers": published_outputs.get("validated_answers"),
                "clarified_intake_session": published_outputs.get("clarified_intake_session"),
                "rerun_report": published_outputs.get("rerun_report"),
            }
        )
        if _dict(authoring_report.get("readiness")).get("ready") is True and not findings:
            status = "real_idea_answer_continuation_ready"
    ready = status == "real_idea_answer_continuation_ready"
    return {
        "artifact_kind": CONTINUATION_REPORT_KIND,
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTINUATION_REPORT_CONTRACT_REF,
        "generated_at": _now_iso(),
        "stage": stage,
        "run_dir": _relative_ref(run_dir),
        "source_artifacts": {
            "specspace_real_idea_answer_import_preview": {
                "artifact_kind": import_preview.get("artifact_kind"),
                "contract_ref": import_preview.get("contract_ref"),
                "source_ref": _relative_ref(import_preview_path),
            },
            "clarification_requests": {
                "artifact_kind": clarification_requests.get("artifact_kind"),
                "contract_ref": clarification_requests.get("contract_ref"),
                "source_ref": _relative_ref(requests_path),
            },
        },
        "outputs": outputs,
        "readiness": {
            "ready": ready,
            "review_state": status,
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": (
                outputs.get("clarified_intake_session") or "clarified_user_idea_intake_session.json"
            ),
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "summary": {
            "status": status,
            "answer_count": _dict(import_preview.get("summary")).get("answer_count", 0),
            "accepted_answer_count": _dict(import_preview.get("summary")).get(
                "accepted_answer_count", 0
            ),
            "finding_count": len(findings),
        },
    }


def _preview(args: argparse.Namespace) -> int:
    run_dir_ref, run_dir = _repo_relative_path(args.run_dir, field="REAL_IDEA_SMOKE_RUN_DIR")
    _reject_reserved_run_dir(run_dir_ref)
    output = _guard_output_path(args.output, run_dir=run_dir, field="--output")
    preview = build_import_preview(
        specspace_answer_state=load_json(args.specspace_answers),
        state_path=args.specspace_answers,
        template=load_json(args.template),
        template_path=args.template,
        clarification_requests=load_json(args.requests),
        requests_path=args.requests,
        intake_session=load_json(args.intake_session),
        intake_session_path=args.intake_session,
        run_dir=run_dir,
        stage=args.stage,
    )
    write_json(preview, output)
    print(
        f"{preview['summary']['status']}: "
        f"{preview['summary']['accepted_answer_count']} accepted answers -> {_relative_ref(output)}"
    )
    if args.strict and _dict(preview.get("readiness")).get("ready") is not True:
        return 1
    return 0


def _materialize(args: argparse.Namespace) -> int:
    run_dir_ref, run_dir = _repo_relative_path(args.run_dir, field="REAL_IDEA_SMOKE_RUN_DIR")
    _reject_reserved_run_dir(run_dir_ref)
    output = _guard_output_path(args.output, run_dir=run_dir, field="--output")
    authoring_report_output = _guard_output_path(
        args.authoring_report,
        run_dir=run_dir,
        field="--authoring-report",
    )
    answer_set_output = _guard_output_path(
        args.answer_set_output,
        run_dir=run_dir,
        field="--answer-set-output",
    )
    validated_answers_output = _guard_output_path(
        args.validated_answers_output,
        run_dir=run_dir,
        field="--validated-answers-output",
    )
    report = build_continuation_report(
        import_preview=load_json(args.import_preview),
        import_preview_path=args.import_preview,
        clarification_requests=load_json(args.requests),
        requests_path=args.requests,
        answer_set_output=answer_set_output,
        validated_answers_output=validated_answers_output,
        authoring_report_output=authoring_report_output,
        run_dir=run_dir,
        stage=args.stage,
    )
    write_json(report, output)
    print(
        f"{report['summary']['status']}: "
        f"{report['summary']['accepted_answer_count']} accepted answers -> {_relative_ref(output)}"
    )
    if args.strict and _dict(report.get("readiness")).get("ready") is not True:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preview = sub.add_parser("preview")
    preview.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    preview.add_argument("--stage", choices=("intake",), default="intake")
    preview.add_argument(
        "--specspace-answers",
        type=Path,
        default=DEFAULT_RUN_DIR / "idea_to_spec_intake_clarification_answers.json",
    )
    preview.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_RUN_DIR / "real_idea_answer_template.json",
    )
    preview.add_argument(
        "--requests",
        type=Path,
        default=DEFAULT_RUN_DIR / "idea_intake_clarification_requests.json",
    )
    preview.add_argument(
        "--intake-session",
        type=Path,
        default=DEFAULT_RUN_DIR / "user_idea_intake_session.json",
    )
    preview.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RUN_DIR / "specspace_real_idea_answer_import_preview.json",
    )
    preview.add_argument("--strict", action="store_true")
    preview.set_defaults(func=_preview)

    materialize = sub.add_parser("materialize")
    materialize.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    materialize.add_argument("--stage", choices=("intake",), default="intake")
    materialize.add_argument(
        "--import-preview",
        type=Path,
        default=DEFAULT_RUN_DIR / "specspace_real_idea_answer_import_preview.json",
    )
    materialize.add_argument(
        "--requests",
        type=Path,
        default=DEFAULT_RUN_DIR / "idea_intake_clarification_requests.json",
    )
    materialize.add_argument(
        "--answer-set-output",
        type=Path,
        default=DEFAULT_RUN_DIR / "real_idea_answer_set.json",
    )
    materialize.add_argument(
        "--validated-answers-output",
        type=Path,
        default=DEFAULT_RUN_DIR / "idea_intake_clarification_answers.json",
    )
    materialize.add_argument(
        "--authoring-report",
        type=Path,
        default=DEFAULT_RUN_DIR / "real_idea_answer_authoring_report.json",
    )
    materialize.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RUN_DIR / "real_idea_answer_continuation_report.json",
    )
    materialize.add_argument("--strict", action="store_true")
    materialize.set_defaults(func=_materialize)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
