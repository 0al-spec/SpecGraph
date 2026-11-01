"""CLI boundary for an explicit project ontology advisory check."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from project_ontology_check_scopes import DEFAULT_SCOPES, normalize_requested_scopes
from project_ontology_context.capture import _load_yaml, _parse
from project_ontology_supervisor_check import (
    TARGET_SPEC_ID_FORMAT,
    build_target_context_check,
    is_target_spec_id,
)

_PROJECT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def run_request(
    root: Path, request: dict[str, Any], *, target_spec: str | None, output_mode: str
) -> int:
    """Compute once, atomically persist only the derived report, and print its view."""
    try:
        if not isinstance(request, dict):
            raise ValueError("ontology context request must be a mapping")
        scopes = normalize_requested_scopes(request.get("requested_scopes", DEFAULT_SCOPES))
        root = Path(root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("workspace must be a directory")
        if not is_target_spec_id(target_spec):
            raise ValueError(f"--target-spec must be {TARGET_SPEC_ID_FORMAT}")
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
        output_path = output.resolve()
        protected = []
        if request.get("ontologyc") is not None:
            protected.append((Path(request["ontologyc"]).resolve(), "compiler"))
        if selection is not None:
            selection_file = (root / Path(selection)).resolve()
            protected.append((selection_file, "selection"))
            if selection_file == output_path:
                raise ValueError("report output collides with selected selection input")
            try:
                payload = _load_yaml(selection_file.read_bytes())
            except FileNotFoundError:
                pass  # The context check reports an unavailable selection.
            else:
                members, _, _ = _parse(payload)
                for member in members:
                    for field in ("source", "ir"):
                        path = Path(member[field])
                        resolved = (root / path).resolve()
                        if path.is_absolute() or not resolved.is_relative_to(root):
                            raise ValueError(f"selection {field} path must stay under workspace")
                        protected.append((resolved, field))
        for path, label in protected:
            if path == output_path:
                raise ValueError(f"report output collides with selected {label} input")
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
            requested_scopes=scopes,
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
                "requested_scopes": report["requested_scopes"],
                "assessments": (
                    {
                        scope: {
                            key: assessment[key]
                            for key in ("check_scope", "outcome", "diagnostics")
                        }
                        for scope, assessment in report["assessments"].items()
                    }
                    if report["assessments"] is not None
                    else None
                ),
                "context_revision": context.get("context_revision"),
                "context_outcome": context.get("outcome"),
                "report_path": output.relative_to(root).as_posix(),
                "previous_freshness": report.get("previous_freshness"),
                "diagnostics": report.get("diagnostics", []),
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return {"checked": 0, "unavailable": 1, "invalid": 2}[report["outcome"]]
    except (OSError, ValueError, TypeError, yaml.YAMLError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
