"""Resolve local, version-pinned inputs and render a JSON ontology Viewer graph."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import Any

import yaml

Identity = tuple[str, str]
FOUNDATION = "ontology.foundation"
LEGACY_FOUNDATION = ("specgraph.foundation", "0.1.0")


def identity(value: Any, source: Path) -> Identity:
    if isinstance(value, dict):
        package_id, version = value.get("id"), value.get("version")
        if isinstance(package_id, str) and package_id and isinstance(version, str) and version:
            return package_id, version
    raise ValueError(f"{source}: expected an ontology ID and pinned version")


def package(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("spec"), dict):
        raise ValueError(f"{path}: expected an ontology YAML package with a spec mapping")
    return data


def catalog_identity(path: Path) -> Identity:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schemaVersion") != "ontology.foundation-model/v1":
        raise ValueError(f"{path}: expected an ontology foundation catalog")
    return identity(data, path)


def add_candidate(candidates: dict[Identity, Path], key: Identity, path: Path) -> None:
    previous = candidates.setdefault(key, path)
    if previous != path:
        raise ValueError(f"Ambiguous input for {'@'.join(key)}: {previous} and {path}")


def projection_inputs(
    root: Path, package_candidates: list[Path], catalog_candidates: list[Path]
) -> tuple[list[Path], list[Path]]:
    packages: dict[Identity, Path] = {}
    documents = {}
    for path in dict.fromkeys([root, *package_candidates]):
        document = package(path)
        add_candidate(packages, identity(document.get("metadata"), path), path)
        documents[path] = document
    catalogs: dict[Identity, Path] = {}
    for path in dict.fromkeys(catalog_candidates):
        add_candidate(catalogs, catalog_identity(path), path)

    pending = deque([root])
    reached = {root}
    imports: list[Path] = []
    models: dict[Path, None] = {}
    while pending:
        source = pending.popleft()
        declarations = documents[source]["spec"].get("imports", [])
        if not isinstance(declarations, list):
            raise ValueError(f"{source}: expected a list at spec.imports")
        for declaration in declarations:
            key = identity(declaration, source)
            if key[0] == FOUNDATION or key == LEGACY_FOUNDATION:
                model = catalogs.get((FOUNDATION, key[1]))
                if model is None:
                    raise ValueError(f"{source}: missing foundation catalog for {'@'.join(key)}")
                models.setdefault(model, None)
                continue
            dependency = packages.get(key)
            if dependency is None:
                raise ValueError(f"{source}: missing YAML package for {'@'.join(key)}")
            if dependency not in reached:
                reached.add(dependency)
                imports.append(dependency)
                pending.append(dependency)
    return imports, list(models)


def executable_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="specgraph ontology-viewer", description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--ontologyviz", required=True, type=Path, help="Path to the renderer")
    parser.add_argument(
        "--viz-sha256", help="Expected SHA-256 of the renderer from a trusted source"
    )
    parser.add_argument("--package-candidate", type=Path, action="append", default=[])
    parser.add_argument("--foundation-catalog", type=Path, action="append", default=[])
    parser.add_argument("--out", required=True, type=Path, help="Graph output directory")
    args = parser.parse_args(argv)
    expected = args.viz_sha256
    if expected is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        parser.error("--viz-sha256 must be a 64-character hexadecimal digest")

    try:
        root = args.package.resolve()
        imports, catalogs = projection_inputs(
            root,
            [path.resolve() for path in args.package_candidate],
            [path.resolve() for path in args.foundation_catalog],
        )
    except (OSError, ValueError, RuntimeError, yaml.YAMLError) as error:
        print(f"ontology-viewer: input preflight failed: {error}", file=sys.stderr)
        return 2

    binary = args.ontologyviz.absolute()
    try:
        actual = executable_sha256(binary)
    except OSError as error:
        print(f"ontology-viewer: cannot read SHA-256 for {binary}: {error}", file=sys.stderr)
        return 2
    if expected is not None and actual != expected.lower():
        print(f"ontology-viewer: SHA-256 mismatch for {binary}: got {actual}", file=sys.stderr)
        return 2
    print(f"ontology-viewer: {binary} SHA-256 {actual}", file=sys.stderr)

    command = [str(binary), "--format", "json", "--out", str(args.out.absolute())]
    for path in imports:
        command.extend(("--import", str(path)))
    for path in catalogs:
        command.extend(("--foundation-model", str(path)))
    command.append(str(root))
    try:
        result = subprocess.run(command, check=False)
    except OSError as error:
        print(f"ontology-viewer: cannot launch ontologyviz: {error}", file=sys.stderr)
        return 2
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
