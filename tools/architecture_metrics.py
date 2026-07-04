#!/usr/bin/env python3
"""Report code-shape and EO-inspired architecture metrics."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))
try:
    import validate_architecture_style
finally:
    sys.path.remove(str(TOOLS_DIR))


@dataclass(frozen=True)
class FunctionShape:
    name: str
    line_count: int
    parameter_count: int


def _python_files(repo: Path, patterns: tuple[str, ...]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in repo.glob(pattern) if path.is_file())
    return sorted(files)


def _relative(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return path.as_posix()


def _function_line_count(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    end_lineno = getattr(function, "end_lineno", None)
    if not isinstance(end_lineno, int):
        return 1
    return max(1, end_lineno - function.lineno + 1)


def _parameter_count(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    arguments = function.args
    count = (
        len(arguments.posonlyargs)
        + len(arguments.args)
        + len(arguments.kwonlyargs)
        + (1 if arguments.vararg is not None else 0)
        + (1 if arguments.kwarg is not None else 0)
    )
    if arguments.args and arguments.args[0].arg in {"self", "cls"}:
        count -= 1
    return count


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _empty_scope(name: str, patterns: tuple[str, ...]) -> dict[str, Any]:
    return {
        "scope": name,
        "patterns": list(patterns),
        "files": [],
        "file_count": 0,
        "syntax_error_count": 0,
        "line_count": 0,
        "class_count": 0,
        "function_count": 0,
        "top_level_function_count": 0,
        "top_level_assignment_count": 0,
        "avg_function_lines": 0.0,
        "max_function_lines": 0,
        "functions_over_50_lines": 0,
        "functions_over_100_lines": 0,
        "avg_parameter_count": 0.0,
        "max_parameter_count": 0,
        "functions_over_5_parameters": 0,
        "dict_any_signature_count": 0,
        "isinstance_call_count": 0,
        "staticmethod_count": 0,
        "setter_function_count": 0,
        "procedural_class_suffix_count": 0,
        "procedural_class_suffixes_by_suffix": {},
    }


def _scope_metrics(repo: Path, name: str, patterns: tuple[str, ...]) -> dict[str, Any]:
    files = _python_files(repo, patterns)
    metrics = _empty_scope(name, patterns)
    metrics["files"] = [_relative(repo, path) for path in files]
    metrics["file_count"] = len(files)

    functions: list[FunctionShape] = []
    procedural_suffixes: Counter[str] = Counter()

    for path in files:
        text = path.read_text(encoding="utf-8")
        metrics["line_count"] += len(text.splitlines())
        try:
            module = ast.parse(text, filename=path.as_posix())
        except SyntaxError:
            metrics["syntax_error_count"] += 1
            continue
        metrics["top_level_function_count"] += sum(
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) for node in module.body
        )
        metrics["top_level_assignment_count"] += sum(
            isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign) for node in module.body
        )

        for node in ast.walk(module):
            if isinstance(node, ast.ClassDef):
                metrics["class_count"] += 1
                for suffix in validate_architecture_style.FORBIDDEN_CLASS_SUFFIXES:
                    if node.name.endswith(suffix):
                        procedural_suffixes[suffix] += 1
                        metrics["procedural_class_suffix_count"] += 1
                        break
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                metrics["function_count"] += 1
                if validate_architecture_style.has_staticmethod(node):
                    metrics["staticmethod_count"] += 1
                if node.name.startswith("set_"):
                    metrics["setter_function_count"] += 1
                for _, annotation in validate_architecture_style.function_annotations(node):
                    if validate_architecture_style.is_dict_any_annotation(annotation):
                        metrics["dict_any_signature_count"] += 1
                functions.append(
                    FunctionShape(
                        name=node.name,
                        line_count=_function_line_count(node),
                        parameter_count=_parameter_count(node),
                    )
                )
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "isinstance"
            ):
                metrics["isinstance_call_count"] += 1

    if functions:
        function_lines = [function.line_count for function in functions]
        parameter_counts = [function.parameter_count for function in functions]
        metrics["avg_function_lines"] = round(sum(function_lines) / len(function_lines), 2)
        metrics["max_function_lines"] = max(function_lines)
        metrics["functions_over_50_lines"] = sum(line_count > 50 for line_count in function_lines)
        metrics["functions_over_100_lines"] = sum(line_count > 100 for line_count in function_lines)
        metrics["avg_parameter_count"] = round(sum(parameter_counts) / len(parameter_counts), 2)
        metrics["max_parameter_count"] = max(parameter_counts)
        metrics["functions_over_5_parameters"] = sum(count > 5 for count in parameter_counts)

    metrics["procedural_class_suffixes_by_suffix"] = _counter_dict(procedural_suffixes)
    return metrics


def _finding_counts(findings: list[validate_architecture_style.Finding]) -> dict[str, int]:
    return _counter_dict(Counter(finding.code for finding in findings))


def report(repo: Path) -> dict[str, Any]:
    repo = repo.resolve()
    package_findings = validate_architecture_style.validate(repo)
    scopes = {
        "new_supervisor_package": _scope_metrics(
            repo,
            "new_supervisor_package",
            validate_architecture_style.SUPERVISOR_PACKAGE_GLOBS,
        ),
        "legacy_supervisor": _scope_metrics(repo, "legacy_supervisor", ("tools/supervisor.py",)),
    }

    return {
        "artifact_kind": "architecture_style_metrics",
        "schema_version": 1,
        "scope_note": (
            "architecture_gate metrics are blocking for new supervisor package code only; "
            "legacy_supervisor metrics are report-only baseline indicators"
        ),
        "architecture_gate": {
            "scope": "src/specgraph/supervisor/**/*.py",
            "status": "pass" if not package_findings else "fail",
            "findings_total": len(package_findings),
            "findings_by_code": _finding_counts(package_findings),
        },
        "scopes": scopes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print report-only architecture metrics as JSON.")
    parser.add_argument("--repo", type=Path, default=ROOT, help="Repository root to inspect.")
    args = parser.parse_args(argv)

    print(json.dumps(report(args.repo), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
