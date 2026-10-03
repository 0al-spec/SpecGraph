"""Synthetic Git approvals prove governance scope checks and a no-write failure boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from spec_yaml import dump_canonical_yaml  # noqa: E402
from subject_publication import (  # noqa: E402
    PublicationGovernanceError,
    SubjectPublicationEvidence,
    scope_digest,
    verify_publication,
)
from subject_source_git import git_command, selected_source_commit  # noqa: E402
from subject_source_write import (  # noqa: E402
    SubjectWriteAuthorization,
    main,
    parse_write_request,
    write_subject_source,
)
from test_subject_canonical_source import (  # noqa: E402
    AC_PATH,
    REQ_PATH,
    get,
    topology_payload,
)
from test_subject_canonical_source import (  # noqa: E402
    source as source,
)
from test_subject_source_write import (  # noqa: E402
    RECORDED_AT,
    SOURCE_REF,
    origin_change,
    request_payload,
    revision_change,
    seed_repository,
)

DECISION = "docs/publication_decisions.json"
PACKET = "docs/publication_packet.json"
REVIEWER = "human:fixture-author"


def write_json(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2))


def commit(root):
    git_command(root, "add", ".")
    git_command(root, "commit", "--quiet", "-m", "Synthetic governance fixture")
    return git_command(root, "rev-parse", "HEAD").stdout.decode().strip()


class FixtureDecisions:
    """Author test-only evidence, never production decisions or Intent."""

    def __init__(self, root):
        self.root = root
        self.counter = 0

    def approve(self, record):
        self.counter += 1
        reference = f"docs/human/review-{self.counter}.json"
        review = {
            "reviewer": REVIEWER,
            "reviewer_authority": "human_project_author",
            "decision_timestamp": RECORDED_AT,
            "outcome": "approved",
            "rationale": "Synthetic approval in a temporary test repository only.",
            "source_quote": "Fixture: approve exactly this scope.",
            "source_ref": reference,
            "scope_sha256": scope_digest({k: v for k, v in record.items() if k != "review"}),
        }
        record["review"] = review
        write_json(
            self.root,
            reference,
            {"schema_version": 1, "artifact_kind": "subject_human_review_record", "review": review},
        )

    def save(self, decisions):
        write_json(self.root, DECISION, decisions)
        return SubjectPublicationEvidence(self.root, commit(self.root), DECISION)


@pytest.fixture(params=[False, True], ids=["content_revision", "bootstrap_origins"])
def governed(source, request):
    root, topology = source
    bootstrap = request.param
    declaration = None
    if bootstrap:
        changes = [origin_change(get(root, REQ_PATH)), origin_change(get(root, AC_PATH))]
        declaration = get(root, "specs/workspace_identity.yaml")
        for path in (REQ_PATH, AC_PATH, "specs/workspace_identity.yaml"):
            (root / path).unlink()
    else:
        changes = [revision_change(root)]
    initial = seed_repository(root)
    repo = (root, topology, initial)
    payload = request_payload(repo, changes=changes, declaration=declaration)
    author = FixtureDecisions(root)
    effects = []
    subjects = []
    templates = []
    transitions = []
    source_proposal = "docs/proposal.md"
    (root / "docs").mkdir(exist_ok=True)
    (root / source_proposal).write_text("Synthetic proposal: preserve the fixture policy.\n")
    write_json(
        root,
        "docs/intent_source.json",
        {
            "artifact_kind": "human_intent_record",
            "actor_id": REVIEWER,
            "text": "Fixture human intent.",
        },
    )
    write_json(
        root,
        "docs/intent.json",
        {
            "artifact_kind": "intent_draft",
            "statement": "Fixture: preserve readiness and review boundaries.",
            "provenance": {
                "authority_class": "authored",
                "actor_id": REVIEWER,
                "source_ref": "docs/intent_source.json",
            },
        },
    )
    lineage = {
        "artifact_kind": "subject_intent_lineage",
        "intent_ref": "docs/intent.json",
        "source_proposal_ref": source_proposal,
        "source_proposal_sha256": hashlib.sha256((root / source_proposal).read_bytes()).hexdigest(),
    }
    author.approve(lineage)
    write_json(root, "docs/lineage.json", lineage)
    for change in changes:
        record = change["proposed_record"]
        revision = record["revisions"][-1]
        local_id = record["id"]
        selection = {"subject": record["subject"], "mode": "exact", "revision": revision["number"]}
        canonical_id = f"canonical-{local_id}"
        revision["provenance"] = DECISION + f"#/effects/{len(effects)}"
        effect = {
            "effect": change["operation"],
            "subject": selection,
            "canonical_transition_id": canonical_id,
        }
        author.approve(effect)
        effects.append(effect)
        if bootstrap:
            event = record["retained_disposition_transitions"][0]
            event["provenance"] = DECISION + f"#/effects/{len(effects)}"
            record["current_disposition"]["observation_provenance"] = event["provenance"]
            activation = {"effect": "activation", "subject": selection}
            author.approve(activation)
            effects.append(activation)
        candidate = f"docs/candidate-{local_id}.json"
        write_json(root, candidate, {"proposed_record": record})
        subject = {
            "local_subject_id": local_id,
            "canonical_revision_selection": selection,
            "candidate_file": candidate,
            "source_draft_ref": candidate + "#/proposed_record",
            "canonical_target_ref": change["path"] + "#/subject",
            "statement": revision["statement"],
            "source_proposal_ref": source_proposal,
            "candidate_sha256": hashlib.sha256((root / candidate).read_bytes()).hexdigest(),
        }
        subjects.append(subject)
        for edge, identifier, source_ref, target_ref in (
            (
                "proposal -> spec_draft",
                f"ingress-{local_id}",
                source_proposal,
                subject["source_draft_ref"],
            ),
            (
                "spec_draft -> canonical_artifact",
                canonical_id,
                subject["source_draft_ref"],
                subject["canonical_target_ref"],
            ),
        ):
            template = {
                "transition_record_id": identifier,
                "transition_identifier": identifier + ":v1",
                "promotion_edge": edge,
                "gate_type": "review",
                "source_ref": source_ref,
                "target_ref": target_ref,
                "state": "review_pending",
                "outcome": None,
            }
            if edge.startswith("proposal"):
                template["intent_lineage_ref"] = "docs/lineage.json"
            else:
                template["target_revision_selection"] = selection
            templates.append(template)
            actual = copy.deepcopy(template)
            actual.update(
                outcome="approved",
                reviewer_or_decider=REVIEWER,
                decision_timestamp=RECORDED_AT,
                rationale="Synthetic approval in a temporary test repository only.",
            )
            if edge.startswith("spec_draft"):
                actual["ingress_transition_id"] = f"ingress-{local_id}"
            author.approve(actual)
            transitions.append(actual)
    workspace = {"workspace_identity": topology.workspace_identity, "source_ref": SOURCE_REF}
    if bootstrap:
        declaration["provenance"] = DECISION + f"#/effects/{len(effects)}"
        allocation = {
            "effect": "workspace_allocation",
            "workspace_identity": topology.workspace_identity,
            "source_ref": SOURCE_REF,
            "expected_commit": initial,
            "identity_allocation_authorized": True,
            "source_ref_initialization_authorized": True,
            "declaration_sha256": hashlib.sha256(
                dump_canonical_yaml(declaration).encode()
            ).hexdigest(),
        }
        author.approve(allocation)
        effects.append(allocation)
        write_json(root, "docs/workspace_candidate.json", {"proposed_record": declaration})
        workspace["proposed_declaration"] = "docs/workspace_candidate.json#/proposed_record"
    topology_ref = DECISION + f"#/effects/{len(effects)}"
    topology_effect = {"effect": "topology", "selection": topology_payload(topology)}
    author.approve(topology_effect)
    effects.append(topology_effect)
    parsed = parse_write_request(payload)
    used = {d["proposed_record"]["revisions"][-1]["provenance"] for d in changes}
    if bootstrap:
        used.update(
            d["proposed_record"]["retained_disposition_transitions"][0]["provenance"]
            for d in changes
        )
        used.add(declaration["provenance"])
    inputs = {
        source_proposal,
        "docs/lineage.json",
        "docs/intent.json",
        "docs/intent_source.json",
        *(s["candidate_file"] for s in subjects),
    }
    if bootstrap:
        inputs.add("docs/workspace_candidate.json")
    packet = {
        "schema_version": 1,
        "artifact_kind": "subject_publication_review_packet",
        "gate_state": "review_pending",
        "canonical_mutations_allowed": False,
        "workspace": workspace,
        "subjects": subjects,
        "transition_records": templates,
        "inputs": {
            "review_tree_file_sha256": {
                path: hashlib.sha256((root / path).read_bytes()).hexdigest()
                for path in sorted(inputs)
            }
        },
    }
    packet["approval_scope_sha256"] = scope_digest(packet)
    write_json(root, PACKET, packet)
    reviewed_head = commit(root)
    binding = {
        "packet_path": PACKET,
        "packet_sha256": hashlib.sha256((root / PACKET).read_bytes()).hexdigest(),
        "approval_scope_sha256": packet["approval_scope_sha256"],
        "reviewed_head": reviewed_head,
    }
    packet_approval = {"packet_binding": binding}
    author.approve(packet_approval)
    publication = {"request_sha256": parsed.digest(), "transition_refs": sorted(used)}
    author.approve(publication)
    decisions = {
        "schema_version": 1,
        "artifact_kind": "subject_publication_decisions",
        "packet_binding": binding,
        "packet_approval": packet_approval,
        "transition_decisions": transitions,
        "effects": effects,
        "topology_decision_ref": topology_ref,
        "publication": publication,
    }
    evidence = author.save(decisions)
    authorization = SubjectWriteAuthorization(
        parsed.digest(),
        DECISION + "#/publication",
        REVIEWER,
        "human_project_author",
        RECORDED_AT,
        tuple(sorted(used)),
    )
    return root, parsed, authorization, evidence, decisions, author


def test_resolved_decisions_allow_atomic_publication(governed):
    root, request, authorization, evidence, _, _ = governed
    result = write_subject_source(root, request, authorization=authorization, governance=evidence)
    assert result["status"] == "published"
    assert (
        result["authorization_verification"]
        == "scope_bound_recorded_decisions_verified_not_attested"
    )
    assert result["reviewer_identity_attested"] is False
    assert selected_source_commit(root, SOURCE_REF) == result["candidate_commit"]


def test_authorization_alone_cannot_publish(governed):
    root, request, authorization, _, _, _ = governed
    with pytest.raises(PublicationGovernanceError, match="evidence required"):
        write_subject_source(root, request, authorization=authorization)
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit


@pytest.mark.parametrize("effect_name", ["activation", "workspace_allocation"])
def test_bootstrap_requires_explicit_activation_and_allocation(governed, effect_name):
    root, request, authorization, _, decisions, author = governed
    if request.workspace_declaration_yaml is None:
        pytest.skip("bootstrap-only decisions")
    effect = next(e for e in decisions["effects"] if e["effect"] == effect_name)
    if effect_name == "activation":
        effect["subject"] = copy.deepcopy(effect["subject"])
        effect["subject"]["subject"]["local_subject_id"] = "another-subject"
    else:
        effect["identity_allocation_authorized"] = False
    author.approve(effect)
    evidence = author.save(decisions)
    with pytest.raises(PublicationGovernanceError):
        write_subject_source(root, request, authorization=authorization, governance=evidence)
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit


def test_missing_governance_creates_no_candidate_objects(governed, monkeypatch):
    root, request, authorization, _, _, _ = governed

    def forbidden(*args):
        pytest.fail("candidate preparation occurred before governance verification")

    monkeypatch.setattr("subject_source_write.SubjectSourceCommit.candidate_commit", forbidden)
    with pytest.raises(PublicationGovernanceError):
        write_subject_source(root, request, authorization=authorization)


def test_late_publication_approval_cannot_change_reviewed_statement(governed):
    root, request, authorization, _, decisions, author = governed
    from spec_yaml import load_yaml_text

    change = request.changes[0]
    document = load_yaml_text(change.document_yaml)
    document["revisions"][-1]["statement"] = "Different normative intent."
    modified = replace(
        request,
        changes=(
            replace(change, document_yaml=dump_canonical_yaml(document)),
            *request.changes[1:],
        ),
    )
    decisions["publication"]["request_sha256"] = modified.digest()
    author.approve(decisions["publication"])
    evidence = author.save(decisions)
    with pytest.raises(PublicationGovernanceError, match="reviewed draft"):
        write_subject_source(
            root,
            modified,
            authorization=replace(authorization, request_sha256=modified.digest()),
            governance=evidence,
        )
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit


def test_publication_cli_with_complete_evidence(governed, capsys):
    root, request, authorization, evidence, _, _ = governed
    write_request_and_authorization(root, request, authorization)
    write_json(
        root,
        "governance.json",
        {
            "schema_version": 1,
            "artifact_kind": "subject_publication_evidence",
            "repository_root": str(root),
            "evidence_commit": evidence.evidence_commit,
            "decision_path": DECISION,
        },
    )
    assert (
        main(
            [
                "--repository-root",
                str(root),
                "--request",
                str(root / "request.json"),
                "--authorization",
                str(root / "authorization.json"),
                "--governance",
                str(root / "governance.json"),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "published"


@pytest.mark.parametrize(
    "mutation",
    [
        "schema",
        "packet_hash",
        "scope",
        "missing_transition",
        "rejected",
        "wrong_ingress",
        "wrong_revision",
        "no_lineage",
        "wrong_effect",
        "wrong_topology",
        "wrong_request",
        "source_mismatch",
        "agent",
    ],
)
def test_scope_and_decision_failures_never_advance_source(governed, mutation):
    root, request, authorization, _, decisions, author = governed
    if mutation == "schema":
        decisions["artifact_kind"] = "rfc0221_subject_storage_decision"
    elif mutation == "packet_hash":
        decisions["packet_binding"]["packet_sha256"] = "0" * 64
        author.approve(decisions["packet_approval"])
    elif mutation == "scope":
        decisions["packet_binding"]["approval_scope_sha256"] = "0" * 64
        author.approve(decisions["packet_approval"])
    elif mutation == "missing_transition":
        decisions["transition_decisions"].pop()
    elif mutation == "rejected":
        transition = decisions["transition_decisions"][0]
        transition["outcome"] = "rejected"
        author.approve(transition)
    elif mutation == "wrong_ingress":
        transition = decisions["transition_decisions"][1]
        transition["ingress_transition_id"] = "other-ingress"
        author.approve(transition)
    elif mutation == "wrong_revision":
        transition = decisions["transition_decisions"][1]
        transition["target_revision_selection"]["revision"] += 1
        author.approve(transition)
    elif mutation == "no_lineage":
        transition = decisions["transition_decisions"][0]
        transition["intent_lineage_ref"] = None
        author.approve(transition)
    elif mutation == "wrong_effect":
        decisions["effects"][0]["effect"] = "schema_approval"
        author.approve(decisions["effects"][0])
    elif mutation == "wrong_topology":
        effect = decisions["effects"][-1]
        effect["selection"]["dataset_identity"] = "other-dataset"
        author.approve(effect)
    elif mutation == "wrong_request":
        decisions["publication"]["request_sha256"] = "0" * 64
        author.approve(decisions["publication"])
    elif mutation == "source_mismatch":
        review = decisions["publication"]["review"]
        record = json.loads((root / review["source_ref"]).read_text())
        record["review"]["outcome"] = "rejected"
        write_json(root, review["source_ref"], record)
    else:
        decisions["publication"]["review"]["reviewer_authority"] = "agent"
    evidence = author.save(decisions)
    with pytest.raises(PublicationGovernanceError):
        write_subject_source(root, request, authorization=authorization, governance=evidence)
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit


def test_working_tree_edits_do_not_replace_selected_decisions(governed):
    root, request, authorization, evidence, _, _ = governed
    (root / DECISION).write_text("malformed and unapproved working-tree content")
    assert (
        verify_publication(evidence, request, authorization)["reviewer_identity_attested"] is False
    )


def write_request_and_authorization(root, request, authorization):
    # Build an external request from the immutable typed object without altering its documents.
    payload = {
        "schema_version": 1,
        "artifact_kind": "subject_source_write_request",
        "source_ref": request.source_ref,
        "expected_commit": request.expected_commit,
        "recorded_at": request.recorded_at,
        "topology_selection": topology_payload(request.topology),
        "expected_source_file_sha256": dict(request.expected_source_file_sha256),
        "changes": [],
    }
    from spec_yaml import load_yaml_text

    for change in request.changes:
        payload["changes"].append(
            {
                "operation": change.operation,
                "path": change.path,
                "expected_prior_sha256": change.expected_prior_sha256,
                "proposed_record": load_yaml_text(change.document_yaml),
            }
        )
    if request.workspace_declaration_yaml:
        payload["workspace_declaration"] = load_yaml_text(request.workspace_declaration_yaml)
    write_json(root, "request.json", payload)
    write_json(
        root,
        "authorization.json",
        {
            "schema_version": 1,
            "artifact_kind": "subject_source_write_authorization",
            **asdict(authorization),
        },
    )


def test_cli_blocks_publication_without_governance(governed, capsys):
    root, request, authorization, _, _, _ = governed
    write_request_and_authorization(root, request, authorization)
    code = main(
        [
            "--repository-root",
            str(root),
            "--request",
            str(root / "request.json"),
            "--authorization",
            str(root / "authorization.json"),
        ]
    )
    assert code == 4
    assert json.loads(capsys.readouterr().out)["status"] == "governance_blocked"
    assert selected_source_commit(root, SOURCE_REF) == request.expected_commit
