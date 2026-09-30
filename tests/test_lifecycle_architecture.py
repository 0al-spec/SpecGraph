from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "tools" / "lifecycle_architecture.py"
    spec = importlib.util.spec_from_file_location("_lifecycle_architecture_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_lifecycle_architecture_reports_classifiers_imports_and_lambda_complexity() -> None:
    module = _load_module()
    report = module.build_report(ROOT, module.load_policy())

    assert report["artifact_kind"] == "lifecycle_architecture_report"
    assert report["policy_sha256"]
    assert report["metric_definition"] == "branch_points_proxy.v1"
    assert report["gate_status"] == "pass"
    assert len(report["head"]["decisions"]) == 8
    assert report["head"]["internal_import_edge_count"] == 36
    assert report["head"]["internal_imports_by_role"]["state_classifier->domain_context"] == 8
    assert report["head"]["internal_imports_by_role"]["state_classifier->state_classifier"] == 9
    assert (
        report["head"]["decision_points_by_role"]["state_classifier"]["predicate_lambda_count"] > 0
    )
    assert (
        report["head"]["decision_points_by_role"]["state_classifier"][
            "predicate_lambda_branch_points"
        ]
        > 0
    )


def test_lifecycle_architecture_counts_branch_points_inside_predicate_lambdas() -> None:
    module = _load_module()
    source = """
def decide(context):
    return context.value

_SPEC = PredicateSpec(lambda c: c.present and (c.ready or c.forced))
"""

    metrics = module._decision_metrics(source, "decide")

    assert metrics["predicate_lambda_count"] == 1
    assert metrics["predicate_lambda_branch_points"] == 2
    assert metrics["branch_points_total"] == 2


def test_protected_raw_reads_are_scoped_to_context_parameters_and_predicate_lambdas() -> None:
    module = _load_module()
    source = """
def positional(context: LifecycleStateContext, /):
    return context.artifact("candidate_approval_decision")

def keyword_only(*, context: LifecycleStateContext):
    return context.summary("approval_execution")

def unrelated(c):
    return c.artifact("candidate_approval_decision")

def outer(context: LifecycleStateContext):
    def inner(context):
        return context.artifact("candidate_approval_decision")
    return inner(context)

_SPEC = PredicateSpec(lambda c: c.artifact("approval_execution"))
_NESTED = PredicateSpec(lambda c: (lambda c: c.artifact("approval_execution"))(c))

def _state(c):
    ctx = c
    result = ctx.artifact("candidate_approval_decision")
    c = c.summary("approval_execution")
    return result

_HELPER = PredicateSpec(lambda c: _state(c))
"""

    reads = module._protected_raw_context_reads(
        source, ["candidate_approval_decision", "approval_execution"]
    )

    assert [(read["artifact"], read["accessor"]) for read in reads] == [
        ("candidate_approval_decision", "artifact"),
        ("approval_execution", "summary"),
        ("approval_execution", "artifact"),
        ("candidate_approval_decision", "artifact"),
        ("approval_execution", "summary"),
    ]


def test_protected_raw_read_gate_flags_only_sibling_state_classifiers(tmp_path: Path) -> None:
    module = _load_module()
    policy = {
        "artifact_kind": "lifecycle_architecture_policy",
        "schema_version": 1,
        "policy_id": "test.lifecycle_state_classification.v1",
        "modules": [
            {
                "name": "idea_maturity_classifier_spec",
                "path": "tools/idea_maturity_classifier_spec.py",
                "role": "state_classifier",
            },
            {
                "name": "idea_maturity_peer_spec",
                "path": "tools/idea_maturity_peer_spec.py",
                "role": "state_classifier",
            },
            {
                "name": "idea_maturity_api_peer_spec",
                "path": "tools/idea_maturity_api_peer_spec.py",
                "role": "state_classifier",
            },
            {
                "name": "idea_maturity_context",
                "path": "tools/idea_maturity_context.py",
                "role": "domain_context",
            },
            {
                "name": "idea_maturity_report",
                "path": "tools/idea_maturity_report.py",
                "role": "report_adapter",
            },
        ],
        "role_dependencies": {
            "domain_context": [],
            "state_classifier": ["domain_context"],
            "composition": ["domain_context", "state_classifier"],
            "report_adapter": ["domain_context", "state_classifier", "composition"],
        },
        "decision_dependencies": {"idea_maturity_api_peer_spec": ["idea_maturity_classifier_spec"]},
        "decisions": [
            {
                "id": "lifecycle.candidate_approval_decision",
                "classifier_module": "idea_maturity_classifier_spec",
                "classifier_symbol": "candidate_approval_decision_state",
                "legacy_symbol": "_candidate_approval_decision_state",
                "protected_raw_inputs": ["candidate_approval_decision", "approval_execution"],
            }
        ],
    }
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    sources = {
        "idea_maturity_classifier_spec.py": (
            "def candidate_approval_decision_state(context: LifecycleStateContext):\n"
            "    return context.artifact('candidate_approval_decision')\n"
        ),
        "idea_maturity_peer_spec.py": (
            "_SPEC = PredicateSpec(lambda c: c.summary('approval_execution'))\n"
            "def peer_state(context):\n    return 'unknown'\n"
        ),
        "idea_maturity_api_peer_spec.py": (
            "from idea_maturity_classifier_spec import candidate_approval_decision_state\n"
            "def peer_state(context):\n"
            "    return candidate_approval_decision_state(context)\n"
        ),
        "idea_maturity_context.py": (
            "def read_context(context):\n    return context.artifact('approval_execution')\n"
        ),
        "idea_maturity_report.py": (
            "def render(context):\n    return context.artifact('candidate_approval_decision')\n"
        ),
    }
    for filename, source in sources.items():
        (tools_dir / filename).write_text(source, encoding="utf-8")

    snapshot = module._snapshot(tmp_path, policy, module._module_map(policy), None)
    findings = [finding for finding in snapshot["findings"] if finding["code"] == "LAC007"]

    assert snapshot["gate_status"] == "fail"
    assert findings == [
        {
            "code": "LAC007",
            "decision_id": "lifecycle.candidate_approval_decision",
            "classifier": "idea_maturity_classifier_spec",
            "module": "idea_maturity_peer_spec",
            "line": 1,
            "artifact": "approval_execution",
            "accessor": "summary",
            "message": "sibling state classifier reads a protected raw context artifact",
        }
    ]


def test_real_policy_protects_only_raw_inputs_owned_by_candidate_decision_classifier() -> None:
    module = _load_module()
    policy = module.load_policy()
    decision = next(
        item
        for item in policy["decisions"]
        if item["id"] == "lifecycle.candidate_approval_decision"
    )

    assert decision["protected_raw_inputs"] == [
        "candidate_approval_decision",
        "approval_execution",
    ]
    report = module.build_report(ROOT, policy)
    assert not [finding for finding in report["findings"] if finding["code"] == "LAC007"]


def test_policy_rejects_non_list_protected_raw_inputs(tmp_path: Path) -> None:
    module = _load_module()
    policy = module.load_policy()
    policy["decisions"][2]["protected_raw_inputs"] = "approval_execution"
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    try:
        module.load_policy(policy_path)
    except ValueError as error:
        assert "protected_raw_inputs" in str(error)
    else:
        raise AssertionError("non-list protected_raw_inputs must be rejected")


def test_lifecycle_architecture_rejects_a_layer_violation(tmp_path: Path) -> None:
    module = _load_module()
    policy = {
        "artifact_kind": "lifecycle_architecture_policy",
        "schema_version": 1,
        "policy_id": "test.v1",
        "modules": [
            {"name": "classifier", "path": "tools/classifier.py", "role": "state_classifier"},
            {"name": "context", "path": "tools/context.py", "role": "domain_context"},
            {"name": "report", "path": "tools/report.py", "role": "report_adapter"},
        ],
        "role_dependencies": {
            "domain_context": [],
            "state_classifier": ["domain_context"],
            "composition": ["domain_context", "state_classifier"],
            "report_adapter": ["domain_context", "state_classifier", "composition"],
        },
        "decision_dependencies": {},
        "decisions": [
            {
                "id": "test.decision",
                "classifier_module": "classifier",
                "classifier_symbol": "decide",
                "legacy_symbol": "_legacy_decide",
            }
        ],
    }
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "classifier.py").write_text(
        "from report import render\n\n"
        "def decide(context):\n    return context.value\n\n"
        "def label(state):\n"
        "    match state:\n"
        "        case 'ready': return 'Ready'\n"
        "        case 'blocked': return 'Blocked'\n",
        encoding="utf-8",
    )
    (tools_dir / "context.py").write_text("value = None\n", encoding="utf-8")
    (tools_dir / "report.py").write_text("def render(value):\n    return value\n", encoding="utf-8")
    (tools_dir / "idea_maturity_rogue_spec.py").write_text(
        "from classifier import decide\n\n"
        "def label(state):\n"
        "    match state:\n"
        "        case 'ready': return True\n"
        "        case 'blocked': return False\n",
        encoding="utf-8",
    )

    snapshot = module._snapshot(tmp_path, policy, module._module_map(policy), None)

    assert snapshot["gate_status"] == "fail"
    assert snapshot["findings"][0]["code"] == "LAC001"
    assert snapshot["findings"][0]["source"] == "classifier"
    assert snapshot["findings"][0]["target"] == "report"
    assert any(
        finding["code"] == "LAC006" and finding["module"] == "idea_maturity_rogue_spec"
        for finding in snapshot["findings"]
    )
    assert snapshot["repeated_dispatch_candidates"][0]["selector"] == "state"
    assert snapshot["repeated_dispatch_candidates"][0]["site_count"] == 2


def test_lifecycle_architecture_compares_legacy_functions_with_current_classifiers(
    tmp_path: Path,
) -> None:
    module = _load_module()
    policy = module.load_policy()
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    legacy_symbols = [item["legacy_symbol"] for item in policy["decisions"]]
    legacy_source = "\n\n".join(
        f"def {symbol}(context):\n    return context" for symbol in legacy_symbols
    )
    legacy_report = tools_dir / "idea_maturity_metrics_report.py"
    legacy_report.write_text(legacy_source, encoding="utf-8")
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Lifecycle Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "lifecycle-test@example.invalid"],
        check=True,
    )
    subprocess.run(["git", "-C", str(tmp_path), "add", "tools"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "add legacy decision baseline"],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "-C", str(tmp_path), "tag", "legacy-baseline"], check=True)
    for item in policy["modules"]:
        destination = tmp_path / item["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / item["path"], destination)

    report = module.build_report(tmp_path, policy, base_ref="legacy-baseline")

    assert report["gate_status"] == "pass"
    assert report["base"]["role"] == "legacy_state_classifier"
    assert report["base"]["scope_basis"] == "eight legacy function bodies, measured independently"
    assert len(report["base"]["decisions"]) == 8
    assert all(item["legacy"]["metrics"] for item in report["head"]["decisions"])


def test_lifecycle_architecture_detects_import_cycles() -> None:
    module = _load_module()

    assert module._cycles(
        [("classifier", "context"), ("context", "classifier")], {"classifier", "context"}
    ) == [["classifier", "context", "classifier"]]
