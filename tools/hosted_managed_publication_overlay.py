#!/usr/bin/env python3
"""Validate and apply one hosted managed-operation public report packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

PACKET_ARTIFACT_KIND = "platform_hosted_managed_publication_packet"
PACKET_CONTRACT_REF = "platform.hosted-managed.public-report-publication.v1"
WORKSPACE_ID = "hosted-operation-canary"
OPERATION_ID = "review_status_execute"
CANDIDATE_BRANCH = "graph-candidate/hosted-operation-canary"
REVIEW_OBJECT_REF = "runs/product_candidate_promotion_review_object_evidence.json"
REVIEW_STATUS_REF = "runs/product_candidate_promotion_review_status_report.json"
REVIEW_OBJECT_KIND = "platform_product_candidate_promotion_review_object_evidence"
REVIEW_STATUS_KIND = "platform_product_candidate_promotion_review_status_report"
MAX_PACKET_BYTES = 32 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVIEW_URL_RE = re.compile(r"^https://github\.com/0al-spec/SpecGraph/pull/([1-9][0-9]*)$")
LOCAL_PATH_RE = re.compile(
    r"(?:^|[\s\"'])(?:"
    r"/Users/|/home/|/private/|/tmp/|/var/folders/|/srv/|"
    r"/workspace/|/github/workspace/|/opt/|/root/|/etc/0al/|"
    r"/run/secrets/|/data/|[A-Za-z]:\\"
    r")"
)
SECRET_VALUE_RE = re.compile(
    r"(?:"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"gh[opusr]_[A-Za-z0-9_]{20,}|"
    r"Bearer\s+\S{20,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\b(?:password|secret|token|authorization)\s*[:=]\s*\S+"
    r")",
    re.IGNORECASE,
)
FORBIDDEN_KEY_PARTS = (
    "command",
    "stdout",
    "stderr",
    "exit_code",
    "returncode",
    "password",
    "secret",
    "token",
    "raw_idea",
    "workspace_dir",
    "repository_dir",
)


class OverlayError(RuntimeError):
    """A publication packet violates the bounded workspace overlay contract."""


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() == value and value else None


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _json_bytes(payload: dict[str, Any]) -> bytes:
    try:
        rendered = json.dumps(
            payload,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise OverlayError("publication packet contains non-strict JSON") from exc
    return (rendered + "\n").encode("utf-8")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value}")


def load_packet(path: Path) -> dict[str, Any]:
    if not path.is_absolute():
        raise OverlayError("publication packet path must be absolute")
    if path.is_symlink() or not path.is_file():
        raise OverlayError("publication packet must be a regular file")
    try:
        if path.stat().st_size > MAX_PACKET_BYTES:
            raise OverlayError("publication packet exceeds its bounded size")
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise OverlayError("publication packet is unreadable") from exc
    if not isinstance(payload, dict):
        raise OverlayError("publication packet must contain an object")
    return payload


def _public_boundary(value: Any) -> bool:
    boundary = _record(value)
    required = (
        "accepts_arbitrary_commands",
        "creates_git_commits",
        "merges_pull_requests",
        "mutates_canonical_specs",
        "opens_pull_requests",
        "publishes_read_models",
        "writes_ontology_packages",
        "accepts_ontology_terms",
    )
    return all(boundary.get(key) is False for key in required) and all(
        isinstance(key, str) and item is False for key, item in boundary.items()
    )


def _public_privacy(value: Any) -> bool:
    privacy = _record(value)
    return privacy == {
        "public_safe": True,
        "raw_idea_included": False,
        "local_paths_included": False,
    }


def _scan_public(value: Any, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise OverlayError("public report contains a non-string key")
            lowered = key.lower()
            negative_boundary_declaration = (
                path[-1:] == ("authority_boundary",) and item is False
            ) or (
                path[-1:] == ("privacy_boundary",)
                and key in {"raw_idea_included", "local_paths_included"}
                and item is False
            )
            if (
                any(part in lowered for part in FORBIDDEN_KEY_PARTS)
                and not negative_boundary_declaration
            ):
                raise OverlayError(
                    f"public report contains forbidden field {'.'.join((*path, key))}"
                )
            if key.startswith("may_") and item is not False:
                raise OverlayError("public report expands unknown may_* authority")
            _scan_public(item, path=(*path, key))
        return
    if isinstance(value, list):
        if len(value) > 128:
            raise OverlayError("public report contains an oversized list")
        for index, item in enumerate(value):
            _scan_public(item, path=(*path, str(index)))
        return
    if isinstance(value, str):
        if len(value) > 4096 or any(ord(character) < 32 for character in value):
            raise OverlayError("public report contains unsafe text")
        if LOCAL_PATH_RE.search(value):
            raise OverlayError("public report contains a local path")
        if SECRET_VALUE_RE.search(value):
            raise OverlayError("public report contains a secret-like value")


def _identity(report: dict[str, Any]) -> tuple[str, str, str]:
    workspace_id = _text(report.get("workspace_id"))
    candidate_id = _text(report.get("candidate_id"))
    candidate_branch = _text(report.get("candidate_branch"))
    if (
        workspace_id != WORKSPACE_ID
        or candidate_id != WORKSPACE_ID
        or candidate_branch != CANDIDATE_BRANCH
    ):
        raise OverlayError("public report workspace or candidate identity is invalid")
    return workspace_id, candidate_id, candidate_branch


def _review_identity(
    *,
    review_url: Any,
    review_number: Any,
) -> tuple[str, int]:
    url = _text(review_url)
    number = _integer(review_number)
    match = REVIEW_URL_RE.fullmatch(url or "")
    if match is None or number is None or number <= 0 or int(match.group(1)) != number:
        raise OverlayError("public report review identity is invalid")
    return url, number


def _validate_review_object(report: dict[str, Any]) -> None:
    workspace_id, _candidate_id, _candidate_branch = _identity(report)
    _review_identity(
        review_url=report.get("review_url"),
        review_number=report.get("review_number"),
    )
    workspace_binding = _record(report.get("workspace_binding"))
    if (
        report.get("artifact_kind") != REVIEW_OBJECT_KIND
        or report.get("schema_version") != 1
        or report.get("ok") is not True
        or report.get("probe_only") is not True
        or report.get("review_state_at_capture") != "open"
        or report.get("base_branch") != "main"
        or report.get("promotion_execution_report_ref")
        != "runs/product_candidate_promotion_execution_report.json"
        or not SHA256_RE.fullmatch(_text(report.get("promotion_execution_report_sha256")) or "")
        or not re.fullmatch(
            r"[0-9a-f]{40}",
            _text(report.get("review_head_sha")) or "",
        )
        or not _public_privacy(report.get("privacy_boundary"))
        or not _public_boundary(report.get("authority_boundary"))
        or workspace_binding
        != {
            "status": "ready",
            "workspace_id": workspace_id,
            "binding_id": f"product-workspace-binding://{workspace_id}",
        }
    ):
        raise OverlayError("review object public report is invalid")


def _validate_review_status(report: dict[str, Any]) -> None:
    _workspace_id, _candidate_id, candidate_branch = _identity(report)
    pull_request = _record(report.get("pull_request"))
    review_url, review_number = _review_identity(
        review_url=pull_request.get("url"),
        review_number=pull_request.get("number"),
    )
    graph_review = _record(report.get("graph_repository_review_status"))
    graph_summary = _record(graph_review.get("summary"))
    summary = _record(report.get("summary"))
    review_state = report.get("review_state")
    review_probe_only = report.get("review_probe_only")
    expected_pull_request_state = {
        "open": "OPEN",
        "closed": "CLOSED",
        "merged": "MERGED",
    }.get(review_state)
    expected_summary_status = (
        "review_probe_completed"
        if review_probe_only is True
        else (
            "ready_for_read_model_publication"
            if review_state == "merged"
            else "waiting_for_review_merge"
        )
    )
    expected_graph_summary_status = expected_summary_status
    review_merged = review_state == "merged"
    if (
        report.get("artifact_kind") != REVIEW_STATUS_KIND
        or report.get("schema_version") != 1
        or report.get("ok") is not True
        or report.get("workflow_lane") != "product_idea_to_spec"
        or expected_pull_request_state is None
        or not isinstance(review_probe_only, bool)
        or report.get("promotion_execution_report_ref")
        != "runs/product_candidate_promotion_execution_report.json"
        or report.get("review_object_evidence_ref") != REVIEW_OBJECT_REF
        or pull_request.get("headRefName") != candidate_branch
        or pull_request.get("baseRefName") != "main"
        or pull_request.get("number") != review_number
        or pull_request.get("state") != expected_pull_request_state
        or not isinstance(pull_request.get("isDraft"), bool)
        or graph_review.get("ok") is not True
        or graph_review.get("review_state") != review_state
        or graph_review.get("review_url") != review_url
        or graph_summary.get("status") != expected_graph_summary_status
        or graph_summary.get("review_merged") is not review_merged
        or summary.get("status") != expected_summary_status
        or summary.get("review_merged") is not review_merged
        or summary.get("read_model_published") is not False
        or not _public_privacy(report.get("privacy_boundary"))
        or not _public_boundary(report.get("authority_boundary"))
    ):
        raise OverlayError("review status public report is invalid")
    for digest in (
        pull_request.get("headRefOid"),
        _record(pull_request.get("mergeCommit")).get("oid"),
    ):
        if digest is not None and not re.fullmatch(r"[0-9a-f]{40}", digest):
            raise OverlayError("review status public report contains an invalid Git SHA")


def validate_packet(
    packet: dict[str, Any],
    *,
    workspace_id: str,
) -> tuple[str, dict[str, Any]]:
    report = _record(packet.get("report"))
    logical_ref = _text(packet.get("logical_ref"))
    expected_kind = {
        REVIEW_OBJECT_REF: REVIEW_OBJECT_KIND,
        REVIEW_STATUS_REF: REVIEW_STATUS_KIND,
    }.get(logical_ref)
    scope = _record(packet.get("publication_scope"))
    summary = _record(packet.get("summary"))
    if (
        packet.get("artifact_kind") != PACKET_ARTIFACT_KIND
        or packet.get("contract_ref") != PACKET_CONTRACT_REF
        or packet.get("schema_version") != 1
        or packet.get("workspace_id") != workspace_id
        or workspace_id != WORKSPACE_ID
        or packet.get("operation_id") != OPERATION_ID
        or expected_kind is None
        or report.get("artifact_kind") != expected_kind
        or scope
        != {
            "workspace_bundle_only": True,
            "maximum_report_count": 1,
            "incremental_upload_required": True,
        }
        or summary
        != {
            "status": "publication_packet_ready",
            "report_count": 1,
        }
        or not _public_privacy(packet.get("privacy_boundary"))
        or not _public_boundary(packet.get("authority_boundary"))
    ):
        raise OverlayError("publication packet contract is invalid")
    expected_digest = _text(packet.get("public_report_sha256"))
    actual_digest = hashlib.sha256(_json_bytes(report)).hexdigest()
    if expected_digest != actual_digest:
        raise OverlayError("publication report digest does not match the packet")
    _scan_public(packet)
    if logical_ref == REVIEW_OBJECT_REF:
        _validate_review_object(report)
    else:
        _validate_review_status(report)
    return logical_ref, report


def apply_packet(
    *,
    packet_path: Path,
    run_dir: Path,
    workspace_id: str,
) -> dict[str, Any]:
    packet = load_packet(packet_path)
    logical_ref, report = validate_packet(packet, workspace_id=workspace_id)
    run_dir = run_dir.resolve()
    expected_run_dir = (Path(__file__).resolve().parents[1] / "runs" / workspace_id).resolve()
    if run_dir != expected_run_dir or run_dir.is_symlink() or not run_dir.is_dir():
        raise OverlayError("workspace run directory is not the tracked scoped run directory")
    relative = PurePosixPath(logical_ref).relative_to("runs")
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
        raise OverlayError("publication logical ref is not a bounded top-level run artifact")
    destination = run_dir / relative.as_posix()
    data = _json_bytes(report)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "schema_version": 1,
        "artifact_kind": "specgraph_hosted_managed_publication_overlay_report",
        "status": "applied",
        "workspace_id": workspace_id,
        "logical_ref": logical_ref,
        "public_report_sha256": hashlib.sha256(data).hexdigest(),
        "summary": {
            "applied_report_count": 1,
            "bounded_workspace_overlay": True,
        },
        "privacy_boundary": {
            "public_safe": True,
            "raw_idea_included": False,
            "local_paths_included": False,
        },
        "authority_boundary": {
            "executes_managed_operations": False,
            "mutates_canonical_specs": False,
            "writes_ontology_packages": False,
            "accepts_ontology_terms": False,
            "opens_pull_requests": False,
            "merges_pull_requests": False,
            "publishes_read_models": False,
        },
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(report))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--input", type=Path, required=True)
    root.add_argument("--workspace-id", required=True)
    root.add_argument("--run-dir", type=Path, required=True)
    root.add_argument("--output", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        report = apply_packet(
            packet_path=args.input.resolve(),
            run_dir=args.run_dir.resolve(),
            workspace_id=args.workspace_id,
        )
        write_report(args.output.resolve(), report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except OverlayError as exc:
        print(f"hosted managed publication overlay error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
