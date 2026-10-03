#!/usr/bin/env python3
"""Measure proposed publication-policy classifications; never decide merge readiness."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from subject_source_git import git_command

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "tools/publication_policy_classification.json"
CATEGORIES = {"policy", "mechanics", "variant_behavior"}


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ValueError("classification paths must be canonical and repository-relative")
    return value


def read_source(root: Path, path: str, revision: str | None) -> str:
    relative_path(path)
    if revision:
        entry = git_command(root, "ls-tree", "-z", revision, "--", path).stdout
        if not entry or entry.split()[0] not in {b"100644", b"100755"}:
            raise ValueError(f"missing regular source blob: {path}")
        return git_command(root, "show", f"{revision}:{path}").stdout.decode("utf-8")
    selected = root / path
    if selected.is_symlink() or not selected.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"source is outside the selected root: {path}")
    return selected.read_text(encoding="utf-8")


def pin_revision(root: Path, revision: str) -> str:
    return (
        git_command(root, "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}")
        .stdout.decode()
        .strip()
    )


def message_label(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value if isinstance(part, ast.Constant) else "{}" for part in node.values
        )
    return ast.unparse(node)


@dataclass(frozen=True)
class Site:
    path: str
    symbol: str
    kind: str
    label: str
    line: int
    expression: ast.AST

    @property
    def location(self) -> str:
        return f"{self.path}::{self.symbol}"

    @property
    def predicate_sha256(self) -> str:
        return digest(ast.dump(self.expression, include_attributes=False))


class Sites(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.scope: list[str] = []
        self.sites: list[Site] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef

    def add(self, node: ast.AST, kind: str, label: str, expression: ast.AST) -> None:
        self.sites.append(
            Site(
                self.path, ".".join(self.scope) or "<module>", kind, label, node.lineno, expression
            )
        )

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "require" and len(node.args) == 2:
            self.add(node, "require", message_label(node.args[1]), node.args[0])
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self.add(node, "if", ast.unparse(node.test), node.test)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.add(node, "assert", ast.unparse(node.test), node.test)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.add(node, "conditional_expression", ast.unparse(node.test), node.test)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.add(node, "match", ast.unparse(node.subject), node.subject)
        self.generic_visit(node)


def validate_manifest(manifest: dict) -> dict:
    if (
        not isinstance(manifest, dict)
        or manifest.get("artifact_kind") != "publication_policy_classification"
        or type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != 1
        or manifest.get("classification_status") != "proposed"
    ):
        raise ValueError("expected a proposed version-1 publication classification")
    modules = manifest["modules"]
    paths = [relative_path(module["path"]) for module in modules]
    sites = manifest["sites"]
    ids = [site["id"] for site in sites]
    selectors = [(site["path"], site["kind"], site["label"]) for site in sites]
    if (
        len(paths) != len(set(paths))
        or len(ids) != len(set(ids))
        or len(selectors) != len(set(selectors))
    ):
        raise ValueError("module paths and site IDs must be unique")
    families = manifest["families"]
    family_ids = [family["id"] for family in families]
    if len(family_ids) != len(set(family_ids)):
        raise ValueError("family IDs must be unique")
    for site in sites:
        if site["category"] not in CATEGORIES or not site["rationale"].strip():
            raise ValueError("each site needs an explicit category and rationale")
        if site["category"] == "policy" and site["family_id"] not in family_ids:
            raise ValueError("policy sites need a declared semantic family")
        if site["path"] not in paths or site["kind"] not in {"require", "if"}:
            raise ValueError("site is outside the supported guard/dispatch scope")
        if not site["allowed_locations"] or not site["predicate_sha256"]:
            raise ValueError("site needs architectural locations and a predicate binding")
    for spec in manifest["specifications"]:
        if spec["path"] not in paths or spec["family_id"] not in family_ids:
            raise ValueError("specification is outside the declared scope")
    spec_keys = [(spec["path"], spec["symbol"]) for spec in manifest["specifications"]]
    if len(spec_keys) != len(set(spec_keys)):
        raise ValueError("specification bindings must be unique")
    if len({Path(path).stem for path in paths}) != len(paths):
        raise ValueError("the flat-module pilot requires distinct module names")
    for family in families:
        if not isinstance(family["allowed_definition_paths"], list) or any(
            path not in paths for path in family["allowed_definition_paths"]
        ):
            raise ValueError("definition homes must belong to the selected scope")
    return manifest


def import_bindings(tree: ast.Module) -> dict[str, tuple[str, str]]:
    return {
        alias.asname or alias.name: (node.module, alias.name)
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
        for alias in node.names
    }


def factory_present(tree: ast.Module, symbol: str, expected_sha256: str) -> bool:
    imports = import_bindings(tree)
    assignments = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments.append((node.target.id, node.value))
        elif isinstance(node, ast.Assign):
            assignments.extend(
                (target.id, node.value) for target in node.targets if isinstance(target, ast.Name)
            )
    values = [value for name, value in assignments if name == symbol]
    return (
        len(values) == 1
        and isinstance(values[0], ast.Call)
        and isinstance(values[0].func, ast.Name)
        and imports.get(values[0].func.id) == ("specification_core", "PredicateSpec")
        and values[0].func.id not in {name for name, _ in assignments}
        and digest(ast.dump(values[0], include_attributes=False)) == expected_sha256
    )


def receiver_shadowed(tree: ast.Module, name: str) -> bool:
    # Conservative within this bounded module: never credit an imported policy
    # name which is also assigned or bound as an argument/class/function.
    return any(
        (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id == name)
        or (isinstance(node, ast.arg) and node.arg == name)
        or (isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name)
        for node in ast.walk(tree)
    )


def snapshot(root: Path, manifest: dict, revision: str | None = None) -> dict:
    validate_manifest(manifest)
    trees: dict[str, ast.Module] = {}
    diagnostics: list[dict] = []
    sources = {}
    discovered = []
    for module in manifest["modules"]:
        path = module["path"]
        try:
            source = read_source(root, path, revision)
            sources[path] = hashlib.sha256(source.encode()).hexdigest()
            trees[path] = ast.parse(source)
            if module["inventory_guards"]:
                visitor = Sites(path)
                visitor.visit(trees[path])
                discovered.extend(visitor.sites)
        except (OSError, ValueError, SyntaxError) as exc:
            diagnostics.append({"code": "unreadable_source", "path": path, "detail": str(exc)})
    specifications = {}
    for spec in manifest["specifications"]:
        if spec["path"] in trees and factory_present(
            trees[spec["path"]], spec["symbol"], spec["predicate_sha256"]
        ):
            specifications[(Path(spec["path"]).stem, spec["symbol"])] = spec
        else:
            diagnostics.append({"code": "unresolved_specification", "definition": spec})
    resolved = []
    matched: set[tuple[str, int, str]] = set()
    for classified in manifest["sites"]:
        matches = [
            site
            for site in discovered
            if site.path == classified["path"]
            and site.kind == classified["kind"]
            and site.label == classified["label"]
        ]
        if len(matches) != 1:
            diagnostics.append(
                {"code": "unresolved_site", "site_id": classified["id"], "matches": len(matches)}
            )
            continue
        site = matches[0]
        matched.add((site.path, site.line, site.kind))
        if site.predicate_sha256 != classified["predicate_sha256"]:
            diagnostics.append({"code": "changed_predicate", "site_id": classified["id"]})
            continue
        evaluation = "procedural"
        definition = None
        if classified["category"] == "policy":
            evaluation = "inline"
            definition = f"inline:{classified['id']}"
            expr = site.expression
            if (
                isinstance(expr, ast.Call)
                and isinstance(expr.func, ast.Attribute)
                and expr.func.attr == "is_satisfied_by"
                and isinstance(expr.func.value, ast.Name)
            ):
                binding = import_bindings(trees[site.path]).get(expr.func.value.id)
                spec = specifications.get(binding)
                if (
                    spec is None
                    or spec["family_id"] != classified["family_id"]
                    or receiver_shadowed(trees[site.path], expr.func.value.id)
                ):
                    diagnostics.append(
                        {"code": "unresolved_policy_call", "site_id": classified["id"]}
                    )
                    continue
                evaluation = "specification"
                definition = f"spec:{spec['path']}:{spec['symbol']}"
        resolved.append(
            {
                "id": classified["id"],
                "family_id": classified.get("family_id"),
                "category": classified["category"],
                "rationale": classified["rationale"],
                "path": site.path,
                "symbol": site.symbol,
                "line": site.line,
                "evaluation": evaluation,
                "definition": definition,
                "boundary_violation": classified["category"] == "policy"
                and site.location not in classified["allowed_locations"],
            }
        )
    for site in discovered:
        if (site.path, site.line, site.kind) not in matched:
            diagnostics.append(
                {
                    "code": "unclassified_site",
                    "path": site.path,
                    "symbol": site.symbol,
                    "line": site.line,
                    "label": site.label,
                }
            )
    definitions: dict[str, set[str]] = defaultdict(set)
    violations = []
    for site in resolved:
        if site["category"] != "policy":
            continue
        definitions[site["family_id"]].add(site["definition"])
        if site["evaluation"] == "inline":
            violations.append(
                {"id": f"inline:{site['id']}", "kind": "inline_policy", "site_id": site["id"]}
            )
        if site["boundary_violation"]:
            violations.append(
                {
                    "id": f"boundary:{site['id']}",
                    "kind": "policy_boundary_violation",
                    "site_id": site["id"],
                }
            )
    for family in manifest["families"]:
        actual = definitions.get(family["id"], set())
        if actual and family["canonical_definition"] not in actual:
            diagnostics.append({"code": "missing_canonical_definition", "family_id": family["id"]})
        for definition in sorted(actual - {family["canonical_definition"]}):
            violations.append(
                {
                    "id": f"duplicate:{family['id']}:{definition}",
                    "kind": "duplicate_policy_definition",
                    "family_id": family["id"],
                    "definition": definition,
                }
            )
        for definition in sorted(actual):
            if definition.startswith("spec:"):
                path = definition.split(":")[1]
                if path not in family["allowed_definition_paths"]:
                    violations.append(
                        {
                            "id": f"boundary:{family['id']}:{definition}",
                            "kind": "policy_boundary_violation",
                            "family_id": family["id"],
                            "definition": definition,
                        }
                    )
    observed = Counter(v["kind"] for v in violations)
    counts = {
        "inline_policies": observed["inline_policy"],
        "duplicate_policy_definitions": observed["duplicate_policy_definition"],
        "policy_boundary_violations": observed["policy_boundary_violation"],
    }
    complete = not diagnostics
    return {
        "artifact_kind": "publication_policy_diagnostics",
        "schema_version": 1,
        "mode": "informational",
        "merge_gate_enabled": False,
        "classification_status": manifest["classification_status"],
        "profile_id": manifest["profile_id"],
        "scope_note": manifest["scope_note"],
        "manifest_sha256": digest(manifest),
        "revision": revision or "working_tree",
        "source_sha256": sources,
        "completeness": "complete" if complete else "incomplete",
        "counts": counts if complete else None,
        "observed_counts": counts,
        "coverage": {"discovered_sites": len(discovered), "resolved_sites": len(resolved)},
        "category_counts": dict(Counter(site["category"] for site in resolved)),
        "sites": resolved,
        "violations": sorted(violations, key=lambda v: v["id"]),
        "diagnostics": diagnostics,
    }


def compare(base: dict, head: dict) -> dict:
    if (
        base["completeness"] != "complete"
        or head["completeness"] != "complete"
        or base["profile_id"] != head["profile_id"]
    ):
        return {"status": "unavailable", "reason": "incomplete or incompatible snapshots"}
    before = {v["id"]: v for v in base["violations"]}
    after = {v["id"]: v for v in head["violations"]}
    return {
        "status": "complete",
        "classification_contract_changed": base["manifest_sha256"] != head["manifest_sha256"],
        "added_violations": [after[key] for key in sorted(after.keys() - before.keys())],
        "removed_violations": [before[key] for key in sorted(before.keys() - after.keys())],
        "count_delta": {key: head["counts"][key] - base["counts"][key] for key in head["counts"]},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", default=MANIFEST)
    parser.add_argument("--revision")
    parser.add_argument("--base-ref")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    try:
        revision = pin_revision(args.root, args.revision) if args.revision else None
        manifest = validate_manifest(json.loads(read_source(args.root, args.manifest, revision)))
        report = snapshot(args.root, manifest, revision)
        if args.base_ref:
            base_ref = pin_revision(args.root, args.base_ref)
            try:
                base_manifest = validate_manifest(
                    json.loads(read_source(args.root, args.manifest, base_ref))
                )
            except (OSError, ValueError) as exc:
                report["comparison"] = {
                    "status": "unavailable",
                    "reason": "baseline classification unavailable",
                    "detail": str(exc),
                    "base_revision": base_ref,
                }
            else:
                base = snapshot(args.root, base_manifest, base_ref)
                report["base"] = base
                report["comparison"] = compare(base, report)
        encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        if args.summary:
            summary = {
                key: report[key]
                for key in (
                    "mode",
                    "classification_status",
                    "completeness",
                    "counts",
                    "coverage",
                )
            }
            summary["diagnostic_count"] = len(report["diagnostics"])
            if "comparison" in report:
                summary["comparison_status"] = report["comparison"]["status"]
            print(json.dumps(summary, indent=2))
        elif not args.output:
            print(encoded, end="")
        return 0
    except (OSError, ValueError, SyntaxError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "invalid_input", "diagnostic": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
