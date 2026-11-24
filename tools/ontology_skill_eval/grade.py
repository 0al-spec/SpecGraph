"""Independent structural check for the fixed review package experiment."""

import json
from pathlib import Path

from scenario import digest


def grade(path: Path, catalog: Path, *, exact_binding: bool = False) -> bool:
    try:
        data = json.loads(path.read_text())
        expected = json.loads(catalog.read_text())
        bindings = data.get("foundationCatalogs", [])
        if exact_binding and len(bindings) != 1:
            return False
        for entry in bindings:
            if entry.get("id") == "specgraph.foundation" and entry.get("version") == "0.1.0":
                observed = entry.get("catalog", {})
                if exact_binding and (
                    entry.get("alias") != "sg"
                    or entry.get("catalogByteDigest") != f"sha256:{digest(catalog)}"
                    or observed != expected
                ):
                    return False
                return (
                    observed.get("classes", {}).get("DomainEntity")
                    == expected["classes"]["DomainEntity"]
                ) and any(
                    item.get("fqid") == "review:Proposal"
                    and item.get("extends") == "sg:DomainEntity"
                    for item in data.get("classes", [])
                )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return False


def first_catalog_correct(trace: Path, expected: Path) -> bool | None:
    """Score the first projection invocation, or return None without usable evidence."""
    try:
        with trace.open() as file:
            first = json.loads(file.readline())
        if first["parsed"] is False:
            return False
        if first["parsed"] is True and isinstance(first["catalogs"], list):
            return first["catalogs"] == [str(expected)]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None
