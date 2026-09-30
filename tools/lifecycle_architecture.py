#!/usr/bin/env python3
"""Report and gate lifecycle state classification and import boundaries."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import platform
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "tools" / "lifecycle_architecture_policy.json"
LEGACY_REPORT_PATH = "tools/idea_maturity_metrics_report.py"


@dataclass(frozen=True)
class Module:
    name: str
    path: str
    role: str


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    modules = policy.get("modules")
    decisions = policy.get("decisions")
    if policy.get("artifact_kind") != "lifecycle_architecture_policy" or not isinstance(
        modules, list
    ):
        raise ValueError("invalid lifecycle architecture policy")
    names = [module.get("name") for module in modules if isinstance(module, dict)]
    paths = [module.get("path") for module in modules if isinstance(module, dict)]
    if len(names) != len(modules) or len(names) != len(set(names)):
        raise ValueError("module names must be present and unique")
    if len(paths) != len(set(paths)) or not isinstance(decisions, list):
        raise ValueError("module paths must be unique and decisions must be a list")
    known = set(names)
    for decision in decisions:
        if decision.get("classifier_module") not in known:
            raise ValueError(f"unknown classifier for decision {decision.get('id')!r}")
        protected_raw_inputs = decision.get("protected_raw_inputs", [])
        if not isinstance(protected_raw_inputs, list) or any(
            not isinstance(name, str) or not name for name in protected_raw_inputs
        ):
            raise ValueError(
                f"protected_raw_inputs for decision {decision.get('id')!r} must be a list of names"
            )
    return policy


def _module_map(policy: dict[str, Any]) -> dict[str, Module]:
    return {
        item["name"]: Module(item["name"], item["path"], item["role"]) for item in policy["modules"]
    }


def _source_for_ref(repo: Path, ref: str, path: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{path}"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout if completed.returncode == 0 else None


def _sources(repo: Path, modules: dict[str, Module], ref: str | None) -> dict[str, str]:
    result = {}
    for name, module in modules.items():
        source = _source_for_ref(repo, ref, module.path) if ref else None
        if source is None and not ref:
            file_path = repo / module.path
            if file_path.is_file():
                source = file_path.read_text(encoding="utf-8")
        if source is not None:
            result[name] = source
    return result


def _unregistered_scope_sources(
    repo: Path, modules: dict[str, Module], ref: str | None
) -> dict[str, str]:
    if ref:
        completed = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", ref, "--", "tools/"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        paths = completed.stdout.splitlines() if completed.returncode == 0 else []
    else:
        paths = [
            path.relative_to(repo).as_posix()
            for path in (repo / "tools").glob("idea_maturity_*.py")
        ]
    registered_paths = {module.path for module in modules.values()}
    result = {}
    for path in paths:
        if not path.startswith("tools/idea_maturity_") or path in registered_paths:
            continue
        source = (
            _source_for_ref(repo, ref, path) if ref else (repo / path).read_text(encoding="utf-8")
        )
        if source is not None:
            result[Path(path).stem] = source
    return result


def _internal_imports(source: str, known_modules: set[str]) -> list[tuple[str, int]]:
    tree = ast.parse(source)
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            candidates = [item.name for item in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            candidates = [node.module]
        else:
            continue
        for candidate in candidates:
            if candidate in known_modules:
                imports.append((candidate, node.lineno))
    return imports


def _literal_values(pattern: ast.pattern) -> list[Any]:
    if isinstance(pattern, ast.MatchValue):
        try:
            return [ast.literal_eval(pattern.value)]
        except (ValueError, TypeError):
            return []
    if isinstance(pattern, ast.MatchOr):
        return [value for item in pattern.patterns for value in _literal_values(item)]
    return []


def _comparison_dispatch(test: ast.expr) -> tuple[str, list[Any]] | None:
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
        return None
    left, right, operation = test.left, test.comparators[0], test.ops[0]
    if isinstance(operation, ast.Eq):
        try:
            return ast.unparse(left), [ast.literal_eval(right)]
        except (ValueError, TypeError):
            try:
                return ast.unparse(right), [ast.literal_eval(left)]
            except (ValueError, TypeError):
                return None
    if isinstance(operation, ast.In) and isinstance(right, (ast.Set, ast.Tuple, ast.List)):
        values = []
        for element in right.elts:
            try:
                values.append(ast.literal_eval(element))
            except (ValueError, TypeError):
                continue
        return (ast.unparse(left), values) if values else None
    return None


class DispatchSiteVisitor(ast.NodeVisitor):
    """Find switch statements and simple if/elif chains for discovery reporting."""

    def __init__(self, module: str) -> None:
        self.module = module
        self.sites: list[dict[str, Any]] = []
        self._if_chain_members: set[int] = set()

    def visit_If(self, node: ast.If) -> None:
        if id(node) in self._if_chain_members:
            self.generic_visit(node)
            return
        chain = [node]
        current = node
        while len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
            current = current.orelse[0]
            chain.append(current)
        self._if_chain_members.update(id(item) for item in chain)
        if len(chain) > 1:
            selectors = [_comparison_dispatch(item.test) for item in chain]
            if all(item is not None for item in selectors):
                concrete = [item for item in selectors if item is not None]
                names = {item[0] for item in concrete}
                if len(names) == 1:
                    self.sites.append(
                        {
                            "module": self.module,
                            "line": node.lineno,
                            "kind": "if_elif_chain",
                            "selector": concrete[0][0],
                            "arm_count": len(chain),
                            "variants": [value for _, values in concrete for value in values],
                        }
                    )
        self.generic_visit(node)

    def visit_Match(self, self_node: ast.Match) -> None:
        variants = [value for case in self_node.cases for value in _literal_values(case.pattern)]
        if len(self_node.cases) > 1:
            self.sites.append(
                {
                    "module": self.module,
                    "line": self_node.lineno,
                    "kind": "match",
                    "selector": ast.unparse(self_node.subject),
                    "arm_count": len(self_node.cases),
                    "variants": variants,
                }
            )
        self.generic_visit(self_node)


def _dispatch_candidates(sources: dict[str, str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for module, source in sources.items():
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        visitor = DispatchSiteVisitor(module)
        visitor.visit(tree)
        for site in visitor.sites:
            grouped[site["selector"]].append(site)
    return [
        {
            "selector": selector,
            "site_count": len(sites),
            "modules": sorted({site["module"] for site in sites}),
            "sites": sites,
        }
        for selector, sites in sorted(grouped.items())
        if len(sites) > 1
    ]


class BranchPointVisitor(ast.NodeVisitor):
    """Count explicit control-flow and short-circuit branch points in one scope."""

    def __init__(self) -> None:
        self.points = 0
        self.max_nesting = 0
        self._nesting = 0

    def _nested(self, node: ast.AST) -> None:
        self._nesting += 1
        self.max_nesting = max(self.max_nesting, self._nesting)
        self.generic_visit(node)
        self._nesting -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_If(self, node: ast.If) -> None:
        self.points += 1
        self._nested(node)

    def visit_For(self, node: ast.For) -> None:
        self.points += 1
        self._nested(node)

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> None:
        self.points += 1
        self._nested(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.points += 1
        self._nested(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.points += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.points += max(0, len(node.cases) - 1)
        self._nested(node)

    def visit_Try(self, node: ast.Try) -> None:
        self.points += len(node.handlers)
        self._nested(node)

    visit_TryStar = visit_Try

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.points += 1 + len(node.ifs)
        self.generic_visit(node)


def _scope_points(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> tuple[int, int]:
    visitor = BranchPointVisitor()
    if isinstance(node, ast.Lambda):
        visitor.visit(node.body)
    else:
        for statement in node.body:
            visitor.visit(statement)
    return visitor.points, visitor.max_nesting


def _predicate_lambdas(tree: ast.Module) -> list[ast.Lambda]:
    predicates: list[ast.Lambda] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func).split(".")[-1]
        if name != "PredicateSpec":
            continue
        predicates.extend(argument for argument in node.args if isinstance(argument, ast.Lambda))
    return predicates


def _protected_raw_context_reads(source: str, artifact_names: list[str]) -> list[dict[str, Any]]:
    """Find protected reads from roots propagated through local classifier helpers.

    Classifier modules use the first positional PredicateSpec argument as the
    context predicate. Propagation is intentionally limited to simple aliases
    and direct calls to named functions defined in this module.
    """
    tree = ast.parse(source)
    protected = set(artifact_names)
    reads = []
    local_functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    visited_scopes: set[tuple[int, frozenset[str]]] = set()

    class ReadVisitor(ast.NodeVisitor):
        def __init__(self, context_names: set[str]) -> None:
            self.context_names = context_names

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"artifact", "summary"}:
                receiver = node.func.value
                if (
                    isinstance(receiver, ast.Name)
                    and receiver.id in self.context_names
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                ):
                    artifact = node.args[0].value
                    if isinstance(artifact, str) and artifact in protected:
                        reads.append(
                            {
                                "line": node.lineno,
                                "artifact": artifact,
                                "accessor": node.func.attr,
                            }
                        )
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "artifacts"
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id in self.context_names
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                artifact = node.args[0].value
                if isinstance(artifact, str) and artifact in protected:
                    reads.append(
                        {"line": node.lineno, "artifact": artifact, "accessor": "artifacts.get"}
                    )
            if isinstance(node.func, ast.Name):
                helper = local_functions.get(node.func.id)
                if helper is not None:
                    positional_parameters = [*helper.args.posonlyargs, *helper.args.args]
                    propagated = set()
                    for index, argument in enumerate(node.args):
                        if index >= len(positional_parameters):
                            break
                        parameter = positional_parameters[index]
                        if isinstance(argument, ast.Name) and argument.id in self.context_names:
                            propagated.add(parameter.arg)
                    keyword_parameters = {
                        argument.arg for argument in [*helper.args.args, *helper.args.kwonlyargs]
                    }
                    for keyword in node.keywords:
                        if (
                            keyword.arg in keyword_parameters
                            and isinstance(keyword.value, ast.Name)
                            and keyword.value.id in self.context_names
                        ):
                            propagated.add(keyword.arg)
                    if propagated:
                        scan_function(helper, propagated)
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            if (
                isinstance(node.value, ast.Attribute)
                and node.value.attr == "artifacts"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id in self.context_names
                and isinstance(node.slice, ast.Constant)
            ):
                artifact = node.slice.value
                if isinstance(artifact, str) and artifact in protected:
                    reads.append(
                        {"line": node.lineno, "artifact": artifact, "accessor": "artifacts[]"}
                    )
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            return

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

        def _visit_assignment(self, targets: list[ast.expr], value: ast.expr) -> None:
            self.visit(value)
            source_name = value.id if isinstance(value, ast.Name) else None
            for target in targets:
                if isinstance(target, ast.Name):
                    if source_name in self.context_names:
                        self.context_names.add(target.id)
                    else:
                        self.context_names.discard(target.id)

        def visit_Assign(self, node: ast.Assign) -> None:
            self._visit_assignment(node.targets, node.value)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            if node.value is None:
                return
            self._visit_assignment([node.target], node.value)

    def scan_function(
        function: ast.FunctionDef | ast.AsyncFunctionDef, context_names: set[str]
    ) -> None:
        key = (id(function), frozenset(context_names))
        if key in visited_scopes:
            return
        visited_scopes.add(key)
        visitor = ReadVisitor(set(context_names))
        for statement in function.body:
            visitor.visit(statement)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parameters = [
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
                *([node.args.vararg] if node.args.vararg else []),
                *([node.args.kwarg] if node.args.kwarg else []),
            ]
            context_names = {
                argument.arg
                for argument in parameters
                if (
                    isinstance(argument.annotation, ast.Name)
                    and argument.annotation.id == "LifecycleStateContext"
                )
                or (
                    isinstance(argument.annotation, ast.Attribute)
                    and argument.annotation.attr == "LifecycleStateContext"
                )
            }
            if context_names:
                scan_function(node, context_names)

    # The classifier-module convention is that PredicateSpec's predicate is
    # its first positional argument; other call arguments are outside this gate.
    for call in ast.walk(tree):
        if (
            isinstance(call, ast.Call)
            and ast.unparse(call.func).split(".")[-1] == "PredicateSpec"
            and call.args
            and isinstance(call.args[0], ast.Lambda)
            and call.args[0].args.args
        ):
            predicate = call.args[0]
            visitor = ReadVisitor({predicate.args.args[0].arg})
            visitor.visit(predicate.body)
    return reads


def _decision_metrics(
    source: str, symbol: str, *, include_module_predicates: bool = True
) -> dict[str, Any]:
    tree = ast.parse(source)
    functions = [
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    classifier = next((node for node in functions if node.name == symbol), None)
    if classifier is None:
        raise ValueError(f"classifier symbol {symbol!r} not found")
    scoped_functions = functions if include_module_predicates else [classifier]
    callable_points = [_scope_points(node) for node in scoped_functions]
    predicates = _predicate_lambdas(tree) if include_module_predicates else []
    predicate_points = [_scope_points(node) for node in predicates]
    all_points = [*callable_points, *predicate_points]
    return {
        "public_callable_branch_points": _scope_points(classifier)[0],
        "classifier_callable_count": len(functions),
        "classifier_callable_branch_points": sum(points for points, _ in callable_points),
        "max_callable_branch_points": max((points for points, _ in callable_points), default=0),
        "max_control_nesting": max((depth for _, depth in callable_points), default=0),
        "predicate_lambda_count": len(predicates),
        "predicate_lambda_branch_points": sum(points for points, _ in predicate_points),
        "max_predicate_lambda_branch_points": max(
            (points for points, _ in predicate_points), default=0
        ),
        "branch_points_total": sum(points for points, _ in all_points),
    }


def _legacy_source(repo: Path, ref: str | None) -> str | None:
    if ref:
        return _source_for_ref(repo, ref, LEGACY_REPORT_PATH)
    path = repo / LEGACY_REPORT_PATH
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _allowed_edges(policy: dict[str, Any], modules: dict[str, Module]) -> set[tuple[str, str]]:
    role_dependencies = policy["role_dependencies"]
    edges = {
        (source.name, target.name)
        for source in modules.values()
        for target in modules.values()
        if target.role in role_dependencies.get(source.role, [])
    }
    for source, targets in policy.get("decision_dependencies", {}).items():
        edges.update((source, target) for target in targets)
    return edges


def _cycles(edges: list[tuple[str, str]], module_names: set[str]) -> list[list[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for source, target in edges:
        graph[source].add(target)
    cycles: list[list[str]] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            start = visiting.index(name)
            cycles.append([*visiting[start:], name])
            return
        if name in visited:
            return
        visiting.append(name)
        for target in sorted(graph[name]):
            visit(target)
        visiting.pop()
        visited.add(name)

    for module in sorted(module_names):
        visit(module)
    return cycles


def _snapshot(
    repo: Path,
    policy: dict[str, Any],
    modules: dict[str, Module],
    ref: str | None,
) -> dict[str, Any]:
    sources = _sources(repo, modules, ref)
    unregistered_sources = _unregistered_scope_sources(repo, modules, ref)
    sources.update(unregistered_sources)
    known = set(modules)
    edges: list[tuple[str, str]] = []
    edge_records = []
    syntax_errors = []
    for name, source in sources.items():
        try:
            imports = _internal_imports(source, known)
        except SyntaxError as error:
            syntax_errors.append({"module": name, "line": error.lineno, "message": error.msg})
            continue
        for target, line in imports:
            edges.append((name, target))
            edge_records.append({"source": name, "target": target, "line": line})

    allowed = _allowed_edges(policy, modules)
    forbidden = [edge for edge in edge_records if (edge["source"], edge["target"]) not in allowed]
    cycles = _cycles(edges, known)
    missing_modules = sorted(known - set(sources))
    decisions = []
    for decision in policy["decisions"]:
        classifier_module = decision["classifier_module"]
        classifier_source = sources.get(classifier_module)
        classifier_metrics = None
        classifier_missing = classifier_source is None
        if classifier_source is not None:
            try:
                classifier_metrics = _decision_metrics(
                    classifier_source, decision["classifier_symbol"]
                )
            except (SyntaxError, ValueError) as error:
                syntax_errors.append({"module": classifier_module, "message": str(error)})
        decisions.append(
            {
                "id": decision["id"],
                "classifier": {
                    "module": classifier_module,
                    "symbol": decision["classifier_symbol"],
                },
                "classifier_missing": classifier_missing,
                "classifier_metrics": classifier_metrics,
            }
        )
    classification_findings = []
    for decision in policy["decisions"]:
        protected_inputs = decision.get("protected_raw_inputs", [])
        classifier_module = decision["classifier_module"]
        if not protected_inputs:
            continue
        for name, source in sources.items():
            module = modules.get(name)
            if module is None or module.role != "state_classifier" or name == classifier_module:
                continue
            try:
                reads = _protected_raw_context_reads(source, protected_inputs)
            except SyntaxError:
                continue
            classification_findings.extend(
                {
                    "decision_id": decision["id"],
                    "classifier": classifier_module,
                    "module": name,
                    **read,
                    "message": "sibling state classifier reads a protected raw context artifact",
                }
                for read in reads
            )
    metrics_by_role: dict[str, Counter[str]] = defaultdict(Counter)
    imports_by_role: Counter[str] = Counter()
    for source, target in edges:
        source_role = modules[source].role if source in modules else "unregistered"
        target_role = modules[target].role
        imports_by_role[f"{source_role}->{target_role}"] += 1
    decisions_by_id = {item["id"]: item for item in decisions}
    for decision in policy["decisions"]:
        module = modules[decision["classifier_module"]]
        metrics = decisions_by_id[decision["id"]]["classifier_metrics"]
        if metrics:
            for field in (
                "branch_points_total",
                "predicate_lambda_count",
                "predicate_lambda_branch_points",
            ):
                metrics_by_role[module.role][field] += metrics[field]
    findings = []
    findings.extend({"code": "LAC001", **item} for item in forbidden)
    findings.extend({"code": "LAC002", "cycle": cycle} for cycle in cycles)
    findings.extend({"code": "LAC003", "module": name} for name in missing_modules)
    findings.extend({"code": "LAC004", **item} for item in syntax_errors)
    findings.extend({"code": "LAC007", **item} for item in classification_findings)
    findings.extend(
        {
            "code": "LAC006",
            "module": name,
            "message": "lifecycle module is missing from the policy",
        }
        for name in sorted(unregistered_sources)
    )
    findings.extend(
        {"code": "LAC005", "decision_id": item["id"], "classifier": item["classifier"]}
        for item in decisions
        if item["classifier_missing"] or item["classifier_metrics"] is None
    )
    return {
        "ref": ref or "working_tree",
        "module_count": len(sources),
        "scope_basis": (
            "registered state classifiers and PredicateSpec lambdas; "
            "unregistered lifecycle modules are reported"
        ),
        "internal_import_edge_count": len(edges),
        "internal_import_edges": edge_records,
        "internal_imports_by_role": dict(imports_by_role),
        "repeated_dispatch_candidates": _dispatch_candidates(sources),
        "decision_points_by_role": {
            role: dict(counter) for role, counter in metrics_by_role.items()
        },
        "decisions": decisions,
        "findings": findings,
        "gate_status": "fail" if findings else "pass",
    }


def build_report(
    repo: Path = ROOT,
    policy: dict[str, Any] | None = None,
    base_ref: str | None = None,
    head_ref: str | None = None,
) -> dict[str, Any]:
    policy = policy or load_policy()
    modules = _module_map(policy)
    head = _snapshot(repo, policy, modules, head_ref)
    base = None
    if base_ref:
        legacy_source = _legacy_source(repo, base_ref)
        base_decisions = []
        role_points: dict[str, Counter[str]] = defaultdict(Counter)
        source_kinds: set[str] = set()
        legacy_functions: set[str] = set()
        if legacy_source:
            legacy_tree = ast.parse(legacy_source)
            legacy_functions = {
                node.name
                for node in ast.walk(legacy_tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
        for decision in policy["decisions"]:
            classifier_module = modules[decision["classifier_module"]]
            source = _source_for_ref(repo, base_ref, classifier_module.path)
            source_kind = "classifier_module"
            symbol = decision["classifier_symbol"]
            role = classifier_module.role
            metrics = None
            if source is not None:
                try:
                    metrics = _decision_metrics(source, symbol)
                except (SyntaxError, ValueError):
                    metrics = None
            if source is None and legacy_source and decision["legacy_symbol"] in legacy_functions:
                source_kind = "legacy_report"
                symbol = decision["legacy_symbol"]
                role = "legacy_state_classifier"
                metrics = _decision_metrics(legacy_source, symbol, include_module_predicates=False)
            if metrics is not None:
                source_kinds.add(source_kind)
                role_points[role]["branch_points_total"] += metrics["branch_points_total"]
            base_decisions.append(
                {
                    "id": decision["id"],
                    "symbol": symbol,
                    "source": {
                        "kind": source_kind if metrics is not None else "unavailable",
                        "module": (
                            classifier_module.name
                            if source_kind == "classifier_module"
                            else "idea_maturity_metrics_report"
                        ),
                        "path": (
                            classifier_module.path
                            if source_kind == "classifier_module"
                            else LEGACY_REPORT_PATH
                        ),
                        "symbol": symbol,
                    },
                    "metrics": metrics,
                }
            )
        all_legacy = source_kinds == {"legacy_report"}
        all_classifiers = source_kinds == {"classifier_module"}
        base_role = (
            "legacy_state_classifier"
            if all_legacy
            else "state_classifier"
            if all_classifiers
            else "mixed_lifecycle_baseline"
        )
        scope_basis = (
            "eight legacy function bodies, measured independently"
            if all_legacy
            else "registered classifier symbols and PredicateSpec lambdas at base ref"
            if all_classifiers
            else "registered classifiers at base ref with per-decision legacy fallback"
        )
        base = {
            "ref": base_ref,
            "module_count": len(
                {item["source"]["path"] for item in base_decisions if item["metrics"] is not None}
            ),
            "role": base_role,
            "scope_basis": scope_basis,
            "decision_points_by_role": {role: dict(points) for role, points in role_points.items()},
            "decisions": base_decisions,
        }
        baseline_metrics = {item["id"]: item["metrics"] for item in base_decisions}
        baseline_sources = {item["id"]: item["source"] for item in base_decisions}
        for decision in head["decisions"]:
            decision["baseline"] = {
                **baseline_sources[decision["id"]],
                "metrics": baseline_metrics.get(decision["id"]),
            }
            if baseline_sources[decision["id"]]["kind"] == "legacy_report":
                decision["legacy"] = {
                    "module": "idea_maturity_metrics_report",
                    "symbol": decision["baseline"]["symbol"],
                    "metrics": baseline_metrics.get(decision["id"]),
                }
    findings = head["findings"]
    policy_digest = hashlib.sha256(
        json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "artifact_kind": "lifecycle_architecture_report",
        "schema_version": 1,
        "policy_id": policy["policy_id"],
        "policy_sha256": policy_digest,
        "python_version": platform.python_version(),
        "metric_definition": "branch_points_proxy.v1",
        "base": base,
        "head": head,
        "gate_status": "fail" if findings else "pass",
        "findings": findings,
    }


def _summary(report: dict[str, Any]) -> str:
    head = report["head"]
    lines = [
        f"Lifecycle state classification gate: {report['gate_status']}",
        f"Policy: {report['policy_id']} ({report['policy_sha256'][:12]})",
        "Head modules/imports/decisions: "
        f"{head['module_count']}/{head['internal_import_edge_count']}/{len(head['decisions'])}",
    ]
    if report["base"]:
        baseline = {item["id"]: item["metrics"] for item in report["base"]["decisions"]}
        lines.append("Branch-point proxy by decision (base -> head):")
        for decision in head["decisions"]:
            old = baseline.get(decision["id"])
            current = decision["classifier_metrics"]
            if old and current:
                lines.append(
                    f"  {decision['id']}: {old['branch_points_total']} -> "
                    f"{current['branch_points_total']}"
                )
    for role, metrics in sorted(head["decision_points_by_role"].items()):
        lines.append(
            f"  {role}: {metrics.get('branch_points_total', 0)} branch points; "
            f"{metrics.get('predicate_lambda_count', 0)} predicate lambdas"
        )
    lines.append(
        f"Repeated-dispatch discovery candidates: {len(head['repeated_dispatch_candidates'])}"
    )
    if report["findings"]:
        lines.append("Findings:")
        lines.extend(f"  {finding['code']}: {finding}" for finding in report["findings"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", help="optional Git ref to compare with head")
    parser.add_argument("--head-ref", help="Git ref to analyze; defaults to the working tree")
    parser.add_argument(
        "--check", action="store_true", help="return nonzero when the contract fails"
    )
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args()
    try:
        report = build_report(ROOT, load_policy(), args.base_ref, args.head_ref)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"artifact_kind": "lifecycle_architecture_report", "error": str(error)}))
        return 1
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_summary(report))
    return 1 if args.check and report["gate_status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
