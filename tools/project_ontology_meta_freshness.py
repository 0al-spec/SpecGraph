"""Compare a complete schema-3 meta bundle with a newly computed bundle.

The caller captures and recomputes the current bundle before calling this module.
Binding and producer identity are caller-attributed, not an attestation or proof
of human approval. The schema-2 domain freshness implementation stays separate.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from project_ontology_check_scopes import CHECK_SCOPES, SCOPED_ANALYSIS_PROFILE
from project_ontology_report_freshness import FreshnessResult, bind_report_bundle
from project_ontology_report_freshness import _shape as domain_shape
from spec_ontology_metamodel_check import PACKAGE, PROFILE, SOURCE_SHA256

META_BUNDLE_PROFILE = "specgraph-scoped-ontology-advisory-v2"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_TARGET = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-SPEC-[0-9]+\Z")
_DOMAIN, _META = CHECK_SCOPES


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _hash(value: object) -> bool:
    return isinstance(value, str) and bool(_HEX.fullmatch(value))


@dataclass(frozen=True, slots=True)
class MetaReportBinding:
    bundle_sha256: str
    producer_identity: str
    binding_sha256: str

    def report(self) -> dict[str, object]:
        return {
            "artifact_kind": "project_ontology_meta_report_binding",
            "schema_version": 1,
            "bundle_sha256": self.bundle_sha256,
            "producer_identity": self.producer_identity,
            "binding_sha256": self.binding_sha256,
            "producer_provenance": "caller_attributed",
        }


def _shape(bundle: object) -> tuple[str, str] | None:
    if not isinstance(bundle, dict):
        return "unavailable", "meta bundle unavailable"
    if type(bundle.get("schema_version")) is not int or bundle["schema_version"] != 3:
        return "unavailable", "meta bundle schema 3 unavailable"
    if bundle.get("analysis_profile") != META_BUNDLE_PROFILE:
        return "unavailable", "meta bundle analysis profile unavailable"
    if any(key not in bundle for key in ("inputs", "binding_index", "validation_report")):
        return "unavailable", "meta bundle input or child slots missing"
    requested = bundle.get("requested_scopes")
    if not isinstance(requested, list) or requested not in ([_META], [_DOMAIN, _META]):
        return "invalid", "meta requested scopes malformed"
    assessments = bundle.get("assessments")
    if not isinstance(assessments, dict) or set(assessments) != set(CHECK_SCOPES):
        return "invalid", "scope assessment manifest malformed"
    if bundle.get("outcome") != "analyzed":
        outcome = bundle.get("outcome")
        if outcome not in ("unavailable", "invalid"):
            return "invalid", "meta bundle outcome malformed"
        return outcome, "complete analyzed meta bundle unavailable"
    if (
        bundle.get("semantic_approval") != "not_established"
        or bundle.get("full_spec_conformance") != "not_assessed"
        or bundle.get("diagnostics") != []
    ):
        return "invalid", "bundle outcome or authority boundaries inconsistent"

    meta, domain = assessments[_META], assessments[_DOMAIN]
    if not isinstance(meta, dict) or not isinstance(domain, dict):
        return "invalid", "scope assessment malformed"
    if (
        meta.get("check_scope") != _META
        or meta.get("outcome") != "analyzed"
        or meta.get("analysis_profile") != PROFILE
        or meta.get("diagnostics") != []
    ):
        return "invalid", "meta assessment identity or outcome inconsistent"
    summary, context = meta.get("summary"), meta.get("project_context")
    if not isinstance(summary, dict) or not isinstance(context, dict):
        return "unavailable", "meta summary or captured context missing"
    document = summary.get("document")
    if not isinstance(document, dict):
        return "unavailable", "captured document missing"
    document_id, document_path = document.get("id"), document.get("path")
    if not _text(document_id) or not _text(document_path) or not _hash(document.get("sha256")):
        return "unavailable", "captured document identity missing"
    path = PurePosixPath(document_path)
    if (
        not _TARGET.fullmatch(document_id)
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != document_path
        or path != PurePosixPath("specs", "nodes", f"{document_id}.yaml")
    ):
        return "invalid", "captured document path or identity invalid"
    if any(not _hash(summary.get(key)) for key in ("mapping_sha256", "decision_sha256")):
        return "unavailable", "mapping or disposition digest missing"
    if (
        summary.get("decision_provenance") != "caller_attributed_not_attested"
        or summary.get("node_membership") != "not_assessed"
        or summary.get("lifecycle") != "not_assessed"
        or summary.get("semantic_approval") != "not_established"
        or summary.get("canonical_mutations_allowed") is not False
    ):
        return "invalid", "meta authority or lifecycle boundary inconsistent"

    revision = context.get("context_revision")
    if (
        any(
            not _text(context.get(key))
            for key in ("project_id", "workspace", "analysis_profile", "compiler_provenance")
        )
        or not isinstance(revision, str)
        or not revision.startswith("sha256:")
        or not _hash(revision[7:])
        or any(
            not _hash(context.get(key)) for key in ("source_sha256", "ir_sha256", "compiler_sha256")
        )
    ):
        return "unavailable", "meta context identity or capture digest missing"
    member = context.get("selected_member")
    if not isinstance(member, dict):
        return "unavailable", "selected meta package missing"
    if (
        tuple(member.get(k) for k in ("id", "namespace", "version")) != PACKAGE
        or context.get("source_sha256") != SOURCE_SHA256
        or context.get("context_outcome") != "verified"
        or context.get("scope") != "single_member_local_symbols"
        or context.get("verified_closure") is not False
        or context.get("semantic_approval") != "not_established"
        or context.get("binding_authority") != "structural_advisory_only"
    ):
        return "invalid", "captured meta context differs from supported package or authority"

    check = summary.get("class_check")
    if not isinstance(check, dict) or not isinstance(check.get("origin"), dict):
        return "unavailable", "class check or origin missing"
    origin = check["origin"]
    if (
        check.get("ontology_ref") != "sgcore:Spec"
        or check.get("source") != "/kind"
        or check.get("result") != "matched"
        or origin.get("ontology_ref") != "sgcore:Spec"
        or origin.get("ontology_uri") != f"ontology://{PACKAGE[0]}/{PACKAGE[2]}/classes/Spec"
        or origin.get("package") != member
        or any(
            origin.get(k) != context.get(k)
            for k in ("source_sha256", "ir_sha256", "compiler_sha256")
        )
        or origin.get("verification") != "compiler_checked"
    ):
        return "invalid", "meta class check does not match captured context"

    if _DOMAIN not in requested:
        if (
            domain.get("check_scope") != _DOMAIN
            or domain.get("outcome") != "not_requested"
            or domain.get("diagnostics") != []
            or any(k not in domain for k in ("project_context", "analysis_profile", "summary"))
            or any(
                domain.get(k) is not None
                for k in ("project_context", "analysis_profile", "summary")
            )
            or any(
                bundle.get(k) is not None for k in ("inputs", "binding_index", "validation_report")
            )
        ):
            return "invalid", "unrequested domain claims analysis"
        return None

    # Reuse the entire schema-2 validator for the unchanged domain children.
    projected = {
        **bundle,
        "schema_version": 2,
        "analysis_profile": SCOPED_ANALYSIS_PROFILE,
        "requested_scopes": [_DOMAIN],
        "assessments": {
            _DOMAIN: domain,
            _META: {
                "check_scope": _META,
                "outcome": "not_requested",
                "diagnostics": [],
                "project_context": None,
                "analysis_profile": None,
                "summary": None,
            },
        },
    }
    issue = domain_shape(projected)
    if issue:
        return issue
    entries = bundle["inputs"]["specs"]
    if len(entries) != 1 or entries[0] != {"path": document_path, "sha256": document["sha256"]}:
        return "invalid", "domain and meta document captures differ"
    if (
        domain["project_context"].get("project_id") != context["project_id"]
        or domain["project_context"].get("workspace") != context["workspace"]
    ):
        return "invalid", "domain and meta workspace identities differ"
    return None


def bind_meta_bundle(bundle: dict[str, Any], *, producer_identity: str) -> MetaReportBinding:
    """Create a caller-attributed binding for one complete analyzed meta bundle."""
    issue = _shape(bundle)
    if issue or not _text(producer_identity):
        raise ValueError(issue[1] if issue else "producer identity missing")
    bundle_sha = _digest(bundle)
    binding_sha = _digest({"bundle_sha256": bundle_sha, "producer_identity": producer_identity})
    return MetaReportBinding(bundle_sha, producer_identity, binding_sha)


def assess_meta_freshness(
    saved_bundle: dict[str, Any] | None,
    *,
    input_binding: MetaReportBinding | dict[str, Any] | None,
    current_bundle: dict[str, Any] | None,
    producer_identity: str | None,
) -> FreshnessResult:
    """Compare a bound saved bundle to caller's newly computed complete bundle."""
    if saved_bundle is None or input_binding is None or not _text(producer_identity):
        return FreshnessResult("unavailable", ("saved bundle, binding or producer missing",))
    if isinstance(saved_bundle, dict) and saved_bundle.get("schema_version") == 2:
        if not isinstance(input_binding, dict):
            return FreshnessResult("invalid", ("legacy binding shape invalid",))
        try:
            legacy = bind_report_bundle(
                saved_bundle, producer_identity=input_binding.get("producer_identity")
            ).report()
            if legacy != input_binding:
                return FreshnessResult("invalid", ("legacy bundle or binding differs",))
        except (TypeError, ValueError, OverflowError) as error:
            return FreshnessResult("invalid", (f"invalid legacy report: {error}",))
        return FreshnessResult(
            "unavailable", ("schema 2 domain report has no metamodel freshness evidence",)
        )
    if isinstance(input_binding, dict):
        if (
            input_binding.get("artifact_kind") != "project_ontology_meta_report_binding"
            or type(input_binding.get("schema_version")) is not int
            or input_binding.get("schema_version") != 1
            or input_binding.get("producer_provenance") != "caller_attributed"
        ):
            return FreshnessResult("invalid", ("meta binding shape invalid",))
        input_binding = MetaReportBinding(
            input_binding.get("bundle_sha256"),
            input_binding.get("producer_identity"),
            input_binding.get("binding_sha256"),
        )
    if (
        not isinstance(input_binding, MetaReportBinding)
        or not _hash(input_binding.bundle_sha256)
        or not _hash(input_binding.binding_sha256)
        or not _text(input_binding.producer_identity)
    ):
        return FreshnessResult("invalid", ("meta binding identity invalid",))
    try:
        if input_binding.binding_sha256 != _digest(
            {
                "bundle_sha256": input_binding.bundle_sha256,
                "producer_identity": input_binding.producer_identity,
            }
        ):
            return FreshnessResult("invalid", ("meta binding digest differs from its fields",))
        if _digest(saved_bundle) != input_binding.bundle_sha256:
            return FreshnessResult("invalid", ("saved bundle differs from captured binding",))
        saved_issue = _shape(saved_bundle)
        if saved_issue:
            return FreshnessResult(saved_issue[0], (saved_issue[1],))
        current_issue = _shape(current_bundle)
        if current_issue:
            return FreshnessResult(current_issue[0], ("current: " + current_issue[1],))
        comparisons = (
            ("producer_identity", input_binding.producer_identity == producer_identity),
            ("complete_bundle", _digest(saved_bundle) == _digest(current_bundle)),
        )
        if all(match for _, match in comparisons):
            return FreshnessResult("fresh", ("explicit meta advisory inputs match",), comparisons)
        return FreshnessResult(
            "stale",
            tuple(f"{name} changed" for name, match in comparisons if not match),
            comparisons,
        )
    except (TypeError, ValueError, OverflowError) as error:
        return FreshnessResult("invalid", (f"invalid meta report: {error}",))
