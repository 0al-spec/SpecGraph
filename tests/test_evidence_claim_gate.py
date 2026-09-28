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


def test_adapter_report_digest_covers_raw_stdout_bytes(cli_inputs, inputs):
    import hashlib
    import json

    report = inputs[2]
    raw_report = json.dumps(report, sort_keys=True).encode() + b"\r\n"
    executable = cli_inputs[3]
    executable.write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.stdout.buffer.write(" + repr(raw_report) + ")\n"
    )
    code, result = invoke_cli(cli_inputs)
    assert code == 0, result
    assert result["adapter"]["report_sha256"] == hashlib.sha256(raw_report).hexdigest()


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_json_boundary_rejects_nonfinite_numbers(constant):
    with pytest.raises(ValueError, match="non-finite JSON number"):
        gate.read_json('{"unused":' + constant + "}")


def test_cli_rejects_nonfinite_adapter_response(cli_inputs):
    raw_response = '{"unused": NaN}\n'
    executable = cli_inputs[3]
    executable.write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.stdout.write(" + repr(raw_response) + ")\n"
    )
    code, result = invoke_cli(cli_inputs)
    assert code == 1 and not result["admitted"]
    assert "non-finite JSON number" in result["error"]


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


@pytest.fixture
def runtime_cli_inputs(tmp_path):
    import hashlib
    import json

    def raw_digest(raw):
        return hashlib.sha256(raw).hexdigest()

    mapping = {
        "feature_id": "feature.demo",
        "passport_id": "fp.demo",
        "passport_version": "1",
        "claim_id": "runtime-1",
        "claim_policy_id": "policy.demo",
        "claim_policy_version": "1",
        "claim_policy_digest": "",
        "predicate_profile": "local-aggregate-claim-evaluation-v1",
        "authority_id": "authority.demo",
        "key_id": "key.demo",
    }
    passport_path = tmp_path / "passport.json"
    passport_path.write_text(json.dumps({"metadata": {"passport_id": "fp.demo", "version": "1"}}))
    policy_path = tmp_path / "policy.json"
    policy_raw = b'{"id":"policy.demo","version":"1"}'
    policy_path.write_bytes(policy_raw)
    mapping["claim_policy_digest"] = "sha256:" + raw_digest(policy_raw)
    bundle_path = tmp_path / "bundle.json"
    bundle_raw = b'{"artifact_kind":"local_aggregate_claim_bundle","schema_version":1,"pairs":[]}'
    bundle_path.write_bytes(bundle_raw)
    receipt_trust_path = tmp_path / "receipt-trust.json"
    receipt_trust_raw = b'{"trusted_keys":[]}'
    receipt_trust_path.write_bytes(receipt_trust_raw)
    decision_trust_path = tmp_path / "decision-trust.json"
    decision_trust_path.write_bytes(b'{"trusted_keys":[]}')
    decision = {
        "artifact_kind": "aggregate_claim_decision",
        "schema_version": 1,
        "decision_profile": "fp-aggregate-decision-v1-fields",
        "decision_digest": "sha256:" + "a" * 64,
        "decision": "accepted",
        "feature_id": mapping["feature_id"],
        "passport_id": mapping["passport_id"],
        "passport_version": mapping["passport_version"],
        "claim_id": mapping["claim_id"],
        "claim_policy_id": mapping["claim_policy_id"],
        "claim_policy_version": mapping["claim_policy_version"],
        "claim_policy_digest": mapping["claim_policy_digest"],
        "predicate_profile": mapping["predicate_profile"],
        "evaluation_time": "2026-09-28T00:00:00Z",
        "passport_digest": "sha256:" + raw_digest(passport_path.read_bytes()),
        "bundle_digest": "sha256:" + raw_digest(bundle_raw),
        "receipt_trust_store_digest": "sha256:" + raw_digest(receipt_trust_raw),
        "pair_digests": [],
        "issuer": {"authority_id": mapping["authority_id"], "key_id": mapping["key_id"]},
        "signature": {"algorithm": "test", "profile": "test", "value": "pinned-fixture-signature"},
    }
    decision_path = tmp_path / "decision.json"
    decision_path.write_text(json.dumps(decision))
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        "id: ZEU-SPEC-0016\nkind: spec\nstatus: reviewed\ngate_state: none\n"
        "evidence_claims:\n- id: runtime-1\n  kind: runtime_verified\n"
        "  passport_criterion_ids: [rule]\n  feature_passport_decision:\n"
        + "".join(f"    {key}: {json.dumps(value)}\n" for key, value in mapping.items())
    )
    request = {
        "artifact_kind": "evidence_claim_admission_request",
        "schema_version": 1,
        "claims": [
            {
                "id": "runtime-1",
                "kind": "runtime_verified",
                "passport_criterion_ids": ["rule"],
                "feature_passport_decision": mapping,
            }
        ],
        "source": {
            "spec_id": "ZEU-SPEC-0016",
            "spec_sha256": raw_digest(spec_path.read_bytes()),
            "passport_sha256": raw_digest(passport_path.read_bytes()),
            "runtime": {
                "claim_policy_sha256": raw_digest(policy_raw),
                "bundle_sha256": raw_digest(bundle_raw),
                "decision_sha256": raw_digest(decision_path.read_bytes()),
                "receipt_trust_store_sha256": raw_digest(receipt_trust_raw),
                "decision_trust_store_sha256": raw_digest(decision_trust_path.read_bytes()),
                "feature_passport_cli_sha256": "",
                "pair_files": [],
            },
        },
    }
    request_path = tmp_path / "request.json"
    executable = tmp_path / "feature-passport"
    accepted_report = json.dumps(
        {"trusted": True, "decision": "accepted", "claim_id": "runtime-1", "issues": []}
    )
    executable.write_text("#!/usr/bin/env python3\nprint(" + repr(accepted_report) + ")\n")
    executable.chmod(0o755)
    request["source"]["runtime"]["feature_passport_cli_sha256"] = raw_digest(
        executable.read_bytes()
    )
    request_path.write_text(json.dumps(request))
    return {
        "request": request_path,
        "passport": passport_path,
        "spec": spec_path,
        "cli": executable,
        "policy": policy_path,
        "bundle": bundle_path,
        "decision": decision_path,
        "receipt_trust": receipt_trust_path,
        "decision_trust": decision_trust_path,
    }


def invoke_runtime_cli(paths):
    import json
    import subprocess

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--request",
            str(paths["request"]),
            "--passport",
            str(paths["passport"]),
            "--spec",
            str(paths["spec"]),
            "--feature-passport-cli",
            str(paths["cli"]),
            "--feature-passport-cli-sha256",
            gate.digest(paths["cli"].read_bytes()),
            "--claim-policy",
            str(paths["policy"]),
            "--bundle",
            str(paths["bundle"]),
            "--decision",
            str(paths["decision"]),
            "--receipt-trust-store",
            str(paths["receipt_trust"]),
            "--decision-trust-store",
            str(paths["decision_trust"]),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


def set_runtime_cli_output(paths, output, exit_code=0, mutate_path=None):
    import json

    script = "#!/usr/bin/env python3\nprint(" + repr(output) + ")\n"
    if mutate_path is not None:
        target = repr(str(mutate_path))
        script += (
            "from pathlib import Path\n"
            f"Path({target}).write_bytes(Path({target}).read_bytes() + b' ')\n"
        )
    if exit_code:
        script += f"raise SystemExit({exit_code})\n"
    paths["cli"].write_text(script)
    paths["cli"].chmod(0o755)
    request = json.loads(paths["request"].read_text())
    request["source"]["runtime"]["feature_passport_cli_sha256"] = gate.digest(
        paths["cli"].read_bytes()
    )
    paths["request"].write_text(json.dumps(request))


def test_runtime_verified_requires_fresh_trusted_accepted_decision(runtime_cli_inputs):
    code, result = invoke_runtime_cli(runtime_cli_inputs)
    assert code == 0, result
    assert result["claims"][0]["state"] == "satisfied"
    assert result["claims"][0]["scope"] == "signed_feature_passport_runtime_predicate"
    assert result["runtime_verification"]["executable_sha256"] == gate.digest(
        runtime_cli_inputs["cli"].read_bytes()
    )
    assert result["feature_passport_decision_trusted"] is True


def test_runtime_verified_not_satisfied_remains_unknown(runtime_cli_inputs):
    import json

    decision_path = runtime_cli_inputs["decision"]
    decision = json.loads(decision_path.read_text())
    decision["decision"] = "not_satisfied"
    decision_path.write_text(json.dumps(decision))
    request_path = runtime_cli_inputs["request"]
    request = json.loads(request_path.read_text())
    request["source"]["runtime"]["decision_sha256"] = gate.digest(decision_path.read_bytes())
    request_path.write_text(json.dumps(request))
    set_runtime_cli_output(
        runtime_cli_inputs,
        json.dumps(
            {"trusted": True, "decision": "not_satisfied", "claim_id": "runtime-1", "issues": []}
        ),
    )
    code, result = invoke_runtime_cli(runtime_cli_inputs)
    assert code == 2
    assert result["claims"][0]["state"] == "unknown"
    assert result["claims"][0]["reason"] == "signed_decision_not_accepted"
    assert result["feature_passport_decision_trusted"] is True


def test_runtime_verified_rejects_stale_decision_pin(runtime_cli_inputs):
    runtime_cli_inputs["decision"].write_bytes(runtime_cli_inputs["decision"].read_bytes() + b" ")
    code, result = invoke_runtime_cli(runtime_cli_inputs)
    assert code == 1 and result["admitted"] is False
    assert "stale runtime input digest" in result["error"]


def test_runtime_review_pending_remains_blocker(runtime_cli_inputs):
    import json

    paths = runtime_cli_inputs
    paths["spec"].write_text(
        paths["spec"].read_text().replace("gate_state: none", "gate_state: review_pending")
    )
    request = json.loads(paths["request"].read_text())
    request["source"]["spec_sha256"] = gate.digest(paths["spec"].read_bytes())
    paths["request"].write_text(json.dumps(request))
    code, result = invoke_runtime_cli(paths)
    assert code == 2 and not result["admitted"]
    assert result["claims"][0]["state"] == "satisfied"
    assert result["blockers"] == ["source_gate:review_pending"]


def test_runtime_cli_report_and_exit_are_both_required(runtime_cli_inputs):
    paths = runtime_cli_inputs
    set_runtime_cli_output(
        paths,
        '{"trusted":true,"decision":"accepted","claim_id":"runtime-1","issues":[]}',
        exit_code=1,
    )
    code, result = invoke_runtime_cli(paths)
    assert code == 2 and not result["admitted"]
    assert result["claims"][0]["reason"] == "runtime_decision_untrusted"


def test_runtime_false_trust_report_remains_unknown(runtime_cli_inputs):
    paths = runtime_cli_inputs
    set_runtime_cli_output(
        paths,
        '{"trusted":false,"decision":null,"claim_id":null,"issues":[{"code":"decision_trust_store_invalid"}]}',
    )
    code, result = invoke_runtime_cli(paths)
    assert code == 2 and not result["admitted"]
    assert result["claims"][0]["reason"] == "runtime_decision_untrusted"


def test_runtime_invalid_report_remains_unknown(runtime_cli_inputs):
    paths = runtime_cli_inputs
    set_runtime_cli_output(paths, '{"trusted":true,"trusted":true}')
    code, result = invoke_runtime_cli(paths)
    assert code == 2 and not result["admitted"]
    assert result["claims"][0]["reason"] == "invalid_runtime_verification_report"


def test_runtime_canonical_identity_mismatch_fails_closed(runtime_cli_inputs):
    import json

    paths = runtime_cli_inputs
    source = (
        paths["spec"]
        .read_text()
        .replace('feature_id: "feature.demo"', 'feature_id: "feature.other"')
    )
    paths["spec"].write_text(source)
    request = json.loads(paths["request"].read_text())
    request["source"]["spec_sha256"] = gate.digest(paths["spec"].read_bytes())
    paths["request"].write_text(json.dumps(request))
    code, result = invoke_runtime_cli(paths)
    assert code == 1 and not result["admitted"]
    assert "exact canonical" in result["error"]


def test_runtime_request_must_pin_the_same_cli_bytes(runtime_cli_inputs):
    import json

    paths = runtime_cli_inputs
    request = json.loads(paths["request"].read_text())
    request["source"]["runtime"]["feature_passport_cli_sha256"] = "0" * 64
    paths["request"].write_text(json.dumps(request))
    code, result = invoke_runtime_cli(paths)
    assert code == 1 and not result["admitted"]
    assert "CLI digest pin" in result["error"]


def test_runtime_signed_identity_must_match_canonical_mapping(runtime_cli_inputs):
    import json

    paths = runtime_cli_inputs
    decision = json.loads(paths["decision"].read_text())
    decision["feature_id"] = "feature.other"
    paths["decision"].write_text(json.dumps(decision))
    request = json.loads(paths["request"].read_text())
    request["source"]["runtime"]["decision_sha256"] = gate.digest(paths["decision"].read_bytes())
    paths["request"].write_text(json.dumps(request))
    code, result = invoke_runtime_cli(paths)
    assert code == 1 and not result["admitted"]
    assert "identity does not match canonical" in result["error"]


def test_runtime_original_inputs_are_checked_after_cli(runtime_cli_inputs):
    paths = runtime_cli_inputs
    output = '{"trusted":true,"decision":"accepted","claim_id":"runtime-1","issues":[]}'
    set_runtime_cli_output(paths, output, mutate_path=paths["decision"])
    code, result = invoke_runtime_cli(paths)
    assert code == 1 and not result["admitted"]
    assert "inputs changed during evaluation" in result["error"]


def test_runtime_subprocess_stdout_is_bounded(runtime_cli_inputs):
    import json

    paths = runtime_cli_inputs
    paths["cli"].write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.stdout.write('x' * 1_000_001)\n"
    )
    paths["cli"].chmod(0o755)
    request = json.loads(paths["request"].read_text())
    request["source"]["runtime"]["feature_passport_cli_sha256"] = gate.digest(
        paths["cli"].read_bytes()
    )
    paths["request"].write_text(json.dumps(request))
    code, result = invoke_runtime_cli(paths)
    assert code == 1 and not result["admitted"]
    assert "stdout exceeds output limit" in result["error"]


def test_aggregate_pair_sizes_are_rejected_before_reading(tmp_path):
    observation = tmp_path / "large-observation.json"
    receipt = tmp_path / "receipt.json"
    with observation.open("wb") as stream:
        stream.truncate(9_500_000)
    receipt.write_bytes(b"")
    pair_sources = [(None, None, observation, receipt)] * 7
    with pytest.raises(ValueError, match="aggregate limit"):
        gate._validate_pair_file_sizes(pair_sources)


def test_runtime_and_source_adapters_use_the_same_pinned_cli_snapshot(runtime_cli_inputs, tmp_path):
    import json

    paths = runtime_cli_inputs
    source_marker, runtime_marker = tmp_path / "source-cli-path", tmp_path / "runtime-cli-path"
    spec_text = paths["spec"].read_text()
    spec_text += "- id: source-1\n  kind: source_anchored\n  passport_criterion_ids: [rule]\n"
    paths["spec"].write_text(spec_text)
    request = json.loads(paths["request"].read_text())
    request["claims"].append(
        {"id": "source-1", "kind": "source_anchored", "passport_criterion_ids": ["rule"]}
    )
    request["source"]["spec_sha256"] = gate.digest(paths["spec"].read_bytes())
    script = (
        "#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
        f"source_marker = Path({str(source_marker)!r})\n"
        f"runtime_marker = Path({str(runtime_marker)!r})\n"
        "if sys.argv[1] == 'resolve-sources': source_marker.write_text(sys.argv[0])\n"
        "if sys.argv[1] == 'verify-decision': runtime_marker.write_text(sys.argv[0])\n"
        'print(\'{"trusted":true,"decision":"accepted","claim_id":"runtime-1","issues":[]}\')\n'
    )
    paths["cli"].write_text(script)
    paths["cli"].chmod(0o755)
    request["source"]["runtime"]["feature_passport_cli_sha256"] = gate.digest(
        paths["cli"].read_bytes()
    )
    paths["request"].write_text(json.dumps(request))
    code, result = invoke_runtime_cli(paths)
    assert code == 2  # The fixture passport has no source anchors for source-1.
    assert source_marker.read_text() == runtime_marker.read_text()
    assert source_marker.read_text() != str(paths["cli"].resolve())


def test_bounded_reads_reject_fifo_without_blocking(tmp_path):
    import os

    fifo = tmp_path / "input.fifo"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="regular file"):
        gate.read_bounded(fifo, 100, "test input")


def test_subprocess_stderr_is_bounded():
    command = [sys.executable, "-c", "import sys; sys.stderr.write('x' * 1_000_001)"]
    with pytest.raises(ValueError, match="stderr exceeds output limit"):
        gate.run_bounded(command, 2, 100, 1_000_000)


def test_subprocess_timeout_kills_child_holding_pipes():
    import subprocess
    import time

    command = [
        sys.executable,
        "-c",
        "import subprocess,sys; "
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(15)'])",
    ]
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        gate.run_bounded(command, 0.2, 100, 100)
    assert time.monotonic() - started < 3
