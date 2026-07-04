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
FORBIDDEN_IMPORT_PREFIXES = ("tools.supervisor", "tests", "docs")
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
    ("subprocess", "run"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("subprocess", "Popen"),
    ("json", "load"),
    ("yaml", "safe_load"),
}


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


def annotation_text(annotation: ast.expr | None) -> str:
    if annotation is None:
        return ""
    try:
        return ast.unparse(annotation).replace(" ", "")
    except Exception:  # pragma: no cover - defensive fallback for malformed AST objects
        return ""


def is_dict_any_annotation(annotation: ast.expr | None) -> bool:
    text = annotation_text(annotation)
    return text in {"dict[str,Any]", "Dict[str,Any]"}


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


def dotted_call_name(call: ast.Call) -> tuple[str, str] | None:
    function = call.func
    if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
        return function.value.id, function.attr
    return None


def is_top_level_io_call(call: ast.Call) -> bool:
    function = call.func
    if isinstance(function, ast.Name) and function.id == "open":
        return True
    if isinstance(function, ast.Attribute) and function.attr in TOP_LEVEL_IO_METHODS:
        return True
    return dotted_call_name(call) in TOP_LEVEL_RUNTIME_CALLS


def top_level_calls(module: ast.Module) -> Iterable[ast.Call]:
    for statement in module.body:
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        for node in ast.walk(statement):
            if isinstance(node, ast.Call):
                yield node


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

    for call in top_level_calls(module):
        if is_top_level_io_call(call):
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
    findings = validate(repo)
    if findings:
        print("Architecture style validation failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding.format(repo)}", file=sys.stderr)
        return 1

    print("Architecture style validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
