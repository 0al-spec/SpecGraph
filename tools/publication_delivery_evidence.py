#!/usr/bin/env python3
"""Join existing pytest and HTTP publication signals for one bootstrap feature."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from publication_evidence.bindings_spec import BINDING_ERROR_SPEC
from publication_evidence.bound_observation_spec import TEST_OBSERVATION_SPEC
from publication_evidence.case_spec import TEST_CASE_SPEC
from publication_evidence.context import (
    BindingContext,
    ExecutionIdentity,
    HttpObservationContext,
    MergedRevisionContext,
    SnapshotContext,
    SourceIdentity,
    TestCaseContext,
    TestObservationContext,
    TestSuiteContext,
)
from publication_evidence.http_observation_spec import HTTP_OBSERVATION_SPEC
from publication_evidence.merged_revision_spec import MERGED_REVISION_SPEC
from publication_evidence.snapshot_spec import SOURCE_SNAPSHOT_SPEC
from publication_evidence.suite_spec import TEST_SUITE_SPEC
from spec_yaml import load_yaml_text

DEFAULT_BINDINGS = "tools/feature_passports/static-publication-bindings.json"


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def load_pilot(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    bindings = load_json(root / DEFAULT_BINDINGS)
    passport = load_json(root / bindings["passport"])
    criteria = {item["id"] for item in passport["spec"]["intent"]["acceptance_criteria"]}
    node = load_yaml_text((root / bindings["spec"]).read_text(encoding="utf-8"))
    graph_criteria = {item["id"] for item in node["specification"]["requirement"]["criteria"]}
    obligations = bindings["obligations"]
    error = BINDING_ERROR_SPEC.decide(
        BindingContext(
            frozenset(criteria),
            frozenset(graph_criteria),
            tuple(item["criterion_id"] for item in obligations),
            tuple(item["test"] for item in obligations),
        )
    ).value
    if error:
        raise ValueError(error)
    return bindings, passport


def source_identity(root: Path, bindings: dict[str, Any]) -> dict[str, Any]:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    paths = {
        DEFAULT_BINDINGS,
        bindings["passport"],
        bindings["spec"],
        bindings["implementation"],
        "tools/publication_delivery_evidence.py",
        *(
            path.relative_to(root).as_posix()
            for path in (root / "tools/publication_evidence").glob("*.py")
        ),
        *(item["test"].split("::", 1)[0] for item in bindings["obligations"]),
    }
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=root, text=True
    )
    return {
        "repository": "0al-spec/SpecGraph",
        "revision": revision,
        "working_tree_clean": not bool(dirty.strip()),
        "files_sha256": {name: file_digest(root / name) for name in sorted(paths)},
    }


def provenance() -> dict[str, str]:
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "0al-spec/SpecGraph")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    return {
        "provider": "github_actions" if run_id else "local",
        "run_id": run_id,
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "uri": f"{server}/{repository}/actions/runs/{run_id}" if run_id else "local-run",
    }


def junit_obligations(
    path: Path, obligations: list[dict[str, str]], exit_code: int
) -> tuple[str, list[dict[str, str]]]:
    cases = list(ET.parse(path).getroot().iter("testcase")) if path.is_file() else []
    results = []
    for item in obligations:
        filename, function = item["test"].split("::", 1)
        classname = filename.removesuffix(".py").replace("/", ".")
        matches = [
            case
            for case in cases
            if case.get("classname") == classname and case.get("name") == function
        ]
        result = TEST_CASE_SPEC.decide(
            TestCaseContext(
                len(matches),
                any(
                    case.find("failure") is not None or case.find("error") is not None
                    for case in matches
                ),
                any(case.find("skipped") is not None for case in matches),
            )
        ).value
        results.append({**item, "result": result})
    result = TEST_SUITE_SPEC.decide(
        TestSuiteContext(
            exit_code,
            frozenset(item["result"] for item in results),
            len(cases),
            len(obligations),
        )
    ).value
    return result, results


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_tests(root: Path, output: Path) -> int:
    bindings, _ = load_pilot(root)
    source = source_identity(root, bindings)
    output.mkdir(parents=True, exist_ok=True)
    junit = output / "tests.xml"
    # A failed collection must not leave a previous run's passing XML in place.
    for name in ("tests.xml", "tests.json", "report.json", "report.md"):
        (output / name).unlink(missing_ok=True)
    command = [sys.executable, "-m", "pytest", "-q", f"--junitxml={junit}"]
    command.extend(item["test"] for item in bindings["obligations"])
    completed = subprocess.run(command, cwd=root, check=False)
    result, obligations = junit_obligations(junit, bindings["obligations"], completed.returncode)
    if not SOURCE_SNAPSHOT_SPEC.is_satisfied_by(
        SnapshotContext(source_facts(source), source_facts(source_identity(root, bindings)))
    ):
        result = "missing"
    write_json(
        output / "tests.json",
        {
            "artifact_kind": "specgraph_publication_test_observation",
            "schema_version": 1,
            "source": source,
            "provenance": provenance(),
            "result": result,
            "exit_code": completed.returncode,
            "obligations": obligations,
            "junit_sha256": file_digest(junit) if junit.is_file() else None,
        },
    )
    return 0 if result == "observed_success" else 1


def stage(
    result: str, summary: str, evidence: list[dict[str, str]], **details: Any
) -> dict[str, Any]:
    return {"result": result, "summary": summary, "evidence": evidence, **details}


def observation_context(
    observer: dict[str, Any] | None, target_environment: str, target_uri: str
) -> dict[str, Any]:
    return {
        "observer": observer,
        "target": {"environment": target_environment, "uri": target_uri},
    }


def source_facts(source: dict[str, Any]) -> SourceIdentity:
    return SourceIdentity(
        source.get("repository", ""),
        source.get("revision", ""),
        tuple(sorted(source.get("files_sha256", {}).items())),
    )


def execution_facts(run: dict[str, Any]) -> ExecutionIdentity:
    return ExecutionIdentity(
        *(run.get(key, "") for key in ("provider", "run_id", "run_attempt", "uri"))
    )


def obligation_facts(items: list[dict[str, Any]]) -> tuple[tuple[str, str], ...]:
    return tuple((item.get("criterion_id", ""), item.get("test", "")) for item in items)


def integer(value: Any) -> int | None:
    return value if type(value) is int else None


def acceptance_signal(path: Path | None, source: dict[str, Any]) -> dict[str, Any]:
    missing = stage("missing", "Awaiting a merged PR for this revision.", [])
    if path is None or not path.is_file():
        return missing
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return missing
    if not isinstance(rows, list):
        return missing
    for row in rows:
        if not isinstance(row, dict):
            continue
        base = row.get("base")
        repository = base.get("repo") if isinstance(base, dict) else None
        if not isinstance(repository, dict):
            continue
        if MERGED_REVISION_SPEC.is_satisfied_by(
            MergedRevisionContext(
                row.get("merged_at", ""),
                source["revision"],
                row.get("merge_commit_sha", ""),
                source["repository"],
                repository.get("full_name", ""),
                integer(row.get("number")) or 0,
            )
        ):
            uri = f"https://github.com/{source['repository']}/pull/{row['number']}"
            return stage(
                "observed_success",
                "Recorded revision merged through a pull request.",
                [
                    {"uri": path.name, "sha256": file_digest(path)},
                    {"uri": uri},
                ],
            )
    return missing


def delivery_report(
    root: Path,
    tests_path: Path,
    bundle: Path | None,
    runtime_path: Path | None,
    environment: str,
    acceptance_path: Path | None = None,
) -> dict[str, Any]:
    bindings, passport = load_pilot(root)
    source = source_identity(root, bindings)
    run = provenance()
    report_observer = {
        **run,
        "environment": "ci" if run["provider"] == "github_actions" else "local",
    }
    metadata = passport["metadata"]
    tests = load_json(tests_path) if tests_path.is_file() else None
    test_result = "missing"
    test_observer = None
    obligations = []
    if tests is not None:
        if TEST_OBSERVATION_SPEC.is_satisfied_by(
            TestObservationContext(
                source_facts(source),
                source_facts(tests.get("source", {})),
                execution_facts(run),
                execution_facts(tests.get("provenance", {})),
                obligation_facts(bindings["obligations"]),
                obligation_facts(tests.get("obligations", [])),
            )
        ):
            test_observer = report_observer
            obligations = tests["obligations"]
            test_result = TEST_SUITE_SPEC.decide(
                TestSuiteContext(
                    integer(tests.get("exit_code")),
                    frozenset(item.get("result") for item in obligations),
                    len(obligations),
                    len(bindings["obligations"]),
                    tests.get("result", ""),
                )
            ).value
    test_refs = [{"uri": tests_path.name, "sha256": file_digest(tests_path)}] if tests else []
    runtime = load_json(runtime_path) if runtime_path and runtime_path.is_file() else None
    bundle_identity = None
    runtime_result = "missing"
    runtime_observer = None
    if bundle is not None:
        bundle_identity = {
            "manifest_sha256": file_digest(bundle / "artifact_manifest.json"),
            "checksums_sha256": file_digest(bundle / "checksums.sha256"),
        }
    if runtime is not None and bundle_identity is not None:
        execution = runtime.get("execution_context", {})
        manifest = load_json(bundle / "artifact_manifest.json")
        summary = runtime.get("summary", {})
        observed_bundle = runtime.get("bundle_identity", {})
        if HTTP_OBSERVATION_SPEC.is_satisfied_by(
            HttpObservationContext(
                source_revision=source["revision"],
                observed_source_revision=execution.get("source_revision", ""),
                expected_execution=execution_facts(run),
                observed_execution=execution_facts(execution),
                observer_environment=execution.get("environment", ""),
                expected_bundle=(
                    bundle_identity["manifest_sha256"],
                    bundle_identity["checksums_sha256"],
                ),
                observed_bundle=(
                    observed_bundle.get("manifest_sha256", ""),
                    observed_bundle.get("checksums_sha256", ""),
                ),
                expected_origin=bindings["runtime_base_url"],
                observed_origin=runtime.get("remote_base_url", ""),
                status=runtime.get("status", ""),
                artifact_kind=runtime.get("artifact_kind", ""),
                expected_file_count=len(manifest["files"]),
                verified_file_count=integer(summary.get("verified_file_count")),
                verified_metadata_count=integer(summary.get("verified_metadata_file_count")),
                failure_count=integer(summary.get("failure_count")),
            )
        ):
            runtime_result = "observed_success"
            runtime_observer = {
                key: execution.get(key, "")
                for key in ("provider", "environment", "uri", "run_id", "run_attempt")
            }
    native_ref = (
        [{"uri": runtime_path.name, "sha256": file_digest(runtime_path)}]
        if runtime is not None and runtime_path
        else []
    )
    repository_uri = f"https://github.com/{source['repository']}"
    source_scope = observation_context(
        report_observer, "repository", f"{repository_uri}/tree/{source['revision']}"
    )
    publication_scope = observation_context(
        runtime_observer, bindings["runtime_environment"], bindings["runtime_base_url"]
    )
    acceptance = acceptance_signal(acceptance_path, source)
    acceptance["provenance"] = observation_context(report_observer, "github", repository_uri)
    stages = {
        "intent": stage(
            "observed_success",
            passport["spec"]["intent"]["summary"],
            [
                {"uri": "inputs/passport.json", "sha256": file_digest(root / bindings["passport"])},
            ],
            provenance=source_scope,
        ),
        "spec": stage(
            "observed_success",
            "Authored requirement and explicit test bindings.",
            [
                {"uri": "inputs/spec.yaml", "sha256": file_digest(root / bindings["spec"])},
                {"uri": "inputs/bindings.json", "sha256": file_digest(root / DEFAULT_BINDINGS)},
            ],
            provenance=source_scope,
        ),
        "tests": stage(
            test_result,
            "Required pytest function observations.",
            test_refs,
            obligations=obligations,
            provenance=observation_context(
                test_observer, report_observer["environment"], run["uri"]
            ),
        ),
        "deploy": stage(
            runtime_result,
            "Expected root bundle observed at the HTTP origin.",
            native_ref,
            provenance=publication_scope,
        ),
        "runtime": stage(
            runtime_result,
            "HTTP bytes checked by the CI/local verifier.",
            native_ref,
            observation=runtime,
            provenance=publication_scope,
        ),
        "acceptance": acceptance,
    }
    return {
        "artifact_kind": "feature_delivery_signals",
        "schema_version": 1,
        "profile": "linked_delivery_signals_v1",
        "feature_passport": {
            **{key: metadata[key] for key in ("feature_id", "passport_id", "version")},
            "file_sha256": file_digest(root / bindings["passport"]),
        },
        "source": source,
        "provenance": {
            **run,
            "environment": environment,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "bundle_identity": bundle_identity,
        "trust_model": "provider_reported",
        "admission": "not_evaluated",
        "stages": stages,
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Publication delivery signals",
        "",
        f"Feature: `{report['feature_passport']['feature_id']}`",
        "",
        f"Source: `{report['source']['revision']}`",
        "",
        "Trust: `provider_reported`; admission: `not_evaluated`.",
        "",
        "| Stage | Result | Observer | Target | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, item in report["stages"].items():
        refs = ", ".join(f"[{ref['uri']}]({ref['uri']})" for ref in item["evidence"]) or "—"
        context = item["provenance"]
        observer = context["observer"]
        observer_label = observer["environment"] if observer else "unknown"
        target = context["target"]
        lines.append(
            f"| {name} | {item['result']} | {observer_label} | "
            f"{target['environment']}: {target['uri']} | {refs} |"
        )
    lines.extend(
        [
            "",
            "Tests are function-level observations. Runtime means HTTP publication",
            "observed by a CI/local verifier. Acceptance uses an explicitly merged revision.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("test", "report"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tests-report", type=Path)
    parser.add_argument("--bundle-dir", type=Path)
    parser.add_argument("--runtime-report", type=Path)
    parser.add_argument("--environment", default="local")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    try:
        if args.command == "test":
            return run_tests(root, output)
        output.mkdir(parents=True, exist_ok=True)
        for name in ("report.json", "report.md"):
            (output / name).unlink(missing_ok=True)
        bindings, _ = load_pilot(root)
        for name, source_path in (
            ("passport.json", bindings["passport"]),
            ("spec.yaml", bindings["spec"]),
            ("bindings.json", DEFAULT_BINDINGS),
        ):
            target = output / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / source_path).read_bytes())
        report = delivery_report(
            root,
            args.tests_report or output / "tests.json",
            args.bundle_dir,
            args.runtime_report,
            args.environment,
            output / "associated-pulls.json",
        )
        write_json(output / "report.json", report)
        (output / "report.md").write_text(markdown_report(report), encoding="utf-8")
        return 0
    except (OSError, ValueError, KeyError, ET.ParseError) as exc:
        print(f"publication delivery evidence: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
