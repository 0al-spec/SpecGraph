"""Real temporary Git repositories prove source publication and conflict boundaries."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import subject_source_git as git_source  # noqa: E402
from spec_yaml import dump_canonical_yaml  # noqa: E402
from subject_canonical_source import DECLARATION, read_canonical_source  # noqa: E402
from subject_read_model import SubjectClass  # noqa: E402
from subject_read_model_io import SubjectDocumentError  # noqa: E402
from subject_source_git import (  # noqa: E402
    SOURCE_REF_PREFIX,
    SubjectSourceCommit,
    SubjectSourceConflict,
    git_command,
    selected_source_commit,
)
from subject_source_write import (  # noqa: E402
    SubjectWriteAuthorization,
    main,
    parse_write_authorization,
    parse_write_request,
    write_subject_source,
)
from test_subject_canonical_source import (  # noqa: E402
    AC_PATH,
    REQ_PATH,
    get,
    ref,
    topology_payload,
)
from test_subject_canonical_source import (  # noqa: E402
    source as source,
)

SOURCE_REF = SOURCE_REF_PREFIX + "fixture"
DECISION = "fixture:write-decision"
RECORDED_AT = "2026-10-02T18:06:00Z"


@pytest.fixture(autouse=True)
def storage_boundary_only(monkeypatch):
    """These tests isolate storage/CAS. Real mandatory governance is tested separately."""
    monkeypatch.setattr("subject_source_write.verify_publication", lambda *args: {})


def seed_repository(root: Path) -> str:
    git_command(root, "init", "--quiet")
    for key, value in (
        ("user.name", "Fixture"),
        ("user.email", "fixture@localhost"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", "/dev/null"),
    ):
        git_command(root, "config", key, value)
    (root / "unrelated.txt").write_text("Keep this source unchanged.\n")
    git_command(root, "add", ".")
    git_command(root, "commit", "--quiet", "-m", "Fixture source")
    commit = git_command(root, "rev-parse", "HEAD").stdout.decode().strip()
    git_command(root, "update-ref", SOURCE_REF, commit)
    return commit


@pytest.fixture()
def repository(source):
    root, topology = source
    return root, topology, seed_repository(root)


def request_payload(repository, *, changes=None, declaration=None) -> dict:
    root, topology, commit = repository
    digests = (
        read_canonical_source(root, topology).source_file_sha256
        if (root / DECLARATION).exists()
        else ()
    )
    payload = {
        "schema_version": 1,
        "artifact_kind": "subject_source_write_request",
        "source_ref": SOURCE_REF,
        "expected_commit": commit,
        "recorded_at": RECORDED_AT,
        "topology_selection": topology_payload(topology),
        "expected_source_file_sha256": dict(digests),
        "changes": changes if changes is not None else [revision_change(root)],
    }
    if declaration is not None:
        payload["workspace_declaration"] = declaration
    return payload


def revision_change(root: Path) -> dict:
    document = get(root, REQ_PATH)
    next_revision = copy.deepcopy(document["revisions"][-1])
    next_revision.update(
        number=3,
        predecessor=2,
        statement="Fixture revised normative statement",
        provenance=DECISION,
        revision_scope="Fixture change: revise the readiness statement.",
    )
    next_revision["node_fields"]["title"] = "Fixture revised Requirement"
    next_revision["node_fields"]["provenance"]["recorded_at"] = RECORDED_AT
    document["revisions"].append(next_revision)
    document.update(copy.deepcopy(next_revision["node_fields"]))
    document["current_revision"] = 3
    return {
        "operation": "content_revision",
        "path": REQ_PATH,
        "expected_prior_sha256": hashlib.sha256((root / REQ_PATH).read_bytes()).hexdigest(),
        "proposed_record": document,
    }


def origin_change(document: dict, *, local_id=None, path=None) -> dict:
    document = copy.deepcopy(document)
    original = document["revisions"][-1]
    if local_id is not None:
        document["id"] = document["subject"]["local_subject_id"] = local_id
    path = path or original["containment"]
    original.update(number=1, predecessor=None, provenance=DECISION, containment=path)
    original["revision_scope"] = "Fixture origin, authorized only in a temporary repository."
    for selection in original["acceptance_criteria_refs"]:
        selection["revision"] = 1
    event_ref = "fixture:origin-" + document["id"]
    document["revisions"] = [original]
    document["current_revision"] = 1
    document["retained_disposition_transitions"] = [
        {"event_ref": event_ref, "transition": "activation", "provenance": DECISION}
    ]
    document["current_disposition"] = {
        "state": "active",
        "basis_ref": event_ref,
        "observation_provenance": DECISION,
    }
    return {
        "operation": "origin",
        "path": path,
        "expected_prior_sha256": None,
        "proposed_record": document,
    }


def authorization(request, transitions=(DECISION,)) -> SubjectWriteAuthorization:
    return SubjectWriteAuthorization(
        request.digest(),
        "fixture:publication-approval",
        "fixture:project-author",
        "human_project_author",
        RECORDED_AT,
        transitions,
    )


def published_read(root: Path, commit: str, topology):
    with SubjectSourceCommit(root, commit).export() as selected:
        return read_canonical_source(selected, topology).index


def test_revision_is_one_atomic_commit_and_leaves_worktree_index_and_head_unchanged(
    repository,
) -> None:
    root, topology, original_commit = repository
    before = read_canonical_source(root, topology).index.lookup_current(ref()).record
    working_bytes = {p: p.read_bytes() for p in root.rglob("*.yaml")}
    index_bytes = (root / ".git/index").read_bytes()
    request = parse_write_request(request_payload(repository))
    result = write_subject_source(root, request, authorization=authorization(request))
    assert result["status"] == "published" and result["source_ref_updated"] is True
    assert result["authorization_verification"] == "operator_supplied_not_attested"
    assert result["canonical_readiness"] == "not_evaluated"
    commit = selected_source_commit(root, SOURCE_REF)
    assert commit == result["candidate_commit"] != original_commit
    assert git_command(root, "rev-parse", commit + "^").stdout.decode().strip() == original_commit
    after = published_read(root, commit, topology).lookup_current(ref()).record
    assert after.current_revision == 3 and after.revisions[:-1] == before.revisions
    assert after.disposition_history == before.disposition_history
    assert after.current_disposition == before.current_disposition
    assert (root / ".git/index").read_bytes() == index_bytes
    assert working_bytes == {p: p.read_bytes() for p in root.rglob("*.yaml")}
    assert git_command(root, "rev-parse", "HEAD").stdout.decode().strip() == original_commit
    assert (
        git_command(root, "show", commit + ":unrelated.txt").stdout
        == (root / "unrelated.txt").read_bytes()
    )


def test_bootstrap_publishes_declaration_requirement_and_criterion_together(
    source, tmp_path
) -> None:
    fixture_root, topology = source
    root = tmp_path / "empty-repository"
    root.mkdir()
    base = seed_repository(root)
    changes = [
        origin_change(get(fixture_root, AC_PATH)),
        origin_change(get(fixture_root, REQ_PATH)),
    ]
    declaration = get(fixture_root, DECLARATION)
    declaration["provenance"] = DECISION
    request = parse_write_request(
        request_payload((root, topology, base), changes=changes, declaration=declaration)
    )
    prepared = write_subject_source(root, request, preview=True)
    assert selected_source_commit(root, SOURCE_REF) == base
    assert prepared["status"] == "prepared" and prepared["source_ref_updated"] is False
    assert not (root / "specs").exists()
    result = write_subject_source(root, request, authorization=authorization(request))
    assert result["candidate_commit"] == prepared["candidate_commit"]
    assert len(result["source_file_sha256"]) == 3
    index = published_read(root, result["candidate_commit"], topology)
    requirement = index.lookup_exact(ref(), 1)
    assert requirement.status == "resolved"
    assert requirement.selected_revision.acceptance_criteria_refs[0].revision == 1
    assert index.lookup_exact(ref("ac.ready", SubjectClass.CRITERION), 1).status == "resolved"


@pytest.mark.parametrize(
    "precondition", ["commit", "source_digest", "record_digest", "missing_source_path"]
)
def test_stale_preconditions_fail_without_publication(repository, precondition) -> None:
    root, _, base = repository
    payload = request_payload(repository)
    if precondition == "commit":
        payload["expected_commit"] = "0" * 40
    elif precondition == "source_digest":
        payload["expected_source_file_sha256"][REQ_PATH] = "0" * 64
    elif precondition == "record_digest":
        payload["changes"][0]["expected_prior_sha256"] = "0" * 64
    else:
        payload["expected_source_file_sha256"].pop(AC_PATH)
    request = parse_write_request(payload)
    with pytest.raises(SubjectSourceConflict):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


@pytest.mark.parametrize(
    "mutation",
    [
        "statement",
        "scope",
        "provenance",
        "metadata",
        "membership",
        "removed_revision",
        "second_successor",
    ],
)
def test_retained_history_is_immutable_across_writes(repository, mutation) -> None:
    root, _, base = repository
    payload = request_payload(repository)
    document = payload["changes"][0]["proposed_record"]
    old = document["revisions"][0]
    if mutation == "statement":
        old["statement"] = "rewritten history"
    elif mutation == "scope":
        old["revision_scope"] = "rewritten scope"
    elif mutation == "provenance":
        old["provenance"] = "fixture:rewritten-attribution"
    elif mutation == "metadata":
        old["node_fields"]["provenance"]["actor_id"] = "fixture:other-actor"
    elif mutation == "membership":
        old["acceptance_criteria_refs"][0]["revision"] = 2
    elif mutation == "removed_revision":
        document["revisions"].pop(0)
    else:
        extra = copy.deepcopy(document["revisions"][-1])
        extra.update(number=4, predecessor=3)
        document["revisions"].append(extra)
        document["current_revision"] = 4
    request = parse_write_request(payload)
    with pytest.raises(SubjectDocumentError):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


def test_disposition_changes_cannot_be_smuggled_into_content_revision(repository) -> None:
    root, _, base = repository
    payload = request_payload(repository)
    document = payload["changes"][0]["proposed_record"]
    document["retained_disposition_transitions"].append(
        {"event_ref": "fixture:new-activation", "transition": "activation", "provenance": DECISION}
    )
    document["current_disposition"].update(state="active", basis_ref="fixture:new-activation")
    request = parse_write_request(payload)
    with pytest.raises(SubjectDocumentError, match="disposition changes"):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


def test_new_criterion_and_requirement_membership_revision_publish_together(repository) -> None:
    root, topology, _ = repository
    change = origin_change(
        get(root, AC_PATH), local_id="ac.new", path="specs/criteria/new/ac.new.yaml"
    )
    payload = request_payload(repository)
    membership = payload["changes"][0]["proposed_record"]["revisions"][-1][
        "acceptance_criteria_refs"
    ]
    membership[0]["subject"]["local_subject_id"] = "ac.new"
    membership[0]["revision"] = 1
    payload["changes"].append(change)
    request = parse_write_request(payload)
    result = write_subject_source(root, request, authorization=authorization(request))
    index = published_read(root, result["candidate_commit"], topology)
    assert (
        index.lookup_current(ref())
        .selected_revision.acceptance_criteria_refs[0]
        .subject.local_subject_id
        == "ac.new"
    )
    assert index.lookup_exact(ref("ac.new", SubjectClass.CRITERION), 1).status == "resolved"


def test_portable_namespace_collision_across_classes_is_rejected(repository) -> None:
    root, _, base = repository
    change = origin_change(
        get(root, AC_PATH), local_id="REQ.READINESS", path="specs/criteria/group/REQ.READINESS.yaml"
    )
    request = parse_write_request(request_payload(repository, changes=[change]))
    with pytest.raises(SubjectDocumentError, match="portable namespace"):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


def test_missing_exact_pin_rejects_the_entire_candidate(repository) -> None:
    root, _, base = repository
    payload = request_payload(repository)
    payload["changes"][0]["proposed_record"]["revisions"][-1]["acceptance_criteria_refs"][0][
        "revision"
    ] = 99
    request = parse_write_request(payload)
    with pytest.raises(SubjectDocumentError):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


def test_competing_successors_do_not_overwrite_a_published_revision(repository) -> None:
    root, topology, _ = repository
    first = parse_write_request(request_payload(repository))
    second_payload = request_payload(repository)
    second_payload["changes"][0]["proposed_record"]["revisions"][-1]["statement"] = (
        "Competing statement"
    )
    second = parse_write_request(second_payload)
    published = write_subject_source(root, first, authorization=authorization(first))
    with pytest.raises(SubjectSourceConflict):
        write_subject_source(root, second, authorization=authorization(second))
    assert selected_source_commit(root, SOURCE_REF) == published["candidate_commit"]
    record = (
        published_read(root, published["candidate_commit"], topology).lookup_current(ref()).record
    )
    assert record.revisions[-1].statement != "Competing statement"


def test_late_compare_and_swap_conflict_preserves_the_winner(repository, monkeypatch) -> None:
    root, topology, base = repository
    request = parse_write_request(request_payload(repository))
    winning_payload = request_payload(repository)
    winning_payload["changes"][0]["proposed_record"]["revisions"][-1]["statement"] = (
        "Winning statement"
    )
    winning = parse_write_request(winning_payload)
    winning_commit = write_subject_source(root, winning, preview=True)["candidate_commit"]
    original = git_source.git_command
    raced = False

    def concurrent_publication(repository, *arguments, **kwargs):
        nonlocal raced
        if arguments[0] == "update-ref" and not raced:
            raced = True
            original(root, "update-ref", SOURCE_REF, winning_commit, base)
        return original(repository, *arguments, **kwargs)

    monkeypatch.setattr(git_source, "git_command", concurrent_publication)
    with pytest.raises(SubjectSourceConflict, match="atomic publication"):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == winning_commit
    assert (
        published_read(root, winning_commit, topology)
        .lookup_current(ref())
        .record.revisions[-1]
        .statement
        == "Winning statement"
    )


@pytest.mark.parametrize("phase", ["initial", "before_publish", "at_cas"])
def test_deleted_ref_is_a_cli_source_conflict(repository, tmp_path, capsys, monkeypatch, phase):
    root, _, base = repository
    payload = request_payload(repository)
    request_path = tmp_path / "request.yaml"
    request_path.write_text(dump_canonical_yaml(payload))
    request = parse_write_request(payload)
    auth_path = tmp_path / "authorization.yaml"
    from dataclasses import asdict

    auth_path.write_text(
        dump_canonical_yaml(
            {
                "schema_version": 1,
                "artifact_kind": "subject_source_write_authorization",
                **asdict(authorization(request)),
            }
        )
    )
    original = git_source.git_command
    if phase == "initial":
        original(root, "update-ref", "-d", SOURCE_REF, base)
    elif phase == "before_publish":
        publish = SubjectSourceCommit.publish

        def deleted_before_publish(self, source_ref, candidate_commit):
            original(root, "update-ref", "-d", SOURCE_REF, base)
            return publish(self, source_ref, candidate_commit)

        monkeypatch.setattr(SubjectSourceCommit, "publish", deleted_before_publish)
    else:

        def deleted_at_cas(repository, *arguments, **kwargs):
            if arguments[0] == "update-ref":
                original(root, "update-ref", "-d", SOURCE_REF, base)
            return original(repository, *arguments, **kwargs)

        monkeypatch.setattr(git_source, "git_command", deleted_at_cas)
    assert (
        main(
            [
                "--repository-root",
                str(root),
                "--request",
                str(request_path),
                "--authorization",
                str(auth_path),
            ]
        )
        == 3
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "source_conflict"
    assert result["source_ref_updated"] is False
    assert (
        original(root, "show-ref", "--verify", "--quiet", SOURCE_REF, check=False).returncode == 1
    )


@pytest.mark.parametrize("commit", ["abc", "A" * 40, "not-a-commit", None, 123])
def test_malformed_expected_commit_is_invalid_input(repository, tmp_path, capsys, commit):
    root, _, base = repository
    payload = request_payload(repository)
    payload["expected_commit"] = commit
    with pytest.raises(SubjectDocumentError, match="complete lowercase Git commit ID"):
        parse_write_request(payload)
    request_path = tmp_path / "request.yaml"
    request_path.write_text(dump_canonical_yaml(payload))
    assert main(["--repository-root", str(root), "--request", str(request_path), "--preview"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "invalid_input"
    assert result["source_ref_updated"] is False
    assert selected_source_commit(root, SOURCE_REF) == base


def test_failure_preparing_git_objects_never_publishes_partial_records(
    repository, monkeypatch
) -> None:
    root, _, base = repository
    request = parse_write_request(request_payload(repository))

    def interrupted_preparation(*_args, **_kwargs):
        raise OSError("fixture interrupted write")

    monkeypatch.setattr(SubjectSourceCommit, "candidate_commit", interrupted_preparation)
    with pytest.raises(OSError, match="interrupted write"):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


@pytest.mark.parametrize("failure", ["missing", "digest", "transitions"])
def test_authorization_is_explicit_and_bound_to_exact_content_and_decisions(
    repository, failure
) -> None:
    root, _, base = repository
    request = parse_write_request(request_payload(repository))
    approval = authorization(request)
    if failure == "missing":
        approval = None
    elif failure == "digest":
        approval = replace(approval, request_sha256="0" * 64)
    else:
        approval = replace(approval, transition_refs=("fixture:wrong-decision",))
    with pytest.raises(SubjectDocumentError):
        write_subject_source(root, request, authorization=approval)
    assert selected_source_commit(root, SOURCE_REF) == base


@pytest.mark.parametrize(
    "operation",
    ["containment_move", "withdrawal", "replacement", "migration", "topology", "decomposes_into"],
)
def test_unsupported_operations_are_rejected(repository, operation) -> None:
    payload = request_payload(repository)
    payload["changes"][0]["operation"] = operation
    with pytest.raises(SubjectDocumentError, match="unsupported operation"):
        parse_write_request(payload)


@pytest.mark.parametrize("source_ref", ["HEAD", "refs/heads/main", "refs/tags/release"])
def test_publication_cannot_target_normal_branches_or_tags(repository, source_ref) -> None:
    root, _, _ = repository
    request = replace(parse_write_request(request_payload(repository)), source_ref=source_ref)
    with pytest.raises(SubjectDocumentError, match="explicit refs/specgraph"):
        write_subject_source(root, request, authorization=authorization(request))


def test_symbolic_source_ref_cannot_redirect_publication(repository) -> None:
    root, _, base = repository
    git_command(root, "update-ref", "-d", SOURCE_REF)
    git_command(root, "symbolic-ref", SOURCE_REF, "refs/heads/master")
    request = parse_write_request(request_payload(repository))
    with pytest.raises(SubjectDocumentError, match="symbolic ref"):
        write_subject_source(root, request, authorization=authorization(request))
    assert git_command(root, "rev-parse", "HEAD").stdout.decode().strip() == base


def test_inherited_git_overrides_cannot_change_the_selected_repository(
    repository, monkeypatch, tmp_path
) -> None:
    root, _, base = repository
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "wrong-repository"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "operator-index"))
    assert selected_source_commit(root, SOURCE_REF) == base
    request = parse_write_request(request_payload(repository))
    assert write_subject_source(root, request, preview=True)["status"] == "prepared"
    assert not (tmp_path / "operator-index").exists()


def test_cli_preview_publication_conflict_and_invalid_authorization(
    repository, tmp_path, capsys
) -> None:
    root, _, base = repository
    payload = request_payload(repository)
    request_path = tmp_path / "request.yaml"
    request_path.write_text(dump_canonical_yaml(payload))
    args = ["--repository-root", str(root), "--request", str(request_path)]
    assert main(args + ["--preview"]) == 0
    prepared = json.loads(capsys.readouterr().out)
    approval = {
        "schema_version": 1,
        "artifact_kind": "subject_source_write_authorization",
        "request_sha256": prepared["request_sha256"],
        "decision_ref": "fixture:publication-approval",
        "reviewer": "fixture:project-author",
        "reviewer_authority": "human_project_author",
        "recorded_at": RECORDED_AT,
        "transition_refs": [DECISION],
    }
    assert parse_write_authorization(approval) == authorization(parse_write_request(payload))
    authorization_path = tmp_path / "authorization.yaml"
    authorization_path.write_text(dump_canonical_yaml(approval))
    assert main(args + ["--authorization", str(authorization_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["candidate_commit"] == prepared["candidate_commit"] != base
    assert main(args + ["--authorization", str(authorization_path)]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "source_conflict"
    approval["reviewer_authority"] = "agent"
    authorization_path.write_text(dump_canonical_yaml(approval))
    assert main(args + ["--authorization", str(authorization_path)]) == 2
    assert json.loads(capsys.readouterr().out)["source_ref_updated"] is False


def test_existing_origin_cannot_reallocate_an_existing_requirement(repository) -> None:
    root, _, base = repository
    change = origin_change(get(root, REQ_PATH))
    request = parse_write_request(request_payload(repository, changes=[change]))
    with pytest.raises(SubjectSourceConflict, match="no existing subject"):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


@pytest.mark.parametrize("status", ["frozen", "idea"])
def test_frozen_history_and_lifecycle_regression_are_rejected(repository, status) -> None:
    root, topology, base = repository
    if status == "frozen":
        document = get(root, REQ_PATH)
        document["status"] = document["revisions"][-1]["node_fields"]["status"] = "frozen"
        (root / REQ_PATH).write_text(dump_canonical_yaml(document))
        git_command(root, "add", REQ_PATH)
        git_command(root, "commit", "--quiet", "-m", "Fixture frozen source")
        base = git_command(root, "rev-parse", "HEAD").stdout.decode().strip()
        git_command(root, "update-ref", SOURCE_REF, base)
    payload = request_payload((root, topology, base))
    if status == "idea":
        document = payload["changes"][0]["proposed_record"]
        document["status"] = document["revisions"][-1]["node_fields"]["status"] = "idea"
    request = parse_write_request(payload)
    with pytest.raises(SubjectDocumentError, match="frozen or regressed"):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


@pytest.mark.parametrize("violation", ["unrelated_path", "parent"])
def test_actual_git_commit_scope_is_checked_before_publication(repository, monkeypatch, violation):
    root, _, base = repository
    request = parse_write_request(request_payload(repository))
    original = SubjectSourceCommit.candidate_commit

    def corrupted_commit(source, files, recorded_at, digest):
        if violation == "unrelated_path":
            return original(
                source, {**files, "unrelated.txt": b"unrequested change"}, recorded_at, digest
            )
        commit = original(source, files, recorded_at, digest)
        tree = git_command(root, "rev-parse", commit + "^{tree}").stdout.decode().strip()
        return (
            git_command(root, "commit-tree", tree, content=b"Wrong parent\n")
            .stdout.decode()
            .strip()
        )

    monkeypatch.setattr(SubjectSourceCommit, "candidate_commit", corrupted_commit)
    with pytest.raises(SubjectDocumentError, match="unrequested paths or an unexpected parent"):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


def test_cleanup_failure_occurs_before_publication(repository, monkeypatch) -> None:
    root, _, base = repository
    request = parse_write_request(request_payload(repository))
    original = SubjectSourceCommit.export

    @contextmanager
    def failing_cleanup(source):
        with original(source) as exported:
            yield exported
        if source.commit_id == base:
            raise OSError("fixture failed candidate cleanup")

    monkeypatch.setattr(SubjectSourceCommit, "export", failing_cleanup)
    with pytest.raises(OSError, match="failed candidate cleanup"):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == base


@pytest.mark.parametrize(
    "violation", ["unknown_field", "boolean_version", "duplicate_change", "path_escape"]
)
def test_request_schema_and_paths_fail_closed(repository, violation) -> None:
    payload = request_payload(repository)
    if violation == "unknown_field":
        payload["topology_mutation"] = True
    elif violation == "boolean_version":
        payload["schema_version"] = True
    elif violation == "duplicate_change":
        payload["changes"].append(copy.deepcopy(payload["changes"][0]))
    else:
        payload["changes"][0]["path"] = "specs/requirements/../../outside.yaml"
    with pytest.raises(SubjectDocumentError):
        parse_write_request(payload)


def test_committed_symlink_is_rejected_without_following_its_target(repository, tmp_path) -> None:
    root, _, _ = repository
    payload = request_payload(repository)
    outside = tmp_path / "outside.yaml"
    outside.write_bytes((root / REQ_PATH).read_bytes())
    (root / REQ_PATH).unlink()
    (root / REQ_PATH).symlink_to(outside)
    git_command(root, "add", REQ_PATH)
    git_command(root, "commit", "--quiet", "-m", "Fixture invalid symlink")
    commit = git_command(root, "rev-parse", "HEAD").stdout.decode().strip()
    git_command(root, "update-ref", SOURCE_REF, commit)
    payload["expected_commit"] = commit
    request = parse_write_request(payload)
    before = outside.read_bytes()
    with pytest.raises(SubjectDocumentError, match="no symlinks"):
        write_subject_source(root, request, authorization=authorization(request))
    assert selected_source_commit(root, SOURCE_REF) == commit
    assert outside.read_bytes() == before
