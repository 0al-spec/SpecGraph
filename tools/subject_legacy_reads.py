"""Read-only inventory of candidate-local records and unassigned legacy text.

Source locators identify occurrences for inspection, never durable subjects.
This module does not allocate IDs, bind workspaces, or infer migration mappings.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CandidateScope:
    source_ref: str
    node_id: str


@dataclass(frozen=True)
class CandidateNode:
    scope: CandidateScope
    locator: str
    candidate_source_id: str | None = None


@dataclass(frozen=True)
class CandidateRecord:
    scope: CandidateScope
    kind: Literal["requirement", "criterion"]
    id: str
    statement: str
    acceptance_criteria_refs: tuple[str, ...]
    locator: str


@dataclass(frozen=True)
class LegacyAcceptanceOccurrence:
    source_ref: str
    locator: str
    statement: str


@dataclass(frozen=True)
class CompatibilityDiagnostic:
    code: str
    locator: str
    message: str


@dataclass(frozen=True)
class CompatibilityInventory:
    source_ref: str
    nodes: tuple[CandidateNode, ...]
    records: tuple[CandidateRecord, ...]
    legacy_acceptance: tuple[LegacyAcceptanceOccurrence, ...]
    diagnostics: tuple[CompatibilityDiagnostic, ...]


def parse_compatibility_document(
    data: Mapping[str, object], source_ref: str
) -> CompatibilityInventory:
    """Inspect existing input shapes without normalizing their IDs or text.

    Invalid entries produce diagnostics. Duplicate records remain visible in the
    inventory, accompanied by ambiguity diagnostics; callers must not select one.
    Absent optional lists are empty, while explicitly malformed lists are errors.
    """
    nodes: list[CandidateNode] = []
    records: list[CandidateRecord] = []
    legacy: list[LegacyAcceptanceOccurrence] = []
    diagnostics: list[CompatibilityDiagnostic] = []
    seen_nodes: dict[str, Mapping[str, object]] = {}

    def issue(code: str, locator: str, message: str) -> None:
        diagnostics.append(CompatibilityDiagnostic(code, locator, message))

    def text(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def entries(container: Mapping[str, object], field: str, locator: str) -> list[object]:
        value = container.get(field, [])
        if not isinstance(value, list):
            issue("malformed_list", locator, f"{field} must be a list")
            return []
        return value

    def candidate_node(
        node: Mapping[str, object], locator: str, *, materialized: bool = False
    ) -> None:
        node_id = node.get("id")
        if not text(node_id):
            issue("missing_candidate_id", f"{locator}.id", "Candidate node requires an authored ID")
            return
        previous_node = seen_nodes.get(node_id)
        if previous_node is not None:
            code = (
                "duplicate_candidate_identity"
                if previous_node == node
                else "conflicting_candidate_definition"
            )
            issue(code, locator, "Candidate node ID is repeated within this source artifact")
        else:
            seen_nodes[node_id] = node
        scope = CandidateScope(source_ref, node_id)
        body = node
        source_id = None
        if materialized:
            body = node["specification"]
            source_id = body.get("candidate_source_id")
            if source_id is not None and not text(source_id):
                issue(
                    "malformed_candidate_id",
                    "$.specification.candidate_source_id",
                    "candidate_source_id must be non-empty text",
                )
                source_id = None
        nodes.append(CandidateNode(scope, locator, source_id))
        body_locator = f"{locator}.specification" if materialized else locator
        local_records: list[CandidateRecord] = []
        seen_records: dict[str, tuple[str, Mapping[str, object]]] = {}
        for field, kind in (("requirements", "requirement"), ("acceptance_criteria", "criterion")):
            for index, entry in enumerate(entries(body, field, f"{body_locator}.{field}")):
                entry_locator = f"{body_locator}.{field}[{index}]"
                if not isinstance(entry, Mapping):
                    issue(
                        "malformed_candidate_record",
                        entry_locator,
                        "Candidate record must be a mapping",
                    )
                    continue
                entry_id = entry.get("id")
                if not text(entry_id):
                    issue(
                        "missing_candidate_id",
                        f"{entry_locator}.id",
                        "Candidate record requires an authored ID",
                    )
                    continue
                previous = seen_records.get(entry_id)
                if previous is not None:
                    code = (
                        "duplicate_candidate_identity"
                        if previous == (kind, entry)
                        else "conflicting_candidate_definition"
                    )
                    issue(
                        code, entry_locator, "Candidate record ID is repeated within its node scope"
                    )
                else:
                    seen_records[entry_id] = (kind, entry)
                statement = entry.get("statement")
                if not text(statement):
                    issue(
                        "malformed_candidate_statement",
                        f"{entry_locator}.statement",
                        "statement must be non-empty text",
                    )
                    continue
                refs: list[str] = []
                for ref_index, ref in enumerate(
                    entries(
                        entry,
                        "acceptance_criteria_refs",
                        f"{entry_locator}.acceptance_criteria_refs",
                    )
                ):
                    if not text(ref):
                        issue(
                            "malformed_candidate_reference",
                            f"{entry_locator}.acceptance_criteria_refs[{ref_index}]",
                            "Criterion reference must be non-empty text",
                        )
                    else:
                        refs.append(ref)
                local_records.append(
                    CandidateRecord(scope, kind, entry_id, statement, tuple(refs), entry_locator)
                )
        criterion_ids = {record.id for record in local_records if record.kind == "criterion"}
        for record in local_records:
            if record.kind == "requirement":
                for ref in record.acceptance_criteria_refs:
                    if ref not in criterion_ids:
                        issue(
                            "unknown_candidate_criterion_reference",
                            record.locator,
                            f"Unknown node-local criterion reference: {ref}",
                        )
        records.extend(local_records)

    if not text(source_ref):
        issue("invalid_source_ref", "$", "source_ref must be non-empty text")
    if not isinstance(data, Mapping):
        issue("malformed_document", "$", "Document must be a mapping")
    else:
        for index, statement in enumerate(entries(data, "acceptance", "$.acceptance")):
            locator = f"$.acceptance[{index}]"
            if not text(statement):
                issue(
                    "malformed_legacy_acceptance",
                    locator,
                    "Legacy acceptance must be non-empty text",
                )
            else:
                legacy.append(LegacyAcceptanceOccurrence(source_ref, locator, statement))
        if "candidate_graph" in data:
            graph = data["candidate_graph"]
            if not isinstance(graph, Mapping):
                issue(
                    "malformed_candidate_graph",
                    "$.candidate_graph",
                    "candidate_graph must be a mapping",
                )
            else:
                for index, node in enumerate(entries(graph, "nodes", "$.candidate_graph.nodes")):
                    locator = f"$.candidate_graph.nodes[{index}]"
                    if not isinstance(node, Mapping):
                        issue(
                            "malformed_candidate_node", locator, "Candidate node must be a mapping"
                        )
                    else:
                        candidate_node(node, locator)
        if "specification" in data:
            body = data["specification"]
            if not isinstance(body, Mapping):
                issue(
                    "malformed_specification", "$.specification", "specification must be a mapping"
                )
            elif any(
                field in body
                for field in ("requirements", "acceptance_criteria", "candidate_source_id")
            ):
                candidate_node(data, "$", materialized=True)
    return CompatibilityInventory(
        source_ref, tuple(nodes), tuple(records), tuple(legacy), tuple(diagnostics)
    )
