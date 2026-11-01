"""Capture external inputs, check authored bindings and publish a derived pair."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from ontology_snapshot import (
    CapturedOntologyInputs,
    capture_ontology_snapshot,
    parse_ontology_ir,
)

from .model import PROFILE, OverviewError, Role, render, selected_role, sha


def workspace_file(root: Path, name: str) -> Path:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise OverviewError(f"expected a workspace-relative source path: {name}")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise OverviewError(f"source is missing or outside workspace: {name}")
    return resolved


def run_hypercode(executable: Path, hc: Path, hcs: Path) -> object:
    try:
        result = subprocess.run(
            [str(executable), "emit", str(hc), "--hcs", str(hcs), "--ir-version", "2"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise OverviewError(f"Hypercode unavailable: {error}", outcome="unavailable") from error
    if result.returncode != 0:
        raise OverviewError(f"Hypercode rejected the selected pair: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        raise OverviewError("Hypercode returned unusable JSON", outcome="unavailable") from error


def production_line(data: bytes, symbol: str, anchor: str) -> int:
    try:
        source = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        module = ast.parse(source)
    except (SyntaxError, UnicodeError) as error:
        raise OverviewError("production source must be valid UTF-8 Python syntax") from error
    functions = [
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
    ]
    if len(functions) != 1:
        raise OverviewError("production function missing or ambiguous")
    function = functions[0]
    lines = source.split("\n")
    matching = [
        number
        for number in range(function.lineno, function.end_lineno + 1)
        if anchor in lines[number - 1]
    ]
    if len(matching) != 1:
        raise OverviewError("production anchor must occur once inside the selected function")
    return matching[0]


def checked_bindings(
    root: Path, role: Role, ontologyc: Path, compiler_sha256: str
) -> dict[str, dict[str, str]]:
    sources: dict[str, bytes] = {}
    packages: dict[str, tuple[object, str, str]] = {}
    bindings = {}
    default_source = dict(role.properties).get("ontology_source")

    def capture(name: str, expected: str | None = None) -> bytes:
        if name not in sources:
            sources[name] = workspace_file(root, name).read_bytes()
        data = sources[name]
        if expected is not None and expected != sha(data):
            raise OverviewError(f"source hash mismatch: {name}")
        return data

    def package(name: str, expected: str | None):
        source = capture(name, expected)
        if name not in packages:
            # Reuse the existing snapshot adapter's captured bytes and structured checks.
            path = workspace_file(root, name)
            snapshot = capture_ontology_snapshot(
                path,
                ontologyc,
                captured_inputs=CapturedOntologyInputs(path, None, source, None, None, None),
                structured_check=True,
                expected_compiler_sha256=compiler_sha256,
            )
            packages[name] = (
                parse_ontology_ir(snapshot.ir_bytes),
                snapshot.source_sha256,
                snapshot.ir_sha256,
            )
        return packages[name]

    for _, item in role.walk():
        props = dict(item.properties)
        source_name = props.get("ontology_source", default_source)
        if source_name is None:
            raise OverviewError(f"missing ontology_source for {item.identity}")
        ir, source_hash, ir_hash = package(source_name, props.get("ontology_sha256"))
        if not isinstance(ir, dict):
            raise OverviewError("ontology compiler returned an unusable declaration inventory")
        declarations = {
            row.get("uri")
            for section in ("classes", "protocols")
            for row in ir.get(section, [])
            if isinstance(row, dict)
        }
        if props["ontology_ref"] not in declarations:
            raise OverviewError(
                f"unknown ontology_ref for {item.identity}: {props['ontology_ref']}"
            )
        if props.get("composition_ref") is not None and props["composition_ref"] not in {
            row.get("uri") for row in ir.get("relations", []) if isinstance(row, dict)
        }:
            raise OverviewError(f"unknown composition_ref for {item.identity}")
        props.update(
            ontology_source=source_name,
            ontology_sha256=source_hash,
            ontology_ir_sha256=ir_hash,
            ontology_compiler_sha256=compiler_sha256,
        )
        if "scenario_source" in props:
            data = capture(props["scenario_source"], props.get("scenario_sha256"))
            props["scenario_sha256"] = sha(data)
        elif "scenario_sha256" in props:
            raise OverviewError("scenario_sha256 requires scenario_source")
        production = {key for key in props if key.startswith("production_")}
        if production:
            required = {"production_path", "production_symbol", "production_anchor"}
            if not required.issubset(production):
                raise OverviewError("production binding requires path, symbol and anchor")
            data = capture(props["production_path"], props.get("production_sha256"))
            line = production_line(data, props["production_symbol"], props["production_anchor"])
            props.update(production_sha256=sha(data), production_line=str(line))
        bindings[item.identity] = props
    return bindings


def export_overview(
    root: Path, hc_path: Path, hcs_path: Path, hypercode: Path, ontologyc: Path, output: Path
) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise OverviewError("workspace must be an existing directory")
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise OverviewError("output must be a new directory with an existing parent")
    hc = workspace_file(root, hc_path.as_posix()).read_bytes()
    hcs = workspace_file(root, hcs_path.as_posix()).read_bytes()
    if any(re.match(r"@import(?:\s|$)", line.strip()) for line in hcs.decode("utf-8").splitlines()):
        raise OverviewError("HCS imports are outside the single-sheet export profile")
    for tool in (hypercode, ontologyc):
        if not tool.is_file() or not os.access(tool, os.X_OK):
            raise OverviewError(f"tool is not an executable file: {tool}", outcome="unavailable")
    hypercode_bytes = hypercode.read_bytes()
    compiler_hash = sha(ontologyc.read_bytes())
    with tempfile.TemporaryDirectory(prefix="specgraph-overview-") as temporary:
        work = Path(temporary)
        executable = work / "hypercode"
        executable.write_bytes(hypercode_bytes)
        executable.chmod(0o500)
        source_hc, source_hcs = work / "selection.hc", work / "selection.hcs"
        source_hc.write_bytes(hc)
        source_hcs.write_bytes(hcs)
        role = selected_role(run_hypercode(executable, source_hc, source_hcs))
        bindings = checked_bindings(root, role, ontologyc, compiler_hash)
        bindings[role.identity].update(
            input_hc_sha256=sha(hc),
            input_hcs_sha256=sha(hcs),
            hypercode_sha256=sha(hypercode_bytes),
        )
        rendered_hc, rendered_hcs = render(role, bindings)
        generated_hc, generated_hcs = work / "context.hc", work / "context.hcs"
        generated_hc.write_bytes(rendered_hc)
        generated_hcs.write_bytes(rendered_hcs)
        generated_ir = run_hypercode(executable, generated_hc, generated_hcs)
        checked = selected_role(generated_ir)
        if [(p, r.identity) for p, r in checked.walk()] != [
            (p, r.identity) for p, r in role.walk()
        ]:
            raise OverviewError("generated cascade does not preserve the selected roles")

        # Compare all output properties: a same-name selector must not leak into another role.
        def compare(nodes: list, expected: Role):
            node = nodes[0]
            actual = {k: v["value"] for k, v in node["properties"].items()}
            wanted = {
                **bindings[expected.identity],
                "role_id": expected.identity,
                "source_type": expected.source_type,
            }
            if expected is role:
                wanted.update(
                    projection_profile=PROFILE,
                    composition_status="proposed",
                    hc_sha256=sha(rendered_hc),
                )
            if actual != wanted:
                raise OverviewError("generated cascade has overlapping role selectors")
            for child_node, child in zip(node["children"], expected.children, strict=True):
                compare([child_node], child)

        compare(generated_ir["nodes"], role)
        output.mkdir()  # Exclusive creation; no source or previous export is overwritten.
        try:
            (output / "context.hc").write_bytes(rendered_hc)
            (output / "context.hcs").write_bytes(rendered_hcs)
        except OSError:
            for name in ("context.hc", "context.hcs"):
                (output / name).unlink(missing_ok=True)
            output.rmdir()
            raise
    return {
        "status": "exported",
        "roles": len(tuple(role.walk())),
        "hc_sha256": sha(rendered_hc),
        "hcs_sha256": sha(rendered_hcs),
        "semantic_approval": "not_established",
    }
