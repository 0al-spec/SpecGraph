"""Package-resource copying at an explicit filesystem boundary; no global install."""

import hashlib
from importlib.resources import files
from pathlib import Path

from . import __version__

DEFAULT_SKILL = "specgraph-conversation-notes"
SKILL_FILES = {
    DEFAULT_SKILL: ("SKILL.md", "references/usage.md"),
    "specgraph-project-ontology": ("SKILL.md",),
}


def skill_contents(skill_name: str = DEFAULT_SKILL) -> dict[str, bytes]:
    if skill_name not in SKILL_FILES:
        raise ValueError(f"Unknown skill: {skill_name}")
    root = files("specgraph")
    for part in ("resources", "skills", skill_name):
        root = root.joinpath(part)
    contents = {}
    for name in SKILL_FILES[skill_name]:
        resource = root
        for part in name.split("/"):
            resource = resource.joinpath(part)
        contents[name] = resource.read_bytes()
    return contents


def project_skill_destination(project: Path, skill_name: str = DEFAULT_SKILL) -> Path:
    if skill_name not in SKILL_FILES:
        raise ValueError(f"Unknown skill: {skill_name}")
    project = project.expanduser().absolute()
    if not project.is_dir():
        raise ValueError("Project must be an existing directory")
    codex = project / ".codex"
    skills = codex / "skills"
    if codex.is_symlink() or skills.is_symlink():
        raise ValueError("Project skill directories must not be symlinks")
    return skills / skill_name


def install_skill(destination: Path, skill_name: str = DEFAULT_SKILL) -> dict[str, object]:
    destination = destination.expanduser().absolute()
    contents = skill_contents(skill_name)
    if destination.is_symlink():
        raise ValueError("Skill destination must not be a symlink")
    if destination.exists():
        if not destination.is_dir() or any(
            (destination / name).is_symlink()
            or (destination / name).parent.is_symlink()
            or not (destination / name).is_file()
            or (destination / name).read_bytes() != data
            for name, data in contents.items()
        ):
            raise ValueError("Skill destination differs; existing content was not overwritten")
        status = "already_installed"
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.mkdir()  # Exclusive creation; a concurrent installer cannot overwrite it.
        for name, data in contents.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
        status = "installed"
    return {
        "status": status,
        "skill": skill_name,
        "runtime_version": __version__,
        "destination": str(destination),
        "files_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
