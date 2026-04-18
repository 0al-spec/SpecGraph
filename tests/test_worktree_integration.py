"""Integration tests that exercise real ``git worktree`` commands.

Unlike the unit tests in test_supervisor.py — which replace
``create_isolated_worktree`` with a lambda that copies a directory tree —
these tests let the real implementation run.  They require a working
``git`` binary on PATH and at least one commit in the repository (provided
by the ``git_repo`` fixture from conftest.py).

Coverage goals
--------------
* ``create_isolated_worktree`` actually calls ``git worktree add``.
* The resulting worktree is visible in ``git worktree list``.
* The branch created for the worktree appears in ``git branch``.
* Path / branch naming conventions match the documented format.
* Files committed to HEAD are present in the new worktree.
* RuntimeError is raised when ROOT is not a git repository.
* Two worktrees for different spec IDs coexist without conflict.
* ``git_changed_files`` reflects real git-status output.
* ``main()`` creates a real worktree even though the executor is faked.
* The worktree directory persists after ``main()`` returns (accumulation
  by design — cleanup is tracked as task #1 in tasks.md).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SPEC_ID = "SG-SPEC-0001"

# Minimal spec that passes all validators in a fresh worktree:
#   • acceptance: []   → no acceptance_evidence entries required
#   • outputs points to the spec file itself, which is committed to HEAD
#     and therefore present in every worktree
_SPEC_DATA: dict = {
    "id": _SPEC_ID,
    "title": "Integration Test Node",
    "kind": "spec",
    "status": "outlined",
    "maturity": 0.2,
    "depends_on": [],
    "relates_to": [],
    "inputs": [],
    "outputs": [f"specs/nodes/{_SPEC_ID}.yaml"],
    "allowed_paths": [f"specs/nodes/{_SPEC_ID}.yaml"],
    "acceptance": [],
    # acceptance_evidence must be a list (even empty) — validate_acceptance_evidence
    # checks isinstance(evidence, list) regardless of acceptance length.
    "acceptance_evidence": [],
    "prompt": "Refine this node.",
}


def _git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=check)


def _worktree_paths(repo: Path) -> list[str]:
    """Absolute worktree paths reported by ``git worktree list --porcelain``."""
    result = _git(["git", "worktree", "list", "--porcelain"], cwd=repo)
    return [
        line.split(maxsplit=1)[1]
        for line in result.stdout.splitlines()
        if line.startswith("worktree ")
    ]


def _local_branches(repo: Path) -> list[str]:
    result = _git(["git", "branch", "--list"], cwd=repo)
    # git branch --list prefixes the current branch with "* " and
    # worktree-checked-out branches with "+ "; strip both markers.
    return [line.strip().lstrip("+* ") for line in result.stdout.splitlines() if line.strip()]


def _remove_worktree(repo: Path, worktree_path: Path, branch: str) -> None:
    """Best-effort cleanup used in finally blocks."""
    _git(["git", "worktree", "remove", "--force", str(worktree_path)], cwd=repo, check=False)
    _git(["git", "branch", "-D", branch], cwd=repo, check=False)


def _commit_spec(repo: Path) -> Path:
    """Write _SPEC_DATA into specs/nodes/ and commit it. Returns spec file path."""
    specs_dir = repo / "specs" / "nodes"
    specs_dir.mkdir(parents=True, exist_ok=True)
    spec_file = specs_dir / f"{_SPEC_ID}.yaml"
    spec_file.write_text(json.dumps(_SPEC_DATA), encoding="utf-8")
    _git(["git", "add", "."], cwd=repo)
    _git(["git", "commit", "-m", "add spec"], cwd=repo)
    return spec_file


def _patch_supervisor(
    monkeypatch: pytest.MonkeyPatch, module: object, repo: Path
) -> dict[str, Path]:
    """Redirect all module-level path constants to *repo*."""
    specs_dir = repo / "specs" / "nodes"
    runs_dir = repo / "runs"
    agents_file = repo / "AGENTS.md"
    monkeypatch.setattr(module, "ROOT", repo)
    monkeypatch.setattr(module, "SPECS_DIR", specs_dir)
    monkeypatch.setattr(module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(module, "WORKTREES_DIR", repo / ".worktrees")
    monkeypatch.setattr(module, "AGENTS_FILE", agents_file)
    return {"specs_dir": specs_dir, "runs_dir": runs_dir, "agents_file": agents_file}


# ---------------------------------------------------------------------------
# create_isolated_worktree — real git worktree add
# ---------------------------------------------------------------------------


class TestCreateIsolatedWorktree:
    """Verify that create_isolated_worktree() actually calls git worktree add."""

    def test_worktree_directory_is_created(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The returned path must exist as a real directory after the call."""
        monkeypatch.setattr(supervisor_module, "ROOT", git_repo)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", git_repo / ".worktrees")

        worktree_path, branch = supervisor_module.create_isolated_worktree(_SPEC_ID)
        try:
            assert worktree_path.is_dir(), f"expected a directory at {worktree_path}"
        finally:
            _remove_worktree(git_repo, worktree_path, branch)

    def test_git_worktree_list_includes_new_worktree(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """git worktree list must report the newly created worktree."""
        monkeypatch.setattr(supervisor_module, "ROOT", git_repo)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", git_repo / ".worktrees")

        worktree_path, branch = supervisor_module.create_isolated_worktree(_SPEC_ID)
        try:
            listed = _worktree_paths(git_repo)
            resolved = [str(Path(p).resolve()) for p in listed]
            assert str(worktree_path.resolve()) in resolved, (
                f"worktree {worktree_path} not in `git worktree list`: {listed}"
            )
        finally:
            _remove_worktree(git_repo, worktree_path, branch)

    def test_branch_exists_in_repository(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The branch created by git worktree add must appear in git branch."""
        monkeypatch.setattr(supervisor_module, "ROOT", git_repo)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", git_repo / ".worktrees")

        worktree_path, branch = supervisor_module.create_isolated_worktree(_SPEC_ID)
        try:
            branches = _local_branches(git_repo)
            assert branch in branches, f"branch {branch!r} missing from: {branches}"
        finally:
            _remove_worktree(git_repo, worktree_path, branch)

    def test_path_naming_convention(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Worktree path: .worktrees/sg-spec-0001-<timestamp>."""
        monkeypatch.setattr(supervisor_module, "ROOT", git_repo)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", git_repo / ".worktrees")

        worktree_path, branch = supervisor_module.create_isolated_worktree(_SPEC_ID)
        try:
            assert worktree_path.parent == git_repo / ".worktrees"
            assert worktree_path.name.startswith("sg-spec-0001-"), (
                f"unexpected worktree name: {worktree_path.name}"
            )
        finally:
            _remove_worktree(git_repo, worktree_path, branch)

    def test_branch_naming_convention(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Branch name: codex/sg-spec-0001/<timestamp>."""
        monkeypatch.setattr(supervisor_module, "ROOT", git_repo)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", git_repo / ".worktrees")

        worktree_path, branch = supervisor_module.create_isolated_worktree(_SPEC_ID)
        try:
            assert branch.startswith("codex/sg-spec-0001/"), f"unexpected branch name: {branch}"
        finally:
            _remove_worktree(git_repo, worktree_path, branch)

    def test_committed_files_appear_in_worktree(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Files committed to HEAD are present in the worktree checkout."""
        _commit_spec(git_repo)
        monkeypatch.setattr(supervisor_module, "ROOT", git_repo)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", git_repo / ".worktrees")

        worktree_path, branch = supervisor_module.create_isolated_worktree(_SPEC_ID)
        try:
            spec_in_worktree = worktree_path / "specs" / "nodes" / f"{_SPEC_ID}.yaml"
            assert spec_in_worktree.is_file(), (
                f"committed spec must appear in worktree at {spec_in_worktree}"
            )
        finally:
            _remove_worktree(git_repo, worktree_path, branch)

    def test_raises_outside_git_repository(
        self,
        tmp_path: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """RuntimeError is raised when ROOT is not inside a git repository."""
        non_git = tmp_path / "no_git_here"
        non_git.mkdir()
        monkeypatch.setattr(supervisor_module, "ROOT", non_git)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", non_git / ".worktrees")

        with pytest.raises(RuntimeError):
            supervisor_module.create_isolated_worktree(_SPEC_ID)

    def test_two_worktrees_coexist(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Two worktrees for different spec IDs can coexist in the same repo."""
        monkeypatch.setattr(supervisor_module, "ROOT", git_repo)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", git_repo / ".worktrees")

        wt1, br1 = supervisor_module.create_isolated_worktree("SG-SPEC-0001")
        wt2, br2 = supervisor_module.create_isolated_worktree("SG-SPEC-0002")
        try:
            assert wt1 != wt2, "each worktree must get a unique path"
            assert br1 != br2, "each worktree must get a unique branch"
            assert wt1.is_dir()
            assert wt2.is_dir()
            listed = [str(Path(p).resolve()) for p in _worktree_paths(git_repo)]
            assert str(wt1.resolve()) in listed
            assert str(wt2.resolve()) in listed
        finally:
            for wt, br in [(wt1, br1), (wt2, br2)]:
                _remove_worktree(git_repo, wt, br)


# ---------------------------------------------------------------------------
# git_changed_files — real git status
# ---------------------------------------------------------------------------


class TestGitChangedFiles:
    """Verify git_changed_files() reads real git-status output."""

    def test_empty_on_clean_repository(self, git_repo: Path, supervisor_module: object) -> None:
        """Clean repo → empty list."""
        result = supervisor_module.git_changed_files(cwd=git_repo)
        assert result == []

    def test_detects_untracked_file(self, git_repo: Path, supervisor_module: object) -> None:
        """New untracked file appears in output."""
        (git_repo / "untracked.txt").write_text("hello", encoding="utf-8")
        result = supervisor_module.git_changed_files(cwd=git_repo)
        assert any("untracked.txt" in f for f in result), (
            f"expected 'untracked.txt' in changed files: {result}"
        )

    def test_detects_modified_tracked_file(self, git_repo: Path, supervisor_module: object) -> None:
        """Modification to a committed file is reported."""
        readme = git_repo / "README.md"
        readme.write_text("# modified\n", encoding="utf-8")
        result = supervisor_module.git_changed_files(cwd=git_repo)
        assert any("README.md" in f for f in result), (
            f"expected 'README.md' in changed files: {result}"
        )

    def test_detects_staged_file(self, git_repo: Path, supervisor_module: object) -> None:
        """Staged (indexed) file appears in output."""
        new_file = git_repo / "staged.txt"
        new_file.write_text("staged", encoding="utf-8")
        _git(["git", "add", "staged.txt"], cwd=git_repo)
        result = supervisor_module.git_changed_files(cwd=git_repo)
        assert any("staged.txt" in f for f in result), (
            f"expected 'staged.txt' in changed files: {result}"
        )

    def test_clean_after_commit(self, git_repo: Path, supervisor_module: object) -> None:
        """After committing all changes the list is empty again."""
        (git_repo / "to_commit.txt").write_text("data", encoding="utf-8")
        _git(["git", "add", "to_commit.txt"], cwd=git_repo)
        _git(["git", "commit", "-m", "add to_commit"], cwd=git_repo)
        result = supervisor_module.git_changed_files(cwd=git_repo)
        assert result == []


# ---------------------------------------------------------------------------
# main() end-to-end with real worktree
# ---------------------------------------------------------------------------


class TestMainWithRealWorktree:
    """main() must create a real git worktree even when the executor is faked."""

    def _fake_executor(self, node: object, worktree_path: Path) -> object:
        """Write one bounded spec edit and return a successful done outcome."""
        node_path = worktree_path / "specs" / "nodes" / f"{node.id}.yaml"
        data = json.loads(node_path.read_text(encoding="utf-8"))
        data["prompt"] = f"Refined in real worktree at status {data.get('status', 'unknown')}."
        data["acceptance_evidence"] = []
        node_path.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
            stderr="",
        )

    def test_main_creates_real_git_worktree(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A real worktree must be visible via git worktree list after main() runs."""
        paths = _patch_supervisor(monkeypatch, supervisor_module, git_repo)
        paths["runs_dir"].mkdir(parents=True, exist_ok=True)
        paths["agents_file"].write_text("# AGENTS\n", encoding="utf-8")
        _commit_spec(git_repo)

        worktrees_before = set(_worktree_paths(git_repo))
        ret = supervisor_module.main(executor=self._fake_executor, auto_approve=False)
        worktrees_after = set(_worktree_paths(git_repo))

        new_worktrees = worktrees_after - worktrees_before
        assert new_worktrees, "main() must have created at least one real git worktree"
        assert ret == 0

        # Cleanup
        for wt_path in new_worktrees:
            wt = Path(wt_path)
            # Recover branch name from worktree list porcelain output
            info = _git(["git", "worktree", "list", "--porcelain"], cwd=git_repo, check=False)
            branch = None
            current_wt = None
            for line in info.stdout.splitlines():
                if line.startswith("worktree "):
                    current_wt = line.split(maxsplit=1)[1]
                elif line.startswith("branch ") and current_wt == wt_path:
                    branch = line.split("refs/heads/", 1)[-1]
            _git(["git", "worktree", "remove", "--force", str(wt)], cwd=git_repo, check=False)
            if branch:
                _git(["git", "branch", "-D", branch], cwd=git_repo, check=False)

    def test_main_sets_review_pending_gate(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """gate_state must be 'review_pending' after a successful run without auto_approve."""
        paths = _patch_supervisor(monkeypatch, supervisor_module, git_repo)
        paths["runs_dir"].mkdir(parents=True, exist_ok=True)
        paths["agents_file"].write_text("# AGENTS\n", encoding="utf-8")
        _commit_spec(git_repo)

        supervisor_module.main(executor=self._fake_executor, auto_approve=False)

        specs = supervisor_module.load_specs()
        node = next((s for s in specs if s.id == _SPEC_ID), None)
        assert node is not None
        assert node.gate_state == "review_pending", (
            f"expected 'review_pending', got {node.gate_state!r}"
        )

        # Cleanup worktrees created during this test
        for wt_path in _worktree_paths(git_repo)[1:]:  # skip primary worktree
            _git(["git", "worktree", "remove", "--force", wt_path], cwd=git_repo, check=False)

    def test_main_worktree_persists_after_run(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Worktree directory must still exist after main() returns.

        Worktrees accumulate by design so humans can inspect the changes
        before approving.  (Automatic cleanup is tracked as task #1.)
        """
        paths = _patch_supervisor(monkeypatch, supervisor_module, git_repo)
        paths["runs_dir"].mkdir(parents=True, exist_ok=True)
        paths["agents_file"].write_text("# AGENTS\n", encoding="utf-8")
        _commit_spec(git_repo)

        supervisor_module.main(executor=self._fake_executor, auto_approve=False)

        worktrees_dir = git_repo / ".worktrees"
        remaining = list(worktrees_dir.iterdir()) if worktrees_dir.exists() else []
        assert remaining, (
            "worktree directory must persist after main() returns "
            "(accumulation by design — cleanup is task #1)"
        )

        # Cleanup
        for wt in remaining:
            _git(["git", "worktree", "remove", "--force", str(wt)], cwd=git_repo, check=False)

    def test_main_records_worktree_path_in_spec(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """last_worktree_path in the saved spec must point to a real directory."""
        paths = _patch_supervisor(monkeypatch, supervisor_module, git_repo)
        paths["runs_dir"].mkdir(parents=True, exist_ok=True)
        paths["agents_file"].write_text("# AGENTS\n", encoding="utf-8")
        _commit_spec(git_repo)

        supervisor_module.main(executor=self._fake_executor, auto_approve=False)

        specs = supervisor_module.load_specs()
        node = next(s for s in specs if s.id == _SPEC_ID)
        wt_path = Path(node.data.get("last_worktree_path", ""))
        assert wt_path.is_dir(), f"last_worktree_path {wt_path} must be an existing directory"

        # Cleanup
        branch = node.data.get("last_branch", "")
        _remove_worktree(git_repo, wt_path, branch)

    def test_main_materializes_child_spec_from_non_root_parent_in_real_worktree(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        paths = _patch_supervisor(monkeypatch, supervisor_module, git_repo)
        paths["runs_dir"].mkdir(parents=True, exist_ok=True)
        paths["agents_file"].write_text("# AGENTS\n", encoding="utf-8")
        _commit_spec(git_repo)

        parent_file = git_repo / "specs" / "nodes" / "SG-SPEC-0002.yaml"
        parent_file.write_text(
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
                    "allowed_paths": [
                        "specs/nodes/SG-SPEC-0002.yaml",
                        "specs/nodes/SG-SPEC-0003.yaml",
                    ],
                    "acceptance": ["Delegate one bounded child vocabulary slice."],
                    "acceptance_evidence": ["Parent evidence."],
                    "prompt": "Materialize one bounded child from this parent delegation boundary.",
                }
            ),
            encoding="utf-8",
        )
        _git(["git", "add", "."], cwd=git_repo)
        _git(["git", "commit", "-m", "add non-root parent"], cwd=git_repo)

        def fake_executor(node: object, worktree_path: Path) -> object:
            parent_path = worktree_path / "specs" / "nodes" / "SG-SPEC-0002.yaml"
            parent = json.loads(parent_path.read_text(encoding="utf-8"))
            parent["depends_on"] = ["SG-SPEC-0003"]
            parent["acceptance_evidence"] = ["Parent now delegates a concrete child slice."]
            parent_path.write_text(json.dumps(parent), encoding="utf-8")

            child_path = worktree_path / "specs" / "nodes" / "SG-SPEC-0003.yaml"
            child_path.write_text(
                json.dumps(
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
                args=[],
                returncode=0,
                stdout="RUN_OUTCOME: done\nBLOCKER: none\n",
                stderr="",
            )

        try:
            ret = supervisor_module.main(
                executor=fake_executor,
                auto_approve=False,
                target_spec="SG-SPEC-0002",
                operator_note=(
                    "Create one new child spec for the delegated bootstrap relation vocabulary."
                ),
                run_authority=(supervisor_module.RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,),
            )
            assert ret == 0

            yaml_module = supervisor_module.get_yaml_module()
            parent = yaml_module.safe_load(parent_file.read_text(encoding="utf-8"))
            assert parent["gate_state"] == "review_pending"
            assert parent["depends_on"] == []
            assert parent["outputs"] == ["specs/nodes/SG-SPEC-0002.yaml"]
            assert parent["allowed_paths"] == [
                "specs/nodes/SG-SPEC-0002.yaml",
                "specs/nodes/SG-SPEC-0003.yaml",
            ]
            assert parent["pending_sync_paths"] == [
                "specs/nodes/SG-SPEC-0002.yaml",
                "specs/nodes/SG-SPEC-0003.yaml",
            ]
            assert parent["last_materialized_child_paths"] == ["specs/nodes/SG-SPEC-0003.yaml"]
            assert not (git_repo / "specs" / "nodes" / "SG-SPEC-0003.yaml").exists()

            specs = supervisor_module.load_specs()
            node = next(spec for spec in specs if spec.id == "SG-SPEC-0002")
            wt_path = Path(node.data.get("last_worktree_path", ""))
            branch = node.data.get("last_branch", "")
            assert wt_path.is_dir()

            child = yaml_module.safe_load(
                (wt_path / "specs" / "nodes" / "SG-SPEC-0003.yaml").read_text(encoding="utf-8")
            )
            assert child["refines"] == ["SG-SPEC-0002"]
            assert child["outputs"] == [
                "specs/nodes/SG-SPEC-0002.yaml",
                "specs/nodes/SG-SPEC-0003.yaml",
            ]
            assert child["allowed_paths"] == [
                "specs/nodes/SG-SPEC-0002.yaml",
                "specs/nodes/SG-SPEC-0003.yaml",
            ]
        finally:
            specs = supervisor_module.load_specs()
            node = next((spec for spec in specs if spec.id == "SG-SPEC-0002"), None)
            if node is not None:
                wt_path = Path(node.data.get("last_worktree_path", ""))
                branch = node.data.get("last_branch", "")
                if wt_path.as_posix():
                    _remove_worktree(git_repo, wt_path, branch)


# ---------------------------------------------------------------------------
# Worktree cleanup (manual git worktree remove)
# ---------------------------------------------------------------------------


class TestWorktreeCleanup:
    """Verify that worktrees created by the supervisor can be cleanly removed."""

    def test_git_worktree_remove_deletes_directory(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After ``git worktree remove``, the directory and git reference are gone."""
        monkeypatch.setattr(supervisor_module, "ROOT", git_repo)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", git_repo / ".worktrees")

        worktree_path, branch = supervisor_module.create_isolated_worktree(_SPEC_ID)
        assert worktree_path.is_dir()

        _git(["git", "worktree", "remove", "--force", str(worktree_path)], cwd=git_repo)
        _git(["git", "branch", "-D", branch], cwd=git_repo)

        assert not worktree_path.exists(), (
            f"worktree directory must be gone after removal: {worktree_path}"
        )
        listed = _worktree_paths(git_repo)
        assert str(worktree_path.resolve()) not in [str(Path(p).resolve()) for p in listed], (
            "removed worktree must not appear in git worktree list"
        )
        assert branch not in _local_branches(git_repo), f"branch {branch!r} must be deleted"

    def test_removing_one_worktree_leaves_others_intact(
        self,
        git_repo: Path,
        supervisor_module: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Removing one worktree must not affect a sibling worktree."""
        monkeypatch.setattr(supervisor_module, "ROOT", git_repo)
        monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", git_repo / ".worktrees")

        wt1, br1 = supervisor_module.create_isolated_worktree("SG-SPEC-0001")
        wt2, br2 = supervisor_module.create_isolated_worktree("SG-SPEC-0002")

        try:
            _git(["git", "worktree", "remove", "--force", str(wt1)], cwd=git_repo)
            _git(["git", "branch", "-D", br1], cwd=git_repo)

            assert not wt1.exists(), "removed worktree must be gone"
            assert wt2.is_dir(), "sibling worktree must still exist"
            listed = [str(Path(p).resolve()) for p in _worktree_paths(git_repo)]
            assert str(wt2.resolve()) in listed
        finally:
            _remove_worktree(git_repo, wt2, br2)
