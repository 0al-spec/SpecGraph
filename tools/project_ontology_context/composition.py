"""A bounded, explicitly selected motivation/events dependency closure."""

from __future__ import annotations

from dataclasses import dataclass

from . import foundation
from .model import CheckResult, ReferenceSite, ResolvedImport

PROFILE = "ontologyc-motivation-composition-v1"
MOTIVATION = ("org.0al.motivation.core", "motivcore", "0.1.0")
EVENTS = ("org.0al.events.core", "eventcore", "0.2.0")
FOUNDATION = (foundation.PIN.id, foundation.PIN.namespace, foundation.PIN.version)


@dataclass(frozen=True, slots=True)
class PackageDeclarations:
    identity: tuple[str, str, str]
    source: str
    source_sha256: str
    imports: tuple[tuple[str, str, str], ...]
    classes: frozenset[str]
    protocols: frozenset[str]
    references: tuple[tuple[str, str, str], ...]


def declarations(member: dict, source: dict) -> PackageDeclarations:
    """Parse already hash-checked source bytes at the capture boundary."""
    spec = source["spec"]
    imports = spec.get("imports", [])
    if not isinstance(imports, list) or any(
        not isinstance(row, dict)
        or set(row) != {"id", "namespace", "version"}
        or any(not isinstance(v, str) or not v for v in row.values())
        for row in imports
    ):
        raise ValueError("Malformed explicit imports")
    references = tuple(foundation.reference_sites(spec))
    if any(not isinstance(ref, str) or not ref for _, ref, _ in references):
        raise ValueError("Malformed structural reference")
    return PackageDeclarations(
        tuple(member[k] for k in ("id", "namespace", "version")),
        member["source"],
        member["source_sha256"],
        tuple(tuple(row[k] for k in ("id", "namespace", "version")) for row in imports),
        frozenset(spec["classes"]),
        frozenset(spec.get("protocols", {})),
        references,
    )


def check_packages(
    packages: tuple[PackageDeclarations, ...],
    vocabulary: dict[str, set[str]],
    selected: tuple[tuple[str, str, str], ...],
) -> tuple[list[CheckResult], tuple[ResolvedImport, ...]]:
    """Resolve declared edges and concept slots; do not infer semantic acceptance."""
    checks: list[CheckResult] = []
    by_id = {p.identity[0]: p for p in packages}
    identities = {p[0]: p for p in selected}
    roots = [p for p in selected if p[0] not in {MOTIVATION[0], EVENTS[0]}]

    def closure(outcome: str, detail: str, package: str | None = None) -> None:
        checks.append(CheckResult("dependency_closure", outcome, detail, package))

    for expected in (MOTIVATION, EVENTS):
        package = identities.get(expected[0])
        if package is None:
            closure("invalid", f"Missing selected dependency {expected}")
        elif package != expected:
            closure("invalid", f"Incompatible dependency pin; expected {expected}", expected[0])
    if len(roots) != 1:
        closure(
            "unavailable", "Profile requires one project package plus motivation-core/events-core"
        )
    if any(p[0] == FOUNDATION[0] or p[1] == FOUNDATION[1] for p in selected):
        closure("invalid", "Selected package shadows the pinned foundation")
    if {p.identity for p in packages} != set(selected):
        closure("unavailable", "Not all selected package declarations were captured")

    for package in packages:
        identity = package.identity
        pid = identity[0]
        if len(package.imports) != len(set(package.imports)):
            closure("invalid", "Duplicate import declaration", pid)
        if pid == MOTIVATION[0] and set(package.imports) != {FOUNDATION, EVENTS}:
            closure(
                "invalid", "motivation-core must import the pinned foundation and events-core", pid
            )
        if pid == EVENTS[0] and set(package.imports) != {FOUNDATION}:
            closure("invalid", "events-core must import only the pinned foundation", pid)
        if identity in roots and MOTIVATION not in package.imports:
            closure("invalid", "Project package must explicitly import motivation-core", pid)

        visible = {identity[1]: identity}
        for dependency in package.imports:
            target = (
                FOUNDATION if dependency[0] == FOUNDATION[0] else (identities.get(dependency[0]))
            )
            if target != dependency or dependency == identity:
                closure("invalid", f"Missing, incompatible or self import {dependency}", pid)
            elif dependency[1] in visible:
                closure("invalid", f"Ambiguous imported namespace {dependency[1]}", pid)
            else:
                visible[dependency[1]] = dependency

        for pointer, name, role in package.references:
            namespace, separator, symbol = name.partition(":")
            if not separator:
                namespace, symbol = identity[1], name
            target = visible.get(namespace)
            accepted: frozenset[str] | set[str] = frozenset()
            unavailable = False
            if target == FOUNDATION:
                accepted = vocabulary[role]
            elif target is not None:
                captured_target = by_id.get(target[0])
                if captured_target is None:
                    unavailable = True
                elif role != "policy_base":
                    accepted = (
                        captured_target.protocols
                        if role == "protocols"
                        else captured_target.classes
                    )
            valid = symbol in accepted
            section = "protocols" if role == "protocols" else "classes"
            uri = f"ontology://{target[0]}/{target[2]}/{section}/{symbol}" if valid else None
            checks.append(
                CheckResult(
                    "name_resolution",
                    "unavailable" if unavailable else "verified" if valid else "invalid",
                    f"{pointer}: dependency exports unavailable for {name}"
                    if unavailable
                    else f"{pointer}: {name} -> {uri}"
                    if valid
                    else (
                        f"{pointer}: unresolved {role} reference {name}; "
                        "imported names require qualification"
                    ),
                    pid,
                    ReferenceSite(pointer, name, uri),
                )
            )

    resolved = (foundation.PIN,) + tuple(
        ResolvedImport(*p.identity, p.source, p.source_sha256)
        for p in sorted(packages, key=lambda p: p.identity)
        if p.identity[0] in {MOTIVATION[0], EVENTS[0]}
    )
    if not any(c.outcome != "verified" for c in checks):
        closure(
            "verified", "Pinned project/motivation/events/foundation closure and references checked"
        )
    return checks, resolved
