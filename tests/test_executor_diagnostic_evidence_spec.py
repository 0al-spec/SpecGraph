"""Behavioral contract for diagnostic evidence admission, independent of JSON shape."""

import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from specification_core import TraceRecorder


@pytest.mark.parametrize(
    ("origin", "event_kind", "admitted"),
    [
        ("codex_native_event", "error", True),
        ("codex_native_event", "turn.failed", True),
        ("codex_native_event", "turn.completed", False),
        ("codex_native_event", "item.completed", False),
        ("codex_native_event", "unknown", False),
        ("codex_native_event", "", False),
        ("agent_message", "error", False),
        ("agent_message", "turn.failed", False),
        ("command_execution", "error", False),
        ("command_execution", "turn.failed", False),
        ("mcp_tool_call", "error", False),
        ("unknown", "error", False),
    ],
)
def test_diagnostic_admission_requires_native_error_origin(
    supervisor_module, origin, event_kind, admitted
):
    policy = supervisor_module.get_executor_diagnostic_evidence_module()
    context = policy.ExecutorDiagnosticEvidenceContext(origin, event_kind)

    assert policy.EXECUTOR_DIAGNOSTIC_EVIDENCE_SPEC.is_satisfied_by(context) is admitted


def test_diagnostic_admission_has_a_stable_trace_name(supervisor_module):
    policy = supervisor_module.get_executor_diagnostic_evidence_module()
    recorder = TraceRecorder()

    assert policy.EXECUTOR_DIAGNOSTIC_EVIDENCE_SPEC.is_satisfied_by(
        policy.ExecutorDiagnosticEvidenceContext("codex_native_event", "error"),
        recorder=recorder,
    )
    assert recorder.events[0].name == "executor.diagnostic_evidence_admitted"


def test_diagnostic_origin_facts_are_immutable(supervisor_module):
    policy = supervisor_module.get_executor_diagnostic_evidence_module()
    context = policy.ExecutorDiagnosticEvidenceContext("agent_message", "error")

    with pytest.raises(FrozenInstanceError):
        context.origin = "codex_native_event"


def test_file_import_loads_diagnostic_policy_outside_checkout(tmp_path):
    supervisor = Path(__file__).resolve().parents[1] / "tools/supervisor.py"
    script = """
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("isolated_supervisor", sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
print(module.codex_json_error_diagnostics(
    '{"type":"error","message":"failed to open state db"}\\n'
), end="")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script, str(supervisor)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == "codex error: failed to open state db\n"
    assert result.stderr == ""
