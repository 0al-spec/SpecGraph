"""Execute the bounded local profile; no CLI, canonical transition or trust admission."""

from dataclasses import asdict
from pathlib import Path
from secrets import token_hex
from uuid import uuid4

from traceability.criterion_inputs import read_regular, sha256
from traceability.criterion_passport import PassportValidation
from traceability.criterion_provider import INPUT_ERRORS

from .execution_collection import collect_and_report, record_execution
from .execution_files import RunFiles, check_snapshot, existing_paths, regular_path, snapshot
from .execution_invocation import invocation_command, validate_invocation
from .execution_model import (
    ExecutionOutcome,
    ExecutionSettings,
    InvocationIdentity,
    ProducerAdapter,
    ProducerContext,
)
from .execution_pins import verify_inputs
from .execution_process import ProcessObservation, command_ready, execute_process
from .model import ExecutionRecord, FilePin, Finalization, PinRecord, Status, VerificationRequest
from .run import VerificationRun


def capture_journal(
    adapter: ProducerAdapter, context: ProducerContext, before: frozenset[Path], files: RunFiles
) -> bytes:
    paths = adapter.journals(context)
    if len(paths) != 1:
        raise ValueError("execution v1 requires exactly one newly produced journal")
    path = regular_path(files.root, paths[0])
    if path in before or not (
        path.is_relative_to(context.snapshot) or path.is_relative_to(context.output)
    ):
        raise ValueError("journal is not a fresh producer-owned output")
    raw = read_regular(path)
    files.pins.append(FilePin(str(path.relative_to(files.root)), sha256(raw)))
    return raw


def failed_stage(run: VerificationRun, process: ProcessObservation | None) -> VerificationRun:
    owner = run.records.owner
    if run.rejection_findings:
        return run
    if run.records.pin is None:
        return run.with_pin(PinRecord(owner, Status.FAILED, False, False))
    if run.records.execution is None:
        return run.with_execution(
            ExecutionRecord(
                owner,
                process.status if process and process.status != Status.COMPLETED else Status.FAILED,
                owner.request.scope.execution_revision,
                None,
                process.exit_code if process else None,
                (),
                None,
            )
        )
    return run


def execute_verification(
    request: VerificationRequest,
    settings: ExecutionSettings,
    adapter: ProducerAdapter,
    validator: PassportValidation,
) -> ExecutionOutcome:
    """The supplied adapter and validator are reviewed operator-installed collaborators.

    Supported producers keep descendants in their POSIX process group. This is
    local custody, not protection against a hostile producer that escapes it.
    The producer must emit the pre-execution invocation challenge from inside
    each selected test case; a newly copied journal is insufficient.
    A failed terminal write raises: callers must not treat existing reports as completion.
    """
    repository = settings.repository.resolve(strict=True)
    settings.output_root.mkdir(parents=True, exist_ok=True)
    output_root = settings.output_root.resolve(strict=True)
    run_id = str(uuid4())
    directory = output_root / run_id
    directory.mkdir(mode=0o700)  # Exclusive even in the improbable event of a UUID collision.
    files = RunFiles(directory)
    run = VerificationRun.begin(request, run_id, used_run_ids=frozenset())
    files.json(".verification/request.json", asdict(request))
    invocation = InvocationIdentity(request.request_id, run_id, token_hex(32))
    files.json(".verification/invocation.json", invocation.to_payload())
    process = None
    intact = False
    try:
        if run.rejection_findings:
            raise ValueError("; ".join(run.rejection_findings))
        passport, template = verify_inputs(repository, request, adapter, validator)
        manifest = snapshot(repository, request.scope.execution_revision, directory / "snapshot")
        files.write(request.scope.passport.artifact.path, passport)
        files.write(".verification/template.json", template)
        files.json(
            ".verification/snapshot.json", [dict(pin=asdict(p), mode=m) for p, m in manifest]
        )
        run = run.with_pin(PinRecord(run.records.owner, Status.COMPLETED, True, True))
        context = ProducerContext(
            request, run_id, directory / "snapshot", directory / "producer", invocation
        )
        context.output.mkdir()
        files.json(".verification/preparation-start.json", {"adapter": asdict(adapter.identity)})
        adapter.prepare(context)
        check_snapshot(context.snapshot, manifest)
        verify_inputs(repository, request, adapter, validator)
        files.json(".verification/preparation-complete.json", {"completed": True})
        command = invocation_command(adapter.command(context), invocation)
        command_ready(command, context)
        check_snapshot(context.snapshot, manifest)
        verify_inputs(repository, request, adapter, validator)
        files.verify()
        before = existing_paths(context.snapshot) | existing_paths(context.output)
        files.json(
            ".verification/command.json",
            {
                "argv": command.argv,
                "cwd": str(command.cwd),
                "environment_keys": sorted(dict(command.environment)),
                "timeout_seconds": command.timeout_seconds,
                "executable_sha256": command.executable_sha256,
            },
        )
        process = execute_process(
            command,
            context,
            directory / ".verification/process.log",
            lambda pid, started: files.json(
                ".verification/process-start.json", {"pid": pid, "started_at": started}
            ),
        )
        files.json(".verification/process.json", asdict(process))
        log = regular_path(directory, directory / ".verification/process.log")
        files.pins.append(
            FilePin(".verification/process.log", sha256(read_regular(log, 128 * 1024 * 1024)))
        )
        if process.timed_out or process.descendants_remaining:
            raise ValueError("producer process group did not finish within the supported boundary")
        check_snapshot(context.snapshot, manifest)
        raw = capture_journal(adapter, context, before, files)
        bound = adapter.bind(context, raw)
        validate_invocation(raw, bound, invocation)
        check_snapshot(context.snapshot, manifest)
        files.verify()
        run = record_execution(run, files, template, raw, bound, process.status, process.exit_code)
        run = collect_and_report(run, files, repository, validator)
        check_snapshot(context.snapshot, manifest)
        verify_inputs(repository, request, adapter, validator)
        command_ready(command, context)
        files.verify()
        intact = True
    except INPUT_ERRORS as error:
        run = failed_stage(run, process)
        files.json(
            ".verification/failure.json", {"kind": type(error).__name__, "detail": str(error)}
        )
    run = run.finalized(Finalization(run.records.owner, intact))
    result = run.result()
    payload = {
        **result.to_payload(),
        "process": asdict(process) if process else None,
        "retained_artifacts": [asdict(pin) for pin in files.pins],
    }
    files.terminal(payload)
    return ExecutionOutcome(directory, result)
