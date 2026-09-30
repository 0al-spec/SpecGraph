"""Isolated criterion-change exercise; never modifies working-tree product code."""

from __future__ import annotations

import argparse
import ast
import copy
import difflib
import hashlib
import importlib.util
import itertools
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE_REF = "425078cc74e1c2cccbff259b5505b1b958b8e904"
EXTRACTED_REF = "38d85167d59f4a77f67235154d8ce3d4caa577a5"
ALIAS = "accepted_with_conditions"
MODULE = "ontology_decision_state_spec.py"
SITES = {
    "ontology_imports.py": (
        ("build_ontology_owner_decision_report", "decisions"),
        ("build_ontology_decision_import_preview", "previews"),
    ),
    "ontology_owner_decision_import_v2.py": (("build_owner_decision_import_v2", "reviews"),),
}


def sources_from_git() -> dict[str, dict[str, str]]:
    def source(ref: str, name: str) -> str:
        return subprocess.check_output(["git", "show", f"{ref}:tools/{name}"], cwd=ROOT, text=True)

    baseline = {name: source(BASE_REF, name) for name in SITES}
    specification = {name: source(EXTRACTED_REF, name) for name in (*SITES, MODULE)}
    conventional = {
        **specification,
        MODULE: subprocess.check_output(
            [
                "git",
                "show",
                f"{EXTRACTED_REF}:tests/fixtures/ontology_decision_counts/conventional.py",
            ],
            cwd=ROOT,
            text=True,
        ),
    }
    return {"baseline": baseline, "conventional": conventional, "specification": specification}


def function_node(source: str, name: str) -> ast.FunctionDef:
    return next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def assignment_name(node: ast.stmt) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        return target.id if isinstance(target, ast.Name) else None
    return None


def count_region(source: str, symbol: str) -> list[ast.stmt]:
    body = function_node(source, symbol).body
    start = next(
        index
        for index, node in enumerate(body)
        if assignment_name(node) in {"accepted_count", "decision_counts"}
    )
    end = next(
        index
        for index in range(start, len(body))
        if assignment_name(body[index]) == "clarification_count"
    )
    return body[start : end + 1]


def accepted_comparison(nodes: list[ast.AST]) -> ast.Compare:
    matches = [
        node
        for root in nodes
        for node in ast.walk(root)
        if isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value == "accepted"
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one accepted criterion, found {len(matches)}")
    return matches[0]


def change_criterion(sources: dict[str, str], variant: str, *, partial: bool = False):
    changed = dict(sources)
    sites: dict[str, list[ast.Compare]] = {}
    if variant == "baseline":
        for filename, symbols in SITES.items():
            sites[filename] = [
                accepted_comparison(count_region(sources[filename], symbol))
                for symbol, _ in symbols
            ]
        if partial:
            sites = {"ontology_imports.py": sites["ontology_imports.py"][:1]}
    elif variant == "conventional":
        sites[MODULE] = [
            accepted_comparison([function_node(sources[MODULE], "count_decision_states")])
        ]
    elif variant == "specification":
        assignment = next(
            node for node in ast.parse(sources[MODULE]).body if assignment_name(node) == "ACCEPTED"
        )
        sites[MODULE] = [accepted_comparison([assignment])]
    else:
        raise ValueError(f"Unknown variant: {variant}")

    for filename, comparisons in sites.items():
        encoded = sources[filename].encode()
        lines = encoded.splitlines(keepends=True)
        for node in sorted(
            comparisons, key=lambda item: (item.lineno, item.col_offset), reverse=True
        ):
            start = sum(map(len, lines[: node.lineno - 1])) + node.col_offset
            end = sum(map(len, lines[: node.end_lineno - 1])) + node.end_col_offset
            left = ast.get_source_segment(sources[filename], node.left)
            replacement = f'{left} in ("accepted", "{ALIAS}")'.encode()
            encoded = encoded[:start] + replacement + encoded[end:]
        changed[filename] = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--stdin-filename",
                filename,
                "--line-length",
                "100",
                "--target-version",
                "py310",
                "-",
            ],
            input=encoded.decode(),
            text=True,
            check=True,
            capture_output=True,
        ).stdout
    return changed, sum(map(len, sites.values()))


def consumers(sources: dict[str, str], path: Path, label: str):
    namespace = {}
    if MODULE in sources:
        module_name = f"decision_change_{label}"
        spec = importlib.util.spec_from_file_location(module_name, path / MODULE)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        namespace["count_decision_states"] = module.count_decision_states
    result = {}
    for filename, symbols in SITES.items():
        for symbol, records_name in symbols:
            # Execute only the production counting region, excluding I/O,
            # taxonomy validation, readiness, and operator-action decisions.
            tree = ast.parse(f"{records_name} = records\n")
            tree.body.extend(copy.deepcopy(count_region(sources[filename], symbol)))
            tree.body.extend(
                ast.parse("result = (accepted_count, rejected_count, clarification_count)").body
            )
            code = compile(ast.fix_missing_locations(tree), f"{path / filename}#{symbol}", "exec")

            def evaluate(records, *, code=code, namespace=namespace):
                local = {"records": records}
                exec(code, namespace.copy(), local)
                return local["result"]

            result[symbol] = evaluate
    return result


def check_matrix(functions, *, include_alias: bool) -> dict[str, object]:
    states = ("accepted", "rejected", "needs_clarification", "unknown", None, ALIAS)
    failures = {name: 0 for name in functions}
    cases = 0
    for length in range(5):
        for values in itertools.product(states, repeat=length):
            records = [{"decision_state": value} for value in values]
            expected = (
                values.count("accepted") + (values.count(ALIAS) if include_alias else 0),
                values.count("rejected"),
                values.count("needs_clarification"),
            )
            for name, evaluate in functions.items():
                failures[name] += evaluate(records) != expected
            cases += 1
    return {"cases_per_consumer": cases, "failures": failures}


def write_sources(path: Path, sources: dict[str, str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for filename, source in sources.items():
        (path / filename).write_text(source)


def check_edges(functions) -> None:
    for evaluate in functions.values():
        records = [{"decision_state": value} for value in ([], {}, True, 0, " Accepted ")]
        original = copy.deepcopy(records)
        if evaluate(records) != (0, 0, 0) or records != original:
            raise ValueError("Unknown values or input immutability changed")
        try:
            evaluate([{}])
        except KeyError as error:
            if error.args != ("decision_state",):
                raise ValueError("Missing-key error changed") from error
        else:
            raise ValueError("Missing decision_state must remain a KeyError")


def footprint(before: dict[str, str], after: dict[str, str], output: Path):
    files = []
    patches = []
    for filename, source in before.items():
        if source == after[filename]:
            continue
        diff = list(
            difflib.unified_diff(
                source.splitlines(keepends=True),
                after[filename].splitlines(keepends=True),
                fromfile=f"before/{filename}",
                tofile=f"after/{filename}",
            )
        )
        added = sum(line.startswith("+") and not line.startswith("+++") for line in diff)
        removed = sum(line.startswith("-") and not line.startswith("---") for line in diff)
        files.append({"path": filename, "added": added, "removed": removed})
        patches.extend(diff)
    output.write_text("".join(patches))
    return {
        "files": files,
        "changed_files": len(files),
        "added": sum(file["added"] for file in files),
        "removed": sum(file["removed"] for file in files),
    }


def run(output: Path) -> dict[str, object]:
    if output.exists():
        raise ValueError("Use a fresh output directory to avoid mixing experiment runs")
    variants = sources_from_git()
    output.mkdir(parents=True)
    report = {
        "exercise_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "baseline_ref": BASE_REF,
        "extracted_ref": EXTRACTED_REF,
        "criterion": f"accepted also counts {ALIAS}",
        "ruff_version": version("ruff"),
        "scope": "counting regions only; synthetic alias is not adopted into product taxonomy",
        "variants": {},
    }
    for variant, before in variants.items():
        after, edited_criteria = change_criterion(before, variant)
        before_path, after_path = output / "before" / variant, output / "after" / variant
        write_sources(before_path, before)
        write_sources(after_path, after)
        old_functions = consumers(before, before_path, f"{variant}_before")
        new_functions = consumers(after, after_path, f"{variant}_after")
        check_edges(old_functions)
        check_edges(new_functions)
        report["variants"][variant] = {
            "source_sha256": {
                phase: {
                    name: hashlib.sha256(source.encode()).hexdigest()
                    for name, source in sources.items()
                }
                for phase, sources in (("before", before), ("after", after))
            },
            "footprint": footprint(before, after, output / f"{variant}.patch"),
            "edited_criteria": edited_criteria,
            "edge_checks_passed": True,
            "before_matrix": check_matrix(old_functions, include_alias=False),
            "after_matrix": check_matrix(new_functions, include_alias=True),
            "changed_consumers": [
                name
                for name in new_functions
                if old_functions[name]([{"decision_state": ALIAS}])
                != new_functions[name]([{"decision_state": ALIAS}])
            ],
        }
    partial, _ = change_criterion(variants["baseline"], "baseline", partial=True)
    partial_path = output / "partial_baseline"
    write_sources(partial_path, partial)
    report["incomplete_change_probe"] = check_matrix(
        consumers(partial, partial_path, "partial"), include_alias=True
    )
    matrices_passed = all(
        not any(result[phase]["failures"].values())
        for result in report["variants"].values()
        for phase in ("before_matrix", "after_matrix")
    )
    probe_detected = report["incomplete_change_probe"]["failures"] == {
        "build_ontology_owner_decision_report": 0,
        "build_ontology_decision_import_preview": 774,
        "build_owner_decision_import_v2": 774,
    }
    report["status"] = "pass" if matrices_passed and probe_detected else "fail"
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output_dir)
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
