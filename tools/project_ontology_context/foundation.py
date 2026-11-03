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
    id="ontology.foundation",
    namespace="ont",
    version="0.1.0",
    source_uri="https://github.com/0al-spec/Ontology/blob/c52553f872f440dde26c61abf9193f5fff171d98/SPECS/ontology/foundation/0.1.0/exports.json",
    source_sha256="1c6b3ac3e4aa9b4e56d823b3645f94c126840c1922c555998b848e9e0fe18f8f",
)
# The release catalog is canonical; existing packages retain their authored alias.
LEGACY_PIN = ResolvedImport(
    id="specgraph.foundation",
    namespace="sg",
    version=PIN.version,
    source_uri=PIN.source_uri,
    source_sha256=PIN.source_sha256,
)
PINS = (PIN, LEGACY_PIN)
EXPORTS = Path(__file__).parent / "pinned_foundation/exports.json"


def selected_import(spec: dict) -> ResolvedImport | None:
    """The profile supports the canonical and legacy default namespaces only."""
    return next(
        (
            pin
            for pin in PINS
            if spec.get("imports")
            == [{"id": pin.id, "namespace": pin.namespace, "version": pin.version}]
        ),
        None,
    )


def reference_sites(spec: dict) -> Iterator[tuple[str, str, str]]:
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
            pin = selected_import(spec)
            if pin and isinstance(value, str) and value.startswith(pin.namespace + ":"):
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
    if member_count != 1 or selected_import(spec) is None:
        return CheckResult(
            "dependency_closure",
            "unavailable",
            "Profile requires one member importing ontology.foundation@0.1.0 as ont "
            "or legacy specgraph.foundation@0.1.0 as sg",
            package,
        )
    if any(package == pin.id or member["namespace"] == pin.namespace for pin in PINS):
        return CheckResult(
            "dependency_closure",
            "invalid",
            "Selected member shadows the foundation identity or namespace",
            package,
        )
    return None


def _resolve(
    path: str, ref: str, role: str, vocab: dict[str, set[str]], package: str, pin: ResolvedImport
) -> CheckResult:
    namespace, _, name = ref.partition(":")
    if namespace != pin.namespace or name not in vocab[role]:
        return CheckResult(
            "name_resolution",
            "invalid",
            f"{path}: unresolved {role} reference {ref}",
            package,
            ReferenceSite(path, ref),
        )
    section = "protocols" if role == "protocols" else "classes"
    uri = f"ontology://{pin.id}/{pin.version}/{section}/{name}"
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
    pin = selected_import(spec)
    assert pin is not None
    try:
        vocab = capture_vocabulary()
    except OSError as error:
        return [closure("unavailable", f"Pinned foundation vocabulary unavailable: {error}")], ()
    except ValueError as error:
        return [closure("invalid", str(error))], ()
    try:
        checks = [
            _resolve(path, ref, role, vocab, package, pin)
            for path, ref, role in reference_sites(spec)
            if _external(ref, member["namespace"])
        ]
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        return [closure("invalid", f"Malformed captured reference declaration: {error}")], (pin,)
    if INVALID_SPEC.is_satisfied_by(ContextFacts(tuple(checks))):
        checks.append(
            closure("invalid", "The selected foundation import has unresolved references")
        )
    else:
        checks.append(
            closure("verified", "Pinned foundation vocabulary and qualified references checked")
        )
    return checks, (pin,)


def capture_vocabulary() -> dict[str, set[str]]:
    """Read and verify one immutable release catalog before resolving references."""
    data = EXPORTS.read_bytes()
    if hashlib.sha256(data).hexdigest() != PIN.source_sha256:
        raise ValueError("Foundation exports SHA-256 differs from the release pin")
    catalog = json.loads(data)
    return {
        "classes": set(catalog["classes"]),
        "protocols": set(catalog["protocols"]),
        "policy_base": set(catalog["policyBases"]),
    }
