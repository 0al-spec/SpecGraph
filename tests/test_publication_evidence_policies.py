from __future__ import annotations

import ast
import importlib
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from specification_core import TraceRecorder

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import publication_delivery_evidence as pilot
from publication_evidence import context as facts
from publication_evidence.bindings_spec import BINDING_ERROR_SPEC
from publication_evidence.bound_observation_spec import TEST_OBSERVATION_SPEC
from publication_evidence.case_spec import TEST_CASE_SPEC
from publication_evidence.http_observation_spec import HTTP_OBSERVATION_SPEC
from publication_evidence.merged_revision_spec import MERGED_REVISION_SPEC
from publication_evidence.suite_spec import TEST_SUITE_SPEC
from spec_yaml import load_yaml_text

ROOT = Path(__file__).resolve().parents[1]
SOURCE = facts.SourceIdentity("0al-spec/SpecGraph", "a" * 40, (("policy.py", "b" * 64),))
EXECUTION = facts.ExecutionIdentity("github_actions", "12", "2", "run/12")


@pytest.mark.parametrize(
    "change,error_fragment",
    [
        ({}, None),
        ({"requirement_ids": frozenset({"other"})}, "canonical pilot requirement"),
        ({"bound_ids": ()}, "exactly once"),
        ({"bound_ids": ("a", "a")}, "exactly once"),
        ({"selectors": ("tests/a.py::test_a", "tests/a.py::test_a")}, "distinct explicit"),
        ({"selectors": ("tests/a.py", "tests/a.py::test_b")}, "distinct explicit"),
    ],
)
def test_binding_contract(change, error_fragment) -> None:
    context = facts.BindingContext(
        frozenset({"a", "b"}),
        frozenset({"a", "b"}),
        ("a", "b"),
        ("tests/a.py::test_a", "tests/a.py::test_b"),
    )
    error = BINDING_ERROR_SPEC.decide(replace(context, **change)).value
    assert (error is None) if error_fragment is None else error_fragment in error


@pytest.mark.parametrize(
    "count,failed,skipped,expected",
    [
        (0, False, False, "missing"),
        (2, True, False, "missing"),
        (1, True, True, "observed_failure"),
        (1, False, True, "missing"),
        (1, False, False, "observed_success"),
    ],
)
def test_test_case_decision(count, failed, skipped, expected) -> None:
    assert TEST_CASE_SPEC.decide(facts.TestCaseContext(count, failed, skipped)).value == expected


@pytest.mark.parametrize(
    "exit_code,outcomes,count,declared,expected",
    [
        (1, {"observed_success"}, 2, "observed_success", "observed_failure"),
        (0, {"observed_failure", "observed_success"}, 2, "observed_success", "observed_failure"),
        (0, {"missing"}, 2, "observed_success", "missing"),
        (0, {"observed_success"}, 1, "observed_success", "missing"),
        (0, {"observed_success"}, 2, "missing", "missing"),
        (0, set(), 0, "observed_success", "missing"),
        (0, {"observed_success"}, 2, "observed_success", "observed_success"),
    ],
)
def test_test_suite_decision(exit_code, outcomes, count, declared, expected) -> None:
    context = facts.TestSuiteContext(exit_code, frozenset(outcomes), count, 2, declared)
    assert TEST_SUITE_SPEC.decide(context).value == expected


def test_failure_priority_records_skipped_success_branch() -> None:
    recorder = TraceRecorder()
    context = facts.TestSuiteContext(1, frozenset({"observed_success"}), 2, 2)
    assert TEST_SUITE_SPEC.decide(context, recorder=recorder).value == "observed_failure"
    assert ("pair[1]:publication.suite_complete", "skipped") in [
        (event.name, event.outcome.value) for event in recorder.events
    ]


@pytest.mark.parametrize(
    "difference", [None, "repository", "revision", "files", "attempt", "bindings"]
)
def test_test_observation_identity(difference) -> None:
    context = facts.TestObservationContext(
        SOURCE,
        SOURCE,
        EXECUTION,
        EXECUTION,
        (("PB-ALL", "test_a"),),
        (("PB-ALL", "test_a"),),
    )
    if difference in {"repository", "revision", "files"}:
        value = () if difference == "files" else "foreign"
        context = replace(context, observed_source=replace(SOURCE, **{difference: value}))
    elif difference == "attempt":
        context = replace(context, observed_execution=replace(EXECUTION, run_attempt="1"))
    elif difference == "bindings":
        context = replace(context, observed_obligations=(("PB-ALL", "another_test"),))
    assert TEST_OBSERVATION_SPEC.is_satisfied_by(context) is (difference is None)


@pytest.mark.parametrize(
    "change,expected",
    [
        ({}, True),
        ({"expected_bundle": None}, False),
        ({"observed_bundle": ("foreign", "checksum")}, False),
        ({"observed_origin": "https://staging.example"}, False),
        ({"observed_source_revision": "foreign"}, False),
        ({"observed_source_revision": ""}, False),
        ({"source_revision": "", "observed_source_revision": ""}, False),
        (
            {
                "expected_execution": facts.ExecutionIdentity("local", "", "", "local-run"),
                "observed_execution": facts.ExecutionIdentity("local", "", "", "local-run"),
                "observer_environment": "local",
                "observed_source_revision": "",
            },
            False,
        ),
        ({"observed_execution": replace(EXECUTION, run_attempt="1")}, False),
        ({"verified_file_count": 0}, False),
        ({"verified_metadata_count": 1}, False),
        ({"failure_count": 1}, False),
        ({"observer_environment": ""}, False),
        ({"observed_execution": replace(EXECUTION, uri="")}, False),
        ({"expected_execution": facts.ExecutionIdentity("local", "", "", "local-run")}, True),
        ({"status": "failed"}, False),
    ],
)
def test_http_observation_identity(change, expected) -> None:
    context = facts.HttpObservationContext(
        source_revision=SOURCE.revision,
        observed_source_revision=SOURCE.revision,
        expected_execution=EXECUTION,
        observed_execution=EXECUTION,
        observer_environment="ci",
        expected_bundle=("manifest", "checksum"),
        observed_bundle=("manifest", "checksum"),
        expected_origin="https://specgraph.tech",
        observed_origin="https://specgraph.tech",
        status="verified",
        artifact_kind="specgraph_static_artifact_remote_verification_report",
        expected_file_count=1,
        verified_file_count=1,
        verified_metadata_count=2,
        failure_count=0,
    )
    assert HTTP_OBSERVATION_SPEC.is_satisfied_by(replace(context, **change)) is expected


@pytest.mark.parametrize(
    "change,expected",
    [
        ({}, True),
        ({"merged_at": ""}, False),
        ({"observed_revision": "foreign"}, False),
        ({"observed_repository": "another/repo"}, False),
        ({"pull_number": 0}, False),
    ],
)
def test_merged_revision_acceptance(change, expected) -> None:
    context = facts.MergedRevisionContext(
        "2026-10-20T09:00:00Z",
        SOURCE.revision,
        SOURCE.revision,
        SOURCE.repository,
        SOURCE.repository,
        773,
    )
    assert MERGED_REVISION_SPEC.is_satisfied_by(replace(context, **change)) is expected


def test_every_declared_atom_has_a_real_test_and_policy_binding() -> None:
    bindings, _ = pilot.load_pilot(ROOT)
    node = load_yaml_text((ROOT / bindings["spec"]).read_text())
    atoms = {item["id"]: item for item in node["atoms"]["intents"]}
    assert len(atoms) == len(node["atoms"]["intents"])
    publication_ids = {item["id"] for item in node["specification"]["requirement"]["criteria"]}
    policy_ids = set(node["specification"]["delivery_signals"]["policy_atom_ids"])
    assert atoms.keys() == publication_ids | policy_ids
    for criterion in node["specification"]["requirement"]["criteria"]:
        assert criterion["intent_atom_id"] == criterion["id"]
    for atom in atoms.values():
        for selector in atom["verifiable_by"]:
            path, function = selector.split("::")
            tree = ast.parse((ROOT / path).read_text())
            assert any(
                isinstance(item, ast.FunctionDef) and item.name == function for item in tree.body
            )
    bound_ids = []
    adapter_tree = ast.parse((ROOT / "tools/publication_delivery_evidence.py").read_text())
    used_names = {item.id for item in ast.walk(adapter_tree) if isinstance(item, ast.Name)}
    for binding in bindings["policies"]:
        module, symbol = binding["specification"].rsplit(".", 1)
        assert getattr(importlib.import_module(module), symbol).name.startswith("publication.")
        assert symbol in used_names
        bound_ids.extend(binding["atom_ids"])
    assert len(bound_ids) == len(set(bound_ids))
    assert set(bound_ids) == policy_ids


def test_source_identity_includes_extracted_policies() -> None:
    bindings, _ = pilot.load_pilot(ROOT)
    source = pilot.source_identity(ROOT, bindings)
    for path in (ROOT / "tools/publication_evidence").glob("*.py"):
        assert source["files_sha256"][path.relative_to(ROOT).as_posix()] == pilot.file_digest(path)
