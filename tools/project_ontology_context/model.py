"""Immutable facts and results for a project ontology capture."""

from __future__ import annotations

from dataclasses import dataclass

from ontology_snapshot import OntologySnapshot


@dataclass(frozen=True, slots=True)
class CheckResult:
    check: str
    outcome: str
    detail: str
    package: str | None = None

    def report(self) -> dict[str, object]:
        return {
            "check": self.check,
            "outcome": self.outcome,
            "detail": self.detail,
            "package": self.package,
        }


@dataclass(frozen=True, slots=True)
class ContextFacts:
    checks: tuple[CheckResult, ...]


@dataclass(frozen=True, slots=True)
class ContextResult:
    project_id: str
    workspace: str
    selection_path: str | None
    outcome: str
    revision: str | None
    snapshots: tuple[OntologySnapshot, ...]
    captured_members: tuple[tuple[str, str, str], ...]
    checks: tuple[CheckResult, ...]
    members: tuple[tuple[str, str, str], ...]
    profiles: tuple[str, ...]
    rules: tuple[tuple[str, str], ...]

    def report(self) -> dict[str, object]:
        return {
            "artifact_kind": "project_ontology_context_report",
            "schema_version": 1,
            "project_id": self.project_id,
            "workspace": self.workspace,
            "selection_path": self.selection_path,
            "outcome": self.outcome,
            "context_revision": self.revision,
            "members": [{"id": x[0], "namespace": x[1], "version": x[2]} for x in self.members],
            "profiles": list(self.profiles),
            "composition": dict(self.rules),
            "snapshots": [
                {
                    "id": m[0],
                    "namespace": m[1],
                    "version": m[2],
                    "source_sha256": s.source_sha256,
                    "ir_sha256": s.ir_sha256,
                    "compiler_sha256": s.compiler_sha256,
                    "compiler_provenance": s.compiler_provenance,
                }
                for m, s in zip(self.captured_members, self.snapshots, strict=True)
            ],
            "checks": [check.report() for check in self.checks],
            "semantic_approval": "not_established",
            "canonical_mutations_allowed": False,
        }
