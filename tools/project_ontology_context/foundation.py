"""Resolve one explicitly pinned foundation import against the release's glossary."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from pathlib import Path

from .invalid_spec import INVALID_SPEC
from .model import CheckResult, ContextFacts, ReferenceSite, ResolvedImport

PROFILE = "ontologyc-foundation-v1"
PIN = ResolvedImport(
    id="specgraph.foundation",
    namespace="sg",
    version="0.1.0",
    source_uri="https://github.com/0al-spec/Ontology/blob/d831e25b46095dfea5e17befbc88c5fdcd03e031/SPECS/ontology/glossary.md",
    source_sha256="0f0d543da04e8250be4711e7785cb7318ae0e43c594c2f1cc4970c63207e1910",
)
GLOSSARY = Path(__file__).parent / "pinned_foundation/glossary.txt"


def _terms(text: str, section: str) -> set[str]:
    table = text.split(f"## {section}\n", 1)[1].split("\n## ", 1)[0].split("|---|---|", 1)[1]
    return set(re.findall(r"^\| ([A-Z][a-zA-Z0-9_]*) \|", table, re.MULTILINE))


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

    if member_count != 1 or spec.get("imports") != [
        {"id": PIN.id, "namespace": PIN.namespace, "version": PIN.version}
    ]:
        return [
            closure(
                "unavailable",
                "Profile requires one member importing specgraph.foundation@0.1.0 as sg",
            )
        ], ()
    if package == PIN.id or member["namespace"] == PIN.namespace:
        return [
            closure("invalid", "Selected member shadows the foundation identity or namespace")
        ], ()
    try:
        data = GLOSSARY.read_bytes()
    except OSError as error:
        return [closure("unavailable", f"Pinned foundation vocabulary unavailable: {error}")], ()
    if hashlib.sha256(data).hexdigest() != PIN.source_sha256:
        return [closure("invalid", "Foundation glossary SHA-256 differs from the release pin")], ()

    text = data.decode("utf-8")
    kinds = _terms(text, "Foundation Kinds")
    vocab = {
        "classes": kinds,
        "protocols": _terms(text, "Protocols"),
        "policy_base": kinds & {"Policy"},
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
