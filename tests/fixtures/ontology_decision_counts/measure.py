"""Optional benchmark runner; requires complexipy 8.0.1 and radon 6.0.1.

Writes isolated production-source cohorts for an external clone detector.
Experimental fixtures themselves are excluded from measured source cohorts.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from importlib.metadata import version
from pathlib import Path

from complexipy import code_complexity
from radon.complexity import cc_visit

ROOT = Path(__file__).resolve().parents[3]
BASE_REF = "425078cc74e1c2cccbff259b5505b1b958b8e904"
CONSUMERS = ("ontology_imports.py", "ontology_owner_decision_import_v2.py")
MODULE = "ontology_decision_state_spec.py"
TARGETS = {
    "build_ontology_owner_decision_report",
    "build_ontology_decision_import_preview",
    "build_owner_decision_import_v2",
    "count_decision_states",
}


def measure(sources: dict[str, str]) -> dict[str, object]:
    functions = {}
    edges = []
    predicate_count = 0
    for filename, source in sources.items():
        cc = {function.name: function.complexity for function in cc_visit(source)}
        cog = {function.name: function.complexity for function in code_complexity(source).functions}
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in TARGETS:
                functions[node.name] = {
                    "cc": cc[node.name],
                    "cog": cog[node.name],
                    "lines": node.end_lineno - node.lineno + 1,
                }
            if isinstance(node, ast.ImportFrom) and f"{node.module}.py" in sources:
                edges.append([filename, f"{node.module}.py"])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                predicate_count += node.func.id == "PredicateSpec"
    return {
        "production_lines": sum(len(source.splitlines()) for source in sources.values()),
        "modules": len(sources),
        "internal_import_edges": edges,
        "predicate_lambdas": predicate_count,
        "functions": functions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    baseline = {
        name: subprocess.check_output(
            ["git", "show", f"{BASE_REF}:tools/{name}"], cwd=ROOT, text=True
        )
        for name in CONSUMERS
    }
    specification = {name: (ROOT / "tools" / name).read_text() for name in (*CONSUMERS, MODULE)}
    conventional = {
        **specification,
        MODULE: (Path(__file__).parent / "conventional.py").read_text(),
    }
    variants = {"baseline": baseline, "conventional": conventional, "specification": specification}
    report = {
        "baseline_ref": BASE_REF,
        "versions": {name: version(name) for name in ("complexipy", "radon")},
    }
    for name, sources in variants.items():
        output = args.output_dir / name
        output.mkdir(parents=True, exist_ok=True)
        for filename, source in sources.items():
            (output / filename).write_text(source)
        report[name] = measure(sources)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
