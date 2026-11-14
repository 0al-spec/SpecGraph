"""Independent structural check for the fixed review package experiment."""

import json


def grade(path, catalog):
    try:
        data = json.loads(path.read_text())
        expected = json.loads(catalog.read_text())["classes"]["DomainEntity"]
        for entry in data.get("foundationCatalogs", []):
            if entry.get("id") == "specgraph.foundation" and entry.get("version") == "0.1.0":
                observed = entry.get("catalog", {}).get("classes", {}).get("DomainEntity")
                return observed == expected and any(
                    item.get("fqid") == "review:Proposal"
                    and item.get("extends") == "sg:DomainEntity"
                    for item in data.get("classes", [])
                )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return False
