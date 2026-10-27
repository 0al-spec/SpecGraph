"""Exercise an installed wheel from a synthetic consumer, without PYTHONPATH."""

import argparse
import hashlib
import json
import os
import re
import select
import subprocess
from email.parser import Parser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile


def observe(command: Path, python: Path, wheel: Path, project: Path, forbidden: Path) -> dict:
    project.mkdir(parents=True, exist_ok=True)
    workspace = project / "conversation_memory" / "sketches" / "synthetic"
    environment = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")

    def run(*arguments, payload=None, expected=0):
        result = subprocess.run(
            [str(command), *map(str, arguments)],
            input=None if payload is None else json.dumps(payload),
            cwd=project,
            env=environment,
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == expected, (arguments, result.returncode, result.stderr)
        return result

    def notes_hashes():
        return {
            p.relative_to(workspace).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in workspace.rglob("*")
            if p.is_file()
        }

    with ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata = Parser().parsestr(
            archive.read(next(n for n in names if n.endswith(".dist-info/METADATA"))).decode()
        )
        version = metadata["Version"]
        assert metadata["Name"] == "specgraph"
        assert not any(
            n.startswith(("conversation_memory/", "specs/", "runs/", ".git/")) for n in names
        )
        assets = {
            route: archive.read(f"specdraft_preview/static/{name}")
            for route, name in (
                ("/", "index.html"),
                ("/app.js", "app.js"),
                ("/style.css", "style.css"),
                ("/icon.svg", "icon.svg"),
            )
        }
        for name in ("SKILL.md", "references/usage.md"):
            assert archive.read(f"specgraph/resources/skills/specgraph-conversation-notes/{name}")

    probe = subprocess.check_output(
        [
            str(python),
            "-I",
            "-c",
            (
                "import json, platform, importlib.metadata as m; "
                "import specgraph.cli, conversation_notes.api, specdraft_preview.server; "
                "d=json.loads(m.distribution('specification-core')"
                ".read_text('direct_url.json') or '{}'); "
                "print(json.dumps({'version':m.version('specgraph'),'python':platform.python_version(),"
                "'dependency_commit':d.get('vcs_info',{}).get('commit_id'),"
                "'origins':{x.__name__:x.__file__ for x in "
                "(specgraph.cli,conversation_notes.api,specdraft_preview.server)}}))"
            ),
        ],
        cwd=project,
        env=environment,
        text=True,
        timeout=30,
    )
    runtime = json.loads(probe)
    assert runtime["version"] == version
    assert runtime["dependency_commit"] == "6113d773e78cb94c4eb0ce31e8439877fef45494"
    assert all(
        not Path(p).resolve().is_relative_to(forbidden.resolve())
        for p in runtime["origins"].values()
    )
    assert run("--version").stdout.strip() == f"specgraph {version}"
    initial = json.loads(run("notes", "read_notes", "--workspace", workspace).stdout)
    assert initial["revision"] is None and initial["canonical"] is False
    request = {
        "expected_revision": None,
        "source": {
            "ref": "synthetic:portable-install",
            "quote": "Synthetic installation fixture",
            "speaker": "human",
        },
        "changes": [{"op": "add", "id": "goal", "label": "Installed runtime", "parent_id": None}],
    }
    saved = json.loads(
        run("notes", "update_notes", "--workspace", workspace, payload=request).stdout
    )
    restored = json.loads(
        run("notes", "read_notes", "--workspace", workspace, "--history-limit", "2").stdout
    )
    assert saved["revision"] == restored["revision"] and restored["canonical"] is False
    assert restored["nodes"][0]["sources"][0]["quote"] == request["source"]["quote"]
    before = notes_hashes()
    stale = run("notes", "update_notes", "--workspace", workspace, payload=request, expected=2)
    assert "Revision conflict" in json.loads(stale.stderr)["error"] and notes_hashes() == before

    destination = project / ".codex" / "skills" / "specgraph-conversation-notes"
    skill = json.loads(run("skill", "install", "--destination", destination).stdout)
    assert skill["status"] == "installed" and skill["runtime_version"] == version
    assert (
        json.loads(run("skill", "install", "--destination", destination).stdout)["status"]
        == "already_installed"
    )
    for name, expected in skill["files_sha256"].items():
        path = destination / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        for reference in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            target = (path.parent / reference).resolve()
            assert target.is_relative_to(destination.resolve()) and target.is_file()

    server = subprocess.Popen(
        [str(command), "preview", "--workspace", str(workspace), "--port", "0"],
        cwd=project,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert server.stdout is not None and select.select([server.stdout], [], [], 15)[0], (
            "Preview did not report its URL"
        )
        line = server.stdout.readline()
        assert line, "Installed preview exited before startup"
        address = json.loads(line)
        assert address["canonical"] is False and address["url"].startswith("http://127.0.0.1:")
        base = address["url"].rstrip("/")
        for route, expected in assets.items():
            with urlopen(base + route, timeout=10) as response:
                assert response.status == 200 and response.read() == expected
        with urlopen(base + "/api/notes", timeout=10) as response:
            shown = json.load(response)
        assert (
            shown["display_state"] == "current"
            and shown["snapshot"]["revision"] == saved["revision"]
        )
        changed = {
            **request,
            "expected_revision": saved["revision"],
            "changes": [{"op": "revise", "id": "goal", "label": "Live installed update"}],
        }
        updated = json.loads(
            run("notes", "update_notes", "--workspace", workspace, payload=changed).stdout
        )
        with urlopen(base + "/api/notes", timeout=10) as response:
            refreshed = json.load(response)
        assert refreshed["snapshot"]["revision"] == updated["revision"]
        assert refreshed["snapshot"]["nodes"][0]["label"] == "Live installed update"
        before = notes_hashes()
        try:
            urlopen(Request(base + "/api/notes", data=b"{}", method="POST"), timeout=10)
        except HTTPError as error:
            assert error.code == 405
        else:
            raise AssertionError("Preview accepted mutation")
        assert notes_hashes() == before
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)

    return {
        "artifact_kind": "specdraft_distribution_smoke",
        "schema_version": 1,
        "status": "passed",
        "synthetic_workspace": True,
        "runtime_version": version,
        "python_version": runtime["python"],
        "dependency_commit": runtime["dependency_commit"],
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "module_origins_outside_developer_checkout": {name: True for name in runtime["origins"]},
        "checks": {
            name: "passed"
            for name in (
                "installed_cli",
                "fresh_process_recovery",
                "stale_revision_preserves_data",
                "self_contained_skill",
                "packaged_http_assets",
                "preview_observes_update",
                "preview_rejects_mutation",
            )
        },
        "browser_rendering": "not_observed",
        "canonical_acceptance": "not_evaluated",
        "admission": "not_evaluated",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("python", "command", "wheel", "project", "forbidden-source-root", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    report = observe(
        args.command, args.python, args.wheel, args.project, args.forbidden_source_root
    )
    report["build_source_revision"] = args.source_revision
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
