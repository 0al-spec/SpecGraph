"""Resolve one explicitly pinned foundation import against the compiler's versioned exports."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from pathlib import Path

from ontology_snapshot import OntologySnapshotError, OntologySourceRejection

from .invalid_spec import INVALID_SPEC
from .model import CheckResult, CompilerDiagnostic, ContextFacts, ReferenceSite, ResolvedImport

PROFILE = "ontologyc-foundation-v1"
PIN = ResolvedImport(
    id="specgraph.foundation",
    namespace="sg",
    version="0.1.0",
    source_uri="https://github.com/0al-spec/Ontology/blob/0fcc94469d971aaf39fcc182bc5c6b8acff37fd2/SPECS/ontology/foundation/0.1.0/exports.json",
    source_sha256="ef07cf4e8dd4cdc8c8dd583971fc3cabfe82e4b00fb0e680b6d1db48cfe262ad",
)
EXPORTS = Path(__file__).parent / "pinned_foundation/exports.json"


def _reference_sites(spec: dict) -> Iterator[tuple[str, str, str]]:
    """Qualified concept slots from v1alpha1. Text, labels and field values are data."""
    for name, cls in spec["classes"].items():
        path = f"/spec/classes/{name}"
        yield path + "/extends", cls["extends"], "classes"
        for i, ref in enumerate(cls.get("implements", [])):
            yield f"{path}/implements/{i}", ref, "protocols"
    for name, rel in spec["relations"].items():
        path = f"/spec/relations/{name}"
        yield path + "/domain", rel["domain"], "classes"
        target = rel["range"]
        if isinstance(target, str):
            yield path + "/range", target, "classes"
        else:
            for i, ref in enumerate(target["oneOf"]):
                yield f"{path}/range/oneOf/{i}", ref, "classes"
    for name, policy in spec.get("policies", {}).items():
        path = f"/spec/policies/{name}"
        yield path + "/extends", policy["extends"], "policy_base"
        for i, ref in enumerate(policy["appliesTo"]):
            yield f"{path}/appliesTo/{i}", ref, "classes"


def _external(ref: str, package_namespace: str) -> bool:
    namespace, separator, _ = ref.partition(":")
    return bool(separator) and namespace != package_namespace


def failed_capture_checks(
    source: dict, member: dict, member_count: int, rejection: OntologySnapshotError
) -> Iterator[CheckResult]:
    """Bind compiler reference errors to existing fields in the same captured source."""
    spec = source.get("spec")
    if not isinstance(spec, dict):
        return
    issue = _scope_issue(spec, member, member_count)
    if issue is not None:
        yield issue
        return
    if not isinstance(rejection, OntologySourceRejection):
        return
    symbol = r"[A-Za-z][A-Za-z0-9_]*"
    sites = {
        "class.extends.unresolved": rf"classes\.{symbol}\.extends",
        "protocol.unresolved": rf"classes\.{symbol}\.implements\[[0-9]+\]",
        "relation.domain.unresolved": rf"relations\.{symbol}\.domain",
        "relation.range.unresolved": rf"relations\.{symbol}\.range(?:\.oneOf\[[0-9]+\])?",
        "policy.extends.unresolved": rf"policies\.{symbol}\.extends",
        "policy.appliesTo.unresolved": rf"policies\.{symbol}\.appliesTo\[[0-9]+\]",
    }
    for code, field, message in rejection.diagnostics:
        if code not in sites or not re.fullmatch(r"spec\." + sites[code], field):
            continue
        parts = re.findall(r"[A-Za-z][A-Za-z0-9_]*|[0-9]+", field)
        value = source
        for key in parts:
            if isinstance(value, dict):
                value = value.get(key)
            elif (
                isinstance(value, list)
                and key.isdigit()
                and len(key) <= len(str(len(value)))
                and int(key) < len(value)
            ):
                value = value[int(key)]
            else:
                break
        else:
            if isinstance(value, str) and value.startswith(PIN.namespace + ":"):
                yield CheckResult(
                    "name_resolution",
                    "invalid",
                    message,
                    member["id"],
                    ReferenceSite("/" + "/".join(parts), value),
                    compiler_diagnostic=CompilerDiagnostic(
                        code, rejection.source_sha256, rejection.compiler_sha256
                    ),
                )


def _scope_issue(spec: dict, member: dict, member_count: int) -> CheckResult | None:
    package = member["id"]
    if member_count != 1 or spec.get("imports") != [
        {"id": PIN.id, "namespace": PIN.namespace, "version": PIN.version}
    ]:
        return CheckResult(
            "dependency_closure",
            "unavailable",
            "Profile requires one member importing specgraph.foundation@0.1.0 as sg",
            package,
        )
    if package == PIN.id or member["namespace"] == PIN.namespace:
        return CheckResult(
            "dependency_closure",
            "invalid",
            "Selected member shadows the foundation identity or namespace",
            package,
        )
    return None


def _resolve(
    path: str, ref: str, role: str, vocab: dict[str, set[str]], package: str
) -> CheckResult:
    namespace, _, name = ref.partition(":")
    if namespace != PIN.namespace or name not in vocab[role]:
        return CheckResult(
            "name_resolution",
            "invalid",
            f"{path}: unresolved {role} reference {ref}",
            package,
            ReferenceSite(path, ref),
        )
    section = "protocols" if role == "protocols" else "classes"
    uri = f"ontology://{PIN.id}/{PIN.version}/{section}/{name}"
    return CheckResult(
        "name_resolution",
        "verified",
        f"{path}: {ref} -> {uri}",
        package,
        ReferenceSite(path, ref, uri),
    )


def check_import(
    spec: dict, member: dict, member_count: int
) -> tuple[list[CheckResult], tuple[ResolvedImport, ...]]:
    package = member["id"]

    def closure(outcome: str, detail: str) -> CheckResult:
        return CheckResult("dependency_closure", outcome, detail, package)

    issue = _scope_issue(spec, member, member_count)
    if issue is not None:
        return [issue], ()
    try:
        data = EXPORTS.read_bytes()
    except OSError as error:
        return [closure("unavailable", f"Pinned foundation vocabulary unavailable: {error}")], ()
    if hashlib.sha256(data).hexdigest() != PIN.source_sha256:
        return [closure("invalid", "Foundation exports SHA-256 differs from the release pin")], ()

    catalog = json.loads(data)
    vocab = {
        "classes": set(catalog["classes"]),
        "protocols": set(catalog["protocols"]),
        "policy_base": set(catalog["policyBases"]),
    }
    try:
        checks = [
            _resolve(path, ref, role, vocab, package)
            for path, ref, role in _reference_sites(spec)
            if _external(ref, member["namespace"])
        ]
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        return [closure("invalid", f"Malformed captured reference declaration: {error}")], (PIN,)
    if INVALID_SPEC.is_satisfied_by(ContextFacts(tuple(checks))):
        checks.append(
            closure("invalid", "The selected foundation import has unresolved references")
        )
    else:
        checks.append(
            closure("verified", "Pinned foundation vocabulary and qualified references checked")
        )
    return checks, (PIN,)
