"""Pinned foundation catalog identities shared by lightweight ontology tools."""

from typing import NamedTuple


class FoundationPin(NamedTuple):
    id: str
    namespace: str
    version: str
    source_uri: str
    source_sha256: str


PIN = FoundationPin(
    id="ontology.foundation",
    namespace="ont",
    version="0.1.0",
    source_uri="https://github.com/0al-spec/Ontology/blob/c52553f872f440dde26c61abf9193f5fff171d98/SPECS/ontology/foundation/0.1.0/exports.json",
    source_sha256="1c6b3ac3e4aa9b4e56d823b3645f94c126840c1922c555998b848e9e0fe18f8f",
)
LEGACY_PIN = FoundationPin(
    id="specgraph.foundation",
    namespace="sg",
    version=PIN.version,
    source_uri=PIN.source_uri,
    source_sha256=PIN.source_sha256,
)
ACTION_PIN = FoundationPin(
    id="ontology.foundation",
    namespace="ont",
    version="0.2.0",
    source_uri="https://github.com/0al-spec/Ontology/blob/40672c189f33dee2b8c6fdac903758e90d9fba86/SPECS/ontology/foundation/0.2.0/exports.json",
    source_sha256="0444a5848b89cc8b0505ebc8a3114d07bfce9c9089a07f1c5a952f6ce8087841",
)
