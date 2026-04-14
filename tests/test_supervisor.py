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


def test_build_codex_exec_command_uses_named_execution_profile(
    supervisor_module: object,
) -> None:
    profile = supervisor_module.resolve_execution_profile(
        requested_profile="fast",
        run_authority=(),
        operator_target=False,
    )
    cmd = supervisor_module.build_codex_exec_command(
        prompt="Refine one bounded spec.",
        profile=profile,
    )

    assert "--model" in cmd
    assert profile.model in cmd
    assert f'model_reasoning_effort="{profile.reasoning_effort}"' in cmd
    assert "--sandbox" in cmd
    assert profile.sandbox in cmd


def test_build_codex_exec_command_bypasses_inner_sandbox_for_sandbox_branch(
    supervisor_module: object,
) -> None:
    cmd = supervisor_module.build_codex_exec_command(
        prompt="Refine one bounded spec.",
        bypass_inner_sandbox=True,
    )

    assert cmd[:2] == ["codex", "exec"]
    assert "--dangerously-bypass-approvals-and-sandbox" in cmd
    assert "--sandbox" not in cmd
    assert cmd[-1] == "Refine one bounded spec."


def test_effective_child_executor_timeout_seconds_uses_longer_budget_for_child_materialization(
    supervisor_module: object,
) -> None:
    default_timeout = supervisor_module.effective_child_executor_timeout_seconds(
        (),
        operator_target=False,
    )
    child_timeout = supervisor_module.effective_child_executor_timeout_seconds(
        (supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,),
        operator_target=True,
    )

    assert default_timeout == supervisor_module.FAST_EXECUTION_PROFILE_TIMEOUT_SECONDS
    assert child_timeout == supervisor_module.CHILD_MATERIALIZATION_TIMEOUT_SECONDS
    assert child_timeout > default_timeout


def test_reasoning_effort_timeout_floor_seconds_raises_standard_xhigh_budget(
    supervisor_module: object,
) -> None:
    assert (
        supervisor_module.reasoning_effort_timeout_floor_seconds("xhigh")
        == supervisor_module.XHIGH_REASONING_TIMEOUT_FLOOR_SECONDS
    )
    assert (
        supervisor_module.reasoning_effort_timeout_floor_seconds("medium")
        == supervisor_module.FAST_EXECUTION_PROFILE_TIMEOUT_SECONDS
    )


def test_resolve_execution_profile_auto_selects_materialize_for_child_materialization(
    supervisor_module: object,
) -> None:
    profile = supervisor_module.resolve_execution_profile(
        requested_profile=None,
        run_authority=(supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,),
        operator_target=True,
    )

    assert profile.name == supervisor_module.AUTO_CHILD_MATERIALIZATION_PROFILE_NAME
    assert profile.timeout_seconds == supervisor_module.CHILD_MATERIALIZATION_TIMEOUT_SECONDS


def test_resolve_execution_profile_prefers_explicit_profile_over_auto_selection(
    supervisor_module: object,
) -> None:
    profile = supervisor_module.resolve_execution_profile(
        requested_profile="fast",
        run_authority=(supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,),
        operator_target=True,
    )

    assert profile.name == "fast"
    assert profile.reasoning_effort == supervisor_module.CHILD_EXECUTOR_REASONING_EFFORT
    assert profile.timeout_seconds == supervisor_module.FAST_EXECUTION_PROFILE_TIMEOUT_SECONDS


def test_resolve_execution_profile_auto_selects_fast_for_heuristic_run(
    supervisor_module: object,
) -> None:
    profile = supervisor_module.resolve_execution_profile(
        requested_profile=None,
        run_authority=(),
        operator_target=False,
    )

    assert profile.name == supervisor_module.AUTO_HEURISTIC_PROFILE_NAME
    assert profile.reasoning_effort == supervisor_module.CHILD_EXECUTOR_REASONING_EFFORT
    assert profile.timeout_seconds == supervisor_module.FAST_EXECUTION_PROFILE_TIMEOUT_SECONDS


def test_resolve_execution_profile_keeps_standard_for_explicit_target(
    supervisor_module: object,
) -> None:
    profile = supervisor_module.resolve_execution_profile(
        requested_profile=None,
        run_authority=(),
        operator_target=True,
    )

    assert profile.name == supervisor_module.DEFAULT_EXECUTION_PROFILE_NAME
    assert profile.reasoning_effort == supervisor_module.CHILD_EXECUTOR_REASONING_EFFORT


def test_infer_ordinary_execution_profile_uses_materialize_for_root_seed_like_node(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node = supervisor_module.SpecNode(
        path=repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml",
        data={
            "id": "SG-SPEC-0001",
            "title": "Root Spec",
            "status": "specified",
            "maturity": 0.57,
            "depends_on": [],
            "relates_to": [],
            "refines": [],
            "inputs": [],
            "outputs": ["specs/nodes/SG-SPEC-0001.yaml"],
            "allowed_paths": ["specs/nodes/*.yaml"],
            "acceptance": ["Define how the parent delegates one bounded child concern."],
            "acceptance_evidence": ["seed evidence"],
            "prompt": "This seed spec delegates one child spec when decomposition is needed.",
        },
    )
    specs = [node]

    profile_name = supervisor_module.infer_ordinary_execution_profile_name(
        node=node,
        specs=specs,
        requested_profile=None,
        operator_target=False,
        run_authority=(),
    )

    assert profile_name == supervisor_module.AUTO_CHILD_MATERIALIZATION_PROFILE_NAME


def test_infer_ordinary_execution_profile_keeps_fast_for_refined_policy_with_child_terms(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node = supervisor_module.SpecNode(
        path=repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml",
        data={
            "id": "SG-SPEC-0002",
            "title": "Spec Refinement and Linkage Policy",
            "status": "specified",
            "maturity": 0.57,
            "depends_on": [],
            "relates_to": [],
            "refines": ["SG-SPEC-0001"],
            "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
            "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
            "allowed_paths": ["specs/nodes/*.yaml"],
            "acceptance": ["Define when descendant child specs unlock the parent."],
            "acceptance_evidence": ["policy evidence"],
            "prompt": (
                "Define rules for advancing a seed spec to linked once concrete descendants exist."
            ),
        },
    )
    specs = [node]

    profile_name = supervisor_module.infer_ordinary_execution_profile_name(
        node=node,
        specs=specs,
        requested_profile=None,
        operator_target=False,
        run_authority=(),
    )

    assert profile_name == supervisor_module.AUTO_HEURISTIC_PROFILE_NAME
    assert supervisor_module.bootstrap_child_hint(node, specs) is None


def test_seed_like_spec_requires_root_or_overview_structure(
    supervisor_module: object,
) -> None:
    assert supervisor_module.is_seed_like_spec(
        {
            "title": "Root Spec",
            "prompt": "This seed spec is a root overview spec with child specs.",
        }
    )
    assert not supervisor_module.is_seed_like_spec(
        {
            "title": "Spec Refinement and Linkage Policy",
            "prompt": "Define rules for advancing a seed spec to linked.",
            "refines": ["SG-SPEC-0001"],
            "specification": {
                "objective": "Define how seed specs delegate unresolved areas to child specs.",
            },
        }
    )


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


def test_create_child_codex_home_omits_inner_sandbox_in_bypass_mode(
    supervisor_module: object,
    tmp_path: Path,
) -> None:
    source_home = tmp_path / "source-codex-home"
    source_home.mkdir()
    (source_home / "auth.json").write_text('{"token":"secret"}', encoding="utf-8")

    child_home = supervisor_module.create_child_codex_home(
        source_codex_home=source_home,
        bypass_inner_sandbox=True,
    )
    try:
        config_text = (child_home / "config.toml").read_text(encoding="utf-8")
        assert 'approval_policy = "never"' in config_text
        assert 'sandbox_mode = "workspace-write"' not in config_text
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
            self.wait_timeout: float | None = None

        def wait(self, timeout: float | None = None) -> int:
            self.wait_timeout = timeout
            return 0

    captured: dict[str, object] = {}

    def fake_create_child_codex_home(
        *,
        source_codex_home: Path = Path(),
        profile: object | None = None,
        bypass_inner_sandbox: bool = False,
    ) -> Path:
        _ = source_codex_home
        captured["profile"] = profile
        captured["bypass_inner_sandbox"] = bypass_inner_sandbox
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
        process = FakeProcess()
        captured["process"] = process
        return process

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(node, repo_fixture)

    assert result.returncode == 0
    assert captured["cwd"] == repo_fixture
    assert captured["env"]["CODEX_HOME"] == str(repo_fixture / ".fake-codex-home")
    assert "--ephemeral" in captured["cmd"]
    assert captured["bypass_inner_sandbox"] is False
    assert captured["profile"].name == supervisor_module.AUTO_HEURISTIC_PROFILE_NAME
    assert captured["process"].wait_timeout == min(
        supervisor_module.EXECUTOR_PROGRESS_POLL_SECONDS,
        supervisor_module.FAST_EXECUTION_PROFILE_TIMEOUT_SECONDS,
    )


def test_run_codex_bypasses_inner_sandbox_for_sandbox_branch(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.wait_timeout: float | None = None

        def wait(self, timeout: float | None = None) -> int:
            self.wait_timeout = timeout
            return 0

    captured: dict[str, object] = {}

    def fake_create_child_codex_home(
        *,
        source_codex_home: Path = Path(),
        profile: object | None = None,
        bypass_inner_sandbox: bool = False,
    ) -> Path:
        _ = source_codex_home
        captured["profile"] = profile
        captured["bypass_inner_sandbox"] = bypass_inner_sandbox
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
        process = FakeProcess()
        captured["process"] = process
        return process

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(
        node,
        repo_fixture,
        worktree_branch="sandbox/sg-spec-0010/20260408T122118Z",
    )

    assert result.returncode == 0
    assert captured["cwd"] == repo_fixture
    assert captured["env"]["CODEX_HOME"] == str(repo_fixture / ".fake-codex-home")
    assert captured["bypass_inner_sandbox"] is True
    assert captured["profile"].name == supervisor_module.AUTO_HEURISTIC_PROFILE_NAME
    assert "--dangerously-bypass-approvals-and-sandbox" in captured["cmd"]
    assert "--sandbox" not in captured["cmd"]
    assert captured["process"].wait_timeout == min(
        supervisor_module.EXECUTOR_PROGRESS_POLL_SECONDS,
        supervisor_module.FAST_EXECUTION_PROFILE_TIMEOUT_SECONDS,
    )


def test_run_codex_uses_longer_timeout_for_child_materialization_authority(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.wait_timeout: float | None = None

        def wait(self, timeout: float | None = None) -> int:
            self.wait_timeout = timeout
            return 0

    captured: dict[str, object] = {}

    def fake_create_child_codex_home(
        *,
        source_codex_home: Path = Path(),
        profile: object | None = None,
        bypass_inner_sandbox: bool = False,
    ) -> Path:
        _ = source_codex_home
        captured["profile"] = profile
        _ = bypass_inner_sandbox
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
        _ = (cmd, cwd, env, stdout, stderr, text, bufsize)
        process = FakeProcess()
        captured["process"] = process
        return process

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(
        node,
        repo_fixture,
        run_authority=(supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,),
    )

    assert result.returncode == 0
    assert captured["profile"].name == supervisor_module.AUTO_CHILD_MATERIALIZATION_PROFILE_NAME
    assert captured["process"].wait_timeout == min(
        supervisor_module.EXECUTOR_PROGRESS_POLL_SECONDS,
        supervisor_module.CHILD_MATERIALIZATION_TIMEOUT_SECONDS,
    )


def test_run_codex_uses_explicit_fast_execution_profile(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.wait_timeout: float | None = None

        def wait(self, timeout: float | None = None) -> int:
            self.wait_timeout = timeout
            return 0

    captured: dict[str, object] = {}

    def fake_create_child_codex_home(
        *,
        source_codex_home: Path = Path(),
        profile: object | None = None,
        bypass_inner_sandbox: bool = False,
    ) -> Path:
        _ = source_codex_home
        _ = bypass_inner_sandbox
        captured["profile"] = profile
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
        _ = (cwd, env, stdout, stderr, text, bufsize)
        process = FakeProcess()
        captured["process"] = process
        return process

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(
        node,
        repo_fixture,
        execution_profile="fast",
    )

    assert result.returncode == 0
    assert captured["profile"].name == "fast"
    assert f'model_reasoning_effort="{captured["profile"].reasoning_effort}"' in captured["cmd"]
    assert captured["process"].wait_timeout == min(
        supervisor_module.EXECUTOR_PROGRESS_POLL_SECONDS,
        supervisor_module.FAST_EXECUTION_PROFILE_TIMEOUT_SECONDS,
    )


def test_run_codex_allows_child_model_override(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.wait_timeout: float | None = None

        def wait(self, timeout: float | None = None) -> int:
            self.wait_timeout = timeout
            return 0

    captured: dict[str, object] = {}
    child_model = "gpt-5.3-codex-spark"

    def fake_create_child_codex_home(
        *,
        source_codex_home: Path = Path(),
        profile: object | None = None,
        bypass_inner_sandbox: bool = False,
    ) -> Path:
        _ = source_codex_home
        _ = bypass_inner_sandbox
        captured["profile"] = profile
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
        _ = (cwd, env, stdout, stderr, text, bufsize)
        process = FakeProcess()
        captured["process"] = process
        return process

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(node, repo_fixture, child_model=child_model)

    assert result.returncode == 0
    assert captured["profile"].model == child_model
    cmd = captured["cmd"]
    assert "--model" in cmd
    assert cmd[cmd.index("--model") + 1] == child_model


def test_run_codex_allows_quiet_grace_windows_for_xhigh_reasoning(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.wait_calls: list[float | None] = []
            self.kill_called = False
            self.timeout_events_remaining = 3

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls.append(timeout)
            if self.kill_called:
                return 124
            if self.timeout_events_remaining > 0:
                self.timeout_events_remaining -= 1
                raise subprocess.TimeoutExpired(cmd=["codex"], timeout=timeout or 0)
            return 0

        def kill(self) -> None:
            self.kill_called = True

    captured: dict[str, object] = {}

    profile = supervisor_module.ExecutionProfile(
        name="standard",
        model=supervisor_module.CHILD_EXECUTOR_MODEL,
        reasoning_effort="xhigh",
        timeout_seconds=1,
        disabled_features=supervisor_module.CHILD_EXECUTOR_DISABLED_FEATURES,
    )

    def fake_create_child_codex_home(
        *,
        source_codex_home: Path = Path(),
        profile: object | None = None,
        bypass_inner_sandbox: bool = False,
    ) -> Path:
        _ = (source_codex_home, profile, bypass_inner_sandbox)
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
        _ = (cmd, cwd, env, stdout, stderr, text, bufsize)
        process = FakeProcess()
        captured["process"] = process
        return process

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(supervisor_module, "resolve_execution_profile", lambda **_kwargs: profile)
    monkeypatch.setattr(
        supervisor_module,
        "effective_child_executor_timeout_seconds",
        lambda *args, **kwargs: 1,
    )
    monkeypatch.setattr(
        supervisor_module,
        "capture_nested_executor_progress",
        lambda *_args, **_kwargs: (0, 0, 0),
    )
    monkeypatch.setattr(supervisor_module, "EXECUTOR_PROGRESS_POLL_SECONDS", 1)
    monkeypatch.setattr(supervisor_module, "XHIGH_QUIET_PROGRESS_WINDOWS", 3)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(node, repo_fixture)

    assert result.returncode == 0
    assert captured["process"].kill_called is False
    assert captured["process"].wait_calls == [1, 1, 1, 1]


def test_run_codex_times_out_after_repeated_quiet_windows_without_progress(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.wait_calls: list[float | None] = []
            self.kill_called = False

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls.append(timeout)
            if self.kill_called:
                return 124
            raise subprocess.TimeoutExpired(cmd=["codex"], timeout=timeout or 0)

        def kill(self) -> None:
            self.kill_called = True

    captured: dict[str, object] = {}

    profile = supervisor_module.ExecutionProfile(
        name="standard",
        model=supervisor_module.CHILD_EXECUTOR_MODEL,
        reasoning_effort="xhigh",
        timeout_seconds=1,
        disabled_features=supervisor_module.CHILD_EXECUTOR_DISABLED_FEATURES,
    )

    def fake_create_child_codex_home(
        *,
        source_codex_home: Path = Path(),
        profile: object | None = None,
        bypass_inner_sandbox: bool = False,
    ) -> Path:
        _ = (source_codex_home, profile, bypass_inner_sandbox)
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
        _ = (cmd, cwd, env, stdout, stderr, text, bufsize)
        process = FakeProcess()
        captured["process"] = process
        return process

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(supervisor_module, "resolve_execution_profile", lambda **_kwargs: profile)
    monkeypatch.setattr(
        supervisor_module,
        "effective_child_executor_timeout_seconds",
        lambda *args, **kwargs: 1,
    )
    monkeypatch.setattr(
        supervisor_module,
        "capture_nested_executor_progress",
        lambda *_args, **_kwargs: (0, 0, 0),
    )
    monkeypatch.setattr(supervisor_module, "EXECUTOR_PROGRESS_POLL_SECONDS", 1)
    monkeypatch.setattr(supervisor_module, "XHIGH_QUIET_PROGRESS_WINDOWS", 2)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(node, repo_fixture)

    assert result.returncode == 124
    assert captured["process"].kill_called is True
    assert result.stderr.endswith("supervisor timeout: nested executor timed out after 1 seconds\n")


def test_run_codex_resets_quiet_grace_when_progress_signals_advance(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.wait_calls: list[float | None] = []
            self.kill_called = False
            self.timeout_events_remaining = 4

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls.append(timeout)
            if self.kill_called:
                return 124
            if self.timeout_events_remaining > 0:
                self.timeout_events_remaining -= 1
                raise subprocess.TimeoutExpired(cmd=["codex"], timeout=timeout or 0)
            return 0

        def kill(self) -> None:
            self.kill_called = True

    captured: dict[str, object] = {}

    profile = supervisor_module.ExecutionProfile(
        name="standard",
        model=supervisor_module.CHILD_EXECUTOR_MODEL,
        reasoning_effort="xhigh",
        timeout_seconds=1,
        disabled_features=supervisor_module.CHILD_EXECUTOR_DISABLED_FEATURES,
    )
    progress_states = iter(
        [
            (0, 0, 0),
            (0, 0, 0),
            (0, 0, 1),
            (0, 0, 1),
            (0, 0, 1),
        ]
    )

    def fake_create_child_codex_home(
        *,
        source_codex_home: Path = Path(),
        profile: object | None = None,
        bypass_inner_sandbox: bool = False,
    ) -> Path:
        _ = (source_codex_home, profile, bypass_inner_sandbox)
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
        _ = (cmd, cwd, env, stdout, stderr, text, bufsize)
        process = FakeProcess()
        captured["process"] = process
        return process

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(supervisor_module, "resolve_execution_profile", lambda **_kwargs: profile)
    monkeypatch.setattr(
        supervisor_module,
        "effective_child_executor_timeout_seconds",
        lambda *args, **kwargs: 1,
    )
    monkeypatch.setattr(
        supervisor_module,
        "capture_nested_executor_progress",
        lambda *_args, **_kwargs: next(progress_states),
    )
    monkeypatch.setattr(supervisor_module, "EXECUTOR_PROGRESS_POLL_SECONDS", 1)
    monkeypatch.setattr(supervisor_module, "XHIGH_QUIET_PROGRESS_WINDOWS", 2)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(node, repo_fixture)

    assert result.returncode == 0
    assert captured["process"].kill_called is False
    assert captured["process"].wait_calls == [1, 1, 1, 1, 1]


def test_run_codex_times_out_after_base_budget_when_no_quiet_grace_is_allowed(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.wait_calls: list[float | None] = []
            self.kill_called = False

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls.append(timeout)
            if self.kill_called:
                return 124
            raise subprocess.TimeoutExpired(cmd=["codex"], timeout=timeout or 0)

        def kill(self) -> None:
            self.kill_called = True

    captured: dict[str, object] = {}

    profile = supervisor_module.ExecutionProfile(
        name="standard",
        model=supervisor_module.CHILD_EXECUTOR_MODEL,
        reasoning_effort="high",
        timeout_seconds=1,
        disabled_features=supervisor_module.CHILD_EXECUTOR_DISABLED_FEATURES,
    )
    progress_states = iter(
        [
            (0, 0, 0),
            (0, 0, 1),
        ]
    )

    def fake_create_child_codex_home(
        *,
        source_codex_home: Path = Path(),
        profile: object | None = None,
        bypass_inner_sandbox: bool = False,
    ) -> Path:
        _ = (source_codex_home, profile, bypass_inner_sandbox)
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
        _ = (cmd, cwd, env, stdout, stderr, text, bufsize)
        process = FakeProcess()
        captured["process"] = process
        return process

    monkeypatch.setattr(supervisor_module, "create_child_codex_home", fake_create_child_codex_home)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(supervisor_module, "resolve_execution_profile", lambda **_kwargs: profile)
    monkeypatch.setattr(
        supervisor_module,
        "effective_child_executor_timeout_seconds",
        lambda *args, **kwargs: 1,
    )
    monkeypatch.setattr(
        supervisor_module,
        "capture_nested_executor_progress",
        lambda *_args, **_kwargs: next(progress_states),
    )
    monkeypatch.setattr(supervisor_module, "EXECUTOR_PROGRESS_POLL_SECONDS", 1)

    node = supervisor_module.load_specs()[0]
    result = supervisor_module.run_codex(node, repo_fixture)

    assert result.returncode == 124
    assert captured["process"].kill_called is True
    assert captured["process"].wait_calls == [1, None]


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


def test_sanitize_spec_sync_text_removes_runtime_only_keys(supervisor_module: object) -> None:
    source = """id: SG-SPEC-9999
title: Draft
kind: spec
status: outlined
maturity: 0.1
prompt: Keep this change.
RUN_OUTCOME: done
BLOCKER: none
gate_state: blocked
last_run_id: old-run
"""

    sanitized = supervisor_module.sanitize_spec_sync_text(source)
    data = supervisor_module.get_yaml_module().safe_load(sanitized)

    assert data["id"] == "SG-SPEC-9999"
    assert data["prompt"] == "Keep this change."
    assert "RUN_OUTCOME" not in data
    assert "BLOCKER" not in data
    assert "gate_state" not in data
    assert "last_run_id" not in data

    spec_yaml_path = Path(__file__).resolve().parents[1] / "tools" / "spec_yaml.py"
    spec_yaml_spec = importlib.util.spec_from_file_location("test_spec_yaml_module", spec_yaml_path)
    assert spec_yaml_spec and spec_yaml_spec.loader
    spec_yaml_module = importlib.util.module_from_spec(spec_yaml_spec)
    sys.modules[spec_yaml_spec.name] = spec_yaml_module
    spec_yaml_spec.loader.exec_module(spec_yaml_module)
    assert sanitized == spec_yaml_module.canonicalize_text(sanitized)


def test_validate_refinement_acceptance_approves_local_refinement(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node = supervisor_module.load_specs()[0]
    node.data["acceptance_evidence"] = ["initial evidence"]
    before = json.loads(json.dumps(node.data))
    after = json.loads(json.dumps(node.data))
    after["prompt"] = "Refined one bounded slice."
    after["acceptance_evidence"] = ["updated evidence"]

    result = supervisor_module.validate_refinement_acceptance(
        node=node,
        before_data=before,
        after_data=after,
        changed_files=["specs/nodes/SG-SPEC-0001.yaml"],
        is_graph_refactor_run=False,
        output_errors=[],
        allowed_path_errors=[],
        reconciliation_errors=[],
        transition_errors=[],
        atomicity_errors=[],
    )

    assert result["decision"] == supervisor_module.REFINEMENT_ACCEPT_DECISION_APPROVE
    assert result["change_class"] == supervisor_module.REFINEMENT_CLASS_LOCAL
    assert result["checks"]["content_changed"] is True
    assert result["errors"] == []


def test_validate_refinement_acceptance_requires_review_for_constitutional_diff(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node = supervisor_module.load_specs()[0]
    node.data["acceptance_evidence"] = ["initial evidence"]
    before = json.loads(json.dumps(node.data))
    after = json.loads(json.dumps(node.data))
    after["specification"] = {
        "boundary_policy": {
            "layer_separation": ["Canonical nodes remain the accepted graph of record."]
        }
    }

    result = supervisor_module.validate_refinement_acceptance(
        node=node,
        before_data=before,
        after_data=after,
        changed_files=["specs/nodes/SG-SPEC-0001.yaml"],
        is_graph_refactor_run=False,
        output_errors=[],
        allowed_path_errors=[],
        reconciliation_errors=[],
        transition_errors=[],
        atomicity_errors=[],
    )

    assert result["decision"] == supervisor_module.REFINEMENT_ACCEPT_DECISION_REVIEW_REQUIRED
    assert result["change_class"] == supervisor_module.REFINEMENT_CLASS_CONSTITUTIONAL
    assert result["checks"]["constitutional_diff"] is True


def test_validate_refinement_acceptance_rejects_noop_run(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node = supervisor_module.load_specs()[0]
    node.data["acceptance_evidence"] = ["initial evidence"]
    before = json.loads(json.dumps(node.data))

    result = supervisor_module.validate_refinement_acceptance(
        node=node,
        before_data=before,
        after_data=before,
        changed_files=[],
        is_graph_refactor_run=False,
        output_errors=[],
        allowed_path_errors=[],
        reconciliation_errors=[],
        transition_errors=[],
        atomicity_errors=[],
    )

    assert result["decision"] == supervisor_module.REFINEMENT_ACCEPT_DECISION_REJECT
    assert "No canonical spec change detected" in result["errors"][0]


def test_parse_mutation_budget_rejects_unknown_class(
    supervisor_module: object,
) -> None:
    with pytest.raises(ValueError, match="Unknown mutation class"):
        supervisor_module.parse_mutation_budget("policy_text,unknown_class")


def test_parse_run_authority_rejects_unknown_grant(
    supervisor_module: object,
) -> None:
    with pytest.raises(ValueError, match="Unknown run authority grant"):
        supervisor_module.parse_run_authority("materialize_one_child,unknown_grant")


def test_validate_refinement_acceptance_tracks_schema_required_addition_and_budget(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node = supervisor_module.load_specs()[0]
    before = json.loads(json.dumps(node.data))
    after = json.loads(json.dumps(node.data))
    after["specification"] = {
        "terminology": {
            "proposal_artifact_link": {
                "required_components": [
                    {
                        "component": "reference_value",
                        "cardinality": "exactly 1",
                    }
                ]
            }
        }
    }

    result = supervisor_module.validate_refinement_acceptance(
        node=node,
        before_data=before,
        after_data=after,
        changed_files=["specs/nodes/SG-SPEC-0001.yaml"],
        is_graph_refactor_run=False,
        output_errors=[],
        allowed_path_errors=[],
        reconciliation_errors=[],
        transition_errors=[],
        atomicity_errors=[],
        mutation_budget=(supervisor_module.MUTATION_CLASS_POLICY_TEXT,),
    )

    assert supervisor_module.MUTATION_CLASS_POLICY_TEXT in result["mutation_classes"]
    assert supervisor_module.MUTATION_CLASS_SCHEMA_REQUIRED_ADDITION in result["mutation_classes"]
    assert result["checks"]["within_mutation_budget"] is False
    assert result["budget_exceeded_classes"] == [
        supervisor_module.MUTATION_CLASS_SCHEMA_REQUIRED_ADDITION
    ]
    assert any("mutation budget" in reason for reason in result["review_reasons"])


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


def test_validate_split_proposal_artifact_rejects_too_many_parent_blockers(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    artifact = make_valid_split_proposal(node_data, "RUN-1")
    for idx in range(4, 6):
        slot_key = f"child_{idx}"
        child_id = f"SG-SPEC-000{idx + 1}"
        artifact["parent_after_split"]["intended_depends_on"].append(
            {"slot_key": slot_key, "suggested_id": child_id}
        )
        artifact["suggested_children"].append(
            {
                "slot_key": slot_key,
                "suggested_id": child_id,
                "suggested_path": f"specs/nodes/{child_id}.yaml",
                "bounded_concern_summary": f"Extra child {idx}",
                "suggested_title": f"Extra Child {idx}",
                "suggested_prompt": f"Refine extra child {idx}.",
                "assigned_acceptance": [],
            }
        )

    node = supervisor_module.SpecNode(path=node_path, data=node_data)
    errors = supervisor_module.validate_split_proposal_artifact(
        artifact=artifact,
        node=node,
        run_id="RUN-1",
    )

    assert any("intended_depends_on must not exceed" in error for error in errors)


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


def test_pick_next_work_item_does_not_auto_execute_retrospective_refactor_candidate(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    queue_path = repo_fixture / "runs" / "refactor_queue.json"
    queue_path.write_text(
        json.dumps(
            [
                {
                    "id": "graph_refactor::SG-SPEC-0001::retrospective_refactor_candidate",
                    "work_item_type": "graph_refactor",
                    "spec_id": "SG-SPEC-0001",
                    "signal": "retrospective_refactor_candidate",
                    "recommended_action": "propose_retrospective_refactor",
                    "status": "proposed",
                    "source_run_id": "RUN-1",
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


def test_main_reports_pending_gate_actions_when_no_auto_eligible_work(
    supervisor_module: object,
    repo_fixture: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["status"] = "specified"
    node_data["gate_state"] = "review_pending"
    node_data["required_human_action"] = "approve or retry refinement"
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    exit_code = supervisor_module.main()

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "No eligible auto-refinement gaps found." in out
    assert "Pending gate actions block automatic selection:" in out
    assert "SG-SPEC-0001 | gate=review_pending" in out
    assert "action=approve or retry refinement" in out
    assert "--resolve-gate <SPEC_ID> --decision <decision>" in out


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


def test_observe_graph_health_emits_retrospective_signal_for_live_oversized_parent(
    supervisor_module: object,
) -> None:
    spec_node = supervisor_module.SpecNode
    source = spec_node(
        path=Path("/tmp/source.yaml"),
        data={
            "id": "SG-SPEC-9999",
            "title": "Live Parent",
            "kind": "spec",
            "status": "specified",
            "maturity": 0.4,
            "depends_on": [],
            "acceptance": [f"criterion-{i}" for i in range(6)],
            "prompt": "Refine one bounded slice of this node.",
        },
    )
    child = spec_node(
        path=Path("/tmp/child.yaml"),
        data={
            "id": "SG-SPEC-1000",
            "title": "Existing Child",
            "kind": "spec",
            "status": "specified",
            "maturity": 0.5,
            "depends_on": [],
            "relates_to": [],
            "refines": ["SG-SPEC-9999"],
            "acceptance": ["child-kept"],
            "acceptance_evidence": ["accepted"],
            "prompt": "Existing accepted child.",
        },
    )

    graph_health = supervisor_module.observe_graph_health(
        source_node=source,
        worktree_specs=[source, child],
        reconciliation={"semantic_dependencies_resolved": True},
        atomicity_errors=[],
        outcome="done",
    )

    assert supervisor_module.RETROSPECTIVE_REFACTOR_SIGNAL in graph_health["signals"]
    assert "oversized_spec" not in graph_health["signals"]
    assert "propose_retrospective_refactor" in graph_health["recommended_actions"]
    retrospective = next(
        observation
        for observation in graph_health["observations"]
        if observation["kind"] == supervisor_module.RETROSPECTIVE_REFACTOR_SIGNAL
    )
    assert retrospective["details"]["live_child_ids"] == ["SG-SPEC-1000"]
    assert retrospective["details"]["accepted_child_ids"] == ["SG-SPEC-1000"]


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


def test_update_refactor_queue_marks_retrospective_candidate_proposal_first(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    graph_health = {
        "source_spec_id": "SG-SPEC-9999",
        "observations": [
            {
                "kind": supervisor_module.RETROSPECTIVE_REFACTOR_SIGNAL,
                "details": {
                    "atomicity": ["too many acceptance criteria"],
                    "live_child_ids": ["SG-SPEC-1000"],
                    "accepted_child_ids": ["SG-SPEC-1000"],
                },
            }
        ],
        "signals": [supervisor_module.RETROSPECTIVE_REFACTOR_SIGNAL],
        "recommended_actions": ["propose_retrospective_refactor"],
    }

    path = supervisor_module.update_refactor_queue(graph_health=graph_health, run_id="RUN-1")
    items = json.loads(path.read_text(encoding="utf-8"))

    assert len(items) == 1
    item = items[0]
    assert item["work_item_type"] == "graph_refactor"
    assert item["signal"] == supervisor_module.RETROSPECTIVE_REFACTOR_SIGNAL
    assert item["recommended_action"] == "propose_retrospective_refactor"
    assert item["execution_policy"] == "emit_proposal"


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


def test_update_proposal_queue_emits_retrospective_refactor_proposal_immediately(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    graph_health = {
        "source_spec_id": "SG-SPEC-9999",
        "observations": [
            {
                "kind": supervisor_module.RETROSPECTIVE_REFACTOR_SIGNAL,
                "details": {
                    "atomicity": ["too many acceptance criteria"],
                    "live_child_ids": ["SG-SPEC-1000"],
                    "accepted_child_ids": ["SG-SPEC-1000"],
                },
            }
        ],
        "signals": [supervisor_module.RETROSPECTIVE_REFACTOR_SIGNAL],
        "recommended_actions": ["propose_retrospective_refactor"],
    }

    _path, items = supervisor_module.update_proposal_queue(
        graph_health=graph_health,
        run_id="RUN-1",
    )

    assert len(items) == 1
    proposal = items[0]
    assert proposal["proposal_type"] == "refactor_proposal"
    assert proposal["signal"] == supervisor_module.RETROSPECTIVE_REFACTOR_SIGNAL
    assert proposal["trigger"] == "retrospective_signal"
    assert proposal["occurrence_count"] == 1
    assert proposal["threshold"] == 1
    assert proposal["supporting_run_ids"] == ["RUN-1"]
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
    assert "Do not browse the web or external sources" in prompt
    assert "Bootstrap guidance:" not in prompt


def test_build_prompt_includes_child_materialization_guidance_for_targeted_non_root_parent(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    specs_dir = repo_fixture / "specs" / "nodes"
    node_path = specs_dir / "SG-SPEC-0002.yaml"
    node_path.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Vocabulary Parent",
                "kind": "spec",
                "status": "specified",
                "maturity": 0.4,
                "depends_on": [],
                "relates_to": [],
                "refines": ["SG-SPEC-0001"],
                "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["Delegate one bounded child vocabulary slice."],
                "acceptance_evidence": ["Existing evidence."],
                "prompt": "Materialize one bounded child from this parent delegation boundary.",
            }
        ),
        encoding="utf-8",
    )

    node = next(spec for spec in supervisor_module.load_specs() if spec.id == "SG-SPEC-0002")
    prompt = supervisor_module.build_prompt(
        node,
        operator_target=True,
        operator_note="Create one new child spec for the delegated bootstrap relation vocabulary.",
        run_authority=(supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,),
    )

    assert "Refinement mode: explicit_target_refine" in prompt
    assert "Run authority grant:" in prompt
    assert f"- {supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD}" in prompt
    assert "Child materialization guidance:" in prompt
    assert "Suggested child spec ID: SG-SPEC-0003" in prompt
    assert "Suggested child spec path: specs/nodes/SG-SPEC-0003.yaml" in prompt
    assert "Prefer one child over multiple siblings in this mode." in prompt


def test_build_prompt_includes_mutation_budget_for_explicit_target(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node = supervisor_module.load_specs()[0]
    prompt = supervisor_module.build_prompt(
        node,
        operator_target=True,
        operator_note="Only tighten one bridge concern.",
        mutation_budget=(
            supervisor_module.MUTATION_CLASS_POLICY_TEXT,
            supervisor_module.MUTATION_CLASS_SCHEMA_REQUIRED_ADDITION,
        ),
    )

    assert "Mutation budget:" in prompt
    assert f"- {supervisor_module.MUTATION_CLASS_POLICY_TEXT}" in prompt
    assert f"- {supervisor_module.MUTATION_CLASS_SCHEMA_REQUIRED_ADDITION}" in prompt
    assert "do not smuggle it in silently" in prompt


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
    assert "id = refactor_proposal::SG-SPEC-0001::oversized_spec" in prompt
    assert "execution_policy = emit_proposal" in prompt
    assert "parent_after_split.retained_acceptance[] =" in prompt
    assert '"acceptance_index": <int>' in prompt
    assert '"refines": ["SG-SPEC-0001"]' in prompt
    assert "source_run_ids must include the current run ID above." in prompt
    assert "Current parent acceptance criteria:" in prompt
    assert "- [1] criterion-1" in prompt


def test_build_prompt_includes_retrospective_split_preservation_guidance(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    parent_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    parent = supervisor_module.get_yaml_module().safe_load(parent_path.read_text(encoding="utf-8"))
    parent["title"] = "Calculator Overview"
    parent["prompt"] = "Keep this parent as overview and split detailed concerns."
    parent["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    parent_path.write_text(json.dumps(parent), encoding="utf-8")

    child_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    child_path.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Existing Child",
                "kind": "spec",
                "status": "specified",
                "maturity": 0.4,
                "depends_on": [],
                "relates_to": [],
                "refines": ["SG-SPEC-0001"],
                "inputs": [],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["child-kept"],
                "acceptance_evidence": ["accepted child work"],
                "prompt": "Preserve accepted child work.",
            }
        ),
        encoding="utf-8",
    )

    specs = supervisor_module.load_specs()
    node = next(spec for spec in specs if spec.id == "SG-SPEC-0001")
    work_item = supervisor_module.build_split_refactor_work_item(node, specs)
    work_item["planned_run_id"] = "RUN-1"
    prompt = supervisor_module.build_prompt(node, work_item)

    assert work_item["retrospective_target"] is True
    assert work_item["live_child_ids"] == ["SG-SPEC-0002"]
    assert work_item["accepted_child_ids"] == ["SG-SPEC-0002"]
    assert (
        "This target already sits inside a live graph region with existing child specs." in prompt
    )
    assert "Accepted child work must remain traceable" in prompt
    assert "Live child spec IDs: SG-SPEC-0002" in prompt
    assert "Accepted child spec IDs: SG-SPEC-0002" in prompt


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

    changed_snapshots = [
        [],
        ["specs/nodes/SG-SPEC-0001.yaml"],
        ["specs/nodes/SG-SPEC-0001.yaml"],
    ]
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
        node_path.write_text(
            supervisor_module.dump_yaml_text(data) + "RUN_OUTCOME: done\nBLOCKER: none\n",
            encoding="utf-8",
        )
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
    assert updated["prompt"] == "Updated by Codex"
    assert updated["acceptance_evidence"] == ["criterion satisfied by refined section"]
    assert "RUN_OUTCOME" not in updated
    assert "BLOCKER" not in updated
    assert "RUN_OUTCOME:" not in node_path.read_text(encoding="utf-8")
    assert "BLOCKER:" not in node_path.read_text(encoding="utf-8")
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


def test_main_dry_run_supports_explicit_targeted_refinement_for_review_pending_node(
    supervisor_module: object,
    repo_fixture: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["status"] = "specified"
    node_data["maturity"] = 0.4
    node_data["gate_state"] = "review_pending"
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    exit_code = supervisor_module.main(
        target_spec="SG-SPEC-0001",
        dry_run=True,
        operator_note="Tighten only the proposal-lane ownership semantics.",
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Selected spec node: SG-SPEC-0001" in captured.out
    assert '"selection_mode": "explicit_target_refine"' in captured.out
    assert '"operator_target": "SG-SPEC-0001"' in captured.out
    assert '"operator_note": "Tighten only the proposal-lane ownership semantics."' in captured.out
    assert "Refinement mode: explicit_target_refine" in captured.out
    assert "Operator intent:" in captured.out
    assert "Tighten only the proposal-lane ownership semantics." in captured.out
    assert captured.err == ""


def test_pick_next_spec_gap_selects_linked_continuation_candidate_when_no_workable_specs(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node1_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node1 = supervisor_module.get_yaml_module().safe_load(node1_path.read_text(encoding="utf-8"))
    node1["status"] = "linked"
    node1["maturity"] = 0.4
    node1["depends_on"] = ["SG-SPEC-0002"]
    node1_path.write_text(json.dumps(node1), encoding="utf-8")

    node2_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    node2_path.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Dependency Node",
                "kind": "spec",
                "status": "linked",
                "maturity": 0.6,
                "depends_on": [],
                "relates_to": [],
                "refines": [],
                "inputs": [],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["kept"],
                "prompt": "Refine this linked node.",
            }
        ),
        encoding="utf-8",
    )

    specs = supervisor_module.load_specs()
    selected = supervisor_module.pick_next_spec_gap(specs)

    assert selected is not None
    assert selected.id == "SG-SPEC-0001"
    assert supervisor_module.selection_mode_for_node(selected, specs) == "linked_continuation"
    assert supervisor_module.linked_continuation_reasons(
        selected, supervisor_module.index_specs(specs)
    ) == ["latent_graph_improvement_candidate", "weak_structural_linkage_candidate"]


def test_pick_next_spec_gap_does_not_select_low_maturity_linked_spec_without_signal_pressure(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node["status"] = "linked"
    node["maturity"] = 0.4
    node["depends_on"] = []
    node_path.write_text(json.dumps(node), encoding="utf-8")

    specs = supervisor_module.load_specs()

    assert supervisor_module.pick_next_spec_gap(specs) is None


def test_pick_next_spec_gap_does_not_select_reviewed_spec_for_linked_continuation(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node["status"] = "reviewed"
    node["maturity"] = 0.4
    node["depends_on"] = ["SG-SPEC-0002"]
    node["last_outcome"] = "blocked"
    node_path.write_text(json.dumps(node), encoding="utf-8")

    node2_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    node2_path.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Dependency Node",
                "kind": "spec",
                "status": "specified",
                "maturity": 0.6,
                "depends_on": [],
                "relates_to": [],
                "refines": [],
                "inputs": [],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["kept"],
                "prompt": "Refine this node.",
            }
        ),
        encoding="utf-8",
    )

    specs = supervisor_module.load_specs()

    assert (
        supervisor_module.linked_continuation_reasons(
            specs[0], supervisor_module.index_specs(specs)
        )
        == []
    )
    assert supervisor_module.pick_next_spec_gap(specs).id == "SG-SPEC-0002"


def test_main_explicit_targeted_refinement_dry_run_prints_mutation_budget(
    supervisor_module: object,
    repo_fixture: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = supervisor_module.main(
        target_spec="SG-SPEC-0001",
        dry_run=True,
        operator_note="Tighten only one bounded schema concern.",
        mutation_budget=(
            supervisor_module.MUTATION_CLASS_POLICY_TEXT,
            supervisor_module.MUTATION_CLASS_SCHEMA_REQUIRED_ADDITION,
        ),
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"mutation_budget": ["policy_text", "schema_required_addition"]' in captured.out
    assert "Mutation budget:" in captured.out
    assert "- schema_required_addition" in captured.out


def test_main_targeted_refinement_hides_executor_transcript_by_default(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Working Node"
    node_data["prompt"] = "Refine one bounded slice of this node."
    node_data["allowed_paths"] = ["specs/nodes/SG-SPEC-0001.yaml"]
    if not isinstance(node_data.get("acceptance_evidence"), list):
        acceptance = node_data.get("acceptance", [])
        node_data["acceptance_evidence"] = [f"evidence-{idx}" for idx, _ in enumerate(acceptance)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [
        [],
        ["specs/nodes/SG-SPEC-0001.yaml"],
        ["specs/nodes/SG-SPEC-0001.yaml"],
    ]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(
            worktree_node.read_text(encoding="utf-8")
        )
        data["prompt"] = "Refined prompt."
        worktree_node.write_text(supervisor_module.dump_yaml_text(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\nexecutor detail line\n",
            stderr="executor stderr detail\n",
        )

    exit_code = supervisor_module.main(executor=fake_executor, target_spec="SG-SPEC-0001")

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Run log:" in captured.out
    assert "Finished status: ok" in captured.out
    assert "=== codex stdout ===" not in captured.out
    assert "executor detail line" not in captured.out
    assert "=== codex stderr ===" not in captured.err
    assert "executor stderr detail" not in captured.err


def test_main_targeted_refinement_shows_executor_transcript_in_verbose_mode(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Working Node"
    node_data["prompt"] = "Refine one bounded slice of this node."
    node_data["allowed_paths"] = ["specs/nodes/SG-SPEC-0001.yaml"]
    if not isinstance(node_data.get("acceptance_evidence"), list):
        acceptance = node_data.get("acceptance", [])
        node_data["acceptance_evidence"] = [f"evidence-{idx}" for idx, _ in enumerate(acceptance)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [
        [],
        ["specs/nodes/SG-SPEC-0001.yaml"],
        ["specs/nodes/SG-SPEC-0001.yaml"],
    ]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(
            worktree_node.read_text(encoding="utf-8")
        )
        data["prompt"] = "Refined prompt."
        worktree_node.write_text(supervisor_module.dump_yaml_text(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\nexecutor detail line\n",
            stderr="executor stderr detail\n",
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0001",
        verbose=True,
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Created worktree:" in captured.out
    assert "Detected changed files:" in captured.out
    assert "=== codex stdout ===" in captured.out
    assert "executor detail line" in captured.out
    assert "=== codex stderr ===" in captured.err
    assert "executor stderr detail" in captured.err


def test_main_explicit_targeted_refinement_reruns_review_pending_spec(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["status"] = "specified"
    node_data["maturity"] = 0.4
    node_data["gate_state"] = "review_pending"
    node_data["prompt"] = "Proposal lane policy needs tightening."
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/explicit-target"),
    )

    changed_snapshots = [
        [],
        ["specs/nodes/SG-SPEC-0001.yaml"],
        ["specs/nodes/SG-SPEC-0001.yaml"],
    ]
    monkeypatch.setattr(
        supervisor_module,
        "git_changed_files",
        lambda _cwd=None: changed_snapshots.pop(0),
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        current_path = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        current_data = supervisor_module.get_yaml_module().safe_load(
            current_path.read_text(encoding="utf-8")
        )
        current_data["prompt"] = "Proposal lane policy now distinguishes tracked handles."
        current_data["acceptance_evidence"] = ["criterion satisfied by targeted rerun"]
        current_path.write_text(
            supervisor_module.dump_yaml_text(current_data),
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
        operator_note="Refine only one bounded concern for targeted rerun.",
    )

    assert exit_code == 0
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["gate_state"] == "review_pending"
    assert updated["proposed_status"] == "linked"
    assert updated["prompt"] == "Proposal lane policy now distinguishes tracked handles."
    assert updated["acceptance_evidence"] == ["criterion satisfied by targeted rerun"]

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["selected_by_rule"]["selection_mode"] == "explicit_target_refine"
    assert payload["selected_by_rule"]["operator_target"] == "SG-SPEC-0001"
    assert (
        payload["selected_by_rule"]["operator_note"]
        == "Refine only one bounded concern for targeted rerun."
    )
    assert payload["outcome"] == "done"


def test_main_blocks_executor_environment_failures_without_graph_health_side_effects(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["acceptance"] = [f"criterion-{i}" for i in range(1, 7)]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")
    before_data = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )

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

    exit_code = supervisor_module.main(executor=fake_executor, target_spec="SG-SPEC-0001")
    assert exit_code == 1

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    stripped_updated = {
        key: value
        for key, value in updated.items()
        if key not in supervisor_module.SYNC_STRIPPED_SPEC_KEYS
    }
    assert stripped_updated == before_data
    assert updated["gate_state"] == "blocked"
    assert updated["required_human_action"] == "repair executor environment and rerun supervisor"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["gate_state"] == "blocked"
    assert payload["required_human_action"] == "repair executor environment and rerun supervisor"
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


def test_main_usage_limit_failure_reports_quota_recovery_action(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    before_data = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )
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
                "ERROR: You've hit your usage limit. Upgrade to Pro or purchase more credits.\n"
            ),
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0001",
    )
    assert exit_code == 1

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    stripped_updated = {
        key: value
        for key, value in updated.items()
        if key not in supervisor_module.SYNC_STRIPPED_SPEC_KEYS
    }
    assert stripped_updated == before_data
    assert updated["gate_state"] == "blocked"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["gate_state"] == "blocked"
    assert (
        payload["required_human_action"]
        == "wait for usage reset or add credits and rerun supervisor"
    )
    assert payload["executor_environment"]["issue_kinds"] == ["usage_limit_failure"]


def test_main_interrupted_source_refinement_cleans_runtime_tail_when_only_source_changed(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_path.write_text(
        "# keep original source text during failed cleanup\n"
        + node_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    before_text = node_path.read_text(encoding="utf-8")
    before_data = supervisor_module.get_yaml_module().safe_load(before_text)

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

    def fake_executor(_node: object, _worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_node = _worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        worktree_node.write_text(
            worktree_node.read_text(encoding="utf-8") + "\n# interrupted partial edit\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=124,
            stdout="RUN_OUTCOME: escalate\nBLOCKER: none\n",
            stderr="supervisor timeout: nested executor timed out after 180 seconds\n",
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0001",
    )
    assert exit_code == 1

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    stripped_updated = {
        key: value
        for key, value in updated.items()
        if key not in supervisor_module.SYNC_STRIPPED_SPEC_KEYS
    }
    assert stripped_updated == before_data
    assert updated["gate_state"] == "escalated"
    assert updated["last_exit_code"] == 124
    assert updated["last_changed_files"] == ["specs/nodes/SG-SPEC-0001.yaml"]
    assert updated["required_human_action"] == "manual escalation"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["gate_state"] in {"blocked", "escalated"}
    assert payload["changed_files"] == ["specs/nodes/SG-SPEC-0001.yaml"]
    assert payload["exit_code"] == 124


def test_main_interrupted_source_refinement_cleans_runtime_tail_when_no_canonical_diff(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    before_data = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    monkeypatch.setattr(
        supervisor_module,
        "git_changed_files",
        lambda _cwd=None: [],
    )

    def fake_executor(_node: object, _worktree_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=124,
            stdout="RUN_OUTCOME: blocked\nBLOCKER: none\n",
            stderr="supervisor timeout: nested executor timed out after 300 seconds\n",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    stripped_updated = {
        key: value
        for key, value in updated.items()
        if key not in supervisor_module.SYNC_STRIPPED_SPEC_KEYS
    }
    assert stripped_updated == before_data
    assert updated["gate_state"] == "blocked"
    assert updated["last_exit_code"] == 124
    assert updated["last_changed_files"] == []
    assert updated["required_human_action"] == "repair executor environment and rerun supervisor"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["gate_state"] == "blocked"
    assert payload["changed_files"] == []
    assert payload["exit_code"] == 124


def test_main_interrupted_multi_file_refinement_cleans_parent_runtime_tail(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    before_text = node_path.read_text(encoding="utf-8")
    before_data = supervisor_module.get_yaml_module().safe_load(before_text)

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [
        [],
        ["specs/nodes/SG-SPEC-0001.yaml", "specs/nodes/SG-SPEC-0002.yaml"],
    ]
    monkeypatch.setattr(
        supervisor_module,
        "git_changed_files",
        lambda _cwd=None: changed_snapshots.pop(0),
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(
            worktree_node.read_text(encoding="utf-8")
        )
        data["depends_on"] = ["SG-SPEC-0002"]
        worktree_node.write_text(json.dumps(data), encoding="utf-8")

        child_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0002.yaml"
        child_node.write_text(
            json.dumps(
                {
                    "id": "SG-SPEC-0002",
                    "title": "Interrupted Child",
                    "kind": "spec",
                    "status": "outlined",
                    "maturity": 0.2,
                    "depends_on": [],
                    "relates_to": [],
                    "refines": ["SG-SPEC-0001"],
                    "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                    "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                    "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                    "acceptance": ["Defines the interrupted child boundary"],
                    "acceptance_evidence": [
                        {
                            "criterion": "Defines the interrupted child boundary",
                            "evidence": "Draft child content existed only in the worktree.",
                        }
                    ],
                    "prompt": "Refine one interrupted child.",
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=124,
            stdout="",
            stderr="supervisor timeout: nested executor timed out after 420 seconds\n",
        )

    exit_code = supervisor_module.main(executor=fake_executor)
    assert exit_code == 1

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    stripped_updated = {
        key: value
        for key, value in updated.items()
        if key not in supervisor_module.SYNC_STRIPPED_SPEC_KEYS
    }
    assert stripped_updated == before_data
    assert not (repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml").exists()
    assert updated["gate_state"] == "escalated"
    assert updated["last_exit_code"] == 124
    assert updated["required_human_action"] == "manual escalation"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["completion_status"] == "failed"
    assert payload["changed_files"] == [
        "specs/nodes/SG-SPEC-0001.yaml",
        "specs/nodes/SG-SPEC-0002.yaml",
    ]
    assert payload["executor_environment"]["issue_kinds"] == ["executor_timeout_failure"]


def test_classify_executor_environment_detects_supervisor_timeout(
    supervisor_module: object,
) -> None:
    environment = supervisor_module.classify_executor_environment(
        "supervisor timeout: nested executor timed out after 180 seconds\n"
    )

    assert environment["issue_kinds"] == ["executor_timeout_failure"]


def test_classify_executor_environment_detects_usage_limit_failure(
    supervisor_module: object,
) -> None:
    environment = supervisor_module.classify_executor_environment(
        "ERROR: You've hit your usage limit. Upgrade to Pro or purchase more credits.\n"
    )

    assert environment["issue_kinds"] == ["usage_limit_failure"]


def test_normalize_executor_stderr_condenses_known_noise(
    supervisor_module: object,
) -> None:
    stderr = (
        "2026-04-11T13:11:10Z ERROR codex_core::models_manager::manager: "
        "failed to refresh available models: timeout waiting for child process to exit\n"
        "2026-04-11T13:11:18Z WARN codex_app_server_client: "
        "dropping in-process app-server event because consumer queue is full\n"
        "warning: in-process app-server event stream lagged; dropped 20 events\n"
        "ERROR: stream disconnected before completion: error sending request for url\n"
    )

    normalized = supervisor_module.normalize_executor_stderr(stderr)

    assert "failed to refresh available models" not in normalized
    assert "consumer queue is full" not in normalized
    assert "event stream lagged" not in normalized
    assert "stream disconnected before completion" in normalized
    assert "suppressed model refresh timeout warning (1 occurrence(s))" in normalized
    assert "suppressed app-server queue-full warning (1 occurrence(s))" in normalized
    assert "suppressed app-server stream lag warning (1 occurrence(s))" in normalized


def test_repair_candidate_yaml_text_restores_original_key_indentation(
    supervisor_module: object,
) -> None:
    original = (
        "specification:\n"
        "  graph_health_signal_policy:\n"
        "    initial_signals:\n"
        "    - oversized_spec\n"
        "    semantics:\n"
        "    - Signal presence is diagnostic only.\n"
    )
    candidate = original.replace("    initial_signals:", "  initial_signals:")

    repaired = supervisor_module.repair_candidate_yaml_text(candidate, original)

    assert "    initial_signals:" in repaired
    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["specification"]["graph_health_signal_policy"]["initial_signals"] == [
        "oversized_spec"
    ]


def test_repair_candidate_yaml_text_restores_original_list_item_indentation(
    supervisor_module: object,
) -> None:
    original = (
        "acceptance:\n"
        "- criterion: Keeps canonical application and refusal semantics separate.\n"
        "  evidence: Evidence.\n"
    )
    candidate = original.replace(
        "- criterion: Keeps canonical application and refusal semantics separate.",
        "  - criterion: Keeps canonical application and refusal semantics separate.",
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate, original)

    repaired_item = "\n- criterion: Keeps canonical application and refusal semantics separate.\n"
    assert repaired_item in repaired
    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["acceptance"][0]["criterion"] == (
        "Keeps canonical application and refusal semantics separate."
    )


def test_repair_candidate_yaml_text_quotes_multiline_sequence_scalar_with_colon(
    supervisor_module: object,
) -> None:
    candidate = (
        "specification:\n"
        "  revision_contract:\n"
        "    record_minimum_semantics:\n"
        "    - Every revision_origin_marker MUST justify history origin (for\n"
        "      example: seeded, imported, migrated).\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    assert "example: seeded, imported, migrated" in repaired
    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["specification"]["revision_contract"]["record_minimum_semantics"] == [
        (
            "Every revision_origin_marker MUST justify history origin "
            "(for example: seeded, imported, migrated)."
        )
    ]


def test_repair_candidate_yaml_text_indents_sequence_under_new_key(
    supervisor_module: object,
) -> None:
    candidate = (
        "specification:\n"
        "  semantic_contracts:\n"
        "    governed_by_state_family:\n"
        "    - '`governed_by_state_family` must identify the authoritative "
        "StateFamily used to describe the subject\n"
        "      Concept''s admissible condition space.'\n"
        "    - This relation must not collapse StateFamily semantics into "
        "free-floating tags without a governing\n"
        "      Concept.\n"
        "    resolved_by_alias:\n"
        "    - '`resolved_by_alias` must preserve one-way subordination from "
        "Alias to canonical primitive identity.'\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    assert "    governed_by_state_family:\n      - " in repaired
    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["specification"]["semantic_contracts"]["governed_by_state_family"][0].startswith(
        "`governed_by_state_family` must identify"
    )


def test_repair_candidate_yaml_text_restores_existing_key_outdent(
    supervisor_module: object,
) -> None:
    original = (
        "specification:\n  scope:\n    out:\n    - Existing item.\n  terminology:\n    key: value\n"
    )
    candidate = (
        "specification:\n"
        "  scope:\n"
        "    out:\n"
        "    - Existing item.\n"
        "        terminology:\n"
        "    key: value\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate, original)

    assert "\n  terminology:\n" in repaired
    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["specification"]["terminology"]["key"] == "value"


def test_repair_candidate_yaml_text_quotes_multiline_sequence_scalar_with_colon_suffix(
    supervisor_module: object,
) -> None:
    candidate = (
        "specification:\n"
        "  continuation:\n"
        "    - The supervisor may continue into at most one linked "
        "latent_graph_improvement_candidate at a time;\n"
        "      each continuation decision emits one derived selection record with at least:\n"
        "      candidate_spec_id, triggering_signal_id, and rationale.\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["specification"]["continuation"] == [
        (
            "The supervisor may continue into at most one linked "
            "latent_graph_improvement_candidate at a time; "
            "each continuation decision emits one derived selection record "
            "with at least: candidate_spec_id, triggering_signal_id, and rationale."
        )
    ]


def test_repair_candidate_yaml_text_quotes_multiline_sequence_scalar_starting_with_backtick(
    supervisor_module: object,
) -> None:
    candidate = (
        "specification:\n"
        "  output_contract:\n"
        "  - `derived_continuation_handoff` contains one entry per non-selected "
        "candidate after deterministic ranking\n"
        "    and may include suppression or ranking-rationale annotations.\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["specification"]["output_contract"] == [
        (
            "`derived_continuation_handoff` contains one entry per non-selected "
            "candidate after deterministic ranking and may include suppression "
            "or ranking-rationale annotations."
        )
    ]


def test_repair_candidate_yaml_text_quotes_multiline_mapping_scalar(
    supervisor_module: object,
) -> None:
    candidate = (
        "validation_invariants:\n"
        "- id: LYR-003\n"
        "  statement: Any newly proposed node kind must be refined through a "
        "dedicated child spec before changing\n"
        "  ownership semantics.\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["validation_invariants"][0]["statement"] == (
        "Any newly proposed node kind must be refined through a dedicated "
        "child spec before changing ownership semantics."
    )


def test_repair_candidate_yaml_text_quotes_multiline_sequence_mapping_scalar(
    supervisor_module: object,
) -> None:
    candidate = (
        "acceptance_evidence:\n"
        "- criterion: Defines the bounded execution-mechanics cluster beneath "
        "SG-SPEC-0026 that groups exactly two concerns:\n"
        "    retrospective direct-update boundaries and one proposal/split "
        "mechanics subcluster.\n"
        "  evidence: specification.cluster_members assigns retrospective "
        "direct-update boundary to SG-SPEC-0005.\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["acceptance_evidence"][0]["criterion"] == (
        "Defines the bounded execution-mechanics cluster beneath SG-SPEC-0026 "
        "that groups exactly two concerns: retrospective direct-update "
        "boundaries and one proposal/split mechanics subcluster."
    )
    assert parsed["acceptance_evidence"][0]["evidence"] == (
        "specification.cluster_members assigns retrospective direct-update "
        "boundary to SG-SPEC-0005."
    )


def test_repair_candidate_yaml_text_quotes_sequence_mapping_scalar_with_nested_list(
    supervisor_module: object,
) -> None:
    candidate = (
        "specification:\n"
        "  queue_contract_fields:\n"
        "  - retry_condition: a bounded retry state enum controlling whether "
        "a queued control item is currently\n"
        "      considered for retry selection. Allowed values:\n"
        "      - retry_ready\n"
        "      - retry_blocked_by_dependency\n"
        "      - retry_blocked_by_governance\n"
        "      - retry_exhausted\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["specification"]["queue_contract_fields"] == [
        {
            "retry_condition": (
                "a bounded retry state enum controlling whether a queued control item is currently "
                "considered for retry selection. Allowed values: retry_ready "
                "retry_blocked_by_dependency retry_blocked_by_governance retry_exhausted"
            )
        }
    ]


def test_repair_candidate_yaml_text_preserves_quoted_sibling_key_in_sequence_mapping(
    supervisor_module: object,
) -> None:
    candidate = (
        "acceptance_evidence:\n"
        "- criterion: Defines the bounded execution-mechanics cluster beneath "
        "SG-SPEC-0026 that groups exactly two concerns:\n"
        "    retrospective direct-update boundaries and one proposal/split "
        "mechanics subcluster.\n"
        '  "evidence note": Keep the sibling key intact.\n'
        "  evidence: specification.cluster_members assigns retrospective "
        "direct-update boundary to SG-SPEC-0005.\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    item = parsed["acceptance_evidence"][0]
    assert item["criterion"] == (
        "Defines the bounded execution-mechanics cluster beneath SG-SPEC-0026 "
        "that groups exactly two concerns: retrospective direct-update "
        "boundaries and one proposal/split mechanics subcluster."
    )
    assert item["evidence note"] == "Keep the sibling key intact."
    assert item["evidence"] == (
        "specification.cluster_members assigns retrospective direct-update "
        "boundary to SG-SPEC-0005."
    )


def test_repair_candidate_yaml_text_outdents_nested_sibling_sequence_item(
    supervisor_module: object,
) -> None:
    candidate = (
        "acceptance_evidence:\n"
        "- criterion: First criterion.\n"
        "  evidence: First evidence line.\n"
        "  - criterion: Second criterion.\n"
        "  evidence: Second evidence line.\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["acceptance_evidence"][0]["criterion"] == "First criterion."
    assert parsed["acceptance_evidence"][0]["evidence"] == "First evidence line."
    assert parsed["acceptance_evidence"][1]["criterion"] == "Second criterion."
    assert parsed["acceptance_evidence"][1]["evidence"] == "Second evidence line."


def test_repair_candidate_yaml_text_preserves_nested_sequence_items(
    supervisor_module: object,
) -> None:
    candidate = (
        "specification:\n"
        "  items:\n"
        "  - name: parent\n"
        "    children:\n"
        "      - child_one\n"
        "      - child_two\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["specification"]["items"][0]["name"] == "parent"
    assert parsed["specification"]["items"][0]["children"] == ["child_one", "child_two"]


def test_repair_candidate_yaml_text_does_not_swallow_nested_mapping_key(
    supervisor_module: object,
) -> None:
    candidate = "specification:\n  summary: Short summary line\n    new_key: value\n"

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    assert "new_key: value" in repaired
    parse_failed = False
    try:
        supervisor_module.get_yaml_module().safe_load(repaired)
    except BaseException:
        parse_failed = True
    assert parse_failed is True


def test_repair_candidate_yaml_text_preserves_nested_mapping_under_nested_key(
    supervisor_module: object,
) -> None:
    original = (
        "specification:\n"
        "  retry_condition_fields:\n"
        "    retry_condition:\n"
        "      description: Base description.\n"
    )
    candidate = (
        "specification:\n"
        "  retry_condition_fields:\n"
        "    retry_condition:\n"
        "      reason:\n"
        "        description: Retry rationale.\n"
        "        allowed_values:\n"
        "        - dependency_unblocked\n"
        "        - transport_retryable\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate, original)

    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    reason = parsed["specification"]["retry_condition_fields"]["retry_condition"]["reason"]
    assert reason["description"] == "Retry rationale."
    assert reason["allowed_values"] == [
        "dependency_unblocked",
        "transport_retryable",
    ]


def test_repair_candidate_yaml_text_skips_ambiguous_original_line_indent(
    supervisor_module: object,
) -> None:
    original = (
        "depends_on:\n- SG-SPEC-0001\nlast_reconciliation:\n  changed_spec_ids:\n  - SG-SPEC-0001\n"
    )
    candidate = (
        "depends_on:\n"
        "- SG-SPEC-0001\n"
        "last_reconciliation:\n"
        "  changed_spec_ids:\n"
        "    - SG-SPEC-0001\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate, original)

    assert repaired.splitlines()[-1] == "    - SG-SPEC-0001"


def test_repair_candidate_yaml_text_keeps_sequence_siblings_under_same_key(
    supervisor_module: object,
) -> None:
    original = "runtime:\n  changed_spec_ids:\n  - SG-SPEC-0001\n- SG-SPEC-0023\n"
    candidate = "runtime:\n  changed_spec_ids:\n    - SG-SPEC-0001\n- SG-SPEC-0023\n"

    repaired = supervisor_module.repair_candidate_yaml_text(candidate, original)

    assert repaired.splitlines()[3] == "    - SG-SPEC-0023"


def test_repair_candidate_yaml_text_strips_patch_markers(
    supervisor_module: object,
) -> None:
    candidate = (
        "specification:\n"
        "  objective: Keep the downstream proposal/split gateway-edge contract non-bypass.\n"
        "*** Begin Patch\n"
        "  scope:\n"
        "    in:\n"
        "    - Gateway-edge topology only.\n"
    )

    repaired = supervisor_module.repair_candidate_yaml_text(candidate)

    assert "*** Begin Patch" not in repaired
    parsed = supervisor_module.get_yaml_module().safe_load(repaired)
    assert parsed["specification"]["scope"]["in"] == ["Gateway-edge topology only."]


def test_repair_worktree_changed_spec_yaml_skips_valid_candidate(
    supervisor_module: object,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo_spec = repo_root / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    worktree_spec = worktree / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    repo_spec.parent.mkdir(parents=True)
    worktree_spec.parent.mkdir(parents=True)

    original_text = "specification:\n  nested:\n    key: value\n"
    valid_candidate_text = "specification:\n  key: value\n"
    repo_spec.write_text(original_text, encoding="utf-8")
    worktree_spec.write_text(valid_candidate_text, encoding="utf-8")

    repaired_paths = supervisor_module.repair_worktree_changed_spec_yaml(
        repo_root=repo_root,
        worktree_path=worktree,
        changed_files=["specs/nodes/SG-SPEC-0001.yaml"],
    )

    assert repaired_paths == []
    assert worktree_spec.read_text(encoding="utf-8") == valid_candidate_text


def test_repair_worktree_changed_spec_yaml_repairs_acceptance_size_mismatch(
    supervisor_module: object,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo_spec = repo_root / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    worktree_spec = worktree / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    repo_spec.parent.mkdir(parents=True)
    worktree_spec.parent.mkdir(parents=True)

    original_text = (
        "id: SG-SPEC-0001\n"
        "acceptance:\n"
        "- First criterion.\n"
        "- Second criterion.\n"
        "acceptance_evidence:\n"
        "- criterion: First criterion.\n"
        "  evidence: First evidence.\n"
        "- criterion: Second criterion.\n"
        "  evidence: Second evidence.\n"
    )
    candidate_text = (
        "id: SG-SPEC-0001\n"
        "acceptance:\n"
        "- First criterion.\n"
        "  - Second criterion.\n"
        "acceptance_evidence:\n"
        "- criterion: First criterion.\n"
        "  evidence: First evidence.\n"
        "- criterion: Second criterion.\n"
        "  evidence: Second evidence.\n"
    )
    repo_spec.write_text(original_text, encoding="utf-8")
    worktree_spec.write_text(candidate_text, encoding="utf-8")

    repaired_paths = supervisor_module.repair_worktree_changed_spec_yaml(
        repo_root=repo_root,
        worktree_path=worktree,
        changed_files=["specs/nodes/SG-SPEC-0001.yaml"],
    )

    assert repaired_paths == ["specs/nodes/SG-SPEC-0001.yaml"]
    repaired = supervisor_module.get_yaml_module().safe_load(
        worktree_spec.read_text(encoding="utf-8")
    )
    assert repaired["acceptance"] == ["First criterion.", "Second criterion."]
    assert len(repaired["acceptance_evidence"]) == 2


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


def test_main_split_proposal_accepts_untracked_parent_directory_change(
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

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/split-proposal"),
    )

    work_item = supervisor_module.build_split_refactor_work_item(supervisor_module.load_specs()[0])
    changed_snapshots = [[], ["runs/proposals/"]]
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

    proposal_artifact = repo_fixture / work_item["proposal_artifact_relpath"]
    assert proposal_artifact.exists()
    queue_items = json.loads(
        (repo_fixture / "runs" / "proposal_queue.json").read_text(encoding="utf-8")
    )
    assert len(queue_items) == 1


def test_main_split_proposal_passes_operator_target_to_executor(
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

    captured: dict[str, object] = {}

    def fake_invoke_executor(
        executor: object,
        node: object,
        worktree_path: Path,
        refactor_work_item: dict[str, object] | None = None,
        *,
        operator_target: bool = False,
        operator_note: str = "",
        mutation_budget: tuple[str, ...] = (),
        run_authority: tuple[str, ...] = (),
        execution_profile: str | None = None,
        child_model: str | None = None,
        child_timeout_seconds: int | None = None,
        worktree_branch: str = "",
    ) -> subprocess.CompletedProcess[str]:
        _ = (executor, operator_note, mutation_budget, run_authority, execution_profile)
        captured["operator_target"] = operator_target
        captured["worktree_branch"] = worktree_branch
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

    monkeypatch.setattr(supervisor_module, "invoke_executor", fake_invoke_executor)

    exit_code = supervisor_module.main(
        executor=supervisor_module.run_codex,
        target_spec="SG-SPEC-0001",
        split_proposal=True,
    )

    assert exit_code == 0
    assert captured["operator_target"] is True
    assert captured["worktree_branch"] == "codex/sg-spec-0001/split-proposal"


def test_process_one_spec_uses_materialize_profile_for_seed_like_ordinary_run(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    node_data = {
        "id": "SG-SPEC-0002",
        "title": "Root Spec",
        "kind": "spec",
        "status": "specified",
        "maturity": 0.57,
        "depends_on": [],
        "relates_to": [],
        "refines": [],
        "inputs": [],
        "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
        "allowed_paths": ["specs/nodes/*.yaml"],
        "acceptance": ["Define how the parent delegates one bounded child concern."],
        "acceptance_evidence": ["seed evidence"],
        "prompt": "This seed spec delegates one child spec when decomposition is needed.",
    }
    node_path.write_text(json.dumps(node_data), encoding="utf-8")
    node = supervisor_module.SpecNode(path=node_path, data=node_data)
    specs = [node]
    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0002/test"),
    )
    changed_snapshots = [[], []]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    captured: dict[str, object] = {}

    def fake_invoke_executor(
        executor: object,
        node: object,
        worktree_path: Path,
        refactor_work_item: dict[str, object] | None = None,
        *,
        operator_target: bool = False,
        operator_note: str = "",
        mutation_budget: tuple[str, ...] = (),
        run_authority: tuple[str, ...] = (),
        execution_profile: str | None = None,
        child_model: str | None = None,
        child_timeout_seconds: int | None = None,
        worktree_branch: str = "",
    ) -> subprocess.CompletedProcess[str]:
        _ = (
            executor,
            node,
            worktree_path,
            refactor_work_item,
            operator_target,
            operator_note,
            mutation_budget,
            run_authority,
            worktree_branch,
        )
        captured["execution_profile"] = execution_profile
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: blocked\nBLOCKER: none\n",
            stderr="",
        )

    monkeypatch.setattr(supervisor_module, "invoke_executor", fake_invoke_executor)

    exit_code, outcome, completion_status, gate_state = supervisor_module._process_one_spec(
        node=node,
        specs=specs,
        executor=supervisor_module.run_codex,
        auto_approve=False,
    )

    assert exit_code == 1
    assert outcome == "blocked"
    assert completion_status == supervisor_module.COMPLETION_STATUS_FAILED
    assert gate_state == "blocked"
    assert (
        captured["execution_profile"] == supervisor_module.AUTO_CHILD_MATERIALIZATION_PROFILE_NAME
    )


def test_main_targeted_root_like_run_defaults_to_20min_timeout(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["title"] = "Root Spec"
    node_data["prompt"] = "Root spec for overall project."
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_process_one_spec(
        node: object,
        specs: object,
        executor: object,
        auto_approve: bool,
        refactor_work_item: object | None = None,
        operator_target: bool = False,
        operator_note: str = "",
        mutation_budget: tuple[str, ...] = (),
        run_authority: tuple[str, ...] = (),
        execution_profile: str | None = None,
        child_model: str | None = None,
        child_timeout_seconds: int | None = None,
    ) -> tuple[int, str, str, str]:
        captured["child_timeout_seconds"] = child_timeout_seconds
        captured["child_model"] = child_model
        captured["execution_profile"] = execution_profile
        captured["operator_target"] = operator_target
        return 0, "blocked", supervisor_module.COMPLETION_STATUS_FAILED, "blocked"

    monkeypatch.setattr(supervisor_module, "_process_one_spec", fake_process_one_spec)

    exit_code = supervisor_module.main(
        target_spec="SG-SPEC-0001",
        executor=supervisor_module.run_codex,
    )
    assert exit_code == 0
    assert captured["child_timeout_seconds"] == supervisor_module.ROOT_REFACTOR_TIMEOUT_SECONDS


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


def test_main_apply_split_proposal_reuses_existing_refining_child(
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

    existing_child_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    existing_child_path.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Existing Arithmetic Child",
                "kind": "spec",
                "status": "linked",
                "maturity": 0.7,
                "depends_on": [],
                "relates_to": [],
                "refines": ["SG-SPEC-0001"],
                "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["existing acceptance"],
                "acceptance_evidence": ["existing evidence"],
                "prompt": "Preserve existing accepted child work.",
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
    assert exit_code == 0

    updated_parent = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )
    reused_child = supervisor_module.get_yaml_module().safe_load(
        existing_child_path.read_text(encoding="utf-8")
    )
    new_child = supervisor_module.get_yaml_module().safe_load(
        (repo_fixture / "specs" / "nodes" / "SG-SPEC-0003.yaml").read_text(encoding="utf-8")
    )

    assert updated_parent["depends_on"] == ["SG-SPEC-0002", "SG-SPEC-0003"]
    assert updated_parent["acceptance"] == ["criterion-1"]
    assert reused_child["prompt"] == "Preserve existing accepted child work."
    assert reused_child["acceptance"] == ["criterion-2", "criterion-3"]
    assert reused_child["acceptance_evidence"] == [
        "Retained from applied split proposal refactor_proposal::SG-SPEC-0001::oversized_spec "
        "for acceptance [2]",
        "Retained from applied split proposal refactor_proposal::SG-SPEC-0001::oversized_spec "
        "for acceptance [3]",
    ]
    assert new_child["refines"] == ["SG-SPEC-0001"]
    assert new_child["acceptance"] == ["criterion-4", "criterion-5", "criterion-6"]


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


def test_main_auto_approve_does_not_bypass_review_required_refinement(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["acceptance_evidence"] = ["initial evidence"]
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
        data["acceptance_evidence"] = ["updated evidence"]
        data["specification"] = {
            "boundary_policy": {
                "layer_separation": ["Canonical nodes remain the accepted graph of record."]
            }
        }
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
    assert updated["status"] == "outlined"
    assert updated["gate_state"] == "review_pending"
    assert updated["proposed_status"] == "specified"
    assert updated["last_refinement_acceptance"]["decision"] == "review_required"
    assert updated["last_refinement_acceptance"]["change_class"] == "constitutional_change"

    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["auto_approved"] is False
    assert payload["refinement_acceptance"]["decision"] == "review_required"


def test_main_rejects_noop_successful_refinement_run(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["acceptance_evidence"] = ["initial evidence"]
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

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

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["gate_state"] == "retry_pending"
    assert updated["required_human_action"] == (
        "repair invalid or empty refinement and rerun supervisor"
    )
    assert updated["last_refinement_acceptance"]["decision"] == "reject"
    assert updated["last_validator_results"]["refinement_acceptance"] is False
    assert any("No canonical spec change detected" in err for err in updated["last_errors"])


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


def test_main_keeps_linked_status_proposal_when_dependencies_not_review_ready(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["status"] = "linked"
    node_data["maturity"] = 0.68
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
        supervisor_module,
        "git_changed_files",
        lambda _cwd=None: changed_snapshots.pop(0),
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        root_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        root_data = supervisor_module.get_yaml_module().safe_load(
            root_node.read_text(encoding="utf-8")
        )
        root_data["depends_on"] = ["SG-SPEC-0002"]
        root_node.write_text(json.dumps(root_data), encoding="utf-8")

        child_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0002.yaml"
        child_node.write_text(
            json.dumps(
                {
                    "id": "SG-SPEC-0002",
                    "title": "Linked But Not Review Ready Child",
                    "kind": "spec",
                    "status": "linked",
                    "maturity": 0.5,
                    "depends_on": [],
                    "relates_to": [],
                    "refines": ["SG-SPEC-0001"],
                    "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                    "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                    "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                    "acceptance": ["Defines a linked but not reviewed child"],
                    "acceptance_evidence": [
                        {
                            "criterion": "Defines a linked but not reviewed child",
                            "evidence": "The child is linked but not reviewed or frozen.",
                        }
                    ],
                    "prompt": "Refine one linked child.",
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

    exit_code = supervisor_module.main(executor=fake_executor, target_spec="SG-SPEC-0001")
    assert exit_code == 0

    updated_root = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )
    assert updated_root["status"] == "linked"
    assert updated_root["proposed_status"] == "linked"
    assert updated_root["gate_state"] == "review_pending"
    assert updated_root["last_reconciliation"]["work_dependencies_ready"] is False


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
    assert updated["acceptance"] != [f"criterion-{i}" for i in range(6)]
    assert updated["gate_state"] == "split_required"
    assert updated["required_human_action"] == "split spec scope before rerun"
    assert updated["last_blocker"] == "spec exceeds atomicity quality gate"
    assert updated["last_validator_results"]["atomicity"] is False
    assert updated["last_validator_results"]["refinement_acceptance"] is True
    assert updated["last_refinement_acceptance"]["decision"] == "review_required"
    assert updated["last_refinement_acceptance"]["change_class"] == "graph_refactor"
    assert any("Atomicity gate exceeded" in err for err in updated["last_errors"])
    latest_summary = (repo_fixture / "runs" / "latest-summary.md").read_text(encoding="utf-8")
    assert "- completion_status: progressed" in latest_summary
    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    payload = json.loads(run_logs[-1].read_text(encoding="utf-8"))
    assert payload["completion_status"] == "progressed"
    assert payload["outcome"] == "split_required"
    assert payload["gate_state"] == "split_required"
    assert payload["changed_files"] == ["specs/nodes/SG-SPEC-0001.yaml"]
    assert payload["validator_results"]["atomicity"] is False


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


def test_main_split_required_sync_preserves_source_lifecycle_fields(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    node_data["status"] = "linked"
    node_data["maturity"] = 0.4
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

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0001.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(
            worktree_node.read_text(encoding="utf-8")
        )
        data["status"] = "reviewed"
        data["maturity"] = 0.99
        data.setdefault("specification", {})["objective"] = "Refined objective."
        worktree_node.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: split_required\nBLOCKER: split remains required\n",
            stderr="",
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0001",
        operator_note="Exercise productive split sync without lifecycle drift.",
    )
    assert exit_code == 1

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "linked"
    assert updated["maturity"] == 0.4
    assert updated["gate_state"] == "split_required"
    assert updated["required_human_action"] == "split spec scope before rerun"
    assert updated["specification"]["objective"] == "Refined objective."


def test_main_targeted_non_root_run_materializes_one_child_spec(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs_dir = repo_fixture / "specs" / "nodes"
    parent_path = specs_dir / "SG-SPEC-0002.yaml"
    parent_data = {
        "id": "SG-SPEC-0002",
        "title": "Vocabulary Parent",
        "kind": "spec",
        "status": "specified",
        "maturity": 0.4,
        "depends_on": [],
        "relates_to": [],
        "refines": ["SG-SPEC-0001"],
        "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
        "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
        "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
        "acceptance": ["Delegate one bounded child vocabulary slice."],
        "acceptance_evidence": ["Parent evidence."],
        "prompt": "Materialize one bounded child from this parent delegation boundary.",
    }
    parent_path.write_text(supervisor_module.dump_yaml_text(parent_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0002/test"),
    )

    changed_snapshots = [
        [],
        ["specs/nodes/SG-SPEC-0002.yaml", "specs/nodes/SG-SPEC-0003.yaml"],
    ]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        assert node.id == "SG-SPEC-0002"
        parent_file = worktree_path / "specs" / "nodes" / "SG-SPEC-0002.yaml"
        parent = supervisor_module.get_yaml_module().safe_load(
            parent_file.read_text(encoding="utf-8")
        )
        parent["depends_on"] = ["SG-SPEC-0003"]
        parent["acceptance_evidence"] = ["Parent now delegates a concrete child slice."]
        parent_file.write_text(supervisor_module.dump_yaml_text(parent), encoding="utf-8")

        child_file = worktree_path / "specs" / "nodes" / "SG-SPEC-0003.yaml"
        child_file.write_text(
            supervisor_module.dump_yaml_text(
                {
                    "id": "SG-SPEC-0003",
                    "title": "Bootstrap Relation Vocabulary",
                    "kind": "spec",
                    "status": "outlined",
                    "maturity": 0.2,
                    "depends_on": [],
                    "relates_to": [],
                    "refines": ["SG-SPEC-0002"],
                    "inputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                    "outputs": [
                        "specs/nodes/SG-SPEC-0002.yaml",
                        "specs/nodes/SG-SPEC-0003.yaml",
                    ],
                    "allowed_paths": [
                        "specs/nodes/SG-SPEC-0002.yaml",
                        "specs/nodes/SG-SPEC-0003.yaml",
                    ],
                    "acceptance": ["Define the first bootstrap relation vocabulary slice."],
                    "prompt": "Specify one bounded bootstrap relation vocabulary child.",
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

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0002",
        operator_note="Create one new child spec for the delegated bootstrap relation vocabulary.",
        run_authority=(supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,),
    )

    assert exit_code == 0

    updated_parent = supervisor_module.get_yaml_module().safe_load(
        parent_path.read_text(encoding="utf-8")
    )
    child = supervisor_module.get_yaml_module().safe_load(
        (specs_dir / "SG-SPEC-0003.yaml").read_text(encoding="utf-8")
    )

    assert updated_parent["depends_on"] == ["SG-SPEC-0003"]
    assert updated_parent["outputs"] == ["specs/nodes/SG-SPEC-0002.yaml"]
    assert updated_parent["allowed_paths"] == ["specs/nodes/SG-SPEC-0002.yaml"]
    assert child["refines"] == ["SG-SPEC-0002"]
    assert child["title"] == "Bootstrap Relation Vocabulary"
    assert child["outputs"] == ["specs/nodes/SG-SPEC-0003.yaml"]
    assert child["allowed_paths"] == ["specs/nodes/SG-SPEC-0003.yaml"]


def test_main_targeted_child_materialization_run_blocks_when_no_child_is_produced(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs_dir = repo_fixture / "specs" / "nodes"
    parent_path = specs_dir / "SG-SPEC-0002.yaml"
    parent_path.write_text(
        supervisor_module.dump_yaml_text(
            {
                "id": "SG-SPEC-0002",
                "title": "Vocabulary Parent",
                "kind": "spec",
                "status": "specified",
                "maturity": 0.4,
                "depends_on": [],
                "relates_to": [],
                "refines": ["SG-SPEC-0001"],
                "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["Delegate one bounded child vocabulary slice."],
                "acceptance_evidence": ["Parent evidence."],
                "prompt": "Materialize one bounded child from this parent delegation boundary.",
            }
        ),
        encoding="utf-8",
    )

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0002/test"),
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

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0002",
        operator_note="Create one new child spec for the delegated bootstrap relation vocabulary.",
        run_authority=(supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,),
    )

    assert exit_code == 1

    updated_parent = supervisor_module.get_yaml_module().safe_load(
        parent_path.read_text(encoding="utf-8")
    )
    assert "gate_state" not in updated_parent
    assert "last_blocker" not in updated_parent
    assert "last_run_id" not in updated_parent
    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["gate_state"] == "blocked"
    assert payload["blocker"] == "child materialization requested but no child spec was produced"
    assert any(
        "Explicit child materialization was requested but no new child spec file was produced"
        in error
        for error in payload["validation_errors"]
    )
    assert payload["completion_status"] == "failed"


def test_main_targeted_child_materialization_split_required_does_not_count_as_progress(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs_dir = repo_fixture / "specs" / "nodes"
    parent_path = specs_dir / "SG-SPEC-0002.yaml"
    parent_path.write_text(
        supervisor_module.dump_yaml_text(
            {
                "id": "SG-SPEC-0002",
                "title": "Vocabulary Parent",
                "kind": "spec",
                "status": "specified",
                "maturity": 0.4,
                "depends_on": [],
                "relates_to": [],
                "refines": ["SG-SPEC-0001"],
                "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["Delegate one bounded child vocabulary slice."],
                "acceptance_evidence": ["Parent evidence."],
                "prompt": "Materialize one bounded child from this parent delegation boundary.",
            }
        ),
        encoding="utf-8",
    )

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0002/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0002.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_parent = worktree_path / "specs" / "nodes" / "SG-SPEC-0002.yaml"
        data = supervisor_module.get_yaml_module().safe_load(
            worktree_parent.read_text(encoding="utf-8")
        )
        data["acceptance"] = [f"criterion-{i}" for i in range(6)]
        data["acceptance_evidence"] = [f"evidence-{i}" for i in range(6)]
        worktree_parent.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout=(
                "RUN_OUTCOME: split_required\nBLOCKER: parent still needs another narrowing pass\n"
            ),
            stderr="",
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0002",
        operator_note="Create one new child spec for the delegated bootstrap relation vocabulary.",
        run_authority=(supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,),
    )

    assert exit_code == 1

    latest_summary = (repo_fixture / "runs" / "latest-summary.md").read_text(encoding="utf-8")
    assert "- completion_status: failed" in latest_summary
    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    payload = json.loads(run_logs[-1].read_text(encoding="utf-8"))
    assert payload["completion_status"] == "failed"
    assert payload["gate_state"] == "split_required"
    assert any(
        "Explicit child materialization was requested but no new child spec file was produced"
        in error
        for error in payload["validation_errors"]
    )


def test_main_targeted_child_materialization_blocks_without_run_authority(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    specs_dir = repo_fixture / "specs" / "nodes"
    parent_path = specs_dir / "SG-SPEC-0002.yaml"
    parent_path.write_text(
        supervisor_module.dump_yaml_text(
            {
                "id": "SG-SPEC-0002",
                "title": "Vocabulary Parent",
                "kind": "spec",
                "status": "specified",
                "maturity": 0.4,
                "depends_on": [],
                "relates_to": [],
                "refines": ["SG-SPEC-0001"],
                "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["Delegate one bounded child vocabulary slice."],
                "acceptance_evidence": ["Parent evidence."],
                "prompt": "Materialize one bounded child from this parent delegation boundary.",
            }
        ),
        encoding="utf-8",
    )

    def fake_executor(_node: object, _worktree_path: Path) -> subprocess.CompletedProcess[str]:
        raise AssertionError("executor should not run when child materialization lacks authority")

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0002",
        operator_note="Create one new child spec for the delegated bootstrap relation vocabulary.",
    )

    assert exit_code == 1
    updated_parent = supervisor_module.get_yaml_module().safe_load(
        parent_path.read_text(encoding="utf-8")
    )
    assert "gate_state" not in updated_parent
    assert "last_run_id" not in updated_parent


def test_main_split_required_preserves_source_spec_refinement(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    spec_data = {
        "id": "SG-SPEC-0002",
        "title": "Proposal Handle Slice",
        "kind": "spec",
        "status": "specified",
        "maturity": 0.4,
        "depends_on": [],
        "relates_to": [],
        "refines": ["SG-SPEC-0001"],
        "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
        "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
        "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
        "acceptance": [
            "Criterion 1",
            "Criterion 2",
            "Criterion 3",
            "Criterion 4",
            "Criterion 5",
            "Criterion 6",
        ],
        "acceptance_evidence": [
            "Evidence 1",
            "Evidence 2",
            "Evidence 3",
            "Evidence 4",
            "Evidence 5",
            "Evidence 6",
        ],
        "prompt": "Initial prompt.",
    }
    spec_path.write_text(supervisor_module.dump_yaml_text(spec_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0002/test"),
    )

    changed_snapshots = [[], ["specs/nodes/SG-SPEC-0002.yaml"]]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        worktree_node = worktree_path / "specs" / "nodes" / "SG-SPEC-0002.yaml"
        data = supervisor_module.get_yaml_module().safe_load(
            worktree_node.read_text(encoding="utf-8")
        )
        data["prompt"] = "Refined prompt while node remains oversized."
        data["acceptance_evidence"] = [
            "Updated evidence 1",
            "Updated evidence 2",
            "Updated evidence 3",
            "Updated evidence 4",
            "Updated evidence 5",
            "Updated evidence 6",
        ]
        worktree_node.write_text(supervisor_module.dump_yaml_text(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: split_required\nBLOCKER: node still exceeds atomicity gate\n",
            stderr="",
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0002",
        operator_note="Preserve this refinement even if the node still needs splitting.",
    )

    assert exit_code == 1
    updated = supervisor_module.get_yaml_module().safe_load(spec_path.read_text(encoding="utf-8"))
    assert updated["gate_state"] == "split_required"
    assert updated["prompt"] == "Refined prompt while node remains oversized."
    assert updated["acceptance_evidence"] == [
        "Updated evidence 1",
        "Updated evidence 2",
        "Updated evidence 3",
        "Updated evidence 4",
        "Updated evidence 5",
        "Updated evidence 6",
    ]


def test_loop_counts_split_required_progress_separately(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
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

    exit_code = supervisor_module.main(
        executor=fake_executor, loop=True, max_iterations=1, auto_approve=True
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "progressed with outcome=split_required, gate_state=split_required" in out
    assert "Loop summary: 0 succeeded, 1 progressed, 0 failed" in out


def test_resolve_gate_approve_accepts_staged_worktree_changes(
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
    data["prompt"] = "Approved from worktree"
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


def test_resolve_gate_approve_rejects_stale_worktree_candidate(
    supervisor_module: object,
    repo_fixture: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    worktree = make_fake_worktree(repo_fixture)
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    worktree_node_path = worktree / "specs" / "nodes" / "SG-SPEC-0001.yaml"

    worktree_data = supervisor_module.get_yaml_module().safe_load(
        worktree_node_path.read_text(encoding="utf-8")
    )
    worktree_data["prompt"] = "Stale candidate"
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
    assert exit_code == 1

    err = capsys.readouterr().err
    assert "review gate is stale" in err
    assert "prompt" in err

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "outlined"
    assert updated["gate_state"] == "review_pending"
    assert updated["prompt"] == "Refine this node."
    assert "last_gate_decision" not in updated


def test_resolve_gate_approve_rejects_stale_additional_spec_candidate(
    supervisor_module: object,
    repo_fixture: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    child_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    child_path.write_text(
        json.dumps(
            {
                "id": "SG-SPEC-0002",
                "title": "Child Spec",
                "kind": "spec",
                "status": "specified",
                "maturity": 0.5,
                "depends_on": [],
                "relates_to": [],
                "refines": ["SG-SPEC-0001"],
                "inputs": [],
                "outputs": ["specs/nodes/SG-SPEC-0002.yaml"],
                "allowed_paths": ["specs/nodes/SG-SPEC-0002.yaml"],
                "acceptance": ["kept"],
                "acceptance_evidence": ["kept evidence"],
                "prompt": "Current child prompt",
            }
        ),
        encoding="utf-8",
    )

    worktree = make_fake_worktree(repo_fixture)
    worktree_child_path = worktree / "specs" / "nodes" / "SG-SPEC-0002.yaml"
    worktree_child_data = supervisor_module.get_yaml_module().safe_load(
        worktree_child_path.read_text(encoding="utf-8")
    )
    worktree_child_data["prompt"] = "Stale child prompt"
    worktree_child_path.write_text(json.dumps(worktree_child_data), encoding="utf-8")

    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["allowed_paths"] = ["specs/nodes/*.yaml"]
    data["gate_state"] = "review_pending"
    data["proposed_status"] = "specified"
    data["proposed_maturity"] = 0.4
    data["last_worktree_path"] = worktree.as_posix()
    data["last_changed_files"] = [
        "specs/nodes/SG-SPEC-0001.yaml",
        "specs/nodes/SG-SPEC-0002.yaml",
    ]
    node_path.write_text(json.dumps(data), encoding="utf-8")

    exit_code = supervisor_module.main(
        resolve_gate="SG-SPEC-0001",
        decision="approve",
        note="looks good",
    )
    assert exit_code == 1

    err = capsys.readouterr().err
    assert "review gate is stale" in err
    assert "specs/nodes/SG-SPEC-0002.yaml:prompt" in err

    updated_child = supervisor_module.get_yaml_module().safe_load(
        child_path.read_text(encoding="utf-8")
    )
    updated_parent = supervisor_module.get_yaml_module().safe_load(
        node_path.read_text(encoding="utf-8")
    )
    assert updated_child["prompt"] == "Current child prompt"
    assert updated_parent["gate_state"] == "review_pending"


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
    node_data["prompt"] = "Gate approved unrestricted sync"
    node_path.write_text(json.dumps(node_data), encoding="utf-8")

    exit_code = supervisor_module.main(
        resolve_gate="SG-SPEC-0001",
        decision="approve",
    )
    assert exit_code == 0

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["prompt"] == "Gate approved unrestricted sync"


def test_resolve_gate_approve_clears_review_when_status_already_applied(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["status"] = "linked"
    data["maturity"] = 0.72
    data["gate_state"] = "review_pending"
    data["proposed_status"] = None
    data["proposed_maturity"] = None
    node_path.write_text(json.dumps(data), encoding="utf-8")

    exit_code = supervisor_module.main(
        resolve_gate="SG-SPEC-0001",
        decision="approve",
        note="status was already applied by graph_refactor sync",
    )
    assert exit_code == 0

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "linked"
    assert updated["maturity"] == 0.72
    assert updated["gate_state"] == "none"
    assert updated["required_human_action"] == "-"
    assert updated["last_gate_decision"] == "approve"


def test_resolve_gate_approve_clears_review_when_proposed_status_already_current(
    supervisor_module: object,
    repo_fixture: Path,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    data["status"] = "linked"
    data["maturity"] = 0.72
    data["gate_state"] = "review_pending"
    data["proposed_status"] = "linked"
    data["proposed_maturity"] = 0.77
    node_path.write_text(json.dumps(data), encoding="utf-8")

    exit_code = supervisor_module.main(
        resolve_gate="SG-SPEC-0001",
        decision="approve",
        note="status was already applied by accepted worktree sync",
    )
    assert exit_code == 0

    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["status"] == "linked"
    assert updated["maturity"] == 0.77
    assert updated["gate_state"] == "none"
    assert updated["proposed_status"] is None
    assert updated["last_gate_decision"] == "approve"


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
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    before_text = node_path.read_text(encoding="utf-8")
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

    assert node_path.read_text(encoding="utf-8") == before_text
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert "last_errors" not in updated
    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    assert len(run_logs) == 1
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["completion_status"] == "failed"
    assert payload["outcome"] == "split_required"
    assert payload["gate_state"] == "split_required"
    assert payload["changed_files"] == ["specs/nodes/SG-SPEC-0001.yaml"]
    assert any(
        "Failed to load worktree specs for validation:" in error
        for error in payload["validation_errors"]
    )


def test_main_repairs_recoverable_worktree_yaml_indentation(
    supervisor_module: object,
    repo_fixture: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    node_data = {
        "id": "SG-SPEC-0001",
        "kind": "spec",
        "title": "Recoverable YAML Node",
        "status": "linked",
        "maturity": 0.4,
        "depends_on": [],
        "relates_to": [],
        "refines": [],
        "inputs": ["specs/nodes/SG-SPEC-0001.yaml"],
        "outputs": ["specs/nodes/SG-SPEC-0001.yaml"],
        "allowed_paths": ["specs/nodes/SG-SPEC-0001.yaml"],
        "acceptance": ["Criterion 1"],
        "acceptance_evidence": ["Evidence 1"],
        "prompt": "Initial prompt.",
        "specification": {
            "graph_health_signal_policy": {
                "initial_signals": ["oversized_spec"],
                "semantics": ["Signal presence is diagnostic only."],
            }
        },
    }
    node_path.write_text(supervisor_module.dump_yaml_text(node_data), encoding="utf-8")

    worktree = make_fake_worktree(repo_fixture)
    monkeypatch.setattr(
        supervisor_module,
        "create_isolated_worktree",
        lambda _node_id: (worktree, "codex/sg-spec-0001/test"),
    )

    changed_snapshots = [
        [],
        ["specs/nodes/SG-SPEC-0001.yaml"],
        ["specs/nodes/SG-SPEC-0001.yaml"],
    ]
    monkeypatch.setattr(
        supervisor_module, "git_changed_files", lambda _cwd=None: changed_snapshots.pop(0)
    )

    def fake_executor(_node: object, worktree_path: Path) -> subprocess.CompletedProcess[str]:
        node_path = worktree_path / "specs" / "nodes" / "SG-SPEC-0001.yaml"
        data = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
        data["prompt"] = "Updated by recoverable YAML repair path."
        broken_text = supervisor_module.dump_yaml_text(data).replace(
            "\n    initial_signals:",
            "\n  initial_signals:",
            1,
        )
        node_path.write_text(broken_text, encoding="utf-8")
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    exit_code = supervisor_module.main(
        executor=fake_executor,
        target_spec="SG-SPEC-0001",
    )

    assert exit_code == 0
    node_path = repo_fixture / "specs" / "nodes" / "SG-SPEC-0001.yaml"
    updated = supervisor_module.get_yaml_module().safe_load(node_path.read_text(encoding="utf-8"))
    assert updated["prompt"] == "Updated by recoverable YAML repair path."
    assert updated["gate_state"] == "review_pending"
    run_logs = sorted((repo_fixture / "runs").glob("*-SG-SPEC-*.json"))
    payload = json.loads(run_logs[0].read_text(encoding="utf-8"))
    assert payload["completion_status"] == "ok"
    assert payload["yaml_repair_paths"] == ["specs/nodes/SG-SPEC-0001.yaml"]


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
    """Return a fake executor that makes a bounded canonical refinement each run."""

    def fake_executor(
        node: object,
        worktree_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        node_file = worktree_path / "specs" / "nodes" / f"{node.id}.yaml"
        data = supervisor_module.get_yaml_module().safe_load(node_file.read_text(encoding="utf-8"))
        acceptance = data.get("acceptance", [])
        data["acceptance_evidence"] = [f"evidence-{i}" for i in range(len(acceptance))]
        data["prompt"] = f"Refined at status {data.get('status', 'unknown')}."
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

    spec_yaml_path = Path(__file__).resolve().parents[1] / "tools" / "spec_yaml.py"
    spec_yaml_spec = importlib.util.spec_from_file_location(
        "test_spec_yaml_module_loop",
        spec_yaml_path,
    )
    assert spec_yaml_spec and spec_yaml_spec.loader
    spec_yaml_module = importlib.util.module_from_spec(spec_yaml_spec)
    sys.modules[spec_yaml_spec.name] = spec_yaml_module
    spec_yaml_spec.loader.exec_module(spec_yaml_module)
    updated_text = node_path.read_text(encoding="utf-8")
    assert updated_text == spec_yaml_module.canonicalize_text(updated_text)


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
    last_node_id: dict[str, str] = {"value": "SG-SPEC-0001"}

    def alternating_git_changed(_cwd: object = None) -> list[str]:
        call_counter[0] += 1
        # Even calls (after executor) report the changed file.
        if call_counter[0] % 2 == 0:
            return [f"specs/nodes/{last_node_id['value']}.yaml"]
        return []

    monkeypatch.setattr(supervisor_module, "git_changed_files", alternating_git_changed)

    def per_node_executor(
        node: object,
        worktree_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        last_node_id["value"] = node.id
        node_file = worktree_path / "specs" / "nodes" / f"{node.id}.yaml"
        if node_file.exists():
            data = supervisor_module.get_yaml_module().safe_load(
                node_file.read_text(encoding="utf-8")
            )
            acceptance = data.get("acceptance", [])
            data["acceptance_evidence"] = [f"ev-{i}" for i in range(len(acceptance))]
            data["prompt"] = f"Refined {node.id} at status {data.get('status', 'unknown')}."
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
    last_node_id: dict[str, str] = {"value": "SG-SPEC-0001"}

    def alternating_git_changed(_cwd: object = None) -> list[str]:
        call_counter[0] += 1
        if call_counter[0] % 2 == 0:
            return [f"specs/nodes/{last_node_id['value']}.yaml"]
        return []

    monkeypatch.setattr(supervisor_module, "git_changed_files", alternating_git_changed)

    def mixed_executor(
        node: object,
        worktree_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        last_node_id["value"] = node.id
        # Only write to the current node's file to avoid cross-spec allowed_paths issues.
        node_file = worktree_path / "specs" / "nodes" / f"{node.id}.yaml"
        if node_file.exists():
            data = supervisor_module.get_yaml_module().safe_load(
                node_file.read_text(encoding="utf-8")
            )
            acceptance = data.get("acceptance", [])
            data["acceptance_evidence"] = [f"ev-{i}" for i in range(len(acceptance))]
            data["prompt"] = f"Refined {node.id} at status {data.get('status', 'unknown')}."
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
