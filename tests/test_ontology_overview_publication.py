"""Replay a second ontology fragment using an existing canonical spec's roles."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from ontology_overview.export import export_overview, run_hypercode  # noqa: E402
from ontology_overview.model import OverviewError  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = Path("docs/reviews/0232_project_ontology_context/hypercode-overview/publication")
CORE = Path("ontology/packages/specgraph-core/domain-ontology-package.yaml")
SPEC = Path("specs/nodes/SG-SPEC-0071.yaml")
PRODUCTION = Path("tools/static_artifact_incremental_stage.py")
EXPECTED_HC = (
    b"Publication\n  Verification\n    AllFiles\n    Payload\n"
    b"    Manifest\n    Checksums\n    Missing\n"
)


def flatten(nodes):
    for node in nodes:
        yield node
        yield from flatten(node["children"])


def identities(ir):
    return {
        row["properties"]["role_id"]["value"]: {
            key: row["properties"][key]["value"]
            for key in ("ontology_ref", "source_type", "ontology_source", "ontology_sha256")
        }
        for row in flatten(ir["nodes"])
    }


@pytest.fixture
def tools():
    if not (os.environ.get("HYPERCODE_BIN") and os.environ.get("ONTOLOGYC_BIN")):
        pytest.skip("Real Hypercode / ontologyc publication overview compatibility check")
    return Path(os.environ["HYPERCODE_BIN"]), Path(os.environ["ONTOLOGYC_BIN"])


@pytest.fixture
def workspace(tmp_path):
    for path in (EXAMPLE / "selection.hc", EXAMPLE / "selection.hcs", CORE, SPEC, PRODUCTION):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / path).read_bytes())
    return tmp_path


def export(root, tools, output):
    hypercode, ontologyc = tools
    report = export_overview(
        root, EXAMPLE / "selection.hc", EXAMPLE / "selection.hcs", hypercode, ontologyc, output
    )
    ir = run_hypercode(hypercode, output / "context.hc", output / "context.hcs")
    return report, ir


def test_selected_role_ids_and_order_follow_the_existing_specification():
    spec = yaml.safe_load((ROOT / SPEC).read_text())
    requirement = spec["specification"]["requirement"]
    expected = f"Spec#{spec['id']}\n  Requirement#{requirement['id']}\n" + "".join(
        f"    AcceptanceCriterion#{row['id']}\n" for row in requirement["criteria"]
    )
    assert (ROOT / EXAMPLE / "selection.hc").read_text() == expected
    assert len(requirement["criteria"]) == 5
    declared = yaml.safe_load((ROOT / CORE).read_text())["spec"]
    assert {"Spec", "Requirement", "AcceptanceCriterion"} <= declared["classes"].keys()
    assert {"definesRequirement", "requirementValidatedByCriterion"} <= declared["relations"].keys()


def test_reference_export_keeps_three_levels_and_five_occurrences_of_one_type(tmp_path, tools):
    reports = []
    for name in ("first", "second"):
        output = tmp_path / name
        report, ir = export(ROOT, tools, output)
        reports.append(report)
        assert (output / "context.hc").read_bytes() == EXPECTED_HC
        rows = list(flatten(ir["nodes"]))
        assert report["roles"] == len(rows) == 7
        assert rows[0]["properties"]["role_id"]["value"] == "SG-SPEC-0071"
        assert rows[1]["properties"]["role_id"]["value"] == "SG-REQ-PUBLICATION-VERIFIED"
        criteria = rows[2:]
        assert [row["properties"]["role_id"]["value"] for row in criteria] == [
            "PB-ALL",
            "PB-PAYLOAD",
            "PB-MANIFEST",
            "PB-CHECKSUMS",
            "PB-MISSING",
        ]
        assert {row["properties"]["ontology_ref"]["value"] for row in criteria} == {
            "ontology://org.0al.specgraph.core/0.1.0/classes/AcceptanceCriterion"
        }
        assert {row["properties"]["production_symbol"]["value"] for row in criteria} == {
            "verify_remote_bundle"
        }
        assert len(ir["nodes"][0]["children"][0]["children"]) == 5
        assert report["semantic_approval"] == "not_established"
    assert reports[0] == reports[1]
    assert (tmp_path / "first/context.hcs").read_bytes() == (
        tmp_path / "second/context.hcs"
    ).read_bytes()


def test_reference_display_rename_keeps_role_and_ontology_identity(workspace, tools):
    _, before = export(workspace, tools, workspace / "before")
    hcs = workspace / EXAMPLE / "selection.hcs"
    hcs.write_text(
        hcs.read_text().replace('overview_name: "Manifest"', 'overview_name: "ManifestBytes"')
    )
    _, after = export(workspace, tools, workspace / "after")
    assert identities(before) == identities(after)
    assert (workspace / "after/context.hc").read_bytes() == EXPECTED_HC.replace(
        b"Manifest", b"ManifestBytes"
    )


def test_reference_order_follows_the_selected_tree(workspace, tools):
    hc = workspace / EXAMPLE / "selection.hc"
    hc.write_text(
        hc.read_text().replace(
            "    AcceptanceCriterion#PB-CHECKSUMS\n    AcceptanceCriterion#PB-MISSING\n",
            "    AcceptanceCriterion#PB-MISSING\n    AcceptanceCriterion#PB-CHECKSUMS\n",
        )
    )
    export(workspace, tools, workspace / "reordered")
    assert (workspace / "reordered/context.hc").read_bytes() == EXPECTED_HC.replace(
        b"    Checksums\n    Missing\n", b"    Missing\n    Checksums\n"
    )


@pytest.mark.parametrize(
    ("filename", "old", "new", "message"),
    [
        (
            "selection.hcs",
            "/classes/AcceptanceCriterion",
            "/classes/AcceptanceCriteron",
            "unknown ontology_ref",
        ),
        (
            "selection.hcs",
            "core/0.1.0/classes/AcceptanceCriterion",
            "core/9.0.0/classes/AcceptanceCriterion",
            "unknown ontology_ref",
        ),
        ("selection.hc", "#PB-PAYLOAD", "#PB-ALL", "distinct identity"),
        (
            "selection.hcs",
            'production_symbol: "verify_remote_bundle"',
            'production_symbol: "missing_function"',
            "function missing or ambiguous",
        ),
        (
            "selection.hcs",
            'overview_name: "Payload"',
            'overview_name: "Publication"',
            "overlapping role selectors",
        ),
        (
            "selection.hcs",
            "5bfa2ff40b6174def589546ab2fea2501e1f256c4f1446f36c45c7f3fffcd929",
            "0" * 64,
            "source hash mismatch",
        ),
    ],
)
def test_reference_bad_publication_mapping_is_not_published(
    workspace, tools, filename, old, new, message
):
    path = workspace / EXAMPLE / filename
    path.write_text(path.read_text().replace(old, new))
    output = workspace / "rejected"
    with pytest.raises(OverviewError, match=message):
        export(workspace, tools, output)
    assert not output.exists()
