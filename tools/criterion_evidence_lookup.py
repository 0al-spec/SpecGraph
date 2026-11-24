#!/usr/bin/env python3
"""Locate recorded C2c evidence for one exact acceptance criterion."""

import argparse
import json
import re
import subprocess
from dataclasses import asdict
from itertools import islice
from pathlib import Path
from uuid import UUID

from yaml import YAMLError

from intent_decision_review.sources import digest, strict_json
from spec_yaml import load_yaml_text
from traceability.criterion import CriterionSource, FilePin
from traceability.criterion_inputs import (
    PROFILE,
    checked_hash,
    full_revision,
    parse_inventory,
    pin,
    pinned_blob,
    read_regular,
    sha256,
)
from traceability.criterion_provider import PROVIDER_ID
from traceability.publication import mapping, records, text
from verification_workflow.execution_files import git, regular_path
from verification_workflow.retained_criterion_scope_spec import (
    RETAINED_CRITERION_SCOPE_SPEC,
    RetainedCriterionScope,
    RetainedCriterionScopeMatch,
)

MAX_DIRECTORY_ENTRIES = 1000
SPEC_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
POINTER = re.compile(r"/acceptance/(?:0|[1-9][0-9]*)")
COLLECTION = ".verification/collection.json"
TERMINAL = "terminal.json"
WORKFLOW_OUTCOMES = {"completed", "rejected", "failed", "aborted", "incomplete"}
VERIFICATION_OUTCOMES = {"passed", "failed", "incomplete", "not_applicable"}


def select(
    workspace: Path, spec_id: str, revision: str, pointer: str, repository_id: str | None = None
) -> RetainedCriterionScope:
    if not SPEC_ID.fullmatch(spec_id) or not POINTER.fullmatch(pointer):
        raise ValueError("expected a specification ID and an /acceptance/N pointer")
    full_revision(revision)
    if Path(git(workspace, "rev-parse", "--show-toplevel").decode().strip()).resolve() != workspace:
        raise ValueError("workspace must be the root of the selected Git repository")
    project = load_yaml_text(pinned_blob(workspace, revision, "specgraph.project.yaml").decode())
    project_id = text(project.get("project_id"), "project ID")
    path = f"specs/nodes/{spec_id}.yaml"
    inventory = parse_inventory(pinned_blob(workspace, revision, path), spec_id, revision, path)
    for source in inventory.sources:
        if source.pointer == pointer:
            return RetainedCriterionScope(
                project_id,
                text(repository_id, "repository ID") if repository_id else project_id,
                spec_id,
                source,
            )
    raise FileNotFoundError(f"criterion unavailable: {spec_id}#{pointer} at {revision}")


def scope_key(row: dict) -> tuple:
    return tuple(
        row.get(key) for key in ("workspace", "repository_id", "spec_id", "declaration_revision")
    )


def selected_scope(scope: dict, target: RetainedCriterionScope) -> bool:
    if scope_key(scope) != (
        target.workspace,
        target.repository_id,
        target.spec_id,
        target.source.revision,
    ):
        return False
    spec = pin(scope.get("spec"))
    matches = []
    for criterion in records(scope.get("criteria"), "terminal criterion targets"):
        source = mapping(criterion.get("source"), "terminal criterion source")
        if source.get("pointer") == target.source.pointer:
            matches.append(source)
    if spec != FilePin(target.source.path, target.source.sha256) or len(matches) != 1:
        raise ValueError("terminal criterion or specification pin differs from the selection")
    source = matches[0]
    recorded = CriterionSource(
        source.get("path"),
        source.get("revision"),
        source.get("sha256"),
        source.get("pointer"),
        source.get("text"),
    )
    facts = RetainedCriterionScopeMatch(
        target,
        RetainedCriterionScope(target.workspace, target.repository_id, target.spec_id, recorded),
    )
    if not RETAINED_CRITERION_SCOPE_SPEC.is_satisfied_by(facts):
        raise ValueError("terminal criterion source differs from the selected Git blob")
    return True


def retained_pins(terminal: dict) -> dict[str, FilePin]:
    declared = tuple(map(pin, records(terminal.get("retained_artifacts"), "retained artifacts")))
    pins = {value.path: value for value in declared}
    if len(pins) != len(declared):
        raise ValueError("duplicate retained artifact paths")
    return pins


def artifact(root: Path, role: str, value: FilePin | None, path: str) -> tuple[dict, bytes | None]:
    reference = {"role": role, "path": path, "sha256": value.sha256 if value else None}
    if value is None:
        return {**reference, "status": "unavailable", "detail": "artifact pin absent"}, None
    try:
        raw = read_regular(regular_path(root, root / path))
        checked_hash(raw, value)
    except OSError as error:
        return {**reference, "status": "unavailable", "detail": str(error)}, None
    except ValueError as error:
        return {**reference, "status": "invalid", "detail": str(error)}, None
    return {**reference, "status": "available"}, raw


def read_collection(
    raw: bytes, terminal: dict, target: RetainedCriterionScope
) -> tuple[dict, dict]:
    report = mapping(strict_json(raw), "C2c collection")
    recorded_digest = report.pop("content_sha256", None)
    provider = mapping(report.get("provider"), "C2c provider")
    expected_scope = dict(
        repository_id=target.repository_id,
        spec_ids=[target.spec_id],
        source_revision=target.source.revision,
        resolver_profile=PROFILE,
    )
    if (
        report.get("artifact_kind") != "criterion_observation_report"
        or type(report.get("schema_version")) is not int
        or report["schema_version"] != 1
        or report.get("report_profile") != "criterion_observation_report/v1"
        or provider.get("provider_id") != PROVIDER_ID
        or provider.get("profile") != PROFILE
        or report.get("scope") != terminal["scope"]
        or report.get("admission") != terminal["admission"]
        or report.get("receipt") is not None
        or report.get("evidence_scope") != expected_scope
        or recorded_digest != digest(report)
    ):
        raise ValueError("C2c collection has an inconsistent profile, scope or content digest")
    collection = mapping(terminal.get("collection"), "terminal collection")
    for key in collection:
        if key not in report or report[key] != collection.get(key):
            raise ValueError(f"C2c {key} differs from the terminal collection")
    rows = records(report.get("criteria"), "C2c criteria")
    matches = [row for row in rows if row.get("source") == asdict(target.source)]
    if len(matches) != 1:
        raise ValueError("C2c lacks an unambiguous observation row for the exact criterion")
    if matches[0].get("admission") != terminal["admission"]:
        raise ValueError("C2c observation admission differs from the terminal")
    return matches[0]


def declared_artifact(root: Path, pins: dict[str, FilePin], role: str, value: FilePin) -> dict:
    entry = pins.get(value.path)
    if entry is not None and entry != value:
        return {
            "role": role,
            **asdict(value),
            "status": "invalid",
            "detail": "C2c artifact pin differs from the terminal manifest",
        }
    return artifact(root, role, entry, value.path)[0]


def read_run(root: Path, target: RetainedCriterionScope) -> dict | None:
    raw = read_regular(regular_path(root, root / TERMINAL))
    terminal = mapping(strict_json(raw), "terminal record")
    if (
        terminal.get("artifact_kind") != "verification_workflow_result"
        or type(terminal.get("schema_version")) is not int
        or terminal["schema_version"] != 1
        or terminal.get("profile") != "verify-criteria/v1"
        or terminal.get("run_id") != root.name
        or terminal.get("scope") != "local_test"
        or terminal.get("admission") != "not_evaluated"
        or terminal.get("receipt") is not None
    ):
        raise ValueError("unsupported or inconsistent verification terminal")
    scope = mapping(terminal.get("pinned_scope"), "terminal scope")
    if not selected_scope(scope, target):
        return None
    workflow_outcome = text(terminal.get("workflow_outcome"), "workflow outcome")
    verification_outcome = text(terminal.get("verification_outcome"), "verification outcome")
    if (
        workflow_outcome not in WORKFLOW_OUTCOMES
        or verification_outcome not in VERIFICATION_OUTCOMES
    ):
        raise ValueError("unrecognized terminal lifecycle or verification outcome")
    execution_revision = full_revision(scope.get("execution_revision"))
    test_revision = full_revision(scope.get("test_revision"))

    pins = retained_pins(terminal)
    report_ref, raw_report = artifact(root, "report", pins.get(COLLECTION), COLLECTION)
    passport = mapping(scope.get("passport"), "terminal passport")
    passport_pin = pin(passport.get("artifact"))
    artifacts = [report_ref, declared_artifact(root, pins, "passport", passport_pin)]
    observation = None
    if terminal.get("collection") is not None:
        collection = mapping(terminal["collection"], "terminal collection")
        selection = mapping(collection.get("selection"), "C2c selection")
        journals = mapping(selection.get("journals"), "C2c journals")
        if (
            selection.get("workspace") != target.workspace
            or pin(selection.get("spec")) != pin(scope.get("spec"))
            or pin(selection.get("passport")) != passport_pin
            or len(journals) != 1
        ):
            raise ValueError("C2c selection differs from the terminal scope")
        journal_id, journal = next(iter(journals.items()))
        journal_pin = pin(journal)
        if raw_report is not None:
            observation = read_collection(raw_report, terminal, target)
        recorded = observation.get("journal") if observation is not None else None
        if recorded is not None:
            recorded = mapping(recorded, "C2c observation journal")
            if (
                recorded.get("artifact_id") != journal_id
                or recorded.get("sha256") != journal_pin.sha256
                or recorded.get("execution_source_revision") != scope.get("execution_revision")
                or recorded.get("test_source_revision") != scope.get("test_revision")
            ):
                raise ValueError(
                    "C2c observation journal differs from the selected execution scope"
                )
        artifacts.extend(
            (
                declared_artifact(root, pins, "plan", pin(selection.get("plan"))),
                declared_artifact(root, pins, "journal", journal_pin),
            )
        )

    elif raw_report is not None:
        raise ValueError("terminal has a C2c report pin without a collection declaration")

    states = {entry["status"] for entry in artifacts}
    availability = (
        "invalid"
        if "invalid" in states
        else ("unavailable" if "unavailable" in states else "available")
    )
    return {
        "run_id": root.name,
        "terminal_path": f"{root.name}/{TERMINAL}",
        "terminal_sha256": sha256(raw),
        "workflow_outcome": workflow_outcome,
        "verification_outcome": verification_outcome,
        "scope": terminal["scope"],
        "execution_revision": execution_revision,
        "test_revision": test_revision,
        "admission": terminal["admission"],
        "receipt": None,
        "artifacts": artifacts,
        "recheck_inputs": availability,
        "recorded_observation": observation,
    }


def is_run_name(name: str) -> bool:
    try:
        return str(UUID(name)) == name
    except ValueError:
        return False


def lookup(runs_root: Path, target: RetainedCriterionScope) -> dict:
    entries = list(islice(runs_root.iterdir(), MAX_DIRECTORY_ENTRIES + 1))
    if len(entries) > MAX_DIRECTORY_ENTRIES:
        raise ValueError(f"run catalog exceeds {MAX_DIRECTORY_ENTRIES} directory entries")
    matches, findings = [], []
    for root in sorted(entries):
        if not is_run_name(root.name):
            continue
        try:
            result = read_run(root, target)
        except (ValueError, OSError, RecursionError) as error:
            status = "unavailable" if isinstance(error, OSError) else "invalid"
            findings.append({"run_id": root.name, "status": status, "detail": str(error)})
            continue
        if result is not None:
            matches.append(result)
    return {
        "status": "found" if matches else "incomplete" if findings else "not_found",
        "criterion": asdict(target.source),
        "workspace": target.workspace,
        "repository_id": target.repository_id,
        "spec_id": target.spec_id,
        "runs_root": str(runs_root),
        "runs": matches,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("spec_id")
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--criterion", required=True)
    parser.add_argument(
        "--runs-root", type=Path, help="configured local verification run directory"
    )
    parser.add_argument(
        "--repository-id", help="retained repository identity, defaults to project ID"
    )
    args = parser.parse_args(argv)
    envelope = {"artifact_kind": "specgraph_criterion_evidence_lookup", "schema_version": 1}
    target = None
    try:
        workspace = args.workspace_root.resolve(strict=True)
        target = select(workspace, args.spec_id, args.revision, args.criterion, args.repository_id)
        if args.runs_root is None:
            raise FileNotFoundError("no retained run directory selected; supply --runs-root")
        root = (workspace / args.runs_root.expanduser()).resolve(strict=True)
        result = lookup(root, target)
    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        TypeError,
        YAMLError,
        RecursionError,
    ) as error:
        status = (
            "unavailable" if isinstance(error, (OSError, subprocess.SubprocessError)) else "invalid"
        )
        result = {"status": status, "runs": [], "findings": [{"detail": str(error)}]}
        if target is not None:
            result["criterion"] = asdict(target.source)
    print(json.dumps({**envelope, **result}, ensure_ascii=False, indent=2))
    return 2 if result["status"] in {"invalid", "unavailable"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
