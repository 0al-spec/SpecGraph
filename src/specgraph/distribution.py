"""Package-resource copying at an explicit filesystem boundary; no global install."""

import hashlib
from importlib.resources import files
from pathlib import Path

from . import __version__

SKILL_FILES = ("SKILL.md", "references/usage.md")


def skill_contents() -> dict[str, bytes]:
    root = files("specgraph")
    for part in ("resources", "skills", "specgraph-conversation-notes"):
        root = root.joinpath(part)
    contents = {}
    for name in SKILL_FILES:
        resource = root
        for part in name.split("/"):
            resource = resource.joinpath(part)
        contents[name] = resource.read_bytes()
    return contents


def install_skill(destination: Path) -> dict[str, object]:
    destination = destination.expanduser().absolute()
    contents = skill_contents()
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
        "skill": "specgraph-conversation-notes",
        "runtime_version": __version__,
        "destination": str(destination),
        "files_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
