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
    if criteria != graph_criteria:
        raise ValueError("passport criteria must match the canonical pilot requirement")
    obligations = bindings["obligations"]
    bound = [item["criterion_id"] for item in obligations]
    tests = [item["test"] for item in obligations]
    if not bound or len(bound) != len(set(bound)) or set(bound) != criteria:
        raise ValueError("bindings must cover every passport criterion exactly once")
    if len(tests) != len(set(tests)) or any("::" not in item for item in tests):
        raise ValueError("each binding must name a distinct explicit pytest function")
    return bindings, passport


def source_identity(root: Path, bindings: dict[str, Any]) -> dict[str, Any]:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    paths = {
        DEFAULT_BINDINGS,
        bindings["passport"],
        bindings["spec"],
        bindings["implementation"],
        "tools/publication_delivery_evidence.py",
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
        result = "missing"
        if len(matches) == 1:
            case = matches[0]
            if case.find("failure") is not None or case.find("error") is not None:
                result = "observed_failure"
            elif case.find("skipped") is None:
                result = "observed_success"
        results.append({**item, "result": result})
    outcomes = {item["result"] for item in results}
    if exit_code != 0 or "observed_failure" in outcomes:
        return "observed_failure", results
    if outcomes == {"observed_success"} and len(cases) == len(obligations):
        return "observed_success", results
    return "missing", results


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
    if source_identity(root, bindings) != source:
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


def stage(result: str, summary: str, evidence: list[dict[str, str]]) -> dict[str, Any]:
    return {"result": result, "summary": summary, "evidence": evidence}


def delivery_report(
    root: Path,
    tests_path: Path,
    bundle: Path | None,
    runtime_path: Path | None,
    environment: str,
) -> dict[str, Any]:
    bindings, passport = load_pilot(root)
    source = source_identity(root, bindings)
    run = provenance()
    metadata = passport["metadata"]
    tests = load_json(tests_path) if tests_path.is_file() else None
    test_result = "missing"
    obligations = []
    if tests is not None:
        expected = [(item["criterion_id"], item["test"]) for item in bindings["obligations"]]
        actual = [
            (item.get("criterion_id"), item.get("test")) for item in tests.get("obligations", [])
        ]
        same_run = tests.get("provenance") == run
        observed_source = tests.get("source", {})
        same_source = (
            observed_source.get("revision") == source["revision"]
            and observed_source.get("files_sha256") == source["files_sha256"]
        )
        if same_source and actual == expected and same_run:
            obligations = tests["obligations"]
            outcomes = {item.get("result") for item in obligations}
            if tests.get("exit_code") != 0 or "observed_failure" in outcomes:
                test_result = "observed_failure"
            elif tests.get("result") == "observed_success" and outcomes == {"observed_success"}:
                test_result = "observed_success"
    test_refs = [{"uri": tests_path.name, "sha256": file_digest(tests_path)}] if tests else []
    runtime = load_json(runtime_path) if runtime_path and runtime_path.is_file() else None
    bundle_identity = None
    runtime_result = "missing"
    if bundle is not None:
        bundle_identity = {
            "manifest_sha256": file_digest(bundle / "artifact_manifest.json"),
            "checksums_sha256": file_digest(bundle / "checksums.sha256"),
        }
    if runtime is not None and bundle_identity is not None:
        execution = runtime.get("execution_context", {})
        same_run = not run["run_id"] or execution == {
            "source_revision": source["revision"],
            "run_id": run["run_id"],
            "run_attempt": run["run_attempt"],
        }
        manifest = load_json(bundle / "artifact_manifest.json")
        summary = runtime.get("summary", {})
        if (
            same_run
            and runtime.get("status") == "verified"
            and runtime.get("artifact_kind")
            == "specgraph_static_artifact_remote_verification_report"
            and runtime.get("bundle_identity") == bundle_identity
            and runtime.get("remote_base_url") == bindings["runtime_base_url"]
            and summary.get("verified_file_count") == len(manifest["files"])
            and summary.get("verified_metadata_file_count") == 2
            and summary.get("failure_count") == 0
        ):
            runtime_result = "observed_success"
    native_ref = (
        [{"uri": runtime_path.name, "sha256": file_digest(runtime_path)}]
        if runtime is not None and runtime_path
        else []
    )
    stages = {
        "intent": stage(
            "observed_success",
            passport["spec"]["intent"]["summary"],
            [
                {"uri": "inputs/passport.json", "sha256": file_digest(root / bindings["passport"])},
            ],
        ),
        "spec": stage(
            "observed_success",
            "Authored requirement and explicit test bindings.",
            [
                {"uri": "inputs/spec.yaml", "sha256": file_digest(root / bindings["spec"])},
                {"uri": "inputs/bindings.json", "sha256": file_digest(root / DEFAULT_BINDINGS)},
            ],
        ),
        "tests": {
            **stage(test_result, "Required pytest function observations.", test_refs),
            "obligations": obligations,
        },
        "deploy": stage(
            runtime_result, "Expected root bundle observed at the HTTP origin.", native_ref
        ),
        "runtime": {
            **stage(runtime_result, "HTTP bytes checked by the CI/local verifier.", native_ref),
            "observation": runtime,
        },
        "acceptance": stage("missing", "Awaiting merged PR or explicit operator acceptance.", []),
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
        "| Stage | Result | Evidence |",
        "| --- | --- | --- |",
    ]
    for name, item in report["stages"].items():
        refs = ", ".join(f"[{ref['uri']}]({ref['uri']})" for ref in item["evidence"]) or "—"
        lines.append(f"| {name} | {item['result']} | {refs} |")
    lines.extend(
        [
            "",
            "Tests are function-level observations. Runtime means HTTP publication",
            "observed by a CI/local verifier. Acceptance remains explicit.",
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
        )
        write_json(output / "report.json", report)
        (output / "report.md").write_text(markdown_report(report), encoding="utf-8")
        return 0
    except (OSError, ValueError, KeyError, ET.ParseError) as exc:
        print(f"publication delivery evidence: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
