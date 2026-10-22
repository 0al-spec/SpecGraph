"""Collect publication declarations from explicitly pinned Git blobs, without imports."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from intent_decision_review.sources import (
    GitSources,
    declaration_name,
    digest,
    normalized_path,
    revision,
    strict_json,
)
from publication_evidence.bindings_spec import BINDING_ERROR_SPEC
from publication_evidence.context import BindingContext
from spec_yaml import load_yaml_text

from .atom_roles_spec import ATOM_ROLES_SPEC
from .context import (
    AtomRolesFacts,
    Declaration,
    DeclaredReference,
    PolicyAtomBindingsFacts,
    ReferenceResolution,
)
from .policy_atom_bindings_spec import POLICY_ATOM_BINDINGS_SPEC
from .references import PYTHON_KINDS, resolve_references, supported_reference

PROFILE = "specgraph.publication-exact-links/v1"


def analyzer_identity() -> dict[str, object]:
    """Identify the executing adapter separately from the measured Git revision."""
    tools = Path(__file__).resolve().parents[1]
    paths = [
        "publication_trace_links.py",
        "traceability/__init__.py",
        "traceability/context.py",
        "traceability/reference_status_spec.py",
        "traceability/references.py",
        "traceability/publication.py",
        "traceability/atom_roles_spec.py",
        "traceability/policy_atom_bindings_spec.py",
        "intent_decision_review/sources.py",
        "spec_yaml.py",
        "publication_evidence/bindings_spec.py",
        "publication_evidence/context.py",
    ]
    return {
        "version": "1.0.0",
        "files_sha256": {
            path: hashlib.sha256((tools / path).read_bytes()).hexdigest() for path in sorted(paths)
        },
    }


def mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def records(value: object, label: str) -> list[dict]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must be an object list")
    return value


def text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be nonempty unpadded text")
    return value


def texts(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a text list")
    return [text(item, label) for item in value]


class PublicationSources:
    def __init__(self, sources: GitSources, source_revision: str):
        self.sources = sources
        self.revision = source_revision
        self.manifest: dict[str, dict] = {}
        self.parsed: dict[str, ast.Module | None] = {}

    def blob(self, path: str) -> bytes:
        path = normalized_path(path)
        raw = self.sources.blob(self.revision, path)
        self.manifest[path] = {"status": "read", "sha256": hashlib.sha256(raw).hexdigest()}
        return raw

    def python_declarations(self, kind: str, reference: str) -> tuple[Declaration, ...]:
        path, symbol = reference.split("::")
        if path not in self.parsed:
            try:
                self.parsed[path] = ast.parse(self.blob(path), filename=path)
            except ValueError as error:
                self.manifest[path] = {
                    **self.manifest.get(path, {}),
                    "status": "unavailable",
                    "diagnostic": str(error),
                }
                self.parsed[path] = None
            except (SyntaxError, UnicodeError) as error:
                self.manifest[path] = {
                    **self.manifest[path],
                    "status": "unavailable",
                    "diagnostic": f"Python parse error: {error}",
                }
                self.parsed[path] = None
        tree = self.parsed[path]
        if tree is None:
            return ()
        # Only direct declarations qualify. Imports, aliases and dynamic exports
        # are not resolved by this bounded profile. Keep duplicate names visible.
        return tuple(
            Declaration(
                kind,
                reference,
                path,
                f"lines:{node.lineno}-{node.end_lineno}",
                self.manifest[path]["sha256"],
                "AnnotationOnly"
                if isinstance(node, ast.AnnAssign) and node.value is None
                else type(node).__name__,
            )
            for node in tree.body
            if declaration_name(node) == symbol
        )


@dataclass(frozen=True)
class PublicationLinkCollection:
    """One collection pass; immutable facts alongside the compatible JSON projection."""

    atom_declarations: tuple[Declaration, ...]
    resolutions: tuple[ReferenceResolution, ...]
    report_json: bytes

    def __post_init__(self) -> None:
        object.__setattr__(self, "atom_declarations", tuple(self.atom_declarations))
        object.__setattr__(self, "resolutions", tuple(self.resolutions))
        object.__setattr__(self, "report_json", bytes(self.report_json))

    def to_payload(self) -> dict[str, object]:
        return json.loads(self.report_json)


def collect_publication_links(
    repository_root: Path,
    source_ref: str,
    bindings_path: str = "tools/feature_passports/static-publication-bindings.json",
) -> PublicationLinkCollection:
    """Diagnostic only: inspect authored links, never run tests or grant readiness."""
    pin = revision(repository_root, source_ref)
    sources = PublicationSources(GitSources(repository_root, pin, pin), pin)
    bindings = mapping(strict_json(sources.blob(bindings_path)), "bindings")
    if type(bindings.get("schema_version")) is not int or bindings["schema_version"] != 1:
        raise ValueError("publication bindings require schema_version 1")
    spec_path = normalized_path(text(bindings.get("spec"), "bindings.spec"))
    passport_path = normalized_path(text(bindings.get("passport"), "bindings.passport"))
    node = load_yaml_text(sources.blob(spec_path).decode())
    passport = mapping(strict_json(sources.blob(passport_path)), "passport")
    if (
        passport.get("artifact_kind") != "feature_passport"
        or type(passport.get("schema_version")) is not int
        or passport["schema_version"] != 1
    ):
        raise ValueError("publication passport requires feature_passport schema_version 1")
    spec_id = text(node.get("id"), "spec.id")
    if node.get("kind") != "spec" or Path(spec_path).name != f"{spec_id}.yaml":
        raise ValueError("selected source must be the named canonical spec node")
    specification = mapping(node.get("specification"), "specification")
    atoms = records(mapping(node.get("atoms"), "atoms").get("intents"), "atoms.intents")
    criteria = records(
        mapping(specification.get("requirement"), "requirement").get("criteria"), "criteria"
    )
    declarations = []
    references = []
    findings = []

    def declare(kind: str, identity: str, path: str, location: str) -> None:
        if not supported_reference(kind, identity):
            raise ValueError(f"unsupported declared {kind} ID: {identity}")
        declarations.append(
            Declaration(kind, identity, path, location, sources.manifest[path]["sha256"])
        )

    def link(owner: str, relation: str, kind: str, target: str, path: str, location: str) -> None:
        references.append(DeclaredReference(owner, relation, kind, target, path, location))

    for i, atom in enumerate(atoms):
        identity = text(atom.get("id"), "atom.id")
        location = f"/atoms/intents/{i}"
        declare("atom", identity, spec_path, location)
        selectors = texts(atom.get("verifiable_by"), "verifiable_by")
        if not selectors or len(selectors) != len(set(selectors)):
            findings.append({"code": "empty_or_duplicate_atom_channels", "owner": identity})
        for j, selector in enumerate(selectors):
            link(
                identity,
                "verifiable_by",
                "pytest_function",
                selector,
                spec_path,
                f"{location}/verifiable_by/{j}",
            )
    for i, criterion in enumerate(criteria):
        identity = text(criterion.get("id"), "criterion.id")
        location = f"/specification/requirement/criteria/{i}"
        declare("criterion", identity, spec_path, location)
        link(
            identity,
            "intent_atom_id",
            "atom",
            text(criterion.get("intent_atom_id"), "intent_atom_id"),
            spec_path,
            f"{location}/intent_atom_id",
        )
    passport_criteria = records(
        mapping(
            mapping(passport.get("spec"), "passport.spec").get("intent"), "passport.intent"
        ).get("acceptance_criteria"),
        "passport.criteria",
    )
    obligations = records(bindings.get("obligations"), "bindings.obligations")
    passport_ids = [text(c.get("id"), "passport criterion.id") for c in passport_criteria]
    criterion_ids = [text(c.get("id"), "criterion.id") for c in criteria]
    binding_error = BINDING_ERROR_SPEC.decide(
        BindingContext(
            frozenset(passport_ids),
            frozenset(criterion_ids),
            tuple(text(item.get("criterion_id"), "criterion_id") for item in obligations),
            tuple(text(item.get("test"), "test") for item in obligations),
        )
    ).value
    if binding_error:
        findings.append({"code": "publication_binding_contract", "message": binding_error})
    if len(passport_ids) != len(set(passport_ids)):
        findings.append({"code": "duplicate_passport_criterion"})
    for i, criterion in enumerate(passport_criteria):
        identity = text(criterion.get("id"), "passport criterion.id")
        link(
            spec_id,
            "passport_criterion",
            "criterion",
            identity,
            passport_path,
            f"/spec/intent/acceptance_criteria/{i}/id",
        )
    atom_channels = {a["id"]: a["verifiable_by"] for a in atoms}
    criterion_atoms = {c["id"]: c["intent_atom_id"] for c in criteria}
    for i, obligation in enumerate(obligations):
        identity = text(obligation.get("criterion_id"), "criterion_id")
        location = f"/obligations/{i}"
        link(
            spec_id,
            "bound_criterion",
            "criterion",
            identity,
            bindings_path,
            f"{location}/criterion_id",
        )
        link(
            identity,
            "bound_test",
            "pytest_function",
            text(obligation.get("test"), "test"),
            bindings_path,
            f"{location}/test",
        )
        if obligation["test"] not in atom_channels.get(criterion_atoms.get(identity), []):
            findings.append({"code": "bound_test_not_declared_by_atom", "owner": identity})
    policies = records(bindings.get("policies"), "bindings.policies")
    bound_policy_atoms = []
    for i, policy in enumerate(policies):
        target = text(policy.get("specification"), "policy.specification")
        module, separator, symbol = target.rpartition(".")
        # Invalid module notation is retained as an unsupported exact reference.
        target_ref = (
            f"tools/{module.replace('.', '/')}.py::{symbol}"
            if separator and re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module)
            else target
        )
        policy_ids = texts(policy.get("atom_ids"), "policy.atom_ids")
        if not policy_ids:
            findings.append({"code": "empty_policy_atom_binding", "index": i})
        for j, atom_id in enumerate(policy_ids):
            bound_policy_atoms.append(atom_id)
            link(
                spec_id,
                "policy_atom",
                "atom",
                atom_id,
                bindings_path,
                f"/policies/{i}/atom_ids/{j}",
            )
            link(
                atom_id,
                "policy_declaration",
                "python_value",
                target_ref,
                bindings_path,
                f"/policies/{i}/specification",
            )
    policy_atoms = texts(
        mapping(specification.get("delivery_signals"), "delivery_signals").get("policy_atom_ids"),
        "policy_atom_ids",
    )
    if not POLICY_ATOM_BINDINGS_SPEC.is_satisfied_by(
        PolicyAtomBindingsFacts(tuple(bound_policy_atoms), tuple(policy_atoms))
    ):
        findings.append({"code": "policy_atom_bindings_incomplete_or_duplicate"})
    if not ATOM_ROLES_SPEC.is_satisfied_by(
        AtomRolesFacts(
            frozenset(atom_channels), frozenset(criterion_atoms.values()), frozenset(policy_atoms)
        )
    ):
        findings.append({"code": "atom_roles_incomplete"})
    implementation = text(bindings.get("implementation"), "implementation")
    symbol = text(bindings.get("symbol"), "symbol")
    link(
        spec_id,
        "implementation",
        "python_function",
        f"{implementation}::{symbol}",
        bindings_path,
        "/implementation",
    )

    unavailable = set()
    python_targets = sorted(
        {
            (item.target_kind, item.target)
            for item in references
            if item.target_kind in PYTHON_KINDS
            and supported_reference(item.target_kind, item.target)
        }
    )
    for kind, target in python_targets:
        declarations.extend(sources.python_declarations(kind, target))
        if sources.manifest[target.split("::")[0]]["status"] == "unavailable":
            unavailable.add((kind, target))
    resolutions = resolve_references(tuple(references), tuple(declarations), frozenset(unavailable))
    counts = Counter(item.status for item in resolutions)
    duplicate_ids = [
        {"kind": key[0], "id": key[1], "count": count}
        for key, count in sorted(Counter((d.kind, d.reference) for d in declarations).items())
        if key[0] not in PYTHON_KINDS and count > 1
    ]
    report = {
        "artifact_kind": "publication_trace_links",
        "schema_version": 1,
        "profile": PROFILE,
        "analyzer": analyzer_identity(),
        "source_revision": pin,
        "spec_id": spec_id,
        "source_lifecycle": {"status": node.get("status"), "gate_state": node.get("gate_state")},
        "atom_inventory": {
            "complete": not any(d["kind"] == "atom" for d in duplicate_ids),
            "declared_count": len(atoms),
            "unique_count": len({item["id"] for item in atoms}),
        },
        "sources": dict(sorted(sources.manifest.items())),
        "duplicate_ids": duplicate_ids,
        "findings": findings,
        "links": [item.to_payload() for item in resolutions],
        "resolution_counts": dict(sorted(counts.items())),
        "status": "resolved"
        if not duplicate_ids and not findings and all(r.status == "resolved" for r in resolutions)
        else "needs_review",
        "execution": "not_collected",
        "fulfillment": "not_evaluated",
        "admission": "not_evaluated",
        "readiness": "not_evaluated",
        "canonical_mutations_allowed": False,
    }
    return PublicationLinkCollection(
        tuple(d for d in declarations if d.kind == "atom"),
        resolutions,
        json.dumps({**report, "content_sha256": digest(report)}, allow_nan=False).encode(),
    )


def build_publication_links(
    repository_root: Path,
    source_ref: str,
    bindings_path: str = "tools/feature_passports/static-publication-bindings.json",
) -> dict[str, object]:
    """Preserve the diagnostic facade; provider callers reuse the collected facts."""
    return collect_publication_links(repository_root, source_ref, bindings_path).to_payload()
