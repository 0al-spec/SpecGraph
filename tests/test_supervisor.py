from __future__ import annotations

import importlib.util
import json
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
    monkeypatch.setattr(supervisor_module, "AGENTS_FILE", root / "AGENTS.md")
    return root


def test_pick_next_spec_gap_orders_by_maturity_then_id(supervisor_module: object) -> None:
    spec_node = supervisor_module.SpecNode
    nodes = [
        spec_node(
            path=Path("/tmp/2.yaml"),
            data={"id": "B", "status": "outlined", "maturity": 0.3, "depends_on": []},
        ),
        spec_node(
            path=Path("/tmp/1.yaml"),
            data={"id": "A", "status": "outlined", "maturity": 0.3, "depends_on": []},
        ),
        spec_node(
            path=Path("/tmp/3.yaml"),
            data={
                "id": "C",
                "status": "specified",
                "maturity": 0.1,
                "depends_on": [],
            },
        ),
        spec_node(
            path=Path("/tmp/4.yaml"),
            data={"id": "D", "status": "idea", "maturity": 0.0, "depends_on": []},
        ),
    ]

    selected = supervisor_module.pick_next_spec_gap(nodes)
    assert selected is not None
    assert selected.id == "C"


def test_main_golden_path_updates_node_and_writes_run_log(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda: ["specs/nodes/SG-SPEC-0001.yaml"]
    )
    monkeypatch.setattr(
        supervisor_module,
        "run_codex",
        lambda _node: subprocess.CompletedProcess(
            args=["codex"], returncode=0, stdout="ok", stderr=""
        ),
    )

    exit_code = supervisor_module.main()
    assert exit_code == 0

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "specified"
    assert updated["maturity"] == 0.4
    assert updated["last_exit_code"] == 0

    run_logs = sorted((repo_fixture / "runs").glob("*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["spec_id"] == "SG-SPEC-0001"
    assert payload["validation_errors"] == []


def test_main_fails_when_changed_file_outside_allowed_paths(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed_snapshots = [[], ["README.md"]]

    def fake_git_changed_files() -> list[str]:
        return changed_snapshots.pop(0)

    monkeypatch.setattr(supervisor_module, "git_changed_files", fake_git_changed_files)

    def fake_run_codex(_node: object) -> subprocess.CompletedProcess[str]:
        (repo_fixture / "README.md").write_text("created by codex\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(
        supervisor_module,
        "run_codex",
        fake_run_codex,
    )

    exit_code = supervisor_module.main()
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert "last_errors" in updated
    assert any("outside allowed_paths" in err for err in updated["last_errors"])


def test_main_detects_out_of_scope_change_when_file_already_dirty(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readme_path = repo_fixture / "README.md"
    readme_path.write_text("dirty before run\n", encoding="utf-8")
    changed_snapshots = [["README.md"], ["README.md"]]

    def fake_git_changed_files() -> list[str]:
        return changed_snapshots.pop(0)

    monkeypatch.setattr(supervisor_module, "git_changed_files", fake_git_changed_files)

    def fake_run_codex(_node: object) -> subprocess.CompletedProcess[str]:
        readme_path.write_text("dirty after run\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(
        supervisor_module,
        "run_codex",
        fake_run_codex,
    )

    exit_code = supervisor_module.main()
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert "last_errors" in updated
    assert any("outside allowed_paths" in err for err in updated["last_errors"])
    assert updated["last_changed_files"] == ["README.md"]


def test_main_detects_out_of_scope_deleted_file_when_initially_clean(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readme_path = repo_fixture / "README.md"
    readme_path.write_text("tracked content\n", encoding="utf-8")
    changed_snapshots = [[], ["README.md"]]

    def fake_git_changed_files() -> list[str]:
        return changed_snapshots.pop(0)

    monkeypatch.setattr(supervisor_module, "git_changed_files", fake_git_changed_files)

    def fake_run_codex(_node: object) -> subprocess.CompletedProcess[str]:
        readme_path.unlink()
        return subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(supervisor_module, "run_codex", fake_run_codex)

    exit_code = supervisor_module.main()
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert "last_errors" in updated
    assert any("outside allowed_paths" in err for err in updated["last_errors"])
    assert updated["last_changed_files"] == ["README.md"]


def test_main_reloads_node_after_codex_run_before_saving_metadata(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda: ["specs/nodes/SG-SPEC-0001.yaml"]
    )

    def fake_run_codex(_node: object) -> subprocess.CompletedProcess[str]:
        node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
        data["prompt"] = "Updated by Codex"
        node_path.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(supervisor_module, "run_codex", fake_run_codex)

    exit_code = supervisor_module.main()
    assert exit_code == 0

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["prompt"] == "Updated by Codex"


def test_glob_allowed_paths_matches_wildcard(supervisor_module: object) -> None:
    """fnmatch glob patterns should match files."""
    node = supervisor_module.SpecNode(
        path=Path("/tmp/x.yaml"),
        data={"allowed_paths": ["specs/nodes/*.yaml"]},
    )
    errors = supervisor_module.validate_allowed_paths(
        node, ["specs/nodes/SG-SPEC-0001.yaml", "specs/nodes/SG-SPEC-0002.yaml"]
    )
    assert errors == []


def test_glob_allowed_paths_rejects_outside(supervisor_module: object) -> None:
    """Files not matching any glob should be rejected."""
    node = supervisor_module.SpecNode(
        path=Path("/tmp/x.yaml"),
        data={"allowed_paths": ["specs/nodes/*.yaml"]},
    )
    errors = supervisor_module.validate_allowed_paths(node, ["README.md"])
    assert len(errors) == 1
    assert "README.md" in errors[0]


def test_detect_cycles_finds_simple_cycle(supervisor_module: object) -> None:
    spec_node = supervisor_module.SpecNode
    nodes = [
        spec_node(path=Path("/tmp/a.yaml"), data={"id": "A", "depends_on": ["B"]}),
        spec_node(path=Path("/tmp/b.yaml"), data={"id": "B", "depends_on": ["A"]}),
    ]
    cycles = supervisor_module.detect_cycles(nodes)
    assert len(cycles) >= 1
    flat = [item for cycle in cycles for item in cycle]
    assert "A" in flat and "B" in flat


def test_detect_cycles_returns_empty_for_dag(supervisor_module: object) -> None:
    spec_node = supervisor_module.SpecNode
    nodes = [
        spec_node(path=Path("/tmp/a.yaml"), data={"id": "A", "depends_on": []}),
        spec_node(path=Path("/tmp/b.yaml"), data={"id": "B", "depends_on": ["A"]}),
    ]
    cycles = supervisor_module.detect_cycles(nodes)
    assert cycles == []


def test_detect_cycles_three_node_cycle(supervisor_module: object) -> None:
    spec_node = supervisor_module.SpecNode
    nodes = [
        spec_node(path=Path("/tmp/a.yaml"), data={"id": "A", "depends_on": ["C"]}),
        spec_node(path=Path("/tmp/b.yaml"), data={"id": "B", "depends_on": ["A"]}),
        spec_node(path=Path("/tmp/c.yaml"), data={"id": "C", "depends_on": ["B"]}),
    ]
    cycles = supervisor_module.detect_cycles(nodes)
    assert len(cycles) >= 1


def test_main_with_injectable_executor(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Injectable executor should be used instead of run_codex."""
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda: ["specs/nodes/SG-SPEC-0001.yaml"]
    )

    calls: list[str] = []

    def custom_executor(node: object) -> subprocess.CompletedProcess[str]:
        calls.append(node.id)
        return subprocess.CompletedProcess(args=["custom"], returncode=0, stdout="ok", stderr="")

    exit_code = supervisor_module.main(executor=custom_executor)
    assert exit_code == 0
    assert calls == ["SG-SPEC-0001"]


def test_main_dry_run_does_not_execute(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dry-run mode should not call the executor."""
    called = []

    def should_not_be_called(node: object) -> subprocess.CompletedProcess[str]:
        called.append(True)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    exit_code = supervisor_module.main(executor=should_not_be_called, dry_run=True)
    assert exit_code == 0
    assert called == []


def test_full_status_progression_specified_to_linked(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A specified node should progress to linked on success."""
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["status"] = "specified"
    node_path.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda: ["specs/nodes/SG-SPEC-0001.yaml"]
    )

    def fake_executor(_node: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 0

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "linked"


def test_status_progression_map_covers_lifecycle(supervisor_module: object) -> None:
    """STATUS_PROGRESSION should cover all transitions except frozen."""
    progression = supervisor_module.STATUS_PROGRESSION
    assert progression["idea"] == "stub"
    assert progression["stub"] == "outlined"
    assert progression["outlined"] == "specified"
    assert progression["specified"] == "linked"
    assert progression["linked"] == "reviewed"
    assert progression["reviewed"] == "frozen"
    assert "frozen" not in progression


def test_main_aborts_on_cycle(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """main() should return 1 when dependency cycles exist."""
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


def test_main_records_reload_failure_as_validation_error(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda: ["specs/nodes/SG-SPEC-0001.yaml"]
    )

    def fake_run_codex(_node: object) -> subprocess.CompletedProcess[str]:
        node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        node_path.write_text("id: [broken yaml\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(supervisor_module, "run_codex", fake_run_codex)

    exit_code = supervisor_module.main()
    assert exit_code == 1

    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert "last_errors" in updated
    assert any("Failed to reload node file" in err for err in updated["last_errors"])
