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
