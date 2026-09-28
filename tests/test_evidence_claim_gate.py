import copy
import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/evidence_claim_gate.py"
spec = importlib.util.spec_from_file_location("evidence_claim_gate", TOOL)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


@pytest.fixture
def inputs():
    anchor = {
        "repository": "game",
        "revision": "a" * 40,
        "module": "Engine",
        "path": "Rule.swift",
        "symbol": "Rule.evaluate()",
        "language": "swift",
    }
    passport = {
        "metadata": {"passport_id": "fp.game", "version": "1"},
        "spec": {
            "intent": {"acceptance_criteria": [{"id": "rule", "text": "Rule"}]},
            "implementation": {
                "elements": [{"id": "policy", "role": "policy", "anchors": [anchor]}],
                "bindings": [
                    {
                        "id": "binding",
                        "acceptance_criteria_ids": ["rule"],
                        "element_ids": ["policy"],
                    }
                ],
            },
        },
    }
    request = {
        "claims": [{"id": "claim-1", "kind": "source_anchored", "passport_criterion_ids": ["rule"]}]
    }
    report = {
        "validation_issues": [],
        "anchors": [
            {
                **{k: v for k, v in anchor.items() if k != "language"},
                "element_id": "policy",
                "anchor_index": 0,
                "status": "resolved",
                "blob_oid": "b" * 40,
                "detail": "resolved",
            }
        ],
    }
    return request, passport, report


def test_live_resolved_anchors_admit_only_bounded_source_claim(inputs):
    request, passport, report = inputs
    result = gate.evaluate_claims(request, passport, report)
    assert result["admitted"] is True
    assert result["claims"][0]["state"] == "satisfied"
    assert result["claims"][0]["scope"] == "pinned_source_identity_only"
    assert result == gate.evaluate_claims(request, passport, copy.deepcopy(report))


def test_source_success_cannot_promote_runtime_claim(inputs):
    request, passport, report = inputs
    request["claims"][0]["kind"] = "runtime_verified"
    result = gate.evaluate_claims(request, passport, report)
    assert result["admitted"] is False
    assert result["claims"][0]["reason"] == "evidence_evaluator_unavailable"


@pytest.mark.parametrize(
    "mutation", ["empty", "missing", "duplicate", "revision", "unknown", "failed"]
)
def test_insufficient_or_mismatched_evidence_denies_claim(inputs, mutation):
    request, passport, report = inputs
    if mutation == "empty":
        report["anchors"] = []
    elif mutation == "missing":
        passport["spec"]["implementation"]["elements"][0]["anchors"].append(
            copy.deepcopy(passport["spec"]["implementation"]["elements"][0]["anchors"][0])
        )
    elif mutation == "duplicate":
        report["anchors"].append(copy.deepcopy(report["anchors"][0]))
    elif mutation == "revision":
        report["anchors"][0]["revision"] = "c" * 40
    elif mutation == "unknown":
        request["claims"][0]["passport_criterion_ids"] = ["not-in-passport"]
    else:
        report["anchors"][0]["status"] = "symbol_not_found"
    assert gate.evaluate_claims(request, passport, report)["admitted"] is False


def test_unbound_criterion_cannot_be_satisfied_vacuously(inputs):
    request, passport, report = inputs
    passport["spec"]["implementation"]["bindings"] = []
    assert gate.evaluate_claims(request, passport, report)["admitted"] is False


def test_partial_success_does_not_satisfy_parent_request(inputs):
    request, passport, report = inputs
    request["claims"].append(
        {"id": "runtime", "kind": "runtime_verified", "passport_criterion_ids": ["rule"]}
    )
    result = gate.evaluate_claims(request, passport, report)
    assert result["admitted"] is False
    assert [r["state"] for r in result["claims"]] == ["satisfied", "unknown"]


@pytest.mark.parametrize("field", ["state", "verified", "satisfied", "evidence_status"])
def test_canonical_claims_cannot_self_assert_evidence_state(field):
    node = {
        "evidence_claims": [
            {"id": "a", "kind": "runtime_verified", "passport_criterion_ids": ["rule"], field: True}
        ]
    }
    assert gate.canonical_claim_errors(node)


def test_canonical_declaration_has_no_verdict():
    assert not gate.canonical_claim_errors(
        {
            "evidence_claims": [
                {"id": "a", "kind": "runtime_verified", "passport_criterion_ids": ["rule"]}
            ]
        }
    )


def test_empty_request_does_not_succeed(inputs):
    _, passport, report = inputs
    assert gate.evaluate_claims({"claims": []}, passport, report)["admitted"] is False


@pytest.mark.parametrize("value", [None, [], {}, True])
def test_malformed_kind_fails_closed(value):
    assert gate.canonical_claim_errors(
        {"evidence_claims": [{"id": "a", "kind": value, "passport_criterion_ids": ["rule"]}]}
    )


def test_yaml_lint_rejects_authored_verdict(tmp_path):
    import importlib.util

    module_spec = importlib.util.spec_from_file_location(
        "claim_spec_yaml", TOOL.with_name("spec_yaml.py")
    )
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    path = tmp_path / "node.yaml"
    path.write_text(
        "evidence_claims:\n  - id: fake\n    kind: runtime_verified\n"
        "    passport_criterion_ids: [rule]\n    state: satisfied\n"
    )
    assert any("verdicts are derived" in issue.message for issue in module.lint_file(path))


@pytest.fixture
def cli_inputs(tmp_path, inputs):
    import json

    request, passport, report = inputs
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text("id: ZEU-SPEC-0016\nkind: spec\nstatus: reviewed\ngate_state: none\n")
    passport_path = tmp_path / "passport.json"
    passport_path.write_text(json.dumps(passport))
    request.update(
        artifact_kind="evidence_claim_admission_request",
        schema_version=1,
        source={
            "spec_id": "ZEU-SPEC-0016",
            "spec_sha256": gate.digest(spec_path.read_bytes()),
            "passport_sha256": gate.digest(passport_path.read_bytes()),
        },
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request))
    executable = tmp_path / "adapter"
    executable.write_text(
        "#!/usr/bin/env python3\nimport json\nprint(" + repr(json.dumps(report)) + ")\n"
    )
    executable.chmod(0o755)
    return request_path, passport_path, spec_path, executable


def invoke_cli(paths):
    import json
    import subprocess

    request, passport, source, executable = paths
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--request",
            str(request),
            "--passport",
            str(passport),
            "--spec",
            str(source),
            "--feature-passport-cli",
            str(executable),
            "--feature-passport-cli-sha256",
            gate.digest(executable.read_bytes()),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


def test_cli_live_adapter_is_deterministic(cli_inputs):
    first = invoke_cli(cli_inputs)
    assert first[0] == 0
    assert first == invoke_cli(cli_inputs)
    assert first[1]["canonical_mutations_allowed"] is False


@pytest.mark.parametrize("target", [1, 2])
def test_cli_rejects_stale_subject(cli_inputs, target):
    path = cli_inputs[target]
    path.write_bytes(path.read_bytes() + b"\n")
    code, result = invoke_cli(cli_inputs)
    assert code == 1 and result["admitted"] is False
    assert "stale" in result["error"]


def test_cli_pending_review_cannot_admit(cli_inputs):
    import json

    request, _, source, _ = cli_inputs
    source.write_text(source.read_text().replace("none", "review_pending"))
    data = json.loads(request.read_text())
    data["source"]["spec_sha256"] = gate.digest(source.read_bytes())
    request.write_text(json.dumps(data))
    code, result = invoke_cli(cli_inputs)
    assert code == 2
    assert result["claims"][0]["state"] == "satisfied"
    assert result["blockers"] == ["source_gate:review_pending"]


def test_cli_nonzero_adapter_cannot_admit_successful_looking_report(cli_inputs):
    executable = cli_inputs[3]
    executable.write_text(executable.read_text() + "raise SystemExit(1)\n")
    code, result = invoke_cli(cli_inputs)
    assert code == 2 and not result["admitted"]
    assert "source_adapter_unsuccessful" in result["blockers"]


def test_cli_missing_adapter_output_fails_closed(cli_inputs):
    cli_inputs[3].write_text("#!/bin/sh\nexit 0\n")
    code, result = invoke_cli(cli_inputs)
    assert code == 1 and not result["admitted"]


def test_cli_cannot_omit_declared_claims(cli_inputs):
    import json

    request_path, _, source, _ = cli_inputs
    source.write_text(
        source.read_text() + "evidence_claims:\n- id: required-runtime\n  kind: runtime_verified\n"
        "  passport_criterion_ids: [rule]\n"
    )
    request = json.loads(request_path.read_text())
    request["source"]["spec_sha256"] = gate.digest(source.read_bytes())
    request_path.write_text(json.dumps(request))
    code, result = invoke_cli(cli_inputs)
    assert code == 1
    assert "exact canonical" in result["error"]


def test_cli_detects_concurrent_source_change(cli_inputs):
    _, _, source, executable = cli_inputs
    executable.write_text(
        executable.read_text()
        + "from pathlib import Path\nPath("
        + repr(str(source))
        + ").write_text('changed')\n"
    )
    code, result = invoke_cli(cli_inputs)
    assert code == 1
    assert "inputs changed" in result["error"]


def test_cli_requires_trusted_binary_digest(cli_inputs):
    import json
    import subprocess

    request, passport, source, executable = cli_inputs
    process = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--request",
            str(request),
            "--passport",
            str(passport),
            "--spec",
            str(source),
            "--feature-passport-cli",
            str(executable),
            "--feature-passport-cli-sha256",
            "0" * 64,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 1
    assert "untrusted" in json.loads(process.stdout)["error"]
