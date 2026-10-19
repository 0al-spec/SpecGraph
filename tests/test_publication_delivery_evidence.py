from __future__ import annotations

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import publication_delivery_evidence as pilot
from static_artifact_incremental_stage import verify_remote_bundle

ROOT = Path(__file__).resolve().parents[1]


def write_junit(path: Path, obligations: list[dict[str, str]], outcome: str = "pass") -> None:
    suite = ET.Element("testsuite")
    for item in obligations:
        filename, function = item["test"].split("::")
        case = ET.SubElement(
            suite,
            "testcase",
            {
                "classname": filename.removesuffix(".py").replace("/", "."),
                "name": function,
            },
        )
        if outcome != "pass":
            ET.SubElement(case, outcome)
    ET.ElementTree(suite).write(path)


@pytest.mark.parametrize(
    "outcome,exit_code,expected",
    [
        ("pass", 0, "observed_success"),
        ("failure", 1, "observed_failure"),
        ("skipped", 0, "missing"),
        ("pass", 2, "observed_failure"),
    ],
)
def test_junit_requires_each_bound_test_to_complete(
    tmp_path: Path,
    outcome: str,
    exit_code: int,
    expected: str,
) -> None:
    bindings, _ = pilot.load_pilot(ROOT)
    path = tmp_path / "tests.xml"
    write_junit(path, bindings["obligations"], outcome)
    result, observations = pilot.junit_obligations(path, bindings["obligations"], exit_code)
    assert result == expected
    assert len(observations) == 5


def test_missing_or_subset_junit_cannot_supply_omitted_obligations(tmp_path: Path) -> None:
    bindings, _ = pilot.load_pilot(ROOT)
    path = tmp_path / "tests.xml"
    assert pilot.junit_obligations(path, bindings["obligations"], 0)[0] == "missing"
    write_junit(path, bindings["obligations"][:1])
    result, observations = pilot.junit_obligations(path, bindings["obligations"], 0)
    assert result == "missing"
    assert sum(item["result"] == "missing" for item in observations) == 4


def test_duplicate_junit_test_is_not_unique_evidence(tmp_path: Path) -> None:
    bindings, _ = pilot.load_pilot(ROOT)
    path = tmp_path / "tests.xml"
    write_junit(path, bindings["obligations"] + bindings["obligations"][:1])
    assert pilot.junit_obligations(path, bindings["obligations"], 0)[0] == "missing"


def test_failed_collection_discards_old_passing_xml(tmp_path: Path, monkeypatch) -> None:
    bindings, _ = pilot.load_pilot(ROOT)
    write_junit(tmp_path / "tests.xml", bindings["obligations"])
    monkeypatch.setattr(pilot, "source_identity", lambda *_: {"revision": "a" * 40})
    monkeypatch.setattr(
        pilot.subprocess, "run", lambda *_, **__: subprocess.CompletedProcess([], 2)
    )
    assert pilot.run_tests(ROOT, tmp_path) == 1
    result = pilot.load_json(tmp_path / "tests.json")
    assert result["result"] == "observed_failure"
    assert result["junit_sha256"] is None


def test_failed_report_parse_cannot_leave_an_old_success(tmp_path: Path) -> None:
    (tmp_path / "tests.json").write_text("broken JSON")
    (tmp_path / "report.json").write_text('{"stages": "old success"}')
    (tmp_path / "report.md").write_text("old success")
    assert pilot.main(["report", "--output-dir", str(tmp_path)]) == 2
    assert not (tmp_path / "report.json").exists()
    assert not (tmp_path / "report.md").exists()


def test_passport_bindings_cannot_drift_from_graph_requirement(tmp_path: Path) -> None:
    bindings, _ = pilot.load_pilot(ROOT)
    for name in (pilot.DEFAULT_BINDINGS, bindings["passport"], bindings["spec"]):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    node_path = tmp_path / bindings["spec"]
    node = yaml.safe_load(node_path.read_text())
    node["specification"]["requirement"]["criteria"].pop()
    node_path.write_text(yaml.safe_dump(node))
    with pytest.raises(ValueError, match="canonical pilot requirement"):
        pilot.load_pilot(tmp_path)


@pytest.fixture
def evidence(tmp_path: Path, monkeypatch):
    source = {
        "repository": "0al-spec/SpecGraph",
        "revision": "a" * 40,
        "working_tree_clean": True,
        "files_sha256": {"source.py": "b" * 64},
    }
    monkeypatch.setattr(pilot, "source_identity", lambda *_: source)
    monkeypatch.setattr(
        pilot,
        "provenance",
        lambda: {
            "provider": "github_actions",
            "run_id": "12",
            "run_attempt": "2",
            "uri": "run/12",
        },
    )
    bindings, _ = pilot.load_pilot(ROOT)
    tests = {
        "source": dict(source),
        "provenance": pilot.provenance(),
        "exit_code": 0,
        "result": "observed_success",
        "obligations": [{**item, "result": "observed_success"} for item in bindings["obligations"]],
    }
    tests_path = tmp_path / "tests.json"
    pilot.write_json(tests_path, tests)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    payload = bundle / "payload.json"
    payload.write_text("{}")
    pilot.write_json(
        bundle / "artifact_manifest.json",
        {
            "files": [{"path": payload.name, "sha256": pilot.file_digest(payload)}],
        },
    )
    (bundle / "checksums.sha256").write_text("fixture checksum bytes\n")
    runtime = verify_remote_bundle(
        bundle_dir=bundle,
        remote_base_url="https://specgraph.tech",
        fetcher=lambda url: (bundle / url.rsplit("/", 1)[1]).read_bytes(),
        workers=1,
    )
    runtime["execution_context"] = {
        **pilot.provenance(),
        "environment": "ci",
        "source_revision": "a" * 40,
    }
    runtime_path = tmp_path / "runtime.json"
    pilot.write_json(runtime_path, runtime)
    return tests_path, bundle, runtime_path


def test_native_test_and_http_reports_form_linked_table(evidence) -> None:
    tests, bundle, runtime = evidence
    report = pilot.delivery_report(ROOT, tests, bundle, runtime, "production-http")
    assert report["stages"]["tests"]["result"] == "observed_success"
    assert report["stages"]["runtime"]["result"] == "observed_success"
    assert report["stages"]["deploy"]["result"] == "observed_success"
    assert report["stages"]["acceptance"]["result"] == "missing"
    assert report["trust_model"] == "provider_reported"
    assert report["admission"] == "not_evaluated"
    assert "| acceptance | missing |" in pilot.markdown_report(report)


def test_stage_provenance_separates_ci_execution_and_production_target(evidence) -> None:
    tests, bundle, runtime = evidence
    report = pilot.delivery_report(ROOT, tests, bundle, runtime, "production-http")
    assert report["provenance"]["environment"] == "production-http"
    for name, item in report["stages"].items():
        context = item["provenance"]
        assert context["observer"]["environment"] == "ci"
        assert context["observer"]["uri"] == "run/12"
        target = context["target"]
        if name in {"deploy", "runtime"}:
            assert target == {"environment": "production", "uri": "https://specgraph.tech"}
        elif name == "tests":
            assert target == {"environment": "ci", "uri": "run/12"}
        elif name in {"intent", "spec"}:
            assert target["environment"] == "repository"
            assert target["uri"].endswith("/tree/" + "a" * 40)
        else:
            assert target == {
                "environment": "github",
                "uri": "https://github.com/0al-spec/SpecGraph",
            }
    markdown = pilot.markdown_report(report)
    assert "| runtime | observed_success | ci | production: https://specgraph.tech |" in markdown


def test_local_projection_preserves_native_ci_observer(evidence, monkeypatch) -> None:
    tests, bundle, runtime = evidence
    monkeypatch.setattr(
        pilot,
        "provenance",
        lambda: {"provider": "local", "run_id": "", "run_attempt": "", "uri": "local-run"},
    )
    report = pilot.delivery_report(ROOT, tests, bundle, runtime, "local")
    stage = report["stages"]["runtime"]
    assert stage["result"] == "observed_success"
    assert stage["provenance"]["observer"] == {
        "provider": "github_actions",
        "environment": "ci",
        "uri": "run/12",
        "run_id": "12",
        "run_attempt": "2",
    }
    assert stage["provenance"]["target"]["environment"] == "production"


def test_unknown_native_observer_cannot_claim_runtime_success(evidence) -> None:
    tests, bundle, runtime = evidence
    payload = pilot.load_json(runtime)
    del payload["execution_context"]["environment"]
    pilot.write_json(runtime, payload)
    report = pilot.delivery_report(ROOT, tests, bundle, runtime, "ci")
    assert report["stages"]["runtime"]["result"] == "missing"
    assert report["stages"]["runtime"]["provenance"]["observer"] is None


@pytest.mark.parametrize("in_ci", [True, False])
def test_http_verifier_records_its_actual_execution_environment(
    evidence, monkeypatch, in_ci
) -> None:
    _, bundle, _ = evidence
    for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_REPOSITORY", "GITHUB_SERVER_URL"):
        monkeypatch.delenv(key, raising=False)
    if in_ci:
        monkeypatch.setenv("GITHUB_RUN_ID", "37")
        monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "3")
        monkeypatch.setenv("GITHUB_REPOSITORY", "0al-spec/SpecGraph")
    native = verify_remote_bundle(
        bundle_dir=bundle,
        remote_base_url="https://specgraph.tech",
        fetcher=lambda url: (bundle / url.rsplit("/", 1)[1]).read_bytes(),
        workers=1,
    )
    observer = native["execution_context"]
    assert observer["environment"] == ("ci" if in_ci else "local")
    assert observer["provider"] == ("github_actions" if in_ci else "local")
    assert observer["uri"] == (
        "https://github.com/0al-spec/SpecGraph/actions/runs/37" if in_ci else "local-run"
    )


@pytest.mark.parametrize("field", ["source", "attempt", "subset", "skip"])
def test_test_signal_cannot_borrow_another_source_attempt_or_subset(evidence, field) -> None:
    tests, bundle, runtime = evidence
    payload = pilot.load_json(tests)
    if field == "source":
        payload["source"]["revision"] = "f" * 40
    elif field == "attempt":
        payload["provenance"]["run_attempt"] = "1"
    elif field == "subset":
        payload["obligations"].pop()
    else:
        payload["obligations"][0]["result"] = "missing"
    pilot.write_json(tests, payload)
    report = pilot.delivery_report(ROOT, tests, bundle, runtime, "ci")
    assert report["stages"]["tests"]["result"] == "missing"


@pytest.mark.parametrize("field", ["bundle", "attempt", "count", "origin"])
def test_http_signal_requires_matching_bundle_and_execution(evidence, field) -> None:
    tests, bundle, runtime = evidence
    payload = pilot.load_json(runtime)
    if field == "bundle":
        payload["bundle_identity"]["manifest_sha256"] = "f" * 64
    elif field == "attempt":
        payload["execution_context"]["run_attempt"] = "1"
    elif field == "origin":
        payload["remote_base_url"] = "https://foreign.example"
    else:
        payload["summary"]["verified_file_count"] = 0
    pilot.write_json(runtime, payload)
    report = pilot.delivery_report(ROOT, tests, bundle, runtime, "production-http")
    assert report["stages"]["runtime"]["result"] == "missing"


def test_predeploy_report_keeps_absent_stages_missing(evidence) -> None:
    tests, bundle, _ = evidence
    report = pilot.delivery_report(ROOT, tests, bundle, None, "ci")
    assert report["stages"]["tests"]["result"] == "observed_success"
    assert report["stages"]["deploy"]["result"] == "missing"
    assert report["stages"]["runtime"]["result"] == "missing"
    context = report["stages"]["runtime"]["provenance"]
    assert context["observer"] is None
    assert context["target"] == {"environment": "production", "uri": "https://specgraph.tech"}


@pytest.mark.parametrize(
    "change,expected",
    [
        ("none", "observed_success"),
        ("closed_unmerged", "missing"),
        ("revision", "missing"),
        ("repository", "missing"),
    ],
)
def test_acceptance_uses_native_merged_revision_metadata(tmp_path: Path, change, expected) -> None:
    source = {"revision": "a" * 40, "repository": "0al-spec/SpecGraph"}
    row = {
        "number": 773,
        "merged_at": "2026-10-19T14:00:00Z",
        "merge_commit_sha": source["revision"],
        "base": {"repo": {"full_name": source["repository"]}},
    }
    if change == "closed_unmerged":
        row["merged_at"] = None
        row["state"] = "closed"
    elif change == "revision":
        row["merge_commit_sha"] = "b" * 40
    elif change == "repository":
        row["base"]["repo"]["full_name"] = "foreign/repository"
    path = tmp_path / "associated-pulls.json"
    path.write_text(json.dumps([row]))
    result = pilot.acceptance_signal(path, source)
    assert result["result"] == expected
    if expected == "observed_success":
        assert result["evidence"][1]["uri"] == "https://github.com/0al-spec/SpecGraph/pull/773"


def test_unavailable_acceptance_metadata_is_nonblocking(tmp_path: Path) -> None:
    path = tmp_path / "associated-pulls.json"
    source = {"revision": "a" * 40, "repository": "0al-spec/SpecGraph"}
    assert pilot.acceptance_signal(path, source)["result"] == "missing"
    path.write_text("API temporarily unavailable")
    assert pilot.acceptance_signal(path, source)["result"] == "missing"
    path.write_text('[null, {"base": null}]')
    assert pilot.acceptance_signal(path, source)["result"] == "missing"


def test_workflow_retains_same_run_test_inputs_and_postdeploy_report() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/publish-static-artifacts.yml").read_text())
    build = workflow["jobs"]["build"]["steps"]
    names = [step.get("name") for step in build]
    assert names.index("Observe bound publication tests") < names.index("Build bundle")
    retained = next(step for step in build if step.get("name") == "Retain publication test signals")
    deploy = workflow["jobs"]["deploy"]
    downloaded = next(
        step
        for step in deploy["steps"]
        if step.get("name") == "Download bound publication test signals"
    )
    assert retained["with"]["name"] == downloaded["with"]["name"]
    assert retained["with"]["retention-days"] == 30
    assert retained["if"] == "always()"
    summary = next(
        step
        for step in deploy["steps"]
        if step.get("name") == "Summarize publication delivery signals after deploy"
    )
    assert summary["if"] == "always()"
    assert "root-verification.json" in summary["run"]
    assert deploy["needs"] == "build"
