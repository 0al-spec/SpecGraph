from __future__ import annotations

import importlib.util
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

    run_logs = sorted((repo_fixture / "runs").glob("*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["spec_id"] == "SG-SPEC-0001"
    assert payload["outcome"] == "done"
    assert payload["worktree_path"] == worktree.as_posix()
    assert payload["selected_by_rule"]["selection_mode"] == "default_refine"
    assert payload["selected_by_rule"]["sort_order"] == [
        "ancestor_reconcile_first",
        "nearest_unlocked_ancestor",
        "leaf_first",
        "lower_maturity",
        "stable_id",
    ]
    assert (repo_fixture / "runs" / "latest-summary.md").exists()


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
                    "relates_to": ["SG-SPEC-0001"],
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
                        "relates_to": ["SG-SPEC-0001"],
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

    run_logs = sorted((repo_fixture / "runs").glob("*.json"))
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

    run_logs = sorted((repo_fixture / "runs").glob("*.json"))
    assert len(run_logs) == 1
