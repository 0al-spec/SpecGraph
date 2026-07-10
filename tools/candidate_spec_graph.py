"""Build a review-only candidate spec graph artifact from event-storming intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0150"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph.v0.1"
SEED_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph-seed.v0.1"
INTAKE_CONTRACT_REF = "specgraph.idea-to-spec.event-storming-intake.v0.1"
DEFAULT_INTAKE_PATH = (
    ROOT / "tests" / "fixtures" / "candidate_spec_graph" / "idea_event_storming_intake_ready.json"
)
DEFAULT_SEED_PATH = ROOT / "tests" / "fixtures" / "candidate_spec_graph" / "candidate_ready.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "candidate_spec_graph.json"

STRONG_CLAIM_TYPES = {
    "architectural_decision",
    "constraint",
    "decision",
    "invariant",
    "product_claim",
    "runtime_behavior",
    "security_claim",
    "security_constraint",
}
GRAPH_ENTRY_LIST_FIELDS = {
    "source_refs",
    "source_event_refs",
    "ontology_refs",
    "domain_refs",
    "context_refs",
    "ontology_layer_refs",
    "model_applicability_refs",
    "acceptance_criteria_refs",
    "evidence_refs",
    "assumptions",
}
F_LEVELS = {f"F{index}" for index in range(6)}
R_LEVELS = {f"R{index}" for index in range(6)}
RAW_TRACE_FIELDS = {
    "intent_text",
    "raw_intent",
    "raw_intent_text",
    "raw_model_output",
    "raw_prompt",
    "raw_response",
    "raw_text",
}
DISPLAY_ALIAS_MAX_LENGTH = 64
DISPLAY_ALIAS_PRIVATE_MARKERS = (
    "/Users/",
    "/home/",
    "/private/",
    "/tmp/",
    "/var/folders/",
    "-----BEGIN",
    "api-key",
    "apikey",
    "api_key",
    "bearer ",
    "token=",
)


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


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _display_alias_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    if any(ord(character) < 32 for character in value):
        return ""
    text = " ".join(value.split())
    if not text:
        return ""
    lowered = text.lower()
    if any(marker.lower() in lowered for marker in DISPLAY_ALIAS_PRIVATE_MARKERS):
        return ""
    return text


def _bounded_display_alias(value: str) -> str:
    text = value.rstrip(". ")
    if len(text) <= DISPLAY_ALIAS_MAX_LENGTH:
        return text
    candidate = text[: DISPLAY_ALIAS_MAX_LENGTH - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{candidate or text[: DISPLAY_ALIAS_MAX_LENGTH - 1].rstrip()}…"


def _display_alias_with_suffix(alias: str, suffix: str) -> str:
    if len(alias) + len(suffix) <= DISPLAY_ALIAS_MAX_LENGTH:
        return f"{alias}{suffix}"
    prefix_limit = max(1, DISPLAY_ALIAS_MAX_LENGTH - len(suffix))
    prefix = alias[:prefix_limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{prefix or alias[:prefix_limit].rstrip()}{suffix}"


def _derived_display_alias(title: str) -> str:
    sentence = title.rstrip(". ")
    match = re.search(r"\bmust\s+(.+)", sentence, flags=re.IGNORECASE)
    if match:
        sentence = match.group(1)
        for separator in (" before ", " after ", " when ", " unless ", " while "):
            position = sentence.lower().find(separator)
            if position > 0:
                sentence = sentence[:position]
                break
        sentence = sentence[:1].upper() + sentence[1:]
    return _bounded_display_alias(sentence)


def _node_display_alias(node: dict[str, Any]) -> tuple[str, str, bool]:
    explicit = _display_alias_text(node.get("display_alias"))
    if explicit:
        return _bounded_display_alias(explicit), "provided", False
    if node.get("display_alias") not in (None, ""):
        return "", "", True
    title = _display_alias_text(node.get("title"))
    if not title:
        return "", "", True
    alias = _derived_display_alias(title)
    return alias, ("title" if alias == title.rstrip(". ") else "derived_title"), False


def _apply_display_aliases(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in nodes:
        alias, source, invalid = _node_display_alias(node)
        node_id = _text(node.get("id"))
        if invalid or not alias:
            node.pop("display_alias", None)
            node.pop("display_alias_source", None)
            findings.append(
                _finding(
                    finding_id="candidate_node_display_alias_invalid",
                    severity="review_required",
                    message="Candidate node display alias must be public-safe single-line text.",
                    evidence={"node_id": node_id},
                )
            )
            continue
        key = alias.casefold()
        if key in seen:
            kind = _display_alias_text(node.get("kind")) or "node"
            kind = kind.replace("_", " ")
            alias = _display_alias_with_suffix(alias, f" ({kind[:24]})")
            if not _display_alias_text(alias):
                node.pop("display_alias", None)
                node.pop("display_alias_source", None)
                findings.append(
                    _finding(
                        finding_id="candidate_node_display_alias_invalid",
                        severity="review_required",
                        message=(
                            "Candidate node display alias must be public-safe single-line text."
                        ),
                        evidence={"node_id": node_id},
                    )
                )
                continue
            key = alias.casefold()
        if key in seen:
            digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:6]
            alias = _display_alias_with_suffix(alias, f" [{digest}]")
            if not _display_alias_text(alias):
                node.pop("display_alias", None)
                node.pop("display_alias_source", None)
                findings.append(
                    _finding(
                        finding_id="candidate_node_display_alias_invalid",
                        severity="review_required",
                        message=(
                            "Candidate node display alias must be public-safe single-line text."
                        ),
                        evidence={"node_id": node_id},
                    )
                )
                continue
            key = alias.casefold()
        seen.add(key)
        node["display_alias"] = alias
        node["display_alias_source"] = source
    return findings


def _relative_ref(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        "source": "candidate_spec_graph",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
    }


def _normalize_list_field(
    value: Any,
    *,
    category: str,
    entry_id: str,
    field: str,
    index: int,
) -> tuple[list[str], dict[str, Any] | None]:
    if not isinstance(value, list):
        return [], _finding(
            finding_id="candidate_graph_list_field_malformed",
            severity="review_required",
            message="Candidate graph list-valued fields must be arrays of non-empty strings.",
            evidence={
                "category": category,
                "entry_id": entry_id,
                "field": field,
                "index": index,
                "value_type": type(value).__name__,
            },
        )
    values = _text_list(value)
    if len(values) != len(value):
        return values, _finding(
            finding_id="candidate_graph_list_field_malformed",
            severity="review_required",
            message="Candidate graph list-valued fields must be arrays of non-empty strings.",
            evidence={
                "category": category,
                "entry_id": entry_id,
                "field": field,
                "index": index,
                "value_type": "list",
            },
        )
    return values, None


def _seed_contract_findings(seed: dict[str, Any]) -> list[dict[str, Any]]:
    invalid: list[str] = []
    if seed.get("artifact_kind") != "candidate_spec_graph_seed":
        invalid.append("artifact_kind")
    if seed.get("schema_version") != SCHEMA_VERSION:
        invalid.append("schema_version")
    if seed.get("contract_ref") != SEED_CONTRACT_REF:
        invalid.append("contract_ref")
    if not invalid:
        return []
    return [
        _finding(
            finding_id="candidate_graph_seed_contract_invalid",
            severity="review_required",
            message="Candidate spec graph requires a valid seed contract.",
            evidence={
                "invalid_fields": invalid,
                "expected": {
                    "artifact_kind": "candidate_spec_graph_seed",
                    "schema_version": SCHEMA_VERSION,
                    "contract_ref": SEED_CONTRACT_REF,
                },
                "actual": {
                    "artifact_kind": seed.get("artifact_kind"),
                    "schema_version": seed.get("schema_version"),
                    "contract_ref": seed.get("contract_ref"),
                },
            },
        )
    ]


def _seed_source_generation_findings(seed: dict[str, Any]) -> list[dict[str, Any]]:
    source_generation = _dict(seed.get("source_generation"))
    readiness = _dict(source_generation.get("readiness"))
    source_findings = [
        finding
        for finding in _list(source_generation.get("findings"))
        if isinstance(finding, dict) and finding.get("severity") == "review_required"
    ]
    blocked_by = _text_list(readiness.get("blocked_by"))
    readiness_requires_review = bool(readiness) and (
        readiness.get("ready") is False or bool(blocked_by)
    )
    if not source_findings and not readiness_requires_review:
        return []
    return [
        _finding(
            finding_id="candidate_graph_seed_source_generation_review_required",
            severity="review_required",
            message="Candidate graph seed generation requires review before pre-SIB can proceed.",
            evidence={
                "source_finding_ids": [
                    finding.get("finding_id", "unknown") for finding in source_findings
                ],
                "source_contract_ref": source_generation.get("contract_ref"),
                "source_readiness_ready": readiness.get("ready"),
                "source_readiness_blocked_by": blocked_by,
            },
        )
    ]


def _normalize_entry(
    value: Any,
    *,
    category: str,
    index: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        return None, [
            _finding(
                finding_id="candidate_graph_entry_invalid",
                severity="review_required",
                message="Candidate graph entries must be objects.",
                evidence={"category": category, "index": index},
            )
        ]
    entry = dict(value)
    title = _text(entry.get("title"), _text(entry.get("name"), _text(entry.get("statement"))))
    entry_id = _text(entry.get("id"), f"{category}.{_slug(title, str(index + 1))}")
    normalized: dict[str, Any] = {"id": entry_id}
    findings: list[dict[str, Any]] = []
    for key, item in entry.items():
        if key == "id" or key in RAW_TRACE_FIELDS:
            continue
        if key in GRAPH_ENTRY_LIST_FIELDS:
            normalized[key], finding = _normalize_list_field(
                item,
                category=category,
                entry_id=entry_id,
                field=key,
                index=index,
            )
            if finding:
                findings.append(finding)
        elif isinstance(item, str):
            item_text = item.strip()
            if item_text:
                normalized[key] = item_text
        elif isinstance(item, (bool, int, float)):
            normalized[key] = item
        elif isinstance(item, list):
            normalized[key] = item
        elif isinstance(item, dict):
            normalized[key] = item
    return normalized, findings


def _candidate_seed_graph(seed: dict[str, Any]) -> dict[str, Any]:
    graph = _dict(seed.get("candidate_graph"))
    if graph:
        return graph
    return {
        "nodes": seed.get("nodes", []),
        "edges": seed.get("edges", []),
    }


def _normalize_nested_list(
    values: Any,
    *,
    category: str,
    parent_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for index, value in enumerate(_list(values)):
        entry, entry_findings = _normalize_entry(value, category=category, index=index)
        for finding in entry_findings:
            finding["evidence"]["parent_id"] = parent_id
            findings.append(finding)
        if entry:
            normalized.append(entry)
    return normalized, findings


def _normalize_nodes(seed: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    graph = _candidate_seed_graph(seed)
    nodes: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    seen_node_ids: dict[str, int] = {}
    for index, value in enumerate(_list(graph.get("nodes"))):
        node, entry_findings = _normalize_entry(
            value,
            category="candidate_node",
            index=index,
        )
        if entry_findings:
            findings.extend(entry_findings)
            continue
        if node is None:
            continue
        node_id = _text(node.get("id"))
        if node_id in seen_node_ids:
            findings.append(
                _finding(
                    finding_id="candidate_node_duplicate_id",
                    severity="review_required",
                    message="Candidate graph node ids must be unique.",
                    evidence={
                        "node_id": node_id,
                        "first_index": seen_node_ids[node_id],
                        "duplicate_index": index,
                    },
                )
            )
        else:
            seen_node_ids[node_id] = index
        requirements, requirement_findings = _normalize_nested_list(
            node.get("requirements"),
            category="requirement",
            parent_id=node["id"],
        )
        acceptance_criteria, ac_findings = _normalize_nested_list(
            node.get("acceptance_criteria"),
            category="acceptance_criterion",
            parent_id=node["id"],
        )
        claims, claim_findings = _normalize_nested_list(
            node.get("claims"),
            category="claim",
            parent_id=node["id"],
        )
        gaps, gap_findings = _normalize_nested_list(
            node.get("gaps"),
            category="gap",
            parent_id=node["id"],
        )
        findings.extend(requirement_findings + ac_findings + claim_findings + gap_findings)
        node["requirements"] = requirements
        node["acceptance_criteria"] = acceptance_criteria
        node["claims"] = claims
        node["gaps"] = gaps
        nodes.append(node)
    if not nodes:
        findings.append(
            _finding(
                finding_id="candidate_graph_nodes_missing",
                severity="review_required",
                message="Candidate spec graph requires at least one candidate node.",
            )
        )
    findings.extend(_apply_display_aliases(nodes))
    return nodes, findings


def _normalize_edges(seed: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    graph = _candidate_seed_graph(seed)
    edges: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for index, value in enumerate(_list(graph.get("edges"))):
        edge, entry_findings = _normalize_entry(
            value,
            category="candidate_edge",
            index=index,
        )
        if entry_findings:
            findings.extend(entry_findings)
            continue
        if edge is not None:
            edges.append(edge)
    return edges, findings


def _intake_known_refs(intake: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    event_storming = _dict(intake.get("event_storming"))
    for values in event_storming.values():
        for entry in _list(values):
            entry_id = _text(_dict(entry).get("id"))
            if entry_id:
                refs.add(entry_id)
    return refs


def _validate_intake(intake: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if intake.get("artifact_kind") != "idea_event_storming_intake":
        findings.append(
            _finding(
                finding_id="intake_wrong_artifact_kind",
                severity="review_required",
                message="Candidate graph requires an idea_event_storming_intake input.",
                evidence={"artifact_kind": intake.get("artifact_kind")},
            )
        )
    if intake.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="intake_schema_version_unsupported",
                severity="review_required",
                message="idea_event_storming_intake schema_version must be 1.",
                evidence={"schema_version": intake.get("schema_version")},
            )
        )
    if intake.get("contract_ref") != INTAKE_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="intake_contract_ref_unsupported",
                severity="review_required",
                message=f"idea_event_storming_intake contract_ref must be {INTAKE_CONTRACT_REF}.",
                evidence={"contract_ref": intake.get("contract_ref")},
            )
        )
    readiness = _dict(intake.get("candidate_graph_readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="intake_not_ready",
                severity="review_required",
                message="Candidate graph cannot be built from an intake that is not ready.",
                evidence={"review_state": readiness.get("review_state")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if intake.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="intake_authority_expansion",
                    severity="review_required",
                    message=f"Input intake {field} must be false.",
                    evidence={field: intake.get(field)},
                )
            )
    return findings


def _validate_node_shape(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for node in nodes:
        missing = [
            field for field in ("title", "kind", "description") if not _text(node.get(field))
        ]
        if not _text_list(node.get("ontology_refs")):
            missing.append("ontology_refs")
        if not node.get("requirements"):
            missing.append("requirements")
        if not node.get("acceptance_criteria"):
            missing.append("acceptance_criteria")
        if missing:
            findings.append(
                _finding(
                    finding_id="candidate_node_incomplete",
                    severity="review_required",
                    message=(
                        "Candidate graph nodes require title, kind, description, "
                        "ontology refs, requirements, and acceptance criteria."
                    ),
                    evidence={"node_id": node.get("id"), "missing": missing},
                )
            )
    return findings


def _nested_statement(entry: dict[str, Any]) -> str:
    return _text(
        entry.get("statement"),
        _text(entry.get("description"), _text(entry.get("title"), _text(entry.get("name")))),
    )


def _validate_nested_spec_text(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for node in nodes:
        for requirement in node.get("requirements", []):
            if not _nested_statement(requirement):
                findings.append(
                    _finding(
                        finding_id="candidate_requirement_statement_missing",
                        severity="review_required",
                        message="Candidate requirements require real statement text.",
                        evidence={
                            "node_id": node.get("id"),
                            "requirement_id": requirement.get("id"),
                        },
                    )
                )
        for criterion in node.get("acceptance_criteria", []):
            if not _nested_statement(criterion):
                findings.append(
                    _finding(
                        finding_id="candidate_acceptance_criterion_statement_missing",
                        severity="review_required",
                        message="Candidate acceptance criteria require real statement text.",
                        evidence={
                            "node_id": node.get("id"),
                            "acceptance_criterion_id": criterion.get("id"),
                        },
                    )
                )
    return findings


def _validate_edge_refs(edges: list[dict[str, Any]], node_ids: set[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for edge in edges:
        missing = [field for field in ("from", "to", "relation") if not _text(edge.get(field))]
        unknown = [
            value
            for value in (_text(edge.get("from")), _text(edge.get("to")))
            if value and value not in node_ids
        ]
        if missing or unknown:
            findings.append(
                _finding(
                    finding_id="candidate_edge_invalid",
                    severity="review_required",
                    message="Candidate graph edges require known from/to node refs and a relation.",
                    evidence={
                        "edge_id": edge.get("id"),
                        "missing": missing,
                        "unknown_node_refs": unknown,
                    },
                )
            )
    return findings


def _validate_source_refs(
    nodes: list[dict[str, Any]],
    intake_refs: set[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for node in nodes:
        source_event_refs = _text_list(node.get("source_event_refs"))
        if not source_event_refs:
            findings.append(
                _finding(
                    finding_id="candidate_node_source_event_refs_missing",
                    severity="review_required",
                    message="Candidate graph nodes require source_event_refs provenance.",
                    evidence={"node_id": node.get("id")},
                )
            )
        unknown = [ref for ref in source_event_refs if ref not in intake_refs]
        if unknown:
            findings.append(
                _finding(
                    finding_id="candidate_node_unknown_intake_ref",
                    severity="review_required",
                    message="Candidate graph node source_event_refs must point to intake entries.",
                    evidence={"node_id": node.get("id"), "unknown_refs": unknown},
                )
            )
    return findings


def _validate_requirement_refs(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for node in nodes:
        ac_ids = {entry["id"] for entry in node.get("acceptance_criteria", [])}
        for requirement in node.get("requirements", []):
            refs = _text_list(requirement.get("acceptance_criteria_refs"))
            if not refs:
                findings.append(
                    _finding(
                        finding_id="candidate_requirement_ac_refs_missing",
                        severity="review_required",
                        message="Requirements require acceptance_criteria_refs.",
                        evidence={
                            "node_id": node.get("id"),
                            "requirement_id": requirement.get("id"),
                        },
                    )
                )
            unknown = [ref for ref in refs if ref not in ac_ids]
            if unknown:
                findings.append(
                    _finding(
                        finding_id="candidate_requirement_unknown_ac_ref",
                        severity="review_required",
                        message=(
                            "Requirement acceptance_criteria_refs must point to "
                            "node-local acceptance criteria."
                        ),
                        evidence={
                            "node_id": node.get("id"),
                            "requirement_id": requirement.get("id"),
                            "unknown_refs": unknown,
                        },
                    )
                )
    return findings


def _is_strong_claim(claim: dict[str, Any]) -> bool:
    claim_type = _text(claim.get("type"), "claim")
    return claim_type in STRONG_CLAIM_TYPES or _text(claim.get("strength")) == "strong"


def _claim_has_calibration(claim: dict[str, Any]) -> bool:
    calibration = _dict(claim.get("calibration"))
    scope = _dict(calibration.get("G"))
    return (
        _text(calibration.get("F")) in F_LEVELS
        and _text(calibration.get("R")) in R_LEVELS
        and bool(_text_list(scope.get("applies_to")))
    )


def _validate_claims(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for node in nodes:
        for claim in node.get("claims", []):
            if _is_strong_claim(claim) and not _claim_has_calibration(claim):
                calibration = _dict(claim.get("calibration"))
                findings.append(
                    _finding(
                        finding_id="candidate_strong_claim_without_fgr",
                        severity="review_required",
                        message=(
                            "Strong candidate graph claims require F/G/R calibration "
                            "before pre-SIB review."
                        ),
                        evidence={
                            "node_id": node.get("id"),
                            "claim_id": claim.get("id"),
                            "F": calibration.get("F"),
                            "R": calibration.get("R"),
                        },
                    )
                )
    return findings


def build_candidate_spec_graph(
    *,
    intake: dict[str, Any],
    seed: dict[str, Any],
    intake_path: Path | None = None,
    seed_path: Path | None = None,
) -> dict[str, Any]:
    nodes, node_findings = _normalize_nodes(seed)
    edges, edge_findings = _normalize_edges(seed)
    node_ids = {node["id"] for node in nodes}
    findings = (
        _seed_contract_findings(seed)
        + _seed_source_generation_findings(seed)
        + _validate_intake(intake)
        + node_findings
        + edge_findings
        + _validate_node_shape(nodes)
        + _validate_nested_spec_text(nodes)
        + _validate_edge_refs(edges, node_ids)
        + _validate_source_refs(nodes, _intake_known_refs(intake))
        + _validate_requirement_refs(nodes)
        + _validate_claims(nodes)
    )
    blocking_findings = [
        finding for finding in findings if finding.get("severity") == "review_required"
    ]
    ok = not blocking_findings
    source_ref = _text(seed.get("source_ref"))
    if not source_ref and seed_path is not None:
        source_ref = _relative_ref(seed_path)
    intake_source_ref = _text(intake.get("source_ref"))
    if not intake_source_ref and intake_path is not None:
        intake_source_ref = _relative_ref(intake_path)
    return {
        "artifact_kind": "candidate_spec_graph",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "seed_contract_ref": _text(seed.get("contract_ref"), SEED_CONTRACT_REF),
        "source_ref": source_ref or "operator://candidate-spec-graph-local",
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_intake": {
            "artifact_kind": intake.get("artifact_kind"),
            "contract_ref": intake.get("contract_ref"),
            "source_ref": intake_source_ref or "unknown",
            "root_intent_sha256": _dict(intake.get("root_intent")).get("text_sha256"),
            "readiness": _dict(intake.get("candidate_graph_readiness")).get("review_state"),
        },
        "active_frame": _dict(intake.get("active_frame")),
        "nodes": nodes,
        "edges": edges,
        "materialization_intent": {
            "state": "review_only",
            "target": "pre_sib_coherence_review",
            "may_write_canonical_specs": False,
            "may_create_branch_or_commit": False,
        },
        "pre_sib_readiness": {
            "ready": ok,
            "review_state": "ready_for_pre_sib" if ok else "candidate_graph_review_required",
            "next_artifact": "runs/pre_sib_coherence_report.json",
            "blocked_by": [finding["finding_id"] for finding in blocking_findings],
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_intent_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
        },
        "findings": blocking_findings,
        "warnings": [],
        "summary": {
            "status": "ready_for_pre_sib" if ok else "candidate_graph_review_required",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "requirement_count": sum(len(node.get("requirements", [])) for node in nodes),
            "acceptance_criteria_count": sum(
                len(node.get("acceptance_criteria", [])) for node in nodes
            ),
            "claim_count": sum(len(node.get("claims", [])) for node in nodes),
            "gap_count": sum(len(node.get("gaps", [])) for node in nodes),
            "finding_count": len(blocking_findings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", default=DEFAULT_INTAKE_PATH, type=Path)
    parser.add_argument("--candidate-seed", default=DEFAULT_SEED_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    intake = load_json(args.intake)
    seed = load_json(args.candidate_seed)
    candidate_graph = build_candidate_spec_graph(
        intake=intake,
        seed=seed,
        intake_path=args.intake,
        seed_path=args.candidate_seed,
    )
    write_json(candidate_graph, args.output)
    print(json.dumps(candidate_graph, indent=2, sort_keys=True))
    if args.strict and not candidate_graph["pre_sib_readiness"]["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
