"""Compare PB-ALL evidence with the verifier on the same retained bundle."""

import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError

import pytest

from test_publication_digest_ontology_model import MODEL
from test_publication_digest_ontology_model import compiled_workspace as compiled_workspace
from test_publication_digest_ontology_model import compiler as compiler
from test_static_artifact_incremental_stage import MODULE, IncrementalStageError, _bundle


@pytest.fixture
def bundle_run(tmp_path):
    from build_static_artifact_bundle import PublishFile, write_checksums

    fixture = json.loads((MODEL / "all-case.json").read_bytes())
    files = {name: body.encode() for name, body in fixture["payloads"].items()}
    bundle = _bundle(tmp_path / "bundle", files)
    write_checksums(
        bundle,
        [
            PublishFile(
                path=path, root=".", size_bytes=len(body), sha256=hashlib.sha256(body).hexdigest()
            )
            for path, body in files.items()
        ],
    )
    return bundle, {
        "remoteBaseURL": fixture["remoteBaseURL"],
        "retained": {
            name: (bundle / name).read_bytes().decode()
            for name in ("artifact_manifest.json", "checksums.sha256")
        },
        "observations": [],
    }


def _verify(bundle_run, *, corrupt=None, missing=None):
    bundle, run = bundle_run
    prefix = run["remoteBaseURL"] + "/"

    def fetch(url):
        assert url.startswith(prefix)
        path = url.removeprefix(prefix)
        if path == missing:
            run["observations"].append({"url": url, "httpStatus": 404})
            raise HTTPError(url, 404, "Not Found", None, None)
        body = (bundle / path).read_bytes()
        if path == corrupt:
            body += b"!"
        run["observations"].append({"url": url, "observedSHA256": hashlib.sha256(body).hexdigest()})
        return body

    return MODULE.verify_remote_bundle(
        bundle_dir=bundle, remote_base_url=run["remoteBaseURL"], fetcher=fetch, workers=1
    )


def _assess(compiled_workspace, run):
    script = """
const { assessBundle } = require('./js/model.js');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
assessBundle(input).then(result => console.log(JSON.stringify(result))).catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
"""
    output = subprocess.check_output(
        ["node", "-e", script], input=json.dumps(run), text=True, cwd=compiled_workspace
    )
    return json.loads(output)


@pytest.mark.parametrize(
    ("corrupt", "missing", "failure"),
    [
        (None, None, None),
        ("second.txt", None, "remote artifact digest mismatch: second.txt"),
        (None, "second.txt", "remote artifact request failed for second.txt: HTTP Error 404"),
        ("artifact_manifest.json", None, "remote metadata digest mismatch: artifact_manifest.json"),
        ("checksums.sha256", None, "remote metadata digest mismatch: checksums.sha256"),
    ],
)
def test_pb_all_agrees_with_verifier(bundle_run, compiled_workspace, corrupt, missing, failure):
    _, run = bundle_run
    if failure:
        with pytest.raises(IncrementalStageError) as error:
            _verify(bundle_run, corrupt=corrupt, missing=missing)
        assert failure in str(error.value)
    else:
        report = _verify(bundle_run)
        assert report["status"] == "verified"
        assert report["summary"] == {
            "verified_file_count": 2,
            "verified_metadata_file_count": 2,
            "failure_count": 0,
        }

    result = _assess(compiled_workspace, run)
    assert result["status"] == ("failed" if failure else "verified")
    assert result["failed"] == ([corrupt or missing] if failure else [])
    targets = {n["id"]: n for n in result["nodes"] if "expectedSHA256" in n}
    assert {n["path"] for n in targets.values()} == {
        "first.txt",
        "second.txt",
        "artifact_manifest.json",
        "checksums.sha256",
    }
    # Connect each observed request to its actual path and to PB-ALL.
    nodes = {n["id"]: n for n in result["nodes"]}
    assert len(nodes) == len(result["nodes"])
    edges = {(e["relation"], e["from"], e["to"]) for e in result["edges"]}
    for reading in run["observations"]:
        path = reading["url"].removeprefix(run["remoteBaseURL"] + "/")
        observation = nodes[f"request:0:{path}"]
        relation = "requestedEntry" if "httpStatus" in reading else "comparedAgainst"
        assert (f"payload:{relation}", observation["id"], f"file:{path}") in edges
        assert ("sgcore:evidenceSupportsCriterion", observation["id"], "PB-ALL") in edges
        if "httpStatus" in reading:
            assert observation["httpStatus"] == 404 and "observedSHA256" not in observation
        else:
            assert observation["observedSHA256"] == reading["observedSHA256"]
    if not failure:
        assert result["unchecked"] == []


@pytest.mark.parametrize("repeat_first", [False, True], ids=["skip-second", "count-first-twice"])
def test_pb_all_exposes_skipped_work(bundle_run, compiled_workspace, monkeypatch, repeat_first):
    # Inject a scheduling fault into this invocation. The retained manifest stays intact.
    class FaultyPool(ThreadPoolExecutor):
        def map(self, verify, entries):
            first, second = entries
            assert (first[0], second[0]) == ("first.txt", "second.txt")
            return super().map(verify, [first, first] if repeat_first else [first])

    monkeypatch.setattr(MODULE, "ThreadPoolExecutor", FaultyPool)
    report = _verify(bundle_run)
    assert report["status"] == "verified"
    assert report["summary"]["verified_file_count"] == (2 if repeat_first else 1)
    result = _assess(compiled_workspace, bundle_run[1])
    assert result["status"] == "incomplete"
    assert result["unchecked"] == ["second.txt"]
    assert result["failed"] == []
    assert all(edge["to"] != "file:second.txt" for edge in result["edges"])


@pytest.mark.parametrize("path", ["artifact_manifest.json", "checksums.sha256"])
def test_pb_all_requires_each_metadata_observation(bundle_run, compiled_workspace, path):
    _verify(bundle_run)
    _, run = bundle_run
    url = f"{run['remoteBaseURL']}/{path}"
    run["observations"] = [r for r in run["observations"] if r["url"] != url]
    result = _assess(compiled_workspace, run)
    assert result["status"] == "incomplete"
    assert result["unchecked"] == [path]


def test_pb_all_detects_removing_a_path_from_both_lists(bundle_run, compiled_workspace):
    _verify(bundle_run)
    _, run = bundle_run
    # Keep the observed remote manifest digest from the original successful request.
    manifest = json.loads(run["retained"]["artifact_manifest.json"])
    assert manifest["files"].pop()["path"] == "second.txt"
    run["retained"]["artifact_manifest.json"] = json.dumps(manifest)
    run["observations"] = [r for r in run["observations"] if not r["url"].endswith("/second.txt")]
    result = _assess(compiled_workspace, run)
    assert result["status"] == "failed"
    assert result["unchecked"] == []
    assert result["failed"] == ["artifact_manifest.json"]
