"""Read exact Git objects and Python declarations without executing source."""

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

MAX_BYTES = 2 * 1024 * 1024


def encoded(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value: object) -> str:
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def strict_json(raw: bytes) -> object:
    if len(raw) > MAX_BYTES:
        raise ValueError("review input exceeds the size limit")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate review key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("nonfinite review value")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE)


def revision(root: Path, ref: str) -> str:
    return (
        git(root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").decode().strip()
    )


def normalized_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or any(ord(c) < 32 for c in value)
        or PurePosixPath(value).is_absolute()
        or any(p in ("", ".", "..") for p in value.split("/"))
    ):
        raise ValueError("reference path must be repository relative and normalized")
    return value


class GitSources:
    def __init__(self, root: Path, base: str, head: str):
        self.root, self.base, self.head = root, base, head

    def blob(self, ref: str, path: str) -> bytes:
        path = normalized_path(path)
        entry = git(self.root, "ls-tree", "-z", ref, "--", path)
        if not entry:
            raise ValueError(f"reference file missing: {path}")
        mode, kind, _ = entry.split(b"\t", 1)[0].split()
        if mode not in (b"100644", b"100755") or kind != b"blob":
            raise ValueError(f"reference is not a regular Git blob: {path}")
        raw = git(self.root, "show", f"{ref}:{path}")
        if len(raw) > MAX_BYTES:
            raise ValueError(f"reference file exceeds size limit: {path}")
        return raw

    def changed_paths(self) -> list[str]:
        raw = git(self.root, "diff", "--name-only", "--no-renames", "-z", self.base, self.head)
        return [v.decode() for v in raw.split(b"\0") if v]

    def scope(self, review_path: str) -> dict[str, object]:
        result = {}
        for path in self.changed_paths():
            if path == review_path:
                continue  # No commit/file self-reference; report binds the ledger separately.
            entry = git(self.root, "ls-tree", "-z", self.head, "--", path)
            if not entry:
                result[path] = None
                continue
            mode, kind, oid = entry.split(b"\t", 1)[0].split()
            result[path] = dict(mode=mode.decode(), kind=kind.decode(), oid=oid.decode())
        return result

    def declaration(self, reference: object, *, ref: str | None = None) -> dict[str, object]:
        if not isinstance(reference, dict) or set(reference) != {"path", "symbol"}:
            raise ValueError("code reference requires exactly path and symbol")
        path, symbol = normalized_path(reference["path"]), reference["symbol"]
        if (
            not path.endswith(".py")
            or not isinstance(symbol, str)
            or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", symbol)
        ):
            raise ValueError("v1 references require Python declarations")
        raw = self.blob(ref or self.head, path)
        module = ast.parse(raw)
        core = {
            alias.asname or alias.name: alias.name
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module == "specification_core"
            for alias in node.names
        }
        nodes = module.body
        found = None
        for part in symbol.split("."):
            found = next((node for node in nodes if declaration_name(node) == part), None)
            if found is None:
                raise ValueError(f"declaration missing: {path}:{symbol}")
            nodes = (
                found.body
                if isinstance(found, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                else []
            )
        is_spec = False
        if isinstance(found, ast.ClassDef):
            bases = [b.value if isinstance(b, ast.Subscript) else b for b in found.bases]
            is_spec = any(
                isinstance(b, ast.Name) and core.get(b.id) == "Specification" for b in bases
            )
        elif isinstance(found, (ast.Assign, ast.AnnAssign)):
            call = found.value
            if isinstance(call, ast.Call):
                fn = call.func
                name = (
                    fn.id
                    if isinstance(fn, ast.Name)
                    else fn.value.id
                    if (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name))
                    else None
                )
                is_spec = core.get(name) in {"PredicateSpec", "FirstMatch"}
        lines = raw.decode().splitlines(keepends=True)
        excerpt = "".join(lines[found.lineno - 1 : found.end_lineno])
        return dict(
            path=path,
            symbol=symbol,
            start_line=found.lineno,
            end_line=found.end_lineno,
            file_sha256=hashlib.sha256(raw).hexdigest(),
            code=excerpt,
            recognized_specification=is_spec,
        )


def declaration_name(node: ast.AST) -> str | None:
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    targets = (
        node.targets
        if isinstance(node, ast.Assign)
        else [node.target]
        if isinstance(node, ast.AnnAssign)
        else []
    )
    return targets[0].id if len(targets) == 1 and isinstance(targets[0], ast.Name) else None
