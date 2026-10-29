"""Capture explicit workspace selections; all filesystem work stays at this edge."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import yaml

from ontology_snapshot import OntologySnapshot, OntologySnapshotError, capture_ontology_snapshot

from .invalid_spec import INVALID_SPEC
from .model import CheckResult, ContextFacts, ContextResult
from .unavailable_spec import UNAVAILABLE_SPEC

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class _UniqueLoader(yaml.SafeLoader):
    """Reject ambiguous selection and captured source mappings."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                if key in result:
                    raise ValueError(f"duplicate YAML key: {key!r}")
                result[key] = self.construct_object(value_node, deep=deep)
            except TypeError as error:
                raise ValueError("unhashable YAML mapping key") from error
        return result


def _load_yaml(data: bytes) -> object:
    return yaml.load(data, Loader=_UniqueLoader)


def _path(root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        raise ValueError("selection and package paths must be workspace-relative")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("selection or package path escapes workspace")
    return resolved


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    return value


def _parse(
    payload: object,
) -> tuple[list[dict[str, str]], tuple[str, ...], tuple[tuple[str, str], ...]]:
    if (
        not isinstance(payload, dict)
        or payload.get("artifact_kind") != "specgraph_project_ontology_selection"
        or type(payload.get("schema_version")) is not int
        or payload["schema_version"] != 1
    ):
        raise ValueError("selection must have supported artifact_kind and schema_version 1")
    packages = payload.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("packages must be a non-empty list")
    members = []
    for item in packages:
        if not isinstance(item, dict):
            raise ValueError("each package must be a mapping")
        member = {
            key: _text(item.get(key), f"package.{key}")
            for key in ("id", "namespace", "version", "source", "source_sha256", "ir", "ir_sha256")
        }
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", member["version"]):
            raise ValueError("package version must be an exact version")
        if not _DIGEST.fullmatch(member["source_sha256"]) or not _DIGEST.fullmatch(
            member["ir_sha256"]
        ):
            raise ValueError("package hashes must be lowercase SHA-256 hex")
        members.append(member)
    profiles = payload.get("profiles", [])
    if not isinstance(profiles, list):
        raise ValueError("profiles must be a list")
    selected_profiles = tuple(sorted(_text(p, "profile") for p in profiles))
    if len(set(selected_profiles)) != len(selected_profiles):
        raise ValueError("duplicate profile")
    composition = payload.get("composition")
    if not isinstance(composition, dict) or composition != {
        "dependency_rule": "explicit",
        "name_resolution_rule": "qualified",
    }:
        raise ValueError("composition must declare explicit dependencies and qualified names")
    return (
        sorted(members, key=lambda m: (m["id"], m["namespace"], m["version"])),
        selected_profiles,
        tuple(sorted(composition.items())),
    )


def capture_project_context(
    project_root: Path,
    *,
    project_id: str,
    selection_path: Path | None,
    ontologyc: Path | None,
    compiler_sha256: str | None = None,
) -> ContextResult:
    """Capture once. The caller selects and trusts the compiler; no installation occurs."""
    root = Path(project_root).resolve()
    checks: list[CheckResult] = []
    snapshots: list[OntologySnapshot] = []
    captured_members: list[tuple[str, str, str]] = []
    identities: tuple[tuple[str, str, str], ...] = ()
    profiles: tuple[str, ...] = ()
    rules: tuple[tuple[str, str], ...] = ()
    members: list[dict[str, str]] = []
    revision = None
    selection_ref = str(selection_path) if selection_path is not None else None

    def add(check: str, outcome: str, detail: str, package: str | None = None) -> None:
        checks.append(CheckResult(check, outcome, detail, package))

    if not project_id or not isinstance(project_id, str):
        add("project", "invalid", "project_id is required")
    if not root.is_dir():
        add("workspace", "unavailable", "workspace does not exist")
    if selection_path is None:
        add("selection", "unavailable", "no project ontology context selected")
    else:
        try:
            selection = _path(root, selection_path)
            payload = _load_yaml(selection.read_bytes())
            members, profiles, rules = _parse(payload)
            identities = tuple((m["id"], m["namespace"], m["version"]) for m in members)
            if profiles == ("ontologyc-structural-v1",):
                add("profile", "verified", "supported structural checking profile")
            else:
                add("profile", "unavailable", "required checking profile missing or unsupported")
            ids = [m["id"] for m in members]
            namespaces = [m["namespace"] for m in members]
            if len(ids) != len(set(ids)) or len(namespaces) != len(set(namespaces)):
                add("selection", "invalid", "duplicate package identity or namespace")
            else:
                add("selection", "verified", "explicit package selection parsed")
        except FileNotFoundError:
            add("selection", "unavailable", "selection file unavailable")
        except (ValueError, yaml.YAMLError, OSError, UnicodeError) as error:
            add("selection", "invalid", str(error))

    if compiler_sha256 is not None and (
        not isinstance(compiler_sha256, str) or not _DIGEST.fullmatch(compiler_sha256)
    ):
        add("compiler", "invalid", "compiler_sha256 must be lowercase SHA-256 hex")
    if ontologyc is None or not Path(ontologyc).is_file() or not os.access(ontologyc, os.X_OK):
        add("compiler", "unavailable", "operator-provided executable is unavailable")
    else:
        add(
            "compiler",
            "verified",
            "operator-provided executable available; provenance not verified",
        )

    for member in members:
        package = member["id"]
        try:
            source = _path(root, member["source"])
            ir = _path(root, member["ir"])
            if not source.is_file() or not ir.is_file():
                add("member_capture", "unavailable", "source or saved IR unavailable", package)
                add("dependency_closure", "unavailable", "member inputs unavailable", package)
                continue
            if (
                ontologyc is None
                or not Path(ontologyc).is_file()
                or not os.access(ontologyc, os.X_OK)
            ):
                add(
                    "compiler", "unavailable", "compiler unavailable during member capture", package
                )
                add(
                    "member_capture",
                    "unavailable",
                    "compiler unavailable during member capture",
                    package,
                )
                add("dependency_closure", "unavailable", "member inputs not checked", package)
                continue
            snapshot = capture_ontology_snapshot(
                source,
                Path(ontologyc),
                expected_ir_path=ir,
                expected_compiler_sha256=compiler_sha256,
            )
            snapshots.append(snapshot)
            captured_members.append((member["id"], member["namespace"], member["version"]))
            source_data = _load_yaml(snapshot.source_bytes)
            ir_data = json.loads(snapshot.ir_bytes)
            metadata = source_data.get("metadata") if isinstance(source_data, dict) else None
            if not isinstance(metadata, dict):
                raise ValueError("source metadata is missing")
            expected = (member["id"], member["namespace"], member["version"])
            if (
                tuple(metadata.get(k) for k in ("id", "namespace", "version")) != expected
                or tuple(ir_data.get(k) for k in ("id", "namespace", "version")) != expected
            ):
                raise ValueError("source or IR package identity does not match selection")
            if (
                snapshot.source_sha256 != member["source_sha256"]
                or snapshot.ir_sha256 != member["ir_sha256"]
            ):
                raise ValueError("captured source or IR hash does not match selection")
            add("member_capture", "verified", "source, IR and package identity checked", package)
            source_spec = source_data.get("spec")
            if not isinstance(source_spec, dict):
                raise ValueError("source spec must be a mapping")
            imports = source_spec.get("imports", [])
            if not isinstance(imports, list) or ir_data.get("imports", []) != imports:
                raise ValueError("source and IR imports differ or are malformed")
            if imports or len(members) > 1:
                add(
                    "dependency_closure",
                    "unavailable",
                    "dependency closure and composition checks are unsupported",
                    package,
                )
            else:
                add("dependency_closure", "verified", "single package declares no imports", package)
        except OntologySnapshotError as error:
            add("member_capture", error.outcome, str(error), package)
        except FileNotFoundError:
            add("member_capture", "unavailable", "source or saved IR unavailable", package)
        except (ValueError, yaml.YAMLError, UnicodeError) as error:
            add("member_capture", "invalid", str(error), package)
        except OSError as error:
            add("member_capture", "unavailable", str(error), package)

    if (
        members
        and len(snapshots) == len(members)
        and len({s.compiler_sha256 for s in snapshots}) != 1
    ):
        add("compiler", "invalid", "compiler changed between member captures")
    if not members or len(snapshots) != len(members):
        add("context_capture", "unavailable", "selected context capture is incomplete")
    facts = ContextFacts(tuple(checks))
    outcome = (
        "invalid"
        if INVALID_SPEC.is_satisfied_by(facts)
        else "unavailable"
        if UNAVAILABLE_SPEC.is_satisfied_by(facts)
        else "verified"
    )
    if members and len(snapshots) == len(members) and outcome != "invalid":
        identity = {
            "members": [
                {
                    "id": m["id"],
                    "namespace": m["namespace"],
                    "version": m["version"],
                    "source": m["source"],
                    "ir": m["ir"],
                    "source_sha256": s.source_sha256,
                    "ir_sha256": s.ir_sha256,
                }
                for m, s in zip(members, snapshots, strict=True)
            ],
            "compiler_sha256": snapshots[0].compiler_sha256,
            "profiles": profiles,
            "composition": dict(rules),
        }
        revision = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
        )
    if outcome == "verified" and revision is None:
        add("context_revision", "unavailable", "context revision could not be constructed")
        outcome = "unavailable"
    return ContextResult(
        project_id,
        str(root),
        selection_ref,
        outcome,
        revision,
        tuple(snapshots),
        tuple(captured_members),
        tuple(checks),
        identities,
        profiles,
        rules,
    )
