from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def supervisor_module() -> object:
    module_path = Path(__file__).resolve().parents[1] / "tools" / "supervisor.py"
    spec = importlib.util.spec_from_file_location("test_supervisor_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if module.yaml is None:

        class JsonYamlShim:
            @staticmethod
            def safe_load(stream: object) -> object:
                if hasattr(stream, "read"):
                    return json.loads(stream.read())
                return json.loads(str(stream))

            @staticmethod
            def safe_dump(
                data: object,
                file_obj: object,
                sort_keys: bool = False,
                allow_unicode: bool = True,
            ) -> None:
                _ = (sort_keys, allow_unicode)
                if hasattr(file_obj, "write"):
                    file_obj.write(json.dumps(data))
                else:
                    raise TypeError("file_obj must support write()")

        module.yaml = JsonYamlShim()
    return module


@pytest.fixture()
def repo_fixture(
    tmp_path: Path,
    supervisor_module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    root = tmp_path
    specs_dir = root / "specs" / "nodes"
    runs_dir = root / "runs"
    specs_dir.mkdir(parents=True)
    runs_dir.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")

    node_path = specs_dir / "SG-SPEC-0001.yaml"
    node_path.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0001",
                "title": "Golden Path Node",
                "kind": "spec",
                "status": "outlined",
                "maturity": 0.2,
                "depends_on": [],
                "relates_to": [],
                "inputs": [],
                "outputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0001.yaml"],
                "acceptance": ["kept"],
                "prompt": "Refine this node.",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(supervisor_module, "ROOT", root)
    monkeypatch.setattr(supervisor_module, "SPECS_DIR", specs_dir)
    monkeypatch.setattr(supervisor_module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", root / ".worktrees")
    monkeypatch.setattr(supervisor_module, "AGENTS_FILE", root / "AGENTS.md")
    return root


def make_fake_worktree(root: Path) -> Path:
    worktree = root / ".fake-worktree"
    if worktree.exists():
        shutil.rmtree(worktree)
    (worktree / "specs").mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "specs" / "nodes", worktree / "specs" / "nodes")
    return worktree


def test_create_isolated_worktree_falls_back_to_sandbox_copy_on_ref_lock_error(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["git", "worktree", "add"],
            returncode=128,
            stdout="",
            stderr=(
                "fatal: cannot lock ref 'refs/heads/codex/test': "
                "Unable to create "
                "'/tmp/repo/.git/refs/heads/codex/test.lock': "
                "Operation not permitted"
            ),
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    worktree_path, branch = supervisor_module.create_isolated_worktree("SG-SPEC-0001")

    assert branch.startswith("sandbox/sg-spec-0001/")
    assert worktree_path.is_dir()
    assert (worktree_path / "AGENTS.md").exists()
    assert (worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml").exists()


def test_build_codex_exec_command_uses_explicit_child_runtime_profile(
    supervisor_module: object,
) -> None:
    cmd = supervisor_module.build_codex_exec_command(prompt="Refine one bounded spec.")

    assert cmd[:2] == ["codex", "exec"]
    assert "--model" in cmd
    assert supervisor_module.CHILD_EXECUTOR_MODEL in cmd
    assert "--sandbox" in cmd
    assert supervisor_module.CHILD_EXECUTOR_SANDBOX in cmd
    assert "--ephemeral" in cmd
    assert "--disable" in cmd
    assert "shell_snapshot" in cmd
    assert "multi_agent" in cmd
    assert f'approval_policy="{supervisor_module.CHILD_EXECUTOR_APPROVAL_POLICY}"' in cmd
    assert f'model_reasoning_effort="{supervisor_module.CHILD_EXECUTOR_REASONING_EFFORT}"' in cmd
    assert cmd[-1] == "Refine one bounded spec."


def test_create_child_codex_home_writes_minimal_config_and_copies_auth(
    supervisor_module: object,
    tmp_path: Path,
) -> None:
    source_home = tmp_path / "source-codex-home"
    source_home.mkdir()
    (source_home / "auth.json").write_text('{"token":"secret"}', encoding="utf-8")

    child_home = supervisor_module.create_child_codex_home(source_codex_home=source_home)
    try:
        config_text = (child_home / "config.toml").read_text(encoding="utf-8")
        assert 'model = "gpt-5.4"' in config_text
        assert 'approval_policy = "never"' in config_text
        assert 'sandbox_mode = "workspace-write"' in config_text
        assert "shell_snapshot = false" in config_text
        assert "multi_agent = false" in config_text
        assert (child_home / "auth.json").read_text(encoding="utf-8") == '{"token":"secret"}'
    finally:
        shutil.rmtree(child_home, ignore_errors=True)


def test_run_codex_uses_isolated_codex_home(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")

        def wait(self) -> int:
            return 0

    captured: dict[str, object] = {}

    def fake_create_child_codex_home(*, source_codex_home: Path = Path()) -> Path:
        _ = source_codex_home
        child_home = repo_fixture / ".fake-codex-home"
        child_home.mkdir(exist_ok=True)
        return child_home

    def fake_popen(
        cmd: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        stdout: object,
        stderr: object,
        text: bool,
        bufsize: int,
    ) -> FakeProcess:
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["env"] = env
        captured["stdout"] = stdout
        captured["stderr"] = stderr
        captured["text"] = text
        captured["bufsize"] = bufsize
        return FakeProcess()

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(node, repo_fixture)

    assert result.returncode == 0
    assert captured["cwd"] == repo_fixture
    assert captured["env"]["CODEX_HOME"] == str(repo_fixture / ".fake-codex-home")
    assert "--ephemeral" in captured["cmd"]


def test_write_latest_summary_includes_executor_environment_fields(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    payload = {
        "run_id": "RUN-1",
        "spec_id": "SG-SPEC-0001",
        "title": "Golden Path Node",
        "outcome": "blocked",
        "gate_state": "blocked",
        "before_status": "outlined",
        "proposed_status": None,
        "final_status": "outlined",
        "validation_errors": ["transport failure"],
        "executor_environment": {
            "issues": [{"kind": "transport_failure"}],
            "primary_failure": True,
        },
        "required_human_action": "repair executor environment and rerun supervisor",
    }

    supervisor_module.write_latest_summary(payload)

    summary = (repo_fixture / "runs" / "latest-summary.md").read_text(encoding="utf-8")
    assert "- executor_environment_issues: 1" in summary
    assert "- executor_environment_primary_failure: yes" in summary
    assert "- required_human_action: repair executor environment and rerun supervisor" in summary


def make_valid_split_proposal(node_data: dict[str, object], run_id: str) -> dict[str, object]:
    spec_id = str(node_data["id"])
    acceptance = [str(item) for item in node_data.get("acceptance", [])]
    retained = [{"acceptance_index": 1, "acceptance_text": acceptance[0]}]
    child_one_items = [
        {"acceptance_index": idx, "acceptance_text": text}
        for idx, text in enumerate(acceptance[1:3], start=2)
    ]
    child_two_items = [
        {"acceptance_index": idx, "acceptance_text": text}
        for idx, text in enumerate(acceptance[3:], start=4)
    ]
    acceptance_mapping = [
        {
            "acceptance_index": 1,
            "acceptance_text": acceptance[0],
            "target": "parent_retained",
        }
    ]
    acceptance_mapping.extend(
        {
            "acceptance_index": item["acceptance_index"],
            "acceptance_text": item["acceptance_text"],
            "target": "child_1",
        }
        for item in child_one_items
    )
    acceptance_mapping.extend(
        {
            "acceptance_index": item["acceptance_index"],
            "acceptance_text": item["acceptance_text"],
            "target": "child_2",
        }
        for item in child_two_items
    )
    return {
        "id": f"refactor_proposal::{spec_id}::oversized_spec",
        "proposal_type": "refactor_proposal",
        "refactor_kind": "split_oversized_spec",
        "target_spec_id": spec_id,
        "source_signal": "oversized_spec",
        "source_run_ids": [run_id],
        "execution_policy": "emit_proposal",
        "parent_after_split": {
            "narrowed_role_summary": (
                "Keep the parent as calculator overview and integration shell."
            ),
            "retained_acceptance": retained,
            "intended_depends_on": [
                {"slot_key": "child_1", "suggested_id": "SG-SPEC-0002"},
                {"slot_key": "child_2", "suggested_id": "SG-SPEC-0003"},
            ],
        },
        "suggested_children": [
            {
                "slot_key": "child_1",
                "suggested_id": "SG-SPEC-0002",
                "suggested_path": "specs/nodes/SG-SPEC-0002.yaml",
                "bounded_concern_summary": "Arithmetic functions",
                "suggested_title": "Calculator - Arithmetic Functions",
                "suggested_prompt": "Refine arithmetic functions as one bounded concern.",
                "assigned_acceptance": child_one_items,
            },
            {
                "slot_key": "child_2",
                "suggested_id": "SG-SPEC-0003",
                "suggested_path": "specs/nodes/SG-SPEC-0003.yaml",
                "bounded_concern_summary": "Input constraints",
                "suggested_title": "Calculator - Input Constraints",
                "suggested_prompt": "Refine input constraints as one bounded concern.",
                "assigned_acceptance": child_two_items,
            },
        ],
        "acceptance_mapping": acceptance_mapping,
        "lineage_updates": {
            "parent_depends_on_add": [
                {"slot_key": "child_1", "suggested_id": "SG-SPEC-0002"},
                {"slot_key": "child_2", "suggested_id": "SG-SPEC-0003"},
            ],
            "child_refines_add": [
                {
                    "slot_key": "child_1",
                    "suggested_id": "SG-SPEC-0002",
                    "refines": [spec_id],
                },
                {
                    "slot_key": "child_2",
                    "suggested_id": "SG-SPEC-0003",
                    "refines": [spec_id],
                },
            ],
        },
        "status": "proposed",
    }


def test_pick_next_spec_gap_prefers_leaf_and_filters_status(supervisor_module: object) -> None:
    spec_node = supervisor_module.SpecNode
    nodes = [
        spec_node(
            path=Path("/tmp/root.yaml"),
            data={"id": "ROOT", "status": "outlined", "maturity": 0.1, "depends_on": []},
        ),
        spec_node(
            path=Path("/tmp/leaf.yaml"),
            data={"id": "LEAF", "status": "specified", "maturity": 0.6, "depends_on": []},
        ),
        spec_node(
            path=Path("/tmp/dependent.yaml"),
            data={"id": "DEP", "status": "outlined", "maturity": 0.2, "depends_on": ["ROOT"]},
        ),
        spec_node(
            path=Path("/tmp/linked.yaml"),
            data={"id": "LINKED", "status": "linked", "maturity": 0.0, "depends_on": []},
        ),
    ]

    selected = supervisor_module.pick_next_spec_gap(nodes)
    assert selected is not None
    assert selected.id == "LEAF"


def test_pick_next_spec_gap_allows_retry_pending(supervisor_module: object) -> None:
    spec_node = supervisor_module.SpecNode
    nodes = [
        spec_node(
            path=Path("/tmp/retry.yaml"),
            data={
                "id": "RETRY",
                "status": "specified",
                "maturity": 0.4,
                "depends_on": [],
                "gate_state": "retry_pending",
            },
        ),
    ]

    selected = supervisor_module.pick_next_spec_gap(nodes)
    assert selected is not None
    assert selected.id == "RETRY"


def test_pick_next_spec_gap_prioritizes_nearest_unlocked_ancestor(
    supervisor_module: object,
) -> None:
    spec_node = supervisor_module.SpecNode
    nodes = [
        spec_node(
            path=Path("/tmp/a.yaml"),
            data={"id": "A", "status": "specified", "maturity": 0.7, "depends_on": ["B"]},
        ),
        spec_node(
            path=Path("/tmp/b.yaml"),
            data={"id": "B", "status": "specified", "maturity": 0.5, "depends_on": ["C"]},
        ),
        spec_node(
            path=Path("/tmp/c.yaml"),
            data={"id": "C", "status": "outlined", "maturity": 0.2, "depends_on": []},
        ),
    ]

    selected = supervisor_module.pick_next_spec_gap(nodes)
    assert selected is not None
    assert selected.id == "B"


def test_pick_next_work_item_prefers_graph_refactor_queue_item(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    queue_path = repo_fixture / "runs" / "refactor_queue.json"
    queue_path.write_text(
        json.dumps(
            [
                {
                    "id": "graph_refactor::SG-SPEC-0001::oversized_spec",
                    "work_item_type": "graph_refactor",
                    "spec_id": "SG-SPEC-0001",
                    "signal": "oversized_spec",
                    "recommended_action": "split_or_narrow_spec",
                    "status": "proposed",
                    "source_run_id": "RUN-1",
                },
                {
                    "id": "governance_proposal::SG-SPEC-0001::repeated_split_required_candidate",
                    "work_item_type": "governance_proposal",
                    "spec_id": "SG-SPEC-0001",
                    "signal": "repeated_split_required_candidate",
                    "recommended_action": "review_decomposition_policy",
                    "status": "proposed",
                    "source_run_id": "RUN-1",
                },
            ]
        ),
        encoding="utf-8",
    )

    node, work_item = supervisor_module.pick_next_work_item(supervisor_module.load_specs())

    assert node is not None
    assert node.id == "SG-SPEC-0001"
    assert work_item is not None
    assert work_item["work_item_type"] == "graph_refactor"
    assert work_item["signal"] == "oversized_spec"
    assert work_item["execution_policy"] == "direct_graph_update"


def test_pick_next_work_item_ignores_governance_proposals_for_auto_execution(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    queue_path = repo_fixture / "runs" / "refactor_queue.json"
    queue_path.write_text(
        json.dumps(
            [
                {
                    "id": "governance_proposal::SG-SPEC-0001::repeated_split_required_candidate",
                    "work_item_type": "governance_proposal",
                    "spec_id": "SG-SPEC-0001",
                    "signal": "repeated_split_required_candidate",
                    "recommended_action": "review_decomposition_policy",
                    "status": "proposed",
                    "source_run_id": "RUN-1",
                }
            ]
        ),
        encoding="utf-8",
    )

    node, work_item = supervisor_module.pick_next_work_item(supervisor_module.load_specs())

    assert node is not None
    assert node.id == "SG-SPEC-0001"
    assert work_item is None


def test_pick_next_work_item_defers_graph_refactor_when_active_proposal_exists(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    (repo_fixture / "runs" / "refactor_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "graph_refactor::SG-SPEC-0001::oversized_spec",
                    "work_item_type": "graph_refactor",
                    "spec_id": "SG-SPEC-0001",
                    "signal": "oversized_spec",
                    "recommended_action": "split_or_narrow_spec",
                    "status": "proposed",
                    "source_run_id": "RUN-1",
                    "execution_policy": "direct_graph_update",
                }
            ]
        ),
        encoding="utf-8",
    )
    (repo_fixture / "runs" / "proposal_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "refactor_proposal::SG-SPEC-0001::oversized_spec",
                    "proposal_type": "refactor_proposal",
                    "spec_id": "SG-SPEC-0001",
                    "signal": "oversized_spec",
                    "status": "proposed",
                    "execution_policy": "emit_proposal",
                }
            ]
        ),
        encoding="utf-8",
    )

    node, work_item = supervisor_module.pick_next_work_item(supervisor_module.load_specs())

    assert node is not None
    assert node.id == "SG-SPEC-0001"
    assert work_item is None


def test_observe_graph_health_reports_reflective_signals(
    supervisor_module: object,
) -> None:
    spec_node = supervisor_module.SpecNode
    source = spec_node(
        path=Path("/tmp/source.yaml"),
        data={
            "id": "SG-SPEC-9999",
            "title": "Working Node",
            "kind": "spec",
            "status": "specified",
            "maturity": 0.4,
            "depends_on": ["MISSING"],
            "acceptance": [f"criterion-{i}" for i in range(6)],
            "prompt": "Refine one bounded slice of this node.",
            "last_outcome": "split_required",
        },
    )

    graph_health = supervisor_module.observe_graph_health(
        source_node=source,
        worktree_specs=[source],
        reconciliation={"semantic_dependencies_resolved": False},
        atomicity_errors=[],
        outcome="split_required",
    )

    assert graph_health["source_spec_id"] == "SG-SPEC-9999"
    assert "oversized_spec" in graph_health["signals"]
    assert "missing_dependency_target" in graph_health["signals"]
    assert "repeated_split_required_candidate" in graph_health["signals"]
    assert "stalled_maturity_candidate" in graph_health["signals"]
    assert "weak_structural_linkage_candidate" in graph_health["signals"]
    assert "split_or_narrow_spec" in graph_health["recommended_actions"]


def test_observe_graph_health_does_not_mark_source_oversized_for_child_atomicity(
    supervisor_module: object,
) -> None:
    spec_node = supervisor_module.SpecNode
    source = spec_node(
        path=Path("/tmp/source.yaml"),
        data={
            "id": "SG-SPEC-9999",
            "title": "Working Node",
            "kind": "spec",
            "status": "specified",
            "maturity": 0.4,
            "depends_on": [],
            "acceptance": ["criterion-1"],
            "prompt": "Refine one bounded slice of this node.",
        },
    )

    graph_health = supervisor_module.observe_graph_health(
        source_node=source,
        worktree_specs=[source],
        reconciliation={"semantic_dependencies_resolved": True},
        atomicity_errors=[
            "specs/nodes/SG-SPEC-1000.yaml: Atomicity gate exceeded: child is oversized"
        ],
        outcome="done",
    )

    assert "oversized_spec" not in graph_health["signals"]
    assert not any(
        observation["kind"] == "oversized_spec" for observation in graph_health["observations"]
    )


def test_update_refactor_queue_writes_classified_work_items(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    graph_health = {
        "source_spec_id": "SG-SPEC-9999",
        "observations": [
            {"kind": "oversized_spec", "details": ["too many acceptance criteria"]},
            {
                "kind": "repeated_split_required_candidate",
                "details": (
                    "Consecutive split_required outcomes suggest persistent non-atomic scope."
                ),
            },
        ],
        "signals": ["oversized_spec", "repeated_split_required_candidate"],
        "recommended_actions": ["split_or_narrow_spec", "review_decomposition_policy"],
    }

    path = supervisor_module.update_refactor_queue(graph_health=graph_health, run_id="RUN-1")
    assert path == repo_fixture / "runs" / "refactor_queue.json"

    items = json.loads(path.read_text(encoding="utf-8"))
    assert len(items) == 2
    oversized = next(item for item in items if item["signal"] == "oversized_spec")
    repeated_split = next(
        item for item in items if item["signal"] == "repeated_split_required_candidate"
    )

    assert oversized["work_item_type"] == "graph_refactor"
    assert oversized["recommended_action"] == "split_or_narrow_spec"
    assert oversized["execution_policy"] == "direct_graph_update"
    assert repeated_split["work_item_type"] == "governance_proposal"
    assert repeated_split["recommended_action"] == "review_decomposition_policy"
    assert repeated_split["execution_policy"] == "emit_proposal"


def test_update_refactor_queue_defers_direct_execution_when_active_proposal_exists(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    graph_health = {
        "source_spec_id": "SG-SPEC-9999",
        "observations": [
            {"kind": "oversized_spec", "details": ["too many acceptance criteria"]},
        ],
        "signals": ["oversized_spec"],
        "recommended_actions": ["split_or_narrow_spec"],
    }
    proposal_items = [
        {
            "id": "refactor_proposal::SG-SPEC-9999::oversized_spec",
            "proposal_type": "refactor_proposal",
            "spec_id": "SG-SPEC-9999",
            "signal": "oversized_spec",
            "status": "proposed",
            "execution_policy": "emit_proposal",
        }
    ]

    path = supervisor_module.update_refactor_queue(
        graph_health=graph_health,
        run_id="RUN-1",
        proposal_items=proposal_items,
    )
    items = json.loads(path.read_text(encoding="utf-8"))

    assert len(items) == 1
    item = items[0]
    assert item["execution_policy"] == "defer_to_active_proposal"


def test_update_proposal_queue_emits_governance_proposal_immediately(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    graph_health = {
        "source_spec_id": "SG-SPEC-9999",
        "observations": [
            {
                "kind": "repeated_split_required_candidate",
                "details": (
                    "Consecutive split_required outcomes suggest persistent non-atomic scope."
                ),
            }
        ],
        "signals": ["repeated_split_required_candidate"],
        "recommended_actions": ["review_decomposition_policy"],
    }

    path, items = supervisor_module.update_proposal_queue(graph_health=graph_health, run_id="RUN-2")
    assert path == repo_fixture / "runs" / "proposal_queue.json"

    assert len(items) == 1
    proposal = items[0]
    assert proposal["proposal_type"] == "governance_proposal"
    assert proposal["signal"] == "repeated_split_required_candidate"
    assert proposal["trigger"] == "governance_class_signal"
    assert proposal["occurrence_count"] == 1
    assert proposal["threshold"] == 1
    assert proposal["supporting_run_ids"] == ["RUN-2"]
    assert proposal["execution_policy"] == "emit_proposal"


def test_update_proposal_queue_requires_recurrence_for_refactor_proposal(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    historical_run = {
        "run_id": "RUN-1",
        "graph_health": {
            "source_spec_id": "SG-SPEC-9999",
            "signals": ["oversized_spec"],
        },
    }
    (repo_fixture / "runs" / "20260405T000000Z-SG-SPEC-9999.json").write_text(
        json.dumps(historical_run),
        encoding="utf-8",
    )

    graph_health = {
        "source_spec_id": "SG-SPEC-9999",
        "observations": [
            {"kind": "oversized_spec", "details": ["too many acceptance criteria"]},
        ],
        "signals": ["oversized_spec"],
        "recommended_actions": ["split_or_narrow_spec"],
    }

    path, items = supervisor_module.update_proposal_queue(graph_health=graph_health, run_id="RUN-2")

    assert len(items) == 1
    proposal = items[0]
    assert proposal["proposal_type"] == "refactor_proposal"
    assert proposal["signal"] == "oversized_spec"
    assert proposal["trigger"] == "recurring_signal"
    assert proposal["occurrence_count"] == 2
    assert proposal["threshold"] == 2
    assert proposal["supporting_run_ids"] == ["RUN-1", "RUN-2"]
    assert proposal["execution_policy"] == "emit_proposal"


def test_update_proposal_queue_counts_current_occurrence_when_run_id_collides(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    historical_run = {
        "run_id": "RUN-1",
        "graph_health": {
            "source_spec_id": "SG-SPEC-9999",
            "signals": ["oversized_spec"],
        },
    }
    (repo_fixture / "runs" / "20260405T000000Z-SG-SPEC-9999.json").write_text(
        json.dumps(historical_run),
        encoding="utf-8",
    )

    graph_health = {
        "source_spec_id": "SG-SPEC-9999",
        "observations": [
            {"kind": "oversized_spec", "details": ["too many acceptance criteria"]},
        ],
        "signals": ["oversized_spec"],
        "recommended_actions": ["split_or_narrow_spec"],
    }

    _path, items = supervisor_module.update_proposal_queue(
        graph_health=graph_health,
        run_id="RUN-1",
    )

    assert len(items) == 1
    proposal = items[0]
    assert proposal["proposal_type"] == "refactor_proposal"
    assert proposal["occurrence_count"] == 2
    assert proposal["supporting_run_ids"] == ["RUN-1"]


def test_build_prompt_includes_bootstrap_child_guidance_for_seed_spec(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["allowed_paths"] = ["specs/nodes/*.yaml"]
    data["prompt"] = "This spec is a seed ontology. Use child specs to refine unresolved areas."
    node_path.write_text(json.dumps(data), encoding="utf-8")

    node = supervisor_module.load_specs()[0]
    prompt = supervisor_module.build_prompt(node)

    assert "Refinement policy:" in prompt
    assert "Treat the current spec as one bounded piece of a larger puzzle graph." in prompt
    assert (
        "Prefer the smallest honest change that can advance this node by one status step." in prompt
    )
    assert "Do not try to make the current spec complete in one run." in prompt
    assert "Bootstrap guidance:" in prompt
    assert "Suggested first child spec ID: SG-SPEC-0002" in prompt
    assert "Suggested child spec path: specs/nodes/SG-SPEC-0002.yaml" in prompt
    assert "You may create one or more new child specs in this run" in prompt


def test_build_prompt_includes_incremental_refinement_policy_for_non_seed_spec(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["prompt"] = "Refine one bounded slice of this node."
    node_path.write_text(json.dumps(data), encoding="utf-8")

    node = supervisor_module.load_specs()[0]
    prompt = supervisor_module.build_prompt(node)

    assert "Refinement policy:" in prompt
    assert "Resolve at most one concrete unresolved area per run." in prompt
    assert "Aim for one bounded concern per spec node, not one large document." in prompt
    expected_path_choice = (
        "If multiple independent refinement paths are possible, "
        "choose one and leave the others unchanged."
    )
    expected_child_preference = (
        "Prefer creating or refining one child spec over expanding "
        "the parent when the topic is separable."
    )
    expected_split_rule = (
        "If the node remains non-atomic after your edits, end with RUN_OUTCOME: split_required."
    )
    assert expected_path_choice in prompt
    assert expected_child_preference in prompt
    assert expected_split_rule in prompt
    assert "Bootstrap guidance:" not in prompt


def test_build_prompt_includes_ancestor_reconciliation_guidance(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    specs_dir = repo_fixture / "specs" / "nodes"
    child_path = specs_dir / "SG-SPEC-0002.yaml"
    child_path.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Child",
                "kind": "spec",
                "status": "outlined",
                "maturity": 0.2,
                "depends_on": [],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["criterion"],
                "prompt": "Refine child.",
            }
        ),
        encoding="utf-8",
    )

    node_path = specs_dir / "SG-SPEC-0001.yaml"
    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["status"] = "specified"
    data["depends_on"] = ["SG-SPEC-0002"]
    data["prompt"] = "Reconcile this ancestor with its unlocked child."
    node_path.write_text(json.dumps(data), encoding="utf-8")

    node = supervisor_module.load_specs()[0]
    prompt = supervisor_module.build_prompt(node)

    assert "Refinement mode: ancestor_reconcile" in prompt
    assert (
        "This spec appears semantically unlocked by descendant specs that already exist." in prompt
    )
    assert "Prefer updating links, acceptance_evidence, blockers," in prompt
    assert "and status-readiness over expanding scope." in prompt


def test_build_prompt_includes_graph_refactor_guidance(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node = supervisor_module.load_specs()[0]
    prompt = supervisor_module.build_prompt(
        node,
        {
            "id": "graph_refactor::SG-SPEC-0001::oversized_spec",
            "work_item_type": "graph_refactor",
            "signal": "oversized_spec",
            "recommended_action": "split_or_narrow_spec",
            "source_run_id": "RUN-1",
            "details": ["too many acceptance criteria"],
        },
    )

    assert "Refinement mode: graph_refactor" in prompt
    assert "This run was selected from the derived refactor queue." in prompt
    assert "Signal: oversized_spec" in prompt
    assert "Recommended action: split_or_narrow_spec" in prompt
    assert "too many acceptance criteria" in prompt


def test_build_prompt_includes_split_refactor_proposal_guidance(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["title"] = "Calculator Overview"
    data["prompt"] = "Keep this parent as overview and split detailed concerns."
    data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(data), encoding="utf-8")

    node = supervisor_module.load_specs()[0]
    work_item = supervisor_module.build_split_refactor_work_item(node)
    work_item["planned_run_id"] = "RUN-1"
    prompt = supervisor_module.build_prompt(node, work_item)

    assert "Refinement mode: split_refactor_proposal" in prompt
    assert "This run was explicitly targeted by the operator for split_oversized_spec." in prompt
    assert "Proposal artifact path: runs/proposals/" in prompt
    assert "source_run_ids must include the current run ID above." in prompt
    assert "Current parent acceptance criteria:" in prompt
    assert "- [1] criterion-1" in prompt


def test_main_creates_review_gate_and_provenance_metadata(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module,
        "git_changed_files",
        lambda _cwd=None: changed_snapshots.pop(0),
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        node_path = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
        data["acceptance_evidence"] = ["criterion satisfied by refined section"]
        data["prompt"] = "Updated by Codex"
        node_path.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 0

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "outlined"
    assert updated["gate_state"] == "review_pending"
    assert updated["proposed_status"] == "specified"
    assert updated["last_outcome"] == "done"
    assert updated["last_branch"] == "codex/sg-spec-0001/test"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["spec_id"] == "SG-SPEC-0001"
    assert payload["outcome"] == "done"
    assert payload["worktree_path"] == worktree.as_posix()
    assert payload["graph_health"]["source_spec_id"] == "SG-SPEC-0001"
    assert payload["refactor_queue_artifact"].endswith("runs/refactor_queue.json")
    assert payload["proposal_queue_artifact"].endswith("runs/proposal_queue.json")
    assert payload["selected_by_rule"]["selection_mode"] == "default_refine"
    assert payload["selected_by_rule"]["sort_order"] == [
        "refactor_queue_first",
        "ancestor_reconcile_first",
        "nearest_unlocked_ancestor",
        "leaf_first",
        "lower_maturity",
        "stable_id",
    ]
    assert (repo_fixture / "runs" / "latest-summary.md").exists()


def test_main_blocks_executor_environment_failures_without_graph_health_side_effects(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], []]
    monkeypatch.setattr(
        supervisor_module,
        "git_changed_files",
        lambda _cwd=None: changed_snapshots.pop(0),
    )

    def fake_executor(_node: object, _worktree_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=1,
            stdout="RUN_OUTCOME: escalate\nBLOCKER: none\n",
            stderr=(
                "mcp: playwright failed: MCP client for `playwright` timed out after 10 seconds.\n"
                "ERROR: stream disconnected before completion: "
                "error sending request for url "
                "(https://chatgpt.com/backend-api/codex/responses)\n"
            ),
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["gate_state"] == "blocked"
    assert updated["required_human_action"] == "repair executor environment and rerun supervisor"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["executor_environment"]["primary_failure"] is True
    assert set(payload["executor_environment"]["issue_kinds"]) == {
        "mcp_startup_failure",
        "transport_failure",
    }
    assert payload["graph_health"]["signals"] == []
    assert payload["validator_results"]["executor_environment"] is False
    assert any(
        "transport_failure" in error or "stream disconnected before completion" in error
        for error in payload["validation_errors"]
    )
    assert not (repo_fixture / "runs" / "proposal_queue.json").exists()
    assert not (repo_fixture / "runs" / "refactor_queue.json").exists()


def test_main_does_not_treat_websocket_fallback_warning_as_primary_transport_failure(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], []]
    monkeypatch.setattr(
        supervisor_module,
        "git_changed_files",
        lambda _cwd=None: changed_snapshots.pop(0),
    )

    def fake_executor(_node: object, _worktree_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=1,
            stdout="RUN_OUTCOME: blocked\nBLOCKER: missing upstream spec\n",
            stderr="warning: falling back from websockets to https transport\n",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["gate_state"] == "blocked"
    assert updated["required_human_action"] == "resolve blocker"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["executor_environment"]["issues"] == []
    assert payload["executor_environment"]["primary_failure"] is False
    assert payload["graph_health"]["source_spec_id"] == "SG-SPEC-0001"
    assert payload["validator_results"]["executor_environment"] is True


def test_main_selects_graph_refactor_work_item_before_default_gap(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_path = repo_fixture / "runs" / "refactor_queue.json"
    queue_path.write_text(
        json.dumps(
            [
                {
                    "id": "graph_refactor::SG-SPEC-0001::missing_dependency_target",
                    "work_item_type": "graph_refactor",
                    "spec_id": "SG-SPEC-0001",
                    "signal": "missing_dependency_target",
                    "recommended_action": "repair_canonical_dependencies",
                    "status": "proposed",
                    "source_run_id": "RUN-1",
                    "details": ["SG-SPEC-9999"],
                }
            ]
        ),
        encoding="utf-8",
    )

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module,
        "git_changed_files",
        lambda _cwd=None: changed_snapshots.pop(0),
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        node_path = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
        data["acceptance_evidence"] = ["criterion satisfied by refined section"]
        node_path.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 0

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["selected_by_rule"]["selection_mode"] == "graph_refactor"
    assert (
        payload["selected_by_rule"]["refactor_work_item"]["signal"] == "missing_dependency_target"
    )
    assert (
        payload["selected_by_rule"]["refactor_work_item"]["recommended_action"]
        == "repair_canonical_dependencies"
    )
    assert payload["proposed_status"] is None

    updated = supervisor_module.get_yaml_module().safe_load(
        (repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml").read_text(encoding="utf-8")
    )
    assert updated["status"] == "outlined"
    assert updated["gate_state"] == "review_pending"
    assert updated["proposed_status"] is None


def test_main_split_proposal_emits_structured_artifact_and_queue_entry(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Calculator Overview"
    node_data["prompt"] = "Keep the parent as overview and split detailed concerns."
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")
    before_text = node_path.read_text(encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/split-proposal"),
    )

    work_item = supervisor_module.build_split_refactor_work_item(supervisor_module.load_specs()[0])
    changed_snapshots = [[], [work_item["proposal_artifact_relpath"]]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(
        node: object,
        worktree_path: Path,
        refactor_work_item: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        proposal_path = worktree_path / str(refactor_work_item["proposal_artifact_relpath"])
        proposal_path.parent.mkdir(parents=True, exist_ok=True)
        proposal_path.write_text(
            json.dumps(
                make_valid_split_proposal(
                    node.data,
                    str(refactor_work_item["planned_run_id"]),
                )
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0001",
        split_proposal=True,
    )
    assert exit_code == 0

    assert node_path.read_text(encoding="utf-8") == before_text

    proposal_artifact = repo_fixture / work_item["proposal_artifact_relpath"]
    assert proposal_artifact.exists()
    artifact = json.loads(proposal_artifact.read_text(encoding="utf-8"))
    assert artifact["refactor_kind"] == "split_oversized_spec"
    assert artifact["target_spec_id"] == "SG-SPEC-0001"
    assert artifact["parent_after_split"]["narrowed_role_summary"]
    assert artifact["suggested_children"][0]["suggested_path"] == "specs/nodes/SG-SPEC-0002.yaml"
    assert [entry["acceptance_index"] for entry in artifact["acceptance_mapping"]] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert artifact["acceptance_mapping"][0]["target"] == "parent_retained"
    assert artifact["lineage_updates"]["child_refines_add"][0]["refines"] == ["SG-SPEC-0001"]

    queue_items = json.loads(
        (repo_fixture / "runs" / "proposal_queue.json").read_text(encoding="utf-8")
    )
    assert len(queue_items) == 1
    queue_item = queue_items[0]
    assert queue_item["proposal_type"] == "refactor_proposal"
    assert queue_item["refactor_kind"] == "split_oversized_spec"
    assert queue_item["proposal_artifact_path"] == work_item["proposal_artifact_relpath"]
    assert queue_item["execution_policy"] == "emit_proposal"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["selected_by_rule"]["selection_mode"] == "split_refactor_proposal"
    assert payload["proposal_artifact_path"].endswith(work_item["proposal_artifact_relpath"])
    assert payload["proposed_status"] is None
    assert payload["final_status"] == "outlined"


def test_main_split_proposal_blocks_executor_environment_failures_without_queue_updates(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Calculator Overview"
    node_data["prompt"] = "Keep the parent as overview and split detailed concerns."
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    node = supervisor_module.load_specs()[0]
    work_item = supervisor_module.build_split_refactor_work_item(node)

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/split-proposal"),
    )
    changed_snapshots = [[], []]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(
        _node: object,
        _worktree_path: Path,
        _refactor_work_item: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=1,
            stdout="RUN_OUTCOME: escalate\nBLOCKER: none\n",
            stderr=(
                "ERROR codex_state::runtime: failed to open state db at /tmp/state.sqlite: "
                "migration 21 was previously applied but is missing in the resolved migrations\n"
            ),
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0001",
        split_proposal=True,
    )
    assert exit_code == 1
    assert not (repo_fixture / "runs" / "proposal_queue.json").exists()

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["selected_by_rule"]["selection_mode"] == "split_refactor_proposal"
    assert payload["proposal_artifact_path"].endswith(work_item["proposal_artifact_relpath"])
    assert payload["executor_environment"]["primary_failure"] is True
    assert payload["executor_environment"]["issue_kinds"] == ["state_runtime_failure"]
    assert payload["graph_health"]["signals"] == []
    assert payload["validator_results"]["executor_environment"] is False
    assert all(
        "Missing or invalid structured split proposal artifact" not in error
        for error in payload["validation_errors"]
    )


def test_main_split_proposal_rejects_non_oversized_target(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    exit_code = supervisor_module.main(target_spec="SG-SPEC-0001", split_proposal=True)
    assert exit_code == 1
    assert not (repo_fixture / "runs" / "proposal_queue.json").exists()


def test_main_split_proposal_rejects_seed_like_target(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Root Spec"
    node_data["prompt"] = "This seed spec is a root overview spec with child specs."
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    exit_code = supervisor_module.main(target_spec="SG-SPEC-0001", split_proposal=True)
    assert exit_code == 1
    assert not (repo_fixture / "runs" / "proposal_queue.json").exists()


def test_main_split_proposal_refreshes_existing_artifact_without_duplicate_queue_items(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Calculator Overview"
    node_data["prompt"] = "Keep the parent as overview and split detailed concerns."
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    node = supervisor_module.load_specs()[0]
    work_item = supervisor_module.build_split_refactor_work_item(node)
    existing_queue = [
        {
            "id": "refactor_proposal::SG-SPEC-0001::oversized_spec",
            "proposal_type": "refactor_proposal",
            "spec_id": "SG-SPEC-0001",
            "signal": "oversized_spec",
            "status": "review_pending",
            "execution_policy": "emit_proposal",
            "proposal_artifact_path": work_item["proposal_artifact_relpath"],
            "supporting_run_ids": ["RUN-OLD"],
        }
    ]
    (repo_fixture / "runs" / "proposal_queue.json").write_text(
        json.dumps(existing_queue),
        encoding="utf-8",
    )
    existing_artifact = repo_fixture / work_item["proposal_artifact_relpath"]
    existing_artifact.parent.mkdir(parents=True, exist_ok=True)
    existing_artifact.write_text(
        json.dumps({"id": "old", "status": "review_pending", "note": "stale"}),
        encoding="utf-8",
    )

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/split-proposal"),
    )
    changed_snapshots = [[], [work_item["proposal_artifact_relpath"]]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(
        current_node: object,
        worktree_path: Path,
        refactor_work_item: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        proposal_path = worktree_path / str(refactor_work_item["proposal_artifact_relpath"])
        proposal_path.parent.mkdir(parents=True, exist_ok=True)
        artifact = make_valid_split_proposal(
            current_node.data,
            str(refactor_work_item["planned_run_id"]),
        )
        artifact["parent_after_split"]["narrowed_role_summary"] = "Refreshed overview summary."
        proposal_path.write_text(json.dumps(artifact), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0001",
        split_proposal=True,
    )
    assert exit_code == 0

    queue_items = json.loads(
        (repo_fixture / "runs" / "proposal_queue.json").read_text(encoding="utf-8")
    )
    assert len(queue_items) == 1
    queue_item = queue_items[0]
    assert queue_item["id"] == "refactor_proposal::SG-SPEC-0001::oversized_spec"
    assert queue_item["status"] == "review_pending"
    assert queue_item["proposal_artifact_path"] == work_item["proposal_artifact_relpath"]
    assert "RUN-OLD" in queue_item["supporting_run_ids"]

    refreshed_artifact = json.loads(existing_artifact.read_text(encoding="utf-8"))
    assert refreshed_artifact["parent_after_split"]["narrowed_role_summary"] == (
        "Refreshed overview summary."
    )
    assert "RUN-OLD" in refreshed_artifact["source_run_ids"]


def test_main_apply_split_proposal_materializes_parent_and_children(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Calculator Overview"
    node_data["prompt"] = "Large parent scope."
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    proposal_artifact_path = (
        repo_fixture
        / "runs"
        / "proposals"
        / ("refactor_proposal--sg-spec-0001--oversized_spec.json")
    )
    proposal_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_artifact_path.write_text(
        json.dumps(make_valid_split_proposal(node_data, "RUN-1")),
        encoding="utf-8",
    )
    (repo_fixture / "runs" / "proposal_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "refactor_proposal::SG-SPEC-0001::oversized_spec",
                    "proposal_type": "refactor_proposal",
                    "spec_id": "SG-SPEC-0001",
                    "signal": "oversized_spec",
                    "refactor_kind": "split_oversized_spec",
                    "status": "review_pending",
                    "execution_policy": "emit_proposal",
                    "proposal_artifact_path": (
                        "runs/proposals/refactor_proposal--sg-spec-0001--oversized_spec.json"
                    ),
                }
            ]
        ),
        encoding="utf-8",
    )

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/apply-split"),
    )

    exit_code = supervisor_module.main(
        target_spec="SG-SPEC-0001",
        apply_split_proposal=True,
    )
    assert exit_code == 0

    updated_parent = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )
    assert updated_parent["title"] == "Calculator Overview"
    assert updated_parent["prompt"] == (
        "Keep the parent as calculator overview and integration shell."
    )
    assert updated_parent["acceptance"] == ["criterion-1"]
    assert updated_parent["depends_on"] == ["SG-SPEC-0002", "SG-SPEC-0003"]
    assert len(updated_parent["acceptance_evidence"]) == 1

    child_two = supervisor_module.get_yaml_module().safe_load(
        (repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml").read_text(encoding="utf-8")
    )
    child_three = supervisor_module.get_yaml_module().safe_load(
        (repo_fixture / "specs" / "nodes" / "SG-SPEC-0003.yaml").read_text(encoding="utf-8")
    )
    assert child_two["relates_to"] == []
    assert child_three["relates_to"] == []
    assert child_two["refines"] == ["SG-SPEC-0001"]
    assert child_three["refines"] == ["SG-SPEC-0001"]
    assert child_two["acceptance"] == ["criterion-2", "criterion-3"]
    assert child_three["acceptance"] == ["criterion-4", "criterion-5", "criterion-6"]

    updated_artifact = json.loads(proposal_artifact_path.read_text(encoding="utf-8"))
    assert updated_artifact["status"] == "applied"
    updated_queue = json.loads(
        (repo_fixture / "runs" / "proposal_queue.json").read_text(encoding="utf-8")
    )
    assert updated_queue[0]["status"] == "applied"

    refactor_queue = json.loads(
        (repo_fixture / "runs" / "refactor_queue.json").read_text(encoding="utf-8")
    )
    assert refactor_queue == []


def test_main_apply_split_proposal_rejects_when_no_proposal_exists(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    exit_code = supervisor_module.main(
        target_spec="SG-SPEC-0001",
        apply_split_proposal=True,
    )
    assert exit_code == 1


def test_main_apply_split_proposal_rejects_existing_child_collision(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Calculator Overview"
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    collision_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    collision_path.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Existing Child",
                "kind": "spec",
                "status": "outlined",
                "maturity": 0.2,
                "depends_on": [],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["existing"],
                "prompt": "Existing child.",
            }
        ),
        encoding="utf-8",
    )

    proposal_artifact_path = (
        repo_fixture
        / "runs"
        / "proposals"
        / ("refactor_proposal--sg-spec-0001--oversized_spec.json")
    )
    proposal_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_artifact_path.write_text(
        json.dumps(make_valid_split_proposal(node_data, "RUN-1")),
        encoding="utf-8",
    )
    (repo_fixture / "runs" / "proposal_queue.json").write_text(
        json.dumps(
            [
                {
                    "id": "refactor_proposal::SG-SPEC-0001::oversized_spec",
                    "proposal_type": "refactor_proposal",
                    "spec_id": "SG-SPEC-0001",
                    "signal": "oversized_spec",
                    "refactor_kind": "split_oversized_spec",
                    "status": "review_pending",
                    "execution_policy": "emit_proposal",
                    "proposal_artifact_path": (
                        "runs/proposals/refactor_proposal--sg-spec-0001--oversized_spec.json"
                    ),
                }
            ]
        ),
        encoding="utf-8",
    )

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/apply-split"),
    )

    exit_code = supervisor_module.main(
        target_spec="SG-SPEC-0001",
        apply_split_proposal=True,
    )
    assert exit_code == 1

    updated_queue = json.loads(
        (repo_fixture / "runs" / "proposal_queue.json").read_text(encoding="utf-8")
    )
    assert updated_queue[0]["status"] == "review_pending"


def test_validate_changed_spec_nodes_rejects_relates_to_overlap_with_refines(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["relates_to"] = ["SG-SPEC-9999"]
    node_data["refines"] = ["SG-SPEC-9999"]
    node_data["acceptance_evidence"] = ["evidence"]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree_specs = supervisor_module.load_specs_from_dir(repo_fixture / "specs" / "nodes")
    errors = supervisor_module.validate_changed_spec_nodes(
        source_node_id="SG-SPEC-0001",
        changed_files=["specs/nodes/SG-SPEC-0001.yaml"],
        worktree_specs=worktree_specs,
        worktree_path=repo_fixture,
    )

    assert any(
        "relates_to MUST NOT include SG-SPEC-9999 when refines already targets the same spec"
        in error
        for error in errors
    )


def test_main_seeds_worktree_with_current_uncommitted_node(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    current_data = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )
    current_data["prompt"] = "Current working tree prompt"
    current_data["allowed_paths"] = ["specs/nodes/*.yaml"]
    node_path.write_text(json.dumps(current_data), encoding="utf-8")

    stale_worktree = repo_fixture / ".stale-worktree"
    stale_specs_dir = stale_worktree / "specs" / "nodes"
    stale_specs_dir.mkdir(parents=True, exist_ok=True)
    stale_data = dict(current_data)
    stale_data["prompt"] = "Stale prompt from HEAD"
    stale_data["allowed_paths"] = ["specs/nodes/SG-SPEC-0001.yaml"]
    (stale_specs_dir / "SG-SPEC-0001.yaml").write_text(json.dumps(stale_data), encoding="utf-8")

    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (stale_worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(
            worktree_node.read_text(encoding="utf-8")
        )
        assert data["prompt"] == "Current working tree prompt"
        assert data["allowed_paths"] == ["specs/nodes/*.yaml"]
        data["acceptance_evidence"] = ["evidence"]
        worktree_node.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 0


def test_main_auto_approve_applies_status_and_copies_changes(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        node_path = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
        data["acceptance_evidence"] = ["evidence"]
        data["prompt"] = "Auto-approved prompt"
        node_path.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor, auto_approve=True)
    assert exit_code == 0

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "specified"
    assert updated["gate_state"] == "none"
    assert updated["proposed_status"] is None
    assert updated["maturity"] == 0.4
    assert updated["prompt"] == "Auto-approved prompt"


def test_main_auto_approve_syncs_new_child_spec_from_parent_run(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["allowed_paths"] = ["specs/nodes/*.yaml"]
    node_data["prompt"] = (
        "This spec is a seed ontology. Use child specs to refine unresolved areas."
    )
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml", "specs/nodes/SG-SPEC-0002.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        root_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        root_data = supervisor_module.get_yaml_module().safe_load(
            root_node.read_text(encoding="utf-8")
        )
        root_data["acceptance_evidence"] = ["evidence"]
        root_data["depends_on"] = ["SG-SPEC-0002"]
        root_node.write_text(json.dumps(root_data), encoding="utf-8")

        child_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0002.yaml"
        child_node.write_text(
            json.dumps(
                {
                    "id": "SG-SPEC-0002",
                    "title": "Canonical Substrate and Versioning",
                    "kind": "spec",
                    "status": "outlined",
                    "maturity": 0.2,
                    "depends_on": [],
                    "relates_to": ["SG-SPEC-0001"],
                    "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                    "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                    "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                    "acceptance": [
                        "Defines canonical substrate choices and revision/export invariants"
                    ],
                    "prompt": "Refine the canonical substrate and versioning slice.",
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor, auto_approve=True)
    assert exit_code == 0

    updated_root = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )
    assert updated_root["status"] == "specified"
    assert updated_root["depends_on"] == ["SG-SPEC-0002"]

    child_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    assert child_path.exists()
    child_data = supervisor_module.get_yaml_module().safe_load(
        child_path.read_text(encoding="utf-8")
    )
    assert child_data["id"] == "SG-SPEC-0002"
    assert child_data["title"] == "Canonical Substrate and Versioning"


def test_main_auto_approve_reconciles_seed_to_linked_when_child_exists(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["status"] = "specified"
    node_data["maturity"] = 0.6
    node_data["allowed_paths"] = ["specs/nodes/*.yaml"]
    node_data["prompt"] = (
        "This spec is a seed ontology. Use child specs to refine unresolved areas."
    )
    node_data["acceptance_evidence"] = ["evidence"] * len(node_data["acceptance"])
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml", "specs/nodes/SG-SPEC-0002.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        root_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        root_data = supervisor_module.get_yaml_module().safe_load(
            root_node.read_text(encoding="utf-8")
        )
        root_data["depends_on"] = ["SG-SPEC-0002"]
        root_data["acceptance_evidence"][-1] = "SG-SPEC-0002 now refines the seed linkage policy."
        root_node.write_text(json.dumps(root_data), encoding="utf-8")

        child_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0002.yaml"
        child_node.write_text(
            json.dumps(
                {
                    "id": "SG-SPEC-0002",
                    "title": "Spec Refinement and Linkage Policy",
                    "kind": "spec",
                    "status": "specified",
                    "maturity": 0.55,
                    "depends_on": [],
                    "relates_to": [],
                    "refines": ["SG-SPEC-0001"],
                    "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                    "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                    "allowed_paths": ["specs/nodes/*.yaml"],
                    "acceptance": [
                        ("Defines how a child spec refines a seed spec and unblocks linked status")
                    ],
                    "acceptance_evidence": [
                        {
                            "criterion": (
                                "Defines how a child spec refines a seed spec "
                                "and unblocks linked status"
                            ),
                            "evidence": (
                                "specification.linkage_rules describes "
                                "the parent-child edge contract"
                            ),
                        }
                    ],
                    "prompt": "Refine the seed-to-child linkage rules.",
                    "specification": {
                        "linkage_rules": {
                            "specified_to_linked": [
                                (
                                    "A seed spec may reach linked once each "
                                    "declared child exists and explicitly "
                                    "refines the parent."
                                )
                            ]
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor, auto_approve=True)
    assert exit_code == 0

    updated_root = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )
    assert updated_root["status"] == "linked"
    assert updated_root["depends_on"] == ["SG-SPEC-0002"]
    assert updated_root["last_reconciliation"]["semantic_dependencies_resolved"] is True
    assert updated_root["last_reconciliation"]["work_dependencies_ready"] is False

    child_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    child_data = supervisor_module.get_yaml_module().safe_load(
        child_path.read_text(encoding="utf-8")
    )
    assert child_data["refines"] == ["SG-SPEC-0001"]


def test_main_auto_approve_syncs_when_allowed_paths_empty(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["allowed_paths"] = []
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )
    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(
            worktree_node.read_text(encoding="utf-8")
        )
        data["acceptance_evidence"] = ["evidence"]
        data["prompt"] = "Synced with unrestricted allowed_paths"
        worktree_node.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor, auto_approve=True)
    assert exit_code == 0

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["prompt"] == "Synced with unrestricted allowed_paths"


def test_main_outcome_blocked_sets_gate(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        node_path = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
        data["acceptance_evidence"] = ["evidence"]
        node_path.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=1,
            stdout="RUN_OUTCOME: blocked\nBLOCKER: missing upstream spec\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["gate_state"] == "blocked"
    assert updated["required_human_action"] == "resolve blocker"
    assert updated["last_blocker"] == "missing upstream spec"


def test_acceptance_evidence_is_required(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, _worktree_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert any("acceptance_evidence" in err for err in updated["last_errors"])


def test_source_spec_is_validated_even_when_no_files_change(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], []]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, _worktree_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["gate_state"] == "retry_pending"
    assert any("acceptance_evidence" in err for err in updated["last_errors"])


def test_main_atomicity_gate_forces_split_required(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Working Node"
    node_data["prompt"] = "Refine one bounded slice of this node."
    node_data["allowed_paths"] = ["specs/nodes/SG-SPEC-0001.yaml"]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(
            worktree_node.read_text(encoding="utf-8")
        )
        data["acceptance"] = [f"criterion-{i}" for i in range(6)]
        data["acceptance_evidence"] = [f"evidence-{i}" for i in range(6)]
        worktree_node.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["gate_state"] == "split_required"
    assert updated["required_human_action"] == "split spec scope before rerun"
    assert updated["last_blocker"] == "spec exceeds atomicity quality gate"
    assert updated["last_validator_results"]["atomicity"] is False
    assert any("Atomicity gate exceeded" in err for err in updated["last_errors"])


def test_main_split_required_syncs_decomposition_outputs(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Working Node"
    node_data["prompt"] = "Split this node into several atomic children."
    node_data["allowed_paths"] = ["specs/nodes/*.yaml"]
    node_data["acceptance_evidence"] = ["seed evidence"]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [
        [],
        [
            "specs/nodes/SG-SPEC-0001.yaml",
            "specs/nodes/SG-SPEC-0002.yaml",
            "specs/nodes/SG-SPEC-0003.yaml",
        ],
    ]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        root_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        root_data = supervisor_module.get_yaml_module().safe_load(
            root_node.read_text(encoding="utf-8")
        )
        root_data["depends_on"] = ["SG-SPEC-0002", "SG-SPEC-0003"]
        root_data["acceptance_evidence"] = ["Split into atomic children."]
        root_node.write_text(json.dumps(root_data), encoding="utf-8")

        for child_id, title in (
            ("SG-SPEC-0002", "Arithmetic Functions"),
            ("SG-SPEC-0003", "Input Constraints"),
        ):
            (worktree_path / "specs" / "nodes" / f"{child_id}.yaml").write_text(
                json.dumps(
                    {
                        "id": child_id,
                        "title": title,
                        "kind": "spec",
                        "status": "outlined",
                        "maturity": 0.2,
                        "depends_on": [],
                        "relates_to": [],
                        "refines": ["SG-SPEC-0001"],
                        "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                        "outputs": [f"specs/nodes/{child_id}.yaml"],
                        "allowed_paths": [f"specs/nodes/{child_id}.yaml"],
                        "acceptance": [f"{title} is specified"],
                        "prompt": f"Refine {title}.",
                    }
                ),
                encoding="utf-8",
            )

        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout=(
                "RUN_OUTCOME: split_required\nBLOCKER: parent still needs another narrowing pass\n"
            ),
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    updated_root = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )
    assert updated_root["gate_state"] == "split_required"
    assert updated_root["depends_on"] == ["SG-SPEC-0002", "SG-SPEC-0003"]

    child_two = supervisor_module.get_yaml_module().safe_load(
        (repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml").read_text(encoding="utf-8")
    )
    child_three = supervisor_module.get_yaml_module().safe_load(
        (repo_fixture / "specs" / "nodes" / "SG-SPEC-0003.yaml").read_text(encoding="utf-8")
    )
    assert child_two["refines"] == ["SG-SPEC-0001"]
    assert child_three["refines"] == ["SG-SPEC-0001"]


def test_resolve_gate_approve_applies_worktree_changes(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    worktree_node_path = worktree / "specs" / "nodes" / "SG-SPEC-0001.yaml"

    worktree_data = supervisor_module.get_yaml_module().safe_load(
        worktree_node_path.read_text(encoding="utf-8")
    )
    worktree_data["prompt"] = "Approved from worktree"
    worktree_node_path.write_text(json.dumps(worktree_data), encoding="utf-8")

    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["gate_state"] = "review_pending"
    data["proposed_status"] = "specified"
    data["proposed_maturity"] = 0.4
    data["last_worktree_path"] = worktree.as_posix()
    data["last_changed_files"] = ["specs/nodes/SG-SPEC-0001.yaml"]
    node_path.write_text(json.dumps(data), encoding="utf-8")

    exit_code = supervisor_module.main(
        resolve_gate="SG-SPEC-0001",
        decision="approve",
        note="looks good",
    )
    assert exit_code == 0

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "specified"
    assert updated["maturity"] == 0.4
    assert updated["gate_state"] == "none"
    assert updated["prompt"] == "Approved from worktree"
    assert updated["last_gate_decision"] == "approve"


def test_resolve_gate_approve_syncs_when_allowed_paths_empty(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["allowed_paths"] = []
    node_data["gate_state"] = "review_pending"
    node_data["proposed_status"] = "specified"
    node_data["proposed_maturity"] = 0.4
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    worktree_node = worktree / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    worktree_data = supervisor_module.get_yaml_module().safe_load(
        worktree_node.read_text(encoding="utf-8")
    )
    worktree_data["prompt"] = "Gate approved unrestricted sync"
    worktree_node.write_text(json.dumps(worktree_data), encoding="utf-8")

    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["last_worktree_path"] = worktree.as_posix()
    node_data["last_changed_files"] = ["specs/nodes/SG-SPEC-0001.yaml"]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    exit_code = supervisor_module.main(
        resolve_gate="SG-SPEC-0001",
        decision="approve",
    )
    assert exit_code == 0

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["prompt"] == "Gate approved unrestricted sync"


def test_resolve_gate_retry_sets_retry_pending(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["gate_state"] = "review_pending"
    data["proposed_status"] = "specified"
    node_path.write_text(json.dumps(data), encoding="utf-8")

    exit_code = supervisor_module.main(resolve_gate="SG-SPEC-0001", decision="retry")
    assert exit_code == 0

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["gate_state"] == "retry_pending"
    assert updated["proposed_status"] is None


def test_main_fails_when_changed_file_outside_allowed_paths(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["README.md"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, _worktree_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert any("outside allowed_paths" in err for err in updated["last_errors"])


def test_main_records_yaml_validation_error(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        node_path = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        node_path.write_text("id: [broken yaml\n", encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert any("Invalid YAML" in err or "Failed to reload" in err for err in updated["last_errors"])


def test_main_aborts_on_cycle(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    specs_dir = repo_fixture / "specs" / "nodes"

    node_a = specs_dir / "SG-SPEC-A.yaml"
    node_b = specs_dir / "SG-SPEC-B.yaml"
    node_a.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-A",
                "title": "A",
                "status": "outlined",
                "maturity": 0.0,
                "depends_on": ["SG-SPEC-B"],
                "acceptance": ["x"],
            }
        ),
        encoding="utf-8",
    )
    node_b.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-B",
                "title": "B",
                "status": "outlined",
                "maturity": 0.0,
                "depends_on": ["SG-SPEC-A"],
                "acceptance": ["x"],
            }
        ),
        encoding="utf-8",
    )

    exit_code = supervisor_module.main()
    assert exit_code == 1


def test_status_progression_map_covers_lifecycle(supervisor_module: object) -> None:
    progression = supervisor_module.STATUS_PROGRESSION
    assert progression["idea"] == "stub"
    assert progression["stub"] == "outlined"
    assert progression["outlined"] == "specified"
    assert progression["specified"] == "linked"
    assert progression["linked"] == "reviewed"
    assert progression["reviewed"] == "frozen"
    assert "frozen" not in progression


# --- loop mode tests ---


def test_loop_requires_auto_approve(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    exit_code = supervisor_module.main(loop=True, auto_approve=False)
    assert exit_code == 1


def test_loop_rejects_dry_run(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    exit_code = supervisor_module.main(loop=True, auto_approve=True, dry_run=True)
    assert exit_code == 1


def _make_successful_executor(supervisor_module: object) -> object:
    """Return a fake executor that writes valid acceptance_evidence."""

    def fake_executor(
        _node: object,
        worktree_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        for node_file in (worktree_path / "specs" / "nodes").glob("*.yaml"):
            data = supervisor_module.get_yaml_module().safe_load(
                node_file.read_text(encoding="utf-8")
            )
            acceptance = data.get("acceptance", [])
            data["acceptance_evidence"] = [f"evidence-{i}" for i in range(len(acceptance))]
            node_file.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    return fake_executor


def test_loop_processes_until_no_candidates(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loop should promote outlined->specified->linked, then stop (linked not workable)."""
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (make_fake_worktree(repo_fixture), "codex/test/loop"),
    )
    # Use alternating before/after pattern so changed files are detected correctly.
    call_counter: list[int] = [0]

    def alternating_git_changed(_cwd: object = None) -> list[str]:
        call_counter[0] += 1
        # Odd calls are "after executor" — report changed file.
        if call_counter[0] % 2 == 0:
            return ["specs/nodes/SG-SPEC-0001.yaml"]
        return []

    monkeypatch.setattr(supervisor_module, "git_changed_files", alternating_git_changed)

    fake_executor = _make_successful_executor(supervisor_module)
    exit_code = supervisor_module.main(
        executor=fake_executor,
        auto_approve=True,
        loop=True,
    )
    assert exit_code == 0

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "linked"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    # At least 1 log; may be fewer than 2 due to same-second timestamp collision.
    assert len(run_logs) >= 1


def test_loop_propagates_semantic_unlock_upstream(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs_dir = repo_fixture / "specs" / "nodes"

    root_path = specs_dir / "SG-SPEC-0001.yaml"
    root_data = supervisor_module.get_yaml_module().safe_load(root_path.read_text(encoding="utf-8"))
    root_data["status"] = "specified"
    root_data["maturity"] = 0.6
    root_data["depends_on"] = ["SG-SPEC-0002"]
    root_data["acceptance_evidence"] = ["evidence"]
    root_data["allowed_paths"] = ["specs/nodes/*.yaml"]
    root_path.write_text(json.dumps(root_data), encoding="utf-8")

    specs_dir.joinpath("SG-SPEC-0002.yaml").write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Intermediate Node",
                "kind": "spec",
                "status": "specified",
                "maturity": 0.5,
                "depends_on": ["SG-SPEC-0003"],
                "refines": ["SG-SPEC-0001"],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/*.yaml"],
                "acceptance": ["criterion"],
                "acceptance_evidence": ["evidence"],
                "prompt": "Reconcile one bounded ancestor step.",
            }
        ),
        encoding="utf-8",
    )
    specs_dir.joinpath("SG-SPEC-0003.yaml").write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0003",
                "title": "Leaf Node",
                "kind": "spec",
                "status": "outlined",
                "maturity": 0.2,
                "depends_on": [],
                "refines": ["SG-SPEC-0002"],
                "outputs": ["specs/nodes/SG-SPEC-0003.yaml"],
                "allowed_paths": ["specs/nodes/*.yaml"],
                "acceptance": ["criterion"],
                "prompt": "Leaf already exists and semantically unlocks its ancestors.",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (make_fake_worktree(repo_fixture), "codex/test/loop"),
    )

    monkeypatch.setattr(supervisor_module, "git_changed_files", lambda _cwd=None: [])

    exit_code = supervisor_module.main(
        executor=_make_successful_executor(supervisor_module),
        auto_approve=True,
        loop=True,
        max_iterations=5,
    )
    assert exit_code == 0

    root_updated = supervisor_module.get_yaml_module().safe_load(
        root_path.read_text(encoding="utf-8")
    )
    middle_updated = supervisor_module.get_yaml_module().safe_load(
        (specs_dir / "SG-SPEC-0002.yaml").read_text(encoding="utf-8")
    )

    assert middle_updated["status"] == "linked"
    assert root_updated["status"] == "linked"


def test_loop_processes_multiple_specs(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loop should process multiple independent specs."""
    specs_dir = repo_fixture / "specs" / "nodes"

    # Widen allowed_paths on spec-0001 so cross-file changes don't fail validation.
    node1_path = specs_dir / "SG-SPEC-0001.yaml"
    node1_data = supervisor_module.get_yaml_module().safe_load(
        node1_path.read_text(encoding="utf-8")
    )
    node1_data["allowed_paths"] = ["specs/nodes/*.yaml"]
    node1_path.write_text(json.dumps(node1_data), encoding="utf-8")

    specs_dir.joinpath("SG-SPEC-0002.yaml").write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Second Node",
                "kind": "spec",
                "status": "outlined",
                "maturity": 0.2,
                "depends_on": [],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/*.yaml"],
                "acceptance": ["criterion"],
                "prompt": "Refine second node.",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (make_fake_worktree(repo_fixture), "codex/test/loop"),
    )

    call_counter: list[int] = [0]

    def alternating_git_changed(_cwd: object = None) -> list[str]:
        call_counter[0] += 1
        # Even calls (after executor) report the changed file.
        if call_counter[0] % 2 == 0:
            return ["specs/nodes/SG-SPEC-0001.yaml", "specs/nodes/SG-SPEC-0002.yaml"]
        return []

    monkeypatch.setattr(supervisor_module, "git_changed_files", alternating_git_changed)

    def per_node_executor(
        node: object,
        worktree_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        node_file = worktree_path / "specs" / "nodes" / f"{node.id}.yaml"
        if node_file.exists():
            data = supervisor_module.get_yaml_module().safe_load(
                node_file.read_text(encoding="utf-8")
            )
            acceptance = data.get("acceptance", [])
            data["acceptance_evidence"] = [f"ev-{i}" for i in range(len(acceptance))]
            node_file.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(
        executor=per_node_executor,
        auto_approve=True,
        loop=True,
    )
    assert exit_code == 0

    node1 = supervisor_module.get_yaml_module().safe_load(
        (specs_dir / "SG-SPEC-0001.yaml").read_text(encoding="utf-8")
    )
    node2 = supervisor_module.get_yaml_module().safe_load(
        (specs_dir / "SG-SPEC-0002.yaml").read_text(encoding="utf-8")
    )
    # Both should have advanced beyond their initial "outlined" status.
    assert node1["status"] != "outlined"
    assert node2["status"] != "outlined"


def test_loop_continues_past_failures(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A blocked spec should not stop the loop from processing other specs."""
    specs_dir = repo_fixture / "specs" / "nodes"

    node1_path = specs_dir / "SG-SPEC-0001.yaml"
    node1_data = supervisor_module.get_yaml_module().safe_load(
        node1_path.read_text(encoding="utf-8")
    )
    node1_data["allowed_paths"] = ["specs/nodes/*.yaml"]
    node1_path.write_text(json.dumps(node1_data), encoding="utf-8")

    specs_dir.joinpath("SG-SPEC-0002.yaml").write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Blocked Node",
                "kind": "spec",
                "status": "outlined",
                "maturity": 0.1,
                "depends_on": [],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/*.yaml"],
                "acceptance": ["criterion"],
                "prompt": "This will block.",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (make_fake_worktree(repo_fixture), "codex/test/loop"),
    )

    call_counter: list[int] = [0]

    def alternating_git_changed(_cwd: object = None) -> list[str]:
        call_counter[0] += 1
        if call_counter[0] % 2 == 0:
            return ["specs/nodes/SG-SPEC-0001.yaml", "specs/nodes/SG-SPEC-0002.yaml"]
        return []

    monkeypatch.setattr(supervisor_module, "git_changed_files", alternating_git_changed)

    def mixed_executor(
        node: object,
        worktree_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        # Only write to the current node's file to avoid cross-spec allowed_paths issues.
        node_file = worktree_path / "specs" / "nodes" / f"{node.id}.yaml"
        if node_file.exists():
            data = supervisor_module.get_yaml_module().safe_load(
                node_file.read_text(encoding="utf-8")
            )
            acceptance = data.get("acceptance", [])
            data["acceptance_evidence"] = [f"ev-{i}" for i in range(len(acceptance))]
            node_file.write_text(json.dumps(data), encoding="utf-8")

        if node.id == "SG-SPEC-0002":
            return subprocess.CompletedProcess(
                args=["codex"],
                returncode=1,
                stdout="RUN_OUTCOME: blocked\nBLOCKER: missing dep\n",
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(
        executor=mixed_executor,
        auto_approve=True,
        loop=True,
    )
    assert exit_code == 0

    node1 = supervisor_module.get_yaml_module().safe_load(
        (specs_dir / "SG-SPEC-0001.yaml").read_text(encoding="utf-8")
    )
    node2 = supervisor_module.get_yaml_module().safe_load(
        (specs_dir / "SG-SPEC-0002.yaml").read_text(encoding="utf-8")
    )
    assert node2["gate_state"] == "blocked"
    assert node1["status"] != "outlined"


def test_loop_respects_max_iterations(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (make_fake_worktree(repo_fixture), "codex/test/loop"),
    )
    monkeypatch.setattr(
        supervisor_module,
        "git_changed_files",
        lambda _cwd=None: ["specs/nodes/SG-SPEC-0001.yaml"],
    )

    fake_executor = _make_successful_executor(supervisor_module)
    exit_code = supervisor_module.main(
        executor=fake_executor,
        auto_approve=True,
        loop=True,
        max_iterations=1,
    )
    assert exit_code == 0

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
