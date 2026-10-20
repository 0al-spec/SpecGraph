from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from intent_decision_review.report import collect, draft, inspect_records  # noqa: E402
from intent_decision_review.sources import GitSources, encoded  # noqa: E402
from intent_decision_review_gate import main  # noqa: E402
from test_intent_atoms import git, make_repo  # noqa: E402

LEDGER = "tools/intent_decision_reviews/change.json"
BODY = f"Intent-Decision-Review: {LEDGER}\n\nKeep identity decisions explicit."
SPEC = """from specification_core import Specification
class EligibleSpec(Specification):
    def _evaluate(self, candidate, recorder):
        return candidate
"""


def write(repo, path, text):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def commit(repo, message="change"):
    git(repo, "add", ".")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


def node(text="Only matching source evidence is accepted."):
    return encoded(dict(id="SG-1", kind="spec", acceptance=[text]))


def history(tmp_path, *, initial_spec=False):
    files = {
        "README.md": "fixture",
        "tools/decision.py": "def decide(x):\n    return bool(x)\n",
        "specs/nodes/.keep": "Tracked empty specification directory.",
    }
    if initial_spec:
        files["tools/eligible_spec.py"] = SPEC
    repo = make_repo(tmp_path, files)
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "specs/nodes/SG-1.yaml", node())
    return repo, base, commit(repo)


def record(repo, base, head, disposition="mechanics"):
    review = draft(repo, base, head, LEDGER, pr_context=dict(body=BODY))
    row = review["decisions"][0]
    row.update(
        disposition=disposition,
        rationale="This function adapts a supplied Boolean value.",
        implementation_refs=[dict(path="tools/decision.py", symbol="decide")],
    )
    if disposition.endswith("specification"):
        row["specification_refs"] = [dict(path="tools/eligible_spec.py", symbol="EligibleSpec")]
    return review


def publish(repo, review):
    write(repo, LEDGER, encoded(review))
    return commit(repo, "review coverage")


def measured(repo, base, head, body=BODY):
    return collect(repo, base, head, pr_context=dict(number=12, title="Identity", body=body))


def test_pr773_exact_intent_fixture_requires_review_despite_zero_new_specs(tmp_path):
    fixture = ROOT / "tests/fixtures/intent_decision_review"
    raw = (fixture / "SG-SPEC-0071.yaml").read_bytes()
    provenance = json.loads((fixture / "provenance.json").read_text())
    assert hashlib.sha256(raw).hexdigest() == provenance["sha256"]
    repo = make_repo(tmp_path, {"README.md": "PR773 bounded fixture", "specs/nodes/.keep": ""})
    base = git(repo, "rev-parse", "HEAD")
    write(repo, "specs/nodes/SG-SPEC-0071.yaml", raw.decode())
    excerpt = (fixture / "acceptance_signal.py.txt").read_bytes()
    assert hashlib.sha256(excerpt).hexdigest() == provenance["implementation"]["excerpt_sha256"]
    write(repo, "tools/publication_delivery_evidence.py", excerpt.decode())
    head = commit(repo)
    result = collect(repo, base, head, pr_context=dict(body="Lightweight evidence adapter."))
    assert result["status"] == "needs_review"
    assert result["changed_atoms"] == 3
    assert len(result["missing_changes"]) == 3
    assert {c["atom"]["source_field"] for c in result["changes"]} == {"acceptance"}
    assert not result["semantic_approval"]


@pytest.mark.parametrize("reuse", [False, True])
def test_new_and_reused_specs_bind_actual_definitions_without_head_self_reference(tmp_path, reuse):
    repo, base, head = history(tmp_path, initial_spec=reuse)
    if not reuse:
        write(repo, "tools/eligible_spec.py", SPEC)
        head = commit(repo)
    review = record(repo, base, head, "reuse_specification" if reuse else "new_specification")
    reviewed_head = publish(repo, review)
    assert reviewed_head != head
    result = measured(repo, base, reviewed_head)
    assert result["status"] == "covered"
    assert result["review_blob_sha256"]
    assert result["decisions"][0]["specification_evidence"][0]["recognized_specification"]
    assert result["head_sha"] == reviewed_head


def test_missing_partial_duplicate_unknown_and_unresolved_dispositions(tmp_path):
    repo, base, head = history(tmp_path)
    review = draft(repo, base, head, LEDGER, pr_context=dict(body=BODY))
    head = publish(repo, review)
    assert measured(repo, base, head)["status"] == "needs_review"
    review["decisions"] = []
    head = publish(repo, review)
    assert measured(repo, base, head)["status"] == "needs_review"
    review = record(repo, base, head)
    review["decisions"] *= 2
    head = publish(repo, review)
    assert measured(repo, base, head)["status"] == "invalid"
    review["decisions"] = review["decisions"][:1]
    review["decisions"][0]["change_sha256"] = "f" * 64
    head = publish(repo, review)
    assert measured(repo, base, head)["status"] == "invalid"


def test_code_changes_and_pr_description_changes_stale_the_review(tmp_path):
    repo, base, head = history(tmp_path)
    head = publish(repo, record(repo, base, head))
    assert measured(repo, base, head)["status"] == "covered"
    assert measured(repo, base, head, body=BODY + "New purpose.")["status"] == "invalid"
    write(repo, "tools/decision.py", "def decide(x):\n    return not x\n")
    changed = commit(repo)
    assert measured(repo, base, changed)["status"] == "invalid"
    assert measured(repo, head, changed)["status"] == "not_required"


def test_net_zero_replacement_still_requires_two_dispositions(tmp_path):
    repo, _, base = history(tmp_path)
    write(repo, "specs/nodes/SG-1.yaml", node("A materially different obligation."))
    head = commit(repo)
    result = collect(repo, base, head)
    assert result["intent_summary"]["net_count_delta"] == 0
    assert result["changed_atoms"] == 2
    assert result["status"] == "needs_review"


def test_explicit_atom_modification_and_retirement_are_not_addition_counts(tmp_path):
    repo, _, base = history(tmp_path)
    write(
        repo,
        "specs/nodes/SG-1.yaml",
        encoded(
            dict(
                id="SG-1",
                kind="spec",
                atoms=dict(intents=[dict(id="rule", statement="Initial rule")]),
            )
        ),
    )
    base = commit(repo)
    write(
        repo,
        "specs/nodes/SG-1.yaml",
        encoded(
            dict(
                id="SG-1",
                kind="spec",
                atoms=dict(intents=[dict(id="rule", statement="Changed rule")]),
            )
        ),
    )
    head = commit(repo)
    assert collect(repo, base, head)["changes"][0]["kind"] == "modified"
    (repo / "specs/nodes/SG-1.yaml").unlink()
    retired = commit(repo)
    review = draft(repo, head, retired, LEDGER, pr_context=dict(body=BODY))
    review["decisions"][0].update(disposition="retired", rationale="This obligation is withdrawn.")
    assert measured(repo, head, publish(repo, review))["status"] == "covered"


@pytest.mark.parametrize(
    "attribute, value",
    [
        ("type", "policy"),
        ("scope", "publication"),
        ("premises", ["authenticated"]),
        ("verifiable_by", ["test_rule"]),
    ],
)
@pytest.mark.parametrize("remove", [False, True])
def test_declared_attribute_edits_require_review_without_changing_counter(
    tmp_path, attribute, value, remove
):
    from intent_atoms import build_snapshot, diff_snapshots

    repo, _, _ = history(tmp_path)
    atom = dict(id="rule", statement="Keep the same statement.")

    def document(with_attribute):
        item = dict(atom)
        if with_attribute:
            item[attribute] = value
        return encoded(dict(id="SG-1", kind="spec", atoms=dict(intents=[item])))

    write(repo, "specs/nodes/SG-1.yaml", document(remove))
    base = commit(repo)
    write(repo, "specs/nodes/SG-1.yaml", document(not remove))
    head = commit(repo)
    historical = diff_snapshots(
        build_snapshot(repo=str(repo), revision=base), build_snapshot(repo=str(repo), revision=head)
    )
    assert historical["modified"] == []
    result = collect(repo, base, head)
    assert result["status"] == "needs_review"
    assert result["changed_atoms"] == 1
    assert result["changes"][0]["kind"] == "modified"
    assert result["changes"][0]["atom"]["before"] != result["changes"][0]["atom"]["after"]
    review = record(repo, base, head)
    assert measured(repo, base, publish(repo, review))["status"] == "covered"


def test_reordering_explicit_atoms_does_not_modify_obligations(tmp_path):
    repo, _, _ = history(tmp_path)
    atoms = [dict(id="a", statement="First"), dict(id="b", statement="Second")]
    write(repo, "specs/nodes/SG-1.yaml", encoded(dict(id="SG-1", atoms=dict(intents=atoms))))
    base = commit(repo)
    write(repo, "specs/nodes/SG-1.yaml", encoded(dict(id="SG-1", atoms=dict(intents=atoms[::-1]))))
    assert collect(repo, base, commit(repo))["status"] == "not_required"


@pytest.mark.parametrize("failure", ["per_list", "total", "duplicate"])
def test_all_reference_bounds_are_checked_before_git_or_ast_work(failure):
    from unittest.mock import Mock

    sources = Mock()
    refs = [dict(path="tools/rule.py", symbol=f"rule{i}") for i in range(17)]
    if failure == "per_list":
        rows = [
            dict(implementation_refs=[], specification_refs=[]),
            dict(implementation_refs=refs, specification_refs=[]),
        ]
    elif failure == "total":
        rows = [dict(implementation_refs=refs[:16], specification_refs=refs[:16])] * 9
    else:
        rows = [dict(implementation_refs=refs[:1] * 2, specification_refs=[])]
    with pytest.raises(ValueError):
        inspect_records(sources, dict(decisions=rows), [])
    assert sources.mock_calls == []


def test_declaration_and_module_caches_reuse_exact_revision_reads(tmp_path):
    import intent_decision_review.sources as source_module

    repo, base, head = history(tmp_path)
    write(repo, "tools/decision.py", "def decide(x):\n    return x\ndef other():\n    return 1\n")
    head = commit(repo)
    sources = GitSources(repo, base, head)
    reference = dict(path="tools/decision.py", symbol="decide")
    with (
        patch.object(source_module, "git", wraps=source_module.git) as git_calls,
        patch.object(source_module.ast, "parse", wraps=source_module.ast.parse) as parse_calls,
    ):
        sources.declaration(reference)
        sources.declaration(reference)
        sources.declaration(dict(reference, symbol="other"))
        assert git_calls.call_count == 2
        assert parse_calls.call_count == 1
        sources.declaration(reference, ref=base)
        assert git_calls.call_count == 4
        assert parse_calls.call_count == 2


def test_false_specification_reference_and_wrong_disposition_are_rejected(tmp_path):
    repo, base, head = history(tmp_path)
    review = record(repo, base, head)
    review["decisions"][0].update(
        disposition="new_specification",
        specification_refs=[dict(path="tools/decision.py", symbol="decide")],
    )
    assert measured(repo, base, publish(repo, review))["status"] == "invalid"


@pytest.mark.parametrize("path", ["../outside.py", "/tmp/outside.py", "tools/decision.py/../x.py"])
def test_reference_paths_cannot_escape_the_repository(tmp_path, path):
    repo, base, head = history(tmp_path)
    review = record(repo, base, head)
    review["decisions"][0]["implementation_refs"][0]["path"] = path
    assert measured(repo, base, publish(repo, review))["status"] == "invalid"


def test_incomplete_intent_is_invalid_not_zero(tmp_path):
    repo, base, _ = history(tmp_path)
    write(repo, "specs/nodes/SG-1.yaml", "acceptance: [broken\n")
    result = collect(repo, base, commit(repo))
    assert result["status"] == "invalid"
    assert result["intent_completeness"] == "incomplete"


def test_missing_spec_root_cannot_pass_as_no_intent_changes(tmp_path):
    repo = make_repo(tmp_path, {"README.md": "No tracked specification root."})
    ref = git(repo, "rev-parse", "HEAD")
    result = collect(repo, ref, ref)
    assert result["changed_atoms"] == 0
    assert result["status"] == "invalid"


def test_duplicate_json_keys_and_symlink_review_records_are_rejected(tmp_path):
    repo, base, head = history(tmp_path)
    review = record(repo, base, head)
    write(repo, LEDGER, encoded(review)[:-1] + ',"schema_version":1}')
    assert measured(repo, base, commit(repo))["status"] == "invalid"
    (repo / LEDGER).unlink()
    (repo / LEDGER).symlink_to("../../../README.md")
    assert measured(repo, base, commit(repo))["status"] == "invalid"


@pytest.mark.parametrize(
    "path, content, executable",
    [
        ("tools/new_runtime.py", "def rule():\n    return True\n", False),
        ("tools/policy.bash", "echo policy\n", False),
        ("src/policy.zsh", "echo policy\n", False),
        ("tools/policy", "#!/usr/bin/env bash\necho policy\n", True),
    ],
)
def test_contract_only_cannot_bypass_changed_runtime_source(tmp_path, path, content, executable):
    repo, base, head = history(tmp_path)
    review = draft(repo, base, head, LEDGER, pr_context=dict(body=BODY))
    review["decisions"][0].update(disposition="contract_only", rationale="Future contract.")
    head = publish(repo, review)
    assert measured(repo, base, head)["status"] == "covered"
    write(repo, path, content)
    if executable:
        (repo / path).chmod(0o755)
    head = commit(repo)
    review = draft(repo, base, head, LEDGER, pr_context=dict(body=BODY))
    review["decisions"][0].update(disposition="contract_only", rationale="Future contract.")
    assert measured(repo, base, publish(repo, review))["status"] == "invalid"


def test_deleted_extensionless_shell_source_is_still_a_production_change(tmp_path):
    repo, _, _ = history(tmp_path)
    write(repo, "tools/policy", "#!/bin/sh\necho policy\n")
    (repo / "tools/policy").chmod(0o755)
    base = commit(repo)
    (repo / "tools/policy").unlink()
    head = commit(repo)
    assert GitSources(repo, base, head).production_changed()


def test_cli_event_context_is_preserved_and_no_override_is_allowed(tmp_path, capsys):
    repo, base, head = history(tmp_path)
    event = tmp_path / "event.json"
    event.write_text(
        encoded(
            dict(
                pull_request=dict(
                    base=dict(sha=base),
                    head=dict(sha=head),
                    number=773,
                    title="Pilot",
                    body=BODY,
                    html_url="https://github.com/example/project/pull/773",
                )
            )
        )
    )
    assert main(["--repo-root", str(repo), "--event-path", str(event)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["reviewer_context"]["pull_request"]["body"] == BODY
    assert main(["--event-path", str(event), "--base-ref", base]) == 2


def test_existing_blocking_quality_entrypoint_runs_the_new_gate(monkeypatch):
    import python_quality

    calls = []
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", "/tmp/event.json")
    with patch.object(python_quality, "run_step", side_effect=lambda args: calls.append(args) or 0):
        assert python_quality.main() == 0
    assert calls[-1] == [
        sys.executable,
        "tools/intent_decision_review_gate.py",
        "--event-path",
        "/tmp/event.json",
    ]
    with patch.object(
        python_quality,
        "run_step",
        side_effect=lambda args: 1 if "tools/intent_decision_review_gate.py" in args else 0,
    ):
        assert python_quality.main() == 1


def test_no_impact_claim_cannot_skip_new_intent_review(tmp_path):
    repo, base, head = history(tmp_path)
    report = collect(repo, base, head, pr_context=dict(body="Spec-ID: NO-SPEC-IMPACT"))
    assert report["status"] == "needs_review"


def test_empty_github_description_is_valid_when_no_atoms_change(tmp_path, capsys):
    repo, base, _ = history(tmp_path)
    event = tmp_path / "event.json"
    event.write_text(
        encoded(dict(pull_request=dict(base=dict(sha=base), head=dict(sha=base), body=None)))
    )
    assert main(["--repo-root", str(repo), "--event-path", str(event)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "not_required"


def test_gate_does_not_execute_referenced_source(tmp_path):
    repo, base, _ = history(tmp_path)
    write(
        repo,
        "tools/decision.py",
        "raise RuntimeError('must not execute')\ndef decide(x):\n    return x\n",
    )
    head = commit(repo)
    head = publish(repo, record(repo, base, head))
    with patch("socket.socket.connect", side_effect=AssertionError("offline")):
        assert measured(repo, base, head)["status"] == "covered"
