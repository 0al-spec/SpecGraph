"""Read actual fixture workflow outputs through the criterion lookup entry point."""

# ruff: noqa: E402 -- repository tool packages are not the installed CLI distribution.
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from criterion_evidence_lookup import main
from test_verification_execution import execute
from test_verification_execution import pilot as pilot
from test_verification_execution import retained as retained


def query(pilot, capsys, *, revision=None, runs=True):
    request, settings, *_ = pilot
    scope = request.scope
    args = [
        scope.spec_id,
        "--workspace-root",
        str(settings.repository),
        "--revision",
        revision or scope.declaration_revision,
        "--criterion",
        "/acceptance/1",
        "--repository-id",
        scope.repository_id,
    ]
    if runs:
        args.extend(("--runs-root", str(settings.output_root)))
    code = main(args)
    return code, json.loads(capsys.readouterr().out)


def test_lookup_retains_distinct_runs_and_checks_inputs(pilot, capsys):
    first = execute(pilot).directory
    second = execute(pilot).directory
    failed = execute(pilot, "missing").directory
    code, report = query(pilot, capsys)
    assert code == 0 and report["status"] == "found"
    runs = {row["run_id"]: row for row in report["runs"]}
    assert set(runs) == {first.name, second.name, failed.name}
    for directory in (first, second):
        record = runs[directory.name]
        assert record["recorded_observation"]["observed_outcome"] == "passed"
        assert record["recheck_inputs"] == "available"
        assert record["admission"] == "not_evaluated" and record["receipt"] is None
    assert runs[failed.name]["recorded_observation"] is None
    assert runs[failed.name]["verification_outcome"] != "passed"
    (first / ".verification/journal.ndjson").unlink()
    (second / ".verification/journal.ndjson").write_text("modified")
    _, report = query(pilot, capsys)
    runs = {row["run_id"]: row for row in report["runs"]}
    for directory, status in ((first, "unavailable"), (second, "invalid")):
        record = runs[directory.name]
        assert record["recorded_observation"]["observed_outcome"] == "passed"
        assert record["recheck_inputs"] == status
        assert next(a for a in record["artifacts"] if a["role"] == "journal")["status"] == status


def test_lookup_does_not_substitute_revision_or_report(pilot, capsys):
    result = execute(pilot)
    directory = result.directory
    code, report = query(pilot, capsys, revision=pilot[0].scope.execution_revision)
    assert code == 0 and report["status"] == "not_found"
    code, report = query(pilot, capsys, runs=False)
    assert code == 2 and report["status"] == "unavailable"
    assert report["criterion"]["pointer"] == "/acceptance/1"

    report_path = directory / ".verification/collection.json"
    report_path.unlink()
    _, report = query(pilot, capsys)
    record = report["runs"][0]
    assert record["recorded_observation"] is None and record["recheck_inputs"] == "unavailable"
    assert {item["role"]: item["status"] for item in record["artifacts"]} == {
        "report": "unavailable",
        "passport": "available",
        "plan": "available",
        "journal": "available",
    }
    report_path.symlink_to(directory / "terminal.json")
    _, report = query(pilot, capsys)
    assert report["runs"][0]["recheck_inputs"] == "invalid"
    assert report["runs"][0]["recorded_observation"] is None
