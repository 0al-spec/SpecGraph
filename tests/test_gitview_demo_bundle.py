"""Verify the checked-in, read-only GitView demo publication snapshot."""

import hashlib
import json
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1] / "demos" / "gitview"


def test_demo_bundle_manifest_and_graph_are_consistent():
    manifest = json.loads((BUNDLE / "artifact_manifest.json").read_text())
    assert manifest["safety_gate"]["status"] == "passed"
    for artifact in manifest["files"]:
        content = (BUNDLE / artifact["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
        assert b"/Volumes/" not in content
        assert b"/Users/" not in content
    candidate = json.loads((BUNDLE / "runs" / "candidate_spec_graph.json").read_text())
    assert candidate["artifact_kind"] == "gitview_demo_candidate_projection"
    assert candidate["canonical"] is False
    assert len(candidate["nodes"]) == 71
    assert len(candidate["edges"]) == 434
    assert (BUNDLE / "runs" / "gitview" / "candidate_spec_graph.json").read_bytes() == (
        BUNDLE / "runs" / "candidate_spec_graph.json"
    ).read_bytes()
