#!/usr/bin/env python3
"""Validate baseline-friendly architecture style rules for new supervisor code."""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUPERVISOR_PACKAGE_GLOBS = ("src/specgraph/supervisor/**/*.py",)
FORBIDDEN_CLASS_SUFFIXES = (
    "Utils",
    "Helper",
    "Manager",
    "Processor",
    "Service",
    "Controller",
    "Validator",
    "Calculator",
)
FORBIDDEN_IMPORT_PREFIXES = ("tools", "tests", "docs")
TOP_LEVEL_IO_METHODS = {
    "open",
    "read_text",
    "read_bytes",
    "write_text",
    "write_bytes",
    "mkdir",
    "unlink",
    "rename",
    "replace",
    "rmdir",
}
TOP_LEVEL_RUNTIME_CALLS = {
    "subprocess.run",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.Popen",
    "json.load",
    "yaml.safe_load",
}
PATH_CONSTRUCTORS = {"Path", "pathlib.Path"}
PATH_CLASS_METHODS = {"Path.cwd", "Path.home", "pathlib.Path.cwd", "pathlib.Path.home"}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    code: str
    message: str

    def format(self, repo: Path) -> str:
        try:
            relative_path = self.path.relative_to(repo)
        except ValueError:
            relative_path = self.path
        return f"{relative_path.as_posix()}:{self.line}: {self.code}: {self.message}"


def python_files(repo: Path) -> list[Path]:
    files: set[Path] = set()
    for pattern in SUPERVISOR_PACKAGE_GLOBS:
        files.update(path for path in repo.glob(pattern) if path.is_file())
    return sorted(files)


def decorator_name(decorator: ast.expr) -> str:
    if isinstance(decorator, ast.Call):
        return decorator_name(decorator.func)
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    return ""


def has_staticmethod(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(decorator_name(decorator) == "staticmethod" for decorator in function.decorator_list)


def qualified_name(expression: ast.expr) -> str:
    if isinstance(expression, ast.Name):
        return expression.id
    if isinstance(expression, ast.Attribute):
        base = qualified_name(expression.value)
        if base:
            return f"{base}.{expression.attr}"
    return ""


def parsed_string_annotation(annotation: ast.expr) -> ast.expr:
    if not isinstance(annotation, ast.Constant) or not isinstance(annotation.value, str):
        return annotation
    try:
        return ast.parse(annotation.value, mode="eval").body
    except SyntaxError:
        return annotation


def is_any_annotation(annotation: ast.expr) -> bool:
    parsed = parsed_string_annotation(annotation)
    return qualified_name(parsed) in {"Any", "typing.Any"}


def contains_any_annotation(annotation: ast.expr) -> bool:
    parsed = parsed_string_annotation(annotation)
    if is_any_annotation(parsed):
        return True
    return any(contains_any_annotation(child) for child in ast.iter_child_nodes(parsed))


def contains_dict_any_annotation(annotation: ast.expr) -> bool:
    parsed = parsed_string_annotation(annotation)
    if isinstance(parsed, ast.Subscript):
        name = qualified_name(parsed.value)
        if name in {"dict", "Dict", "typing.Dict"} and contains_any_annotation(parsed.slice):
            return True
    return any(contains_dict_any_annotation(child) for child in ast.iter_child_nodes(parsed))


def is_dict_any_annotation(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    return contains_dict_any_annotation(annotation)


def function_annotations(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterable[tuple[int, ast.expr | None]]:
    for argument in (
        *function.args.posonlyargs,
        *function.args.args,
        *function.args.kwonlyargs,
    ):
        yield argument.lineno, argument.annotation
    if function.args.vararg is not None:
        yield function.args.vararg.lineno, function.args.vararg.annotation
    if function.args.kwarg is not None:
        yield function.args.kwarg.lineno, function.args.kwarg.annotation
    yield function.lineno, function.returns


def import_aliases(module: ast.Module) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in module.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                local_name = alias.asname or alias.name
                aliases[local_name] = f"{module_name}.{alias.name}" if module_name else alias.name
    return aliases


def resolved_name(expression: ast.expr, aliases: dict[str, str]) -> str:
    if isinstance(expression, ast.Name):
        return aliases.get(expression.id, expression.id)
    if isinstance(expression, ast.Attribute):
        base = resolved_name(expression.value, aliases)
        if base:
            return f"{base}.{expression.attr}"
    return ""


def call_name(call: ast.Call, aliases: dict[str, str]) -> str:
    return resolved_name(call.func, aliases)


def is_path_constructor_call(call: ast.Call, aliases: dict[str, str]) -> bool:
    name = call_name(call, aliases)
    return name in PATH_CONSTRUCTORS or name in PATH_CLASS_METHODS


def is_pathlike_expression(
    expression: ast.expr,
    aliases: dict[str, str],
    pathlike_names: set[str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in pathlike_names
    if isinstance(expression, ast.Call):
        return is_path_constructor_call(expression, aliases)
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div):
        return is_pathlike_expression(
            expression.left, aliases, pathlike_names
        ) or is_pathlike_expression(expression.right, aliases, pathlike_names)
    return False


def assignment_names(target: ast.expr) -> Iterable[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, ast.Tuple | ast.List):
        for element in target.elts:
            yield from assignment_names(element)


def collect_pathlike_names(module: ast.Module, aliases: dict[str, str]) -> set[str]:
    pathlike_names: set[str] = set()
    changed = True
    while changed:
        changed = False
        for statement in module.body:
            value: ast.expr | None = None
            targets: list[ast.expr] = []
            if isinstance(statement, ast.Assign):
                value = statement.value
                targets = list(statement.targets)
            elif isinstance(statement, ast.AnnAssign):
                value = statement.value
                targets = [statement.target]
            if value is None or not is_pathlike_expression(value, aliases, pathlike_names):
                continue
            for target in targets:
                for name in assignment_names(target):
                    if name not in pathlike_names:
                        pathlike_names.add(name)
                        changed = True
    return pathlike_names


class ImportTimeCallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[ast.Call] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        for statement in node.body:
            self.visit(statement)

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append(node)
        self.generic_visit(node)


def import_time_calls(module: ast.Module) -> Iterable[ast.Call]:
    visitor = ImportTimeCallVisitor()
    visitor.visit(module)
    return visitor.calls


def is_top_level_io_call(
    call: ast.Call,
    aliases: dict[str, str],
    pathlike_names: set[str],
) -> bool:
    function = call.func
    name = call_name(call, aliases)
    if name == "open":
        return True
    if name in TOP_LEVEL_RUNTIME_CALLS:
        return True
    if isinstance(function, ast.Attribute) and function.attr in TOP_LEVEL_IO_METHODS:
        return is_pathlike_expression(function.value, aliases, pathlike_names)
    return False


def annotation_text(annotation: ast.expr | None) -> str:
    if annotation is None:
        return ""
    try:
        return ast.unparse(annotation).replace(" ", "")
    except Exception:  # pragma: no cover - defensive fallback for malformed AST objects
        return ""


def import_target(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    module = node.module or ""
    if module == "tools":
        return [f"{module}.{alias.name}" for alias in node.names]
    return [module]


def is_forbidden_import(target: str) -> bool:
    return any(
        target == prefix or target.startswith(f"{prefix}.") for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


def validate_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        module = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    except SyntaxError as exc:
        return [
            Finding(
                path=path,
                line=exc.lineno or 1,
                code="ARCH000",
                message=f"syntax error prevents architecture validation: {exc.msg}",
            )
        ]
    aliases = import_aliases(module)
    pathlike_names = collect_pathlike_names(module, aliases)

    for node in ast.walk(module):
        if isinstance(node, ast.ClassDef):
            for suffix in FORBIDDEN_CLASS_SUFFIXES:
                if node.name.endswith(suffix):
                    findings.append(
                        Finding(
                            path=path,
                            line=node.lineno,
                            code="ARCH001",
                            message=(
                                f"class name {node.name!r} uses procedural suffix {suffix!r}; "
                                "name the domain abstraction instead"
                            ),
                        )
                    )
                    break
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if has_staticmethod(node):
                findings.append(
                    Finding(
                        path=path,
                        line=node.lineno,
                        code="ARCH002",
                        message="@staticmethod hides behavior outside an object instance",
                    )
                )
            if node.name.startswith("set_"):
                findings.append(
                    Finding(
                        path=path,
                        line=node.lineno,
                        code="ARCH003",
                        message="setter-style methods are forbidden; return a changed value/object",
                    )
                )
            for line, annotation in function_annotations(node):
                if is_dict_any_annotation(annotation):
                    findings.append(
                        Finding(
                            path=path,
                            line=line,
                            code="ARCH004",
                            message=(
                                "dict[str, Any] in public signatures leaks untyped DTOs into "
                                "the supervisor package"
                            ),
                        )
                    )
        elif isinstance(node, ast.Import | ast.ImportFrom):
            for target in import_target(node):
                if is_forbidden_import(target):
                    findings.append(
                        Finding(
                            path=path,
                            line=node.lineno,
                            code="ARCH005",
                            message=(
                                f"forbidden dependency on {target!r}; keep package code "
                                "independent from legacy tools/tests/docs"
                            ),
                        )
                    )

    for call in import_time_calls(module):
        if is_top_level_io_call(call, aliases, pathlike_names):
            findings.append(
                Finding(
                    path=path,
                    line=call.lineno,
                    code="ARCH006",
                    message=(
                        "import-time I/O or subprocess work is forbidden in supervisor package code"
                    ),
                )
            )

    return findings


def validate(repo: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in python_files(repo):
        findings.extend(validate_file(path))
    return sorted(
        findings,
        key=lambda finding: (finding.path.as_posix(), finding.line, finding.code),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate architecture style rules for new SpecGraph supervisor package code."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=ROOT,
        help="Repository root to validate.",
    )
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    checked_file_count = len(python_files(repo))
    findings = validate(repo)
    if findings:
        print(
            f"Architecture style validation failed ({checked_file_count} files):",
            file=sys.stderr,
        )
        for finding in findings:
            print(f"- {finding.format(repo)}", file=sys.stderr)
        return 1

    print(f"Architecture style validation passed ({checked_file_count} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
