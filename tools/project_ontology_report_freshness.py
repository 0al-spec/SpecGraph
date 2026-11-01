"""Explicitly compare an advisory bundle against current captured inputs.

The input_binding is caller-attributed, not an authenticated producer attestation.
No report is selected, cached, or activated by this module.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from project_ontology_check_scopes import (
    CHECK_SCOPES,
    DEFAULT_SCOPES,
    SCOPED_ANALYSIS_PROFILE,
    SCOPED_SCHEMA_VERSION,
)
from project_ontology_context import ContextResult
from project_ontology_report_freshness_spec import REPORT_INPUTS_COMPATIBLE_SPEC, FreshnessFacts
from spec_ontology_context_reports import build_context_reports

_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ReportInputBinding:
    bundle_sha256: str
    binding_sha256: str
    producer_identity: str

    def report(self) -> dict[str, object]:
        return {
            "artifact_kind": "project_ontology_report_binding",
            "schema_version": 1,
            "bundle_sha256": self.bundle_sha256,
            "binding_sha256": self.binding_sha256,
            "producer_identity": self.producer_identity,
            "producer_provenance": "caller_attributed",
        }


@dataclass(frozen=True, slots=True)
class FreshnessResult:
    outcome: str
    diagnostics: tuple[str, ...]
    comparisons: tuple[tuple[str, bool], ...] = ()

    def report(self) -> dict[str, object]:
        return {
            "artifact_kind": "project_ontology_report_freshness",
            "schema_version": 1,
            "outcome": self.outcome,
            "diagnostics": list(self.diagnostics),
            "comparisons": [
                {"input": name, "matches": matched} for name, matched in self.comparisons
            ],
            "scope": "advisory_report_input_compatibility",
            "semantic_approval": "not_established",
            "tests_verified": False,
            "producer_provenance": "caller_attributed",
        }


def _input_binding(value: ReportInputBinding | dict[str, Any]) -> ReportInputBinding:
    if isinstance(value, ReportInputBinding):
        return value
    if (
        not isinstance(value, dict)
        or value.get("artifact_kind") != "project_ontology_report_binding"
        or value.get("schema_version") != 1
    ):
        raise ValueError("unsupported input_binding")
    return ReportInputBinding(
        value.get("bundle_sha256"), value.get("binding_sha256"), value.get("producer_identity")
    )


def _identity_valid(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _shape(bundle: object) -> tuple[str, str] | None:
    if not isinstance(bundle, dict):
        return "unavailable", "analyzed bundle unavailable"
    if bundle.get("schema_version") != SCOPED_SCHEMA_VERSION:
        return "unavailable", "scoped advisory bundle version unavailable"
    if bundle.get("analysis_profile") != SCOPED_ANALYSIS_PROFILE:
        return "unavailable", "scoped advisory analysis profile unavailable"
    requested = bundle.get("requested_scopes")
    if (
        not isinstance(requested, list)
        or any(not isinstance(scope, str) or scope not in CHECK_SCOPES for scope in requested)
        or requested != [scope for scope in CHECK_SCOPES if scope in requested]
    ):
        return "invalid", "requested scope manifest is malformed"
    assessments = bundle.get("assessments")
    if not isinstance(assessments, dict) or set(assessments) != set(CHECK_SCOPES):
        return "invalid", "scope assessment manifest is incomplete or malformed"
    for scope in CHECK_SCOPES:
        assessment = assessments[scope]
        if (
            not isinstance(assessment, dict)
            or assessment.get("check_scope") != scope
            or assessment.get("outcome")
            not in ("analyzed", "unavailable", "invalid", "not_requested")
            or not isinstance(assessment.get("diagnostics"), list)
            or any(not isinstance(detail, str) for detail in assessment["diagnostics"])
            or any(
                key not in assessment for key in ("project_context", "analysis_profile", "summary")
            )
        ):
            return "invalid", "scope assessment is malformed"
        outcome = assessment["outcome"]
        if (scope not in requested) != (outcome == "not_requested"):
            return "invalid", "scope assessment differs from requested scopes"
        if scope == "specification_metamodel" and outcome == "analyzed":
            return "invalid", "specification metamodel analysis is not supported"
        if outcome == "analyzed":
            if (
                not isinstance(assessment["project_context"], dict)
                or assessment["analysis_profile"] != bundle["analysis_profile"]
                or not isinstance(assessment["summary"], dict)
                or assessment["diagnostics"]
            ):
                return "invalid", "analyzed scope assessment is inconsistent"
        elif any(
            assessment[key] is not None
            for key in ("project_context", "analysis_profile", "summary")
        ):
            return "invalid", "unanalyzed scope claims analysis identity or summary"
    outcomes = [assessments[scope]["outcome"] for scope in requested]
    expected = (
        "invalid"
        if "invalid" in outcomes
        else "unavailable"
        if not outcomes or "unavailable" in outcomes
        else "analyzed"
    )
    if bundle.get("outcome") != expected:
        return "invalid", "aggregate outcome differs from scope assessments"
    if expected != "analyzed":
        return expected, "analyzed scope bundle unavailable"
    inputs = bundle.get("inputs")
    binding = bundle.get("binding_index")
    validation = bundle.get("validation_report")
    if (
        not isinstance(inputs, dict)
        or not isinstance(binding, dict)
        or not isinstance(validation, dict)
    ):
        return "unavailable", "bundle input or report missing"
    if not _identity_valid(inputs.get("specs_root")) or not isinstance(inputs.get("specs"), list):
        return "unavailable", "spec input inventory missing"
    if any(
        not isinstance(row, dict)
        or not _identity_valid(row.get("path"))
        or not isinstance(row.get("sha256"), str)
        or not _HEX.fullmatch(row["sha256"])
        for row in inputs["specs"]
    ):
        return "unavailable", "spec input identity missing"
    metadata = binding.get("project_context")
    if not isinstance(metadata, dict) or any(
        not _identity_valid(metadata.get(k))
        for k in (
            "project_id",
            "workspace",
            "context_revision",
            "analysis_profile",
            "context_outcome",
            "scope",
        )
    ):
        return "unavailable", "project context identity missing"
    if not metadata["context_revision"].startswith("sha256:") or not _HEX.fullmatch(
        metadata["context_revision"][7:]
    ):
        return "unavailable", "context revision missing or malformed"
    if metadata["scope"] == "selected_composition_symbols":
        members = metadata.get("members")
        if not isinstance(members, list) or len(members) != 3:
            return "unavailable", "composed member capture inventory missing"
        catalog = metadata.get("foundation_catalog")
        if (
            not isinstance(catalog, dict)
            or any(
                not _identity_valid(catalog.get(k))
                for k in ("id", "namespace", "version", "source_uri")
            )
            or not isinstance(catalog.get("source_sha256"), str)
            or not _HEX.fullmatch(catalog["source_sha256"])
        ):
            return "unavailable", "foundation catalog identity missing or malformed"
    else:
        member = metadata.get("selected_member")
        if not isinstance(member, dict):
            return "unavailable", "selected member identity missing"
        members = [
            {
                **member,
                **{k: metadata.get(k) for k in ("source_sha256", "ir_sha256", "compiler_sha256")},
            }
        ]
    if any(
        not isinstance(row, dict)
        or any(not _identity_valid(row.get(k)) for k in ("id", "namespace", "version"))
        or any(
            not isinstance(row.get(k), str) or not _HEX.fullmatch(row[k])
            for k in ("source_sha256", "ir_sha256", "compiler_sha256")
        )
        for row in members
    ):
        return "unavailable", "selected member identity or snapshot hash missing or malformed"
    if len({row["id"] for row in members}) != len(members):
        return "invalid", "duplicate captured member identity"
    if any(
        k not in binding or k not in validation
        for k in (
            "artifact_kind",
            "schema_version",
            "entries",
            "summary",
            "inputs",
            "project_context",
            "check_scope",
            "analysis_profile",
        )
    ):
        return "unavailable", "report payload incomplete"
    if (
        binding["inputs"] != inputs
        or validation["inputs"] != inputs
        or validation["project_context"] != metadata
    ):
        return "invalid", "report input metadata is inconsistent"
    if (
        binding["artifact_kind"] != "spec_ontology_binding_index"
        or validation["artifact_kind"] != "spec_ontology_validation_report"
    ):
        return "invalid", "report kind is inconsistent"
    if any(
        report["check_scope"] != "domain_vocabulary"
        or report["schema_version"] != SCOPED_SCHEMA_VERSION
        or report["analysis_profile"] != SCOPED_ANALYSIS_PROFILE
        for report in (binding, validation)
    ):
        return "invalid", "domain report scope, profile or version is inconsistent"
    domain = assessments["domain_vocabulary"]
    if domain["project_context"] != metadata or domain["summary"] != {
        "binding_index": binding["summary"],
        "validation_report": validation["summary"],
    }:
        return "invalid", "domain assessment differs from report payloads"
    return None


def bind_report_bundle(bundle: dict[str, Any], *, producer_identity: str) -> ReportInputBinding:
    """Bind a complete bundle at capture time; this does not attest its origin."""
    issue = _shape(bundle)
    if issue or not _identity_valid(producer_identity):
        raise ValueError(issue[1] if issue else "producer identity missing")
    return ReportInputBinding(_digest(bundle), _digest(bundle["binding_index"]), producer_identity)


def assess_report_freshness(
    saved_bundle: dict[str, Any] | None,
    *,
    input_binding: ReportInputBinding | dict[str, Any] | None,
    context: ContextResult,
    workspace_root: Path,
    specs_root: Path,
    producer_identity: str | None,
    documents: tuple[tuple[str, bytes], ...] | None = None,
    requested_scopes: tuple[str, ...] = DEFAULT_SCOPES,
) -> FreshnessResult:
    """Compare saved data and input_binding with newly captured explicit current inputs."""
    if input_binding is None or saved_bundle is None or not _identity_valid(producer_identity):
        return FreshnessResult(
            "unavailable", ("saved bundle, capture input_binding or producer identity missing",)
        )
    try:
        saved_input_binding = _input_binding(input_binding)
        if not _identity_valid(saved_input_binding.producer_identity) or not all(
            isinstance(digest, str) and _HEX.fullmatch(digest)
            for digest in (saved_input_binding.bundle_sha256, saved_input_binding.binding_sha256)
        ):
            return FreshnessResult("unavailable", ("input_binding identities missing",))
        issue = _shape(saved_bundle)
        if issue and issue[0] == "invalid":
            return FreshnessResult(issue[0], (issue[1],))
        complete_payload = isinstance(saved_bundle, dict) and all(
            isinstance(saved_bundle.get(key), dict)
            for key in ("inputs", "binding_index", "validation_report")
        )
        if (
            complete_payload
            and (issue is None or saved_bundle.get("outcome") != "analyzed")
            and (
                _digest(saved_bundle) != saved_input_binding.bundle_sha256
                or _digest(saved_bundle["binding_index"]) != saved_input_binding.binding_sha256
            )
        ):
            return FreshnessResult(
                "invalid",
                ("saved bundle or binding payload differs from its capture input_binding",),
            )
        if issue:
            return FreshnessResult(issue[0], (issue[1],))
        if (
            not _identity_valid(context.revision)
            or not context.revision.startswith("sha256:")
            or not _HEX.fullmatch(context.revision[7:])
        ):
            return FreshnessResult(
                "unavailable", ("current context revision missing or malformed",)
            )
        saved_meta = saved_bundle["binding_index"]["project_context"]
        root = str(Path(workspace_root).resolve())
        direct = (
            ("producer_identity", saved_input_binding.producer_identity == producer_identity),
            ("project_id", saved_meta["project_id"] == context.project_id),
            ("workspace", saved_meta["workspace"] == root and context.workspace == root),
            ("context_revision", saved_meta["context_revision"] == context.revision),
        )
        if not all(result for _, result in direct):
            return FreshnessResult(
                "stale", tuple(f"{name} changed" for name, ok in direct if not ok), direct
            )
        current = build_context_reports(
            context,
            workspace_root=workspace_root,
            specs_root=specs_root,
            documents=documents,
            requested_scopes=requested_scopes,
        )
        if current.get("outcome") != "analyzed":
            return FreshnessResult(
                "invalid" if current.get("outcome") == "invalid" else "unavailable",
                (
                    "current advisory inputs unavailable: "
                    + "; ".join(current.get("diagnostics", [])),
                ),
                direct,
            )
        issue = _shape(current)
        if issue:
            return FreshnessResult(
                "unavailable", ("current bundle incomplete: " + issue[1],), direct
            )
        current_meta = current["binding_index"]["project_context"]
        keys = (
            "analysis_profile",
            "selected_member",
            "source_sha256",
            "ir_sha256",
            "compiler_sha256",
            "context_outcome",
            "scope",
            "members",
            "foundation_catalog",
        )
        comparisons = (
            direct
            + tuple((key, saved_meta.get(key) == current_meta.get(key)) for key in keys)
            + (
                (
                    "bundle_schema_version",
                    saved_bundle["schema_version"] == current["schema_version"],
                ),
                (
                    "bundle_analysis_profile",
                    saved_bundle["analysis_profile"] == current["analysis_profile"],
                ),
                (
                    "requested_scopes",
                    saved_bundle["requested_scopes"] == current["requested_scopes"],
                ),
                ("scope_assessments", saved_bundle["assessments"] == current["assessments"]),
                ("bundle_outcome", saved_bundle["outcome"] == current["outcome"]),
                ("spec_inputs", saved_bundle["inputs"] == current["inputs"]),
                (
                    "binding_payload",
                    _digest(saved_bundle["binding_index"]) == _digest(current["binding_index"]),
                ),
                (
                    "validation_payload",
                    _digest(saved_bundle["validation_report"])
                    == _digest(current["validation_report"]),
                ),
            )
        )
        facts = FreshnessFacts(tuple(match for _, match in comparisons))
        if REPORT_INPUTS_COMPATIBLE_SPEC.is_satisfied_by(facts):
            return FreshnessResult("fresh", ("explicit advisory inputs match",), comparisons)
        return FreshnessResult(
            "stale",
            tuple(f"{name} changed" for name, match in comparisons if not match),
            comparisons,
        )
    except (TypeError, ValueError, OSError) as error:
        return FreshnessResult("invalid", (f"invalid report or input_binding: {error}",))
