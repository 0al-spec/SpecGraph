from __future__ import annotations

import importlib.util
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


def test_lifecycle_architecture_reports_owners_imports_and_lambda_complexity() -> None:
    module = _load_module()
    report = module.build_report(ROOT, module.load_policy())

    assert report["artifact_kind"] == "lifecycle_architecture_report"
    assert report["policy_sha256"]
    assert report["metric_definition"] == "branch_points_proxy.v1"
    assert report["gate_status"] == "pass"
    assert len(report["head"]["decisions"]) == 8
    assert report["head"]["internal_import_edge_count"] == 36
    assert report["head"]["internal_imports_by_role"]["decision_owner->domain_context"] == 8
    assert report["head"]["internal_imports_by_role"]["decision_owner->decision_owner"] == 9
    assert report["head"]["decision_points_by_role"]["decision_owner"]["predicate_lambda_count"] > 0
    assert (
        report["head"]["decision_points_by_role"]["decision_owner"][
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


def test_lifecycle_architecture_rejects_a_layer_violation(tmp_path: Path) -> None:
    module = _load_module()
    policy = {
        "artifact_kind": "lifecycle_architecture_policy",
        "schema_version": 1,
        "policy_id": "test.v1",
        "modules": [
            {"name": "owner", "path": "tools/owner.py", "role": "decision_owner"},
            {"name": "context", "path": "tools/context.py", "role": "domain_context"},
            {"name": "report", "path": "tools/report.py", "role": "report_adapter"},
        ],
        "role_dependencies": {
            "domain_context": [],
            "decision_owner": ["domain_context"],
            "composition": ["domain_context", "decision_owner"],
            "report_adapter": ["domain_context", "decision_owner", "composition"],
        },
        "decision_dependencies": {},
        "decisions": [
            {
                "id": "test.decision",
                "owner_module": "owner",
                "owner_symbol": "decide",
                "legacy_symbol": "_legacy_decide",
            }
        ],
    }
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "owner.py").write_text(
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
        "from owner import decide\n\n"
        "def label(state):\n"
        "    match state:\n"
        "        case 'ready': return True\n"
        "        case 'blocked': return False\n",
        encoding="utf-8",
    )

    snapshot = module._snapshot(tmp_path, policy, module._module_map(policy), None)

    assert snapshot["gate_status"] == "fail"
    assert snapshot["findings"][0]["code"] == "LAC001"
    assert snapshot["findings"][0]["source"] == "owner"
    assert snapshot["findings"][0]["target"] == "report"
    assert any(
        finding["code"] == "LAC006" and finding["module"] == "idea_maturity_rogue_spec"
        for finding in snapshot["findings"]
    )
    assert snapshot["repeated_dispatch_candidates"][0]["selector"] == "state"
    assert snapshot["repeated_dispatch_candidates"][0]["site_count"] == 2


def test_lifecycle_architecture_compares_legacy_functions_with_current_owners(
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
    assert report["base"]["role"] == "legacy_decision_owner"
    assert report["base"]["scope_basis"] == "eight legacy function bodies, measured independently"
    assert len(report["base"]["decisions"]) == 8
    assert all(item["legacy"]["metrics"] for item in report["head"]["decisions"])


def test_lifecycle_architecture_detects_import_cycles() -> None:
    module = _load_module()

    assert module._cycles([("owner", "context"), ("context", "owner")], {"owner", "context"}) == [
        ["context", "owner", "context"]
    ]
