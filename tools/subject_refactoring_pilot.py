"""Replay the authored PR 743/744 criterion bindings against pinned SpecGraph source.

This is an experimental evidence harness, not a canonical identity allocator or
acceptance gate. --execute runs repository tests from the three historical commits.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from importlib.metadata import distribution, version
from pathlib import Path, PurePosixPath

from subject_read_model_io import lookup_payload, parse_subject_index, parse_subject_ref


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, timeout=60
    ).stdout


def checked_commit(repo: Path, commit: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("checkpoint requires a full Git commit SHA")
    if git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip() != commit:
        raise ValueError("checkpoint does not select the declared commit")
    return commit


def relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ValueError(f"expected a repository-relative path: {value}")
    return value


def source_blob(repo: Path, commit: str, path: str) -> bytes | None:
    path = relative_path(path)
    if not git(repo, "ls-tree", "--name-only", commit, "--", path).strip():
        return None
    return git(repo, "show", f"{commit}:{path}")


def code_anchor(repo: Path, commit: str, anchor: str) -> dict:
    path, symbol = anchor.split("::")
    blob = source_blob(repo, commit, path)
    result = {"commit": commit, "path": path, "symbol": symbol}
    if blob is None:
        return {**result, "status": "missing_path"}
    matches = [
        node
        for node in ast.parse(blob).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name == symbol
    ]
    if len(matches) != 1:
        return {**result, "status": "missing_or_ambiguous_symbol"}
    node = matches[0]
    return {
        **result,
        "status": "source_anchored",
        "blob_sha256": digest(blob),
        "start_line": node.lineno,
        "end_line": node.end_lineno,
        "url": f"https://github.com/0al-spec/SpecGraph/blob/{commit}/{path}#L{node.lineno}",
    }


def source_statement(repo: Path, commit: str, path: str, statement: str) -> dict:
    blob = source_blob(repo, commit, path)
    matches = 0 if blob is None else " ".join(blob.decode().split()).count(statement)
    return {
        "commit": commit,
        "path": path,
        "status": "unique_text_match" if matches == 1 else "missing_or_ambiguous_text",
        "match_count": matches,
        "blob_sha256": None if blob is None else digest(blob),
        "url": f"https://github.com/0al-spec/SpecGraph/blob/{commit}/{path}",
        "scope": "verbatim_statement_presence_not_semantic_proof",
    }


def validate_plan(plan: dict):
    if plan["artifact_kind"] != "subject_refactoring_pilot_plan" or plan["schema_version"] != 1:
        raise ValueError("unsupported pilot plan")
    index = parse_subject_index(plan["snapshot"])
    identities = []
    for binding in plan["bindings"]:
        selection = binding["criterion"]
        ref = parse_subject_ref(selection["subject"])
        if ref.subject_class.value != "criterion" or selection["mode"] != "exact":
            raise ValueError("pilot evidence must pin an exact criterion")
        if index.lookup_exact(ref, selection["revision"]).status != "resolved":
            raise ValueError("unresolved criterion binding")
        if binding["canonical_requirement"] is not None:
            raise ValueError("this pilot has no adopted canonical Requirement mapping")
        if not binding["tests"] or len(set(binding["tests"])) != len(binding["tests"]):
            raise ValueError("binding needs distinct test selections")
        identities.append(ref.identity)
    if not identities or len(set(identities)) != len(identities):
        raise ValueError("duplicate or empty criterion bindings")
    declared = [r.reference.identity for w in index.snapshots for r in w.subjects]
    if sorted(identities) != sorted(declared):
        raise ValueError("pilot bindings must cover exactly the declared subjects")
    names = [c["name"] for c in plan["checkpoints"]]
    if not names or len(set(names)) != len(names):
        raise ValueError("checkpoint names must be distinct")
    for checkpoint in plan["checkpoints"]:
        if not re.fullmatch(r"[a-z0-9-]+", checkpoint["name"]):
            raise ValueError("invalid checkpoint name")
        if set(checkpoint["implementation"]) != {i[1] for i in identities}:
            raise ValueError("checkpoint implementation bindings are incomplete")
        if not all(checkpoint["implementation"].values()):
            raise ValueError("each criterion needs an implementation anchor")
    trace = plan["trace_probe"]
    if trace["commit"] not in {c["commit"] for c in plan["checkpoints"]}:
        raise ValueError("trace commit must be a checkpoint")
    if trace["criterion"] not in [b["criterion"] for b in plan["bindings"]]:
        raise ValueError("trace must pin a declared criterion")
    return index


def junit_results(path: Path, expected: list[str], returncode: int) -> dict:
    """A successful process without every selected test is not passing evidence."""
    cases = []
    if path.exists():
        for case in ET.parse(path).iter("testcase"):
            status = "passed"
            for kind in ("skipped", "failure", "error"):
                if case.find(kind) is not None:
                    status = kind
            cases.append(
                {
                    "nodeid": case.attrib["classname"].replace(".", "/")
                    + ".py::"
                    + case.attrib["name"],
                    "status": status,
                }
            )
    complete = sorted(c["nodeid"] for c in cases) == sorted(expected)
    passed = complete and returncode == 0 and all(c["status"] == "passed" for c in cases)
    return {"status": "passed" if passed else "failed", "returncode": returncode, "cases": cases}


TRACE_PROBE = """
import json, sys
sys.path.insert(0, 'tools')
from specification_core import TraceRecorder
from candidate_repair_readiness_context import CandidateRepairReadinessContext
from candidate_repair_readiness_spec import candidate_repair_readiness
rows = []
for name, findings in [('clean-noop', False), ('invalid-noop', True)]:
    recorder = TraceRecorder()
    outcome = candidate_repair_readiness(
        CandidateRepairReadinessContext(findings, 0, 0, True), recorder=recorder)
    rows.append({'scenario': name, 'ready': outcome.ready,
                 'no_op_repair_loop': outcome.no_op_repair_loop,
                 'events': [{'name': e.name, 'outcome': e.outcome.value}
                            for e in recorder.events]})
print(json.dumps(rows))
"""


def check_trace(rows: list, event_name: str) -> bool:
    return rows == [
        {
            "scenario": name,
            "ready": ready,
            "no_op_repair_loop": True,
            "events": [{"name": event_name, "outcome": outcome}],
        }
        for name, ready, outcome in (
            ("clean-noop", True, "satisfied"),
            ("invalid-noop", False, "unsatisfied"),
        )
    ]


def execute_checkpoint(repo: Path, commit: str, tests: list[str], out: Path, trace: dict) -> dict:
    """Execute only in a disposable archive; imports cannot reuse another checkpoint."""
    with tempfile.TemporaryDirectory(prefix="subject-pilot-") as tmp:
        root = Path(tmp)
        archive = git(
            repo,
            "archive",
            "--format=tar",
            commit,
            "tools",
            "src",
            "pyproject.toml",
            "tests/conftest.py",
            "tests/test_candidate_repair_loop.py",
            "tests/test_repaired_candidate_promotion_handoff.py",
            "tests/fixtures/candidate_repair_loop",
            "tests/fixtures/pre_sib_coherence",
        )
        with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
            for member in contents:
                path = root / relative_path(member.name.rstrip("/"))
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with contents.extractfile(member) as source:
                        path.write_bytes(source.read())
                else:
                    raise ValueError("pilot archive cannot contain links or special files")
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in {"PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"}
        }
        env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            *tests,
            f"--junitxml={out / 'tests.xml'}",
            f"--basetemp={root / 'test-temp'}",
        ]
        run = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=180)
        (out / "tests.log").write_bytes(run.stdout + run.stderr)
        result = junit_results(out / "tests.xml", tests, run.returncode)
        result["log_sha256"] = digest((out / "tests.log").read_bytes())
        result["junit_sha256"] = (
            digest((out / "tests.xml").read_bytes()) if (out / "tests.xml").exists() else None
        )
        result["selected_tests"] = tests
        result["runtime_trace"] = {"status": "not_collected_at_this_checkpoint"}
        if commit == trace["commit"]:
            probe = subprocess.run(
                [sys.executable, "-c", TRACE_PROBE],
                cwd=root,
                env=env,
                check=True,
                capture_output=True,
                timeout=30,
            )
            rows = json.loads(probe.stdout)
            result["runtime_trace"] = {
                "status": "passed" if check_trace(rows, trace["event_name"]) else "failed",
                "criterion": trace["criterion"],
                "scope": "direct_policy_probe_not_production_telemetry",
                "observations": rows,
            }
        return result


def run_pilot(repo: Path, plan: dict, out: Path, *, execute: bool) -> dict:
    index = validate_plan(plan)
    # Never consume outputs from a previous run, including its JUnit success.
    out.mkdir(parents=True, exist_ok=False)
    (out / "subjects.json").write_text(json.dumps(plan["snapshot"], indent=2) + "\n")
    rows = []
    for checkpoint in plan["checkpoints"]:
        commit = checked_commit(repo, checkpoint["commit"])
        bindings = []
        for binding in plan["bindings"]:
            selection = binding["criterion"]
            ref = parse_subject_ref(selection["subject"])
            lookup = index.lookup_exact(ref, selection["revision"])
            bindings.append(
                {
                    "criterion": selection,
                    "lookup": lookup_payload(lookup),
                    "source": source_statement(
                        repo, commit, binding["source_path"], lookup.selected_revision.statement
                    ),
                    "implementation": [
                        code_anchor(repo, commit, anchor)
                        for anchor in checkpoint["implementation"][ref.local_subject_id]
                    ],
                    "tests": [code_anchor(repo, commit, anchor) for anchor in binding["tests"]],
                    "canonical_requirement": None,
                    "mapping_authority": binding["mapping_authority"],
                }
            )
        anchored = all(
            b["source"]["status"] == "unique_text_match"
            and all(a["status"] == "source_anchored" for a in b["implementation"] + b["tests"])
            for b in bindings
        )
        stage_dir = out / checkpoint["name"]
        stage_dir.mkdir()
        execution = {"status": "not_run"}
        if execute and anchored:
            tests = sorted({t for b in plan["bindings"] for t in b["tests"]})
            execution = execute_checkpoint(repo, commit, tests, stage_dir, plan["trace_probe"])
        rows.append(
            {
                "checkpoint": checkpoint,
                "source_bindings_valid": anchored,
                "bindings": bindings,
                "execution": execution,
            }
        )
    stale = plan["stale_anchor_probe"]
    before = code_anchor(repo, checked_commit(repo, stale["present_at"]), stale["anchor"])
    after = code_anchor(repo, checked_commit(repo, stale["absent_at"]), stale["anchor"])
    unavailable = [
        index.lookup_exact(parse_subject_ref(b["criterion"]["subject"]), 2).status
        for b in plan["bindings"]
    ]
    negatives_ok = (
        before["status"] == "source_anchored"
        and after["status"] == "missing_path"
        and all(s == "unavailable_revision" for s in unavailable)
    )
    traced = [r["execution"].get("runtime_trace", {}) for r in rows]
    trace_ok = sum(t.get("status") == "passed" for t in traced) == 1
    passed = (
        negatives_ok
        and trace_ok
        and all(r["source_bindings_valid"] and r["execution"]["status"] == "passed" for r in rows)
    )
    report = {
        "artifact_kind": "subject_refactoring_pilot_report",
        "schema_version": 1,
        "status": "pilot_passed" if passed else "incomplete",
        "canonical_mutations_allowed": False,
        "canonical_readiness": "not_evaluated",
        "mapping_authority": plan["authority"],
        "identity_scope": plan["identity_scope"],
        "plan_sha256": digest(json.dumps(plan, sort_keys=True).encode()),
        "runner_sha256": digest(Path(__file__).read_bytes()),
        "python_version": sys.version.split()[0],
        "dependencies": {
            "pytest": version("pytest"),
            "PyYAML": version("PyYAML"),
            "specification-core": version("specification-core"),
            "specification_core_commit": json.loads(
                distribution("specification-core").read_text("direct_url.json") or "{}"
            )
            .get("vcs_info", {})
            .get("commit_id"),
        },
        "checkpoints": rows,
        "negative_probes": {
            "passed": negatives_ok,
            "historical_anchor": before,
            "stale_anchor": after,
            "revision_2_results": unavailable,
        },
        "gaps": [
            "canonical_requirement_mapping_missing",
            "historical_subject_revisions_not_adopted",
            "only_clean_noop_has_direct_policy_trace_binding",
            "no_production_telemetry_or_hypercode_binding",
        ],
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--plan", type=Path, default=Path(__file__).with_suffix(".json"))
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for this run")
    parser.add_argument(
        "--execute", action="store_true", help="Run tests from the pinned historical commits"
    )
    args = parser.parse_args()
    try:
        report = run_pilot(
            args.repo.resolve(),
            json.loads(args.plan.read_text()),
            args.output_dir.resolve(),
            execute=args.execute,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
        ET.ParseError,
    ) as exc:
        print(f"pilot incomplete: {exc}", file=sys.stderr)
        return 2
    print(f"{report['status']}: {args.output_dir / 'report.json'}")
    return 0 if report["status"] == "pilot_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
