"""Build an ontology-bound candidate graph seed from approved idea intake."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0159"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.ontology-bound-candidate-graph-seed.v0.1"
SEED_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph-seed.v0.1"
INTAKE_CONTRACT_REF = "specgraph.idea-to-spec.event-storming-intake.v0.1"
DEFAULT_INTAKE_PATH = ROOT / "runs" / "idea_event_storming_intake.json"
DEFAULT_ONTOLOGY_IR_PATH = (
    ROOT / "ontology" / "packages" / "specgraph-core" / "generated" / "ontology.normalized.json"
)
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "candidate_spec_graph_seed.json"
MAX_NODE_SLUG_LENGTH = 72
OPERATIONAL_CONSTRAINT_IDS = {
    "constraint.no-direct-canonical-write",
    "constraint.pre-canonical-review-boundary",
}
OPERATIONAL_CONSTRAINT_STATEMENT_MARKERS = (
    "stay candidate-only until repository promotion gates pass",
    "remains pre-canonical until candidate graph validation and approval gates pass",
)

REQUIRED_ONTOLOGY_CLASSES = (
    "Spec",
    "Node",
    "Requirement",
    "AcceptanceCriterion",
    "Constraint",
)
REQUIRED_ACTIVE_FRAME_LIST_FIELDS = (
    "ontology_refs",
    "domain_refs",
    "context_refs",
    "ontology_layer_refs",
    "model_applicability_refs",
)
ACTIVE_FRAME_TEXT_FIELDS = (
    "project",
    "subsystem",
    "lifecycle_phase",
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


def _bounded_slug(value: str, fallback: str, *, max_length: int = MAX_NODE_SLUG_LENGTH) -> str:
    slug = _slug(value, fallback)
    if len(slug) <= max_length:
        return slug
    return slug[:max_length].rstrip("-") or fallback


def _join_bounded_slug(prefix: str, suffix: str, *, max_length: int) -> str:
    suffix_part = f"-{suffix}" if suffix else ""
    prefix_length = max(1, max_length - len(suffix_part))
    return f"{prefix[:prefix_length].rstrip('-')}{suffix_part}"


def _unique_slug(
    value: str,
    *,
    fallback: str,
    source_ref: str,
    used_slugs: set[str],
    max_length: int = MAX_NODE_SLUG_LENGTH,
) -> str:
    slug = _bounded_slug(value, fallback, max_length=max_length)
    if slug not in used_slugs:
        used_slugs.add(slug)
        return slug
    source_slug = _bounded_slug(source_ref, fallback, max_length=32)
    slug_with_source = _join_bounded_slug(slug, source_slug, max_length=max_length)
    if slug_with_source not in used_slugs:
        used_slugs.add(slug_with_source)
        return slug_with_source
    counter = 2
    unique = _join_bounded_slug(slug_with_source, str(counter), max_length=max_length)
    while unique in used_slugs:
        counter += 1
        unique = _join_bounded_slug(slug_with_source, str(counter), max_length=max_length)
    used_slugs.add(unique)
    return unique


def _entry_identity_slug(entry_id: str, *, kind: str, fallback: str) -> str:
    prefix = f"{kind}."
    if entry_id.startswith(prefix):
        return entry_id[len(prefix) :]
    return entry_id or fallback


def _relative_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
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
        "source": "ontology_bound_candidate_graph_seed",
        "evidence": evidence or {},
    }


def _entry_label(entry: dict[str, Any], *fields: str) -> str:
    for field in fields:
        value = _text(entry.get(field))
        if value:
            return value
    return _text(entry.get("id"), "unnamed")


def _is_operational_constraint(entry: dict[str, Any]) -> bool:
    entry_id = _text(entry.get("id"))
    if entry_id in OPERATIONAL_CONSTRAINT_IDS:
        return True
    statement = _text(entry.get("statement")).lower()
    return any(marker in statement for marker in OPERATIONAL_CONSTRAINT_STATEMENT_MARKERS)


def _event_storming(intake: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    source = _dict(intake.get("event_storming"))
    return {
        key: [item for item in _list(value) if isinstance(item, dict)]
        for key, value in source.items()
    }


def _known_intake_refs(event_storming: dict[str, list[dict[str, Any]]]) -> set[str]:
    refs: set[str] = set()
    for entries in event_storming.values():
        for entry in entries:
            if _is_operational_constraint(entry):
                continue
            entry_id = _text(entry.get("id"))
            if entry_id:
                refs.add(entry_id)
    return refs


def _filtered_refs(values: Any, known_refs: set[str]) -> list[str]:
    return [value for value in _text_list(values) if value in known_refs]


def _active_frame_findings(intake: dict[str, Any]) -> list[dict[str, Any]]:
    active_frame = _dict(intake.get("active_frame"))
    missing: list[str] = []
    for field in ACTIVE_FRAME_TEXT_FIELDS:
        if not _text(active_frame.get(field)):
            missing.append(field)
    for field in REQUIRED_ACTIVE_FRAME_LIST_FIELDS:
        if not _text_list(active_frame.get(field)):
            missing.append(field)
    if not missing:
        return []
    return [
        _finding(
            finding_id="active_frame_ontology_context_missing",
            severity="review_required",
            message=(
                "Ontology-bound candidate graph seed requires ontology/domain/context, "
                "ontology layer, and model applicability refs."
            ),
            evidence={"missing": missing},
        )
    ]


def _intake_findings(intake: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if intake.get("artifact_kind") != "idea_event_storming_intake":
        findings.append(
            _finding(
                finding_id="intake_wrong_artifact_kind",
                severity="review_required",
                message="Ontology-bound candidate seed requires idea_event_storming_intake.",
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
                message="Ontology-bound candidate seed cannot be built from an unready intake.",
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
    findings.extend(_active_frame_findings(intake))
    return findings


def _ontology_classes(ontology_ir: dict[str, Any]) -> dict[str, dict[str, Any]]:
    classes: dict[str, dict[str, Any]] = {}
    for entry in _list(ontology_ir.get("classes")):
        if not isinstance(entry, dict):
            continue
        class_id = _text(entry.get("id"))
        if class_id:
            classes[class_id] = entry
    return classes


def _ontology_findings(classes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    missing = [class_id for class_id in REQUIRED_ONTOLOGY_CLASSES if class_id not in classes]
    if not missing:
        return []
    return [
        _finding(
            finding_id="ontology_required_class_missing",
            severity="review_required",
            message="Core ontology IR is missing classes required for candidate graph seeding.",
            evidence={"missing_classes": missing},
        )
    ]


def _class_uri(classes: dict[str, dict[str, Any]], class_id: str) -> str:
    return _text(
        _dict(classes.get(class_id)).get("uri"), f"ontology://specgraph-core/classes/{class_id}"
    )


def _ontology_summary(ontology_ir: dict[str, Any], ontology_ir_path: Path | None) -> dict[str, Any]:
    return {
        "source_ref": _relative_ref(ontology_ir_path) if ontology_ir_path else "unknown",
        "id": ontology_ir.get("id"),
        "namespace": ontology_ir.get("namespace"),
        "version": ontology_ir.get("version"),
        "source_digest": ontology_ir.get("sourceDigest"),
        "class_count": len(_list(ontology_ir.get("classes"))),
        "relation_count": len(_list(ontology_ir.get("relations"))),
        "model_applicability": _dict(ontology_ir.get("modelApplicability")),
    }


def _binding(class_id: str, classes: dict[str, dict[str, Any]], reason: str) -> dict[str, Any]:
    return {
        "term": class_id,
        "ontology_ref": _class_uri(classes, class_id),
        "binding_kind": "core_type",
        "authority": "ontology_ir",
        "reason": reason,
    }


def _ontology_bindings(classes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    reasons = {
        "Spec": "Candidate product boundary maps to a proposed Spec.",
        "Node": "Each generated candidate item is represented as a SpecGraph node.",
        "Requirement": "Commands and constraints become proposed requirements.",
        "AcceptanceCriterion": "Each requirement carries reviewable acceptance criteria.",
        "Constraint": "Event-storming constraints and policies remain constraint-shaped nodes.",
    }
    return [
        _binding(class_id, classes, reasons[class_id]) for class_id in REQUIRED_ONTOLOGY_CLASSES
    ]


def _domain_terms(event_storming: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    terms: list[dict[str, str]] = []
    specs = {
        "actors": ("name", "actor"),
        "domain_events": ("name", "domain_event"),
        "commands": ("name", "command"),
        "policies": ("name", "policy"),
        "vocabulary_questions": ("term", "vocabulary_question"),
    }
    for category, (field, kind) in specs.items():
        for entry in event_storming.get(category, []):
            term = _entry_label(entry, field, "name", "statement", "question")
            entry_id = _text(entry.get("id"))
            if term and entry_id:
                terms.append({"term": term, "source_ref": entry_id, "source_kind": kind})
    return terms


def _ontology_gaps(
    *,
    event_storming: dict[str, list[dict[str, Any]]],
    classes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    known_classes = {class_id.lower() for class_id in classes}
    gaps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for term in _domain_terms(event_storming):
        normalized = _slug(term["term"], term["source_kind"])
        if term["term"].lower() in known_classes or normalized in seen:
            continue
        seen.add(normalized)
        gaps.append(
            {
                "id": f"ontology-gap.{normalized}",
                "kind": "ontology_gap",
                "term": term["term"],
                "source_ref": term["source_ref"],
                "source_kind": term["source_kind"],
                "suggested_action": "confirm_bind_or_promote_domain_term",
                "blocks_candidate_graph": False,
                "statement": (
                    f"Confirm whether `{term['term']}` should bind to an existing ontology "
                    "term or remain a project-local domain term."
                ),
            }
        )
    return gaps


def _node_common(
    *,
    node_id: str,
    title: str,
    kind: str,
    description: str,
    source_event_refs: list[str],
    ontology_refs: list[str],
    active_frame: dict[str, Any],
    requirements: list[dict[str, Any]],
    acceptance_criteria: list[dict[str, Any]],
    gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "title": title,
        "kind": kind,
        "description": description,
        "source_event_refs": source_event_refs,
        "ontology_refs": ontology_refs,
        "domain_refs": _text_list(active_frame.get("domain_refs")),
        "context_refs": _text_list(active_frame.get("context_refs")),
        "ontology_layer_refs": _text_list(active_frame.get("ontology_layer_refs")),
        "model_applicability_refs": _text_list(active_frame.get("model_applicability_refs")),
        "requirements": requirements,
        "acceptance_criteria": acceptance_criteria,
        "claims": [],
        "gaps": gaps or [],
    }


def _requirement(
    *,
    node_slug: str,
    statement: str,
    ontology_refs: list[str],
    source_refs: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    ac_id = f"ac.{node_slug}.reviewable"
    requirement = {
        "id": f"req.{node_slug}.main",
        "statement": statement,
        "ontology_refs": ontology_refs,
        "source_event_refs": source_refs,
        "acceptance_criteria_refs": [ac_id],
    }
    criterion = {
        "id": ac_id,
        "statement": f"Reviewer can verify: {statement}",
        "ontology_refs": ontology_refs,
        "source_event_refs": source_refs,
    }
    return requirement, criterion


def _product_boundary_node(
    *,
    intake: dict[str, Any],
    event_storming: dict[str, list[dict[str, Any]]],
    classes: dict[str, dict[str, Any]],
    active_frame: dict[str, Any],
    known_refs: set[str],
    ontology_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    intent = _dict(intake.get("root_intent"))
    summary = _text(intent.get("summary"), "Product intent summary unavailable.")
    source_refs = sorted(known_refs)
    if not source_refs:
        source_refs = [
            _text(entry.get("id"))
            for entry in event_storming.get("commands", [])
            if _text(entry.get("id"))
        ]
    node_slug = "product-boundary"
    requirement, criterion = _requirement(
        node_slug=node_slug,
        statement=f"The product specification must preserve the root intent: {summary}",
        ontology_refs=[
            _class_uri(classes, "Requirement"),
            _class_uri(classes, "AcceptanceCriterion"),
        ],
        source_refs=source_refs,
    )
    return _node_common(
        node_id="candidate-spec.product-boundary",
        title="Product Boundary",
        kind="product_spec_boundary",
        description=summary,
        source_event_refs=source_refs,
        ontology_refs=[
            _class_uri(classes, "Spec"),
            _class_uri(classes, "Node"),
        ],
        active_frame=active_frame,
        requirements=[requirement],
        acceptance_criteria=[criterion],
        gaps=ontology_gaps,
    )


def _command_nodes(
    *,
    event_storming: dict[str, list[dict[str, Any]]],
    classes: dict[str, dict[str, Any]],
    active_frame: dict[str, Any],
    known_refs: set[str],
    used_slugs: set[str],
) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    events_by_id = {
        _text(entry.get("id")): _entry_label(entry, "name")
        for entry in event_storming.get("domain_events", [])
        if _text(entry.get("id"))
    }
    for index, command in enumerate(event_storming.get("commands", []), start=1):
        command_name = _entry_label(command, "name")
        command_id = _text(command.get("id"), f"command.{_slug(command_name, str(index))}")
        produces = _filtered_refs(command.get("produces_event_refs"), known_refs)
        produced_labels = [events_by_id[ref] for ref in produces if ref in events_by_id]
        outcome = ", ".join(produced_labels) if produced_labels else "a reviewable domain event"
        source_refs = [command_id] + produces
        node_slug = _unique_slug(
            _entry_identity_slug(command_id, kind="command", fallback=command_name),
            fallback=f"command-{index}",
            source_ref=command_id,
            used_slugs=used_slugs,
        )
        statement = f"The product must support `{command_name}` and record {outcome}."
        requirement, criterion = _requirement(
            node_slug=node_slug,
            statement=statement,
            ontology_refs=[
                _class_uri(classes, "Requirement"),
                _class_uri(classes, "AcceptanceCriterion"),
            ],
            source_refs=source_refs,
        )
        nodes.append(
            _node_common(
                node_id=f"candidate-spec.{node_slug}",
                title=command_name,
                kind="behavior_requirement",
                description=statement,
                source_event_refs=source_refs,
                ontology_refs=[
                    _class_uri(classes, "Requirement"),
                    _class_uri(classes, "Node"),
                ],
                active_frame=active_frame,
                requirements=[requirement],
                acceptance_criteria=[criterion],
            )
        )
    return nodes


def _constraint_nodes(
    *,
    event_storming: dict[str, list[dict[str, Any]]],
    classes: dict[str, dict[str, Any]],
    active_frame: dict[str, Any],
    known_refs: set[str],
    used_slugs: set[str],
) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    entries = [
        ("constraint", entry)
        for entry in event_storming.get("constraints", [])
        if not _is_operational_constraint(entry)
    ] + [("policy", entry) for entry in event_storming.get("policies", [])]
    for index, (kind, entry) in enumerate(entries, start=1):
        title = _entry_label(entry, "name", "statement")
        entry_id = _text(entry.get("id"), f"{kind}.{_slug(title, str(index))}")
        related_refs = [entry_id]
        node_slug = _unique_slug(
            _entry_identity_slug(entry_id, kind=kind, fallback=title),
            fallback=f"{kind}-{index}",
            source_ref=entry_id,
            used_slugs=used_slugs,
        )
        related_refs.extend(_filtered_refs(entry.get("trigger_event_refs"), known_refs))
        related_refs.extend(_filtered_refs(entry.get("command_refs"), known_refs))
        statement = _text(entry.get("statement"), f"The product must enforce `{title}`.")
        requirement, criterion = _requirement(
            node_slug=node_slug,
            statement=statement,
            ontology_refs=[
                _class_uri(classes, "Constraint"),
                _class_uri(classes, "Requirement"),
                _class_uri(classes, "AcceptanceCriterion"),
            ],
            source_refs=related_refs,
        )
        nodes.append(
            _node_common(
                node_id=f"candidate-spec.{node_slug}",
                title=title,
                kind=f"{kind}_constraint",
                description=statement,
                source_event_refs=related_refs,
                ontology_refs=[
                    _class_uri(classes, "Constraint"),
                    _class_uri(classes, "Requirement"),
                    _class_uri(classes, "Node"),
                ],
                active_frame=active_frame,
                requirements=[requirement],
                acceptance_criteria=[criterion],
                gaps=[
                    {
                        "id": f"gap.{node_slug}.enforcement-mechanism",
                        "kind": "implementation_gap",
                        "statement": (f"Define the exact enforcement mechanism for this {kind}."),
                        "source_event_refs": related_refs,
                    }
                ],
            )
        )
    return nodes


def _candidate_topology_edges(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    boundary_id = "candidate-spec.product-boundary"
    node_ids = {_text(node.get("id")) for node in nodes}
    if boundary_id not in node_ids:
        return []
    edges: list[dict[str, Any]] = []
    for node in nodes:
        node_id = _text(node.get("id"))
        if not node_id or node_id == boundary_id:
            continue
        node_slug = node_id.removeprefix("candidate-spec.")
        edges.append(
            {
                "id": f"edge.product-boundary.{node_slug}",
                "from": boundary_id,
                "to": node_id,
                "relation": "decomposes_to",
                "source_event_refs": _text_list(node.get("source_event_refs")),
                "derivation": {
                    "kind": "event_storming_product_boundary_decomposition",
                    "source": "ontology_bound_candidate_graph_seed",
                },
            }
        )
    return edges


def _risk_gaps(event_storming: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for index, risk in enumerate(event_storming.get("risks", []), start=1):
        statement = _entry_label(risk, "statement", "name")
        risk_id = _text(risk.get("id"), f"risk.{index}")
        gaps.append(
            {
                "id": f"gap.risk.{_slug(statement, str(index))}",
                "kind": "risk_requires_review",
                "statement": statement,
                "source_event_refs": [risk_id],
                "blocks_candidate_graph": False,
            }
        )
    return gaps


def _candidate_source_ref(intake: dict[str, Any], intake_path: Path | None) -> str:
    source_ref = _text(intake.get("source_ref"))
    if source_ref.startswith("product://") and source_ref.endswith("/root-intent"):
        return source_ref.removesuffix("/root-intent") + "/candidate-spec-graph-seed"
    if source_ref:
        return source_ref + "#candidate-spec-graph-seed"
    if intake_path:
        return _relative_ref(intake_path) + "#candidate-spec-graph-seed"
    return "operator://ontology-bound-candidate-spec-graph-seed-local"


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_accept_ontology_terms": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
    }


def build_ontology_bound_candidate_graph_seed(
    *,
    intake: dict[str, Any],
    ontology_ir: dict[str, Any],
    intake_path: Path | None = None,
    ontology_ir_path: Path | None = None,
) -> dict[str, Any]:
    event_storming = _event_storming(intake)
    known_refs = _known_intake_refs(event_storming)
    active_frame = _dict(intake.get("active_frame"))
    classes = _ontology_classes(ontology_ir)
    ontology_gaps = _ontology_gaps(event_storming=event_storming, classes=classes)
    risk_gaps = _risk_gaps(event_storming)
    findings = _intake_findings(intake) + _ontology_findings(classes)
    blocking_findings = [
        finding for finding in findings if finding.get("severity") == "review_required"
    ]
    ok = not blocking_findings
    used_slugs = {"product-boundary"}
    product_node = _product_boundary_node(
        intake=intake,
        event_storming=event_storming,
        classes=classes,
        active_frame=active_frame,
        known_refs=known_refs,
        ontology_gaps=ontology_gaps + risk_gaps,
    )
    nodes = [product_node]
    nodes.extend(
        _command_nodes(
            event_storming=event_storming,
            classes=classes,
            active_frame=active_frame,
            known_refs=known_refs,
            used_slugs=used_slugs,
        )
    )
    nodes.extend(
        _constraint_nodes(
            event_storming=event_storming,
            classes=classes,
            active_frame=active_frame,
            known_refs=known_refs,
            used_slugs=used_slugs,
        )
    )
    edges = _candidate_topology_edges(nodes)
    return {
        "artifact_kind": "candidate_spec_graph_seed",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": SEED_CONTRACT_REF,
        "source_ref": _candidate_source_ref(intake, intake_path),
        "candidate_graph": {
            "nodes": nodes,
            "edges": edges,
        },
        "source_generation": {
            "artifact_kind": "ontology_bound_candidate_graph_seed_generation",
            "schema_version": SCHEMA_VERSION,
            "proposal_id": PROPOSAL_ID,
            "contract_ref": CONTRACT_REF,
            "generated_at": _now_iso(),
            "source_intake": {
                "artifact_kind": intake.get("artifact_kind"),
                "contract_ref": intake.get("contract_ref"),
                "source_ref": _text(intake.get("source_ref"))
                or (_relative_ref(intake_path) if intake_path else "unknown"),
                "root_intent_sha256": _dict(intake.get("root_intent")).get("text_sha256"),
                "readiness": _dict(intake.get("candidate_graph_readiness")).get("review_state"),
            },
            "ontology": _ontology_summary(ontology_ir, ontology_ir_path),
            "ontology_bindings": _ontology_bindings(classes),
            "ontology_gaps": ontology_gaps,
            "readiness": {
                "ready": ok,
                "review_state": (
                    "ready_for_candidate_graph" if ok else "ontology_seed_review_required"
                ),
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
                "status": "ready_for_candidate_graph" if ok else "ontology_seed_review_required",
                "node_count": len(nodes),
                "edge_count": len(edges),
                "ontology_binding_count": len(_ontology_bindings(classes)),
                "ontology_gap_count": len(ontology_gaps),
                "finding_count": len(blocking_findings),
            },
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", default=DEFAULT_INTAKE_PATH, type=Path)
    parser.add_argument("--ontology-ir", default=DEFAULT_ONTOLOGY_IR_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    intake = load_json(args.intake)
    ontology_ir = load_json(args.ontology_ir)
    seed = build_ontology_bound_candidate_graph_seed(
        intake=intake,
        ontology_ir=ontology_ir,
        intake_path=args.intake,
        ontology_ir_path=args.ontology_ir,
    )
    write_json(seed, args.output)
    summary = _dict(_dict(seed.get("source_generation")).get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('node_count', 0)} nodes, "
        f"{summary.get('ontology_gap_count', 0)} ontology gaps -> {_relative_ref(args.output)}"
    )
    readiness = _dict(_dict(seed.get("source_generation")).get("readiness"))
    if args.strict and readiness.get("ready") is not True:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
