"""Evidence-provider scope, completeness and source-bound snapshot composition."""

# ruff: noqa: E402 -- CLI packages live under tools, outside installed src packages.

import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from test_publication_trace_links import commit, edit_node
from test_publication_trace_links import repository as repository

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from intent_decision_review.sources import revision
from traceability.evidence import (
    AgreementFacts,
    EvidenceRequest,
    EvidenceScope,
    ResolutionCompletenessFacts,
)
from traceability.fact_agreement_spec import FACT_AGREEMENT_SPEC
from traceability.providers import EvidenceRegistry
from traceability.publication import PROFILE, build_publication_links, collect_publication_links
from traceability.publication_provider import PublicationEvidenceProvider
from traceability.resolution_completeness_spec import RESOLUTION_COMPLETENESS_SPEC
from traceability.snapshot import TraceSnapshot


def request(root, pin="HEAD"):
    return EvidenceRequest(
        root, EvidenceScope("test/repository", revision(root, pin), ("SG-SPEC-0071",), PROFILE)
    )


def test_single_collection_serves_legacy_facade_and_provider(repository, monkeypatch):
    selected = request(repository)
    collection = collect_publication_links(repository, selected.scope.source_revision)
    assert collection.to_payload() == build_publication_links(
        repository, selected.scope.source_revision
    )
    assert len(collection.atom_declarations) == 2
    from traceability import publication_provider

    calls = []

    def once(*args):
        calls.append(args)
        return collection

    monkeypatch.setattr(publication_provider, "collect_publication_links", once)
    report = PublicationEvidenceProvider().collect(selected)
    assert len(calls) == 1
    assert set(report.nodes[0].atoms) == set(collection.atom_declarations)
    assert report.collection_digest == collection.to_payload()["content_sha256"]
    assert report.nodes[0].inventory_complete and report.nodes[0].resolution_complete


@pytest.mark.parametrize(
    ("statuses", "complete"),
    [
        ((), True),
        (("resolved",), True),
        (("unresolved", "ambiguous", "wrong_kind"), True),
        (("unsupported",), False),
        (("resolved", "unavailable"), False),
        (("future_unknown",), False),
    ],
)
def test_resolution_completeness_is_not_resolution_success(statuses, complete):
    assert (
        RESOLUTION_COMPLETENESS_SPEC.is_satisfied_by(
            ResolutionCompletenessFacts(frozenset(statuses))
        )
        is complete
    )


@pytest.mark.parametrize(("values", "agree"), [((), True), (("x", "x"), True), (("x", "y"), False)])
def test_fact_agreement(values, agree):
    assert FACT_AGREEMENT_SPEC.is_satisfied_by(AgreementFacts(frozenset(values))) is agree


def test_required_source_failure_remains_incomplete(repository):
    edit_node(repository, lambda n: n.update(atoms={"intents": None}))
    selected = request(repository, commit(repository))
    snapshot = EvidenceRegistry((PublicationEvidenceProvider(),)).collect(
        selected, ("publication.declarations",)
    )
    node = snapshot.reports[0].nodes[0]
    assert not node.inventory_complete and not node.resolution_complete
    assert node.atoms == () and node.links == ()
    assert node.diagnostics[0].code == "publication_source_unavailable"
    assert snapshot.to_payload()["execution"] == "not_collected"


def test_missing_target_keeps_complete_atom_inventory(repository):
    (repository / "tests/test_sample.py").unlink()
    report = PublicationEvidenceProvider().collect(request(repository, commit(repository)))
    node = report.nodes[0]
    assert node.inventory_complete and not node.resolution_complete
    assert len(node.atoms) == 2 and node.links
    assert any(s.status == "unavailable" for s in report.sources)


@pytest.mark.parametrize("value", [["specified"], {"unexpected": "gate"}])
def test_malformed_lifecycle_cannot_introduce_mutable_facts(repository, value):
    edit_node(repository, lambda n: n.update(status=value))
    report = PublicationEvidenceProvider().collect(request(repository, commit(repository)))
    assert not report.nodes[0].inventory_complete
    assert report.nodes[0].diagnostics[0].code == "publication_source_unavailable"
    with pytest.raises(ValueError, match="lifecycle"):
        replace(report.nodes[0], source_status=value)


def test_duplicate_atom_is_retained_as_incomplete_inventory(repository):
    edit_node(repository, lambda n: n["atoms"]["intents"].append(dict(n["atoms"]["intents"][0])))
    report = PublicationEvidenceProvider().collect(request(repository, commit(repository)))
    assert not report.nodes[0].inventory_complete
    assert len(report.nodes[0].atoms) == 3


@pytest.mark.parametrize("change", ["profile", "spec", "artifacts"])
def test_unsupported_request_is_configuration_error(repository, change):
    selected = request(repository)
    if change == "profile":
        selected = replace(selected, scope=replace(selected.scope, resolver_profile="unknown"))
    elif change == "spec":
        selected = replace(selected, scope=replace(selected.scope, spec_ids=("SG-SPEC-0001",)))
    else:
        selected = replace(selected, artifact_paths=("runs/possibly-stale.json",))
    with pytest.raises(ValueError):
        PublicationEvidenceProvider().collect(selected)


class FixedProvider:
    def __init__(self, report):
        self.report = report
        self.provider_id, self.version = report.identity.provider_id, report.identity.version

    def collect(self, request):
        return self.report


def test_provider_order_and_repeat_observations_do_not_multiply_subjects(repository):
    selected = request(repository)
    report = PublicationEvidenceProvider().collect(selected)
    other = replace(
        report,
        identity=replace(report.identity, provider_id="second"),
        nodes=tuple(
            replace(n, atoms=tuple(reversed(n.atoms)), links=tuple(reversed(n.links)))
            for n in report.nodes
        ),
    )
    first = EvidenceRegistry((FixedProvider(report), FixedProvider(other))).collect(
        selected, ("second", "publication.declarations")
    )
    second = EvidenceRegistry((FixedProvider(other), FixedProvider(report))).collect(
        selected, ("publication.declarations", "second")
    )
    assert first.to_payload() == second.to_payload()
    assert len(first.reports) == 2 and len(first.observed_subjects) == 2
    assert first.conflicts == ()


def test_conflicting_link_and_atom_reports_keep_both_origins(repository):
    selected = request(repository)
    report = PublicationEvidenceProvider().collect(selected)
    node = report.nodes[0]
    changed_atom = replace(node.atoms[0], source_sha256="f" * 64)
    changed_link = replace(node.links[0], status="unresolved", candidates=())
    other = replace(
        report,
        identity=replace(report.identity, provider_id="second"),
        nodes=(
            replace(
                node, atoms=(changed_atom, *node.atoms[1:]), links=(changed_link, *node.links[1:])
            ),
        ),
    )
    snapshot = TraceSnapshot(selected.scope, (report, other))
    assert {c.fact_kind for c in snapshot.conflicts} == {"atom", "link"}
    assert snapshot.reports[0].nodes[0].links != snapshot.reports[1].nodes[0].links
    assert len(snapshot.observed_subjects) == 2
    assert all(
        {p for _, providers in c.variants for p in providers}
        == {"publication.declarations", "second"}
        for c in snapshot.conflicts
    )


def test_unknown_and_duplicate_provider_selection(repository):
    selected = request(repository)
    provider = PublicationEvidenceProvider()
    with pytest.raises(ValueError, match="registry"):
        EvidenceRegistry((provider, provider))
    registry = EvidenceRegistry((provider,))
    for ids in ((), ("unknown",), (provider.provider_id, provider.provider_id)):
        with pytest.raises(ValueError):
            registry.collect(selected, ids)


@pytest.mark.parametrize("change", ["revision", "identity", "version", "missing_node"])
def test_stale_or_misidentified_provider_result_is_rejected(repository, change):
    selected = request(repository)
    report = PublicationEvidenceProvider().collect(selected)
    if change == "missing_node":
        with pytest.raises(ValueError, match="every selected node"):
            replace(report, nodes=())
        return
    provider = FixedProvider(report)
    if change == "revision":
        provider.report = replace(report, scope=replace(report.scope, source_revision="a" * 40))
    else:
        provider.report = replace(
            report,
            identity=replace(
                report.identity,
                **({"provider_id": "other"} if change == "identity" else {"version": "99"}),
            ),
        )
    with pytest.raises(ValueError):
        EvidenceRegistry((provider,)).collect(selected, (provider.provider_id,))


def test_nested_facts_and_serializations_are_independent(repository):
    selected = request(repository)
    report = PublicationEvidenceProvider().collect(selected)
    nodes, reports = list(report.nodes), [report]
    report = replace(report, nodes=nodes)
    snapshot = TraceSnapshot(selected.scope, reports)
    nodes.clear()
    reports.clear()
    assert snapshot.reports and report.nodes
    with pytest.raises(FrozenInstanceError):
        report.nodes[0].atoms[0].reference = "different"
    payload = snapshot.to_payload()
    payload["reports"][0]["nodes"][0]["atoms"].clear()
    assert snapshot.to_payload()["reports"][0]["nodes"][0]["atoms"]


def test_branch_names_are_not_immutable_scope_revisions(repository):
    with pytest.raises(ValueError, match="full pinned"):
        EvidenceScope("test/repository", "HEAD", ("SG-SPEC-0071",), PROFILE)


def test_old_revision_survives_working_tree_and_new_committed_changes(repository):
    selected = request(repository)
    before = PublicationEvidenceProvider().collect(selected)
    (repository / "tests/test_sample.py").write_text("def different(): pass\n")
    assert PublicationEvidenceProvider().collect(selected) == before
    after = PublicationEvidenceProvider().collect(request(repository, commit(repository)))
    assert after != before
    assert any(r.status == "unresolved" for r in after.nodes[0].links)


def test_independent_snapshot_cli(repository, tmp_path):
    command = [
        sys.executable,
        "-B",
        str(ROOT / "tools/publication_trace_snapshot.py"),
        "--repository-root",
        str(repository),
        "--repository-id",
        "test/repository",
        "--revision",
        "HEAD",
        "--spec-id",
        "SG-SPEC-0071",
    ]
    result = subprocess.run(
        command,
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": "", "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["observed_subject_count"] == 2
    assert report["execution"] == "not_collected" and not report["conflicts"]
    failed = subprocess.run(
        [*command, "--provider", "unknown"], cwd=tmp_path, capture_output=True, text=True
    )
    assert failed.returncode == 1 and failed.stdout == ""


def test_actual_publication_provider():
    report = PublicationEvidenceProvider().collect(request(ROOT))
    assert report.nodes[0].inventory_complete
    assert report.nodes[0].resolution_complete
    assert report.nodes[0].atoms and all(r.status == "resolved" for r in report.nodes[0].links)
    assert report.nodes[0].diagnostics == ()
