"""Retained producer artifacts are observations, not execution or admission."""

# ruff: noqa: E402 -- executable tools must also import in isolation.

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import publication_delivery_evidence as producer
from publication_evidence.context import ExecutionIdentity
from static_artifact_incremental_stage import verify_remote_bundle
from test_publication_trace_links import commit, git
from test_publication_trace_links import repository as repository
from traceability.evidence import EvidenceRequest, EvidenceScope
from traceability.execution import ExecutionBindingFacts, PublicationExecutionSelection
from traceability.execution_binding_spec import EXECUTION_BINDING_SPEC
from traceability.providers import EvidenceRegistry
from traceability.publication import PROFILE
from traceability.publication_execution_provider import (
    PublicationExecutionEvidenceProvider,
    pinned_source,
)
from traceability.publication_provider import PublicationEvidenceProvider


@pytest.fixture
def retained(repository, tmp_path_factory, monkeypatch):
    """Use the real report producers with synthetic JUnit and an offline HTTP fetcher."""
    root = repository
    shutil.copytree(ROOT / "tools/publication_evidence", root / "tools/publication_evidence")
    for name in ("artifact_json.py", "publication_delivery_evidence.py"):
        shutil.copy(ROOT / "tools" / name, root / "tools" / name)
    bindings_path = root / producer.DEFAULT_BINDINGS
    bindings = json.loads(bindings_path.read_text())
    bindings.update(runtime_base_url="https://publication.invalid", runtime_environment="fixture")
    producer.write_json(bindings_path, bindings)
    passport_path = root / bindings["passport"]
    passport = json.loads(passport_path.read_text())
    passport["metadata"] = dict(feature_id="fixture", passport_id="fixture", version="1.0.0")
    passport["spec"]["intent"]["summary"] = "Fixture publication"
    producer.write_json(passport_path, passport)
    rev = commit(root)
    for name, value in dict(
        GITHUB_RUN_ID="123",
        GITHUB_RUN_ATTEMPT="2",
        GITHUB_REPOSITORY="0al-spec/SpecGraph",
        GITHUB_SHA=rev,
        GITHUB_SERVER_URL="https://github.com",
    ).items():
        monkeypatch.setenv(name, value)
    output = tmp_path_factory.mktemp("retained-publication")
    junit = output / "tests.xml"
    junit.write_text(
        '<testsuite><testcase classname="tests.test_sample" name="test_all" /></testsuite>'
    )
    result, obligations = producer.junit_obligations(junit, bindings["obligations"], 0)
    tests = dict(
        artifact_kind="specgraph_publication_test_observation",
        schema_version=1,
        source=producer.source_identity(root, bindings),
        provenance=producer.provenance(),
        exit_code=0,
        result=result,
        obligations=obligations,
        junit_sha256=hashlib.sha256(junit.read_bytes()).hexdigest(),
    )
    tests_path = output / "tests.json"
    producer.write_json(tests_path, tests)
    bundle = output / "bundle"
    bundle.mkdir()
    (bundle / "payload.json").write_text("{}")
    producer.write_json(
        bundle / "artifact_manifest.json",
        {
            "files": [
                {"path": "payload.json", "sha256": producer.file_digest(bundle / "payload.json")}
            ]
        },
    )
    (bundle / "checksums.sha256").write_text("fixture checksums")
    native = verify_remote_bundle(
        bundle_dir=bundle,
        remote_base_url=bindings["runtime_base_url"],
        fetcher=lambda url: (bundle / url.rsplit("/", 1)[1]).read_bytes(),
        workers=1,
    )
    runtime_path = output / "runtime.json"
    producer.write_json(runtime_path, native)
    delivery_path = output / "report.json"
    producer.write_json(
        delivery_path, producer.delivery_report(root, tests_path, bundle, runtime_path, "fixture")
    )
    selection = PublicationExecutionSelection(
        ExecutionIdentity(**producer.provenance()), tests_path, delivery_path
    )
    return EvidenceRequest(
        root,
        EvidenceScope("0al-spec/SpecGraph", rev, ("SG-SPEC-0071",), PROFILE),
        execution_selection=selection,
    )


def collect(request):
    return PublicationExecutionEvidenceProvider().collect(request)


def artifact(report, role):
    return next(a for a in report.execution.artifacts if a.role == role)


def change(request, role, transform):
    path = getattr(request.execution_selection, f"{role}_report")
    value = json.loads(path.read_text())
    transform(value)
    producer.write_json(path, value)
    return value


def test_pinned_source_matches_real_producer_without_executing_source(retained):
    expected, obligations, _ = pinned_source(retained)
    tests = json.loads(retained.execution_selection.tests_report.read_text())
    assert expected == producer.source_facts(tests["source"])
    assert obligations == producer.obligation_facts(tests["obligations"])
    # A missing working copy cannot change Git-pinned evidence collection.
    (retained.repository_root / "tools/implementation.py").unlink()
    report = collect(retained)
    assert all(a.binding_status == "matched" for a in report.execution.artifacts)
    assert not report.nodes[0].diagnostics
    assert artifact(report, "tests").signals[0].evaluated_result == "observed_success"
    assert {s.stage for s in artifact(report, "delivery").signals} == {"tests", "deploy", "runtime"}
    assert all(s.binding_status == "matched" for s in artifact(report, "delivery").signals)
    assert not report.nodes[0].inventory_complete  # This provider does not enumerate atoms.


def test_composition_preserves_declarations_and_uses_separate_profile(retained):
    registry = EvidenceRegistry(
        (PublicationEvidenceProvider(), PublicationExecutionEvidenceProvider())
    )
    baseline = registry.collect(
        replace(retained, execution_selection=None), ("publication.declarations",)
    ).to_payload()
    assert baseline["execution"] == "not_collected"
    assert baseline["profile"] == "specgraph.trace-snapshot/declarations-v1"
    both = registry.collect(
        retained, ("publication.execution", "publication.declarations")
    ).to_payload()
    assert both["profile"] == "specgraph.trace-snapshot/execution-v1"
    assert both["observed_subjects"] == baseline["observed_subjects"]
    assert both["reports"][0] == baseline["reports"][0]
    assert both["readiness"] == both["admission"] == "not_evaluated"
    assert both["canonical_mutations_allowed"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider", "local"),
        ("run_id", ""),
        ("run_id", "0"),
        ("run_attempt", "0"),
        ("run_attempt", ""),
        ("uri", "local-run"),
    ],
)
def test_ambiguous_selected_run_is_configuration_error(retained, field, value):
    identity = replace(retained.execution_selection.identity, **{field: value})
    assert not EXECUTION_BINDING_SPEC.is_satisfied_by(
        ExecutionBindingFacts(retained.scope.repository_id, identity, identity)
    )
    with pytest.raises(ValueError, match="complete GitHub"):
        collect(
            replace(
                retained,
                execution_selection=replace(retained.execution_selection, identity=identity),
            )
        )


@pytest.mark.parametrize(
    "field,value",
    [("revision", "f" * 40), ("repository", "other/repository"), ("files_sha256", {})],
)
def test_wrong_source_is_retained_but_not_bound(retained, field, value):
    original = change(retained, "tests", lambda r: r["source"].update({field: value}))
    observed = artifact(collect(retained), "tests")
    assert observed.binding_status == "mismatch"
    assert observed.to_payload()["producer_report"] == original
    assert observed.signals[0].producer_result == "observed_success"
    assert observed.signals[0].evaluated_result is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider", "local"),
        ("run_id", "124"),
        ("run_attempt", "1"),
        ("uri", "https://other.invalid/123"),
    ],
)
def test_wrong_report_run_is_not_bound(retained, field, value):
    change(retained, "tests", lambda r: r["provenance"].update({field: value}))
    assert artifact(collect(retained), "tests").binding_status == "mismatch"


@pytest.mark.parametrize("mode", ["subset", "duplicate", "selector", "criterion"])
def test_test_obligations_cannot_borrow_other_observations(retained, mode):
    def alter(report):
        rows = report["obligations"]
        if mode == "subset":
            rows.clear()
        elif mode == "duplicate":
            rows.extend(copy.deepcopy(rows))
        else:
            rows[0]["test" if mode == "selector" else "criterion_id"] = "unrelated"

    change(retained, "tests", alter)
    signal = artifact(collect(retained), "tests").signals[0]
    assert signal.binding_status == "mismatch"
    assert signal.evaluated_result is None


@pytest.mark.parametrize(
    "outcome,exit_code,expected",
    [
        ("observed_failure", 1, "observed_failure"),
        ("skipped", 0, "missing"),
        ("observed_success", 0, "observed_success"),
    ],
)
def test_existing_suite_policy_preserves_failures_and_missing(
    retained, outcome, exit_code, expected
):
    def alter(report):
        report["obligations"][0]["result"] = outcome
        report["exit_code"] = exit_code

    original = change(retained, "tests", alter)
    observed = artifact(collect(retained), "tests")
    assert observed.binding_status == "matched"  # Complete observation can describe failure.
    assert observed.signals[0].evaluated_result == expected
    assert observed.to_payload()["producer_report"] == original


@pytest.mark.parametrize(
    "field,value",
    [("source_revision", "f" * 40), ("run_attempt", "1"), ("run_id", "124"), ("provider", "local")],
)
def test_delivery_cannot_borrow_nested_runtime_identity(retained, field, value):
    change(
        retained,
        "delivery",
        lambda r: r["stages"]["runtime"]["observation"]["execution_context"].update({field: value}),
    )
    observed = artifact(collect(retained), "delivery")
    assert observed.binding_status == "matched"  # Header is bound; nested observation is not.
    for signal in observed.signals:
        assert signal.binding_status == ("matched" if signal.stage == "tests" else "mismatch")
        assert signal.producer_result == "observed_success"


@pytest.mark.parametrize("mode", ["origin", "bundle", "observer", "tests"])
def test_delivery_checks_nested_signal_bindings(retained, mode):
    def alter(report):
        runtime = report["stages"]["runtime"]
        if mode == "origin":
            runtime["observation"]["remote_base_url"] = "https://other.invalid"
        elif mode == "bundle":
            runtime["observation"]["bundle_identity"]["checksums_sha256"] = "f" * 64
        elif mode == "observer":
            runtime["provenance"]["observer"]["run_attempt"] = "1"
        else:
            report["stages"]["tests"]["obligations"].clear()

    change(retained, "delivery", alter)
    report = collect(retained)
    assert any(d.code == "execution_signal_mismatch" for d in report.nodes[0].diagnostics)


def test_stale_delivery_header_does_not_leave_matched_signals(retained):
    change(retained, "delivery", lambda r: r["source"].update(revision="f" * 40))
    observed = artifact(collect(retained), "delivery")
    assert observed.binding_status == "mismatch"
    assert all(s.binding_status == "mismatch" for s in observed.signals)


def test_missing_stage_remains_missing_not_success(retained):
    def alter(report):
        for name in ("deploy", "runtime"):
            report["stages"][name]["result"] = "missing"
            report["stages"][name]["provenance"]["observer"] = None

    change(retained, "delivery", alter)
    signals = artifact(collect(retained), "delivery").signals
    assert [(s.producer_result, s.binding_status) for s in signals[1:]] == [
        ("missing", "not_asserted")
    ] * 2


@pytest.mark.parametrize("role", ["tests", "delivery"])
@pytest.mark.parametrize(
    "field,value", [("artifact_kind", "other"), ("schema_version", True), ("schema_version", 2)]
)
def test_unknown_report_contract_remains_unavailable_with_original_report(
    retained, role, field, value
):
    original = change(retained, role, lambda r: r.update({field: value}))
    report = collect(retained)
    observed = artifact(report, role)
    assert observed.binding_status == "unavailable"
    assert observed.to_payload()["producer_report"] == original
    assert any(d.code == "execution_artifact_unavailable" for d in report.nodes[0].diagnostics)


@pytest.mark.parametrize(
    "raw",
    [None, b"{", b'{"x":1,"x":2}', b'{"x":NaN}', b"[]", b" " * (2 * 1024 * 1024 + 1)],
    ids=["absent", "invalid-json", "duplicate-key", "nonfinite", "not-object", "oversized"],
)
def test_missing_and_malformed_selected_artifacts_are_explicit(retained, raw):
    path = retained.execution_selection.tests_report
    if raw is None:
        path.unlink()
    else:
        path.write_bytes(raw)
    report = collect(retained)
    assert artifact(report, "tests").binding_status == "unavailable"
    assert not report.nodes[0].inventory_complete
    assert artifact(report, "delivery").binding_status == "matched"


def test_unavailable_pinned_source_does_not_hide_retained_outcome(retained):
    root = retained.repository_root
    git(root, "rm", "tools/artifact_json.py")
    rev = commit(root)
    request = replace(retained, scope=replace(retained.scope, source_revision=rev))
    report = collect(request)
    assert any(d.code == "execution_source_unavailable" for d in report.nodes[0].diagnostics)
    assert artifact(report, "tests").binding_status == "unavailable"
    assert artifact(report, "tests").to_payload()["producer_report"]["result"] == "observed_success"


def test_snapshot_immutable_and_independent_of_artifact_storage_location(retained, tmp_path):
    report = collect(retained)
    with pytest.raises(FrozenInstanceError):
        report.execution.artifacts = ()
    payload = report.to_payload()
    payload["execution"]["artifacts"][0]["producer_report"].clear()
    assert report.to_payload()["execution"]["artifacts"][0]["producer_report"]
    selections = {}
    for role in ("tests", "delivery"):
        path = getattr(retained.execution_selection, f"{role}_report")
        target = tmp_path / f"moved-{role}.json"
        target.write_bytes(path.read_bytes())
        selections[f"{role}_report"] = target
    moved = replace(
        retained, execution_selection=replace(retained.execution_selection, **selections)
    )
    assert collect(moved).to_payload() == report.to_payload()
    assert report.execution.to_payload()["selected_run"] == asdict(
        retained.execution_selection.identity
    )


def test_provider_requires_explicit_selection(retained):
    with pytest.raises(ValueError, match="selection"):
        collect(replace(retained, execution_selection=None))
    with pytest.raises(ValueError, match="absolute"):
        PublicationExecutionSelection(retained.execution_selection.identity, Path("tests.json"))


@pytest.mark.parametrize("exit_code", [None, True, "0"])
def test_invalid_pytest_exit_code_is_not_an_execution_outcome(retained, exit_code):
    original = change(retained, "tests", lambda r: r.update(exit_code=exit_code))
    observed = artifact(collect(retained), "tests")
    assert observed.binding_status == "unavailable"
    assert observed.to_payload()["producer_report"] == original
    assert not observed.signals


def test_curated_ci_input_hashes_and_original_missing_stages_are_preserved():
    evidence = json.loads(
        (ROOT / "docs/evidence/0226_publication_execution_snapshot.json").read_text()
    )
    selected = {}
    for item in evidence["selected_artifacts"]:
        path = ROOT / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        selected[path.name] = json.loads(path.read_text())
    assert selected["tests.json"]["source"]["revision"] == evidence["source_revision"]
    assert selected["tests.json"]["source"]["revision"] != evidence["branch_head"]
    assert len(selected["tests.json"]["obligations"]) == 5
    for name in ("deploy", "runtime"):
        assert selected["report.json"]["stages"][name]["result"] == "missing"


def test_execution_cli_composes_providers_in_isolation(retained, tmp_path):
    command = [
        sys.executable,
        "-B",
        str(ROOT / "tools/publication_trace_snapshot.py"),
        "--repository-root",
        str(retained.repository_root),
        "--repository-id",
        retained.scope.repository_id,
        "--revision",
        retained.scope.source_revision,
        "--spec-id",
        "SG-SPEC-0071",
        "--provider",
        "publication.declarations",
        "--provider",
        "publication.execution",
        "--tests-report",
        str(retained.execution_selection.tests_report),
        "--delivery-report",
        str(retained.execution_selection.delivery_report),
        "--run-id",
        "123",
        "--run-attempt",
        "2",
    ]
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    completed = subprocess.run(command, cwd=tmp_path, env=env, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    assert not completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["profile"] == "specgraph.trace-snapshot/execution-v1"
    assert len(payload["reports"]) == 2
    without_selection = subprocess.run(
        command[:-4], cwd=tmp_path, env=env, text=True, capture_output=True
    )
    assert without_selection.returncode == 1
    assert not without_selection.stdout
