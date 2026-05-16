from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def bundle_module() -> object:
    module_path = Path(__file__).resolve().parents[1] / "tools" / "build_static_artifact_bundle.py"
    spec = importlib.util.spec_from_file_location("test_static_artifact_bundle_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_repo(root: Path) -> Path:
    specs_dir = root / "specs" / "nodes"
    runs_dir = root / "runs"
    specs_dir.mkdir(parents=True)
    runs_dir.mkdir(parents=True)
    (specs_dir / "SG-SPEC-0001.yaml").write_text(
        "\n".join(
            [
                "id: SG-SPEC-0001",
                "title: Root",
                "kind: spec",
                "status: linked",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for name in (
        "graph_dashboard.json",
        "graph_backlog_projection.json",
        "graph_next_moves.json",
        "implementation_work_index.json",
        "spec_activity_feed.json",
    ):
        write_json(runs_dir / name, {"artifact_kind": name.removesuffix(".json")})
    return root


def test_build_public_bundle_copies_specs_and_runs_with_manifest(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "raw_run.json",
        {"worktree_path": "/Users/egor/Development/GitHub/0AL/SpecGraph/.worktrees/x"},
    )
    (repo / "runs" / ".DS_Store").write_text("junk", encoding="utf-8")
    (repo / "runs" / ".gitkeep").write_text("", encoding="utf-8")

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
    )

    assert (result.output_dir / "specs" / "nodes" / "SG-SPEC-0001.yaml").is_file()
    assert (result.output_dir / "runs" / "graph_dashboard.json").is_file()
    assert not (result.output_dir / "runs" / ".DS_Store").exists()
    assert not (result.output_dir / "runs" / ".gitkeep").exists()
    assert "$LOCAL_PATH" in (result.output_dir / "runs" / "raw_run.json").read_text(
        encoding="utf-8"
    )
    assert "/Users/egor" not in (result.output_dir / "runs" / "raw_run.json").read_text(
        encoding="utf-8"
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifact_kind"] == "specgraph_static_artifact_manifest"
    assert manifest["published_roots"] == ["specs", "runs"]
    assert manifest["required_surfaces"]["implementation_work_index.json"] is True
    assert any(
        file_info["path"] == "runs/implementation_work_index.json"
        for file_info in manifest["files"]
    )
    assert manifest["safety_gate"]["status"] == "passed"
    assert manifest["safety_gate"]["redacted_local_path_occurrences"] == 1
    assert "artifact_manifest.json" in result.checksums_path.read_text(encoding="utf-8")
    assert "runs/implementation_work_index.json" in result.checksums_path.read_text(
        encoding="utf-8"
    )


def test_build_public_bundle_skips_symlinked_artifacts(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("do-not-publish", encoding="utf-8")
    (repo / "runs" / "linked-secret.txt").symlink_to(outside)

    linked_dir_target = tmp_path / "linked-dir-target"
    linked_dir_target.mkdir()
    (linked_dir_target / "nested.json").write_text('{"secret": true}', encoding="utf-8")
    (repo / "runs" / "linked-dir").symlink_to(linked_dir_target, target_is_directory=True)

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
    )

    assert not (result.output_dir / "runs" / "linked-secret.txt").exists()
    assert not (result.output_dir / "runs" / "linked-dir" / "nested.json").exists()
    assert "do-not-publish" not in result.checksums_path.read_text(encoding="utf-8")


def test_build_public_bundle_redacts_linux_absolute_paths(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(
        repo / "runs" / "linux_paths.json",
        {
            "runner_path": "/home/runner/work/SpecGraph/SpecGraph/runs/x.json",
            "workspace_path": "/github/workspace/runs/y.json",
            "tmp_path": "/tmp/specgraph/z.json",
        },
    )

    result = bundle_module.build_public_bundle(
        repo_root=repo,
        output_dir=repo / "dist" / "specgraph-public",
    )

    published = (result.output_dir / "runs" / "linux_paths.json").read_text(encoding="utf-8")
    assert "/home/runner" not in published
    assert "/github/workspace" not in published
    assert "/tmp/specgraph" not in published
    assert published.count("$LOCAL_PATH") == 3


def test_build_public_bundle_rejects_malformed_runs_json(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / "broken.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(bundle_module.PublishBundleError, match="malformed JSON artifact"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_rejects_secret_like_content(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    write_json(repo / "runs" / "secret.json", {"api_key": "sk-test"})

    with pytest.raises(bundle_module.PublishBundleError, match="secret-like content"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )

    assert not (repo / "dist" / "specgraph-public").exists()


def test_build_public_bundle_requires_core_viewer_surfaces(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / "graph_next_moves.json").unlink()

    with pytest.raises(bundle_module.PublishBundleError, match="missing required run surfaces"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_build_public_bundle_requires_implementation_work_surface(
    tmp_path: Path,
    bundle_module: object,
) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "runs" / "implementation_work_index.json").unlink()

    with pytest.raises(bundle_module.PublishBundleError, match="implementation_work_index"):
        bundle_module.build_public_bundle(
            repo_root=repo,
            output_dir=repo / "dist" / "specgraph-public",
        )


def test_refresh_publish_surfaces_builds_viewer_and_implementation_work(
    tmp_path: Path,
    bundle_module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_run_make_target(repo_root: Path, target: str) -> None:
        assert repo_root == tmp_path
        calls.append(target)

    monkeypatch.setattr(bundle_module, "run_make_target", fake_run_make_target)

    bundle_module.refresh_publish_surfaces(tmp_path)

    assert calls == ["viewer-surfaces", "implementation-work"]


def test_main_prints_compact_summary(
    tmp_path: Path,
    bundle_module: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = make_repo(tmp_path / "repo")

    exit_code = bundle_module.main(
        [
            "--repo-root",
            str(repo),
            "--output-dir",
            str(repo / "dist" / "specgraph-public"),
        ]
    )

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["file_count"] >= 6
    assert summary["safety_gate"]["status"] == "passed"
