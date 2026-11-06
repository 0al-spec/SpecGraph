"""Synthetic retained runs exercise the registered criterion provider."""

# ruff: noqa: E402 -- Repository CLI packages live outside the installed package.

import json
import os
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from criterion_observation_report import report_payload
from traceability.criterion import CriterionSelection, FilePin
from traceability.criterion_inputs import PROFILE, sha256
from traceability.criterion_passport import NativePassportValidation
from traceability.criterion_provider import PROVIDER_ID, RetainedCriterionEvidenceProvider
from traceability.evidence import EvidenceRequest, EvidenceScope
from traceability.providers import EvidenceRegistry

SPEC = "specs/nodes/TEST-SPEC-0001.yaml"
FEATURE = "features/parcel.feature"
TEXT = ("Посылка попадает в ячейку.", "Ячейка закрывается.", "Код выдаётся один раз.")
EXPECTED = [{"count": 1}, {"state": "closed"}, {"issued": True}, {"reissued": False}]


def json_bytes(document):
    return json.dumps(document, ensure_ascii=False).encode()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args]).decode().strip()


def commit(root, message):
    git(root, "add", ".")
    git(root, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD")


def native_validator():
    binary = os.environ.get("SPECGRAPH_TEST_FEATURE_PASSPORT")
    if not binary:
        pytest.skip("set SPECGRAPH_TEST_FEATURE_PASSPORT to a pinned native validator build")
    path = Path(binary).resolve()
    return NativePassportValidation(path, sha256(path.read_bytes()))


@dataclass(frozen=True)
class PrevalidatedFixture:
    def validate(self, raw):
        assert json.loads(raw)["artifact_kind"] == "feature_passport"
        return "0" * 64


@dataclass
class RetainedFixture:
    root: Path
    artifacts: Path
    scope: dict
    plan: dict
    passport: dict
    journal: list

    def select(self):
        passport = json_bytes(self.passport)
        (self.artifacts / "passport.json").write_bytes(passport)
        self.plan["passport_sha256"] = sha256(passport)
        journal = b"\n".join(map(json_bytes, self.journal)) + b"\n"
        (self.artifacts / "run.ndjson").write_bytes(journal)
        self.plan["journals"][0]["sha256"] = sha256(journal)
        plan = json_bytes(self.plan)
        (self.artifacts / "plan.json").write_bytes(plan)
        return CriterionSelection(
            "demo",
            FilePin(SPEC, self.scope["sha256"]),
            FilePin("passport.json", sha256(passport)),
            FilePin("plan.json", sha256(plan)),
            self.artifacts,
            (("run", FilePin("run.ndjson", sha256(journal))),),
        )

    def run(self, selection=None, validator=None):
        request = EvidenceRequest(
            self.root,
            EvidenceScope("demo/project", self.scope["revision"], ("TEST-SPEC-0001",), PROFILE),
            criterion_selection=selection or self.select(),
        )
        provider = RetainedCriterionEvidenceProvider(validator or PrevalidatedFixture())
        snapshot = EvidenceRegistry((provider,)).collect(request, (PROVIDER_ID,))
        return report_payload(snapshot)


@pytest.fixture
def retained(tmp_path):
    root, artifacts = tmp_path / "repo", tmp_path / "retained"
    root.mkdir()
    artifacts.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Synthetic Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    (root / SPEC).parent.mkdir(parents=True)
    (root / SPEC).write_text(
        "id: TEST-SPEC-0001\nstatus: specified\nacceptance:\n"
        + "".join(f"- {text}\n" for text in TEXT),
        encoding="utf-8",
    )
    spec_revision = commit(root, "Declaration")
    (root / FEATURE).parent.mkdir()
    feature = (
        "Feature: Parcel locker\n  @specgraph-id=parcel\n  Scenario: Deposit\n"
        "    Given an empty compartment\n    When a parcel arrives\n"
        "    Then a code is issued\n    And the code is issued once\n"
        "  @specgraph-id=unrelated\n  Scenario: Screen settings\n"
        "    Then the screen is bright\n"
    )
    (root / FEATURE).write_text(feature)
    test_revision = commit(root, "Test source")
    (root / "build.sh").write_text("exit 88 # Measured source must never execute\n")
    execution_revision = commit(root, "Declared execution source")

    scope = {
        "workspace": "demo",
        "repository": "demo/project",
        "node_id": "TEST-SPEC-0001",
        "revision": spec_revision,
        "path": SPEC,
        "sha256": sha256((root / SPEC).read_bytes()),
    }
    refs = [
        {
            "id": f"ref-{i}",
            "relation": "implements",
            "provider": "specgraph",
            "locator": {**scope, "pointer": f"/acceptance/{i}", "scenario_id": "parcel"},
        }
        for i in range(len(TEXT))
    ]
    anchor = {
        "repository": "demo/project",
        "revision": test_revision,
        "language": "gherkin",
        "module": "parcel",
        "path": FEATURE,
        "symbol": "Deposit",
    }
    passport = {
        "artifact_kind": "feature_passport",
        "schema_version": 1,
        "metadata": {
            "feature_id": "parcel",
            "passport_id": "fp.parcel",
            "version": "0.1.0",
            "status": "draft",
            "issuer": "synthetic",
        },
        "spec": {
            "intent": {
                "summary": "Unrelated English keywords describe a synthetic example",
                "acceptance_criteria": [
                    {"id": f"criterion-{i}", "text": text} for i, text in enumerate(TEXT)
                ],
            },
            "contract_refs": refs,
            "implementation": {
                "repositories": [{"name": "demo/project"}],
                "elements": [{"id": "test", "role": "test", "anchors": [anchor]}],
                "bindings": [
                    {
                        "id": f"binding-{i}",
                        "acceptance_criteria_ids": [f"criterion-{i}"],
                        "contract_ref_ids": [f"ref-{i}"],
                        "element_ids": ["test"],
                        "test_element_ids": ["test"],
                    }
                    for i in range(len(TEXT))
                ],
            },
            "evidence": {"required_level": "L0", "probes": []},
            "privacy": {"pii_allowed": False, "retention_days": 0, "raw_payload_storage": False},
        },
    }
    plan = {
        "artifact_kind": "criterion_observation_binding_plan",
        "schema_version": 1,
        "scope": scope.copy(),
        "profile": PROFILE,
        "passport_sha256": None,
        "journals": [
            {
                "artifact_id": "run",
                "run_id": "r1",
                "sha256": None,
                "test_source_revision": test_revision,
                "execution_source_revision": execution_revision,
                "feature": {"path": FEATURE, "sha256": sha256(feature.encode())},
            }
        ],
        "bindings": [
            {
                "pointer": f"/acceptance/{i}",
                "criterion_id": f"criterion-{i}",
                "contract_ref_id": f"ref-{i}",
                "passport_binding_id": f"binding-{i}",
                "artifact_id": "run",
                "case_id": "c1",
                "case_started_id": "c1s",
                "attempt": 0,
                "assertions": [
                    {
                        "id": f"assert-{j}",
                        "step_id": f"s{j}",
                        "media_type": "application/json",
                        "expected_measurement": EXPECTED[j],
                    }
                    for j in step_ids
                ],
            }
            for i, step_ids in enumerate(((0,), (1,), (2, 3)))
        ],
    }
    journal = [
        {"meta": {"protocolVersion": "34.2.1"}},
        {"source": {"uri": FEATURE, "data": feature}},
        {"testRunStarted": {"id": "r1"}},
        {
            "pickle": {
                "id": "p1",
                "uri": FEATURE,
                "tags": [{"name": "@specgraph-id=parcel"}],
                "steps": [{"id": f"p{i}", "text": f"Parcel step {i}"} for i in range(4)],
            }
        },
        {
            "testCase": {
                "id": "c1",
                "testRunStartedId": "r1",
                "pickleId": "p1",
                "testSteps": [{"id": f"s{i}", "pickleStepId": f"p{i}"} for i in range(4)],
            }
        },
        {"testCaseStarted": {"id": "c1s", "testCaseId": "c1", "attempt": 0}},
        *[
            {
                "testStepFinished": {
                    "testCaseStartedId": "c1s",
                    "testStepId": f"s{i}",
                    "testStepResult": {"status": "PASSED"},
                }
            }
            for i in range(4)
        ],
        *[
            {
                "attachment": {
                    "testCaseStartedId": "c1s",
                    "testStepId": f"s{i}",
                    "mediaType": "application/json",
                    "contentEncoding": "IDENTITY",
                    "body": json_bytes(measurement).decode(),
                }
            }
            for i, measurement in enumerate(EXPECTED)
        ],
        {"testCaseFinished": {"testCaseStartedId": "c1s", "willBeRetried": False}},
        {"testRunFinished": {"testRunStartedId": "r1", "success": True}},
    ]
    return RetainedFixture(root, artifacts, scope, plan, passport, journal)


def states(report):
    return [(r["binding_integrity"], r["observed_outcome"]) for r in report["criteria"]]


def test_registered_provider_projects_pinned_full_inventory(retained):
    # Dirty checkout source cannot affect the pinned inventory or test source.
    (retained.root / SPEC).write_text("id: unrelated")
    (retained.root / FEATURE).write_text("unrelated mutable checkout data")
    report = retained.run()
    assert states(report) == [("checked", "passed")] * 3
    assert report["inventory"] == {"scope": "whole_spec", "complete": True, "criterion_count": 3}
    assert report["provider"]["provider_id"] == PROVIDER_ID
    assert [r["source"]["text"] for r in report["criteria"]] == list(TEXT)
    row = report["criteria"][-1]
    assert row["source"]["pointer"] == "/acceptance/2"
    assert row["source"]["sha256"] == retained.scope["sha256"]
    assert row["bindings"][0]["case_started_id"] == "c1s"
    assert row["bindings"][0]["attempt"] == 0
    assert row["journal"]["run_id"] == "r1"
    assert row["journal"]["execution_source_provenance"] == "producer_declared"
    assert (
        len(
            {
                row["source"]["revision"],
                row["journal"]["test_source_revision"],
                row["journal"]["execution_source_revision"],
            }
        )
        == 3
    )
    assert [step["observed_measurement"] for step in row["observation"]["steps"]] == EXPECTED[2:]
    assert report["passport"]["status"] == "draft"
    assert report["receipt"] is None and report["admission"] == "not_evaluated"
    assert report["canonical_mutations_allowed"] is False
    assert "tests_verified" not in report and "runtime_verified" not in report


def test_missing_journal_keeps_every_criterion(retained):
    selection = retained.select()
    assert states(retained.run(selection)) == [("checked", "passed")] * 3
    (retained.artifacts / "run.ndjson").unlink()
    assert states(retained.run(selection)) == [("unavailable", "unavailable")] * 3


@pytest.mark.parametrize("key", ["[a, b]", "{a: b}"])
def test_unhashable_yaml_key_keeps_invalid_inventory_diagnostic(retained, key):
    raw = f"id: TEST-SPEC-0001\n? {key}\n: value\n".encode()
    (retained.root / SPEC).write_bytes(raw)
    retained.scope.update(
        revision=commit(retained.root, "Malformed YAML mapping"), sha256=sha256(raw)
    )
    report = retained.run()
    assert report["inventory"] == {
        "scope": "whole_spec",
        "complete": False,
        "criterion_count": None,
    }
    assert report["criteria"] == []
    finding = next(f for f in report["findings"] if f["code"] == "spec_input")
    assert finding["kind"] == "invalid"
    assert "invalid specification YAML" in finding["detail"]
    assert report["admission"] == "not_evaluated"


@pytest.mark.parametrize("part", ["spec", "passport", "plan", "journals"])
def test_changed_digest_cannot_validate_selected_inputs(retained, part):
    selection = retained.select()
    current = getattr(selection, part)
    value = (
        replace(current, sha256="1" * 64)
        if part != "journals"
        else (("run", replace(current[0][1], sha256="1" * 64)),)
    )
    report = retained.run(replace(selection, **{part: value}))
    assert states(report) == [("invalid", "unavailable")] * 3
    if part == "spec":
        assert report["inventory"]["complete"] is False


@pytest.mark.parametrize("kind", ["run", "case", "step", "projection", "source"])
def test_bad_joins_do_not_create_passing_observations(retained, kind):
    if kind == "run":
        retained.plan["journals"][0]["run_id"] = "foreign"
    if kind == "case":
        retained.plan["bindings"][0]["case_id"] = "foreign"
    if kind == "step":
        retained.plan["bindings"][0]["assertions"][0]["step_id"] = "foreign"
    if kind == "projection":
        retained.plan["bindings"][0]["assertions"][0]["observed_measurement"] = {"fake": True}
    if kind == "source":
        next(item["source"] for item in retained.journal if "source" in item)["data"] += "# edit"
    assert states(retained.run())[0] == ("invalid", "unavailable")


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ("PASSED", ("checked", "passed")),
        ("FAILED", ("checked", "failed")),
        ("SKIPPED", ("checked", "skipped")),
        ("PENDING", ("checked", "pending")),
        ("omit_attachment", ("unavailable", "partial")),
        ("unfinished_run", ("unavailable", "partial")),
        ("failed_run", ("checked", "partial")),
        ("retry", ("unavailable", "unavailable")),
        ("different_measurement", ("checked", "failed")),
    ],
)
def test_outcome_does_not_impersonate_binding_integrity(retained, change, expected):
    if change in {"PASSED", "FAILED", "SKIPPED", "PENDING"}:
        step = next(
            row["testStepFinished"]
            for row in retained.journal
            if row.get("testStepFinished", {}).get("testStepId") == "s3"
        )
        step["testStepResult"]["status"] = change
    if change == "omit_attachment":
        retained.journal = [
            r for r in retained.journal if r.get("attachment", {}).get("testStepId") != "s3"
        ]
    if change == "unfinished_run":
        retained.journal = [r for r in retained.journal if "testRunFinished" not in r]
    if change == "failed_run":
        retained.journal[-1]["testRunFinished"]["success"] = False
    if change == "retry":
        retained.journal.append(
            {"testCaseStarted": {"id": "c1s-retry", "testCaseId": "c1", "attempt": 1}}
        )
    if change == "different_measurement":
        attachment = next(
            r["attachment"]
            for r in retained.journal
            if r.get("attachment", {}).get("testStepId") == "s3"
        )
        attachment["body"] = '{"reissued": true}'
    assert states(retained.run())[-1] == expected


def test_unbound_and_duplicate_rows_do_not_reduce_inventory(retained):
    del retained.plan["bindings"][1]
    retained.plan["bindings"].append({**retained.plan["bindings"][0], "case_id": "other"})
    report = retained.run()
    assert states(report) == [
        ("conflict", "unavailable"),
        ("unbound", "unavailable"),
        ("checked", "passed"),
    ]
    assert report["inventory"]["criterion_count"] == 3
    assert len(report["criteria"][0]["bindings"]) == 2


def test_duplicate_and_conflicting_journal_facts_are_order_independent(retained):
    def semantic_rows(report):
        for row in report["criteria"]:
            # Raw pins change when duplicate records or their order change.
            row["journal"].pop("sha256")
        return report["criteria"]

    original = semantic_rows(retained.run())
    step = next(r for r in retained.journal if "testStepFinished" in r)
    retained.journal.append(step)
    retained.plan["bindings"].append(retained.plan["bindings"][0])
    retained.journal.reverse()
    assert semantic_rows(retained.run()) == original
    retained.journal.append(
        {"testStepFinished": {**step["testStepFinished"], "testStepResult": {"status": "FAILED"}}}
    )
    conflicting = retained.run()
    retained.journal.reverse()
    assert semantic_rows(retained.run()) == semantic_rows(conflicting)
    assert states(conflicting) == [("conflict", "unavailable")] * 3


def test_native_feature_passport_accepts_and_rejects_exact_pinned_bytes(retained):
    validator = native_validator()
    assert states(retained.run(validator=validator)) == [("checked", "passed")] * 3
    element = retained.passport["spec"]["implementation"]["elements"][0]
    element["role"] = "composition"
    result = retained.run(validator=validator)
    assert states(result) == [("invalid", "unavailable")] * 3
    assert "invalid_reference_role" in result["findings"][0]["detail"]


@pytest.mark.parametrize("malformed_spec", [False, True])
@pytest.mark.parametrize("output_format", [None, "json", "html"])
def test_cli_native_validator_and_read_only_projection(retained, malformed_spec, output_format):
    validator = native_validator()
    if malformed_spec:
        raw = b"id: TEST-SPEC-0001\n? [a, b]\n: value\n"
        (retained.root / SPEC).write_bytes(raw)
        retained.scope.update(revision=commit(retained.root, "Malformed spec"), sha256=sha256(raw))
    selection = retained.select()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/criterion_observation_report.py"),
            "--repository-root",
            str(retained.root),
            "--retained-root",
            str(retained.artifacts),
            "--repository-id",
            "demo/project",
            "--workspace",
            "demo",
            "--spec-id",
            "TEST-SPEC-0001",
            "--revision",
            retained.scope["revision"],
            "--spec",
            SPEC,
            selection.spec.sha256,
            "--passport",
            selection.passport.path,
            selection.passport.sha256,
            "--binding-plan",
            selection.plan.path,
            selection.plan.sha256,
            "--journal",
            "run",
            "run.ndjson",
            selection.journals[0][1].sha256,
            "--validator",
            str(validator.executable),
            "--validator-sha256",
            validator.executable_sha256,
        ]
        + (["--format", output_format] if output_format else []),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Traceback" not in result.stderr
    if output_format == "html":
        assert result.stdout.startswith("<!doctype html>")
        assert (
            "total criterion count unknown" in result.stdout
            if malformed_spec
            else ("Complete inventory · 3 criteria" in result.stdout)
        )
    elif malformed_spec:
        report = json.loads(result.stdout)
        assert report["inventory"]["complete"] is False
        assert report["inventory"]["criterion_count"] is None
        assert any(f["code"] == "spec_input" and f["kind"] == "invalid" for f in report["findings"])
    else:
        assert states(json.loads(result.stdout)) == [("checked", "passed")] * 3
    assert git(retained.root, "status", "--porcelain") == ""
    assert {path.name for path in retained.artifacts.iterdir()} == {
        "passport.json",
        "plan.json",
        "run.ndjson",
    }


def test_unsupported_journal_version_never_passes(retained):
    retained.journal[0]["meta"]["protocolVersion"] = "34.2.2"
    assert states(retained.run()) == [("unavailable", "unavailable")] * 3


def append_unrelated_case(retained, *, status="PASSED"):
    retained.journal.extend(
        [
            {
                "pickle": {
                    "id": "p2",
                    "uri": FEATURE,
                    "tags": [{"name": "@specgraph-id=unrelated"}],
                    "steps": [{"id": "p2-step", "text": "the screen is bright"}],
                }
            },
            {
                "testCase": {
                    "id": "c2",
                    "pickleId": "p2",
                    "testRunStartedId": "r1",
                    "testSteps": [{"id": "s-other", "pickleStepId": "p2-step"}],
                }
            },
            {"testCaseStarted": {"id": "c2s", "testCaseId": "c2", "attempt": 0}},
            {
                "testStepFinished": {
                    "testCaseStartedId": "c2s",
                    "testStepId": "s-other",
                    "testStepResult": {"status": status},
                }
            },
            {"testCaseFinished": {"testCaseStartedId": "c2s", "willBeRetried": False}},
        ]
    )


def test_explicit_case_selection_from_multi_case_run(retained):
    append_unrelated_case(retained)
    report = retained.run()
    assert states(report) == [("checked", "passed")] * 3
    assert all(
        row["observation"]["case_step_statuses"] == {f"s{i}": "PASSED" for i in range(4)}
        for row in report["criteria"]
    )


@pytest.mark.parametrize(("field", "wrong_id"), [("case_id", "c2"), ("case_started_id", "c2s")])
def test_selected_case_and_attempt_must_join_in_multi_case_run(retained, field, wrong_id):
    append_unrelated_case(retained)
    retained.plan["bindings"][0][field] = wrong_id
    assert states(retained.run()) == [
        ("invalid", "unavailable"),
        ("checked", "passed"),
        ("checked", "passed"),
    ]


def test_retry_of_selected_case_in_multi_case_run_is_unavailable(retained):
    append_unrelated_case(retained)
    retained.journal.append(
        {"testCaseStarted": {"id": "c1s-retry", "testCaseId": "c1", "attempt": 1}}
    )
    assert states(retained.run()) == [("unavailable", "unavailable")] * 3


def test_failed_unrelated_case_preserves_passed_selected_steps_and_failed_run(retained):
    append_unrelated_case(retained, status="FAILED")
    next(row["testRunFinished"] for row in retained.journal if "testRunFinished" in row)[
        "success"
    ] = False
    report = retained.run()
    assert states(report) == [("checked", "partial")] * 3
    for row in report["criteria"]:
        observation = row["observation"]
        assert observation["run_success"] is False
        assert set(observation["case_step_statuses"].values()) == {"PASSED"}
        assert all(step["producer_status"] == "PASSED" for step in observation["steps"])


def test_second_test_case_for_selected_pickle_is_ambiguous(retained):
    append_unrelated_case(retained)
    next(row["testCase"] for row in retained.journal if row.get("testCase", {}).get("id") == "c2")[
        "pickleId"
    ] = "p1"
    assert states(retained.run()) == [("conflict", "unavailable")] * 3


def test_replaced_journal_fails_raw_pin(retained):
    selection = retained.select()
    journal = retained.artifacts / "run.ndjson"
    journal.write_bytes(journal.read_bytes() + b"{}\n")
    report = retained.run(selection)
    assert states(report) == [("invalid", "unavailable")] * 3
    assert "SHA-256 mismatch" in report["criteria"][0]["findings"][0]["detail"]


def test_execution_commit_cannot_change_the_pinned_test_source(retained):
    feature = retained.root / FEATURE
    feature.write_text(feature.read_text() + "# incompatible execution source\n")
    retained.plan["journals"][0]["execution_source_revision"] = commit(retained.root, "Drift")
    report = retained.run()
    assert states(report) == [("invalid", "unavailable")] * 3
    assert "SHA-256 mismatch" in report["criteria"][0]["findings"][0]["detail"]


def test_case_finish_cannot_be_borrowed_from_unrelated_attempt(retained):
    retained.journal = [row for row in retained.journal if "testCaseFinished" not in row]
    append_unrelated_case(retained)
    report = retained.run()
    assert states(report) == [("unavailable", "partial")] * 3
    assert all(not row["observation"]["case_finished"] for row in report["criteria"])


def test_passport_locator_drift_is_visible_in_the_affected_row(retained):
    retained.passport["spec"]["contract_refs"][0]["locator"]["pointer"] = "/acceptance/2"
    assert states(retained.run()) == [
        ("invalid", "unavailable"),
        ("checked", "passed"),
        ("checked", "passed"),
    ]


def test_retained_symlink_cannot_escape_explicit_root(retained):
    selection = retained.select()
    path = retained.artifacts / "run.ndjson"
    outside = retained.artifacts.parent / "foreign.ndjson"
    path.rename(outside)
    path.symlink_to(outside)
    assert states(retained.run(selection)) == [("invalid", "unavailable")] * 3
