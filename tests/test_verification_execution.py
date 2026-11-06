"""Real fixture subprocess and C2c collector; native passport validation is synthetic here."""

# ruff: noqa: E402 -- repository tool packages are not the installed CLI distribution.

import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from test_criterion_observation_provider import (
    SPEC,
    PrevalidatedFixture,
    commit,
    json_bytes,
)
from test_criterion_observation_provider import retained as retained
from traceability.criterion_inputs import sha256
from verification_workflow.execution import execute_verification
from verification_workflow.execution_files import RunFiles
from verification_workflow.execution_invocation import INVOCATION_ENV, MEDIA_TYPE
from verification_workflow.execution_model import (
    BoundCriterion,
    BoundRun,
    ExecutionSettings,
    ProducerCommand,
    ProducerContext,
)
from verification_workflow.execution_pins import prepare_request
from verification_workflow.execution_process import command_ready
from verification_workflow.model import ToolPin

PRODUCER = """import json, os, shutil, signal, subprocess, sys, time, uuid
from pathlib import Path
output, workflow_run_id, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
if mode == "timeout": time.sleep(10)
if mode == "signal": os.kill(os.getpid(), signal.SIGTERM)
if mode == "missing": sys.exit(0)
if mode == "cached":
    shutil.copyfile("old.ndjson", output)
    sys.exit(0)
if mode == "mutation": Path("tracked.txt").write_text("changed")
run_id = "r1" if mode == "fixed_producer_id" else str(uuid.uuid4())
# Only declarations come from the fixture. Assertions and observed values execute below.
declarations = [m for m in json.loads(Path("messages.json").read_text())
                if next(iter(m)) in {"meta", "source", "pickle", "testCase"}]
messages = json.loads(json.dumps(declarations).replace('"r1"', json.dumps(run_id)))
messages += [{"testRunStarted": {"id": run_id}},
             {"testCaseStarted": {"id": "c1s", "testCaseId": "c1", "attempt": 0}}]
challenge = json.loads(os.environ["SPECGRAPH_VERIFICATION_INVOCATION"])
if mode == "wrong_invocation": challenge["nonce"] = "previous-invocation"
marker = {"attachment": {"testCaseStartedId": "c1s", "testStepId": "s0",
    "mediaType": "application/vnd.specgraph.execution-invocation+json",
    "contentEncoding": "IDENTITY", "body": json.dumps(challenge)}}
if mode == "wrong_case": marker["attachment"]["testCaseStartedId"] = "foreign-case"
parcels, closed, issued = [], False, set()
for index in range(4):
    step_id = "s" + str(index)
    identity = {"testCaseStartedId": "c1s", "testStepId": step_id}
    messages.append({"testStepStarted": identity})
    if index == 0 and mode not in {"missing_invocation", "late_invocation"}:
        messages.append(marker)
        if mode == "duplicate_invocation": messages.append(marker)
    if index == 0:
        parcels.append("parcel")
        assert len(parcels) == 1
        measurement = {"count": len(parcels)}
    elif index == 1:
        closed = True
        assert closed
        measurement = {"state": "closed" if closed else "open"}
    elif index == 2:
        first = "parcel" not in issued
        issued.add("parcel")
        assert first
        measurement = {"issued": first}
    else:
        repeated = "parcel" not in issued
        assert not repeated
        measurement = {"reissued": repeated}
    messages.append({"attachment": {**identity, "mediaType": "application/json",
        "contentEncoding": "IDENTITY", "body": json.dumps(measurement)}})
    messages.append({"testStepFinished": {**identity, "testStepResult": {"status": "PASSED"}}})
messages += [{"testCaseFinished": {"testCaseStartedId": "c1s", "willBeRetried": False}},
             {"testRunFinished": {"testRunStartedId": run_id, "success": True}}]
if mode == "late_invocation": messages.append(marker)
if mode == "incomplete": messages = [m for m in messages if "testRunFinished" not in m]
if mode == "symlink":
    output.symlink_to(Path("old.ndjson").resolve())
else:
    output.write_text("\\n".join(json.dumps(m) for m in messages) + "\\n")
if mode == "child": subprocess.Popen([sys.executable, "-c", "import time;time.sleep(10)"])
if mode == "nonzero": sys.exit(4)
"""


@dataclass(frozen=True)
class FixtureProducer:
    template: dict
    mode: str = "pass"
    foreign: Path | None = None

    @property
    def implementation(self):
        return Path(__file__).resolve()

    @property
    def identity(self):
        return ToolPin("fixture.producer", "1", sha256(self.implementation.read_bytes()))

    def prepare(self, context):
        if self.mode == "prepare_mutation":
            (context.snapshot / "tracked.txt").write_text("changed by prepare")

    def command(self, context):
        executable = Path(sys.executable).resolve()
        return ProducerCommand(
            (
                str(executable),
                "producer.py",
                str(context.output / "result.ndjson"),
                context.run_id,
                self.mode,
            ),
            context.snapshot,
            (("PATH", os.defpath), ("PYTHONDONTWRITEBYTECODE", "1")),
            0.1 if self.mode == "timeout" else 5,
            sha256(executable.read_bytes()),
        )

    def journals(self, context):
        if self.foreign:
            return (self.foreign,)
        if self.mode == "old":
            return (context.snapshot / "old.ndjson",)
        return (context.output / "result.ndjson",)

    def bind(self, context, raw):
        messages = [json.loads(line) for line in raw.splitlines()]
        producer_run_id = next(m["testRunStarted"]["id"] for m in messages if "testRunStarted" in m)
        return BoundRun(
            producer_run_id,
            tuple(
                BoundCriterion(
                    b["pointer"],
                    b["case_id"],
                    b["case_started_id"],
                    0,
                    tuple((a["id"], a["step_id"]) for a in b["assertions"]),
                )
                for b in self.template["bindings"]
            ),
        )


@pytest.fixture
def pilot(retained, tmp_path):
    retained.select()
    for name in ("passport.json", "plan.json"):
        (retained.root / name).write_bytes((retained.artifacts / name).read_bytes())
    (retained.root / "producer.py").write_text(PRODUCER)
    (retained.root / "messages.json").write_bytes(json_bytes(retained.journal))
    (retained.root / "old.ndjson").write_bytes((retained.artifacts / "run.ndjson").read_bytes())
    (retained.root / "tracked.txt").write_text("original")
    revision = commit(retained.root, "Fixture execution inputs")
    adapter = FixtureProducer(retained.plan)
    validator = PrevalidatedFixture()
    request = prepare_request(
        retained.root,
        request_id="fixture-request",
        workspace="demo",
        repository_id="demo/project",
        spec_id="TEST-SPEC-0001",
        declaration_revision=retained.scope["revision"],
        execution_revision=revision,
        test_revision=revision,
        spec_path=SPEC,
        passport_path="passport.json",
        template_path="plan.json",
        adapter=adapter,
        validator=validator,
    )
    return request, ExecutionSettings(retained.root, tmp_path / "executions"), adapter, validator


def execute(pilot, mode="pass", **adapter_changes):
    request, settings, adapter, validator = pilot
    return execute_verification(
        request, settings, replace(adapter, mode=mode, **adapter_changes), validator
    )


def test_real_process_collector_and_terminal_record(pilot):
    outcome = execute(pilot)
    assert outcome.result.verification_outcome == "passed"
    terminal = json.loads((outcome.directory / "terminal.json").read_text())
    assert terminal["process"]["exit_code"] == 0
    assert terminal["admission"] == "not_evaluated" and terminal["receipt"] is None
    assert terminal["stages"] == dict.fromkeys(("pin", "execute", "collect", "report"), "completed")
    assert (
        (outcome.directory / ".verification/report.html").read_text().startswith("<!doctype html>")
    )
    assert all(row.observed_outcome == "passed" for row in outcome.result.evidence.rows)
    assert (pilot[1].repository / "tracked.txt").read_text() == "original"
    invocation = json.loads((outcome.directory / ".verification/invocation.json").read_text())
    journal = [
        json.loads(line)
        for line in (outcome.directory / ".verification/journal.ndjson").read_text().splitlines()
    ]
    marker = next(
        m["attachment"] for m in journal if m.get("attachment", {}).get("mediaType") == MEDIA_TYPE
    )
    assert json.loads(marker["body"]) == invocation
    assert invocation["workflow_run_id"] == outcome.directory.name
    assert outcome.result.records.execution.producer_run_id != invocation["workflow_run_id"]
    command = json.loads((outcome.directory / ".verification/command.json").read_text())
    assert INVOCATION_ENV in command["environment_keys"]


@pytest.mark.parametrize(
    "mode",
    [
        "missing",
        "old",
        "symlink",
        "mutation",
        "prepare_mutation",
        "nonzero",
        "timeout",
        "signal",
        "incomplete",
        "child",
    ],
)
def test_producer_failures_and_invalid_outputs_cannot_pass(pilot, mode):
    outcome = execute(pilot, mode)
    assert outcome.result.verification_outcome != "passed"
    assert (outcome.directory / "terminal.json").is_file()
    if mode in {"timeout", "signal"}:
        assert outcome.result.workflow_outcome == "aborted"
    if mode == "nonzero":
        assert outcome.result.workflow_outcome == "completed"
        assert outcome.result.verification_outcome == "failed"
    if mode == "prepare_mutation":
        assert not (outcome.directory / ".verification/process-start.json").exists()
    if mode in {"timeout", "child"}:
        assert not (outcome.directory / ".verification/collection.json").exists()


def test_foreign_output_rejected(pilot, tmp_path):
    path = tmp_path / "foreign.ndjson"
    path.write_text("old")
    assert execute(pilot, foreign=path).result.verification_outcome != "passed"


def test_two_invocations_have_distinct_fresh_output_chains(pilot):
    first, second = execute(pilot), execute(pilot)
    assert first.directory != second.directory
    assert first.result.verification_outcome == second.result.verification_outcome == "passed"
    assert (
        first.result.records.execution.producer_run_id
        != second.result.records.execution.producer_run_id
    )


def test_wrong_revision_is_rejected_before_producer(pilot):
    request, settings, adapter, validator = pilot
    request = replace(request, scope=replace(request.scope, execution_revision="a" * 40))
    outcome = execute_verification(request, settings, adapter, validator)
    assert outcome.result.verification_outcome != "passed"
    assert not (outcome.directory / ".verification/process-start.json").exists()


def test_terminal_write_interruption_does_not_leave_success_record(pilot, monkeypatch):
    def interrupt(self, payload):
        raise OSError("simulated terminal write failure")

    monkeypatch.setattr(RunFiles, "terminal", interrupt)
    with pytest.raises(OSError, match="terminal write"):
        execute(pilot)
    (directory,) = pilot[1].output_root.iterdir()
    assert (directory / ".verification/report.html").is_file()
    assert not (directory / "terminal.json").exists()


def test_run_writer_rejects_symlink_parent_before_writing(tmp_path):
    root, outside = tmp_path / "run", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        RunFiles(root).write("linked/escape.txt", b"must not escape")
    assert list(outside.iterdir()) == []


def test_snapshot_rejects_symlink_git_entry_before_producer(pilot):
    request, settings, adapter, validator = pilot
    (settings.repository / "source-link").symlink_to("tracked.txt")
    revision = commit(settings.repository, "Unsupported symbolic source entry")
    request = replace(request, scope=replace(request.scope, execution_revision=revision))
    outcome = execute_verification(request, settings, adapter, validator)
    assert outcome.result.verification_outcome != "passed"
    assert not (outcome.directory / ".verification/process-start.json").exists()


def test_rejected_passport_prevents_execution(pilot):
    class RejectingValidation:
        def validate(self, raw):
            raise ValueError("passport rejected by validator")

    request, settings, adapter, _ = pilot
    outcome = execute_verification(request, settings, adapter, RejectingValidation())
    assert outcome.result.verification_outcome != "passed"
    assert not (outcome.directory / ".verification/process-start.json").exists()


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), -1])
def test_nonfinite_or_negative_timeout_rejected_before_process(pilot, tmp_path, timeout):
    request, _, adapter, _ = pilot
    context = ProducerContext(request, "not-started", tmp_path, tmp_path)
    command = replace(adapter.command(context), timeout_seconds=timeout)
    with pytest.raises(ValueError, match="timeout"):
        command_ready(command, context)


def test_changed_collection_bytes_cannot_finalize_success(pilot, monkeypatch):
    from verification_workflow import execution_collection

    render = execution_collection.render_html

    def change_after_collection(report):
        (directory,) = pilot[1].output_root.iterdir()
        (directory / ".verification/collection.json").write_text("changed after collection")
        return render(report)

    monkeypatch.setattr(execution_collection, "render_html", change_after_collection)
    outcome = execute(pilot)
    assert outcome.result.verification_outcome == "incomplete"
    assert (outcome.directory / "terminal.json").is_file()
    assert "run artifact changed" in (outcome.directory / ".verification/failure.json").read_text()


@pytest.mark.parametrize(
    "mode",
    [
        "cached",
        "missing_invocation",
        "wrong_invocation",
        "late_invocation",
        "wrong_case",
        "duplicate_invocation",
    ],
)
def test_missing_wrong_or_posthoc_invocation_cannot_pass(pilot, mode):
    outcome = execute(pilot, mode)
    assert outcome.result.verification_outcome != "passed"
    assert outcome.result.records.execution.exit_code == 0
    assert not (outcome.directory / ".verification/collection.json").exists()
    assert "invocation" in (outcome.directory / ".verification/failure.json").read_text()


def test_exact_cached_copy_reproduction_is_rejected_on_both_runs(pilot):
    request, settings, adapter, validator = pilot
    (settings.repository / "producer.py").write_text(
        'import shutil,sys; shutil.copyfile("old.ndjson", sys.argv[1])\n'
    )
    revision = commit(settings.repository, "Reproduce cached-output-only producer")
    request = replace(
        request, scope=replace(request.scope, execution_revision=revision, test_revision=revision)
    )
    outcomes = [execute_verification(request, settings, adapter, validator) for _ in range(2)]
    raw = (settings.repository / "old.ndjson").read_bytes()
    for outcome in outcomes:
        assert outcome.result.verification_outcome != "passed"
        assert outcome.result.records.execution.exit_code == 0
        assert (outcome.directory / "producer/result.ndjson").read_bytes() == raw
    assert outcomes[0].directory != outcomes[1].directory


def test_copy_of_previously_correlated_journal_is_rejected(pilot):
    first = execute(pilot)
    request, settings, adapter, validator = pilot
    old = (first.directory / ".verification/journal.ndjson").read_bytes()
    (settings.repository / "old.ndjson").write_bytes(old)
    (settings.repository / "producer.py").write_text(
        'import shutil,sys; shutil.copyfile("old.ndjson", sys.argv[1])\n'
    )
    revision = commit(settings.repository, "Replay a journal with a prior invocation marker")
    request = replace(
        request, scope=replace(request.scope, execution_revision=revision, test_revision=revision)
    )
    replay = execute_verification(request, settings, adapter, validator)
    assert first.result.verification_outcome == "passed"
    assert replay.result.verification_outcome != "passed"
    assert (replay.directory / "producer/result.ndjson").read_bytes() == old
    assert "challenge mismatch" in (replay.directory / ".verification/failure.json").read_text()


def test_fresh_emission_does_not_require_globally_unused_producer_id(pilot):
    first, second = execute(pilot, "fixed_producer_id"), execute(pilot, "fixed_producer_id")
    assert first.result.verification_outcome == second.result.verification_outcome == "passed"
    assert first.result.records.execution.producer_run_id == "r1"
    assert second.result.records.execution.producer_run_id == "r1"
    payloads = [
        json.loads((outcome.directory / ".verification/invocation.json").read_text())
        for outcome in (first, second)
    ]
    assert payloads[0]["nonce"] != payloads[1]["nonce"]


def test_adapter_cannot_supply_its_own_invocation_challenge(pilot, monkeypatch):
    original = FixtureProducer.command

    def command(self, context):
        selected = original(self, context)
        return replace(selected, environment=(*selected.environment, (INVOCATION_ENV, "old")))

    monkeypatch.setattr(FixtureProducer, "command", command)
    outcome = execute(pilot)
    assert outcome.result.verification_outcome != "passed"
    assert not (outcome.directory / ".verification/process-start.json").exists()
