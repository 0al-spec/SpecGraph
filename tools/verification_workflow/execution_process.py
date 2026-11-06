"""Bounded POSIX subprocess execution; surviving process-group members block success."""

import math
import os
import signal
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from traceability.criterion_inputs import read_regular, sha256

from .execution_model import ProducerCommand, ProducerContext
from .execution_process_status_spec import PROCESS_STATUS_SPEC, ProcessCompletion
from .model import Status


@dataclass(frozen=True)
class ProcessObservation:
    status: Status
    exit_code: int | None
    started_at: str
    finished_at: str
    timed_out: bool
    descendants_remaining: bool


def command_ready(command: ProducerCommand, context: ProducerContext) -> Path:
    if (
        os.name != "posix"
        or not command.argv
        or not math.isfinite(command.timeout_seconds)
        or command.timeout_seconds <= 0
    ):
        raise ValueError("the producer requires POSIX, explicit argv and a positive timeout")
    executable = Path(command.argv[0])
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError("producer executable must be explicit and absolute")
    if sha256(read_regular(executable.resolve(), 128 * 1024 * 1024)) != command.executable_sha256:
        raise ValueError("producer executable pin mismatch")
    cwd = command.cwd.resolve(strict=True)
    cwd.relative_to(context.snapshot)
    if len(dict(command.environment)) != len(command.environment):
        raise ValueError("producer environment has duplicate keys")
    return cwd


def group_exists(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    return True


def stop_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def execute_process(
    command: ProducerCommand,
    context: ProducerContext,
    log: Path,
    started_record: Callable[[int, str], None],
) -> ProcessObservation:
    cwd = command_ready(command, context)
    started = datetime.now(timezone.utc).isoformat()
    timed_out = False
    with log.open("xb") as output:
        process = subprocess.Popen(
            command.argv,
            cwd=cwd,
            env=dict(command.environment),
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            started_record(process.pid, started)
            try:
                process.wait(timeout=command.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                stop_group(process)
            descendants = group_exists(process.pid)
        finally:
            # Also cleanup on KeyboardInterrupt/SystemExit; no terminal success is synthesized.
            stop_group(process)
    status = PROCESS_STATUS_SPEC.decide(
        ProcessCompletion(process.returncode, timed_out, descendants),
    ).value
    return ProcessObservation(
        status,
        process.returncode,
        started,
        datetime.now(timezone.utc).isoformat(),
        timed_out,
        descendants,
    )
