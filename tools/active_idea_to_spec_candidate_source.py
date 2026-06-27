"""Build the active idea-to-spec candidate source artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0155"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.active-candidate-source.v0.1"
CONFIG_CONTRACT_REF = "specgraph.idea-to-spec.active-candidate-source-config.v0.1"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "active_idea_to_spec_candidate.json"
DEFAULT_ARTIFACT_REFS = {
    "intake": "runs/idea_event_storming_intake.json",
    "candidate_graph": "runs/candidate_spec_graph.json",
    "pre_sib": "runs/pre_sib_coherence_report.json",
    "repair_loop": "runs/candidate_repair_loop_report.json",
    "materialization": "runs/candidate_spec_materialization_report.json",
    "promotion_gate": "runs/idea_to_spec_promotion_gate.json",
}

EXPECTED_ARTIFACTS = {
    "intake": (
        "idea_event_storming_intake",
        "specgraph.idea-to-spec.event-storming-intake.v0.1",
    ),
    "candidate_graph": (
        "candidate_spec_graph",
        "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
    ),
    "pre_sib": (
        "pre_sib_coherence_report",
        "specgraph.idea-to-spec.pre-sib-coherence-report.v0.1",
    ),
    "repair_loop": (
        "candidate_repair_loop_report",
        "specgraph.idea-to-spec.candidate-repair-loop.v0.1",
    ),
    "materialization": (
        "candidate_spec_materialization_report",
        "specgraph.idea-to-spec.candidate-spec-materialization.v0.1",
    ),
    "promotion_gate": (
        "idea_to_spec_promotion_gate",
        "specgraph.idea-to-spec.promotion-gate.v0.1",
    ),
}
READY_FIELD_BY_ARTIFACT = {
    "intake": "candidate_graph_readiness",
    "candidate_graph": "pre_sib_readiness",
    "pre_sib": "readiness",
    "repair_loop": "readiness",
    "materialization": "readiness",
    "promotion_gate": "readiness",
}
FINAL_READY_ARTIFACTS = ("repair_loop", "materialization", "promotion_gate")
CANDIDATE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
PRODUCT_SOURCE_REF_RE = re.compile(
    r"^product://(?P<candidate_id>[a-z0-9][a-z0-9-]{1,62}[a-z0-9])(?:/|$)"
)
REQUIRED_CANDIDATE_VALUES = {
    "source_mode": "active_candidate",
    "workflow_lane": "product_idea_to_spec",
    "governance_profile": "product_workspace",
    "target_repository_role": "product_spec_workspace",
    "authority_profile": "workspace_owner_controlled",
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


def _slug_to_project_id(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.split("-") if part)


def _slug_to_display_name(value: str) -> str:
    return " ".join(part[:1].upper() + part[1:] for part in value.split("-") if part)


def _slug_to_domain_ref(value: str) -> str:
    return f"domain.{value.replace('-', '_')}"


def _relative_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _repo_path(value: object, *, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty relative path")
    rel = PurePosixPath(value.strip())
    if rel.is_absolute() or ".." in rel.parts or rel.as_posix() in {"", "."}:
        raise ValueError(f"{field} must be a safe repository-relative path")
    return ROOT / rel.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        "source": "active_idea_to_spec_candidate_source",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
    }


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_intent_text_published": False,
        "raw_model_output_published": False,
        "raw_operator_note_published": False,
        "raw_prompt_published": False,
    }


def _default_config() -> dict[str, Any]:
    return {
        "artifact_kind": "active_idea_to_spec_candidate_source_config",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": CONFIG_CONTRACT_REF,
    }


def _config_findings(config: dict[str, Any], *, config_provided: bool) -> list[dict[str, Any]]:
    if not config_provided:
        return []
    invalid = []
    if config.get("artifact_kind") != "active_idea_to_spec_candidate_source_config":
        invalid.append("artifact_kind")
    if config.get("schema_version") != SCHEMA_VERSION:
        invalid.append("schema_version")
    if config.get("contract_ref") != CONFIG_CONTRACT_REF:
        invalid.append("contract_ref")
    if not invalid:
        return []
    return [
        _finding(
            finding_id="active_candidate_config_contract_invalid",
            severity="review_required",
            message="Active candidate source requires a valid config contract.",
            evidence={"invalid_fields": invalid},
        )
    ]


def _candidate_metadata(candidate: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    normalized: dict[str, Any] = {}
    for field, expected in REQUIRED_CANDIDATE_VALUES.items():
        observed = candidate.get(field)
        if observed != expected:
            findings.append(
                _finding(
                    finding_id=f"candidate_{field}_unsupported",
                    severity="review_required",
                    message=f"Active product candidate source requires {field}={expected!r}.",
                    evidence={"expected": expected, "observed": observed},
                )
            )
        normalized[field] = observed
    candidate_id_raw = candidate.get("candidate_id")
    candidate_id = _text(candidate_id_raw)
    if not candidate_id:
        findings.append(
            _finding(
                finding_id="candidate_candidate_id_missing",
                severity="review_required",
                message="Active product candidate source requires a candidate_id.",
            )
        )
    elif candidate_id_raw != candidate_id:
        findings.append(
            _finding(
                finding_id="candidate_candidate_id_not_normalized",
                severity="review_required",
                message="Active product candidate source candidate_id must not need trimming.",
                evidence={"candidate_id": candidate_id_raw, "normalized": candidate_id},
            )
        )
    elif not CANDIDATE_ID_RE.fullmatch(candidate_id):
        findings.append(
            _finding(
                finding_id="candidate_candidate_id_invalid",
                severity="review_required",
                message=(
                    "Active product candidate source candidate_id must be a stable lowercase slug."
                ),
                evidence={"candidate_id": candidate_id},
            )
        )
    normalized["candidate_id"] = candidate_id
    display_name_raw = candidate.get("display_name")
    display_name = _text(display_name_raw)
    if not display_name:
        findings.append(
            _finding(
                finding_id="candidate_display_name_missing",
                severity="review_required",
                message="Active candidate source requires a display name.",
            )
        )
    elif display_name_raw != display_name:
        findings.append(
            _finding(
                finding_id="candidate_display_name_not_normalized",
                severity="review_required",
                message="Active product candidate source display_name must not need trimming.",
                evidence={"display_name": display_name_raw, "normalized": display_name},
            )
        )
    normalized["display_name"] = display_name
    public_route_raw = candidate.get("public_route")
    public_route = _text(public_route_raw)
    if not public_route:
        findings.append(
            _finding(
                finding_id="candidate_public_route_missing",
                severity="review_required",
                message="Active product candidate source requires a public_route.",
            )
        )
    elif public_route_raw != public_route:
        findings.append(
            _finding(
                finding_id="candidate_public_route_not_normalized",
                severity="review_required",
                message="Active product candidate source public_route must not need trimming.",
                evidence={"public_route": public_route_raw, "normalized": public_route},
            )
        )
    elif (
        public_route == "/"
        or not public_route.startswith("/")
        or "//" in public_route
        or "?" in public_route
        or "#" in public_route
    ):
        findings.append(
            _finding(
                finding_id="candidate_public_route_invalid",
                severity="review_required",
                message=(
                    "Active product candidate source public_route must be a non-root "
                    "absolute path without query or fragment."
                ),
                evidence={"public_route": public_route},
            )
        )
    else:
        route_segments = [segment for segment in public_route.split("/") if segment]
        if any(segment in {".", ".."} for segment in route_segments):
            findings.append(
                _finding(
                    finding_id="candidate_public_route_unsafe_segment",
                    severity="review_required",
                    message=(
                        "Active product candidate source public_route must not contain "
                        "dot or traversal segments."
                    ),
                    evidence={"public_route": public_route},
                )
            )
        elif any(unquote(segment) in {".", ".."} for segment in route_segments):
            findings.append(
                _finding(
                    finding_id="candidate_public_route_unsafe_segment",
                    severity="review_required",
                    message=(
                        "Active product candidate source public_route must not contain "
                        "encoded dot or traversal segments."
                    ),
                    evidence={"public_route": public_route},
                )
            )
    normalized["public_route"] = public_route
    return normalized, findings


def _candidate_from_intake_artifact(intake: dict[str, Any]) -> tuple[dict[str, Any], str]:
    source_intake = _dict(intake.get("source_intake"))
    workspace = _dict(source_intake.get("workspace"))
    source_ref = _text(intake.get("source_ref"))
    source_match = PRODUCT_SOURCE_REF_RE.match(source_ref)
    source_candidate_id = source_match.group("candidate_id") if source_match else ""
    candidate_id = _text(workspace.get("candidate_id"), source_candidate_id)
    if _text(workspace.get("candidate_id")):
        identity_source = "intake.source_intake.workspace"
    elif source_candidate_id:
        identity_source = "intake.source_ref"
    else:
        identity_source = "unresolved"
    return (
        {
            **REQUIRED_CANDIDATE_VALUES,
            "candidate_id": candidate_id,
            "display_name": _text(
                workspace.get("display_name"),
                _slug_to_display_name(candidate_id),
            ),
            "public_route": _text(
                workspace.get("public_route"),
                f"/{candidate_id}" if candidate_id else "",
            ),
        },
        identity_source,
    )


def _candidate_for_config(
    *,
    config: dict[str, Any],
    artifacts: dict[str, tuple[Path, dict[str, Any]]],
) -> tuple[dict[str, Any], str]:
    derived, identity_source = _candidate_from_intake_artifact(
        artifacts.get("intake", (None, {}))[1]
    )
    explicit = _dict(config.get("candidate"))
    if any(field in explicit for field in ("candidate_id", "public_route")):
        identity_source = "config_override"
    return {**derived, **explicit}, identity_source


def _artifact_readiness(artifact_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _dict(payload.get(READY_FIELD_BY_ARTIFACT[artifact_key]))


def _source_artifact(
    *,
    artifact_key: str,
    path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    readiness = _artifact_readiness(artifact_key, payload)
    return {
        "artifact_key": artifact_key,
        "artifact_kind": payload.get("artifact_kind"),
        "contract_ref": payload.get("contract_ref"),
        "proposal_id": payload.get("proposal_id"),
        "source_ref": _relative_ref(path),
        "sha256": _sha256(path),
        "readiness": readiness,
        "summary": _dict(payload.get("summary")),
    }


def _artifact_refs_for_config(
    config: dict[str, Any],
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    raw_artifacts = _dict(config.get("artifacts"))
    if raw_artifacts:
        artifact_paths_source = _text(config.get("_artifact_paths_source"), "config")
        expected_keys = set(EXPECTED_ARTIFACTS)
        observed_keys = set(raw_artifacts)
        findings = []
        missing_keys = sorted(expected_keys - observed_keys)
        unknown_keys = sorted(observed_keys - expected_keys)
        if missing_keys:
            findings.append(
                _finding(
                    finding_id="active_candidate_config_artifacts_incomplete",
                    severity="review_required",
                    message="Explicit active candidate config must list every source artifact.",
                    evidence={"missing_keys": missing_keys},
                )
            )
        if unknown_keys:
            findings.append(
                _finding(
                    finding_id="active_candidate_config_artifacts_unknown",
                    severity="review_required",
                    message="Explicit active candidate config contains unknown artifact keys.",
                    evidence={"unknown_keys": unknown_keys},
                )
            )
        return {**DEFAULT_ARTIFACT_REFS, **raw_artifacts}, artifact_paths_source, findings
    return dict(DEFAULT_ARTIFACT_REFS), "defaults", []


def _load_source_artifacts(
    artifact_refs: dict[str, Any],
) -> tuple[dict[str, tuple[Path, dict[str, Any]]], list[dict[str, Any]]]:
    artifacts: dict[str, tuple[Path, dict[str, Any]]] = {}
    findings: list[dict[str, Any]] = []
    for artifact_key, (expected_kind, expected_contract) in EXPECTED_ARTIFACTS.items():
        try:
            path = _repo_path(artifact_refs.get(artifact_key), field=f"artifacts.{artifact_key}")
            payload = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            findings.append(
                _finding(
                    finding_id=f"{artifact_key}_unavailable",
                    severity="review_required",
                    message=f"Active candidate source requires {artifact_key} artifact.",
                    evidence={"error": str(exc)},
                )
            )
            continue
        artifacts[artifact_key] = (path, payload)
        if payload.get("artifact_kind") != expected_kind:
            findings.append(
                _finding(
                    finding_id=f"{artifact_key}_wrong_artifact_kind",
                    severity="review_required",
                    message=f"{artifact_key} must be {expected_kind}.",
                    evidence={"artifact_kind": payload.get("artifact_kind")},
                )
            )
        if payload.get("contract_ref") != expected_contract:
            findings.append(
                _finding(
                    finding_id=f"{artifact_key}_contract_ref_unsupported",
                    severity="review_required",
                    message=f"{artifact_key} contract_ref must be {expected_contract}.",
                    evidence={"contract_ref": payload.get("contract_ref")},
                )
            )
        for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
            if payload.get(field) is not False:
                findings.append(
                    _finding(
                        finding_id=f"{artifact_key}_authority_expanded",
                        severity="review_required",
                        message=f"{artifact_key} {field} must be false.",
                        evidence={field: payload.get(field)},
                    )
                )
    return artifacts, findings


def _active_frame_findings(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    frame = _dict(candidate_graph.get("active_frame"))
    missing = [
        field
        for field in ("ontology_refs", "domain_refs", "context_refs")
        if not _text_list(frame.get(field))
    ]
    if not _text(frame.get("project")):
        missing.append("project")
    if not missing:
        return []
    return [
        _finding(
            finding_id="active_candidate_frame_incomplete",
            severity="review_required",
            message="Active candidate source requires ontology/domain/context/project frame.",
            evidence={"missing": missing},
        )
    ]


def _candidate_artifact_match_findings(
    *,
    candidate: dict[str, Any],
    candidate_graph: dict[str, Any],
) -> list[dict[str, Any]]:
    candidate_id = _text(candidate.get("candidate_id"))
    if not CANDIDATE_ID_RE.fullmatch(candidate_id):
        return []
    frame = _dict(candidate_graph.get("active_frame"))
    expected_project = _slug_to_project_id(candidate_id)
    observed_project = _text(frame.get("project"))
    expected_domain_ref = _slug_to_domain_ref(candidate_id)
    observed_domain_refs = _text_list(frame.get("domain_refs"))
    findings: list[dict[str, Any]] = []
    if observed_project != expected_project:
        findings.append(
            _finding(
                finding_id="active_candidate_project_mismatch",
                severity="review_required",
                message="Candidate graph active_frame.project must match candidate_id.",
                evidence={
                    "candidate_id": candidate_id,
                    "expected_project": expected_project,
                    "observed_project": observed_project,
                },
            )
        )
    if expected_domain_ref not in observed_domain_refs:
        findings.append(
            _finding(
                finding_id="active_candidate_domain_mismatch",
                severity="review_required",
                message="Candidate graph active_frame.domain_refs must include candidate domain.",
                evidence={
                    "candidate_id": candidate_id,
                    "expected_domain_ref": expected_domain_ref,
                    "observed_domain_refs": observed_domain_refs,
                },
            )
        )
    source_ref = _text(candidate_graph.get("source_ref"))
    if source_ref and not source_ref.startswith(f"product://{candidate_id}/"):
        findings.append(
            _finding(
                finding_id="active_candidate_source_ref_mismatch",
                severity="review_required",
                message="Candidate graph source_ref must belong to candidate_id.",
                evidence={"candidate_id": candidate_id, "source_ref": source_ref},
            )
        )
    source_intake = _dict(candidate_graph.get("source_intake"))
    intake_ref = _text(source_intake.get("source_ref"))
    if intake_ref and not intake_ref.startswith(f"product://{candidate_id}/"):
        findings.append(
            _finding(
                finding_id="active_candidate_intake_ref_mismatch",
                severity="review_required",
                message="Candidate graph source_intake.source_ref must belong to candidate_id.",
                evidence={"candidate_id": candidate_id, "source_ref": intake_ref},
            )
        )
    return findings


def _artifact_chain_findings(
    artifacts: dict[str, tuple[Path, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for artifact_key in ("intake", "candidate_graph", *FINAL_READY_ARTIFACTS):
        payload = artifacts.get(artifact_key, (None, {}))[1]
        readiness = _artifact_readiness(artifact_key, payload)
        if readiness.get("ready") is not True:
            findings.append(
                _finding(
                    finding_id=f"{artifact_key}_not_ready",
                    severity="review_required",
                    message=f"{artifact_key} must be ready for active candidate publishing.",
                    evidence={"readiness": readiness},
                )
            )

    pre_sib = artifacts.get("pre_sib", (None, {}))[1]
    materialization = artifacts.get("materialization", (None, {}))[1]
    promotion_gate = artifacts.get("promotion_gate", (None, {}))[1]
    if _artifact_readiness("pre_sib", pre_sib).get("ready") is not True:
        if (
            materialization.get("materialization_source") == "repair_loop_preview"
            and _artifact_readiness("promotion_gate", promotion_gate).get("ready") is True
        ):
            warnings.append(
                _finding(
                    finding_id="pre_sib_findings_repaired_by_preview",
                    severity="warning",
                    message=(
                        "Original pre-SIB report is not ready, but the handoff uses a "
                        "ready repair-loop preview."
                    ),
                    evidence={"readiness": _artifact_readiness("pre_sib", pre_sib)},
                )
            )
        else:
            findings.append(
                _finding(
                    finding_id="pre_sib_not_ready_without_repair_preview",
                    severity="review_required",
                    message="pre_sib must be ready or repaired by a ready materialization preview.",
                    evidence={"readiness": _artifact_readiness("pre_sib", pre_sib)},
                )
            )

    for artifact_key in ("materialization", "promotion_gate"):
        payload = artifacts.get(artifact_key, (None, {}))[1]
        if payload.get("source_mode") == "public_placeholder" or payload.get("placeholder_reason"):
            findings.append(
                _finding(
                    finding_id=f"{artifact_key}_is_public_placeholder",
                    severity="review_required",
                    message=f"{artifact_key} must be a real active candidate artifact.",
                    evidence={
                        "source_mode": payload.get("source_mode"),
                        "placeholder_reason": payload.get("placeholder_reason"),
                    },
                )
            )
    return findings, warnings


def build_active_idea_to_spec_candidate_source(
    config: dict[str, Any] | None = None,
    *,
    config_path: Path | None = None,
    loaded_artifacts: dict[str, tuple[Path, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    config_provided = config is not None
    config = config if config is not None else _default_config()
    if loaded_artifacts is None:
        artifact_refs, artifact_paths_source, artifact_ref_findings = _artifact_refs_for_config(
            config
        )
        artifacts, artifact_findings = _load_source_artifacts(artifact_refs)
    else:
        artifact_paths_source = _text(config.get("_artifact_paths_source"), "loaded_artifacts")
        artifact_ref_findings = []
        artifacts = dict(loaded_artifacts)
        missing_artifact_keys = sorted(set(EXPECTED_ARTIFACTS) - set(artifacts))
        artifact_findings = [
            _finding(
                finding_id=f"{artifact_key}_unavailable",
                severity="review_required",
                message=f"Active candidate source requires {artifact_key} artifact.",
                evidence={"error": "loaded artifact missing"},
            )
            for artifact_key in missing_artifact_keys
        ]
    candidate, identity_source = _candidate_for_config(config=config, artifacts=artifacts)
    normalized_candidate, candidate_findings = _candidate_metadata(candidate)
    chain_findings, chain_warnings = _artifact_chain_findings(artifacts)
    candidate_graph = artifacts.get("candidate_graph", (None, {}))[1]
    findings = (
        _config_findings(config, config_provided=config_provided)
        + candidate_findings
        + artifact_ref_findings
        + artifact_findings
        + _active_frame_findings(candidate_graph)
        + _candidate_artifact_match_findings(
            candidate=normalized_candidate,
            candidate_graph=candidate_graph,
        )
        + chain_findings
    )
    ready = not findings
    source_artifacts = {
        artifact_key: _source_artifact(artifact_key=artifact_key, path=path, payload=payload)
        for artifact_key, (path, payload) in artifacts.items()
    }
    active_frame = _dict(candidate_graph.get("active_frame"))
    materialization_summary = _dict(artifacts.get("materialization", (None, {}))[1].get("summary"))
    promotion_summary = _dict(artifacts.get("promotion_gate", (None, {}))[1].get("summary"))
    return {
        "artifact_kind": "active_idea_to_spec_candidate",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "source_mode": normalized_candidate.get("source_mode", "unknown"),
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "config_source": {
            "artifact_kind": config.get("artifact_kind"),
            "contract_ref": config.get("contract_ref"),
            "source_ref": _relative_ref(config_path) if config_path is not None else None,
            "required": False,
            "mode": _text(
                config.get("_config_source_mode"),
                "config" if config_provided else "artifact_defaults",
            ),
        },
        "source_derivation": {
            "identity_source": identity_source,
            "artifact_paths_source": artifact_paths_source,
            "config_required": False,
            "standard_artifact_paths": dict(DEFAULT_ARTIFACT_REFS),
        },
        "candidate": {
            "candidate_id": normalized_candidate.get("candidate_id"),
            "display_name": normalized_candidate.get("display_name"),
            "workflow_lane": normalized_candidate.get("workflow_lane"),
            "public_route": normalized_candidate.get("public_route"),
            "governance_profile": normalized_candidate.get("governance_profile"),
            "target_repository_role": normalized_candidate.get("target_repository_role"),
            "authority_profile": normalized_candidate.get("authority_profile"),
        },
        "active_frame": active_frame,
        "source_artifacts": source_artifacts,
        "platform_handoff_surfaces": {
            "candidate_spec_materialization_report.json": {
                "source_ref": source_artifacts.get("materialization", {}).get("source_ref"),
                "ready": _artifact_readiness(
                    "materialization", artifacts.get("materialization", (None, {}))[1]
                ).get("ready")
                is True,
            },
            "idea_to_spec_promotion_gate.json": {
                "source_ref": source_artifacts.get("promotion_gate", {}).get("source_ref"),
                "ready": _artifact_readiness(
                    "promotion_gate", artifacts.get("promotion_gate", (None, {}))[1]
                ).get("ready")
                is True,
            },
        },
        "readiness": {
            "ready": ready,
            "review_state": "active_candidate_ready"
            if ready
            else "active_candidate_review_required",
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "SpecSpace product workspace route"
            if ready
            else "repair active candidate source before public handoff",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "warnings": chain_warnings,
        "summary": {
            "status": "active_candidate_ready" if ready else "active_candidate_review_required",
            "candidate_id": normalized_candidate.get("candidate_id"),
            "workspace_route": normalized_candidate.get("public_route"),
            "source_artifact_count": len(source_artifacts),
            "finding_count": len(findings),
            "warning_count": len(chain_warnings),
            "materialized_file_count": materialization_summary.get("materialized_file_count", 0),
            "promotion_path_count": promotion_summary.get("promotion_path_count", 0),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, type=Path)
    parser.add_argument("--intake", default=None)
    parser.add_argument("--candidate-graph", default=None)
    parser.add_argument("--pre-sib", default=None)
    parser.add_argument("--repair-loop", default=None)
    parser.add_argument("--materialization", default=None)
    parser.add_argument("--promotion-gate", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def _artifact_args(args: argparse.Namespace) -> dict[str, str]:
    return {
        key: value
        for key, value in {
            "intake": args.intake,
            "candidate_graph": args.candidate_graph,
            "pre_sib": args.pre_sib,
            "repair_loop": args.repair_loop,
            "materialization": args.materialization,
            "promotion_gate": args.promotion_gate,
        }.items()
        if value is not None
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_json(args.config) if args.config is not None else None
    artifact_args = _artifact_args(args)
    if artifact_args:
        config = config if config is not None else _default_config()
        config = {
            **config,
            "artifacts": {**_dict(config.get("artifacts")), **artifact_args},
            "_artifact_paths_source": "arguments",
            "_config_source_mode": "artifact_arguments"
            if args.config is None
            else "config_with_artifact_arguments",
        }
    artifact = build_active_idea_to_spec_candidate_source(config, config_path=args.config)
    write_json(artifact, args.output)
    print(
        f"{artifact['readiness']['review_state']}: "
        f"{artifact['summary']['source_artifact_count']} artifacts"
    )
    if args.strict and not artifact["readiness"]["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
