"""Select explicitly named specification YAML files inside one workspace."""

from pathlib import Path


def selected_yaml_files(workspace: Path, paths: list[str]) -> list[tuple[Path, Path]]:
    root = workspace.resolve(strict=True)
    if not root.is_dir() or not paths:
        raise ValueError("specify an existing workspace and at least one relative YAML file")
    selected = []
    for value in paths:
        relative = Path(value)
        if (
            relative.parts[:2] not in {("specs", "nodes"), ("docs", "drafts")}
            or ".." in relative.parts
            or relative.suffix not in {".yaml", ".yml"}
        ):
            raise ValueError(
                "YAML paths must be workspace-relative under specs/nodes or docs/drafts"
            )
        path = root / relative
        if path.resolve() != path or (path.exists() and not path.is_file()):
            raise ValueError("YAML paths must identify regular files without symlinks")
        selected.append((relative, path))
    return selected
