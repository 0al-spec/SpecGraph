#!/usr/bin/env python3
"""Check the pending RFC 0221 review snapshot; never authorize publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

from yaml import YAMLError

from spec_yaml import load_yaml_text

PACKET = "docs/reviews/0221_canonical_materialization_packet.json"
MANIFEST = "docs/reviews/0221_subject_storage/manifest.yaml"
DECISION = "docs/reviews/0221_subject_storage_decision.json"
CONTRACTS = (
    "specs/nodes/SG-SPEC-0051.yaml",
    "specs/nodes/SG-SPEC-0068.yaml",
    "specs/nodes/SG-SPEC-0069.yaml",
)
BLOCKERS = {
    "intent_lineage_unresolved",
    "ingress_decisions_pending",
    "canonical_decisions_pending",
    "workspace_allocation_pending",
    "topology_selection_pending",
    "provenance_bindings_pending",
    "writer_request_pending",
    "evidence_applicability_pending",
    "governed_publication_gate_missing",
}


class PacketError(ValueError):
    """The review snapshot is inconsistent or claims an unearned authority."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PacketError(message)


def packet_digest(packet: dict) -> str:
    scope = {key: value for key, value in packet.items() if key != "approval_scope_sha256"}
    encoded = json.dumps(
        scope, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _path(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    require(not path.is_absolute() and ".." not in path.parts, "input path must be relative")
    resolved = (root / relative).resolve()
    require(resolved.is_relative_to(root.resolve()), "input path escapes selected root")
    return resolved


def _json(root: Path, relative: str) -> dict:
    value = json.loads(_path(root, relative).read_text(), object_pairs_hook=_unique_object)
    require(isinstance(value, dict), f"{relative}: expected JSON object")
    return value


def _yaml(root: Path, relative: str) -> dict:
    return load_yaml_text(_path(root, relative).read_text())


def _contract_blob(root: Path, commit: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{relative}"],
        capture_output=True,
        check=False,
    )
    require(result.returncode == 0, f"contract snapshot unavailable: {relative} at {commit}")
    return result.stdout


def _check_inputs(root: Path, packet: dict) -> None:
    subjects = packet["subjects"]
    manifest = _yaml(root, MANIFEST)
    candidate_paths = [subject["candidate_file"] for subject in subjects]
    declaration = packet["workspace"]["proposed_declaration"].split("#")[0]
    require(
        len(manifest["candidate_paths"]) == 7
        and set(manifest["candidate_paths"]) == {*candidate_paths, declaration},
        "candidate inventory must cover the declaration and all six subjects",
    )
    source_paths = {packet["source_proposal"], MANIFEST, DECISION, declaration, *candidate_paths}
    for subject in subjects:
        source_paths.add(subject["source_proposal_ref"])
        source_paths.update(subject["additional_source_refs"])
    digests = packet["inputs"]["review_tree_file_sha256"]
    require(set(digests) == source_paths, "input digest inventory is incomplete or excessive")
    for relative, digest in digests.items():
        actual = hashlib.sha256(_path(root, relative).read_bytes()).hexdigest()
        require(actual == digest, f"input digest mismatch: {relative}")
    require(
        packet["workspace"]["candidate_sha256"] == digests[declaration],
        "workspace declaration digest disagrees with input map",
    )
    snapshot = packet["inputs"]["contract_snapshot"]
    commit = snapshot["commit"]
    require(commit == packet["prepared_against_commit"], "contract snapshot commit mismatch")
    require(
        len(commit) == 40 and all(c in "0123456789abcdef" for c in commit),
        "contract snapshot needs a full Git SHA",
    )
    require(set(snapshot["file_sha256"]) == set(CONTRACTS), "contract snapshot inventory mismatch")
    for relative, digest in snapshot["file_sha256"].items():
        require(
            hashlib.sha256(_contract_blob(root, commit, relative)).hexdigest() == digest,
            f"contract snapshot digest mismatch: {relative}",
        )


def _check_subjects(root: Path, packet: dict) -> None:
    decision = _json(root, DECISION)
    require(packet["prior_approval_ref"] == DECISION + "#/review", "prior approval ref mismatch")
    require(
        packet["approved_mapping_ref"] == DECISION + "#/mapping_decisions", "mapping ref mismatch"
    )
    require(
        packet["prior_approval_scope_sha256"]
        == packet["inputs"]["approved_mapping_scope_sha256"]
        == decision["approval_scope_sha256"],
        "prior approval scope mismatch",
    )
    workspace = packet["workspace"]["workspace_identity"]
    mappings = decision["mapping_decisions"]
    criteria = {item["destination"]["subject"]["local_subject_id"]: item for item in mappings}
    requirements = {item["requirement_id"] for item in mappings}
    subjects = packet["subjects"]
    ids = [subject["local_subject_id"] for subject in subjects]
    require(
        len(criteria) == 4
        and len(requirements) == 2
        and len(ids) == 6
        and set(ids) == set(criteria) | requirements,
        "subject inventory must match the approved two Requirements and four criteria",
    )
    declaration = _yaml(root, packet["workspace"]["proposed_declaration"].split("#")[0])
    _check_candidate_boundary(declaration)
    require(
        declaration["proposed_record"]["workspace_identity"] == workspace
        and declaration["proposed_record"]["provenance"] is None,
        "workspace declaration must remain an unallocated candidate",
    )
    for subject in subjects:
        local_id = subject["local_subject_id"]
        candidate = _yaml(root, subject["candidate_file"])
        _check_candidate_boundary(candidate)
        record = candidate["proposed_record"]
        expected_class = "criterion" if local_id in criteria else "Requirement"
        expected_identity = {
            "workspace_identity": workspace,
            "subject_class": expected_class,
            "local_subject_id": local_id,
        }
        require(record["subject"] == expected_identity, f"candidate identity mismatch: {local_id}")
        revision = record["revisions"][0]
        require(
            candidate["gate_state"] == "review_pending"
            and candidate["canonical_adoption"] is False
            and len(record["revisions"]) == 1
            and record["current_revision"] == 1
            and revision["number"] == 1
            and revision["provenance"] is None
            and record["current_disposition"] is None
            and record["retained_disposition_transitions"] == [],
            f"candidate must remain a pending origin: {local_id}",
        )
        require(
            subject["subject_class"] == expected_class
            and subject["title"] == record["title"]
            and subject["statement"] == revision["statement"]
            and subject["source_draft_ref"] == subject["candidate_file"] + "#/proposed_record"
            and subject["canonical_target_ref"] == candidate["proposed_path"] + "#/subject"
            and subject["canonical_revision_selection"]
            == {"subject": expected_identity, "mode": "exact", "revision": 1},
            f"subject content or reference mismatch: {local_id}",
        )
        digests = packet["inputs"]["review_tree_file_sha256"]
        require(
            subject["candidate_sha256"] == digests[subject["candidate_file"]]
            and subject["source_proposal_sha256"] == digests[subject["source_proposal_ref"]],
            f"subject source binding mismatch: {local_id}",
        )
        if local_id in criteria:
            mapping = criteria[local_id]
            require(
                mapping["destination"] == subject["canonical_revision_selection"],
                "mapping mismatch",
            )
            require(
                candidate["source_mapping"]["source_occurrence"].split("#")[0]
                == subject["source_proposal_ref"],
                "criterion source proposal mismatch",
            )
            statement_digest = hashlib.sha256(subject["statement"].encode()).hexdigest()
            require(
                subject["source_statement_sha256"]
                == mapping["source_statement_sha256"]
                == statement_digest
                and subject["requirement_membership"] == [],
                f"criterion statement mapping mismatch: {local_id}",
            )
        else:
            require(
                revision["node_fields"]["source_ref"] == subject["source_proposal_ref"],
                "Requirement source proposal mismatch",
            )
            expected = {key for key, item in criteria.items() if item["requirement_id"] == local_id}
            pins = revision["acceptance_criteria_refs"]
            require(
                len(subject["requirement_membership"]) == len(expected)
                and set(subject["requirement_membership"]) == expected
                and len(pins) == len(expected)
                and {pin["subject"]["local_subject_id"] for pin in pins} == expected
                and all(
                    pin == criteria[pin["subject"]["local_subject_id"]]["destination"]
                    for pin in pins
                ),
                f"exact Requirement membership mismatch: {local_id}",
            )


def _check_candidate_boundary(candidate: dict) -> None:
    require(
        candidate["artifact_kind"] == "subject_storage_candidate"
        and candidate["source_lane"] == "SpecDraft"
        and candidate["gate_state"] == "review_pending"
        and candidate["canonical_adoption"] is False
        and candidate["canonical_readiness"] == "not_evaluated"
        and candidate["ready_for_materialization"] is False,
        "all seven candidate envelopes must remain pending and unadopted",
    )


def _check_transitions(packet: dict) -> None:
    records = packet["transition_records"]
    by_id = {record["transition_record_id"]: record for record in records}
    require(len(records) == len(by_id) == 12, "need twelve unique paired transition records")
    identifiers = {record["transition_identifier"] for record in records}
    require(len(identifiers) == 12, "transition identifiers must be unique")
    for subject in packet["subjects"]:
        local_id = subject["local_subject_id"]
        ingress_id = "0221-ingress-" + local_id
        for prefix, edge, source, target, token in (
            (
                "ingress",
                "proposal -> spec_draft",
                subject["source_proposal_ref"],
                subject["source_draft_ref"],
                "proposal_ingress",
            ),
            (
                "canonical",
                "spec_draft -> canonical_artifact",
                subject["source_draft_ref"],
                subject["canonical_target_ref"],
                "canonical_materialization",
            ),
        ):
            record = by_id[f"0221-{prefix}-{local_id}"]
            require(
                record["promotion_edge"] == edge
                and record["source_ref"] == source
                and record["target_ref"] == target
                and record["transition_identifier"] == f"rfc0221:{token}:{local_id}:v1"
                and record["gate_type"] == "review"
                and record["state"] == "review_pending",
                f"transition binding mismatch: {local_id}/{prefix}",
            )
            require(
                all(
                    record[field] is None
                    for field in (
                        "reviewer_or_decider",
                        "decision_timestamp",
                        "outcome",
                        "rationale",
                    )
                )
                and set(record["review_record"])
                == {
                    "reviewer",
                    "reviewer_authority",
                    "decision_timestamp",
                    "outcome",
                    "rationale",
                    "provenance",
                }
                and all(value is None for value in record["review_record"].values()),
                "decisions belong in a separate artifact; packet templates must remain pending",
            )
            if prefix == "ingress":
                require(
                    record["intent_lineage_ref"] is None
                    and record["intent_lineage_state"] == "unresolved",
                    "absent Intent lineage must remain an explicit unresolved blocker",
                )
            else:
                require(
                    record["ingress_record_ref"]
                    == PACKET + "#/transition_records/" + str(records.index(by_id[ingress_id]))
                    and record["target_revision_selection"]
                    == subject["canonical_revision_selection"],
                    "canonical transition must bind its ingress and exact revision-1 target",
                )


def _check_pending_boundary(packet: dict) -> None:
    require(
        type(packet["schema_version"]) is int
        and packet["schema_version"] == 1
        and packet["artifact_kind"] == "rfc0221_canonical_materialization_packet"
        and packet["authority"] == "agent_prepared_for_human_review"
        and packet["gate_state"] == "review_pending",
        "packet must remain a pending review artifact",
    )
    for field in ("canonical_adoption", "canonical_mutations_allowed", "ready_for_materialization"):
        require(packet[field] is False, f"unearned authority flag: {field}")
    require(packet["canonical_readiness"] == "not_evaluated", "readiness must remain unevaluated")
    require(
        packet["governing_contract"] == CONTRACTS[0] and packet["storage_contract"] == CONTRACTS[2],
        "governing contract references mismatch",
    )
    boundary = packet["separate_boundaries"]
    require(boundary["canonical_readiness"] == "not_evaluated", "separate readiness mismatch")
    require(
        all(value is False for key, value in boundary.items() if key != "canonical_readiness"),
        "separate boundaries cannot acquire authorization",
    )
    require(
        packet["publication_authorization"] is None, "publication authorization must remain absent"
    )
    workspace = packet["workspace"]
    require(
        workspace["declaration_provenance"] is None
        and workspace["allocation_state"] == "approved_plan_unallocated"
        and workspace["source_ref_initialization"]
        == {"base_commit": None, "decision_ref": None, "state": "pending"},
        "workspace allocation and source initialization must remain pending",
    )
    request = packet["writer_request"]
    require(
        request["state"] == "not_prepared_pending_transition_decisions"
        and request["source_ref"] == workspace["source_ref"]
        and all(
            request[field] is None
            for field in (
                "expected_commit",
                "recorded_at",
                "expected_source_file_sha256",
                "changes",
                "workspace_declaration",
                "request_sha256",
                "topology_selection",
            )
        ),
        "writer request must remain an unusable placeholder",
    )
    require(
        packet["decision_lifecycle"]
        == {
            "packet_mutation_after_approval": "forbidden",
            "decision_storage": "separate_artifact",
            "decision_binding": [
                "packet_path",
                "packet_sha256",
                "approval_scope_sha256",
                "reviewed_head",
            ],
            "scope_change": "new_packet_version_requires_new_approval",
            "writer_request_storage": "separate_artifact_with_its_own_digest",
        },
        "immutable packet and separate decision lifecycle required",
    )
    require(set(packet["review_blocker_codes"]) == BLOCKERS, "review blocker inventory mismatch")
    require(
        packet["topology_review"]["state"] == "pending"
        and packet["topology_review"]["selection"] is None
        and packet["topology_review"]["decision_ref"] is None
        and set(packet["topology_review"]["required_selection_fields"])
        == {
            "workspace_identity",
            "dataset_identity",
            "topology_ref",
            "governance_evidence_ref",
            "requirements",
        },
        "topology review must remain explicitly pending",
    )
    bindings = packet["provenance_binding_review"]
    require(
        bindings["state"] == "pending"
        and bindings["declaration_decision_ref"] is None
        and len(bindings["subject_bindings"]) == 6
        and {item["local_subject_id"] for item in bindings["subject_bindings"]}
        == {item["local_subject_id"] for item in packet["subjects"]}
        and all(
            item["origin_decision_ref"] is None and item["activation_decision_ref"] is None
            for item in bindings["subject_bindings"]
        ),
        "all six origin/activation provenance bindings must remain pending",
    )
    require(
        packet["governed_publication_gate"]["state"] == "not_implemented"
        and packet["governed_publication_gate"]["may_publish"] is False
        and packet["governed_publication_gate"]["writer_authorization_verification"]
        == "operator_supplied_not_attested",
        "packet consistency must not be presented as a governed publication gate",
    )


def validate(root: Path, packet_path: str = PACKET) -> list[str]:
    try:
        packet = _json(root, packet_path)
        require(packet["approval_scope_sha256"] == packet_digest(packet), "packet digest mismatch")
        _check_pending_boundary(packet)
        _check_inputs(root, packet)
        _check_subjects(root, packet)
        _check_transitions(packet)
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, YAMLError) as exc:
        return [f"invalid materialization packet: {exc}"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--packet", default=PACKET)
    args = parser.parse_args(argv)
    errors = validate(args.root, args.packet)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Materialization review packet consistent; review_pending; publication not authorized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
