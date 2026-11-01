"""A lossless advisory vocabulary over captured packages, never a synthetic IR."""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass

from ontology_snapshot import OntologySnapshot, OntologySnapshotError, parse_ontology_ir
from spec_ontology_binding_index import symbol_keys

from . import composition, foundation
from .model import ContextResult


def spelling_keys(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    if not any(char.isalnum() for char in normalized):
        return set()
    if value.isascii():
        return symbol_keys(value)
    key = "-".join("".join(c if c.isalnum() else " " for c in normalized).split())
    return {key, key.replace("-", "")}


@dataclass(frozen=True, slots=True)
class VocabularySymbol:
    reference: str
    name: str
    kind: str
    aliases: tuple[str, ...]
    package: tuple[str, str, str]
    source_sha256: str
    ir_sha256: str | None
    compiler_sha256: str | None
    source_uri: str | None = None
    domain: str | None = None
    range: str | None = None

    def origin(self) -> dict[str, object]:
        section = "classes" if self.kind == "class" else "relations"
        return {
            "ontology_ref": self.reference,
            "ontology_uri": f"ontology://{self.package[0]}/{self.package[2]}/{section}/{self.name}",
            "package": dict(zip(("id", "namespace", "version"), self.package, strict=True)),
            "source_sha256": self.source_sha256,
            "ir_sha256": self.ir_sha256,
            "compiler_sha256": self.compiler_sha256,
            "source_uri": self.source_uri,
            "verification": "compiler_checked" if self.ir_sha256 else "pinned_export_catalog",
        }


@dataclass(frozen=True, slots=True)
class CapturedVocabulary:
    packages: tuple[tuple[tuple[str, str, str], OntologySnapshot], ...]
    symbols: tuple[VocabularySymbol, ...]
    composed: bool

    def candidates(self, term: str) -> tuple[VocabularySymbol, ...]:
        if ":" in term:
            return tuple(s for s in self.symbols if s.reference == term)
        keys = spelling_keys(term)
        return tuple(
            s
            for s in self.symbols
            if any(keys & spelling_keys(name) for name in (s.name, s.reference, *s.aliases))
        )

    def metadata(self, context: ContextResult) -> dict[str, object]:
        members = [
            {
                **dict(zip(("id", "namespace", "version"), member, strict=True)),
                "source_sha256": snapshot.source_sha256,
                "ir_sha256": snapshot.ir_sha256,
                "compiler_sha256": snapshot.compiler_sha256,
                "compiler_provenance": snapshot.compiler_provenance,
            }
            for member, snapshot in self.packages
        ]
        metadata = {
            "project_id": context.project_id,
            "workspace": context.workspace,
            "context_revision": context.revision,
            "context_outcome": context.outcome,
            "scope": "selected_composition_symbols"
            if self.composed
            else "single_member_local_symbols",
            "verified_closure": self.composed,
            "analysis_profile": "specgraph-composed-symbol-advisory-v1"
            if self.composed
            else "specgraph-local-symbol-advisory-v1",
            "semantic_approval": "not_established",
            "binding_authority": "structural_advisory_only",
        }
        if self.composed:
            metadata.update(
                members=members,
                foundation_catalog={
                    "id": foundation.PIN.id,
                    "namespace": foundation.PIN.namespace,
                    "version": foundation.PIN.version,
                    "source_uri": foundation.PIN.source_uri,
                    "source_sha256": foundation.PIN.source_sha256,
                },
            )
        else:
            metadata.update(
                selected_member={k: members[0][k] for k in ("id", "namespace", "version")},
                **{
                    k: members[0][k]
                    for k in (
                        "source_sha256",
                        "ir_sha256",
                        "compiler_sha256",
                        "compiler_provenance",
                    )
                },
            )
        return metadata


def capture_vocabulary(context: ContextResult) -> CapturedVocabulary:
    """Validate captured identities/digests; do not open source or saved IR paths."""
    composed = len(context.members) > 1
    if composed and context.profiles != (composition.PROFILE,):
        raise OntologySnapshotError(
            "multiple-member vocabulary requires the supported composition profile",
            outcome="unavailable",
        )
    if (
        not context.members
        or len(context.snapshots) != len(context.members)
        or len(context.captured_members) != len(context.members)
    ):
        raise OntologySnapshotError("all selected members must be captured", outcome="unavailable")
    if sorted(context.captured_members) != sorted(context.members) or len(
        set(context.members)
    ) != len(context.members):
        raise OntologySnapshotError("captured member identity differs from selection")
    if composed and (
        context.outcome != "verified" or foundation.PIN not in context.resolved_imports
    ):
        raise OntologySnapshotError(
            "joint vocabulary requires verified pinned closure", outcome="unavailable"
        )
    packages = tuple(
        sorted(zip(context.captured_members, context.snapshots, strict=True), key=lambda p: p[0])
    )
    symbols = []
    for member, snapshot in packages:
        checks = [
            c for c in context.checks if c.check == "member_capture" and c.package == member[0]
        ]
        if len(checks) != 1 or checks[0].outcome != "verified":
            raise OntologySnapshotError(
                "selected member lacks one successful capture check", outcome="unavailable"
            )
        if (
            hashlib.sha256(snapshot.source_bytes).hexdigest() != snapshot.source_sha256
            or hashlib.sha256(snapshot.ir_bytes).hexdigest() != snapshot.ir_sha256
        ):
            raise OntologySnapshotError("captured source or IR digest mismatch")
        ir = parse_ontology_ir(snapshot.ir_bytes)
        if (
            not isinstance(ir, dict)
            or tuple(ir.get(k) for k in ("id", "namespace", "version")) != member
        ):
            raise OntologySnapshotError("captured IR identity differs from selection")
        source_uri = next(
            (
                imported.source_uri
                for imported in context.resolved_imports
                if (imported.id, imported.namespace, imported.version) == member
                and imported.source_sha256 == snapshot.source_sha256
            ),
            None,
        )
        for section, kind in (("classes", "class"), ("relations", "relation")):
            rows = ir.get(section, [])
            if not isinstance(rows, list):
                raise OntologySnapshotError(f"IR {section} must be a list")
            for row in rows:
                if not isinstance(row, dict) or not all(
                    isinstance(row.get(k), str) for k in ("id", "fqid")
                ):
                    raise OntologySnapshotError(f"malformed IR {section} declaration")
                if row["fqid"] != f"{member[1]}:{row['id']}":
                    raise OntologySnapshotError("IR symbol namespace differs from selected member")
                aliases = row.get("aliases", [])
                symbols.append(
                    VocabularySymbol(
                        row["fqid"],
                        row["id"],
                        kind,
                        tuple(a for a in aliases if isinstance(a, str))
                        if isinstance(aliases, list)
                        else (),
                        member,
                        snapshot.source_sha256,
                        snapshot.ir_sha256,
                        snapshot.compiler_sha256,
                        source_uri,
                        domain=row.get("domain") if isinstance(row.get("domain"), str) else None,
                        range=row.get("range") if isinstance(row.get("range"), str) else None,
                    )
                )
    if composed:
        try:
            catalog = foundation.capture_vocabulary()
        except OSError as error:
            raise OntologySnapshotError(
                f"pinned foundation catalog unavailable: {error}", outcome="unavailable"
            ) from error
        for name in sorted(catalog["classes"]):
            symbols.append(
                VocabularySymbol(
                    f"sg:{name}",
                    name,
                    "class",
                    (),
                    composition.FOUNDATION,
                    foundation.PIN.source_sha256,
                    None,
                    None,
                    foundation.PIN.source_uri,
                )
            )
    return CapturedVocabulary(
        packages, tuple(sorted(symbols, key=lambda s: (s.reference, s.kind))), composed
    )
