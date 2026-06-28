from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

DEFAULT_OUTPUT_DIR = Path("dist/specgraph-public")
PUBLISHED_ROOTS = ("specs", "runs")
REQUIRED_RUN_SURFACES = (
    "graph_dashboard.json",
    "graph_backlog_projection.json",
    "graph_next_moves.json",
    "implementation_work_index.json",
    "spec_activity_feed.json",
    "supervisor_executor_adapter_index.json",
    "agent_surface_index.json",
    "known_agent_passport_index.json",
    "agent_passport_verification_report.json",
    "agent_verification_gap_index.json",
    "agent_runtime_enforcement_evidence_index.json",
    "agent_runtime_enforcement_evidence/supervisor-executor-adapter-smoke.json",
    "agent_runtime_enforcement_evidence/supervisor-executor-adapter-redacted-local-summary.json",
    "external_consumer_evidence_index.json",
    "ontology_semantic_review_surface.json",
    "ontology_review_dashboard.json",
    "ontology_decision_import_preview.json",
    "ontology_package_index.json",
    "ontology_gap_review_workflow.json",
    "legacy_spec_ontology_backfill_plan.json",
    "ontology_owner_decision_import_v2.json",
    "spec_ontology_binding_index.json",
    "spec_ontology_validation_report.json",
    "specauthor_invocation_artifact.json",
    "specauthor_invocation_artifact_contract_report.json",
    "specauthor_authoring_flow_report.json",
    "candidate_spec_materialization_report.json",
    "idea_to_spec_promotion_gate.json",
    "idea_maturity_metrics_report.json",
)
PLATFORM_HANDOFF_RUN_SURFACES = (
    "candidate_spec_materialization_report.json",
    "idea_to_spec_promotion_gate.json",
)
ACTIVE_IDEA_TO_SPEC_CANDIDATE_SURFACE = "active_idea_to_spec_candidate.json"
CANDIDATE_APPROVAL_DECISION_SURFACE = "candidate_approval_decision.json"
PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH_ENV = "PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH"
PLATFORM_HANDOFF_PLACEHOLDER_REASON = "no_active_candidate"
PLATFORM_HANDOFF_MATERIALIZATION_CONTRACT_REF = (
    "specgraph.idea-to-spec.candidate-spec-materialization.v0.1"
)
PLATFORM_HANDOFF_PROMOTION_GATE_CONTRACT_REF = "specgraph.idea-to-spec.promotion-gate.v0.1"
ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONTRACT_REF = "specgraph.idea-to-spec.active-candidate-source.v0.1"
CANDIDATE_APPROVAL_DECISION_CONTRACT_REF = "specgraph.idea-to-spec.candidate-approval-decision.v0.1"
LOCAL_ONLY_RUN_SURFACES = {
    "local_operator_executor_readiness.json",
    "local_operator_executor_smoke.json",
    "local_operator_executor_task_smoke.json",
    "local_operator_executor_report_contract.json",
    "local_operator_executor_report.json",
    "local_operator_executor_report_review_packet.json",
    "local_operator_executor_analysis_report_review_outcome.json",
    "local_operator_executor_analysis_report_followup_packet.json",
    "local_operator_executor_analysis_report_followup_decision.json",
    "local_operator_executor_proposal_draft_request.json",
    "local_operator_executor_proposal_draft_candidate.json",
    "local_operator_executor_followup_proposal_draft_candidate.json",
    "local_operator_executor_proposal_promotion_packet.json",
    "local_operator_executor_proposal_materialization_report.json",
    "local_operator_executor_public_proposal_materialization_report.json",
    "ontology_term_binding_gate_report.json",
}
LOCAL_ONLY_RUN_PREFIXES = ("local_operator_", "idea_event_storming_seed")
JUNK_FILENAMES = {".DS_Store", ".gitkeep"}
JUNK_DIRNAMES = {"__pycache__", ".pytest_cache", ".ruff_cache"}
LOCAL_PATH_RE = re.compile(
    r"(?P<prefix>(?:/Users/|/home/runner/|/github/workspace/|/private/var/|"
    r"/var/folders/|/tmp/))[^\s\"'<>]+"
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(?:^|[^A-Z0-9_])(?:[A-Z0-9_]*_)?API_KEY\s*=\s*[^\s\"']+"),
    re.compile(r"(?i)\"(?:api_key|authorization|password)\"\s*:\s*\"[^\"\n]+\""),
)
ONTOLOGY_PUBLIC_REVIEW_SURFACES = {
    "runs/ontology_semantic_review_surface.json",
    "runs/ontology_review_dashboard.json",
    "runs/ontology_decision_import_preview.json",
}
DEMO_ONTOLOGY_FIXTURE_MARKERS = (
    "examcalc",
    "edu.university.examcalc",
    "ExamPolicy",
    "CASFunction",
    "allows policy",
    "ontology-gap-examcalc",
)


@dataclass
class PublishFile:
    path: str
    root: str
    size_bytes: int
    sha256: str


@dataclass
class BuildResult:
    output_dir: Path
    manifest_path: Path
    checksums_path: Path
    manifest: dict[str, object]
    copied_files: list[PublishFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    redacted_local_path_occurrences: int = 0


class PublishBundleError(RuntimeError):
    pass


AGENT_PASSPORT_PUBLISH_SURFACES = (
    "supervisor_executor_adapter_index.json",
    "agent_passport_verification_report.json",
    "agent_verification_gap_index.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_git_value(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return value or None


def should_skip_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if path.name in JUNK_FILENAMES:
        return True
    return any(part in JUNK_DIRNAMES for part in rel.parts)


def has_symlink_component(path: Path, stop_at: Path) -> bool:
    current = path
    while current != stop_at:
        if current.is_symlink():
            return True
        current = current.parent
    return False


def iter_publish_sources(repo_root: Path) -> Iterable[tuple[str, Path, PurePosixPath]]:
    active_candidate_ready = is_publishable_active_candidate_source(repo_root)
    approval_ready = is_publishable_candidate_approval_decision(repo_root)
    for root_name in PUBLISHED_ROOTS:
        source_root = repo_root / root_name
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*")):
            if (
                has_symlink_component(path, source_root)
                or not path.is_file()
                or should_skip_file(path, repo_root)
            ):
                continue
            rel = PurePosixPath(root_name, path.relative_to(source_root).as_posix())
            if root_name == "runs":
                run_rel = rel.relative_to("runs").as_posix()
                if is_local_only_run_path(run_rel):
                    continue
                if run_rel == ACTIVE_IDEA_TO_SPEC_CANDIDATE_SURFACE and not active_candidate_ready:
                    continue
                if run_rel == CANDIDATE_APPROVAL_DECISION_SURFACE and not approval_ready:
                    continue
            yield root_name, path, rel


def is_local_only_run_path(run_rel: str) -> bool:
    return run_rel in LOCAL_ONLY_RUN_SURFACES or run_rel.startswith(LOCAL_ONLY_RUN_PREFIXES)


def safe_repo_relative_path(value: object, *, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip():
        raise PublishBundleError(f"{field} must be a non-empty relative path")
    rel = PurePosixPath(value.strip())
    if rel.is_absolute() or ".." in rel.parts:
        raise PublishBundleError(f"unsafe {field}: {value}")
    if rel.as_posix() in {"", "."}:
        raise PublishBundleError(f"unsafe {field}: {value}")
    return rel


def ontology_materialized_ir_refs(repo_root: Path) -> list[PurePosixPath]:
    package_index_path = repo_root / "runs" / "ontology_package_index.json"
    if not package_index_path.is_file():
        return []
    try:
        package_index = json.loads(package_index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PublishBundleError(f"malformed ontology package index: {exc}") from exc
    if not isinstance(package_index, dict):
        raise PublishBundleError("malformed ontology package index: expected object")

    packages = package_index.get("packages")
    if packages is None:
        return []
    if not isinstance(packages, list):
        raise PublishBundleError("ontology_package_index.packages must be a list")

    refs: list[PurePosixPath] = []
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            raise PublishBundleError(f"ontology_package_index.packages[{index}] must be an object")
        raw_ref = package.get("materialized_ir")
        if raw_ref is None:
            continue
        rel = safe_repo_relative_path(
            raw_ref,
            field=f"ontology_package_index.packages[{index}].materialized_ir",
        )
        if rel.suffix != ".json":
            raise PublishBundleError(f"ontology materialized IR must be JSON: {rel.as_posix()}")
        if rel.as_posix() not in {ref.as_posix() for ref in refs}:
            refs.append(rel)
    return refs


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PublishBundleError(f"unsupported non-utf8 artifact: {path}") from exc


def validate_json_artifact(path: Path, text: str) -> None:
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        raise PublishBundleError(f"malformed JSON artifact: {path}: {exc}") from exc


def redact_local_paths(text: str) -> tuple[str, int]:
    return LOCAL_PATH_RE.subn("$LOCAL_PATH", text)


def detect_secret_like_content(path: PurePosixPath, text: str) -> list[str]:
    findings: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"secret-like content in {path}")
    return findings


def detect_demo_ontology_fixture_content(path: PurePosixPath, text: str) -> list[str]:
    rel = path.as_posix()
    if rel not in ONTOLOGY_PUBLIC_REVIEW_SURFACES and not (
        rel.startswith("runs/ontology") and rel.endswith(".json")
    ):
        return []
    leaked_markers = sorted(marker for marker in DEMO_ONTOLOGY_FIXTURE_MARKERS if marker in text)
    if not leaked_markers:
        return []
    return [f"demo ontology fixture content in {path}: {', '.join(leaked_markers)}"]


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def write_json_artifact(path: Path, payload: dict[str, object]) -> None:
    write_text_atomic(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_required_surfaces(output_dir: Path) -> dict[str, bool]:
    return {surface: (output_dir / "runs" / surface).is_file() for surface in REQUIRED_RUN_SURFACES}


def load_published_run_json(output_dir: Path, relative_path: str) -> dict[str, object]:
    path = output_dir / "runs" / relative_path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PublishBundleError(
            f"missing Agent Passport publish surface: {relative_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise PublishBundleError(
            f"malformed Agent Passport publish surface: {relative_path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise PublishBundleError(
            f"malformed Agent Passport publish surface: {relative_path}: expected object"
        )
    return data


def load_run_json_if_present(repo_root: Path, relative_path: str) -> dict[str, object] | None:
    path = repo_root / "runs" / relative_path
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def require_summary_value(
    *,
    summary: dict[str, object],
    field: str,
    expected: object,
    artifact_path: str,
) -> None:
    observed = summary.get(field)
    if observed != expected:
        raise PublishBundleError(
            f"Agent Passport static publish requires {artifact_path}.summary.{field} "
            f"to be {expected!r}; got {observed!r}"
        )


def validate_agent_passport_publish_surfaces(output_dir: Path) -> None:
    artifacts = {
        relative_path: load_published_run_json(output_dir, relative_path)
        for relative_path in AGENT_PASSPORT_PUBLISH_SURFACES
    }
    for relative_path, artifact in artifacts.items():
        summary = artifact.get("summary")
        if not isinstance(summary, dict):
            raise PublishBundleError(
                f"Agent Passport static publish requires {relative_path}.summary to be an object"
            )
        require_summary_value(
            summary=summary,
            field="agent_passport_cli_status",
            expected="available",
            artifact_path=relative_path,
        )

    verification_summary = artifacts["agent_passport_verification_report.json"]["summary"]
    assert isinstance(verification_summary, dict)
    entry_count = verification_summary.get("entry_count")
    valid_count = verification_summary.get("valid_count")
    if not isinstance(entry_count, int) or entry_count <= 0:
        raise PublishBundleError(
            "Agent Passport static publish requires "
            "agent_passport_verification_report.json.summary.entry_count > 0"
        )
    if valid_count != entry_count:
        raise PublishBundleError(
            "Agent Passport static publish requires all report-only passport validations "
            f"to be valid; got valid_count={valid_count!r}, entry_count={entry_count!r}"
        )
    require_summary_value(
        summary=verification_summary,
        field="tool_unavailable_count",
        expected=0,
        artifact_path="agent_passport_verification_report.json",
    )

    gap_summary = artifacts["agent_verification_gap_index.json"]["summary"]
    assert isinstance(gap_summary, dict)
    require_summary_value(
        summary=gap_summary,
        field="verification_tool_unavailable_count",
        expected=0,
        artifact_path="agent_verification_gap_index.json",
    )
    require_summary_value(
        summary=gap_summary,
        field="verification_not_attempted_count",
        expected=0,
        artifact_path="agent_verification_gap_index.json",
    )


def build_manifest(
    *,
    repo_root: Path,
    output_dir: Path,
    copied_files: list[PublishFile],
    warnings: list[str],
    redacted_local_path_occurrences: int,
) -> dict[str, object]:
    root_summary: dict[str, dict[str, int]] = {
        root: {"file_count": 0, "byte_count": 0} for root in PUBLISHED_ROOTS
    }
    for file_info in copied_files:
        root_info = root_summary.setdefault(file_info.root, {"file_count": 0, "byte_count": 0})
        root_info["file_count"] += 1
        root_info["byte_count"] += file_info.size_bytes

    required_surfaces = ensure_required_surfaces(output_dir)
    active_candidate_source = active_candidate_source_manifest_entry(repo_root)
    platform_handoff_surfaces = {
        surface: {
            "path": f"runs/{surface}",
            "present": required_surfaces.get(surface) is True,
        }
        for surface in PLATFORM_HANDOFF_RUN_SURFACES
    }
    platform_handoff_surfaces[ACTIVE_IDEA_TO_SPEC_CANDIDATE_SURFACE] = active_candidate_source
    missing_required = [path for path, present in required_surfaces.items() if not present]
    safety_status = "passed" if not missing_required else "failed"
    if missing_required:
        warnings.append("missing required run surfaces: " + ", ".join(missing_required))

    return {
        "artifact_kind": "specgraph_static_artifact_manifest",
        "schema_version": 1,
        "generated_at": utc_now(),
        "git": {
            "sha": repo_git_value(repo_root, "rev-parse", "HEAD"),
            "ref": repo_git_value(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
        },
        "published_roots": list(root_summary),
        "roots": root_summary,
        "checksums_path": "checksums.sha256",
        "required_surfaces": required_surfaces,
        "platform_handoff_surfaces": platform_handoff_surfaces,
        "safety_gate": {
            "status": safety_status,
            "redacted_local_path_occurrences": redacted_local_path_occurrences,
            "warnings": warnings,
        },
        "files": [file_info.__dict__ for file_info in copied_files],
    }


def write_checksums(output_dir: Path, copied_files: list[PublishFile]) -> Path:
    checksums_path = output_dir / "checksums.sha256"
    lines = [
        f"{file_info.sha256}  {file_info.path}"
        for file_info in sorted(copied_files, key=lambda f: f.path)
    ]
    write_text_atomic(checksums_path, "\n".join(lines) + "\n")
    return checksums_path


def run_make_target(repo_root: Path, target: str) -> None:
    completed = subprocess.run(
        ["make", target],
        cwd=repo_root,
        text=True,
    )
    if completed.returncode != 0:
        raise PublishBundleError(f"make {target} failed")


def platform_handoff_authority_boundary() -> dict[str, bool]:
    return {
        "may_create_branch_or_commit": False,
        "may_execute_prompt_agent": False,
        "may_mark_candidate_graph_accepted": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
        "may_write_ontology_lockfile": False,
        "may_write_ontology_package": False,
    }


def platform_handoff_privacy_boundary() -> dict[str, bool]:
    return {
        "raw_intent_text_published": False,
        "raw_model_output_published": False,
        "raw_prompt_published": False,
    }


def platform_handoff_placeholder_finding() -> dict[str, object]:
    return {
        "finding_id": PLATFORM_HANDOFF_PLACEHOLDER_REASON,
        "severity": "review_required",
        "source": "static_artifact_publish",
        "message": (
            "No active idea-to-spec candidate is configured for public Platform handoff publishing."
        ),
    }


def platform_handoff_placeholder_readiness() -> dict[str, object]:
    return {
        "ready": False,
        "review_state": PLATFORM_HANDOFF_PLACEHOLDER_REASON,
        "blocked_by": [PLATFORM_HANDOFF_PLACEHOLDER_REASON],
        "next_artifact": "run idea-to-spec authoring flow with an active candidate",
    }


def is_publishable_active_candidate_source(repo_root: Path) -> bool:
    active_source = load_run_json_if_present(repo_root, ACTIVE_IDEA_TO_SPEC_CANDIDATE_SURFACE)
    if not active_source:
        return False
    readiness = active_source.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("ready") is not True:
        return False
    if active_source.get("artifact_kind") != "active_idea_to_spec_candidate":
        return False
    if active_source.get("contract_ref") != ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONTRACT_REF:
        return False
    if active_source.get("source_mode") != "active_candidate":
        return False
    candidate = active_source.get("candidate")
    if not isinstance(candidate, dict):
        return False
    if candidate.get("target_repository_role") != "product_spec_workspace":
        return False
    if candidate.get("governance_profile") != "product_workspace":
        return False
    materialization = load_run_json_if_present(
        repo_root, "candidate_spec_materialization_report.json"
    )
    promotion_gate = load_run_json_if_present(repo_root, "idea_to_spec_promotion_gate.json")
    for artifact in (materialization, promotion_gate):
        if not isinstance(artifact, dict):
            return False
        readiness = artifact.get("readiness")
        if not isinstance(readiness, dict) or readiness.get("ready") is not True:
            return False
        if artifact.get("source_mode") == "public_placeholder" or artifact.get(
            "placeholder_reason"
        ):
            return False
    return True


def run_file_sha256_if_present(repo_root: Path, surface: str) -> str | None:
    path = repo_root / "runs" / surface
    return file_sha256(path) if path.is_file() else None


def is_publishable_candidate_approval_decision(repo_root: Path) -> bool:
    approval = load_run_json_if_present(repo_root, CANDIDATE_APPROVAL_DECISION_SURFACE)
    if not approval:
        return False
    if not is_publishable_active_candidate_source(repo_root):
        return False
    if approval.get("artifact_kind") != "candidate_approval_decision":
        return False
    if approval.get("contract_ref") != CANDIDATE_APPROVAL_DECISION_CONTRACT_REF:
        return False
    if approval.get("canonical_mutations_allowed") is not False:
        return False
    if approval.get("tracked_artifacts_written") is not False:
        return False
    source_artifacts = approval.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        return False
    expected_surfaces = {
        "active_candidate": ACTIVE_IDEA_TO_SPEC_CANDIDATE_SURFACE,
        "promotion_gate": "idea_to_spec_promotion_gate.json",
    }
    for key, surface in expected_surfaces.items():
        source = source_artifacts.get(key)
        if not isinstance(source, dict):
            return False
        if source.get("source_ref") != f"runs/{surface}":
            return False
        if source.get("sha256") != run_file_sha256_if_present(repo_root, surface):
            return False
    return True


def should_refresh_product_workspace_active_candidate(repo_root: Path) -> bool:
    refresh_mode = os.environ.get(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH_ENV, "auto")
    if refresh_mode.strip().lower() in {"1", "true", "force", "always"}:
        return True
    return not is_publishable_active_candidate_source(repo_root)


def active_candidate_source_manifest_entry(repo_root: Path) -> dict[str, object]:
    active_source = load_run_json_if_present(repo_root, ACTIVE_IDEA_TO_SPEC_CANDIDATE_SURFACE)
    if not active_source or not is_publishable_active_candidate_source(repo_root):
        return {
            "path": f"runs/{ACTIVE_IDEA_TO_SPEC_CANDIDATE_SURFACE}",
            "present": False,
            "source_mode": "not_configured",
            "ready": False,
        }
    candidate = active_source.get("candidate")
    summary = active_source.get("summary")
    return {
        "path": f"runs/{ACTIVE_IDEA_TO_SPEC_CANDIDATE_SURFACE}",
        "present": True,
        "source_mode": "active_candidate",
        "ready": True,
        "candidate": candidate if isinstance(candidate, dict) else {},
        "summary": summary if isinstance(summary, dict) else {},
    }


def build_platform_handoff_placeholder_surfaces(
    *,
    generated_at: str | None = None,
) -> dict[str, dict[str, object]]:
    generated = generated_at or datetime.now(tz=timezone.utc).isoformat()
    readiness = platform_handoff_placeholder_readiness()
    finding = platform_handoff_placeholder_finding()
    materialization = {
        "artifact_kind": "candidate_spec_materialization_report",
        "schema_version": 1,
        "contract_ref": PLATFORM_HANDOFF_MATERIALIZATION_CONTRACT_REF,
        "proposal_id": "0153",
        "source_mode": "public_placeholder",
        "placeholder_reason": PLATFORM_HANDOFF_PLACEHOLDER_REASON,
        "generated_at": generated,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "materialization_source": PLATFORM_HANDOFF_PLACEHOLDER_REASON,
        "readiness": readiness,
        "authority_boundary": platform_handoff_authority_boundary(),
        "privacy_boundary": platform_handoff_privacy_boundary(),
        "findings": [finding],
        "warnings": [],
        "local_files_written": [],
        "materialized_files": [],
        "promotion_request": {
            "platform_artifact_kind": "platform_graph_repository_promotion_request",
            "path_argument": "--path",
            "paths": [],
        },
        "summary": {
            "status": PLATFORM_HANDOFF_PLACEHOLDER_REASON,
            "candidate_node_count": 0,
            "materialized_file_count": 0,
            "finding_count": 1,
        },
    }
    promotion_gate = {
        "artifact_kind": "idea_to_spec_promotion_gate",
        "schema_version": 1,
        "contract_ref": PLATFORM_HANDOFF_PROMOTION_GATE_CONTRACT_REF,
        "proposal_id": "0154",
        "source_mode": "public_placeholder",
        "placeholder_reason": PLATFORM_HANDOFF_PLACEHOLDER_REASON,
        "generated_at": generated,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "readiness": readiness,
        "authority_boundary": platform_handoff_authority_boundary(),
        "privacy_boundary": platform_handoff_privacy_boundary(),
        "findings": [finding],
        "warnings": [],
        "metric_snapshot": {},
        "promotion_request": {
            "platform_artifact_kind": "platform_graph_repository_promotion_request",
            "next_command": "platform.py graph-repository promotion-request",
            "path_argument": "--path",
            "paths": [],
        },
        "source_artifacts": {
            "materialization": {
                "artifact_kind": "candidate_spec_materialization_report",
                "contract_ref": PLATFORM_HANDOFF_MATERIALIZATION_CONTRACT_REF,
                "proposal_id": "0153",
                "source_ref": "runs/candidate_spec_materialization_report.json",
                "readiness": readiness,
            }
        },
        "summary": {
            "status": PLATFORM_HANDOFF_PLACEHOLDER_REASON,
            "finding_count": 1,
            "warning_count": 0,
            "promotion_path_count": 0,
            "materialized_file_count": 0,
        },
    }
    return {
        "candidate_spec_materialization_report.json": materialization,
        "idea_to_spec_promotion_gate.json": promotion_gate,
    }


def write_public_platform_handoff_surfaces(repo_root: Path) -> None:
    if is_publishable_active_candidate_source(repo_root):
        return
    runs_dir = repo_root / "runs"
    for name, payload in build_platform_handoff_placeholder_surfaces().items():
        write_json_artifact(runs_dir / name, payload)


def refresh_publish_surfaces(repo_root: Path) -> None:
    run_make_target(repo_root, "viewer-surfaces")
    run_make_target(repo_root, "implementation-delta")
    run_make_target(repo_root, "implementation-work")
    run_make_target(repo_root, "executor-adapters")
    run_make_target(repo_root, "agent-passports")
    run_make_target(repo_root, "agent-runtime-evidence")
    run_make_target(repo_root, "viewer-surfaces")
    run_make_target(repo_root, "external-handoffs")
    run_make_target(repo_root, "external-consumer-evidence")
    run_make_target(repo_root, "ontology-imports")
    run_make_target(repo_root, "spec-ontology-bindings")
    run_make_target(repo_root, "spec-ontology-validation")
    run_make_target(repo_root, "ontology-gap-review")
    run_make_target(repo_root, "legacy-spec-ontology-backfill-plan")
    run_make_target(repo_root, "ontology-imports-public")
    run_make_target(repo_root, "ontology-owner-decision-import-v2")
    run_make_target(repo_root, "specauthor-authoring-flow")
    if should_refresh_product_workspace_active_candidate(repo_root):
        run_make_target(repo_root, "product-workspace-active-candidate")
    run_make_target(repo_root, "idea-maturity-metrics")
    write_public_platform_handoff_surfaces(repo_root)


def build_public_bundle(
    *,
    repo_root: Path,
    output_dir: Path,
    refresh_surfaces: bool = False,
    strict_required_surfaces: bool = True,
    require_verified_agent_passports: bool = True,
) -> BuildResult:
    repo_root = repo_root.resolve()
    output_dir = (
        (repo_root / output_dir).resolve() if not output_dir.is_absolute() else output_dir.resolve()
    )

    if refresh_surfaces:
        refresh_publish_surfaces(repo_root)

    git_dir = repo_root / ".git"
    if output_dir == repo_root or output_dir == git_dir or git_dir in output_dir.parents:
        raise PublishBundleError(f"unsafe output directory: {output_dir}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[PublishFile] = []
    copied_paths: set[str] = set()
    warnings: list[str] = []
    redacted_total = 0
    secret_findings: list[str] = []
    ontology_fixture_findings: list[str] = []

    for root_name, source_path, rel_path in iter_publish_sources(repo_root):
        text = load_text(source_path)
        if root_name == "runs" and source_path.suffix == ".json":
            validate_json_artifact(source_path, text)

        redacted_text, redaction_count = redact_local_paths(text)
        redacted_total += redaction_count
        secret_findings.extend(detect_secret_like_content(rel_path, redacted_text))
        ontology_fixture_findings.extend(
            detect_demo_ontology_fixture_content(rel_path, redacted_text)
        )

        target_path = output_dir / rel_path.as_posix()
        write_text_atomic(target_path, redacted_text)
        copied_paths.add(rel_path.as_posix())
        copied_files.append(
            PublishFile(
                path=rel_path.as_posix(),
                root=root_name,
                size_bytes=target_path.stat().st_size,
                sha256=file_sha256(target_path),
            )
        )

    for rel_path in ontology_materialized_ir_refs(repo_root):
        if rel_path.parts and rel_path.parts[0] == "runs":
            run_rel = rel_path.relative_to("runs").as_posix()
            if is_local_only_run_path(run_rel):
                raise PublishBundleError(
                    f"local-only ontology materialized IR is not publishable: {rel_path.as_posix()}"
                )
        source_path = repo_root / rel_path.as_posix()
        if not source_path.is_file():
            raise PublishBundleError(f"missing ontology materialized IR: {rel_path.as_posix()}")
        if has_symlink_component(source_path, repo_root):
            raise PublishBundleError(f"symlinked ontology materialized IR: {rel_path.as_posix()}")

        text = load_text(source_path)
        validate_json_artifact(source_path, text)
        redacted_text, redaction_count = redact_local_paths(text)
        redacted_total += redaction_count
        secret_findings.extend(detect_secret_like_content(rel_path, redacted_text))
        ontology_fixture_findings.extend(
            detect_demo_ontology_fixture_content(rel_path, redacted_text)
        )

        if rel_path.as_posix() in copied_paths:
            continue

        target_path = output_dir / rel_path.as_posix()
        write_text_atomic(target_path, redacted_text)
        copied_paths.add(rel_path.as_posix())
        copied_files.append(
            PublishFile(
                path=rel_path.as_posix(),
                root=rel_path.parts[0],
                size_bytes=target_path.stat().st_size,
                sha256=file_sha256(target_path),
            )
        )

    if secret_findings:
        shutil.rmtree(output_dir)
        raise PublishBundleError("; ".join(sorted(set(secret_findings))))
    if ontology_fixture_findings:
        shutil.rmtree(output_dir)
        raise PublishBundleError("; ".join(sorted(set(ontology_fixture_findings))))

    manifest = build_manifest(
        repo_root=repo_root,
        output_dir=output_dir,
        copied_files=copied_files,
        warnings=warnings,
        redacted_local_path_occurrences=redacted_total,
    )
    required_surfaces = manifest["required_surfaces"]
    if not isinstance(required_surfaces, dict):
        raise PublishBundleError("internal manifest error: required_surfaces is not an object")
    missing_required = [path for path, present in required_surfaces.items() if not present]
    if strict_required_surfaces and missing_required:
        shutil.rmtree(output_dir)
        raise PublishBundleError("missing required run surfaces: " + ", ".join(missing_required))
    if require_verified_agent_passports:
        try:
            validate_agent_passport_publish_surfaces(output_dir)
        except PublishBundleError:
            shutil.rmtree(output_dir)
            raise

    manifest_path = output_dir / "artifact_manifest.json"
    write_text_atomic(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    copied_files.append(
        PublishFile(
            path="artifact_manifest.json",
            root=".",
            size_bytes=manifest_path.stat().st_size,
            sha256=file_sha256(manifest_path),
        )
    )
    checksums_path = write_checksums(output_dir, copied_files)

    return BuildResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        checksums_path=checksums_path,
        manifest=manifest,
        copied_files=copied_files,
        warnings=warnings,
        redacted_local_path_occurrences=redacted_total,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a static HTTP-ready SpecGraph artifact bundle.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--refresh-publish-surfaces",
        action="store_true",
        dest="refresh_publish_surfaces",
        help=(
            "Run publish surface refresh targets before collecting specs/ and runs/: "
            "viewer-surfaces, implementation-delta, implementation-work, executor-adapters, "
            "agent-passports, agent-runtime-evidence, viewer-surfaces, external-handoffs, "
            "external-consumer-evidence, ontology-imports, spec-ontology-bindings, "
            "spec-ontology-validation, ontology-gap-review, "
            "legacy-spec-ontology-backfill-plan, ontology-imports-public, "
            "ontology-owner-decision-import-v2, specauthor-authoring-flow, "
            "then public Platform handoff placeholders."
        ),
    )
    parser.add_argument(
        "--refresh-viewer-surfaces",
        action="store_true",
        dest="refresh_publish_surfaces",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--allow-missing-required-surfaces",
        action="store_true",
        help="Build even if core viewer-facing runs artifacts are missing.",
    )
    parser.add_argument(
        "--allow-unverified-agent-passports",
        action="store_true",
        help=(
            "Build even if Agent Passport CLI verification did not run successfully. "
            "Do not use for public static publishing."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = build_public_bundle(
            repo_root=args.repo_root,
            output_dir=args.output_dir,
            refresh_surfaces=args.refresh_publish_surfaces,
            strict_required_surfaces=not args.allow_missing_required_surfaces,
            require_verified_agent_passports=not args.allow_unverified_agent_passports,
        )
    except PublishBundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = {
        "output_dir": str(result.output_dir),
        "manifest_path": str(result.manifest_path),
        "checksums_path": str(result.checksums_path),
        "file_count": len(result.copied_files),
        "redacted_local_path_occurrences": result.redacted_local_path_occurrences,
        "safety_gate": result.manifest["safety_gate"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
