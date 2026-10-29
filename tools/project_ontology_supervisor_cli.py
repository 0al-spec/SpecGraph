"""CLI boundary for an explicit project ontology advisory check."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from project_ontology_supervisor_check import build_target_context_check

_TARGET = re.compile(r"SG-SPEC-[0-9]{4}\Z")
_PROJECT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def run_request(
    root: Path, request: dict[str, Any], *, target_spec: str | None, output_mode: str
) -> int:
    """Compute once, atomically persist only the derived report, and print its view."""
    try:
        root = Path(root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("workspace must be a directory")
        if not isinstance(target_spec, str) or not _TARGET.fullmatch(target_spec):
            raise ValueError("--target-spec must be SG-SPEC-NNNN")
        project_id = request.get("project_id")
        if not isinstance(project_id, str) or not _PROJECT.fullmatch(project_id):
            raise ValueError("--ontology-context-project-id must be a valid project id")
        selection = request.get("selection")
        previous = request.get("previous_report")
        for value, label in ((selection, "selection"), (previous, "previous report")):
            if value is not None:
                path = Path(value)
                if (label == "selection" and path.is_absolute()) or not (
                    root / path
                ).resolve().is_relative_to(root):
                    raise ValueError(f"{label} path must stay under workspace")
        output = root / "runs" / "project_ontology_context" / f"{target_spec}.json"
        if output.is_symlink() or not output.resolve().is_relative_to(root):
            raise ValueError("report output path must stay inside workspace and not be a symlink")
        if output.exists():
            try:
                existing = json.loads(output.read_text())
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise ValueError("existing output is not a target check report") from error
            if (
                not isinstance(existing, dict)
                or existing.get("artifact_kind") != "project_ontology_target_check"
                or type(existing.get("schema_version")) is not int
                or existing["schema_version"] != 1
                or existing.get("target_spec_id") != target_spec
                or existing.get("project_id") != project_id
            ):
                raise ValueError("existing output belongs to another artifact or target")
        report = build_target_context_check(
            root,
            project_id=project_id,
            target_spec_id=target_spec,
            selection_path=Path(selection) if selection is not None else None,
            ontologyc=Path(request["ontologyc"]) if request.get("ontologyc") is not None else None,
            compiler_sha256=request.get("compiler_sha256"),
            previous_report_path=Path(previous) if previous is not None else None,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.is_symlink() or not output.resolve().is_relative_to(root):
            raise ValueError("report output path must stay inside workspace and not be a symlink")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=output.parent, delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary, output)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        context = report.get("context") or {}
        result = (
            report
            if output_mode == "full"
            else {
                "artifact_kind": report["artifact_kind"],
                "outcome": report["outcome"],
                "target_spec_id": target_spec,
                "project_id": project_id,
                "context_revision": context.get("context_revision"),
                "context_outcome": context.get("outcome"),
                "report_path": output.relative_to(root).as_posix(),
                "previous_freshness": report.get("previous_freshness"),
                "diagnostics": report.get("diagnostics", []),
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return {"checked": 0, "unavailable": 1, "invalid": 2}[report["outcome"]]
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
