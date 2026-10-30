"""Run one local SG-SPEC-0072 model through real SDK generation and execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


class PilotFailure(Exception):
    def __init__(self, layer: str, path: str, message: str, code: int = 1):
        super().__init__(message)
        self.layer, self.path, self.code = layer, path, code


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pointer(document: object, path: str) -> object:
    for part in path.removeprefix("/").split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        document = document[int(key)] if isinstance(document, list) else document[key]
    return document


def source_mapping(expected: dict, document: dict, spec_bytes: bytes) -> None:
    """The six source clauses and four coverage rows of this one reviewed example."""
    base = "/specification/verification_contract/"
    anchors = {
        (base + "invalid", "duplicate identity"),
        (
            base + "unavailable",
            "a required compiler, input or dependency check is missing or unsupported",
        ),
        (
            base + "outcome_precedence",
            "A detected invalidity makes the overall outcome invalid "
            "even if another required check is unavailable.",
        ),
        (base + "outcome_precedence", "retain per-check diagnostics in every case."),
        (
            base + "result_contract",
            "per-check results, one overall outcome, and concrete diagnostics.",
        ),
        (
            "/specification/acceptance_cases/4/expected",
            "a detected context conflict plus another unavailable required check remains invalid "
            "with both diagnostics retained.",
        ),
    }
    actual = [(item["pointer"], item["quote"]) for item in expected["source_fragments"]]
    if set(actual) != anchors or len(actual) != len(anchors):
        raise PilotFailure(
            "model", "source-map.json/source_fragments", "Required source-clause inventory changed"
        )
    if expected["source_sha256"] != digest(spec_bytes):
        raise PilotFailure(
            "model",
            "source-map.json/source_sha256",
            "Source specification changed; this mapping is stale",
        )
    if document["id"] != expected["spec_id"]:
        raise PilotFailure(
            "model", "spec.yaml/id", "Pinned source node differs from the selected specification"
        )
    for path, quote in actual:
        if quote not in pointer(document, path):
            raise PilotFailure("model", path, "Source fragment differs from its pinned quote")
    rows = [(item["pointer"], item["status"]) for item in expected["acceptance"]]
    if (
        rows != [(f"/acceptance/{i}", "partial" if i == 2 else "unmodelled") for i in range(4)]
        or len(document["acceptance"]) != 4
    ):
        raise PilotFailure(
            "model",
            "source-map.json/acceptance",
            "Keep exactly four acceptance rows; only row 2 is partially modelled",
        )
    wanted = expected["expected"]
    required = [("selection", "invalid"), ("compiler", "unavailable")]
    if (
        expected["schema_version"] != 1
        or expected["spec_id"] != "SG-SPEC-0072"
        or expected["scenario_id"] != "SG72-MIXED"
        or wanted["outcome"] != "invalid"
        or wanted["diagnostics_required"] is not True
        or [(c["check"], c["outcome"]) for c in wanted["checks"]] != required
    ):
        raise PilotFailure(
            "model",
            "source-map.json/expected",
            "This fixed pilot requires invalid, both named diagnostics and SG72-MIXED",
        )


def run(args: argparse.Namespace, root: Path) -> tuple[dict, int]:
    work = args.work_dir.resolve()
    if work.exists() and (not work.is_dir() or any(work.iterdir())):
        raise ValueError("--work-dir must be new or empty; existing output is never overwritten")
    work.mkdir(parents=True, exist_ok=True)
    source = work / "src"
    source.mkdir()
    captured = {}
    report = {
        "artifact_kind": "local_ontology_scenario_pilot",
        "schema_version": 1,
        "spec_id": "SG-SPEC-0072",
        "scenario_id": "SG72-MIXED",
        "outcome": "tool_failure",
        "layers": {
            name: {"status": "not_run"} for name in ("compiler", "typecheck", "model", "behavior")
        },
        "findings": [],
        "inputs": {},
        "tools": {},
        "commands": [],
        "canonical_mutations_allowed": False,
        "runtime_gate_activation_allowed": False,
        "unsupported": [
            "Natural-language completeness and contradiction detection",
            "Generic ontology instance validation",
            "Gherkin step execution",
            "Semantic approval, readiness and universal correctness",
        ],
    }

    def capture(path: Path, name: str, destination: Path | None = None) -> bytes:
        data = path.read_bytes()
        report["inputs"][name] = digest(data)
        captured[path] = digest(data)
        if destination is not None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        return data

    def command(
        name: str, argv: list[str], layer: str, accepted: tuple[int, ...] = (0,)
    ) -> subprocess.CompletedProcess:
        try:
            result = subprocess.run(argv, cwd=source, capture_output=True, timeout=60, check=False)
        except subprocess.TimeoutExpired as error:
            result = subprocess.CompletedProcess(
                argv, 124, error.stdout or b"", error.stderr or b""
            )
        for stream in ("stdout", "stderr"):
            (work / f"{name}.{stream}").write_bytes(getattr(result, stream))
        report["commands"].append(
            {
                "name": name,
                "argv": argv,
                "returncode": result.returncode,
                "stdout": f"{name}.stdout",
                "stderr": f"{name}.stderr",
            }
        )
        if result.returncode not in accepted:
            detail = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()
            code = (
                1
                if result.returncode in (1, 2) and layer == "typecheck"
                else 1
                if result.returncode == 1
                else 2
            )
            raise PilotFailure(layer, name, detail or f"Process exited {result.returncode}", code)
        return result

    code, layer = 2, "compiler"
    try:
        model_dir = (args.model_dir or root / "specs/models/SG-SPEC-0072").resolve()
        for name in (
            "domain-ontology-package.yaml",
            "model.ts",
            "tsconfig.json",
            "source-map.json",
            "mixed-outcome.feature",
        ):
            capture(model_dir / name, f"model/{name}", source / name)
        capture(
            root / "tools/local_ontology_pilot/consumer.ts", "consumer.ts", source / "consumer.ts"
        )
        capture(root / "tools/local_ontology_pilot.py", "runner.py", work / "runner.py")
        spec_bytes = capture(
            root / "specs/nodes/SG-SPEC-0072.yaml",
            "specs/nodes/SG-SPEC-0072.yaml",
            work / "spec.yaml",
        )
        sgcore = source / "sgcore.yaml"
        capture(
            root / "ontology/packages/specgraph-core/domain-ontology-package.yaml",
            "sgcore.yaml",
            sgcore,
        )
        try:
            expected = json.loads((source / "source-map.json").read_bytes())
            document = yaml.safe_load(spec_bytes)
            source_mapping(expected, document, spec_bytes)
            feature = (source / "mixed-outcome.feature").read_text().splitlines()
            tags = [
                token for line in feature if line.strip().startswith("@") for token in line.split()
            ]
            scenarios = [line for line in feature if line.strip().startswith("Scenario:")]
            if tags.count("@SG72-MIXED") != 1 or len(scenarios) != 1:
                raise PilotFailure(
                    "model",
                    "mixed-outcome.feature",
                    "Expected one @SG72-MIXED tag and one Scenario",
                )
        except (ValueError, TypeError, KeyError, IndexError, yaml.YAMLError) as error:
            raise PilotFailure(
                "model", "source-map.json", f"Malformed source mapping: {error}"
            ) from error
        report["coverage"] = {"acceptance": expected["acceptance"], "complete": False}
        node = shutil.which("node")
        if node is None:
            raise PilotFailure("typecheck", "node", "Node.js is unavailable", 2)
        compiler, tsc = args.ontologyc.resolve(), args.tsc.resolve()
        report["tools"] = {
            "ontologyc": {
                "path": str(compiler),
                "sha256": digest(compiler.read_bytes()),
                "version": "not_exposed_by_cli",
                "provenance": "not_verified",
            },
            "typescript": {"path": str(tsc), "entrypoint_sha256": digest(tsc.read_bytes())},
            "node": {"path": node, "sha256": digest(Path(node).read_bytes())},
            "python": {
                "path": sys.executable,
                "version": sys.version,
                "sha256": digest(Path(sys.executable).read_bytes()),
            },
        }
        for path in (
            tsc.parent.parent / "package.json",
            tsc.parent.parent / "lib/tsc.js",
            tsc.parent.parent / "lib/_tsc.js",
        ):
            if path.is_file():
                report["tools"]["typescript"].setdefault("implementation_sha256", {})[path.name] = (
                    digest(path.read_bytes())
                )
        for tool, argv in (
            ("typescript", [node, str(tsc), "--version"]),
            ("node", [node, "--version"]),
        ):
            report["tools"][tool]["version"] = (
                command(f"{tool}-version", argv, "typecheck").stdout.decode().strip()
            )
        for name, package in (
            ("sgcore", sgcore),
            ("pilot", source / "domain-ontology-package.yaml"),
        ):
            command(f"{name}-check", [str(compiler), "check", str(package)], "compiler")
            command(
                f"{name}-compile",
                [
                    str(compiler),
                    "compile",
                    str(package),
                    "--target",
                    "typescript",
                    "--out",
                    str(source / "generated" / name),
                ],
                "compiler",
            )
        report["layers"]["compiler"]["status"] = "passed"
        report["generated"] = {
            str(path.relative_to(work)): digest(path.read_bytes())
            for path in sorted((source / "generated").rglob("*"))
            if path.is_file()
        }
        layer = "typecheck"
        command(
            "typescript-model", [node, str(tsc), "--project", str(source / "tsconfig.json")], layer
        )
        report["layers"][layer]["status"] = "passed"
        layer = "model"
        output = command("model-consumer", [node, str(work / "js/consumer.js")], layer, (0, 1))
        consumer = json.loads(output.stdout)
        if consumer["findings"]:
            report["findings"].extend(
                {"layer": layer, **finding} for finding in consumer["findings"]
            )
            first = consumer["findings"][0]
            raise PilotFailure(layer, first["path"], first["message"])
        declaration = consumer["model"]
        report["model"] = declaration
        wanted = expected["expected"]
        if declaration["specification"]["id"] != expected["spec_id"]:
            raise PilotFailure(
                layer,
                "model.ts/specification/id",
                "Model refers to a different source specification",
            )
        if (
            declaration["scenario"]["id"] != expected["scenario_id"]
            or declaration["scenario"]["expectedOutcome"] != wanted["outcome"]
        ):
            raise PilotFailure(
                layer,
                "model.ts/scenario",
                "Declared case/outcome differs from the independent source map",
            )
        declared = {(check["check"], check["outcome"]): check for check in declaration["checks"]}
        required = {(check["check"], check["outcome"]) for check in wanted["checks"]}
        if set(declared) != required or len(declaration["checks"]) != len(required):
            raise PilotFailure(
                layer,
                "model.ts/checks",
                "Declared checks differ from the independent required diagnostic roles",
            )
        report["layers"][layer]["status"] = "passed"
        layer = "behavior"
        # SDK compilation above is real. This production scenario deliberately has no compiler.
        producer_paths = ["tools/ontology_snapshot.py"] + [
            f"tools/project_ontology_context/{name}.py"
            for name in ("__init__", "capture", "model", "invalid_spec", "unavailable_spec")
        ]
        for path in producer_paths:
            capture(root / path, path, work / "producer-source" / path)
        from project_ontology_context import capture_project_context

        runtime = work / "workspace"
        runtime.mkdir()
        for name, data in (
            ("package.yaml", sgcore.read_bytes()),
            ("ontology.json", (source / "generated/sgcore/ontology.normalized.json").read_bytes()),
        ):
            (runtime / name).write_bytes(data)
        metadata = yaml.safe_load(sgcore.read_bytes())["metadata"]
        member = {key: metadata[key] for key in ("id", "namespace", "version")}
        member.update(
            source="package.yaml",
            source_sha256=digest((runtime / "package.yaml").read_bytes()),
            ir="ontology.json",
            ir_sha256=digest((runtime / "ontology.json").read_bytes()),
        )
        selection = {
            "artifact_kind": "specgraph_project_ontology_selection",
            "schema_version": 1,
            "packages": [member, member],
            "profiles": ["ontologyc-structural-v1"],
            "composition": {"dependency_rule": "explicit", "name_resolution_rule": "qualified"},
        }
        (runtime / "selection.yaml").write_text(yaml.safe_dump(selection))
        observed = capture_project_context(
            runtime,
            project_id="local-SG72-MIXED",
            selection_path=Path("selection.yaml"),
            ontologyc=None,
        ).report()
        report["observed"] = observed
        if observed["outcome"] != wanted["outcome"]:
            raise PilotFailure(
                layer,
                "observed/outcome",
                "Production capture disagrees with the source-map expectation",
            )
        for key, check in declared.items():
            if not any(
                (item["check"], item["outcome"]) == key and item["detail"] == check["detail"]
                for item in observed["checks"]
            ):
                raise PilotFailure(
                    layer,
                    f"model.ts/checks/{check['id']}",
                    "Required diagnostic is missing or associated with a different check/outcome",
                )
        report["layers"][layer]["status"] = "passed"
        for path, original in captured.items():
            if digest(path.read_bytes()) != original:
                raise PilotFailure("model", str(path), "Captured input changed during this run")
        if digest(compiler.read_bytes()) != report["tools"]["ontologyc"]["sha256"]:
            raise PilotFailure("compiler", str(compiler), "Compiler changed during this run", 2)
        report["outcome"], code = "satisfied", 0
    except PilotFailure as error:
        report["layers"][error.layer]["status"] = "failed"
        finding = {"layer": error.layer, "path": error.path, "message": str(error)}
        if finding not in report["findings"]:
            report["findings"].append(finding)
        code = error.code
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        report["layers"][layer]["status"] = "failed"
        report["findings"].append(
            {"layer": layer, "path": "inputs_or_tools", "message": str(error)}
        )
    if code:
        report["outcome"] = "mismatch" if code == 1 else "tool_failure"
    (work / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report, code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ontologyc", required=True, type=Path)
    parser.add_argument("--tsc", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--model-dir", type=Path)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    try:
        report, code = run(args, Path(__file__).resolve().parents[1])
    except (OSError, ValueError) as error:
        print(json.dumps({"outcome": "tool_failure", "error": str(error)}), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "outcome": report["outcome"],
                "report": str(args.work_dir / "report.json"),
                "findings": report["findings"],
            }
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
