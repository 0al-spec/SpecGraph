"""Resolve scope-bound human decisions before the subject writer publishes.

Evidence is selected from immutable Git commits. Attribution is checked against
recorded human review artifacts; identity/signature attestation is outside v1.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from yaml import YAMLError

from spec_yaml import load_yaml_text
from subject_canonical_source import parse_topology_selection
from subject_human_approval_spec import HUMAN_APPROVAL_SPEC
from subject_publication_context import (
    HumanApprovalContext,
    ReviewedRecordContext,
    TransitionApprovalContext,
    WorkspaceAllocationContext,
)
from subject_read_model_io import SubjectDocumentError, _object
from subject_reviewed_record_spec import REVIEWED_RECORD_SPEC
from subject_source_git import git_command, require_commit_id
from subject_transition_approval_spec import TRANSITION_APPROVAL_SPEC
from subject_workspace_allocation_spec import WORKSPACE_ALLOCATION_SPEC


class PublicationGovernanceError(SubjectDocumentError):
    """Missing or inconsistent publication decisions; no source ref may advance."""


if TYPE_CHECKING:
    from subject_source_write import SubjectSourceWriteRequest, SubjectWriteAuthorization


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PublicationGovernanceError(f"publication governance: {message}")


def scope_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


@dataclass(frozen=True)
class SubjectPublicationEvidence:
    repository_root: Path
    evidence_commit: str
    decision_path: str

    def __post_init__(self) -> None:
        try:
            require_commit_id(self.evidence_commit)
        except SubjectDocumentError as exc:
            raise PublicationGovernanceError(f"publication governance: {exc}") from exc
        require(isinstance(self.repository_root, Path), "evidence repository must be explicit")
        _path(self.decision_path)


def parse_publication_evidence(value: object) -> SubjectPublicationEvidence:
    try:
        data = _object(
            value,
            {
                "schema_version",
                "artifact_kind",
                "repository_root",
                "evidence_commit",
                "decision_path",
            },
        )
        require(
            type(data["schema_version"]) is int and data["schema_version"] == 1,
            "unsupported evidence version",
        )
        require(data["artifact_kind"] == "subject_publication_evidence", "wrong evidence kind")
        return SubjectPublicationEvidence(
            Path(data["repository_root"]), data["evidence_commit"], data["decision_path"]
        )
    except PublicationGovernanceError:
        raise
    except (ValueError, TypeError, KeyError) as exc:
        raise PublicationGovernanceError(
            f"publication governance: invalid selection: {exc}"
        ) from exc


def load_publication_evidence(path: Path) -> SubjectPublicationEvidence:
    """Classify all selection-file failures at the governance I/O boundary."""
    try:
        return parse_publication_evidence(load_yaml_text(path.read_text(encoding="utf-8")))
    except PublicationGovernanceError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, YAMLError) as exc:
        raise PublicationGovernanceError(
            f"publication governance: unreadable selection: {exc}"
        ) from exc


def _path(value: str) -> str:
    require(isinstance(value, str) and bool(value), "missing repository-relative evidence path")
    path = PurePosixPath(value)
    require(
        not path.is_absolute() and ".." not in path.parts and str(path) == value,
        "evidence path must be canonical and repository-relative",
    )
    return value


@dataclass(frozen=True)
class DecisionSnapshot:
    repository: Path
    commit: str

    def read(self, path: str) -> bytes:
        _path(path)
        require_commit_id(self.commit)
        require(
            not self.repository.is_symlink() and self.repository.is_dir(),
            "evidence repository must be a real directory",
        )
        require(
            git_command(self.repository, "cat-file", "-t", self.commit).stdout.strip() == b"commit",
            "evidence selection must be a commit",
        )
        entries = git_command(self.repository, "ls-tree", "-z", self.commit, "--", path).stdout
        require(bool(entries), f"missing evidence: {path}")
        metadata, name = entries.rstrip(b"\0").split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        require(
            name.decode() == path and kind == "blob" and mode in {"100644", "100755"},
            "evidence must be a regular Git blob, never a symlink",
        )
        return git_command(self.repository, "cat-file", "blob", oid).stdout

    def resolve(self, reference: str) -> object:
        require(isinstance(reference, str) and bool(reference), "missing evidence reference")
        path, _, pointer = reference.partition("#")
        value = load_yaml_text(self.read(path).decode("utf-8"))
        if pointer:
            require(pointer.startswith("/"), "evidence fragment must be a JSON pointer")
            for token in pointer[1:].split("/"):
                key = token.replace("~1", "/").replace("~0", "~")
                if isinstance(value, list):
                    require(
                        re.fullmatch(r"0|[1-9][0-9]*", key) is not None,
                        "array reference must use a canonical nonnegative index",
                    )
                    value = value[int(key)]
                else:
                    value = value[key]
        return value


def _review(record: dict, snapshot: DecisionSnapshot) -> dict:
    review = record["review"]
    require(isinstance(review, dict), "missing actual human review")
    scope = {key: value for key, value in record.items() if key != "review"}
    require(review["scope_sha256"] == scope_digest(scope), "human review covers a different scope")
    require(
        HUMAN_APPROVAL_SPEC.is_satisfied_by(
            HumanApprovalContext(review["reviewer_authority"], review["outcome"])
        ),
        "human approval required",
    )
    for field in ("reviewer", "decision_timestamp", "rationale", "source_quote", "source_ref"):
        require(
            isinstance(review[field], str) and bool(review[field].strip()),
            f"review requires {field}",
        )
    require(
        datetime.fromisoformat(review["decision_timestamp"].replace("Z", "+00:00")).tzinfo
        is not None,
        "review timestamp requires a timezone",
    )
    source = snapshot.resolve(review["source_ref"])
    require(
        source["artifact_kind"] == "subject_human_review_record"
        and type(source["schema_version"]) is int
        and source["schema_version"] == 1,
        "human review source has wrong kind/version",
    )
    require(source["review"] == review, "review attribution disagrees with its recorded source")
    return review


def _packet(snapshot: DecisionSnapshot, binding: dict) -> tuple[dict, DecisionSnapshot]:
    reviewed = DecisionSnapshot(snapshot.repository, binding["reviewed_head"])
    content = reviewed.read(binding["packet_path"])
    require(
        hashlib.sha256(content).hexdigest() == binding["packet_sha256"],
        "reviewed packet bytes changed",
    )
    packet = load_yaml_text(content.decode())
    require(
        packet["artifact_kind"]
        in {"rfc0221_canonical_materialization_packet", "subject_publication_review_packet"}
        and type(packet["schema_version"]) is int
        and packet["schema_version"] == 1,
        "wrong review packet kind/version",
    )
    scope = {key: value for key, value in packet.items() if key != "approval_scope_sha256"}
    require(
        scope_digest(scope) == packet["approval_scope_sha256"] == binding["approval_scope_sha256"],
        "approval does not bind the exact packet scope",
    )
    require(
        packet["gate_state"] == "review_pending" and packet["canonical_mutations_allowed"] is False,
        "review packet must be immutable pending preparation",
    )
    for path, digest in packet["inputs"]["review_tree_file_sha256"].items():
        require(
            hashlib.sha256(reviewed.read(path)).hexdigest() == digest,
            f"review input changed: {path}",
        )
    if "contract_snapshot" in packet["inputs"]:
        contract = packet["inputs"]["contract_snapshot"]
        selected = DecisionSnapshot(snapshot.repository, contract["commit"])
        for path, digest in contract["file_sha256"].items():
            require(
                hashlib.sha256(selected.read(path)).hexdigest() == digest,
                "governing contract snapshot differs from reviewed scope",
            )
    return packet, reviewed


def _input(packet: dict, reviewed: DecisionSnapshot, reference: str) -> object:
    path = reference.split("#")[0]
    require(
        path in packet["inputs"]["review_tree_file_sha256"],
        f"evidence is outside the reviewed input inventory: {path}",
    )
    return reviewed.resolve(reference)


def _lineage(
    packet: dict, reviewed: DecisionSnapshot, transition: dict, snapshot: DecisionSnapshot
) -> None:
    require(
        isinstance(transition.get("intent_lineage_ref"), str)
        and bool(transition["intent_lineage_ref"].strip()),
        "motivating Intent lineage is unresolved",
    )
    lineage = _input(packet, reviewed, transition["intent_lineage_ref"])
    require(lineage["artifact_kind"] == "subject_intent_lineage", "missing authored Intent lineage")
    require(
        lineage["source_proposal_ref"] == transition["source_ref"],
        "lineage belongs to another proposal",
    )
    require(
        lineage["source_proposal_sha256"]
        == packet["inputs"]["review_tree_file_sha256"][transition["source_ref"]],
        "lineage binds another proposal revision",
    )
    _review(lineage, snapshot)
    intent = _input(packet, reviewed, lineage["intent_ref"])
    require(
        intent["artifact_kind"] == "intent_draft" and bool(intent["statement"].strip()),
        "lineage must resolve a substantive IntentDraft",
    )
    require(
        intent["provenance"]["authority_class"] == "authored"
        and intent["provenance"]["actor_id"].startswith("human:")
        and bool(intent["provenance"]["source_ref"].strip()),
        "IntentDraft attribution is absent",
    )
    # The original human source must exist in the selected review snapshot.
    source = _input(packet, reviewed, intent["provenance"]["source_ref"])
    require(
        source["artifact_kind"] == "human_intent_record"
        and source["actor_id"] == intent["provenance"]["actor_id"]
        and bool(source["text"].strip()),
        "Intent source must retain human attribution and text",
    )


def _transitions(
    packet: dict, decisions: dict, reviewed: DecisionSnapshot, snapshot: DecisionSnapshot
) -> dict[str, dict]:
    templates = packet["transition_records"]
    records = decisions["transition_decisions"]
    require(
        len(templates) == len(records) == 2 * len(packet["subjects"]),
        "incomplete paired transition inventory",
    )
    by_id = {record["transition_record_id"]: record for record in records}
    require(
        len(by_id) == len(records)
        and len({t["transition_record_id"] for t in templates}) == len(templates),
        "duplicate transition records",
    )
    require(
        len({r["transition_identifier"] for r in records}) == len(records),
        "duplicate transition identifiers",
    )
    fields = (
        "transition_record_id",
        "transition_identifier",
        "promotion_edge",
        "gate_type",
        "source_ref",
        "target_ref",
    )
    for template in templates:
        record = by_id[template["transition_record_id"]]
        require(
            all(record[field] == template[field] for field in fields),
            "transition decision differs from the reviewed template",
        )
        require(
            template["state"] == "review_pending" and template["outcome"] is None,
            "packet templates cannot be rewritten as decisions",
        )
        review = _review(record, snapshot)
        require(
            TRANSITION_APPROVAL_SPEC.is_satisfied_by(
                TransitionApprovalContext(
                    record["gate_type"],
                    record["outcome"],
                    record["reviewer_or_decider"],
                    review["reviewer"],
                    record["decision_timestamp"],
                    review["decision_timestamp"],
                    record["rationale"],
                    review["rationale"],
                )
            ),
            "incomplete or unapproved transition",
        )
        if record["promotion_edge"] == "proposal -> spec_draft":
            require(
                record["intent_lineage_ref"] == template["intent_lineage_ref"],
                "decision cannot silently supply unreviewed Intent lineage",
            )
            _lineage(packet, reviewed, record, snapshot)
        else:
            require(
                record["promotion_edge"] == "spec_draft -> canonical_artifact",
                "unsupported promotion shortcut",
            )
            require(
                record["target_revision_selection"] == template["target_revision_selection"],
                "canonical decision changes the reviewed revision target",
            )
    return by_id


def _effect(
    snapshot: DecisionSnapshot,
    decisions: dict,
    evidence: SubjectPublicationEvidence,
    reference: str,
    effect: str,
    selection: dict | None = None,
) -> dict:
    require(
        reference.startswith(evidence.decision_path + "#/effects/"),
        "provenance must resolve an effect in the selected decision artifact",
    )
    record = snapshot.resolve(reference)
    require(
        record in decisions["effects"] and record["effect"] == effect,
        f"decision does not authorize {effect}",
    )
    if selection is not None:
        require(record["subject"] == selection, "effect belongs to another subject/revision")
    _review(record, snapshot)
    return record


def _verify_publication(
    evidence: SubjectPublicationEvidence | None,
    request: SubjectSourceWriteRequest,
    authorization: SubjectWriteAuthorization,
) -> dict:
    require(
        isinstance(evidence, SubjectPublicationEvidence), "resolved publication evidence required"
    )
    snapshot = DecisionSnapshot(evidence.repository_root, evidence.evidence_commit)
    decisions = snapshot.resolve(evidence.decision_path)
    require(
        decisions["artifact_kind"] == "subject_publication_decisions"
        and type(decisions["schema_version"]) is int
        and decisions["schema_version"] == 1,
        "schema approval is not subject-publication permission",
    )
    _review(decisions["packet_approval"], snapshot)
    binding = decisions["packet_binding"]
    require(
        decisions["packet_approval"]["packet_binding"] == binding,
        "packet approval binding mismatch",
    )
    packet, reviewed = _packet(snapshot, binding)
    workspace = packet["workspace"]
    require(
        workspace["workspace_identity"] == request.topology.workspace_identity
        and workspace["source_ref"] == request.source_ref,
        "workspace/source ref scope mismatch",
    )
    records = _transitions(packet, decisions, reviewed, snapshot)
    subjects = packet["subjects"]
    require(
        len(subjects) == len(request.changes)
        and len({s["local_subject_id"] for s in subjects}) == len(subjects),
        "request subject inventory differs from reviewed scope",
    )
    used = set()
    used_transitions = set()
    for change in request.changes:
        subject = next(
            (
                s
                for s in subjects
                if s["canonical_revision_selection"]["subject"] == asdict(change.subject)
            ),
            None,
        )
        require(subject is not None, "request contains an unreviewed subject")
        selection = subject["canonical_revision_selection"]
        document = load_yaml_text(change.document_yaml)
        revision = document["revisions"][-1]
        require(
            selection
            == {"subject": asdict(change.subject), "mode": "exact", "revision": revision["number"]},
            "request revision differs from reviewed exact target",
        )
        draft = _input(packet, reviewed, subject["source_draft_ref"])
        require(
            subject["source_draft_ref"] == subject["candidate_file"] + "#/proposed_record"
            and subject["candidate_sha256"]
            == packet["inputs"]["review_tree_file_sha256"][subject["candidate_file"]]
            and subject["canonical_target_ref"] == change.path + "#/subject"
            and revision["statement"] == subject["statement"],
            "request target differs from reviewed draft",
        )
        require(
            REVIEWED_RECORD_SPEC.is_satisfied_by(
                ReviewedRecordContext(scope_digest(draft), scope_digest(document))
            ),
            "request complete record differs from reviewed draft",
        )
        ingress = [
            r
            for r in records.values()
            if r["promotion_edge"] == "proposal -> spec_draft"
            and r["target_ref"] == subject["source_draft_ref"]
        ]
        canonical = [
            r
            for r in records.values()
            if r["promotion_edge"] == "spec_draft -> canonical_artifact"
            and r["source_ref"] == subject["source_draft_ref"]
            and r["target_ref"] == subject["canonical_target_ref"]
        ]
        require(
            len(ingress) == len(canonical) == 1,
            "missing unique approved ingress/canonical transition",
        )
        require(
            ingress[0]["source_ref"] == subject["source_proposal_ref"]
            and canonical[0]["ingress_transition_id"] == ingress[0]["transition_record_id"]
            and canonical[0]["target_revision_selection"] == selection,
            "canonical transition lacks its approved ingress or exact target",
        )
        used_transitions.update(
            [ingress[0]["transition_record_id"], canonical[0]["transition_record_id"]]
        )
        effect = _effect(
            snapshot, decisions, evidence, revision["provenance"], change.operation, selection
        )
        require(
            effect["canonical_transition_id"] == canonical[0]["transition_record_id"],
            "revision provenance does not authorize this canonical transition",
        )
        used.add(revision["provenance"])
        if change.operation == "origin":
            events = document["retained_disposition_transitions"]
            require(
                len(events) == 1 and events[0]["transition"] == "activation",
                "origin needs one activation",
            )
            _effect(snapshot, decisions, evidence, events[0]["provenance"], "activation", selection)
            used.add(events[0]["provenance"])
    require(used_transitions == set(records), "unused or mismatched transition decisions")
    if request.workspace_declaration_yaml is not None:
        declaration = load_yaml_text(request.workspace_declaration_yaml)
        allocation = _effect(
            snapshot, decisions, evidence, declaration["provenance"], "workspace_allocation"
        )
        require(
            WORKSPACE_ALLOCATION_SPEC.is_satisfied_by(
                WorkspaceAllocationContext(
                    allocation=allocation,
                    requested_workspace_identity=request.topology.workspace_identity,
                    requested_source_ref=request.source_ref,
                    requested_expected_commit=request.expected_commit,
                    requested_declaration_sha256=hashlib.sha256(
                        request.workspace_declaration_yaml.encode()
                    ).hexdigest(),
                )
            ),
            "workspace allocation covers a different bootstrap",
        )
        reviewed_declaration = _input(packet, reviewed, workspace["proposed_declaration"])
        require(
            REVIEWED_RECORD_SPEC.is_satisfied_by(
                ReviewedRecordContext(scope_digest(reviewed_declaration), scope_digest(declaration))
            ),
            "request declaration differs from reviewed candidate",
        )
        used.add(declaration["provenance"])
    topology = _effect(
        snapshot, decisions, evidence, decisions["topology_decision_ref"], "topology"
    )
    require(
        asdict(parse_topology_selection(topology["selection"])) == asdict(request.topology),
        "unapproved dataset/topology selection",
    )
    publication = decisions["publication"]
    review = _review(publication, snapshot)
    require(
        publication["request_sha256"] == request.digest() == authorization.request_sha256,
        "publication decision covers another exact request",
    )
    require(
        authorization.decision_ref == evidence.decision_path + "#/publication"
        and authorization.reviewer == review["reviewer"]
        and authorization.recorded_at == review["decision_timestamp"],
        "writer authorization differs from the actual publication decision",
    )
    require(
        set(publication["transition_refs"]) == used == set(authorization.transition_refs)
        and len(publication["transition_refs"]) == len(used),
        "publication effect-reference coverage mismatch",
    )
    require(
        used | {decisions["topology_decision_ref"]}
        == {evidence.decision_path + f"#/effects/{i}" for i in range(len(decisions["effects"]))},
        "unrequested effects in publication decisions",
    )
    return {
        "authorization_verification": "scope_bound_recorded_decisions_verified_not_attested",
        "governance_evidence_commit": evidence.evidence_commit,
        "reviewed_head": binding["reviewed_head"],
        "approval_scope_sha256": binding["approval_scope_sha256"],
        "reviewer_identity_attested": False,
    }


def verify_publication(
    evidence: SubjectPublicationEvidence | None,
    request: SubjectSourceWriteRequest,
    authorization: SubjectWriteAuthorization,
) -> dict:
    try:
        return _verify_publication(evidence, request, authorization)
    except PublicationGovernanceError:
        raise
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, YAMLError) as exc:
        raise PublicationGovernanceError(
            f"publication governance: unresolved evidence: {exc}"
        ) from exc
